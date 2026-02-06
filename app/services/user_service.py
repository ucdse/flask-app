import time
from typing import Any

import jwt
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

import config
from app.extensions import db
from app.models import User


class UserRegistrationError(Exception):
    def __init__(self, message: str, error_code: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _create_token(
    user_id: int,
    secret: str,
    expires_seconds: int,
    token_type: str,
) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + expires_seconds,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _decode_token(token: str, secret: str, expired_msg: str, invalid_msg: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthError(expired_msg, 401)
    except jwt.InvalidTokenError:
        raise AuthError(invalid_msg, 401)


def _extract_user_id(payload: dict[str, Any]) -> int:
    raw_sub = payload.get("sub")
    if raw_sub is None:
        raise AuthError("invalid token payload", 401)
    try:
        return int(raw_sub)
    except (TypeError, ValueError):
        raise AuthError("invalid token payload", 401)


def create_access_token(user_id: int) -> str:
    return _create_token(
        user_id=user_id,
        secret=config.JWT_SECRET_KEY,
        expires_seconds=config.JWT_ACCESS_EXPIRES_SECONDS,
        token_type="access",
    )


def create_refresh_token(user_id: int) -> str:
    return _create_token(
        user_id=user_id,
        secret=config.JWT_REFRESH_SECRET_KEY,
        expires_seconds=config.JWT_REFRESH_EXPIRES_SECONDS,
        token_type="refresh",
    )


def verify_access_token(token: str) -> dict[str, Any]:
    """解码并校验 access 令牌，返回 payload；失败抛出 AuthError。"""
    payload = _decode_token(
        token=token,
        secret=config.JWT_SECRET_KEY,
        expired_msg="access token expired",
        invalid_msg="invalid access token",
    )
    if payload.get("type") != "access":
        raise AuthError("invalid token type", 401)
    payload["sub"] = _extract_user_id(payload)
    return payload


def verify_refresh_token(token: str) -> dict[str, Any]:
    """解码并校验 refresh 令牌，返回 payload；失败抛出 AuthError。"""
    payload = _decode_token(
        token=token,
        secret=config.JWT_REFRESH_SECRET_KEY,
        expired_msg="refresh token expired",
        invalid_msg="invalid refresh token",
    )
    if payload.get("type") != "refresh":
        raise AuthError("invalid token type", 401)
    payload["sub"] = _extract_user_id(payload)
    return payload


def login_user(identifier: str, password: str) -> dict[str, Any]:
    """使用用户名或邮箱 + 密码登录，返回 access_token、refresh_token、expires_in。"""
    user = db.session.scalar(
        db.select(User).where(
            or_(User.username == identifier, User.email == identifier.lower())
        )
    )
    if user is None:
        raise AuthError("invalid username/email or password", 401)
    if not user.is_active:
        raise AuthError("account is disabled", 403)
    if not check_password_hash(user.password_hash, password):
        raise AuthError("invalid username/email or password", 401)

    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "expires_in": config.JWT_ACCESS_EXPIRES_SECONDS,
        "token_type": "Bearer",
    }


def refresh_tokens(refresh_token: str) -> dict[str, Any]:
    """使用 refresh 令牌换取新的 access_token 与 refresh_token。"""
    payload = verify_refresh_token(refresh_token)
    user_id = payload.get("sub")
    if not user_id:
        raise AuthError("invalid refresh token", 401)
    user = db.session.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthError("user not found or disabled", 401)
    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "expires_in": config.JWT_ACCESS_EXPIRES_SECONDS,
        "token_type": "Bearer",
    }


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
