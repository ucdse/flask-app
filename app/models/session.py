from datetime import datetime, timezone

from app.extensions import db


class Session(db.Model):
    """
    Session metadata table:
    - id: One-to-one correspondence with LangChain message_store.session_id
    - user_id: Owning user (references user.id)
    - title: AI-generated session title
    - created_at / updated_at: Creation and last update times
    """

    __tablename__ = "sessions"

    # This is the session_id, e.g. user_1_chat_default
    id = db.Column(db.String(64), primary_key=True)

    # Owning user, foreign key references user.id, convenient for querying by user
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    # AI-generated title, max 100 characters
    title = db.Column(db.String(100), nullable=True)

    @staticmethod
    def utcnow() -> datetime:
        """Returns timezone-aware UTC time, avoiding deprecation warnings from datetime.utcnow."""
        return datetime.now(timezone.utc)

    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    def __repr__(self) -> str:
        return f"<Session {self.id} user={self.user_id}>"
