from flask import Flask

from config import (
    SECRET_KEY,
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
)
from .extensions import db, migrate


def create_app() -> Flask:
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    if SECRET_KEY:
        app.config["SECRET_KEY"] = SECRET_KEY

    db.init_app(app)
    migrate.init_app(app, db)

    # Ensure models are imported for Flask-Migrate autogenerate.
    from . import models  # noqa: F401
    from .api import register_blueprints

    register_blueprints(app)

    return app
