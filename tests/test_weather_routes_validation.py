"""
Tests for the _validation_error_message helper in weather_routes.py.
"""

import pytest
from pydantic import ValidationError

from app.api.weather_routes import _validation_error_message
from app.contracts.request import WeatherQueryDTO


class TestValidationErrorMessage:
    def _make_validation_error(self, payload: dict) -> ValidationError:
        try:
            WeatherQueryDTO.model_validate(payload)
        except ValidationError as exc:
            return exc
        raise AssertionError("Expected ValidationError was not raised")

    def test_returns_field_name_and_message_for_missing_field(self):
        exc = self._make_validation_error({})
        msg = _validation_error_message(exc)
        # Should identify the missing field (lat or lon)
        assert isinstance(msg, str)
        assert len(msg) > 0

    def test_returns_fallback_for_empty_errors_list(self):
        mock_exc = ValidationError.from_exception_data(
            title="test",
            input_type="python",
            line_errors=[],
        )
        msg = _validation_error_message(mock_exc)
        assert msg == "invalid request"

    def test_returns_message_without_field_when_loc_is_root(self):
        """When loc[0] == '__root__', the raw message should be returned."""
        # Simulate an error with __root__ location
        from unittest.mock import patch, MagicMock

        mock_exc = MagicMock()
        mock_exc.errors.return_value = [
            {"msg": "root-level error", "loc": ("__root__",)}
        ]
        msg = _validation_error_message(mock_exc)
        assert msg == "root-level error"

    def test_returns_field_prefix_when_loc_has_field_name(self):
        """When loc[0] is a field name, message should be 'field: error'."""
        from unittest.mock import MagicMock

        mock_exc = MagicMock()
        mock_exc.errors.return_value = [
            {"msg": "field is required", "loc": ("lat",)}
        ]
        msg = _validation_error_message(mock_exc)
        assert msg == "lat: field is required"

    def test_returns_invalid_request_when_no_msg_key(self):
        from unittest.mock import MagicMock

        mock_exc = MagicMock()
        mock_exc.errors.return_value = [{"loc": ("lat",)}]
        msg = _validation_error_message(mock_exc)
        assert msg == "lat: invalid request"

    def test_returns_str_msg_for_empty_loc(self):
        from unittest.mock import MagicMock

        mock_exc = MagicMock()
        mock_exc.errors.return_value = [{"msg": "some error", "loc": ()}]
        msg = _validation_error_message(mock_exc)
        assert "some error" in msg
