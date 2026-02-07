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
        print(f"[邮箱验证] 登录被拒: 账户未激活，请先完成邮箱验证 email={user.email} username={user.username}")
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


def _generate_verification_code() -> str:
    """生成 6 位数字验证码。"""
    return "".join(str(random.randint(0, 9)) for _ in range(6))


def _generate_activation_token() -> str:
    """生成用于激活链接的唯一 Token（URL 安全）。"""
    return secrets.token_urlsafe(32)


def _now_utc() -> datetime:
    """返回当前 UTC 时间（timezone-aware）。"""
    return datetime.now(timezone.utc)


def _as_utc_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """
    将 datetime 统一为 UTC timezone-aware，便于与 _now_utc() 比较。
    数据库读出的时间可能是 naive（无时区），视为 UTC 并附上 tzinfo；已是 aware 则转为 UTC。
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

    # 注册时自动发送一次：SMTP 发邮件（若已配置）+ 控制台输出便于调试
    print(f"[邮箱验证] 注册成功，已发送验证码（见下方）")
    print(f"[邮箱验证-注册] email={user.email} username={user.username} 验证码={verification_code} 过期={expires_at.isoformat()}")
    send_verification_code_email_async(
        user.email,
        verification_code,
        config.VERIFICATION_CODE_EXPIRE_SECONDS // 60,
        activation_token=activation_token,
    )

    return serialize_user(user)


def send_verification_code(identifier: str) -> dict[str, Any]:
    """
    主动请求发送验证码。仅对未激活用户有效；每分钟最多请求一次；每次会覆盖旧验证码（仅最新有效）。
    """
    print(f"[邮箱验证] 请求发送验证码 identifier={identifier!r}")

    user = db.session.scalar(
        db.select(User).where(
            or_(User.username == identifier, User.email == identifier.lower())
        )
    )
    if user is None:
        print(f"[邮箱验证] 发送失败: 用户不存在 identifier={identifier!r}")
        raise AuthError("user not found", 404)
    if user.is_active:
        print(f"[邮箱验证] 发送失败: 账户已激活 email={user.email} username={user.username}")
        raise AuthError("account is already active", 400)

    now = _now_utc()
    sent_at_utc = _as_utc_aware(user.email_verification_code_sent_at)
    if sent_at_utc is not None:
        elapsed = (now - sent_at_utc).total_seconds()
        if elapsed < config.VERIFICATION_CODE_RESEND_COOLDOWN_SECONDS:
            wait_secs = int(config.VERIFICATION_CODE_RESEND_COOLDOWN_SECONDS - elapsed)
            print(f"[邮箱验证] 发送失败: 限频，需再等 {wait_secs}s 上次发送={sent_at_utc.isoformat()}")
            raise AuthError(f"please wait {wait_secs} seconds before requesting another code", 429)

    code = _generate_verification_code()
    expires_at = now + timedelta(seconds=config.VERIFICATION_CODE_EXPIRE_SECONDS)
    user.email_verification_code = code
    user.email_verification_code_expires_at = expires_at
    user.email_verification_code_sent_at = now
    db.session.commit()

    print(f"[邮箱验证-重发] email={user.email} username={user.username} 验证码={code} 过期={expires_at.isoformat()}")
    send_verification_code_email_async(
        user.email,
        code,
        config.VERIFICATION_CODE_EXPIRE_SECONDS // 60,
    )
    return {"message": "verification code sent"}


def activate_user(identifier: str, code: str) -> dict[str, Any]:
    """
    使用邮箱或用户名 + 6 位验证码激活账户。
    仅最新一次发送的验证码有效；过期则不可用。验证通过则设置 is_active=True 并清空验证码相关字段。
    """
    code_stripped = code.strip()
    print(f"[邮箱验证] 尝试激活 identifier={identifier!r} code={code_stripped!r}")

    user = db.session.scalar(
        db.select(User).where(
            or_(User.username == identifier, User.email == identifier.lower())
        )
    )
    if user is None:
        print(f"[邮箱验证] 激活失败: 用户不存在 identifier={identifier!r}")
        raise AuthError("user not found", 404)
    if user.is_active:
        print(f"[邮箱验证] 激活失败: 账户已激活 email={user.email} username={user.username}")
        raise AuthError("account is already active", 400)
    if not user.email_verification_code:
        print(f"[邮箱验证] 激活失败: 无待验证码 email={user.email} username={user.username}")
        raise AuthError("no pending verification code", 400)
    now = _now_utc()
    expires_at_utc = _as_utc_aware(user.email_verification_code_expires_at)
    if expires_at_utc is not None and now > expires_at_utc:
        print(f"[邮箱验证] 激活失败: 验证码已过期 过期时间={expires_at_utc.isoformat()} now={now.isoformat()}")
        raise AuthError("verification code expired", 400)
    if user.email_verification_code != code_stripped:
        print(f"[邮箱验证] 激活失败: 验证码错误 期望={user.email_verification_code!r} 收到={code_stripped!r}")
        raise AuthError("invalid verification code", 400)

    user.is_active = True
    user.email_verification_code = None
    user.email_verification_code_expires_at = None
    user.email_verification_code_sent_at = None
    user.activation_token = None
    db.session.commit()
    print(f"[邮箱验证] 激活成功 email={user.email} username={user.username} id={user.id}")
    return serialize_user(user)


def activate_by_token(token: str) -> dict[str, Any]:
    """
    使用邮件中的激活链接 Token 激活账户。
    URL 形式：/activate/:token，前端将 token 传入本接口。验证通过则设置 is_active=True 并清空 token 与验证码。
    """
    token_stripped = token.strip()
    print(f"[邮箱验证] 尝试通过 Token 激活 token={token_stripped[:16]}...")

    user = db.session.scalar(db.select(User).where(User.activation_token == token_stripped))
    if user is None:
        print(f"[邮箱验证] 激活失败: Token 无效或已使用")
        raise AuthError("invalid or expired activation link", 400)
    if user.is_active:
        print(f"[邮箱验证] 激活失败: 账户已激活 email={user.email} username={user.username}")
        raise AuthError("account is already active", 400)
    now = _now_utc()
    expires_at_utc = _as_utc_aware(user.email_verification_code_expires_at)
    if expires_at_utc is not None and now > expires_at_utc:
        print(f"[邮箱验证] 激活失败: 链接已过期 过期时间={expires_at_utc.isoformat()}")
        raise AuthError("activation link expired", 400)

    user.is_active = True
    user.email_verification_code = None
    user.email_verification_code_expires_at = None
    user.email_verification_code_sent_at = None
    user.activation_token = None
    db.session.commit()
    print(f"[邮箱验证] 激活成功（Token） email={user.email} username={user.username} id={user.id}")
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
