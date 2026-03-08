# app/services/chat_service.py
import json

from flask import current_app

from app.extensions import db
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory


def get_chat_history(session_id: str):
    """动态获取对应 session_id 的数据库记忆对象，复用 Flask-SQLAlchemy 的 engine，避免每次请求重建连接池。"""
    return SQLChatMessageHistory(
        session_id=session_id,
        connection=db.engine,
        table_name='message_store'
    )


def generate_chat_response(session_id: str, user_message: str) -> str:
    """处理核心对话逻辑"""

    # 1. 初始化模型
    llm = ChatOpenAI(
        api_key=current_app.config['ALIYUN_API_KEY'],
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen-plus"
    )

    # 2. 组装 Prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个得力的智能助手，请根据上下文回答问题。"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{user_input}")
    ])

    # 3. 组装 Chain 并外挂记忆模块
    chain = prompt | llm
    chain_with_history = RunnableWithMessageHistory(
        chain,
        get_chat_history,
        input_messages_key="user_input",
        history_messages_key="chat_history"
    )

    # 4. 调用模型
    response = chain_with_history.invoke(
        {"user_input": user_message},
        config={"configurable": {"session_id": session_id}}
    )

    return response.content


def generate_chat_stream(session_id: str, user_message: str):
    """流式处理核心对话逻辑 (Generator)"""

    llm = ChatOpenAI(
        api_key=current_app.config['ALIYUN_API_KEY'],
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen-plus"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个得力的智能助手，请根据上下文回答问题。"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{user_input}")
    ])

    chain = prompt | llm
    chain_with_history = RunnableWithMessageHistory(
        chain,
        get_chat_history,
        input_messages_key="user_input",
        history_messages_key="chat_history"
    )

    # 使用 .stream()，JSON 编码后输出，避免 chunk 内换行符破坏 SSE 格式
    for chunk in chain_with_history.stream(
        {"user_input": user_message},
        config={"configurable": {"session_id": session_id}}
    ):
        if chunk.content:
            yield f"data: {json.dumps({'content': chunk.content}, ensure_ascii=False)}\n\n"
