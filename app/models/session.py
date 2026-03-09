from datetime import datetime

from app.extensions import db


class Session(db.Model):
    """
    会话元数据表：
    - id: 与 LangChain message_store.session_id 一一对应
    - user_id: 归属用户（关联 user.id）
    - title: AI 生成的会话标题
    - created_at / updated_at: 创建与最近更新时间
    """

    __tablename__ = "sessions"

    # 就是 session_id，例如 user_1_chat_default
    id = db.Column(db.String(64), primary_key=True)

    # 归属用户，外键指向 user.id，便于按用户查询
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    # AI 生成的标题，最长 100 字符
    title = db.Column(db.String(100), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Session {self.id} user={self.user_id}>"

