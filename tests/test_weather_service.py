"""
Unit tests for app.services.weather_service.

Uses the WeatherForecast model with the in-memory SQLite DB.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.weather_service import WeatherAPIError, get_weather


class TestGetWeather:
    def test_raises_when_no_forecasts_in_db(self, app, db):
        with app.app_context():
            with pytest.raises(WeatherAPIError) as exc_info:
                get_weather()
        # Either 404 (no data) or 500 (general) – both are WeatherAPIError
        assert isinstance(exc_info.value, WeatherAPIError)

    def test_returns_current_and_hourly_keys(self, app, make_weather_forecast):
        with app.app_context():
            make_weather_forecast(
                forecast_time=datetime.utcnow() + timedelta(hours=1)
            )
            result = get_weather()
        assert "current" in result
        assert "hourly" in result

    def test_current_contains_expected_fields(self, app, make_weather_forecast):
        with app.app_context():
            make_weather_forecast(
                forecast_time=datetime.utcnow() + timedelta(hours=1),
                temperature=18.5,
                humidity=70,
            )
            result = get_weather()
        current = result["current"]
        assert "dt" in current
        assert "temp" in current
        assert "humidity" in current
        assert "weather" in current
        assert isinstance(current["weather"], list)
        assert len(current["weather"]) == 1

    def test_hourly_list_contains_all_forecasts(self, app, make_weather_forecast):
        with app.app_context():
            for i in range(1, 5):
                make_weather_forecast(
                    forecast_time=datetime.utcnow() + timedelta(hours=i)
                )
            result = get_weather()
        # get_weather limits to 6 forecasts
        assert len(result["hourly"]) == 4

    def test_current_uses_earliest_forecast(self, app, make_weather_forecast):
        with app.app_context():
            make_weather_forecast(
                forecast_time=datetime.utcnow() + timedelta(hours=1),
                temperature=10.0,
            )
            make_weather_forecast(
                forecast_time=datetime.utcnow() + timedelta(hours=2),
                temperature=20.0,
            )
            result = get_weather()
        assert result["current"]["temp"] == 10.0

    def test_temperature_value_preserved(self, app, make_weather_forecast):
        with app.app_context():
            make_weather_forecast(
                forecast_time=datetime.utcnow() + timedelta(hours=1),
                temperature=22.5,
            )
            result = get_weather()
        assert result["current"]["temp"] == 22.5

    def test_past_forecasts_excluded(self, app, db, make_weather_forecast):
        """Only forecasts at or after the current hour should be returned."""
        with app.app_context():
            make_weather_forecast(
                forecast_time=datetime.utcnow() - timedelta(hours=2)
            )
            with pytest.raises(WeatherAPIError):
                get_weather()

    def test_weather_code_in_current(self, app, make_weather_forecast):
        with app.app_context():
            make_weather_forecast(
                forecast_time=datetime.utcnow() + timedelta(hours=1),
                weather_code=800,
                description="clear sky",
                icon="01d",
            )
            result = get_weather()
        weather_item = result["current"]["weather"][0]
        assert weather_item["id"] == 800
        assert weather_item["description"] == "clear sky"
        assert weather_item["icon"] == "01d"

    def test_hourly_items_contain_pop_field(self, app, make_weather_forecast):
        with app.app_context():
            make_weather_forecast(
                forecast_time=datetime.utcnow() + timedelta(hours=1),
                pop=0.4,
            )
            result = get_weather()
        assert "pop" in result["hourly"][0]
        assert result["hourly"][0]["pop"] == pytest.approx(0.4)


class TestWeatherAPIError:
    def test_default_message(self):
        err = WeatherAPIError()
        assert err.message == "weather API error"
        assert err.status_code == 500

    def test_custom_message_and_status(self):
        err = WeatherAPIError("no data", 404)
        assert err.message == "no data"
        assert err.status_code == 404
