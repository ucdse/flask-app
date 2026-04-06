"""
Integration tests for the /api/stations blueprint.
"""

from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest


class TestListStationsEndpoint:
    def test_returns_200_with_empty_list(self, client, db):
        resp = client.get("/api/stations/")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["code"] == 0
        assert body["data"] == []

    def test_returns_all_stations(self, client, db, make_station):
        make_station(number=1, name="Station One")
        make_station(number=2, name="Station Two")
        resp = client.get("/api/stations/")
        assert resp.status_code == 200
        assert len(resp.get_json()["data"]) == 2

    def test_station_response_has_expected_fields(self, client, db, make_station):
        make_station(number=5, name="My Station", address="5 Road")
        resp = client.get("/api/stations/")
        station = resp.get_json()["data"][0]
        for key in ("number", "name", "address", "latitude", "longitude", "bike_stands"):
            assert key in station


class TestGetStationAvailabilityEndpoint:
    def test_unknown_station_returns_404(self, client, db):
        resp = client.get("/api/stations/999/availability")
        assert resp.status_code == 404
        assert resp.get_json()["code"] == 1

    def test_known_station_with_no_records_returns_empty_list(
        self, client, db, make_station
    ):
        make_station(number=10)
        resp = client.get("/api/stations/10/availability")
        assert resp.status_code == 200
        assert resp.get_json()["data"] == []

    def test_returns_availability_records(
        self, client, db, make_station, make_availability
    ):
        make_station(number=11)
        make_availability(number=11, available_bikes=7)
        resp = client.get("/api/stations/11/availability")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert len(data) == 1
        assert data[0]["available_bikes"] == 7

    def test_availability_record_has_expected_fields(
        self, client, db, make_station, make_availability
    ):
        make_station(number=12)
        make_availability(number=12)
        data = client.get("/api/stations/12/availability").get_json()["data"][0]
        for key in ("number", "available_bikes", "available_bike_stands", "status"):
            assert key in data


class TestGetAllStationsStatusEndpoint:
    def test_returns_200(self, client, db):
        resp = client.get("/api/stations/status")
        assert resp.status_code == 200

    def test_returns_latest_per_station(
        self, client, db, make_station, make_availability
    ):
        make_station(number=20)
        make_availability(number=20, available_bikes=3)
        make_availability(number=20, available_bikes=8)
        resp = client.get("/api/stations/status")
        data = resp.get_json()["data"]
        assert len(data) == 1
        assert data[0]["available_bikes"] == 8


class TestGetStationPredictionEndpoint:
    def test_returns_400_when_prediction_service_raises(
        self, client, db, make_station
    ):
        make_station(number=50)
        with patch(
            "app.api.station_routes.get_station_predictions",
            side_effect=__import__(
                "app.services.prediction_service", fromlist=["PredictionError"]
            ).PredictionError("no model"),
        ):
            resp = client.get("/api/stations/50/prediction")
        assert resp.status_code == 400

    def test_returns_200_when_predictions_available(
        self, client, db, make_station
    ):
        make_station(number=51)
        predictions = [
            {"forecast_time": "2024-01-01T10:00:00", "predicted_available_bikes": 5}
        ]
        with patch(
            "app.api.station_routes.get_station_predictions",
            return_value=predictions,
        ):
            resp = client.get("/api/stations/51/prediction")
        assert resp.status_code == 200
        assert resp.get_json()["data"] == predictions

    def test_returns_500_on_unexpected_exception(self, client, db, make_station):
        make_station(number=52)
        with patch(
            "app.api.station_routes.get_station_predictions",
            side_effect=RuntimeError("unexpected"),
        ):
            resp = client.get("/api/stations/52/prediction")
        assert resp.status_code == 500
