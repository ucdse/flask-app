import hashlib
import json
import logging
import re

from flask import current_app
from sqlalchemy.exc import IntegrityError
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI

from app.extensions import db
from app.models import ChatHistory, Session

logger = logging.getLogger(__name__)


def get_chat_history(session_id: str):
    """Dynamically get the database memory object for the given session_id, reusing the Flask-SQLAlchemy engine to avoid rebuilding the connection pool on every request."""
    return SQLChatMessageHistory(
        session_id=session_id,
        connection=db.engine,
        table_name="message_store",
    )


def _ensure_session(session_id: str, user_id: int) -> Session:
    """
    Ensure a current session record exists in the sessions table and update updated_at.
    - Create if it doesn't exist (only id and user_id)
    - If it already exists, only refresh updated_at
    """
    session = db.session.get(Session, session_id)
    if session is None:
        session = Session(id=session_id, user_id=user_id)
        db.session.add(session)
    # Explicitly refresh the recent update time for sorting by updated_at
    session.updated_at = Session.utcnow()
    try:
        db.session.commit()
    except IntegrityError:
        # When concurrently creating the same session, rollback and reuse the persisted record to avoid returning 500 for the first message.
        db.session.rollback()
        session = db.session.get(Session, session_id)
        if session is None or session.user_id != user_id:
            raise
        session.updated_at = Session.utcnow()
        db.session.commit()
    return session


def generate_session_id(user_id: int, chat_id: str) -> str:
    """
    Generate the actual session_id for storage based on the chat_id provided by the frontend.

    In the current design, the frontend only maintains chat_id, and the backend always calculates
    a unique session_id from user_id + chat_id, no longer trying to reuse chat_id as an existing session primary key.
    """
    if not isinstance(chat_id, str):
        chat_id = str(chat_id)

    prefix = f"user_{user_id}_chat_"
    candidate = f"{prefix}{chat_id}"
    if len(candidate) <= 64 and re.fullmatch(r"[A-Za-z0-9_.-]+", chat_id) is not None:
        return candidate

    digest = hashlib.sha256(chat_id.encode("utf-8")).hexdigest()[:32]
    return f"{prefix}h_{digest}"


def _generate_title(session_id: str, first_message: str) -> None:
    """Generate session title from the first user message and write it to the sessions table (only set once if no title currently exists)."""
    try:
        llm = ChatOpenAI(
            api_key=current_app.config["ALIYUN_API_KEY"],
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="qwen-plus",
        )
        prompt = (
            "Summarize the topic of this sentence in 6 words or less, output only the title without punctuation: "
            f"{first_message[:200]}"
        )
        title = llm.invoke(prompt).content.strip()[:50]

        session = db.session.get(Session, session_id)
        if session and not session.title:
            session.title = title
            session.updated_at = Session.utcnow()
            db.session.commit()
    except Exception:
        logger.exception("Title generation failed")


def get_session_messages(session_id: str, user_id: int) -> list[dict[str, str]] | None:
    """
    Get the historical message list for the specified session (current user's sessions only).
    - Returns None if the session does not exist or does not belong to the current user
    - Returns [] if the session exists but has no messages yet
    - Normally returns [{role, content}, ...] in chronological order
    """
    # First confirm session ownership to prevent unauthorized access
    session = db.session.get(Session, session_id)
    if session is None or session.user_id != user_id:
        return None

    rows = (
        db.session.query(ChatHistory)
        .filter_by(session_id=session_id)
        .order_by(ChatHistory.id.asc())
        .all()
    )

    def _map_role(message: dict) -> str:
        msg_type = (message or {}).get("type")
        if msg_type == "human":
            return "user"
        if msg_type == "ai":
            return "assistant"
        # Compatible with system / tool and other types
        if msg_type in {"system", "tool"}:
            return msg_type
        return msg_type or "assistant"

    history: list[dict[str, str]] = []
    for row in rows:
        msg = row.message or {}
        data = msg.get("data") or {}
        content = data.get("content") or ""
        if not isinstance(content, str):
            # In LangChain spec, content should be a string; do a string conversion in exception cases
            content = str(content)
        history.append(
            {
                "role": _map_role(msg),
                "content": content,
            }
        )

    return history


def generate_chat_response(session_id: str, user_message: str, user_id: int) -> str:
    """Handle core dialogue logic (non-streaming), and maintain sessions table and title generation."""

    # Check if this is the first message for the current session (based on message_store)
    is_first_message = not db.session.execute(
        db.text("SELECT 1 FROM message_store WHERE session_id = :sid LIMIT 1"),
        {"sid": session_id},
    ).fetchone()

    # Ensure session record exists in sessions table and update last used time
    _ensure_session(session_id, user_id)

    # Initialize model
    llm = ChatOpenAI(
        api_key=current_app.config["ALIYUN_API_KEY"],
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen-plus",
    )

    # Assemble Prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful intelligent assistant. Please answer questions based on the context.",
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{user_input}"),
        ]
    )

    # Assemble Chain and attach memory module
    chain = prompt | llm
    chain_with_history = RunnableWithMessageHistory(
        chain,
        get_chat_history,
        input_messages_key="user_input",
        history_messages_key="chat_history",
    )

    # Invoke model
    response = chain_with_history.invoke(
        {"user_input": user_message},
        config={"configurable": {"session_id": session_id}},
    )

    # If this is the first message, generate the title (one-time only)
    if is_first_message:
        _generate_title(session_id, user_message)

    return response.content


def generate_chat_stream(session_id: str, user_message: str, user_id: int):
    """Stream process core dialogue logic (Generator), and maintain sessions table and title generation."""

    try:
        # Check if this is the first message for the current session (based on message_store)
        is_first_message = not db.session.execute(
            db.text("SELECT 1 FROM message_store WHERE session_id = :sid LIMIT 1"),
            {"sid": session_id},
        ).fetchone()

        # Ensure session record exists in sessions table and update last used time
        _ensure_session(session_id, user_id)

        llm = ChatOpenAI(
            api_key=current_app.config["ALIYUN_API_KEY"],
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="qwen-plus",
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful intelligent assistant. Please answer questions based on the context.",
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{user_input}"),
            ]
        )

        chain = prompt | llm
        chain_with_history = RunnableWithMessageHistory(
            chain,
            get_chat_history,
            input_messages_key="user_input",
            history_messages_key="chat_history",
        )

        for chunk in chain_with_history.stream(
            {"user_input": user_message},
            config={"configurable": {"session_id": session_id}},
        ):
            if chunk.content:
                yield f"data: {json.dumps({'content': chunk.content}, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

        # After streaming ends, if this is the first message, generate the title
        if is_first_message:
            _generate_title(session_id, user_message)

    except Exception:
        logger.exception("Stream generation failed")
        yield f"data: {json.dumps({'error': 'Service temporarily unavailable, please try again later'}, ensure_ascii=False)}\n\n"
