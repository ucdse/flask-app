"""
Unit tests for app.services.station_service.

All DB operations run against the in-memory SQLite instance.
"""

from datetime import datetime, timedelta

import pytest

from app.services.station_service import (
    StationNotFoundError,
    _availability_to_dict,
    _station_to_dict,
    get_all_stations_latest_availability,
    get_recent_station_availability,
    list_stations,
)


# ---------------------------------------------------------------------------
# _station_to_dict
# ---------------------------------------------------------------------------


class TestStationToDict:
    def test_converts_station_to_dict(self, app, make_station):
        with app.app_context():
            station = make_station(number=99)
            result = _station_to_dict(station)
        assert result["number"] == 99
        assert "latitude" in result
        assert "longitude" in result
        assert "bike_stands" in result

    def test_all_expected_keys_present(self, app, make_station):
        with app.app_context():
            station = make_station(number=100)
            result = _station_to_dict(station)
        expected_keys = {
            "number",
            "contract_name",
            "name",
            "address",
            "latitude",
            "longitude",
            "banking",
            "bonus",
            "bike_stands",
        }
        assert set(result.keys()) == expected_keys


# ---------------------------------------------------------------------------
# _availability_to_dict
# ---------------------------------------------------------------------------


class TestAvailabilityToDict:
    def test_converts_availability_to_dict(self, app, make_station, make_availability):
        with app.app_context():
            make_station(number=1)
            av = make_availability(number=1)
            result = _availability_to_dict(av)
        assert result["number"] == 1
        assert "available_bikes" in result
        assert "status" in result

    def test_timestamp_is_iso_string_or_none(
        self, app, make_station, make_availability
    ):
        with app.app_context():
            make_station(number=2)
            av = make_availability(number=2)
            result = _availability_to_dict(av)
        if result["timestamp"] is not None:
            datetime.fromisoformat(result["timestamp"])  # must not raise


# ---------------------------------------------------------------------------
# list_stations
# ---------------------------------------------------------------------------


class TestListStations:
    def test_returns_empty_list_when_no_stations(self, app, db):
        with app.app_context():
            result = list_stations()
        assert result == []

    def test_returns_all_stations_ordered_by_number(
        self, app, make_station
    ):
        with app.app_context():
            make_station(number=5, name="Station Five")
            make_station(number=2, name="Station Two")
            make_station(number=9, name="Station Nine")
            result = list_stations()
        numbers = [s["number"] for s in result]
        assert numbers == sorted(numbers)
        assert len(result) == 3

    def test_station_dict_structure(self, app, make_station):
        with app.app_context():
            make_station(number=42, name="Test", address="123 Rd")
            result = list_stations()
        assert result[0]["name"] == "Test"
        assert result[0]["address"] == "123 Rd"


# ---------------------------------------------------------------------------
# get_recent_station_availability
# ---------------------------------------------------------------------------


class TestGetRecentStationAvailability:
    def test_raises_when_station_not_found(self, app, db):
        with app.app_context():
            with pytest.raises(StationNotFoundError):
                get_recent_station_availability(999)

    def test_returns_records_within_lookback(
        self, app, make_station, make_availability
    ):
        with app.app_context():
            make_station(number=10)
            make_availability(
                number=10, timestamp=datetime.now() - timedelta(hours=12)
            )
            result = get_recent_station_availability(10)
        assert len(result) == 1

    def test_excludes_records_outside_lookback(
        self, app, make_station, make_availability
    ):
        with app.app_context():
            make_station(number=11)
            make_availability(
                number=11, timestamp=datetime.now() - timedelta(days=2)
            )
            result = get_recent_station_availability(11)
        assert result == []

    def test_results_ordered_ascending_by_requested_at(
        self, app, make_station, make_availability
    ):
        with app.app_context():
            make_station(number=12)
            ts1 = datetime.now() - timedelta(hours=6)
            ts2 = datetime.now() - timedelta(hours=3)
            make_availability(number=12, timestamp=ts2, requested_at=ts2)
            make_availability(number=12, timestamp=ts1, requested_at=ts1)
            result = get_recent_station_availability(12)
        assert len(result) == 2
        # First result should have the earlier requested_at
        assert result[0]["requested_at"] < result[1]["requested_at"]


# ---------------------------------------------------------------------------
# get_all_stations_latest_availability
# ---------------------------------------------------------------------------


class TestGetAllStationsLatestAvailability:
    def test_returns_empty_when_no_data(self, app, db):
        with app.app_context():
            result = get_all_stations_latest_availability()
        assert result == []

    def test_returns_only_latest_per_station(
        self, app, make_station, make_availability
    ):
        with app.app_context():
            make_station(number=20)
            # Older record with 5 bikes
            make_availability(
                number=20,
                available_bikes=5,
                timestamp=datetime.now() - timedelta(hours=2),
            )
            # Newer record with 12 bikes (this should be returned)
            make_availability(
                number=20,
                available_bikes=12,
                timestamp=datetime.now() - timedelta(minutes=5),
            )
            result = get_all_stations_latest_availability()
        assert len(result) == 1
        assert result[0]["available_bikes"] == 12

    def test_returns_one_record_per_station(
        self, app, make_station, make_availability
    ):
        with app.app_context():
            make_station(number=30)
            make_station(number=31)
            make_availability(number=30)
            make_availability(number=30)
            make_availability(number=31)
            result = get_all_stations_latest_availability()
        station_numbers = [r["number"] for r in result]
        assert sorted(station_numbers) == [30, 31]
