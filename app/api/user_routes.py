from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import User
from app.schemas.user_schema import (
    UserSchemaError,
    validate_login_request,
    validate_refresh_request,
    validate_user_registration,
)
from app.services.user_service import (
    AuthError,
    login_user,
    refresh_tokens,
    register_user,
    serialize_user,
    verify_access_token,
    UserRegistrationError,
)

user_bp = Blueprint("user", __name__, url_prefix="/api/users")


@user_bp.post("/register")
def register():
    payload = request.get_json(silent=True)

    try:
        validated_payload = validate_user_registration(payload)
        user_data = register_user(validated_payload)
    except UserSchemaError as exc:
        return jsonify({"code": 40001, "msg": str(exc), "data": None}), 400
    except UserRegistrationError as exc:
        code_map = {
            "username_exists": 40901,
            "email_exists": 40902,
            "user_conflict": 40903,
        }
        return jsonify({"code": code_map.get(exc.error_code, 40000), "msg": exc.message, "data": None}), exc.status_code

    return jsonify({"code": 0, "msg": "user registered", "data": user_data}), 201


@user_bp.post("/login")
def login():
    """登录：请求体 { "identifier": "用户名或邮箱", "password": "密码" }，返回 access_token 与 refresh_token。"""
    payload = request.get_json(silent=True)
    try:
        validated = validate_login_request(payload)
        data = login_user(validated["identifier"], validated["password"])
    except UserSchemaError as exc:
        return jsonify({"code": 40001, "msg": str(exc), "data": None}), 400
    except AuthError as exc:
        return jsonify({"code": 40101, "msg": exc.message, "data": None}), exc.status_code
    return jsonify({"code": 0, "msg": "ok", "data": data}), 200


@user_bp.post("/refresh")
def refresh():
    """使用 refresh_token 换取新的 access_token 与 refresh_token。请求体 { "refresh_token": "..." }。"""
    payload = request.get_json(silent=True)
    try:
        validated = validate_refresh_request(payload)
        data = refresh_tokens(validated["refresh_token"])
    except UserSchemaError as exc:
        return jsonify({"code": 40001, "msg": str(exc), "data": None}), 400
    except AuthError as exc:
        return jsonify({"code": 40101, "msg": exc.message, "data": None}), exc.status_code
    return jsonify({"code": 0, "msg": "ok", "data": data}), 200


@user_bp.post("/logout")
def logout():
    """登出：需要携带有效 access_token（Authorization: Bearer <access_token>），服务端确认后返回成功。"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.strip().lower().startswith("bearer "):
        return jsonify({"code": 40101, "msg": "missing or invalid Authorization header", "data": None}), 401
    token = auth_header.strip()[7:].strip()
    try:
        verify_access_token(token)
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
    return jsonify({"code": 0, "msg": "ok", "data": serialize_user(user)}), 200
