from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class User(db.Model):
    __tablename__ = "user"

    # Auto-incrementing primary key ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Username: unique and indexed for fast lookups
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    # Email: unique and indexed, used for login or password recovery
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)

    # Password hash: never store plaintext passwords, reserve sufficient length (e.g. 128 or 256) for hash strings
    password_hash: Mapped[str] = mapped_column(String(256))

    # Avatar URL (optional)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Account status: whether activated (e.g. True after email verification); new users default to inactive
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="Whether account is activated; 0=disabled, 1=activated")

    # Email verification code: 6-digit code generated on registration/resend, cleared after activation; only the latest one is valid; emails not sent yet, only printed to console
    email_verification_code: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)
    # Verification code expiration time (e.g. 5 minutes later); validated on activation
    email_verification_code_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Last time verification code was sent, used for rate limiting (e.g. max once per minute)
    email_verification_code_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Activation token: sent in email as /activate/:token, clicking activates; equivalent to and expires with verification code
    activation_token: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True, index=True)
    # Token version number: increments on logout to immediately invalidate old access/refresh tokens
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Creation time: uses database-level default value (server_default)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Update time: automatically refreshed each time the record is updated
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    def __repr__(self) -> str:
        return f"<User {self.id}: {self.username}>"
