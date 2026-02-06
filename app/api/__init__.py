from flask import Flask


def register_blueprints(app: Flask) -> None:
    from .user_routes import user_bp

    app.register_blueprint(user_bp)
