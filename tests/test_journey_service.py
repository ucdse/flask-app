"""
Unit tests for app.services.journey_service.find_best_route and helpers.

Google Maps API calls are mocked. DB queries run against the in-memory SQLite.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.services.journey_service import find_best_route


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_station_row(number, lat, lon, name="Station", bike_stands=20):
    from app.models import Station

    s = Station(
        number=number,
        contract_name="dublin",
        name=name,
        address=f"{number} Rd",
        latitude=lat,
        longitude=lon,
        banking=True,
        bonus=False,
        bike_stands=bike_stands,
    )
    return s


def _make_availability_row(number, bikes=5, stands=10, status="OPEN", age_minutes=5):
    from app.models import Availability

    ts = datetime.now() - timedelta(minutes=age_minutes)
    av = Availability(
        number=number,
        available_bikes=bikes,
        available_bike_stands=stands,
        status=status,
        last_update=int(ts.timestamp() * 1000),
        timestamp=ts,
        requested_at=ts,
    )
    return av


# ---------------------------------------------------------------------------
# find_best_route
# ---------------------------------------------------------------------------


PATCH_MATRIX = "app.services.journey_service.get_matrix_durations"


class TestFindBestRoute:
    def _seed_stations(self, db, pairs):
        """
        pairs: list of (number, lat, lon, bikes, stands)
        Creates Station + Availability records for each.
        """
        from app.extensions import db as _db

        for number, lat, lon, bikes, stands in pairs:
            s = _make_station_row(number, lat, lon)
            av = _make_availability_row(number, bikes=bikes, stands=stands)
            _db.session.add(s)
            _db.session.add(av)
        _db.session.commit()

    def test_returns_none_when_no_stations(self, app, db):
        with app.app_context():
            result = find_best_route(53.34, -6.26, 53.35, -6.25)
        assert result is None

    def test_returns_none_when_no_available_bikes(
        self, app, db
    ):
        """Only stations with 0 bikes can act as a start; only 0-stand stations
        can act as an end.  With no viable candidates the result is None."""
        with app.app_context():
            # Station 1: 0 bikes (cannot start), 5 stands (can end)
            # Station 2: 0 bikes (cannot start), 0 stands (cannot end)
            # → no valid start station candidates at all
            self._seed_stations(
                db,
                [(1, 53.34, -6.26, 0, 5), (2, 53.35, -6.25, 0, 0)],
            )
            result = find_best_route(53.34, -6.26, 53.35, -6.25)
        assert result is None

    def test_returns_none_when_station_is_closed(self, app, db):
        with app.app_context():
            from app.extensions import db as _db
            s1 = _make_station_row(10, 53.34, -6.26)
            av1 = _make_availability_row(10, bikes=5, stands=10, status="CLOSED")
            s2 = _make_station_row(11, 53.35, -6.25)
            av2 = _make_availability_row(11, bikes=0, stands=5, status="CLOSED")
            _db.session.add_all([s1, av1, s2, av2])
            _db.session.commit()
            result = find_best_route(53.34, -6.26, 53.35, -6.25)
        assert result is None

    def test_returns_none_when_stale_data(self, app, db):
        """Availability older than 30 minutes should be excluded."""
        with app.app_context():
            from app.extensions import db as _db
            s1 = _make_station_row(20, 53.34, -6.26)
            av1 = _make_availability_row(20, bikes=5, stands=10, age_minutes=35)
            s2 = _make_station_row(21, 53.35, -6.25)
            av2 = _make_availability_row(21, bikes=5, stands=10, age_minutes=35)
            _db.session.add_all([s1, av1, s2, av2])
            _db.session.commit()
            result = find_best_route(53.34, -6.26, 53.35, -6.25)
        assert result is None

    def test_returns_best_route_with_two_stations(self, app, db):
        """Happy path: two stations, one with bikes, one with stands."""
        with app.app_context():
            self._seed_stations(
                db,
                [
                    (30, 53.34, -6.26, 5, 0),  # start station: has bikes
                    (31, 53.35, -6.25, 0, 5),  # end station: has stands
                ],
            )
            # Mock matrix durations: [[walk_to_start]], [[walk_from_end]], [[cycle]]
            def mock_matrix(origins, destinations, mode="walking"):
                return [[120]]

            with patch(PATCH_MATRIX, side_effect=mock_matrix):
                result = find_best_route(53.34, -6.26, 53.35, -6.25)

        assert result is not None
        assert result["start_station"]["number"] == 30
        assert result["end_station"]["number"] == 31
        assert "total_duration" in result
        assert result["total_duration"] == 360  # 120 + 120 + 120

    def test_result_contains_expected_keys(self, app, db):
        with app.app_context():
            self._seed_stations(
                db,
                [
                    (40, 53.34, -6.26, 5, 0),
                    (41, 53.35, -6.25, 0, 5),
                ],
            )
            with patch(PATCH_MATRIX, return_value=[[200]]):
                result = find_best_route(53.34, -6.26, 53.35, -6.25)

        assert result is not None
        assert "start_station" in result
        assert "end_station" in result
        assert "cycling_route" in result
        assert "total_duration" in result

    def test_skips_same_station_for_start_and_end(self, app, db):
        """When the same station is the only candidate, no valid route exists."""
        with app.app_context():
            from app.extensions import db as _db
            # Station 50 has both bikes AND stands → might appear as both start & end
            s = _make_station_row(50, 53.34, -6.26)
            av = _make_availability_row(50, bikes=5, stands=5)
            _db.session.add_all([s, av])
            _db.session.commit()

            with patch(PATCH_MATRIX, return_value=[[100]]):
                result = find_best_route(53.34, -6.26, 53.34, -6.26)

        # Since start == end station, find_best_route should return None
        assert result is None

    def test_route_when_matrix_returns_infinity(self, app, db):
        """If all matrix durations are infinity, no valid route can be built."""
        with app.app_context():
            self._seed_stations(
                db,
                [
                    (60, 53.34, -6.26, 5, 0),
                    (61, 53.35, -6.25, 0, 5),
                ],
            )
            with patch(PATCH_MATRIX, return_value=[[float("inf")]]):
                result = find_best_route(53.34, -6.26, 53.35, -6.25)

        assert result is None
