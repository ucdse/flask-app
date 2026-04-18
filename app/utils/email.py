"""Email sending utility using Flask-Mail to send verification codes, etc. Asynchronous sending does not block requests."""

import os
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import config

# Background thread pool for asynchronous email sending, does not block requests
_email_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="email-send")

# HTML email template path
_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
_VERIFICATION_TEMPLATE = os.path.join(_TEMPLATE_DIR, "email_verification.html")


def _render_verification_html(
    code: str, expires_minutes: int, activation_link: str = ""
) -> str:
    """Read HTML template and fill in verification code, expiration time, and activation link."""
    with open(_VERIFICATION_TEMPLATE, "r", encoding="utf-8") as f:
        html = f.read()
    html = html.replace("{code}", code).replace("{expires_minutes}", str(expires_minutes))
    if activation_link:
        activation_section = (
            '<tr><td style="padding: 20px 40px 8px 40px; text-align: center;">'
            '<p style="margin: 0 0 12px 0; font-size: 13px; color: #666666;">Or click the link below to verify your email:</p>'
            f'<a href="{activation_link}" style="display: inline-block; padding: 14px 28px; background: linear-gradient(135deg, #1DB954 0%, #0A8F3F 100%); color: #ffffff; font-size: 15px; font-weight: 600; text-decoration: none; border-radius: 10px;">Verify my email</a>'
            "</td></tr>"
        )
    else:
        activation_section = ""
    html = html.replace("{activation_link_section}", activation_section)
    return html


def _mail_configured() -> bool:
    """Check if email is configured (MAIL_SERVER and sender are required)."""
    return bool(
        config.MAIL_SERVER
        and config.MAIL_FROM
        and config.MAIL_USERNAME
        and config.MAIL_PASSWORD
    )


def _send_verification_code_with_flask_mail(
    app, to_email: str, code: str, expires_minutes: int, activation_token: Optional[str] = None
) -> None:
    """
    Send verification code email using Flask-Mail in application context (HTML + plain-text dual format).
    If activation_token is provided, the email will include a 'click to activate' link.
    """
    if not _mail_configured():
        return
    with app.app_context():
        from flask_mail import Message

        mail = app.extensions["mail"]
        subject = "[Dublin Bikes] Verify your email to start riding"

        activation_link = ""
        if activation_token:
            activation_link = f"{config.FRONTEND_BASE_URL}/activate/{activation_token}"

        # Plain-text fallback
        body = (
            f"Hi there! Thanks for signing up for Dublin Bikes.\n\n"
            f"Your verification code is: {code}\n\n"
            f"This code will expire in {expires_minutes} minutes.\n\n"
        )
        if activation_link:
            body += f"Or click this link to verify your email: {activation_link}\n\n"
        body += "If you didn't sign up for an account, please ignore this message."

        html_body = _render_verification_html(code, expires_minutes, activation_link)

        msg = Message(subject=subject, recipients=[to_email], body=body, html=html_body)
        try:
            mail.send(msg)
            print(f"[Email Verification] Flask-Mail sent successfully to={to_email}")
        except Exception as e:
            print(f"[Email Verification] Flask-Mail failed to send to={to_email} error={e!r}")


def send_verification_code_email_async(
    to_email: str,
    code: str,
    expires_minutes: int,
    activation_token: Optional[str] = None,
) -> None:
    """
    Asynchronously send verification code email: returns immediately after submitting to thread pool, does not block current request.
    If activation_token is provided, the email will include activation link /activate/:token.
    """
    if not _mail_configured():
        return
    from flask import current_app

    app = current_app._get_current_object()
    _email_executor.submit(
        _send_verification_code_with_flask_mail,
        app,
        to_email,
        code,
        expires_minutes,
        activation_token,
    )
