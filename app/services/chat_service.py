from datetime import datetime
import json
import logging

from flask import current_app

from app.extensions import db
from app.models import Session
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


def get_chat_history(session_id: str):
    """动态获取对应 session_id 的数据库记忆对象，复用 Flask-SQLAlchemy 的 engine，避免每次请求重建连接池。"""
    return SQLChatMessageHistory(
        session_id=session_id,
        connection=db.engine,
        table_name="message_store",
    )


def _ensure_session(session_id: str, user_id: int) -> Session:
    """
    确保 sessions 表中存在一条当前会话记录，并更新 updated_at。
    - 若不存在则创建（仅包含 id 和 user_id）
    - 若已存在则只刷新 updated_at
    """
    session = db.session.get(Session, session_id)
    if session is None:
        session = Session(id=session_id, user_id=user_id)
        db.session.add(session)
    # 显式刷新最近更新时间，便于按 updated_at 排序
    session.updated_at = datetime.utcnow()
    db.session.commit()
    return session


def _generate_title(session_id: str, first_message: str) -> None:
    """根据第一条用户消息生成会话标题，写入 sessions 表（仅在当前尚无标题时设置一次）。"""
    try:
        llm = ChatOpenAI(
            api_key=current_app.config["ALIYUN_API_KEY"],
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="qwen-plus",
        )
        prompt = (
            "用6个字以内概括这句话的主题，只输出标题，不加标点："
            f"{first_message[:200]}"
        )
        title = llm.invoke(prompt).content.strip()[:50]

        session = db.session.get(Session, session_id)
        if session and not session.title:
            session.title = title
            session.updated_at = datetime.utcnow()
            db.session.commit()
    except Exception:
        logger.exception("Title generation failed")


def generate_chat_response(session_id: str, user_message: str, user_id: int) -> str:
    """处理核心对话逻辑（非流式），并维护 sessions 表与标题生成。"""

    # 检查是否为当前 session 的第一条消息（基于 message_store）
    is_first_message = not db.session.execute(
        db.text("SELECT 1 FROM message_store WHERE session_id = :sid LIMIT 1"),
        {"sid": session_id},
    ).fetchone()

    # 确保 sessions 表中存在会话记录，并更新最近使用时间
    _ensure_session(session_id, user_id)

    # 初始化模型
    llm = ChatOpenAI(
        api_key=current_app.config["ALIYUN_API_KEY"],
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen-plus",
    )

    # 组装 Prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "你是一个得力的智能助手，请根据上下文回答问题。"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{user_input}"),
        ]
    )

    # 组装 Chain 并外挂记忆模块
    chain = prompt | llm
    chain_with_history = RunnableWithMessageHistory(
        chain,
        get_chat_history,
        input_messages_key="user_input",
        history_messages_key="chat_history",
    )

    # 调用模型
    response = chain_with_history.invoke(
        {"user_input": user_message},
        config={"configurable": {"session_id": session_id}},
    )

    # 如果是第一条消息，生成标题（一次性）
    if is_first_message:
        _generate_title(session_id, user_message)

    return response.content


def generate_chat_stream(session_id: str, user_message: str, user_id: int):
    """流式处理核心对话逻辑 (Generator)，并维护 sessions 表与标题生成。"""

    try:
        # 检查是否为当前 session 的第一条消息（基于 message_store）
        is_first_message = not db.session.execute(
            db.text("SELECT 1 FROM message_store WHERE session_id = :sid LIMIT 1"),
            {"sid": session_id},
        ).fetchone()

        # 确保 sessions 表中存在会话记录，并更新最近使用时间
        _ensure_session(session_id, user_id)

        llm = ChatOpenAI(
            api_key=current_app.config["ALIYUN_API_KEY"],
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="qwen-plus",
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "你是一个得力的智能助手，请根据上下文回答问题。"),
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

        # 流式结束后，如果是第一条消息则生成标题
        if is_first_message:
            _generate_title(session_id, user_message)

    except Exception:
        logger.exception("Stream generation failed")
        yield f"data: {json.dumps({'error': '服务暂时不可用，请稍后重试'}, ensure_ascii=False)}\n\n"
