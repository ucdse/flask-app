"""邮件发送工具，使用 Flask-Mail 发送验证码等。异步发送不阻塞请求。"""

import os
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import config

# 后台线程池，用于异步发邮件，不阻塞请求
_email_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="email-send")

# HTML 邮件模板路径
_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
_VERIFICATION_TEMPLATE = os.path.join(_TEMPLATE_DIR, "email_verification.html")


def _render_verification_html(
    code: str, expires_minutes: int, activation_link: str = ""
) -> str:
    """读取 HTML 模板并填充验证码、过期时间与激活链接。"""
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
    """是否已配置邮件（MAIL_SERVER 与发件人必填）。"""
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
    在应用上下文中使用 Flask-Mail 发送验证码邮件（HTML + 纯文本双格式）。
    若提供 activation_token，邮件中会包含「点击激活」链接。
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
            print(f"[邮箱验证] Flask-Mail 发送成功 to={to_email}")
        except Exception as e:
            print(f"[邮箱验证] Flask-Mail 发送失败 to={to_email} error={e!r}")


def send_verification_code_email_async(
    to_email: str,
    code: str,
    expires_minutes: int,
    activation_token: Optional[str] = None,
) -> None:
    """
    异步发送验证码邮件：提交到线程池后立即返回，不阻塞当前请求。
    若提供 activation_token，邮件中会包含激活链接 /activate/:token。
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
