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
