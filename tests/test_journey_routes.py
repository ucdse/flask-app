"""
Integration tests for the /api/journey blueprint.

Google Maps client is mocked globally in conftest.py.
The find_best_route service function is also mocked where needed.
"""

from unittest.mock import patch, MagicMock

import pytest
import googlemaps.exceptions

PATCH_FIND_BEST_ROUTE = "app.api.journey_routes.find_best_route"
PATCH_SAFE_GEOCODE = "app.api.journey_routes._safe_geocode"


_MOCK_ROUTE = {
    "start_station": {
        "number": 1,
        "name": "Start",
        "address": "1 Start Rd",
        "coords": {"lat": 53.34, "lon": -6.26},
        "walking_time": 120,
        "available_bikes": 5,
    },
    "end_station": {
        "number": 2,
        "name": "End",
        "address": "2 End Rd",
        "coords": {"lat": 53.35, "lon": -6.25},
        "walking_time": 90,
        "available_bike_stands": 3,
    },
    "cycling_route": {"cycling_time": 300},
    "total_duration": 510,
}


class TestPlanJourneyWithCoords:
    def test_valid_coords_returns_200(self, client, db):
        with patch(PATCH_FIND_BEST_ROUTE, return_value=_MOCK_ROUTE):
            resp = client.post(
                "/api/journey/plan",
                json={
                    "start": {"lat": 53.34, "lon": -6.26},
                    "end": {"lat": 53.35, "lon": -6.25},
                },
            )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["code"] == 0
        assert "route_info" in body["data"]

    def test_no_route_found_returns_404(self, client, db):
        with patch(PATCH_FIND_BEST_ROUTE, return_value=None):
            resp = client.post(
                "/api/journey/plan",
                json={
                    "start": {"lat": 53.34, "lon": -6.26},
                    "end": {"lat": 53.35, "lon": -6.25},
                },
            )
        assert resp.status_code == 404

    def test_missing_lat_key_returns_400(self, client, db):
        resp = client.post(
            "/api/journey/plan",
            json={
                "start": {"lon": -6.26},
                "end": {"lat": 53.35, "lon": -6.25},
            },
        )
        assert resp.status_code == 400

    def test_non_dict_start_returns_400(self, client, db):
        resp = client.post(
            "/api/journey/plan",
            json={"start": "Dublin", "end": {"lat": 53.35, "lon": -6.25}},
        )
        assert resp.status_code == 400

    def test_invalid_lat_value_returns_400(self, client, db):
        resp = client.post(
            "/api/journey/plan",
            json={
                "start": {"lat": "not-a-number", "lon": -6.26},
                "end": {"lat": 53.35, "lon": -6.25},
            },
        )
        assert resp.status_code == 400

    def test_out_of_range_latitude_returns_400(self, client, db):
        resp = client.post(
            "/api/journey/plan",
            json={
                "start": {"lat": 200, "lon": -6.26},
                "end": {"lat": 53.35, "lon": -6.25},
            },
        )
        assert resp.status_code == 400

    def test_out_of_range_longitude_returns_400(self, client, db):
        resp = client.post(
            "/api/journey/plan",
            json={
                "start": {"lat": 53.34, "lon": 200},
                "end": {"lat": 53.35, "lon": -6.25},
            },
        )
        assert resp.status_code == 400

    def test_response_includes_resolved_coords(self, client, db):
        with patch(PATCH_FIND_BEST_ROUTE, return_value=_MOCK_ROUTE):
            resp = client.post(
                "/api/journey/plan",
                json={
                    "start": {"lat": 53.34, "lon": -6.26},
                    "end": {"lat": 53.35, "lon": -6.25},
                },
            )
        data = resp.get_json()["data"]
        assert "search_context" in data
        assert data["search_context"]["start_resolved"]["lat"] == pytest.approx(53.34)


class TestPlanJourneyWithAddresses:
    def _mock_geocode_result(self, lat, lng):
        return [{"geometry": {"location": {"lat": lat, "lng": lng}}}]

    def test_valid_addresses_return_200(self, client, db):
        with patch(PATCH_SAFE_GEOCODE) as mock_gc, patch(
            PATCH_FIND_BEST_ROUTE, return_value=_MOCK_ROUTE
        ):
            mock_gc.side_effect = [
                self._mock_geocode_result(53.34, -6.26),
                self._mock_geocode_result(53.35, -6.25),
            ]
            resp = client.post(
                "/api/journey/plan",
                json={
                    "start_address": "O'Connell Street, Dublin",
                    "end_address": "UCD Belfield",
                },
            )
        assert resp.status_code == 200

    def test_unresolvable_start_address_returns_404(self, client, db):
        with patch(PATCH_SAFE_GEOCODE, return_value=[]):
            resp = client.post(
                "/api/journey/plan",
                json={
                    "start_address": "Nonexistent Place XYZ",
                    "end_address": "UCD Belfield",
                },
            )
        assert resp.status_code == 404

    def test_unresolvable_end_address_returns_404(self, client, db):
        with patch(PATCH_SAFE_GEOCODE) as mock_gc:
            mock_gc.side_effect = [
                self._mock_geocode_result(53.34, -6.26),
                [],  # end address not found
            ]
            resp = client.post(
                "/api/journey/plan",
                json={
                    "start_address": "O'Connell Street, Dublin",
                    "end_address": "Nonexistent Place XYZ",
                },
            )
        assert resp.status_code == 404

    def test_google_maps_api_error_returns_502(self, client, db):
        with patch(
            PATCH_SAFE_GEOCODE,
            side_effect=googlemaps.exceptions.ApiError("OVER_QUERY_LIMIT"),
        ):
            resp = client.post(
                "/api/journey/plan",
                json={
                    "start_address": "O'Connell Street",
                    "end_address": "UCD Belfield",
                },
            )
        assert resp.status_code == 502

    def test_google_maps_transport_error_returns_502(self, client, db):
        with patch(
            PATCH_SAFE_GEOCODE,
            side_effect=googlemaps.exceptions.TransportError("connection refused"),
        ):
            resp = client.post(
                "/api/journey/plan",
                json={
                    "start_address": "O'Connell Street",
                    "end_address": "UCD Belfield",
                },
            )
        assert resp.status_code == 502

    def test_google_maps_timeout_returns_504(self, client, db):
        with patch(
            PATCH_SAFE_GEOCODE,
            side_effect=googlemaps.exceptions.Timeout("timed out"),
        ):
            resp = client.post(
                "/api/journey/plan",
                json={
                    "start_address": "O'Connell Street",
                    "end_address": "UCD Belfield",
                },
            )
        assert resp.status_code == 504


class TestPlanJourneyInputValidation:
    def test_missing_body_returns_400(self, client, db):
        resp = client.post("/api/journey/plan")
        assert resp.status_code == 400

    def test_empty_json_body_returns_400(self, client, db):
        resp = client.post("/api/journey/plan", json={})
        assert resp.status_code == 400

    def test_missing_both_coord_and_address_returns_400(self, client, db):
        resp = client.post("/api/journey/plan", json={"foo": "bar"})
        assert resp.status_code == 400

    def test_unexpected_exception_returns_500(self, client, db):
        with patch(
            PATCH_FIND_BEST_ROUTE, side_effect=RuntimeError("boom")
        ), patch(PATCH_SAFE_GEOCODE, return_value=None):
            # Use coords path to bypass geocoding
            resp = client.post(
                "/api/journey/plan",
                json={
                    "start": {"lat": 53.34, "lon": -6.26},
                    "end": {"lat": 53.35, "lon": -6.25},
                },
            )
        assert resp.status_code == 500
