"""
Integration tests for the /api/weather blueprint.
"""

from unittest.mock import patch

import pytest

from app.services.weather_service import WeatherAPIError


PATCH_GET_WEATHER = "app.api.weather_routes.get_weather"


class TestGetWeatherForecastEndpoint:
    def test_returns_200_with_weather_data(self, client, db):
        mock_data = {
            "current": {"dt": 1700000000, "temp": 15.0, "weather": []},
            "hourly": [],
        }
        with patch(PATCH_GET_WEATHER, return_value=mock_data):
            resp = client.get("/api/weather")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["code"] == 0
        assert "current" in body["data"]

    def test_returns_error_when_service_raises(self, client, db):
        with patch(PATCH_GET_WEATHER, side_effect=WeatherAPIError("no data", 404)):
            resp = client.get("/api/weather")
        assert resp.status_code == 404
        body = resp.get_json()
        assert body["code"] == 50001
        assert "no data" in body["msg"]

    def test_returns_500_on_server_error(self, client, db):
        with patch(
            PATCH_GET_WEATHER,
            side_effect=WeatherAPIError("db failure", 500),
        ):
            resp = client.get("/api/weather")
        assert resp.status_code == 500

    def test_response_structure_is_consistent(self, client, db):
        mock_data = {
            "current": {"dt": 1700000000, "temp": 12.0, "weather": []},
            "hourly": [{"dt": 1700003600, "temp": 13.0, "weather": []}],
        }
        with patch(PATCH_GET_WEATHER, return_value=mock_data):
            resp = client.get("/api/weather")
        body = resp.get_json()
        assert "code" in body
        assert "msg" in body
        assert "data" in body

    def test_real_db_no_data_returns_error(self, client, db):
        """Without seeded forecast data the service should raise WeatherAPIError."""
        resp = client.get("/api/weather")
        # Status is either 404 or 500 (WeatherAPIError is always raised when empty)
        assert resp.status_code in (404, 500)
