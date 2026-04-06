"""
Unit tests for app.services.user_service.

All database interaction runs against the in-memory SQLite instance provided
by the `db` fixture.  Email sending is mocked so no SMTP connections are made.
"""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest
import jwt

import config
from app.services.user_service import (
    AuthError,
    UserRegistrationError,
    _as_utc_aware,
    _create_token,
    _decode_token,
    _extract_token_version,
    _extract_user_id,
    _generate_activation_token,
    _generate_verification_code,
    _now_utc,
    activate_by_token,
    activate_user,
    create_access_token,
    create_refresh_token,
    login_user,
    logout_user,
    refresh_tokens,
    register_user,
    send_verification_code,
    serialize_user,
    verify_access_token,
    verify_refresh_token,
)
from app.models import User


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


class TestGenerateVerificationCode:
    def test_returns_six_digit_string(self):
        code = _generate_verification_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_returns_string_type(self):
        assert isinstance(_generate_verification_code(), str)

    def test_different_codes_generated(self):
        codes = {_generate_verification_code() for _ in range(50)}
        # With 10^6 possibilities the chance of all 50 being identical is negligible
        assert len(codes) > 1


class TestGenerateActivationToken:
    def test_returns_non_empty_string(self):
        token = _generate_activation_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_tokens_are_unique(self):
        tokens = {_generate_activation_token() for _ in range(10)}
        assert len(tokens) == 10


class TestNowUtc:
    def test_returns_timezone_aware_datetime(self):
        now = _now_utc()
        assert now.tzinfo is not None

    def test_is_utc(self):
        now = _now_utc()
        assert now.utcoffset().total_seconds() == 0


class TestAsUtcAware:
    def test_none_returns_none(self):
        assert _as_utc_aware(None) is None

    def test_naive_datetime_gets_utc_tzinfo(self):
        naive = datetime(2024, 1, 1, 12, 0, 0)
        aware = _as_utc_aware(naive)
        assert aware.tzinfo is not None
        assert aware.utcoffset().total_seconds() == 0

    def test_aware_datetime_converted_to_utc(self):
        from datetime import timezone as tz
        aware = datetime(2024, 1, 1, 12, 0, 0, tzinfo=tz.utc)
        result = _as_utc_aware(aware)
        assert result.utcoffset().total_seconds() == 0


# ---------------------------------------------------------------------------
# Token creation / decoding
# ---------------------------------------------------------------------------


class TestCreateToken:
    def test_creates_valid_jwt(self):
        token = _create_token(
            user_id=1,
            token_version=0,
            secret="secret",
            expires_seconds=300,
            token_type="access",
        )
        payload = jwt.decode(token, "secret", algorithms=["HS256"])
        assert payload["sub"] == "1"
        assert payload["type"] == "access"

    def test_token_contains_version(self):
        token = _create_token(1, 5, "secret", 300, "access")
        payload = jwt.decode(token, "secret", algorithms=["HS256"])
        assert payload["ver"] == 5


class TestDecodeToken:
    def _make_expired_token(self, secret="secret"):
        payload = {
            "sub": "1",
            "ver": 0,
            "type": "access",
            "iat": int(time.time()) - 600,
            "exp": int(time.time()) - 300,
        }
        return jwt.encode(payload, secret, algorithm="HS256")

    def test_valid_token_decoded_successfully(self):
        token = _create_token(1, 0, "secret", 300, "access")
        payload = _decode_token(token, "secret", "expired", "invalid")
        assert payload["sub"] == "1"

    def test_expired_token_raises_auth_error(self):
        token = self._make_expired_token()
        with pytest.raises(AuthError) as exc_info:
            _decode_token(token, "secret", "expired", "invalid")
        assert exc_info.value.message == "expired"

    def test_invalid_token_raises_auth_error(self):
        with pytest.raises(AuthError) as exc_info:
            _decode_token("not.a.token", "secret", "expired", "invalid")
        assert exc_info.value.message == "invalid"

    def test_wrong_secret_raises_auth_error(self):
        token = _create_token(1, 0, "correct-secret", 300, "access")
        with pytest.raises(AuthError):
            _decode_token(token, "wrong-secret", "expired", "invalid")


class TestExtractUserId:
    def test_valid_sub_returned_as_int(self):
        assert _extract_user_id({"sub": "42"}) == 42

    def test_missing_sub_raises_auth_error(self):
        with pytest.raises(AuthError):
            _extract_user_id({})

    def test_non_numeric_sub_raises_auth_error(self):
        with pytest.raises(AuthError):
            _extract_user_id({"sub": "abc"})


