from flask import Flask

from extensions import db, migrate
import models  # noqa: F401  # Ensure models are registered for Flask-Migrate autogenerate.
from config import (
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    SECRET_KEY,
)


def create_app() -> Flask:
    app = Flask(__name__)

    # 从 config 读取：数据库地址、Session 密钥等
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    if SECRET_KEY:
        app.config["SECRET_KEY"] = SECRET_KEY

    db.init_app(app)
    migrate.init_app(app, db)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
