"""
Unit tests for app.services.chat_service helper functions.

The LLM (ChatOpenAI / Qwen) is fully mocked so no network calls are made.
SQLChatMessageHistory is mocked to avoid needing a LangChain-compatible table
during unit tests.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

import pytest

from app.services.chat_service import generate_session_id, get_session_messages
from app.models import Session as SessionModel, ChatHistory


# ---------------------------------------------------------------------------
# generate_session_id  (pure function – no DB required)
# ---------------------------------------------------------------------------


class TestGenerateSessionId:
    def test_short_alphanumeric_id_returned_verbatim(self):
        sid = generate_session_id(user_id=1, chat_id="abc")
        assert sid == "user_1_chat_abc"

    def test_candidate_exactly_64_chars_accepted(self):
        # prefix = "user_1_chat_" = 12 chars, so chat_id = 52 chars fits exactly
        chat_id = "a" * 52
        sid = generate_session_id(user_id=1, chat_id=chat_id)
        assert len(sid) == 64
        assert sid == f"user_1_chat_{chat_id}"

    def test_candidate_65_chars_triggers_hash(self):
        chat_id = "a" * 53  # prefix(12) + 53 = 65 → over limit
        sid = generate_session_id(user_id=1, chat_id=chat_id)
        assert sid.startswith("user_1_chat_h_")
        assert len(sid) <= 64

    def test_special_characters_trigger_hash(self):
        sid = generate_session_id(user_id=5, chat_id="chat with spaces!")
        assert sid.startswith("user_5_chat_h_")

    def test_integer_chat_id_coerced_to_string(self):
        sid = generate_session_id(user_id=3, chat_id=42)
        assert sid == "user_3_chat_42"

    def test_float_chat_id_coerced_to_string(self):
        sid = generate_session_id(user_id=1, chat_id=3.14)
        # "3.14" contains "." which is allowed by the pattern
        assert sid == "user_1_chat_3.14"

    def test_hash_is_deterministic(self):
        sid1 = generate_session_id(user_id=1, chat_id="some long unique id " * 10)
        sid2 = generate_session_id(user_id=1, chat_id="some long unique id " * 10)
        assert sid1 == sid2

    def test_different_users_produce_different_session_ids(self):
        sid1 = generate_session_id(user_id=1, chat_id="chat1")
        sid2 = generate_session_id(user_id=2, chat_id="chat1")
        assert sid1 != sid2

    def test_different_chat_ids_produce_different_session_ids(self):
        sid1 = generate_session_id(user_id=1, chat_id="chat1")
        sid2 = generate_session_id(user_id=1, chat_id="chat2")
        assert sid1 != sid2


# ---------------------------------------------------------------------------
# get_session_messages
# ---------------------------------------------------------------------------


class TestGetSessionMessages:
    def test_returns_none_when_session_not_found(self, app, db):
        with app.app_context():
            result = get_session_messages("nonexistent-session", user_id=999)
        assert result is None

    def test_returns_none_when_session_belongs_to_different_user(
        self, app, db, make_user
    ):
        from app.extensions import db as _db

        with app.app_context():
            user1 = make_user(username="owner1", email="owner1@example.com")
            user2 = make_user(username="owner2", email="owner2@example.com")

            s = SessionModel(id="owner1-session", user_id=user1.id)
            _db.session.add(s)
            _db.session.commit()

            # user2 tries to access user1's session
            result = get_session_messages("owner1-session", user_id=user2.id)
        assert result is None

    def test_returns_empty_list_for_session_with_no_messages(
        self, app, db, make_user
    ):
        from app.extensions import db as _db

        with app.app_context():
            user = make_user(username="nomsgs", email="nomsgs@example.com")
            s = SessionModel(id="empty-session", user_id=user.id)
            _db.session.add(s)
            _db.session.commit()

            result = get_session_messages("empty-session", user_id=user.id)
        assert result == []

    def test_returns_messages_in_order(self, app, db, make_user):
        from app.extensions import db as _db

        with app.app_context():
            user = make_user(username="msguser", email="msguser@example.com")
            s = SessionModel(id="msg-session", user_id=user.id)
            _db.session.add(s)

            row1 = ChatHistory(
                session_id="msg-session",
                message={"type": "human", "data": {"content": "Hello"}},
            )
            row2 = ChatHistory(
                session_id="msg-session",
                message={"type": "ai", "data": {"content": "Hi there!"}},
            )
            _db.session.add_all([row1, row2])
            _db.session.commit()

            result = get_session_messages("msg-session", user_id=user.id)

        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello"
        assert result[1]["role"] == "assistant"
        assert result[1]["content"] == "Hi there!"

    def test_maps_human_type_to_user_role(self, app, db, make_user):
        from app.extensions import db as _db

        with app.app_context():
            user = make_user(username="roleuser", email="roleuser@example.com")
            s = SessionModel(id="role-session", user_id=user.id)
            _db.session.add(s)
            row = ChatHistory(
                session_id="role-session",
                message={"type": "human", "data": {"content": "test"}},
            )
            _db.session.add(row)
            _db.session.commit()
            result = get_session_messages("role-session", user_id=user.id)
        assert result[0]["role"] == "user"

    def test_maps_ai_type_to_assistant_role(self, app, db, make_user):
        from app.extensions import db as _db

        with app.app_context():
            user = make_user(username="airoleuser", email="airoleuser@example.com")
            s = SessionModel(id="ai-role-session", user_id=user.id)
            _db.session.add(s)
            row = ChatHistory(
                session_id="ai-role-session",
                message={"type": "ai", "data": {"content": "response"}},
            )
            _db.session.add(row)
            _db.session.commit()
            result = get_session_messages("ai-role-session", user_id=user.id)
        assert result[0]["role"] == "assistant"

    def test_unknown_message_type_uses_type_as_role(self, app, db, make_user):
        from app.extensions import db as _db

        with app.app_context():
            user = make_user(username="sysroleuser", email="sysroleuser@example.com")
            s = SessionModel(id="sys-session", user_id=user.id)
            _db.session.add(s)
            row = ChatHistory(
                session_id="sys-session",
                message={"type": "system", "data": {"content": "system prompt"}},
            )
            _db.session.add(row)
            _db.session.commit()
            result = get_session_messages("sys-session", user_id=user.id)
        assert result[0]["role"] == "system"

    def test_non_string_content_coerced_to_string(self, app, db, make_user):
        from app.extensions import db as _db

        with app.app_context():
            user = make_user(username="listcontent", email="listcontent@example.com")
            s = SessionModel(id="list-content-session", user_id=user.id)
            _db.session.add(s)
            row = ChatHistory(
                session_id="list-content-session",
                message={"type": "ai", "data": {"content": [1, 2, 3]}},
            )
            _db.session.add(row)
            _db.session.commit()
            result = get_session_messages("list-content-session", user_id=user.id)
        assert isinstance(result[0]["content"], str)

    def test_message_with_no_data_key_returns_empty_content(
        self, app, db, make_user
    ):
        from app.extensions import db as _db

        with app.app_context():
            user = make_user(username="nodatauser", email="nodatauser@example.com")
            s = SessionModel(id="nodata-session", user_id=user.id)
            _db.session.add(s)
            row = ChatHistory(
                session_id="nodata-session",
                message={"type": "human"},
            )
            _db.session.add(row)
            _db.session.commit()
            result = get_session_messages("nodata-session", user_id=user.id)
        assert result[0]["content"] == ""
