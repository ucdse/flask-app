#!/usr/bin/env python3
"""测试 .env 中配置的 SMTP 服务器连通性（连接 + 登录）。"""

import os
import sys

# 保证从项目根目录加载 .env
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

MAIL_SERVER = os.environ.get("MAIL_SERVER", "").strip()
MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "").strip()
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "").strip()
MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() in ("1", "true", "yes")
MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "").lower() in ("1", "true", "yes")
# 端口 465 通常用 SSL，587 用 STARTTLS；未显式设置时按端口推断
use_ssl = MAIL_USE_SSL or (MAIL_PORT == 465)


def main():
    if not MAIL_SERVER:
        print("未配置 MAIL_SERVER，请在 .env 中填写。")
        sys.exit(1)

    import smtplib

    if use_ssl:
        print(f"正在连接 {MAIL_SERVER}:{MAIL_PORT} (SSL) ...")
    else:
        print(f"正在连接 {MAIL_SERVER}:{MAIL_PORT} (TLS={MAIL_USE_TLS}) ...")
    try:
        if use_ssl:
            with smtplib.SMTP_SSL(MAIL_SERVER, MAIL_PORT, timeout=15) as server:
                if MAIL_USERNAME and MAIL_PASSWORD:
                    server.login(MAIL_USERNAME, MAIL_PASSWORD)
                    print("连接成功，登录成功。")
                else:
                    print("连接成功。（未配置 MAIL_USERNAME/MAIL_PASSWORD，未执行登录）")
        else:
            with smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=15) as server:
                server.ehlo()
                if MAIL_USE_TLS:
                    server.starttls()
                    server.ehlo()
                if MAIL_USERNAME and MAIL_PASSWORD:
                    server.login(MAIL_USERNAME, MAIL_PASSWORD)
                    print("连接成功，登录成功。")
                else:
                    print("连接成功。（未配置 MAIL_USERNAME/MAIL_PASSWORD，未执行登录）")
    except smtplib.SMTPAuthenticationError as e:
        print(f"连接成功，但登录失败（账号或密码错误）: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"连接失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
