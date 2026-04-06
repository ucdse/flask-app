"""
Unit tests for utility functions.

Covers:
  - calculateDistance.calculate_distance (Haversine formula)
  - api_retry.gmaps_retry decorator
"""

import time
import pytest
from unittest.mock import MagicMock, patch, call
import googlemaps.exceptions

from app.utils.calculateDistance import calculate_distance
from app.utils.api_retry import gmaps_retry


# ---------------------------------------------------------------------------
# calculate_distance
# ---------------------------------------------------------------------------


class TestCalculateDistance:
    def test_same_point_returns_zero(self):
        """Distance from a point to itself must be 0."""
        assert calculate_distance(53.34, -6.26, 53.34, -6.26) == 0.0

    def test_known_distance_dublin_to_cork(self):
        """Dublin to Cork is roughly 220 km in a straight line."""
        dist = calculate_distance(53.3498, -6.2603, 51.8985, -8.4756)
        assert 200 < dist < 250

    def test_short_distance_within_dublin(self):
        """Two nearby Dublin stations should be < 2 km apart."""
        dist = calculate_distance(53.345, -6.265, 53.350, -6.260)
        assert 0 < dist < 2

    def test_antipodal_points_roughly_half_earth_circumference(self):
        """Antipodal points should be approximately 20_000 km."""
        dist = calculate_distance(0, 0, 0, 180)
        assert 19_000 < dist < 21_000

    def test_symmetric_distance(self):
        """Distance A→B must equal distance B→A."""
        d1 = calculate_distance(53.34, -6.26, 53.35, -6.25)
        d2 = calculate_distance(53.35, -6.25, 53.34, -6.26)
        assert abs(d1 - d2) < 1e-9

    def test_returns_float(self):
        result = calculate_distance(53.0, -6.0, 54.0, -5.0)
        assert isinstance(result, float)

    def test_north_south_distance(self):
        """One degree of latitude is roughly 111 km."""
        dist = calculate_distance(53.0, 0.0, 54.0, 0.0)
        assert 100 < dist < 120

    def test_negative_coordinates(self):
        """Function should handle negative lat/lon without error."""
        dist = calculate_distance(-33.87, 151.21, -37.81, 144.96)
        assert dist > 0

    def test_floating_point_edge_case_no_math_domain_error(self):
        """Identical floating-point coords must not trigger math domain errors."""
        # Internally clamps 'a' to [0,1] before atan2
        assert calculate_distance(53.34001, -6.26001, 53.34001, -6.26001) == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# gmaps_retry decorator
# ---------------------------------------------------------------------------


class TestGmapsRetry:
    def test_success_on_first_attempt(self):
        """Function returning normally should not retry."""
        mock_fn = MagicMock(return_value="ok")
        decorated = gmaps_retry(max_retries=2)(mock_fn)
        result = decorated()
        assert result == "ok"
        assert mock_fn.call_count == 1

    def test_retries_on_transport_error_then_succeeds(self):
        """Should retry on TransportError and return value after recovery."""
        side_effects = [googlemaps.exceptions.TransportError("fail"), "ok"]
        mock_fn = MagicMock(side_effect=side_effects)

        with patch("time.sleep"):
            decorated = gmaps_retry(max_retries=2)(mock_fn)
            result = decorated()

        assert result == "ok"
        assert mock_fn.call_count == 2

    def test_raises_after_max_retries_exceeded(self):
        """Should raise the original exception after all retries are exhausted."""
        mock_fn = MagicMock(
            side_effect=googlemaps.exceptions.ApiError("OVER_QUERY_LIMIT")
        )

        with patch("time.sleep"):
            decorated = gmaps_retry(max_retries=2)(mock_fn)
            with pytest.raises(googlemaps.exceptions.ApiError):
                decorated()

        assert mock_fn.call_count == 3  # 1 initial + 2 retries

    def test_retries_on_timeout_error(self):
        """Timeout errors should also trigger retries."""
        side_effects = [
            googlemaps.exceptions.Timeout("timeout"),
            googlemaps.exceptions.Timeout("timeout"),
            "success",
        ]
        mock_fn = MagicMock(side_effect=side_effects)

        with patch("time.sleep"):
            decorated = gmaps_retry(max_retries=3)(mock_fn)
            result = decorated()

        assert result == "success"

    def test_non_gmaps_exception_not_retried(self):
        """A plain ValueError must propagate immediately without retries."""
        mock_fn = MagicMock(side_effect=ValueError("unrelated"))
        decorated = gmaps_retry(max_retries=2)(mock_fn)

        with pytest.raises(ValueError):
            decorated()

        assert mock_fn.call_count == 1

    def test_zero_retries_raises_immediately(self):
        """With max_retries=0 the exception should propagate on first failure."""
        mock_fn = MagicMock(
            side_effect=googlemaps.exceptions.TransportError("fail")
        )
        with patch("time.sleep"):
            decorated = gmaps_retry(max_retries=0)(mock_fn)
            with pytest.raises(googlemaps.exceptions.TransportError):
                decorated()

        assert mock_fn.call_count == 1

    def test_preserves_function_name(self):
        """@functools.wraps must preserve the wrapped function's __name__."""

        def my_func():
            return 42

        decorated = gmaps_retry(max_retries=1)(my_func)
        assert decorated.__name__ == "my_func"
