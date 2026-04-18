import random
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

import config
from app.extensions import db
from app.models import User
from app.utils.email import send_verification_code_email_async


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
    token_version: int,
    secret: str,
    expires_seconds: int,
    token_type: str,
) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "ver": token_version,
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


def _extract_token_version(payload: dict[str, Any]) -> int:
    raw_ver = payload.get("ver", 0)
    try:
        token_version = int(raw_ver)
    except (TypeError, ValueError):
        raise AuthError("invalid token payload", 401)
    if token_version < 0:
        raise AuthError("invalid token payload", 401)
    return token_version


def create_access_token(user_id: int, token_version: int) -> str:
    return _create_token(
        user_id=user_id,
        token_version=token_version,
        secret=config.JWT_SECRET_KEY,
        expires_seconds=config.JWT_ACCESS_EXPIRES_SECONDS,
        token_type="access",
    )


def create_refresh_token(user_id: int, token_version: int) -> str:
    return _create_token(
        user_id=user_id,
        token_version=token_version,
        secret=config.JWT_REFRESH_SECRET_KEY,
        expires_seconds=config.JWT_REFRESH_EXPIRES_SECONDS,
        token_type="refresh",
    )


def verify_access_token(token: str) -> dict[str, Any]:
    """Decode and validate the access token, returning the payload; raises AuthError on failure."""
    payload = _decode_token(
        token=token,
        secret=config.JWT_SECRET_KEY,
        expired_msg="access token expired",
        invalid_msg="invalid access token",
    )
    if payload.get("type") != "access":
        raise AuthError("invalid token type", 401)
    user_id = _extract_user_id(payload)
    token_version = _extract_token_version(payload)
    user = db.session.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthError("user not found or disabled", 401)
    if token_version != user.token_version:
        raise AuthError("access token has been revoked", 401)
    payload["sub"] = user_id
    payload["ver"] = token_version
    return payload


def verify_refresh_token(token: str) -> dict[str, Any]:
    """Decode and validate the refresh token, returning the payload; raises AuthError on failure."""
    payload = _decode_token(
        token=token,
        secret=config.JWT_REFRESH_SECRET_KEY,
        expired_msg="refresh token expired",
        invalid_msg="invalid refresh token",
    )
    if payload.get("type") != "refresh":
        raise AuthError("invalid token type", 401)
    payload["sub"] = _extract_user_id(payload)
    payload["ver"] = _extract_token_version(payload)
    return payload


def login_user(identifier: str, password: str) -> dict[str, Any]:
    """Login with username or email and password, returning access_token, refresh_token, and expires_in."""
    user = db.session.scalar(
        db.select(User).where(
            or_(User.username == identifier, User.email == identifier.lower())
        )
    )
    if user is None:
        raise AuthError("invalid username/email or password", 401)
    if not user.is_active:
        print(f"[Email Verification] Login rejected: account not activated, please complete email verification email={user.email} username={user.username}")
        raise AuthError("account is disabled", 403)
    if not check_password_hash(user.password_hash, password):
        raise AuthError("invalid username/email or password", 401)

    return {
        "access_token": create_access_token(user.id, user.token_version),
        "refresh_token": create_refresh_token(user.id, user.token_version),
        "expires_in": config.JWT_ACCESS_EXPIRES_SECONDS,
        "token_type": "Bearer",
    }


def refresh_tokens(refresh_token: str) -> dict[str, Any]:
    """Exchange a refresh token for a new access_token and refresh_token."""
    payload = verify_refresh_token(refresh_token)
    user_id = payload.get("sub")
    token_version = payload.get("ver")
    if not user_id:
        raise AuthError("invalid refresh token", 401)
    user = db.session.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthError("user not found or disabled", 401)
    if token_version != user.token_version:
        raise AuthError("refresh token has been revoked", 401)
    return {
        "access_token": create_access_token(user.id, user.token_version),
        "refresh_token": create_refresh_token(user.id, user.token_version),
        "expires_in": config.JWT_ACCESS_EXPIRES_SECONDS,
        "token_type": "Bearer",
    }


