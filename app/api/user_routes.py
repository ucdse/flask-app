from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from app.contracts import (
    ActivateByTokenRequestDTO,
    ActivateRequestDTO,
    AuthTokenVO,
    LoginRequestDTO,
    RefreshTokenRequestDTO,
    SendVerificationCodeMessageVO,
    SendVerificationCodeRequestDTO,
    UserRegistrationRequestDTO,
    UserVO,
)
from app.extensions import db
from app.models import User
from app.services.user_service import (
    AuthError,
    activate_by_token,
    activate_user,
    login_user,
    logout_user,
    refresh_tokens,
    register_user,
    send_verification_code,
    serialize_user,
    verify_access_token,
    UserRegistrationError,
)

user_bp = Blueprint("user", __name__, url_prefix="/api/users")


def _validation_error_message(exc: ValidationError) -> str:
    """从 Pydantic ValidationError 取第一条错误信息。"""
    errors = exc.errors()
    if not errors:
        return "invalid request"
    first = errors[0]
    msg = first.get("msg", "invalid request")
    loc = first.get("loc", ())
    if len(loc) >= 1 and loc[0] != "__root__":
        return f"{loc[0]}: {msg}"
    return str(msg)


@user_bp.post("/register")
def register():
    payload = request.get_json(silent=True)
    if payload is None:
        payload = {}

    try:
        dto = UserRegistrationRequestDTO.model_validate(payload)
        user_data = register_user(dto.model_dump())
    except ValidationError as exc:
        return jsonify({"code": 40001, "msg": _validation_error_message(exc), "data": None}), 400
    except UserRegistrationError as exc:
        code_map = {
            "username_exists": 40901,
            "email_exists": 40902,
            "user_conflict": 40903,
        }
        return jsonify({"code": code_map.get(exc.error_code, 40000), "msg": exc.message, "data": None}), exc.status_code

    data = UserVO.model_validate(user_data).model_dump()
    return jsonify({"code": 0, "msg": "user registered", "data": data}), 201


@user_bp.post("/send-verification-code")
def send_code():
    """请求发送验证码：请求体 { "identifier": "用户名或邮箱" }。未激活用户每分钟最多请求一次；仅最新验证码有效。"""
    payload = request.get_json(silent=True) or {}
    try:
        dto = SendVerificationCodeRequestDTO.model_validate(payload)
        raw = send_verification_code(dto.identifier)
    except ValidationError as exc:
        return jsonify({"code": 40001, "msg": _validation_error_message(exc), "data": None}), 400
    except AuthError as exc:
        return jsonify({"code": 40101, "msg": exc.message, "data": None}), exc.status_code
    data = SendVerificationCodeMessageVO.model_validate(raw).model_dump()
    return jsonify({"code": 0, "msg": "verification code sent", "data": data}), 200


@user_bp.post("/activate")
def activate():
    """激活账户：请求体 { "identifier": "用户名或邮箱", "code": "6位验证码" }，验证码匹配则设为已激活。"""
    payload = request.get_json(silent=True) or {}
    try:
        dto = ActivateRequestDTO.model_validate(payload)
        user_data = activate_user(dto.identifier, dto.code)
    except ValidationError as exc:
        return jsonify({"code": 40001, "msg": _validation_error_message(exc), "data": None}), 400
    except AuthError as exc:
        return jsonify({"code": 40101, "msg": exc.message, "data": None}), exc.status_code
    data = UserVO.model_validate(user_data).model_dump()
    return jsonify({"code": 0, "msg": "account activated", "data": data}), 200


@user_bp.post("/activate-by-token")
def activate_by_token_route():
    """通过邮件中的激活链接 Token 激活账户：请求体 { "token": "..." }。"""
    payload = request.get_json(silent=True) or {}
    try:
        dto = ActivateByTokenRequestDTO.model_validate(payload)
        user_data = activate_by_token(dto.token)
    except ValidationError as exc:
        return jsonify({"code": 40001, "msg": _validation_error_message(exc), "data": None}), 400
    except AuthError as exc:
        return jsonify({"code": 40101, "msg": exc.message, "data": None}), exc.status_code
    data = UserVO.model_validate(user_data).model_dump()
    return jsonify({"code": 0, "msg": "account activated", "data": data}), 200


@user_bp.post("/login")
def login():
    """登录：请求体 { "identifier": "用户名或邮箱", "password": "密码" }，返回 access_token 与 refresh_token。"""
    payload = request.get_json(silent=True) or {}
    try:
        dto = LoginRequestDTO.model_validate(payload)
        raw = login_user(dto.identifier, dto.password)
    except ValidationError as exc:
        return jsonify({"code": 40001, "msg": _validation_error_message(exc), "data": None}), 400
    except AuthError as exc:
        return jsonify({"code": 40101, "msg": exc.message, "data": None}), exc.status_code
    data = AuthTokenVO.model_validate(raw).model_dump()
    return jsonify({"code": 0, "msg": "ok", "data": data}), 200


@user_bp.post("/refresh")
def refresh():
    """使用 refresh_token 换取新的 access_token 与 refresh_token。请求体 { "refresh_token": "..." }。"""
    payload = request.get_json(silent=True) or {}
    try:
        dto = RefreshTokenRequestDTO.model_validate(payload)
        raw = refresh_tokens(dto.refresh_token)
    except ValidationError as exc:
        return jsonify({"code": 40001, "msg": _validation_error_message(exc), "data": None}), 400
    except AuthError as exc:
        return jsonify({"code": 40101, "msg": exc.message, "data": None}), exc.status_code
    data = AuthTokenVO.model_validate(raw).model_dump()
    return jsonify({"code": 0, "msg": "ok", "data": data}), 200


@user_bp.post("/logout")
def logout():
    """登出：需要携带有效 access_token，服务端将当前用户 token_version 递增并使旧 token 失效。"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.strip().lower().startswith("bearer "):
        return jsonify({"code": 40101, "msg": "missing or invalid Authorization header", "data": None}), 401
    token = auth_header.strip()[7:].strip()
    try:
        logout_user(token)
    except AuthError as exc:
        return jsonify({"code": 40101, "msg": exc.message, "data": None}), exc.status_code
    return jsonify({"code": 0, "msg": "logged out", "data": None}), 200


@user_bp.get("/me")
def me():
    """需要携带有效 access_token：请求头 Authorization: Bearer <access_token>，返回当前用户信息。"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.strip().lower().startswith("bearer "):
        return jsonify({"code": 40101, "msg": "missing or invalid Authorization header", "data": None}), 401
    token = auth_header.strip()[7:].strip()
    try:
        payload = verify_access_token(token)
    except AuthError as exc:
        return jsonify({"code": 40101, "msg": exc.message, "data": None}), exc.status_code
    user_id = payload.get("sub")
    user = db.session.get(User, user_id)
    if user is None or not user.is_active:
        return jsonify({"code": 40101, "msg": "user not found or disabled", "data": None}), 401
    data = UserVO.model_validate(serialize_user(user)).model_dump()
    return jsonify({"code": 0, "msg": "ok", "data": data}), 200
