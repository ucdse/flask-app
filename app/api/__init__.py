from flask import Flask


def register_blueprints(app: Flask) -> None:
    from .station_routes import station_bp
    from .user_routes import user_bp

    app.register_blueprint(station_bp)
    app.register_blueprint(user_bp)
