"""
Integration tests for the /api/chat blueprint.

The LLM calls (generate_chat_response / generate_chat_stream) and
database session helpers are mocked so no real Qwen/OpenAI calls are made.
"""

from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from app.services.user_service import create_access_token


PATCH_GENERATE = "app.api.chat_routes.generate_chat_response"
PATCH_STREAM = "app.api.chat_routes.generate_chat_stream"
PATCH_GET_MSGS = "app.api.chat_routes.get_session_messages"
PATCH_GEN_SESSION_ID = "app.api.chat_routes.generate_session_id"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_auth_header(app, make_user, username="chatuser", email="chat@example.com"):
    """Create a user and return the Authorization header dict."""
    with app.app_context():
        user = make_user(username=username, email=email, is_active=True)
        token = create_access_token(user.id, user.token_version)
    return user, {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# POST /api/chat/
# ---------------------------------------------------------------------------


class TestChatEndpoint:
    def test_valid_message_returns_200(self, client, app, db, make_user):
        user, headers = _make_auth_header(app, make_user)
        with patch(PATCH_GENERATE, return_value="Hello there!"):
            resp = client.post(
                "/api/chat/",
                json={"message": "Hi", "chat_id": "test-chat"},
                headers=headers,
            )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["code"] == 0
        assert body["data"]["reply"] == "Hello there!"

    def test_missing_auth_header_returns_401(self, client, db):
        resp = client.post("/api/chat/", json={"message": "Hi"})
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, client, db):
        resp = client.post(
            "/api/chat/",
            json={"message": "Hi"},
            headers={"Authorization": "Bearer invalid.token"},
        )
        assert resp.status_code == 401

    def test_missing_message_field_returns_400(self, client, app, db, make_user):
        user, headers = _make_auth_header(
            app, make_user, username="chatuser2", email="chat2@example.com"
        )
        resp = client.post(
            "/api/chat/",
            json={"chat_id": "some-chat"},
            headers=headers,
        )
        assert resp.status_code == 400

    def test_empty_message_returns_400(self, client, app, db, make_user):
        user, headers = _make_auth_header(
            app, make_user, username="chatuser3", email="chat3@example.com"
        )
        resp = client.post(
            "/api/chat/",
            json={"message": "", "chat_id": "some-chat"},
            headers=headers,
        )
        assert resp.status_code == 400

    def test_non_string_message_returns_400(self, client, app, db, make_user):
        user, headers = _make_auth_header(
            app, make_user, username="chatuser4", email="chat4@example.com"
        )
        resp = client.post(
            "/api/chat/",
            json={"message": 123, "chat_id": "some-chat"},
            headers=headers,
        )
        assert resp.status_code == 400

    def test_non_dict_body_returns_400(self, client, app, db, make_user):
        user, headers = _make_auth_header(
            app, make_user, username="chatuser5", email="chat5@example.com"
        )
        resp = client.post(
            "/api/chat/",
            data="not json",
            content_type="application/json",
            headers=headers,
        )
        assert resp.status_code == 400

    def test_service_exception_returns_500(self, client, app, db, make_user):
        user, headers = _make_auth_header(
            app, make_user, username="chatuser6", email="chat6@example.com"
        )
        with patch(PATCH_GENERATE, side_effect=RuntimeError("llm down")):
            resp = client.post(
                "/api/chat/",
                json={"message": "Hi", "chat_id": "test-chat"},
                headers=headers,
            )
        assert resp.status_code == 500
        assert resp.get_json()["code"] == 50000

    def test_response_contains_chat_id(self, client, app, db, make_user):
        user, headers = _make_auth_header(
            app, make_user, username="chatuser7", email="chat7@example.com"
        )
        with patch(PATCH_GENERATE, return_value="Reply"):
            resp = client.post(
                "/api/chat/",
                json={"message": "Test", "chat_id": "my-chat"},
                headers=headers,
            )
        assert resp.get_json()["data"]["chat_id"] == "my-chat"


# ---------------------------------------------------------------------------
# POST /api/chat/stream
# ---------------------------------------------------------------------------