class TestExtractTokenVersion:
    def test_valid_version_returned(self):
        assert _extract_token_version({"ver": "3"}) == 3

    def test_zero_version_accepted(self):
        assert _extract_token_version({"ver": 0}) == 0

    def test_missing_ver_defaults_to_zero(self):
        assert _extract_token_version({}) == 0

    def test_negative_version_raises_auth_error(self):
        with pytest.raises(AuthError):
            _extract_token_version({"ver": -1})

    def test_non_numeric_ver_raises_auth_error(self):
        with pytest.raises(AuthError):
            _extract_token_version({"ver": "abc"})


# ---------------------------------------------------------------------------
# Public token API
# ---------------------------------------------------------------------------


class TestCreateAccessToken:
    def test_creates_decodable_access_token(self):
        token = create_access_token(user_id=1, token_version=0)
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=["HS256"])
        assert payload["type"] == "access"

    def test_expiry_matches_config(self):
        before = int(time.time())
        token = create_access_token(user_id=1, token_version=0)
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=["HS256"])
        assert payload["exp"] >= before + config.JWT_ACCESS_EXPIRES_SECONDS - 2


class TestCreateRefreshToken:
    def test_creates_decodable_refresh_token(self):
        token = create_refresh_token(user_id=1, token_version=0)
        payload = jwt.decode(token, config.JWT_REFRESH_SECRET_KEY, algorithms=["HS256"])
        assert payload["type"] == "refresh"


# ---------------------------------------------------------------------------
# register_user
# ---------------------------------------------------------------------------


PATCH_EMAIL = "app.services.user_service.send_verification_code_email_async"


class TestRegisterUser:
    def test_successful_registration(self, app, db):
        with app.app_context():
            with patch(PATCH_EMAIL):
                result = register_user(
                    {
                        "username": "newuser",
                        "email": "new@example.com",
                        "password": "password123",
                        "avatar_url": None,
                    }
                )
        assert result["username"] == "newuser"
        assert result["email"] == "new@example.com"
        assert result["is_active"] is False

    def test_duplicate_username_raises(self, app, db, make_user):
        with app.app_context():
            make_user(username="taken", email="unique@example.com")
            with patch(PATCH_EMAIL):
                with pytest.raises(UserRegistrationError) as exc_info:
                    register_user(
                        {
                            "username": "taken",
                            "email": "other@example.com",
                            "password": "password123",
                            "avatar_url": None,
                        }
                    )
            assert exc_info.value.error_code == "username_exists"

    def test_duplicate_email_raises(self, app, db, make_user):
        with app.app_context():
            make_user(username="user1", email="shared@example.com")
            with patch(PATCH_EMAIL):
                with pytest.raises(UserRegistrationError) as exc_info:
                    register_user(
                        {
                            "username": "user2",
                            "email": "shared@example.com",
                            "password": "password123",
                            "avatar_url": None,
                        }
                    )
            assert exc_info.value.error_code == "email_exists"

    def test_email_async_function_called(self, app, db):
        with app.app_context():
            with patch(PATCH_EMAIL) as mock_send:
                register_user(
                    {
                        "username": "emailtest",
                        "email": "emailtest@example.com",
                        "password": "password123",
                        "avatar_url": None,
                    }
                )
            mock_send.assert_called_once()


# ---------------------------------------------------------------------------
# send_verification_code
# ---------------------------------------------------------------------------


class TestSendVerificationCode:
    def test_sends_code_to_inactive_user(self, app, db, make_user):
        with app.app_context():
            make_user(
                username="inactive",
                email="inactive@example.com",
                is_active=False,
                email_verification_code_sent_at=datetime.now(timezone.utc)
                - timedelta(seconds=120),
            )
            with patch(PATCH_EMAIL):
                result = send_verification_code("inactive")
        assert result == {"message": "verification code sent"}

    def test_user_not_found_raises(self, app, db):
        with app.app_context():
            with pytest.raises(AuthError) as exc_info:
                send_verification_code("ghost")
        assert exc_info.value.status_code == 404

    def test_already_active_user_raises(self, app, db, make_user):
        with app.app_context():
            make_user(username="active", email="active@example.com", is_active=True)
            with pytest.raises(AuthError) as exc_info:
                send_verification_code("active")
        assert exc_info.value.status_code == 400

    def test_cooldown_enforced(self, app, db, make_user):
        """Requesting a code too soon should return 429."""
        with app.app_context():
            make_user(
                username="cooldown_user",
                email="cooldown@example.com",
                is_active=False,
                email_verification_code_sent_at=datetime.now(timezone.utc)
                - timedelta(seconds=10),  # sent 10s ago, cooldown is 60s
            )
            with pytest.raises(AuthError) as exc_info:
                send_verification_code("cooldown_user")
        assert exc_info.value.status_code == 429


# ---------------------------------------------------------------------------
# activate_user
# ---------------------------------------------------------------------------


