from typing import Any

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import User


class UserRegistrationError(Exception):
    def __init__(self, message: str, error_code: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


def register_user(payload: dict[str, Any]) -> dict[str, Any]:
    existing_user = db.session.scalar(
        db.select(User).where(or_(User.username == payload["username"], User.email == payload["email"]))
    )
    if existing_user is not None:
        if existing_user.username == payload["username"]:
            raise UserRegistrationError("username already exists.", "username_exists", 409)
        raise UserRegistrationError("email already exists.", "email_exists", 409)

    user = User(
        username=payload["username"],
        email=payload["email"],
        password_hash=generate_password_hash(payload["password"]),
        avatar_url=payload["avatar_url"],
    )

    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise UserRegistrationError("username or email already exists.", "user_conflict", 409) from None

    return serialize_user(user)


def serialize_user(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "avatar_url": user.avatar_url,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