class TestChatStreamEndpoint:
    def _make_fake_stream(self):
        """Generator that yields two SSE data chunks and a DONE marker."""

        def _gen(*args, **kwargs):
            yield 'data: {"content": "Hello"}\n\n'
            yield 'data: {"content": " world"}\n\n'
            yield "data: [DONE]\n\n"

        return _gen

    def test_valid_request_returns_event_stream(self, client, app, db, make_user):
        user, headers = _make_auth_header(
            app, make_user, username="streamuser", email="stream@example.com"
        )
        with patch(PATCH_STREAM, new=self._make_fake_stream()):
            resp = client.post(
                "/api/chat/stream",
                json={"message": "Hi", "chat_id": "stream-chat"},
                headers=headers,
            )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.content_type

    def test_missing_auth_returns_401(self, client, db):
        resp = client.post("/api/chat/stream", json={"message": "Hi"})
        assert resp.status_code == 401

    def test_missing_message_returns_400(self, client, app, db, make_user):
        user, headers = _make_auth_header(
            app, make_user, username="streamuser2", email="stream2@example.com"
        )
        resp = client.post(
            "/api/chat/stream",
            json={"chat_id": "stream-chat"},
            headers=headers,
        )
        assert resp.status_code == 400

    def test_non_dict_body_returns_400(self, client, app, db, make_user):
        user, headers = _make_auth_header(
            app, make_user, username="streamuser3", email="stream3@example.com"
        )
        resp = client.post(
            "/api/chat/stream",
            data="not json",
            content_type="application/json",
            headers=headers,
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/chat/sessions
# ---------------------------------------------------------------------------


class TestListSessionsEndpoint:
    def test_returns_200_for_authenticated_user(self, client, app, db, make_user):
        user, headers = _make_auth_header(
            app, make_user, username="sessuser", email="sess@example.com"
        )
        resp = client.get("/api/chat/sessions", headers=headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["code"] == 0
        assert isinstance(body["data"], list)

    def test_missing_auth_returns_401(self, client, db):
        resp = client.get("/api/chat/sessions")
        assert resp.status_code == 401

    def test_returns_user_sessions_from_db(self, client, app, db, make_user):
        """Sessions belonging to the authenticated user should appear in the list."""
        from app.models import Session as SessionModel
        from app.extensions import db as _db

        with app.app_context():
            user = make_user(username="sessowner", email="sessowner@example.com")
            # Capture plain-int values while still inside the session
            user_id = user.id
            token_version = user.token_version
            token = create_access_token(user_id, token_version)
            headers = {"Authorization": f"Bearer {token}"}

            # Manually create a session record
            session_id = f"user_{user_id}_chat_test"
            s = SessionModel(id=session_id, user_id=user_id)
            _db.session.add(s)
            _db.session.commit()

        resp = client.get("/api/chat/sessions", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert len(data) >= 1
        session_ids = [item["session_id"] for item in data]
        assert session_id in session_ids


# ---------------------------------------------------------------------------
# GET /api/chat/sessions/<session_id>/messages
# ---------------------------------------------------------------------------


class TestGetSessionHistoryEndpoint:
    def test_returns_404_for_unknown_session(self, client, app, db, make_user):
        user, headers = _make_auth_header(
            app, make_user, username="histuser", email="hist@example.com"
        )
        with patch(PATCH_GET_MSGS, return_value=None):
            resp = client.get(
                "/api/chat/sessions/nonexistent-session/messages",
                headers=headers,
            )
        assert resp.status_code == 404
        assert resp.get_json()["code"] == 404

    def test_returns_messages_for_valid_session(self, client, app, db, make_user):
        user, headers = _make_auth_header(
            app, make_user, username="histuser2", email="hist2@example.com"
        )
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        with patch(PATCH_GET_MSGS, return_value=messages):
            resp = client.get(
                "/api/chat/sessions/some-session-id/messages",
                headers=headers,
            )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["code"] == 0
        assert body["data"]["messages"] == messages

    def test_missing_auth_returns_401(self, client, db):
        resp = client.get("/api/chat/sessions/some-session/messages")
        assert resp.status_code == 401

    def test_empty_session_returns_empty_list(self, client, app, db, make_user):
        user, headers = _make_auth_header(
            app, make_user, username="histuser3", email="hist3@example.com"
        )
        with patch(PATCH_GET_MSGS, return_value=[]):
            resp = client.get(
                "/api/chat/sessions/empty-session/messages",
                headers=headers,
            )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["messages"] == []


# ---------------------------------------------------------------------------
# generate_session_id  (unit-level test for chat_service helper)
# ---------------------------------------------------------------------------


class TestGenerateSessionId:
    def test_short_alphanumeric_chat_id(self):
        from app.services.chat_service import generate_session_id

        sid = generate_session_id(user_id=1, chat_id="chat1")
        assert sid == "user_1_chat_chat1"

    def test_non_string_chat_id_coerced(self):
        from app.services.chat_service import generate_session_id

        sid = generate_session_id(user_id=2, chat_id=42)
        assert sid == "user_2_chat_42"

    def test_long_chat_id_uses_hash(self):
        from app.services.chat_service import generate_session_id

        long_id = "x" * 100
        sid = generate_session_id(user_id=1, chat_id=long_id)
        assert sid.startswith("user_1_chat_h_")
        assert len(sid) <= 64

    def test_special_chars_in_chat_id_uses_hash(self):
        from app.services.chat_service import generate_session_id

        sid = generate_session_id(user_id=1, chat_id="chat id with spaces!")
        assert sid.startswith("user_1_chat_h_")
