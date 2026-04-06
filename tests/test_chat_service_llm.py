"""
Tests for the LLM-facing functions in chat_service.py.

ChatOpenAI / LangChain calls are fully mocked.  SQLChatMessageHistory is also
mocked so we don't need a real `message_store` table schema beyond what SQLite
creates automatically (the table is already present in test DB via the model).
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.models import Session as SessionModel


PATCH_CHAT_OPENAI = "app.services.chat_service.ChatOpenAI"
PATCH_PROMPT = "app.services.chat_service.ChatPromptTemplate"
PATCH_RUNNABLE = "app.services.chat_service.RunnableWithMessageHistory"
PATCH_SQL_HISTORY = "app.services.chat_service.SQLChatMessageHistory"
PATCH_DB_TEXT = "app.services.chat_service.db.text"
PATCH_DB_SESSION_EXECUTE = "app.services.chat_service.db.session.execute"


# ---------------------------------------------------------------------------
# get_chat_history (factory for SQLChatMessageHistory)
# ---------------------------------------------------------------------------


class TestGetChatHistory:
    def test_returns_sql_history_instance(self, app):
        from app.services.chat_service import get_chat_history
        from app.extensions import db as _db

        with app.app_context():
            with patch(PATCH_SQL_HISTORY) as mock_cls:
                mock_cls.return_value = MagicMock()
                result = get_chat_history("test-session-id")
            mock_cls.assert_called_once_with(
                session_id="test-session-id",
                connection=_db.engine,
                table_name="message_store",
            )


# ---------------------------------------------------------------------------
# _ensure_session
# ---------------------------------------------------------------------------


class TestEnsureSession:
    def test_creates_session_when_not_found(self, app, db, make_user):
        from app.services.chat_service import _ensure_session
        from app.extensions import db as _db

        with app.app_context():
            user = make_user(username="ensureuser", email="ensure@example.com")
            user_id = user.id  # capture scalar before leaving session scope
            _ensure_session("new-session-id", user_id)
            s = _db.session.get(SessionModel, "new-session-id")
            assert s is not None
            assert s.user_id == user_id

    def test_updates_existing_session_timestamp(self, app, db, make_user):
        from app.services.chat_service import _ensure_session
        from app.extensions import db as _db

        with app.app_context():
            user = make_user(username="ensureuser2", email="ensure2@example.com")
            # Create first
            _ensure_session("existing-session", user.id)
            s1 = _db.session.get(SessionModel, "existing-session")
            ts1 = s1.updated_at

            # Call again – should update updated_at
            _ensure_session("existing-session", user.id)
            _db.session.refresh(s1)
            ts2 = s1.updated_at

        # updated_at should be >= the first call
        assert ts2 >= ts1


# ---------------------------------------------------------------------------
# generate_chat_response
# ---------------------------------------------------------------------------


class TestGenerateChatResponse:
    def _setup_mocks(self, mock_openai_cls, mock_prompt_cls, mock_runnable_cls):
        """Configure mocks for LLM chain."""
        mock_llm = MagicMock()
        mock_openai_cls.return_value = mock_llm

        mock_prompt = MagicMock()
        mock_prompt_cls.from_messages.return_value = mock_prompt

        mock_chain = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        mock_chain_with_history = MagicMock()
        mock_runnable_cls.return_value = mock_chain_with_history

        mock_response = MagicMock()
        mock_response.content = "Test response from AI"
        mock_chain_with_history.invoke.return_value = mock_response

        return mock_chain_with_history

    def test_returns_llm_response_content(self, app, db, make_user):
        from app.services.chat_service import generate_chat_response
        from app.extensions import db as _db

        with app.app_context():
            user = make_user(username="chatllm1", email="chatllm1@example.com")

            with patch(PATCH_CHAT_OPENAI) as mock_oai, \
                 patch(PATCH_PROMPT) as mock_p, \
                 patch(PATCH_RUNNABLE) as mock_r, \
                 patch(PATCH_SQL_HISTORY):

                chain_mock = self._setup_mocks(mock_oai, mock_p, mock_r)
                # Simulate no existing messages (first message)
                with patch.object(_db.session, "execute") as mock_exec:
                    mock_exec.return_value.fetchone.return_value = None
                    result = generate_chat_response(
                        "user_1_chat_test", "Hello!", user.id
                    )

        assert result == "Test response from AI"

    def test_calls_chain_with_user_input(self, app, db, make_user):
        from app.services.chat_service import generate_chat_response
        from app.extensions import db as _db

        with app.app_context():
            user = make_user(username="chatllm2", email="chatllm2@example.com")

            with patch(PATCH_CHAT_OPENAI) as mock_oai, \
                 patch(PATCH_PROMPT) as mock_p, \
                 patch(PATCH_RUNNABLE) as mock_r, \
                 patch(PATCH_SQL_HISTORY):

                chain_mock = self._setup_mocks(mock_oai, mock_p, mock_r)
                with patch.object(_db.session, "execute") as mock_exec:
                    mock_exec.return_value.fetchone.return_value = None
                    generate_chat_response("session-abc", "Hi there", user.id)

            call_args = chain_mock.invoke.call_args
            assert call_args[0][0]["user_input"] == "Hi there"


# ---------------------------------------------------------------------------
# generate_chat_stream
# ---------------------------------------------------------------------------


class TestGenerateChatStream:
    def test_yields_data_chunks_and_done(self, app, db, make_user):
        from app.services.chat_service import generate_chat_stream
        from app.extensions import db as _db

        with app.app_context():
            user = make_user(username="streamllm1", email="streamllm1@example.com")

            mock_chunk1 = MagicMock()
            mock_chunk1.content = "Hello"
            mock_chunk2 = MagicMock()
            mock_chunk2.content = " world"

            mock_chain_with_history = MagicMock()
            mock_chain_with_history.stream.return_value = iter([mock_chunk1, mock_chunk2])

            with patch(PATCH_CHAT_OPENAI), \
                 patch(PATCH_PROMPT), \
                 patch(PATCH_RUNNABLE, return_value=mock_chain_with_history), \
                 patch(PATCH_SQL_HISTORY):

                with patch.object(_db.session, "execute") as mock_exec:
                    mock_exec.return_value.fetchone.return_value = None
                    chunks = list(
                        generate_chat_stream("stream-session", "Hi", user.id)
                    )

        # Should have two data chunks plus the [DONE] marker
        assert any("[DONE]" in c for c in chunks)
        content_chunks = [c for c in chunks if '"content"' in c]
        assert len(content_chunks) == 2

    def test_yields_error_event_on_exception(self, app, db, make_user):
        from app.services.chat_service import generate_chat_stream
        from app.extensions import db as _db

        with app.app_context():
            user = make_user(username="streamllm2", email="streamllm2@example.com")

            with patch(PATCH_CHAT_OPENAI, side_effect=RuntimeError("LLM down")):
                with patch.object(_db.session, "execute") as mock_exec:
                    mock_exec.return_value.fetchone.return_value = None
                    chunks = list(
                        generate_chat_stream("error-session", "Hi", user.id)
                    )

        assert any("error" in c for c in chunks)

    def test_empty_content_chunks_not_yielded(self, app, db, make_user):
        from app.services.chat_service import generate_chat_stream
        from app.extensions import db as _db

        with app.app_context():
            user = make_user(username="streamllm3", email="streamllm3@example.com")

            mock_chunk_empty = MagicMock()
            mock_chunk_empty.content = ""  # empty content should be skipped

            mock_chain_with_history = MagicMock()
            mock_chain_with_history.stream.return_value = iter([mock_chunk_empty])

            with patch(PATCH_CHAT_OPENAI), \
                 patch(PATCH_PROMPT), \
                 patch(PATCH_RUNNABLE, return_value=mock_chain_with_history), \
                 patch(PATCH_SQL_HISTORY):

                with patch.object(_db.session, "execute") as mock_exec:
                    mock_exec.return_value.fetchone.return_value = None
                    chunks = list(
                        generate_chat_stream("empty-stream-session", "Hi", user.id)
                    )

        # Only [DONE] should be yielded
        content_chunks = [c for c in chunks if '"content"' in c]
        assert len(content_chunks) == 0
        assert any("[DONE]" in c for c in chunks)