class TestActivateUser:
    def test_valid_code_activates_user(self, app, db, make_user):
        with app.app_context():
            make_user(
                username="inactiveact",
                email="inactiveact@example.com",
                is_active=False,
                email_verification_code="654321",
                email_verification_code_expires_at=datetime.now(timezone.utc)
                + timedelta(minutes=5),
            )
            result = activate_user("inactiveact", "654321")
        assert result["is_active"] is True

    def test_user_not_found_raises(self, app, db):
        with app.app_context():
            with pytest.raises(AuthError) as exc_info:
                activate_user("ghost", "123456")
        assert exc_info.value.status_code == 404

    def test_already_active_raises(self, app, db, make_user):
        with app.app_context():
            make_user(username="alreadyact", email="alreadyact@example.com", is_active=True)
            with pytest.raises(AuthError) as exc_info:
                activate_user("alreadyact", "123456")
        assert exc_info.value.status_code == 400

    def test_wrong_code_raises(self, app, db, make_user):
        with app.app_context():
            make_user(
                username="wrongcode",
                email="wrongcode@example.com",
                is_active=False,
                email_verification_code="111111",
                email_verification_code_expires_at=datetime.now(timezone.utc)
                + timedelta(minutes=5),
            )
            with pytest.raises(AuthError) as exc_info:
                activate_user("wrongcode", "999999")
        assert exc_info.value.status_code == 400

    def test_expired_code_raises(self, app, db, make_user):
        with app.app_context():
            make_user(
                username="expiredcode",
                email="expiredcode@example.com",
                is_active=False,
                email_verification_code="123456",
                email_verification_code_expires_at=datetime.now(timezone.utc)
                - timedelta(minutes=1),
            )
            with pytest.raises(AuthError) as exc_info:
                activate_user("expiredcode", "123456")
        assert exc_info.value.status_code == 400

    def test_no_pending_code_raises(self, app, db, make_user):
        with app.app_context():
            make_user(
                username="nocode",
                email="nocode@example.com",
                is_active=False,
                email_verification_code=None,
            )
            with pytest.raises(AuthError) as exc_info:
                activate_user("nocode", "123456")
        assert exc_info.value.status_code == 400

    def test_code_cleared_after_activation(self, app, db, make_user):
        """Verification code fields should be nulled out after successful activation."""
        with app.app_context():
            user = make_user(
                username="cleartest",
                email="cleartest@example.com",
                is_active=False,
                email_verification_code="777777",
                email_verification_code_expires_at=datetime.now(timezone.utc)
                + timedelta(minutes=5),
            )
            activate_user("cleartest", "777777")
            db.session.refresh(user)
            assert user.email_verification_code is None
            assert user.activation_token is None


# ---------------------------------------------------------------------------
# activate_by_token
# ---------------------------------------------------------------------------


class TestActivateByToken:
    def test_valid_token_activates_user(self, app, db, make_user):
        with app.app_context():
            make_user(
                username="tokenact",
                email="tokenact@example.com",
                is_active=False,
                activation_token="valid-token-abc",
                email_verification_code_expires_at=datetime.now(timezone.utc)
                + timedelta(minutes=5),
            )
            result = activate_by_token("valid-token-abc")
        assert result["is_active"] is True

    def test_invalid_token_raises(self, app, db):
        with app.app_context():
            with pytest.raises(AuthError) as exc_info:
                activate_by_token("no-such-token")
        assert exc_info.value.status_code == 400

    def test_already_active_raises(self, app, db, make_user):
        with app.app_context():
            make_user(
                username="activetok",
                email="activetok@example.com",
                is_active=True,
                activation_token="already-active-token",
            )
            with pytest.raises(AuthError):
                activate_by_token("already-active-token")

    def test_expired_link_raises(self, app, db, make_user):
        with app.app_context():
            make_user(
                username="expiredtok",
                email="expiredtok@example.com",
                is_active=False,
                activation_token="expired-token-xyz",
                email_verification_code_expires_at=datetime.now(timezone.utc)
                - timedelta(minutes=1),
            )
            with pytest.raises(AuthError) as exc_info:
                activate_by_token("expired-token-xyz")
        assert "expired" in exc_info.value.message


# ---------------------------------------------------------------------------
# login_user
# ---------------------------------------------------------------------------


