"""
Unit tests for app.services.prediction_service.

The ML model (pickle file) and all DB queries are mocked so the tests run
without trained artefacts or a real database.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.services.prediction_service import PredictionError


PATCH_LOAD_MODEL = "app.services.prediction_service._load_model"
PATCH_MODEL = "app.services.prediction_service._model"
PATCH_FEATURES = "app.services.prediction_service._features"


class TestPredictionError:
    def test_default_message(self):
        err = PredictionError()
        assert err.message == "prediction error"

    def test_custom_message(self):
        err = PredictionError("station not found")
        assert err.message == "station not found"


class TestGetStationPredictions:
    def _make_mock_forecast(self, hour_offset=1, temperature=15.0, humidity=60, pressure=1013):
        """Create a minimal WeatherForecast-like mock."""
        f = MagicMock()
        f.forecast_time = datetime.utcnow().replace(
            minute=0, second=0, microsecond=0
        ) + timedelta(hours=hour_offset)
        f.temperature = temperature
        f.humidity = humidity
        f.pressure = pressure
        return f

    def _make_mock_station(self, number=1, bike_stands=20, lat=53.34, lon=-6.26):
        s = MagicMock()
        s.number = number
        s.bike_stands = bike_stands
        s.latitude = lat
        s.longitude = lon
        return s

    def test_raises_prediction_error_when_station_not_found(self, app, db):
        from app.services import prediction_service

        with app.app_context():
            with patch.object(prediction_service, "_load_model"):
                with patch("app.extensions.db.session") as mock_session:
                    mock_session.get.return_value = None
                    with pytest.raises(PredictionError, match="not found"):
                        prediction_service.get_station_predictions(9999)

    def test_raises_prediction_error_when_no_forecasts(self, app, db, make_station):
        from app.services import prediction_service

        with app.app_context():
            make_station(number=77)
            with patch.object(prediction_service, "_load_model"):
                with patch.object(
                    prediction_service, "_model", MagicMock()
                ), patch.object(prediction_service, "_features", ["station_id"]):
                    with patch(
                        "app.models.weather.WeatherForecast.query"
                    ) as mock_query:
                        mock_query.filter.return_value.order_by.return_value.all.return_value = []
                        with pytest.raises(PredictionError, match="No weather forecast"):
                            prediction_service.get_station_predictions(77)

    def test_predictions_returned_for_valid_station_and_forecasts(
        self, app, db, make_station
    ):
        from app.services import prediction_service
        import pandas as pd

        with app.app_context():
            make_station(number=78, bike_stands=15)
            forecasts = [self._make_mock_forecast(i) for i in range(1, 4)]
            features = [
                "station_id", "capacity", "lat", "lon",
                "hour", "day", "day_of_week", "is_weekend",
                "avg_temperature", "avg_humidity", "avg_pressure",
            ]
            mock_model = MagicMock()
            mock_model.predict.return_value = [5.3, 7.1, 3.9]

            with patch.object(prediction_service, "_load_model"):
                with patch.object(prediction_service, "_model", mock_model):
                    with patch.object(prediction_service, "_features", features):
                        with patch(
                            "app.models.weather.WeatherForecast.query"
                        ) as mock_query:
                            mock_query.filter.return_value.order_by.return_value.all.return_value = forecasts
                            result = prediction_service.get_station_predictions(78)

        assert len(result) == 3
        for item in result:
            assert "forecast_time" in item
            assert "predicted_available_bikes" in item
            assert isinstance(item["predicted_available_bikes"], int)

    def test_predictions_clamped_to_zero_minimum(
        self, app, db, make_station
    ):
        """Negative predictions must be clamped to 0."""
        from app.services import prediction_service

        with app.app_context():
            make_station(number=79, bike_stands=20)
            forecasts = [self._make_mock_forecast(1)]
            features = [
                "station_id", "capacity", "lat", "lon",
                "hour", "day", "day_of_week", "is_weekend",
                "avg_temperature", "avg_humidity", "avg_pressure",
            ]
            mock_model = MagicMock()
            mock_model.predict.return_value = [-5.0]  # negative prediction

            with patch.object(prediction_service, "_load_model"):
                with patch.object(prediction_service, "_model", mock_model):
                    with patch.object(prediction_service, "_features", features):
                        with patch(
                            "app.models.weather.WeatherForecast.query"
                        ) as mock_query:
                            mock_query.filter.return_value.order_by.return_value.all.return_value = forecasts
                            result = prediction_service.get_station_predictions(79)

        assert result[0]["predicted_available_bikes"] == 0

    def test_predictions_clamped_to_bike_stands_maximum(
        self, app, db, make_station
    ):
        """Predictions over bike_stands capacity must be clamped to bike_stands."""
        from app.services import prediction_service

        with app.app_context():
            make_station(number=80, bike_stands=10)
            forecasts = [self._make_mock_forecast(1)]
            features = [
                "station_id", "capacity", "lat", "lon",
                "hour", "day", "day_of_week", "is_weekend",
                "avg_temperature", "avg_humidity", "avg_pressure",
            ]
            mock_model = MagicMock()
            mock_model.predict.return_value = [999.9]  # way over capacity

            with patch.object(prediction_service, "_load_model"):
                with patch.object(prediction_service, "_model", mock_model):
                    with patch.object(prediction_service, "_features", features):
                        with patch(
                            "app.models.weather.WeatherForecast.query"
                        ) as mock_query:
                            mock_query.filter.return_value.order_by.return_value.all.return_value = forecasts
                            result = prediction_service.get_station_predictions(80)

        assert result[0]["predicted_available_bikes"] == 10

    def test_load_model_raises_when_files_missing(self, app):
        """_load_model must raise FileNotFoundError when pkl files are absent."""
        from app.services import prediction_service

        with app.app_context():
            # Reset cached globals to force re-load
            prediction_service._model = None
            prediction_service._features = None

            with patch("os.path.exists", return_value=False):
                with pytest.raises(FileNotFoundError):
                    prediction_service._load_model()

        # Restore so other tests are not affected
        prediction_service._model = None
        prediction_service._features = None

    def test_load_model_skips_when_already_loaded(self, app):
        """_load_model should be a no-op if model is already cached."""
        from app.services import prediction_service

        mock_model = MagicMock()
        mock_features = ["col1"]

        with app.app_context():
            prediction_service._model = mock_model
            prediction_service._features = mock_features

            with patch("builtins.open") as mock_open:
                prediction_service._load_model()
            mock_open.assert_not_called()

        prediction_service._model = None
        prediction_service._features = None
