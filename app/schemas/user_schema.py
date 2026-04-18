import re
from typing import Any


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


class UserSchemaError(Exception):
    pass


def validate_user_registration(payload: Any) -> dict[str, str | None]:
    if not isinstance(payload, dict):
        raise UserSchemaError("Request body must be a JSON object.")

    username = str(payload.get("username", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    avatar_url = payload.get("avatar_url")

    if not username:
        raise UserSchemaError("username is required.")
    if len(username) < 3 or len(username) > 64:
        raise UserSchemaError("username length must be between 3 and 64.")
    if not USERNAME_PATTERN.match(username):
        raise UserSchemaError("username can only contain letters, numbers, '_', '-' and '.'.")

    if not email:
        raise UserSchemaError("email is required.")
    if len(email) > 120 or not EMAIL_PATTERN.match(email):
        raise UserSchemaError("email format is invalid.")

    if not password:
        raise UserSchemaError("password is required.")
    if len(password) < 8 or len(password) > 128:
        raise UserSchemaError("password length must be between 8 and 128.")

    normalized_avatar_url: str | None
    if avatar_url is None:
        normalized_avatar_url = None
    else:
        normalized_avatar_url = str(avatar_url).strip()
        if normalized_avatar_url and len(normalized_avatar_url) > 255:
            raise UserSchemaError("avatar_url length must be <= 255.")
        if not normalized_avatar_url:
            normalized_avatar_url = None

    return {
        "username": username,
        "email": email,
        "password": password,
        "avatar_url": normalized_avatar_url,
    }


def validate_login_request(payload: Any) -> dict[str, str]:
    """Validate login request body: identifier (username or email) + password."""
    if not isinstance(payload, dict):
        raise UserSchemaError("Request body must be a JSON object.")

    identifier = str(payload.get("identifier", "")).strip()
    password = str(payload.get("password", ""))

    if not identifier:
        raise UserSchemaError("identifier is required (username or email).")
    if len(identifier) > 120:
        raise UserSchemaError("identifier is too long.")

    if not password:
        raise UserSchemaError("password is required.")

    return {"identifier": identifier, "password": password}


def validate_refresh_request(payload: Any) -> dict[str, str]:
    """Validate refresh token request body: refresh_token."""
    if not isinstance(payload, dict):
        raise UserSchemaError("Request body must be a JSON object.")

    refresh_token = payload.get("refresh_token")
    if refresh_token is None:
        raise UserSchemaError("refresh_token is required.")
    if not isinstance(refresh_token, str) or not refresh_token.strip():
        raise UserSchemaError("refresh_token must be a non-empty string.")

    return {"refresh_token": refresh_token.strip()}


def validate_activate_request(payload: Any) -> dict[str, str]:
    """Validate activation request body: identifier (username or email) + code (6-digit verification code)."""
    if not isinstance(payload, dict):
        raise UserSchemaError("Request body must be a JSON object.")

    identifier = str(payload.get("identifier", "")).strip()
    code = payload.get("code")

    if not identifier:
        raise UserSchemaError("identifier is required (username or email).")
    if len(identifier) > 120:
        raise UserSchemaError("identifier is too long.")

    if code is None:
        raise UserSchemaError("code is required.")
    code_str = str(code).strip()
    if len(code_str) != 6 or not code_str.isdigit():
        raise UserSchemaError("code must be a 6-digit string.")

    return {"identifier": identifier, "code": code_str}


def validate_send_verification_code_request(payload: Any) -> dict[str, str]:
    """Validate send verification code request body: identifier (username or email)."""
    if not isinstance(payload, dict):
        raise UserSchemaError("Request body must be a JSON object.")

    identifier = str(payload.get("identifier", "")).strip()

    if not identifier:
        raise UserSchemaError("identifier is required (username or email).")
    if len(identifier) > 120:
        raise UserSchemaError("identifier is too long.")

    return {"identifier": identifier}


def validate_activate_by_token_request(payload: Any) -> dict[str, str]:
    """Validate token-based activation request body: token (from email link)."""
    if not isinstance(payload, dict):
        raise UserSchemaError("Request body must be a JSON object.")

    token = payload.get("token")
    if token is None:
        raise UserSchemaError("token is required.")
    token_str = str(token).strip()
    if not token_str:
        raise UserSchemaError("token must be a non-empty string.")

    return {"token": token_str}
