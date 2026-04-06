"""
Unit tests for app/schemas/user_schema.py.

These are legacy validation helpers separate from the Pydantic DTOs.
"""

import pytest

from app.schemas.user_schema import (
    UserSchemaError,
    validate_activate_by_token_request,
    validate_activate_request,
    validate_login_request,
    validate_refresh_request,
    validate_send_verification_code_request,
    validate_user_registration,
)


# ---------------------------------------------------------------------------
# validate_user_registration
# ---------------------------------------------------------------------------


class TestValidateUserRegistration:
    VALID = {
        "username": "alice",
        "email": "alice@example.com",
        "password": "password123",
    }

    def test_valid_payload_returns_dict(self):
        result = validate_user_registration(self.VALID)
        assert result["username"] == "alice"
        assert result["email"] == "alice@example.com"

    def test_non_dict_raises(self):
        with pytest.raises(UserSchemaError, match="JSON object"):
            validate_user_registration("not a dict")

    def test_list_raises(self):
        with pytest.raises(UserSchemaError):
            validate_user_registration(["a", "b"])

    def test_missing_username_raises(self):
        with pytest.raises(UserSchemaError, match="username is required"):
            validate_user_registration({"email": "a@b.com", "password": "password123"})

    def test_username_too_short_raises(self):
        with pytest.raises(UserSchemaError, match="length"):
            validate_user_registration({**self.VALID, "username": "ab"})

    def test_username_too_long_raises(self):
        with pytest.raises(UserSchemaError, match="length"):
            validate_user_registration({**self.VALID, "username": "a" * 65})

    def test_username_invalid_chars_raises(self):
        with pytest.raises(UserSchemaError, match="letters"):
            validate_user_registration({**self.VALID, "username": "alice!"})

    def test_missing_email_raises(self):
        with pytest.raises(UserSchemaError, match="email is required"):
            validate_user_registration(
                {"username": "alice", "password": "password123"}
            )

    def test_invalid_email_raises(self):
        with pytest.raises(UserSchemaError, match="email format"):
            validate_user_registration({**self.VALID, "email": "bad-email"})

    def test_email_too_long_raises(self):
        with pytest.raises(UserSchemaError, match="email format"):
            validate_user_registration(
                {**self.VALID, "email": "a" * 121 + "@b.com"}
            )

    def test_missing_password_raises(self):
        with pytest.raises(UserSchemaError, match="password is required"):
            validate_user_registration(
                {"username": "alice", "email": "a@b.com"}
            )

    def test_password_too_short_raises(self):
        with pytest.raises(UserSchemaError, match="length"):
            validate_user_registration({**self.VALID, "password": "short"})

    def test_password_too_long_raises(self):
        with pytest.raises(UserSchemaError, match="length"):
            validate_user_registration({**self.VALID, "password": "x" * 129})

    def test_avatar_url_none_by_default(self):
        result = validate_user_registration(self.VALID)
        assert result["avatar_url"] is None

    def test_avatar_url_stored(self):
        result = validate_user_registration(
            {**self.VALID, "avatar_url": "http://example.com/img.png"}
        )
        assert result["avatar_url"] == "http://example.com/img.png"

    def test_avatar_url_too_long_raises(self):
        with pytest.raises(UserSchemaError, match="avatar_url"):
            validate_user_registration({**self.VALID, "avatar_url": "x" * 256})

    def test_blank_avatar_url_becomes_none(self):
        result = validate_user_registration({**self.VALID, "avatar_url": "   "})
        assert result["avatar_url"] is None

    def test_email_lowercased(self):
        result = validate_user_registration({**self.VALID, "email": "ALICE@EXAMPLE.COM"})
        assert result["email"] == "alice@example.com"

    def test_username_stripped(self):
        result = validate_user_registration({**self.VALID, "username": "  alice  "})
        assert result["username"] == "alice"


# ---------------------------------------------------------------------------
# validate_login_request
# ---------------------------------------------------------------------------


class TestValidateLoginRequest:
    def test_valid_payload(self):
        result = validate_login_request({"identifier": "alice", "password": "pw"})
        assert result["identifier"] == "alice"

    def test_non_dict_raises(self):
        with pytest.raises(UserSchemaError):
            validate_login_request("string")

    def test_empty_identifier_raises(self):
        with pytest.raises(UserSchemaError, match="identifier is required"):
            validate_login_request({"identifier": "", "password": "pw"})

    def test_identifier_too_long_raises(self):
        with pytest.raises(UserSchemaError, match="too long"):
            validate_login_request({"identifier": "a" * 121, "password": "pw"})

    def test_empty_password_raises(self):
        with pytest.raises(UserSchemaError, match="password is required"):
            validate_login_request({"identifier": "alice", "password": ""})

    def test_identifier_stripped(self):
        result = validate_login_request({"identifier": "  alice  ", "password": "pw"})
        assert result["identifier"] == "alice"


