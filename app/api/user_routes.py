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
    """Extract the first error message from Pydantic ValidationError."""
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
    """Request sending verification code: request body { "identifier": "username or email" }. Unactivated users can request at most once per minute; only the latest verification code is valid."""
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
    """Activate account: request body { "identifier": "username or email", "code": "6-digit verification code" }, matching verification code sets the account as activated."""
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
    """Activate account via activation link token in email: request body { "token": "..." }."""
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
    """Login: request body { "identifier": "username or email", "password": "password" }, returns access_token and refresh_token."""
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
    """Use refresh_token to exchange for new access_token and refresh_token. Request body { "refresh_token": "..." }."""
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
    """Logout: requires a valid access_token, the server will increment the current user's token_version and invalidate the old token."""
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
    """Requires a valid access_token: request header Authorization: Bearer <access_token>, returns current user information."""
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
