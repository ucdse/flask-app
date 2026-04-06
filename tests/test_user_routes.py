"""
Integration tests for the /api/users blueprint.

All service layer calls that touch external dependencies (email, JWT with real
DB) are verified end-to-end through the Flask test client.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.services.user_service import create_access_token, create_refresh_token

PATCH_EMAIL = "app.services.user_service.send_verification_code_email_async"


# ---------------------------------------------------------------------------
# POST /api/users/register
# ---------------------------------------------------------------------------


class TestRegisterEndpoint:
    def test_successful_registration_returns_201(self, client, db):
        with patch(PATCH_EMAIL):
            resp = client.post(
                "/api/users/register",
                json={
                    "username": "newuser",
                    "email": "new@example.com",
                    "password": "password123",
                },
            )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["code"] == 0
        assert body["data"]["username"] == "newuser"
        assert body["data"]["is_active"] is False

    def test_missing_body_returns_400(self, client, db):
        resp = client.post("/api/users/register")
        assert resp.status_code == 400
        assert resp.get_json()["code"] == 40001

    def test_missing_username_returns_400(self, client, db):
        resp = client.post(
            "/api/users/register",
            json={"email": "x@example.com", "password": "password123"},
        )
        assert resp.status_code == 400

    def test_short_password_returns_400(self, client, db):
        resp = client.post(
            "/api/users/register",
            json={
                "username": "validuser",
                "email": "valid@example.com",
                "password": "short",
            },
        )
        assert resp.status_code == 400

    def test_invalid_email_returns_400(self, client, db):
        resp = client.post(
            "/api/users/register",
            json={
                "username": "testuser",
                "email": "not-an-email",
                "password": "password123",
            },
        )
        assert resp.status_code == 400

    def test_duplicate_username_returns_409(self, client, db, make_user):
        make_user(username="taken", email="unique@example.com")
        with patch(PATCH_EMAIL):
            resp = client.post(
                "/api/users/register",
                json={
                    "username": "taken",
                    "email": "other@example.com",
                    "password": "password123",
                },
            )
        assert resp.status_code == 409
        assert resp.get_json()["code"] == 40901

    def test_duplicate_email_returns_409(self, client, db, make_user):
        make_user(username="uniqueuser", email="shared@example.com")
        with patch(PATCH_EMAIL):
            resp = client.post(
                "/api/users/register",
                json={
                    "username": "otheruser",
                    "email": "shared@example.com",
                    "password": "password123",
                },
            )
        assert resp.status_code == 409
        assert resp.get_json()["code"] == 40902

    def test_non_json_body_treated_as_empty_dict_returns_400(self, client, db):
        resp = client.post(
            "/api/users/register",
            data="not json",
            content_type="text/plain",
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/users/send-verification-code
# ---------------------------------------------------------------------------


class TestSendVerificationCodeEndpoint:
    def test_sends_code_for_inactive_user(self, client, db, make_user):
        make_user(
            username="sendcode",
            email="sendcode@example.com",
            is_active=False,
            email_verification_code_sent_at=datetime.now(timezone.utc)
            - timedelta(seconds=120),
        )
        with patch(PATCH_EMAIL):
            resp = client.post(
                "/api/users/send-verification-code",
                json={"identifier": "sendcode"},
            )
        assert resp.status_code == 200
        assert resp.get_json()["code"] == 0

    def test_unknown_user_returns_4xx(self, client, db):
        resp = client.post(
            "/api/users/send-verification-code",
            json={"identifier": "nobody"},
        )
        assert resp.status_code in (400, 401, 404)

    def test_missing_identifier_returns_400(self, client, db):
        resp = client.post(
            "/api/users/send-verification-code", json={}
        )
        assert resp.status_code == 400

    def test_already_active_user_returns_4xx(self, client, db, make_user):
        make_user(
            username="activeuser", email="activeuser@example.com", is_active=True
        )
        resp = client.post(
            "/api/users/send-verification-code",
            json={"identifier": "activeuser"},
        )
        assert resp.status_code in (400, 401)


# ---------------------------------------------------------------------------
# POST /api/users/activate
# ---------------------------------------------------------------------------


class TestActivateEndpoint:
    def test_valid_code_activates_and_returns_200(self, client, db, make_user):
        make_user(
            username="toactivate",
            email="toactivate@example.com",
            is_active=False,
            email_verification_code="111222",
            email_verification_code_expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=5),
        )
        resp = client.post(
            "/api/users/activate",
            json={"identifier": "toactivate", "code": "111222"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["is_active"] is True

    def test_wrong_code_returns_4xx(self, client, db, make_user):
        make_user(
            username="wrongcodeact",
            email="wrongcodeact@example.com",
            is_active=False,
            email_verification_code="999888",
            email_verification_code_expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=5),
        )
        resp = client.post(
            "/api/users/activate",
            json={"identifier": "wrongcodeact", "code": "000000"},
        )
        assert resp.status_code in (400, 401)

    def test_invalid_code_format_returns_400(self, client, db):
        resp = client.post(
            "/api/users/activate",
            json={"identifier": "someone", "code": "abc"},
        )
        assert resp.status_code == 400

    def test_missing_code_returns_400(self, client, db):
        resp = client.post(
            "/api/users/activate",
            json={"identifier": "someone"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/users/activate-by-token
# ---------------------------------------------------------------------------


class TestActivateByTokenEndpoint:
    def test_valid_token_activates_returns_200(self, client, db, make_user):
        make_user(
            username="tokenuser",
            email="tokenuser@example.com",
            is_active=False,
            activation_token="valid-activation-token",
            email_verification_code_expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=5),
        )
        resp = client.post(
            "/api/users/activate-by-token",
            json={"token": "valid-activation-token"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["is_active"] is True

    def test_invalid_token_returns_4xx(self, client, db):
        resp = client.post(
            "/api/users/activate-by-token",
            json={"token": "no-such-token"},
        )
        assert resp.status_code in (400, 401)

    def test_missing_token_returns_400(self, client, db):
        resp = client.post(
            "/api/users/activate-by-token",
            json={},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/users/login
# ---------------------------------------------------------------------------


class TestLoginEndpoint:
    def test_valid_credentials_return_200_with_tokens(self, client, db, make_user):
        make_user(username="logintest", email="logintest@example.com", is_active=True)
        resp = client.post(
            "/api/users/login",
            json={"identifier": "logintest", "password": "password123"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["code"] == 0
        assert "access_token" in body["data"]
        assert "refresh_token" in body["data"]

    def test_wrong_password_returns_401(self, client, db, make_user):
        make_user(username="badpass", email="badpass@example.com", is_active=True)
        resp = client.post(
            "/api/users/login",
            json={"identifier": "badpass", "password": "wrong"},
        )
        assert resp.status_code == 401

    def test_missing_credentials_returns_400(self, client, db):
        resp = client.post("/api/users/login", json={})
        assert resp.status_code == 400

    def test_inactive_user_returns_403(self, client, db, make_user):
        make_user(
            username="inactivelogin",
            email="inactivelogin@example.com",
            is_active=False,
        )
        resp = client.post(
            "/api/users/login",
            json={"identifier": "inactivelogin", "password": "password123"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/users/refresh
# ---------------------------------------------------------------------------


class TestRefreshEndpoint:
    def test_valid_refresh_token_returns_new_tokens(self, client, app, db, make_user):
        with app.app_context():
            user = make_user(username="refreshme", email="refreshme@example.com")
            refresh_tok = create_refresh_token(user.id, user.token_version)
        resp = client.post(
            "/api/users/refresh",
            json={"refresh_token": refresh_tok},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert "access_token" in body["data"]

    def test_invalid_refresh_token_returns_401(self, client, db):
        resp = client.post(
            "/api/users/refresh",
            json={"refresh_token": "not.a.valid.token"},
        )
        assert resp.status_code == 401

    def test_missing_refresh_token_returns_400(self, client, db):
        resp = client.post("/api/users/refresh", json={})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/users/logout
# ---------------------------------------------------------------------------


class TestLogoutEndpoint:
    def test_valid_token_returns_200(self, client, app, db, make_user):
        with app.app_context():
            user = make_user(username="logoutme", email="logoutme@example.com")
            token = create_access_token(user.id, user.token_version)
        resp = client.post(
            "/api/users/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    def test_missing_auth_header_returns_401(self, client, db):
        resp = client.post("/api/users/logout")
        assert resp.status_code == 401

    def test_malformed_auth_header_returns_401(self, client, db):
        resp = client.post(
            "/api/users/logout",
            headers={"Authorization": "Token abc"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/users/me
# ---------------------------------------------------------------------------


class TestMeEndpoint:
    def test_valid_token_returns_user_data(self, client, app, db, make_user):
        with app.app_context():
            user = make_user(username="meuser", email="me@example.com")
            token = create_access_token(user.id, user.token_version)
        resp = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["username"] == "meuser"

    def test_missing_auth_header_returns_401(self, client, db):
        resp = client.get("/api/users/me")
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, client, db):
        resp = client.get(
            "/api/users/me",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert resp.status_code == 401

    def test_revoked_token_returns_401(self, client, app, db, make_user):
        with app.app_context():
            user = make_user(username="revokedme", email="revokedme@example.com")
            token = create_access_token(user.id, token_version=0)
            user.token_version = 1
            from app.extensions import db as _db
            _db.session.commit()
        resp = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
