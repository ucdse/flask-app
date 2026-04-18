from flask import Flask

from config import (
    ALIYUN_API_KEY,
    MAIL_DEFAULT_SENDER,
    MAIL_PASSWORD,
    MAIL_PORT,
    MAIL_SERVER,
    MAIL_USE_SSL,
    MAIL_USE_TLS,
    MAIL_USERNAME,
    SECRET_KEY,
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
)
from .extensions import db, mail, migrate


def create_app() -> Flask:
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    if SECRET_KEY:
        app.config["SECRET_KEY"] = SECRET_KEY

    # Flask-Mail
    app.config["MAIL_SERVER"] = MAIL_SERVER
    app.config["MAIL_PORT"] = MAIL_PORT
    app.config["MAIL_USE_TLS"] = MAIL_USE_TLS
    app.config["MAIL_USE_SSL"] = MAIL_USE_SSL
    app.config["MAIL_USERNAME"] = MAIL_USERNAME
    app.config["MAIL_PASSWORD"] = MAIL_PASSWORD
    app.config["MAIL_DEFAULT_SENDER"] = MAIL_DEFAULT_SENDER

    # Aliyun Qwen (chat)
    app.config["ALIYUN_API_KEY"] = ALIYUN_API_KEY

    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    # Ensure models are imported for Flask-Migrate autogenerate.
    from . import models  # noqa: F401
    from .api import register_blueprints

    register_blueprints(app)

    # Pre-warm the application on startup
    with app.app_context():
        from .services.prediction_service import _load_model
        import logging
        try:
            _load_model()
            logging.info("🚲 Bike prediction model correctly preloaded.")
        except Exception as e:
            logging.error(f"⚠️ Failed to preload prediction model: {e}")

    return app
