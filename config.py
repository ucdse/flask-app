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
