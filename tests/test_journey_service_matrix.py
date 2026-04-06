"""
Tests for the get_matrix_durations helper in journey_service.py.

All Google Maps API calls are mocked.
"""

from unittest.mock import MagicMock, patch

import pytest
import googlemaps.exceptions

from app.services.journey_service import get_matrix_durations


PATCH_GMAPS = "app.services.journey_service.gmaps"


def _ok_matrix_response(duration_seconds: int = 300):
    """Build a minimal successful Google Maps Distance Matrix API response."""
    return {
        "status": "OK",
        "rows": [
            {
                "elements": [
                    {
                        "status": "OK",
                        "duration": {"value": duration_seconds},
                    }
                ]
            }
        ],
    }


class TestGetMatrixDurations:
    def test_returns_duration_from_successful_api_response(self):
        mock_client = MagicMock()
        mock_client.distance_matrix.return_value = _ok_matrix_response(200)

        with patch(PATCH_GMAPS, mock_client):
            result = get_matrix_durations(
                [(53.34, -6.26)], [(53.35, -6.25)], mode="walking"
            )

        assert result == [[200]]

    def test_returns_infinity_for_impossible_element(self):
        mock_client = MagicMock()
        mock_client.distance_matrix.return_value = {
            "status": "OK",
            "rows": [{"elements": [{"status": "ZERO_RESULTS"}]}],
        }

        with patch(PATCH_GMAPS, mock_client):
            result = get_matrix_durations(
                [(53.34, -6.26)], [(53.35, -6.25)], mode="walking"
            )

        assert result == [[float("inf")]]

    def test_returns_infinity_matrix_when_gmaps_is_none(self):
        with patch(PATCH_GMAPS, None):
            result = get_matrix_durations(
                [(53.34, -6.26)], [(53.35, -6.25)], mode="walking"
            )

        assert result == [[float("inf")]]

    def test_raises_api_error_on_non_ok_status(self):
        mock_client = MagicMock()
        mock_client.distance_matrix.return_value = {
            "status": "OVER_QUERY_LIMIT",
            "error_message": "quota exceeded",
        }

        with patch(PATCH_GMAPS, mock_client):
            with pytest.raises(googlemaps.exceptions.ApiError):
                get_matrix_durations(
                    [(53.34, -6.26)], [(53.35, -6.25)]
                )

    def test_multiple_origins_and_destinations(self):
        mock_client = MagicMock()
        mock_client.distance_matrix.return_value = {
            "status": "OK",
            "rows": [
                {
                    "elements": [
                        {"status": "OK", "duration": {"value": 100}},
                        {"status": "OK", "duration": {"value": 200}},
                    ]
                },
                {
                    "elements": [
                        {"status": "OK", "duration": {"value": 300}},
                        {"status": "OK", "duration": {"value": 400}},
                    ]
                },
            ],
        }

        with patch(PATCH_GMAPS, mock_client):
            result = get_matrix_durations(
                [(53.34, -6.26), (53.35, -6.25)],
                [(53.36, -6.24), (53.37, -6.23)],
            )

        assert result == [[100, 200], [300, 400]]

    def test_raises_api_error_after_retries_on_transport_error(self):
        mock_client = MagicMock()
        mock_client.distance_matrix.side_effect = (
            googlemaps.exceptions.TransportError("network error")
        )

        with patch(PATCH_GMAPS, mock_client):
            with patch("time.sleep"):
                with pytest.raises(googlemaps.exceptions.ApiError):
                    get_matrix_durations([(53.34, -6.26)], [(53.35, -6.25)])
