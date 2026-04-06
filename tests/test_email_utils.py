"""
Unit tests for app/utils/email.py.

Tests verify the mail-configuration guard, the HTML rendering helper, and the
async dispatch path – without ever connecting to a real SMTP server.
"""

import os
from unittest.mock import patch, MagicMock, mock_open

import pytest


# ---------------------------------------------------------------------------
# _mail_configured
# ---------------------------------------------------------------------------


class TestMailConfigured:
    def test_returns_false_when_no_config(self):
        import config as cfg
        with patch.multiple(
            cfg,
            MAIL_SERVER="",
            MAIL_FROM="",
            MAIL_USERNAME="",
            MAIL_PASSWORD="",
        ):
            from app.utils.email import _mail_configured
            assert _mail_configured() is False

    def test_returns_true_when_all_fields_set(self):
        import config as cfg
        with patch.multiple(
            cfg,
            MAIL_SERVER="smtp.example.com",
            MAIL_FROM="no-reply@example.com",
            MAIL_USERNAME="user",
            MAIL_PASSWORD="pass",
        ):
            from app.utils.email import _mail_configured
            assert _mail_configured() is True

    def test_returns_false_when_missing_mail_from(self):
        import config as cfg
        with patch.multiple(
            cfg,
            MAIL_SERVER="smtp.example.com",
            MAIL_FROM="",
            MAIL_USERNAME="user",
            MAIL_PASSWORD="pass",
        ):
            from app.utils.email import _mail_configured
            assert _mail_configured() is False


# ---------------------------------------------------------------------------
# _render_verification_html
# ---------------------------------------------------------------------------


class TestRenderVerificationHtml:
    def _template(self):
        return (
            "<html>{code} expires in {expires_minutes} minutes."
            "{activation_link_section}</html>"
        )

    def test_renders_code_and_expiry(self):
        from app.utils.email import _render_verification_html

        with patch("builtins.open", mock_open(read_data=self._template())):
            html = _render_verification_html("123456", 5)
        assert "123456" in html
        assert "5 minutes" in html

    def test_no_activation_link_section_when_no_link(self):
        from app.utils.email import _render_verification_html

        with patch("builtins.open", mock_open(read_data=self._template())):
            html = _render_verification_html("654321", 10)
        # activation_link_section placeholder should be replaced with empty string
        assert "{activation_link_section}" not in html

    def test_activation_link_section_present_when_token_given(self):
        from app.utils.email import _render_verification_html

        with patch("builtins.open", mock_open(read_data=self._template())):
            html = _render_verification_html(
                "111111", 5, activation_link="http://example.com/activate/abc"
            )
        assert "http://example.com/activate/abc" in html


# ---------------------------------------------------------------------------
# send_verification_code_email_async
# ---------------------------------------------------------------------------


class TestSendVerificationCodeEmailAsync:
    def test_does_nothing_when_mail_not_configured(self):
        """If mail is not configured, the function should return without submitting."""
        from app.utils import email as email_mod

        with patch.object(email_mod, "_mail_configured", return_value=False):
            with patch.object(email_mod._email_executor, "submit") as mock_submit:
                email_mod.send_verification_code_email_async(
                    "to@example.com", "123456", 5
                )
            mock_submit.assert_not_called()

    def test_submits_task_when_configured(self, app):
        """When mail IS configured, a background task should be submitted."""
        from app.utils import email as email_mod

        with app.app_context():
            with patch.object(email_mod, "_mail_configured", return_value=True):
                with patch.object(
                    email_mod._email_executor, "submit"
                ) as mock_submit:
                    email_mod.send_verification_code_email_async(
                        "to@example.com", "654321", 10
                    )
            mock_submit.assert_called_once()


# ---------------------------------------------------------------------------
# _send_verification_code_with_flask_mail
# ---------------------------------------------------------------------------


class TestSendVerificationCodeWithFlaskMail:
    def test_does_nothing_when_mail_not_configured(self, app):
        from app.utils import email as email_mod

        with patch.object(email_mod, "_mail_configured", return_value=False):
            # Should return without error
            email_mod._send_verification_code_with_flask_mail(
                app, "to@example.com", "123456", 5
            )

    def test_sends_message_when_configured(self, app):
        from app.utils import email as email_mod

        fake_mail = MagicMock()
        # Patch _mail_configured and mail instance
        with patch.object(email_mod, "_mail_configured", return_value=True):
            with patch.object(email_mod, "_render_verification_html", return_value="<html>body</html>"):
                with app.app_context():
                    app.extensions["mail"] = fake_mail
                    email_mod._send_verification_code_with_flask_mail(
                        app, "to@example.com", "999999", 5
                    )
        fake_mail.send.assert_called_once()

    def test_activation_link_included_when_token_provided(self, app):
        from app.utils import email as email_mod
        import config as cfg

        captured_body = {}

        def fake_send(msg):
            captured_body["body"] = msg.body

        fake_mail = MagicMock()
        fake_mail.send.side_effect = fake_send

        with patch.object(email_mod, "_mail_configured", return_value=True):
            with patch.object(email_mod, "_render_verification_html", return_value="<html>body</html>"):
                with patch.object(cfg, "FRONTEND_BASE_URL", "http://localhost:5173"):
                    with app.app_context():
                        app.extensions["mail"] = fake_mail
                        email_mod._send_verification_code_with_flask_mail(
                            app, "to@example.com", "000000", 5,
                            activation_token="mytoken"
                        )
        assert "http://localhost:5173/activate/mytoken" in captured_body.get("body", "")

    def test_mail_send_exception_is_silenced(self, app):
        """A send failure must not propagate — just print and continue."""
        from app.utils import email as email_mod

        fake_mail = MagicMock()
        fake_mail.send.side_effect = Exception("SMTP error")

        with patch.object(email_mod, "_mail_configured", return_value=True):
            with patch.object(email_mod, "_render_verification_html", return_value="<html>"):
                with app.app_context():
                    app.extensions["mail"] = fake_mail
                    # Should not raise
                    email_mod._send_verification_code_with_flask_mail(
                        app, "to@example.com", "111111", 5
                    )
