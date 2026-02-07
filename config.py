"""Flask 应用配置。隐私信息从环境变量读取（见 .env）。"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 数据库配置（必须从 .env 读取）
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL 环境变量未设置，请在 .env 文件中配置")

SQLALCHEMY_DATABASE_URI = DATABASE_URL
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = os.environ.get("SECRET_KEY")

# JWT 配置（从 .env 读取，用于 access/refresh 令牌）
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY 环境变量未设置，请在 .env 文件中配置")

JWT_REFRESH_SECRET_KEY = os.environ.get("JWT_REFRESH_SECRET_KEY")
if not JWT_REFRESH_SECRET_KEY:
    raise ValueError("JWT_REFRESH_SECRET_KEY 环境变量未设置，请在 .env 文件中配置")

# 过期时间（秒），可选，未设置时使用默认值
JWT_ACCESS_EXPIRES_SECONDS = int(os.environ.get("JWT_ACCESS_EXPIRES_SECONDS", "900"))   # 默认 15 分钟
JWT_REFRESH_EXPIRES_SECONDS = int(os.environ.get("JWT_REFRESH_EXPIRES_SECONDS", "604800"))  # 默认 7 天

# 邮箱验证码：有效期（秒，如 5 分钟）；重发冷却（秒，如 1 分钟内只能请求一次）
VERIFICATION_CODE_EXPIRE_SECONDS = int(os.environ.get("VERIFICATION_CODE_EXPIRE_SECONDS", "300"))   # 默认 5 分钟
VERIFICATION_CODE_RESEND_COOLDOWN_SECONDS = int(os.environ.get("VERIFICATION_CODE_RESEND_COOLDOWN_SECONDS", "60"))  # 默认 1 分钟

# Flask-Mail / SMTP 发件配置（用于发送验证码邮件）；未配置时仅输出到控制台
MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() in ("1", "true", "yes")
MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "").lower() in ("1", "true", "yes") or (MAIL_PORT == 465)
MAIL_FROM = os.environ.get("MAIL_FROM", "")  # 发件人地址，如 noreply@example.com
MAIL_DEFAULT_FROM_NAME = os.environ.get("MAIL_DEFAULT_FROM_NAME", "Dublin Bikes")  # 发件人显示名（可选）
# Flask-Mail 的 MAIL_DEFAULT_SENDER：tuple (显示名, 邮箱) 或仅邮箱
MAIL_DEFAULT_SENDER = (
    (MAIL_DEFAULT_FROM_NAME, MAIL_FROM) if MAIL_FROM else None
)
# 前端激活页基础 URL，用于邮件中的「点击激活」链接：{FRONTEND_BASE_URL}/activate/{token}
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://localhost:5173").rstrip("/")