class TestLoginUser:
    def test_successful_login_returns_tokens(self, app, db, make_user):
        with app.app_context():
            make_user(username="loginuser", email="login@example.com", is_active=True)
            result = login_user("loginuser", "password123")
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "Bearer"

    def test_login_with_email_works(self, app, db, make_user):
        with app.app_context():
            make_user(username="emaillogin", email="emaillogin@example.com", is_active=True)
            result = login_user("emaillogin@example.com", "password123")
        assert "access_token" in result

    def test_wrong_password_raises(self, app, db, make_user):
        with app.app_context():
            make_user(username="wrongpwd", email="wrongpwd@example.com", is_active=True)
            with pytest.raises(AuthError) as exc_info:
                login_user("wrongpwd", "wrong-password")
        assert exc_info.value.status_code == 401

    def test_inactive_user_raises(self, app, db, make_user):
        with app.app_context():
            make_user(username="inactlogin", email="inactlogin@example.com", is_active=False)
            with pytest.raises(AuthError) as exc_info:
                login_user("inactlogin", "password123")
        assert exc_info.value.status_code == 403

    def test_unknown_identifier_raises(self, app, db):
        with app.app_context():
            with pytest.raises(AuthError) as exc_info:
                login_user("nobody", "password")
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# verify_access_token
# ---------------------------------------------------------------------------


class TestVerifyAccessToken:
    def test_valid_token_returns_payload(self, app, db, make_user):
        with app.app_context():
            user = make_user(username="verifyuser", email="verify@example.com")
            token = create_access_token(user.id, user.token_version)
            payload = verify_access_token(token)
        assert payload["sub"] == user.id

    def test_revoked_token_raises(self, app, db, make_user):
        with app.app_context():
            user = make_user(username="revokeduser", email="revoked@example.com")
            token = create_access_token(user.id, token_version=0)
            # Bump version to revoke old tokens
            user.token_version = 1
            db.session.commit()
            with pytest.raises(AuthError) as exc_info:
                verify_access_token(token)
        assert "revoked" in exc_info.value.message

    def test_refresh_token_rejected_as_access(self, app, db, make_user):
        """A refresh token must be rejected when used as an access token.
        Because the refresh token is signed with a different secret key it will
        fail signature verification (raising 'invalid access token') before the
        type-claim check is ever reached.
        """
        with app.app_context():
            user = make_user(username="wrongtype", email="wrongtype@example.com")
            refresh_tok = create_refresh_token(user.id, user.token_version)
            with pytest.raises(AuthError) as exc_info:
                verify_access_token(refresh_tok)
        # Either the signature check or the type check rejects the token –
        # either way an AuthError is raised.
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# refresh_tokens
# ---------------------------------------------------------------------------


class TestRefreshTokens:
    def test_valid_refresh_token_returns_new_tokens(self, app, db, make_user):
        with app.app_context():
            user = make_user(username="refreshuser", email="refresh@example.com")
            refresh_tok = create_refresh_token(user.id, user.token_version)
            result = refresh_tokens(refresh_tok)
        assert "access_token" in result
        assert "refresh_token" in result

    def test_revoked_refresh_token_raises(self, app, db, make_user):
        with app.app_context():
            user = make_user(username="refreshrev", email="refreshrev@example.com")
            refresh_tok = create_refresh_token(user.id, token_version=0)
            user.token_version = 1
            db.session.commit()
            with pytest.raises(AuthError) as exc_info:
                refresh_tokens(refresh_tok)
        assert "revoked" in exc_info.value.message

    def test_access_token_rejected_as_refresh(self, app, db, make_user):
        with app.app_context():
            user = make_user(username="refreshwrong", email="refreshwrong@example.com")
            access_tok = create_access_token(user.id, user.token_version)
            with pytest.raises(AuthError):
                refresh_tokens(access_tok)


# ---------------------------------------------------------------------------
# logout_user
# ---------------------------------------------------------------------------


class TestLogoutUser:
    def test_logout_increments_token_version(self, app, db, make_user):
        with app.app_context():
            user = make_user(username="logoutuser", email="logout@example.com")
            token = create_access_token(user.id, user.token_version)
            logout_user(token)
            db.session.refresh(user)
            assert user.token_version == 1

    def test_old_token_rejected_after_logout(self, app, db, make_user):
        with app.app_context():
            user = make_user(username="loggedout", email="loggedout@example.com")
            token = create_access_token(user.id, user.token_version)
            logout_user(token)
            with pytest.raises(AuthError):
                verify_access_token(token)


# ---------------------------------------------------------------------------
# serialize_user
# ---------------------------------------------------------------------------


class TestSerializeUser:
    def test_returns_expected_keys(self, app, db, make_user):
        with app.app_context():
            user = make_user(username="serial", email="serial@example.com")
            result = serialize_user(user)
        assert set(result.keys()) == {
            "id",
            "username",
            "email",
            "avatar_url",
            "is_active",
            "created_at",
        }

    def test_created_at_is_iso_string_or_none(self, app, db, make_user):
        with app.app_context():
            user = make_user(username="serial2", email="serial2@example.com")
            result = serialize_user(user)
        # created_at may be None if the DB doesn't populate it (SQLite)
        if result["created_at"] is not None:
            datetime.fromisoformat(result["created_at"])  # should not raise
