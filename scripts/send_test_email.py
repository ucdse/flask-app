#!/usr/bin/env python3
"""向指定邮箱发送一封验证码测试邮件（HTML 模板），用于确认 SMTP 发信与模板效果。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 收件人写死，仅用于测试
TEST_RECIPIENT = "kevvvinyao@gmail.com"
TEST_CODE = "985724"
TEST_EXPIRES_MINUTES = 5


def main():
    from app import create_app
    from flask_mail import Message

    from app.utils.email import _render_verification_html

    app = create_app()
    with app.app_context():
        mail = app.extensions["mail"]
        subject = "[Dublin Bikes] Verify your email to start riding"

        body = (
            f"Hi there! Thanks for signing up for Dublin Bikes.\n\n"
            f"Your verification code is: {TEST_CODE}\n\n"
            f"This code will expire in {TEST_EXPIRES_MINUTES} minutes.\n\n"
            f"If you didn't sign up for an account, please ignore this message."
        )

        html_body = _render_verification_html(TEST_CODE, TEST_EXPIRES_MINUTES)

        msg = Message(
            subject=subject,
            recipients=[TEST_RECIPIENT],
            body=body,
            html=html_body,
        )
        try:
            mail.send(msg)
            print(f"已发送 HTML 验证码测试邮件到 {TEST_RECIPIENT}，请查收（含垃圾邮件）。")
        except Exception as e:
            print(f"发送失败: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