# ---------------------------------------------------------------------------
# validate_refresh_request
# ---------------------------------------------------------------------------


class TestValidateRefreshRequest:
    def test_valid_payload(self):
        result = validate_refresh_request({"refresh_token": "some.jwt"})
        assert result["refresh_token"] == "some.jwt"

    def test_non_dict_raises(self):
        with pytest.raises(UserSchemaError):
            validate_refresh_request(None)

    def test_missing_token_raises(self):
        with pytest.raises(UserSchemaError, match="required"):
            validate_refresh_request({})

    def test_empty_string_token_raises(self):
        with pytest.raises(UserSchemaError, match="non-empty"):
            validate_refresh_request({"refresh_token": "   "})

    def test_non_string_token_raises(self):
        with pytest.raises(UserSchemaError, match="non-empty"):
            validate_refresh_request({"refresh_token": 123})

    def test_token_stripped(self):
        result = validate_refresh_request({"refresh_token": "  token  "})
        assert result["refresh_token"] == "token"


# ---------------------------------------------------------------------------
# validate_activate_request
# ---------------------------------------------------------------------------


class TestValidateActivateRequest:
    def test_valid_payload(self):
        result = validate_activate_request(
            {"identifier": "alice", "code": "123456"}
        )
        assert result["code"] == "123456"

    def test_non_dict_raises(self):
        with pytest.raises(UserSchemaError):
            validate_activate_request([])

    def test_missing_identifier_raises(self):
        with pytest.raises(UserSchemaError, match="identifier is required"):
            validate_activate_request({"code": "123456"})

    def test_identifier_too_long_raises(self):
        with pytest.raises(UserSchemaError, match="too long"):
            validate_activate_request({"identifier": "a" * 121, "code": "123456"})

    def test_missing_code_raises(self):
        with pytest.raises(UserSchemaError, match="code is required"):
            validate_activate_request({"identifier": "alice"})

    def test_non_six_digit_code_raises(self):
        with pytest.raises(UserSchemaError, match="6-digit"):
            validate_activate_request({"identifier": "alice", "code": "12345"})

    def test_non_numeric_code_raises(self):
        with pytest.raises(UserSchemaError, match="6-digit"):
            validate_activate_request({"identifier": "alice", "code": "12345a"})

    def test_integer_code_accepted(self):
        result = validate_activate_request({"identifier": "alice", "code": 123456})
        assert result["code"] == "123456"


# ---------------------------------------------------------------------------
# validate_send_verification_code_request
# ---------------------------------------------------------------------------


class TestValidateSendVerificationCodeRequest:
    def test_valid_payload(self):
        result = validate_send_verification_code_request({"identifier": "alice"})
        assert result["identifier"] == "alice"

    def test_non_dict_raises(self):
        with pytest.raises(UserSchemaError):
            validate_send_verification_code_request("not a dict")

    def test_empty_identifier_raises(self):
        with pytest.raises(UserSchemaError, match="identifier is required"):
            validate_send_verification_code_request({"identifier": ""})

    def test_too_long_identifier_raises(self):
        with pytest.raises(UserSchemaError, match="too long"):
            validate_send_verification_code_request({"identifier": "a" * 121})

    def test_identifier_stripped(self):
        result = validate_send_verification_code_request(
            {"identifier": "  alice@example.com  "}
        )
        assert result["identifier"] == "alice@example.com"


# ---------------------------------------------------------------------------
# validate_activate_by_token_request
# ---------------------------------------------------------------------------


class TestValidateActivateByTokenRequest:
    def test_valid_payload(self):
        result = validate_activate_by_token_request({"token": "abc123"})
        assert result["token"] == "abc123"

    def test_non_dict_raises(self):
        with pytest.raises(UserSchemaError):
            validate_activate_by_token_request(42)

    def test_missing_token_raises(self):
        with pytest.raises(UserSchemaError, match="required"):
            validate_activate_by_token_request({})

    def test_empty_string_token_raises(self):
        with pytest.raises(UserSchemaError, match="non-empty"):
            validate_activate_by_token_request({"token": "  "})

    def test_token_stripped(self):
        result = validate_activate_by_token_request({"token": "  mytoken  "})
        assert result["token"] == "mytoken"
