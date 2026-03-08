# app/models/chat_history.py
from app.extensions import db


class ChatHistory(db.Model):
    """
    专门给 LangChain 使用的聊天记录表
    让 Flask-Migrate 知道这张表的存在，避免被意外 Drop
    """
    __tablename__ = 'message_store'  # 保持和 LangChain 默认表名一致

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Text)  # 存储用户或会话 ID
    message = db.Column(db.JSON)     # 存储 JSON 格式的消息体 (MySQL 推荐用 JSON)
