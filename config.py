"""Flask application configuration. Sensitive info is read from environment variables (see .env)."""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Database configuration (must be read from .env)
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set, please configure in .env file")

SQLALCHEMY_DATABASE_URI = DATABASE_URL
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = os.environ.get("SECRET_KEY")

# JWT configuration (read from .env, used for access/refresh tokens)
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable is not set, please configure in .env file")

JWT_REFRESH_SECRET_KEY = os.environ.get("JWT_REFRESH_SECRET_KEY")
if not JWT_REFRESH_SECRET_KEY:
    raise ValueError("JWT_REFRESH_SECRET_KEY environment variable is not set, please configure in .env file")

# Expiration time (seconds), optional, uses default value if not set
JWT_ACCESS_EXPIRES_SECONDS = int(os.environ.get("JWT_ACCESS_EXPIRES_SECONDS", "900"))   # Default 15 minutes
JWT_REFRESH_EXPIRES_SECONDS = int(os.environ.get("JWT_REFRESH_EXPIRES_SECONDS", "604800"))  # Default 7 days

# Email verification code: expiration (seconds, e.g. 5 minutes); resend cooldown (seconds, e.g. can only request once within 1 minute)
VERIFICATION_CODE_EXPIRE_SECONDS = int(os.environ.get("VERIFICATION_CODE_EXPIRE_SECONDS", "300"))   # Default 5 minutes
VERIFICATION_CODE_RESEND_COOLDOWN_SECONDS = int(os.environ.get("VERIFICATION_CODE_RESEND_COOLDOWN_SECONDS", "60"))  # Default 1 minute

# Flask-Mail / SMTP sender configuration (used for sending verification code emails); when not configured, only outputs to console
MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() in ("1", "true", "yes")
MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "").lower() in ("1", "true", "yes") or (MAIL_PORT == 465)
MAIL_FROM = os.environ.get("MAIL_FROM", "")  # Sender address, e.g. noreply@example.com
MAIL_DEFAULT_FROM_NAME = os.environ.get("MAIL_DEFAULT_FROM_NAME", "Dublin Bikes")  # Sender display name (optional)
# Flask-Mail MAIL_DEFAULT_SENDER: tuple (display name, email) or email only
MAIL_DEFAULT_SENDER = (
    (MAIL_DEFAULT_FROM_NAME, MAIL_FROM) if MAIL_FROM else None
)
# Frontend activation page base URL, used for "click to activate" link in emails: {FRONTEND_BASE_URL}/activate/{token}
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://localhost:5173").rstrip("/")

# OpenWeatherMap API configuration (used for weather forecast)
OPENWEATHER_API_BASE_URL = os.environ.get("OPENWEATHER_API_BASE_URL", "https://api.openweathermap.org/data/3.0/onecall")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")
if not OPENWEATHER_API_KEY:
    raise ValueError("OPENWEATHER_API_KEY environment variable is not set, please configure in .env file")

# Google Maps API configuration (used for route planning)
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")

# Aliyun Qwen configuration (used for LLM etc.)
ALIYUN_API_KEY = os.environ.get("ALIYUN_API_KEY")
