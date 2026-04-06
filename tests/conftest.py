"""
Shared pytest fixtures for the Flask application test suite.

All tests run against an in-memory SQLite database so they never touch
the production MySQL instance.  External services (Google Maps, Qwen LLM,
Flask-Mail, email executor) are fully mocked at the module level.
"""

import os
import sys

# ---------------------------------------------------------------------------
# Force test env vars BEFORE any application code is imported so
# config.py does not raise ValueError on missing keys.
# Use direct assignment (not setdefault) to override any values already
# exported by the shell or CI, ensuring the suite is always hermetic and
# never accidentally connects to a real database or external service.
# ---------------------------------------------------------------------------
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-12345678"
os.environ["JWT_REFRESH_SECRET_KEY"] = "test-jwt-refresh-secret-key-12345678"
os.environ["OPENWEATHER_API_KEY"] = "test-openweather-api-key"
os.environ["GOOGLE_MAPS_API_KEY"] = "test-google-maps-api-key"
os.environ["ALIYUN_API_KEY"] = "test-aliyun-api-key"

from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from werkzeug.security import generate_password_hash

# ---------------------------------------------------------------------------
# Patch heavy / external dependencies before importing app modules
# ---------------------------------------------------------------------------

# googlemaps is a real installed package – import it first so submodules
# (googlemaps.exceptions, googlemaps.Client) resolve correctly.
import googlemaps  # noqa: E402
import googlemaps.exceptions  # noqa: E402

# Prevent a real googlemaps.Client from being instantiated at module-import
# time inside journey_routes.py / journey_service.py.  We patch the class
# at the top-level module so the module-level `gmaps = googlemaps.Client(...)
# call returns a MagicMock instead of making a real HTTP connection.
_fake_gmaps_client = MagicMock()
googlemaps.Client = MagicMock(return_value=_fake_gmaps_client)

# ---------------------------------------------------------------------------
# Now import application modules (env vars and mocks are in place)
# ---------------------------------------------------------------------------
from app import create_app  # noqa: E402
from app.extensions import db as _db  # noqa: E402
from app.models import User, Station, Availability, WeatherForecast, Session, ChatHistory  # noqa: E402


# ---------------------------------------------------------------------------
# App / DB fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def app():
    """Create a Flask application instance configured for testing."""
    flask_app = create_app()
    flask_app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "WTF_CSRF_ENABLED": False,
            "MAIL_SUPPRESS_SEND": True,
        }
    )
    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.drop_all()


@pytest.fixture()
def db(app):
    """Yield the database and roll back after each test for isolation."""
    with app.app_context():
        yield _db
        _db.session.rollback()
        # Delete all rows so tests don't bleed state into each other
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Common model factory helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def make_user(db):
    """Factory: create and persist a User instance."""

    def _factory(
        username="testuser",
        email="test@example.com",
        password="password123",
        is_active=True,
        token_version=0,
        email_verification_code=None,
        email_verification_code_expires_at=None,
        email_verification_code_sent_at=None,
        activation_token=None,
    ):
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            is_active=is_active,
            token_version=token_version,
            email_verification_code=email_verification_code,
            email_verification_code_expires_at=email_verification_code_expires_at,
            email_verification_code_sent_at=email_verification_code_sent_at,
            activation_token=activation_token,
        )
        db.session.add(user)
        db.session.commit()
        return user

    return _factory


@pytest.fixture()
def make_station(db):
    """Factory: create and persist a Station instance."""

    def _factory(
        number=1,
        contract_name="dublin",
        name="Test Station",
        address="1 Test Street",
        latitude=53.34,
        longitude=-6.26,
        banking=True,
        bonus=False,
        bike_stands=20,
    ):
        station = Station(
            number=number,
            contract_name=contract_name,
            name=name,
            address=address,
            latitude=latitude,
            longitude=longitude,
            banking=banking,
            bonus=bonus,
            bike_stands=bike_stands,
        )
        db.session.add(station)
        db.session.commit()
        return station

    return _factory


@pytest.fixture()
def make_availability(db):
    """Factory: create and persist an Availability instance."""
    from datetime import datetime

    def _factory(
        number=1,
        available_bikes=10,
        available_bike_stands=10,
        status="OPEN",
        last_update=1700000000000,
        timestamp=None,
        requested_at=None,
    ):
        ts = timestamp or datetime.now()
        availability = Availability(
            number=number,
            available_bikes=available_bikes,
            available_bike_stands=available_bike_stands,
            status=status,
            last_update=last_update,
            timestamp=ts,
            requested_at=requested_at or ts,
        )
        db.session.add(availability)
        db.session.commit()
        return availability

    return _factory


@pytest.fixture()
def make_weather_forecast(db):
    """Factory: create and persist a WeatherForecast instance."""
    from datetime import datetime, timedelta

    def _factory(
        forecast_time=None,
        temperature=15.0,
        weather_code=800,
        description="clear sky",
        icon="01d",
        feels_like=14.0,
        pressure=1013,
        humidity=65,
        uvi=2.0,
        clouds=5,
        visibility=10000,
        wind_speed=3.5,
        wind_deg=180,
        pop=0.0,
    ):
        ft = forecast_time or (datetime.utcnow() + timedelta(hours=1))
        wf = WeatherForecast(
            forecast_time=ft,
            temperature=temperature,
            weather_code=weather_code,
            description=description,
            icon=icon,
            feels_like=feels_like,
            pressure=pressure,
            humidity=humidity,
            uvi=uvi,
            clouds=clouds,
            visibility=visibility,
            wind_speed=wind_speed,
            wind_deg=wind_deg,
            pop=pop,
        )
        db.session.add(wf)
        db.session.commit()
        return wf

    return _factory


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------


@pytest.fixture()
def auth_headers(app, make_user):
    """Return a (user, headers) tuple for an active, logged-in user."""
    from app.services.user_service import create_access_token

    user = make_user(username="authuser", email="auth@example.com", is_active=True)

    with app.app_context():
        token = create_access_token(user.id, user.token_version)

    return user, {"Authorization": f"Bearer {token}"}
