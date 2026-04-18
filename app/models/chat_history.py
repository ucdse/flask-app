# app/models/chat_history.py
from app.extensions import db


class ChatHistory(db.Model):
    """
    Chat history table specifically for LangChain.
    Lets Flask-Migrate know this table exists to avoid accidental drops.
    """
    __tablename__ = 'message_store'  # Kept consistent with LangChain's default table name

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Text)  # Stores user or session ID
    message = db.Column(db.JSON)     # Stores message body in JSON format (MySQL recommends using JSON)