def logout_user(access_token: str) -> None:
    """
    Invalidate all sessions for the user associated with the current access token.
    Implementation: increment token_version, which invalidates all old access/refresh tokens.
    """
    payload = verify_access_token(access_token)
    user = db.session.get(User, payload["sub"])
    if user is None or not user.is_active:
        raise AuthError("user not found or disabled", 401)
    user.token_version += 1
    db.session.commit()


def _generate_verification_code() -> str:
    """Generate a 6-digit numeric verification code."""
    return "".join(str(random.randint(0, 9)) for _ in range(6))


def _generate_activation_token() -> str:
    """Generate a unique token (URL-safe) for the activation link."""
    return secrets.token_urlsafe(32)


def _now_utc() -> datetime:
    """Return the current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


def _as_utc_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Convert datetime to UTC timezone-aware for comparison with _now_utc().
    Datetimes from the database may be naive (no timezone); treat them as UTC and attach tzinfo;
    if already aware, convert to UTC.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def register_user(payload: dict[str, Any]) -> dict[str, Any]:
    existing_user = db.session.scalar(
        db.select(User).where(or_(User.username == payload["username"], User.email == payload["email"]))
    )
    if existing_user is not None:
        if existing_user.username == payload["username"]:
            raise UserRegistrationError("username already exists.", "username_exists", 409)
        raise UserRegistrationError("email already exists.", "email_exists", 409)

    verification_code = _generate_verification_code()
    activation_token = _generate_activation_token()
    now = _now_utc()
    expires_at = now + timedelta(seconds=config.VERIFICATION_CODE_EXPIRE_SECONDS)

    user = User(
        username=payload["username"],
        email=payload["email"],
        password_hash=generate_password_hash(payload["password"]),
        avatar_url=payload["avatar_url"],
        is_active=False,
        email_verification_code=verification_code,
        email_verification_code_expires_at=expires_at,
        email_verification_code_sent_at=now,
        activation_token=activation_token,
    )

    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise UserRegistrationError("username or email already exists.", "user_conflict", 409) from None

    # Auto-send on registration: SMTP email (if configured) + console output for debugging
    print(f"[Email Verification] Registration successful, verification code sent (see below)")
    print(f"[Email Verification - Register] email={user.email} username={user.username} code={verification_code} expires={expires_at.isoformat()}")
    send_verification_code_email_async(
        user.email,
        verification_code,
        config.VERIFICATION_CODE_EXPIRE_SECONDS // 60,
        activation_token=activation_token,
    )

    return serialize_user(user)


def send_verification_code(identifier: str) -> dict[str, Any]:
    """
    Actively request sending a verification code. Only valid for inactive users;
    maximum one request per minute; each request overwrites the old code (only the latest is valid).
    """
    print(f"[Email Verification] Requesting verification code identifier={identifier!r}")

    user = db.session.scalar(
        db.select(User).where(
            or_(User.username == identifier, User.email == identifier.lower())
        )
    )
    if user is None:
        print(f"[Email Verification] Send failed: user does not exist identifier={identifier!r}")
        raise AuthError("user not found", 404)
    if user.is_active:
        print(f"[Email Verification] Send failed: account already activated email={user.email} username={user.username}")
        raise AuthError("account is already active", 400)

    now = _now_utc()
    sent_at_utc = _as_utc_aware(user.email_verification_code_sent_at)
    if sent_at_utc is not None:
        elapsed = (now - sent_at_utc).total_seconds()
        if elapsed < config.VERIFICATION_CODE_RESEND_COOLDOWN_SECONDS:
            wait_secs = int(config.VERIFICATION_CODE_RESEND_COOLDOWN_SECONDS - elapsed)
            print(f"[Email Verification] Send failed: rate limited, wait {wait_secs}s last sent={sent_at_utc.isoformat()}")
            raise AuthError(f"please wait {wait_secs} seconds before requesting another code", 429)

    code = _generate_verification_code()
    expires_at = now + timedelta(seconds=config.VERIFICATION_CODE_EXPIRE_SECONDS)
    user.email_verification_code = code
    user.email_verification_code_expires_at = expires_at
    user.email_verification_code_sent_at = now
    db.session.commit()

    print(f"[Email Verification - Resend] email={user.email} username={user.username} code={code} expires={expires_at.isoformat()}")
    send_verification_code_email_async(
        user.email,
        code,
        config.VERIFICATION_CODE_EXPIRE_SECONDS // 60,
    )
    return {"message": "verification code sent"}


def activate_user(identifier: str, code: str) -> dict[str, Any]:
    """
    Activate account using email or username plus 6-digit verification code.
    Only the most recently sent code is valid; expired codes cannot be used.
    On successful verification, sets is_active=True and clears verification code fields.
    """
    code_stripped = code.strip()
    print(f"[Email Verification] Attempting activation identifier={identifier!r} code={code_stripped!r}")

    user = db.session.scalar(
        db.select(User).where(
            or_(User.username == identifier, User.email == identifier.lower())
        )
    )
    if user is None:
        print(f"[Email Verification] Activation failed: user does not exist identifier={identifier!r}")
        raise AuthError("user not found", 404)
    if user.is_active:
        print(f"[Email Verification] Activation failed: account already activated email={user.email} username={user.username}")
        raise AuthError("account is already active", 400)
    if not user.email_verification_code:
        print(f"[Email Verification] Activation failed: no pending verification code email={user.email} username={user.username}")
        raise AuthError("no pending verification code", 400)
    now = _now_utc()
    expires_at_utc = _as_utc_aware(user.email_verification_code_expires_at)
    if expires_at_utc is not None and now > expires_at_utc:
        print(f"[Email Verification] Activation failed: code expired expires={expires_at_utc.isoformat()} now={now.isoformat()}")
        raise AuthError("verification code expired", 400)
    if user.email_verification_code != code_stripped:
        print(f"[Email Verification] Activation failed: code incorrect expected={user.email_verification_code!r} received={code_stripped!r}")
        raise AuthError("invalid verification code", 400)

    user.is_active = True
    user.email_verification_code = None
    user.email_verification_code_expires_at = None
    user.email_verification_code_sent_at = None
    user.activation_token = None
    db.session.commit()
    print(f"[Email Verification] Activation successful email={user.email} username={user.username} id={user.id}")
    return serialize_user(user)


def activate_by_token(token: str) -> dict[str, Any]:
    """
    Activate account using the activation link token from email.
    URL format: /activate/:token, frontend passes token to this endpoint.
    On successful verification, sets is_active=True and clears token and verification code.
    """
    token_stripped = token.strip()
    print(f"[Email Verification] Attempting token activation token={token_stripped[:16]}...")

    user = db.session.scalar(db.select(User).where(User.activation_token == token_stripped))
    if user is None:
        print(f"[Email Verification] Activation failed: token invalid or already used")
        raise AuthError("invalid or expired activation link", 400)
    if user.is_active:
        print(f"[Email Verification] Activation failed: account already activated email={user.email} username={user.username}")
        raise AuthError("account is already active", 400)
    now = _now_utc()
    expires_at_utc = _as_utc_aware(user.email_verification_code_expires_at)
    if expires_at_utc is not None and now > expires_at_utc:
        print(f"[Email Verification] Activation failed: link expired expires={expires_at_utc.isoformat()}")
        raise AuthError("activation link expired", 400)

    user.is_active = True
    user.email_verification_code = None
    user.email_verification_code_expires_at = None
    user.email_verification_code_sent_at = None
    user.activation_token = None
    db.session.commit()
    print(f"[Email Verification] Activation successful (Token) email={user.email} username={user.username} id={user.id}")
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
