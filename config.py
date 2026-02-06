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
