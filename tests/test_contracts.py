"""
Unit tests for Pydantic request DTOs and response VOs.

Verifies field-level validation rules, strip/lowercase transforms, and
correct rejection of invalid inputs.
"""

import pytest
from pydantic import ValidationError

from app.contracts.request import (
    ActivateByTokenRequestDTO,
    ActivateRequestDTO,
    LoginRequestDTO,
    RefreshTokenRequestDTO,
    SendVerificationCodeRequestDTO,
    UserRegistrationRequestDTO,
    WeatherQueryDTO,
)
from app.contracts.response import (
    AuthTokenVO,
    AvailabilityVO,
    SendVerificationCodeMessageVO,
    StationVO,
    UserVO,
    WeatherDataVO,
)


# ---------------------------------------------------------------------------
# UserRegistrationRequestDTO
# ---------------------------------------------------------------------------


class TestUserRegistrationRequestDTO:
    VALID = {
        "username": "alice",
        "email": "alice@example.com",
        "password": "secret99",
    }

    def test_valid_payload_accepted(self):
        dto = UserRegistrationRequestDTO.model_validate(self.VALID)
        assert dto.username == "alice"
        assert dto.email == "alice@example.com"

    def test_username_stripped_of_whitespace(self):
        dto = UserRegistrationRequestDTO.model_validate(
            {**self.VALID, "username": "  alice  "}
        )
        assert dto.username == "alice"

    def test_email_lowercased_and_stripped(self):
        dto = UserRegistrationRequestDTO.model_validate(
            {**self.VALID, "email": "  ALICE@EXAMPLE.COM  "}
        )
        assert dto.email == "alice@example.com"

    def test_avatar_url_none_by_default(self):
        dto = UserRegistrationRequestDTO.model_validate(self.VALID)
        assert dto.avatar_url is None

    def test_avatar_url_stripped(self):
        dto = UserRegistrationRequestDTO.model_validate(
            {**self.VALID, "avatar_url": "  http://example.com/img.png  "}
        )
        assert dto.avatar_url == "http://example.com/img.png"

    def test_avatar_url_too_long_raises(self):
        with pytest.raises(ValidationError):
            UserRegistrationRequestDTO.model_validate(
                {**self.VALID, "avatar_url": "x" * 256}
            )

    def test_username_too_short_raises(self):
        with pytest.raises(ValidationError):
            UserRegistrationRequestDTO.model_validate(
                {**self.VALID, "username": "ab"}
            )

    def test_username_too_long_raises(self):
        with pytest.raises(ValidationError):
            UserRegistrationRequestDTO.model_validate(
                {**self.VALID, "username": "a" * 65}
            )

    def test_username_invalid_chars_raises(self):
        with pytest.raises(ValidationError):
            UserRegistrationRequestDTO.model_validate(
                {**self.VALID, "username": "alice!@#"}
            )

    def test_password_too_short_raises(self):
        with pytest.raises(ValidationError):
            UserRegistrationRequestDTO.model_validate(
                {**self.VALID, "password": "short"}
            )

    def test_email_invalid_format_raises(self):
        with pytest.raises(ValidationError):
            UserRegistrationRequestDTO.model_validate(
                {**self.VALID, "email": "not-an-email"}
            )

    def test_missing_required_fields_raises(self):
        with pytest.raises(ValidationError):
            UserRegistrationRequestDTO.model_validate({})

    def test_username_with_dots_and_dashes_accepted(self):
        dto = UserRegistrationRequestDTO.model_validate(
            {**self.VALID, "username": "ali.ce-123_xyz"}
        )
        assert dto.username == "ali.ce-123_xyz"

    def test_empty_avatar_url_becomes_none(self):
        dto = UserRegistrationRequestDTO.model_validate(
            {**self.VALID, "avatar_url": ""}
        )
        assert dto.avatar_url is None

    def test_whitespace_only_avatar_url_becomes_none(self):
        dto = UserRegistrationRequestDTO.model_validate(
            {**self.VALID, "avatar_url": "   "}
        )
        assert dto.avatar_url is None


# ---------------------------------------------------------------------------
# LoginRequestDTO
# ---------------------------------------------------------------------------


class TestLoginRequestDTO:
    def test_valid_payload_accepted(self):
        dto = LoginRequestDTO.model_validate(
            {"identifier": "alice", "password": "secret99"}
        )
        assert dto.identifier == "alice"

    def test_identifier_stripped(self):
        dto = LoginRequestDTO.model_validate(
            {"identifier": "  alice  ", "password": "p"}
        )
        assert dto.identifier == "alice"

    def test_missing_identifier_raises(self):
        with pytest.raises(ValidationError):
            LoginRequestDTO.model_validate({"password": "p"})

    def test_missing_password_raises(self):
        with pytest.raises(ValidationError):
            LoginRequestDTO.model_validate({"identifier": "alice"})

    def test_empty_identifier_raises(self):
        with pytest.raises(ValidationError):
            LoginRequestDTO.model_validate({"identifier": "", "password": "p"})


# ---------------------------------------------------------------------------
# ActivateRequestDTO
# ---------------------------------------------------------------------------


class TestActivateRequestDTO:
    def test_valid_code_accepted(self):
        dto = ActivateRequestDTO.model_validate(
            {"identifier": "alice", "code": "123456"}
        )
        assert dto.code == "123456"

    def test_code_stripped(self):
        dto = ActivateRequestDTO.model_validate(
            {"identifier": "alice", "code": " 123456 "}
        )
        assert dto.code == "123456"

    def test_code_too_short_raises(self):
        with pytest.raises(ValidationError):
            ActivateRequestDTO.model_validate({"identifier": "alice", "code": "12345"})

    def test_code_too_long_raises(self):
        with pytest.raises(ValidationError):
            ActivateRequestDTO.model_validate(
                {"identifier": "alice", "code": "1234567"}
            )

    def test_non_digit_code_raises(self):
        with pytest.raises(ValidationError):
            ActivateRequestDTO.model_validate(
                {"identifier": "alice", "code": "12345a"}
            )

    def test_numeric_code_converted_to_string(self):
        """Integer codes should be coerced via str(v).strip()."""
        dto = ActivateRequestDTO.model_validate({"identifier": "alice", "code": 123456})
        assert dto.code == "123456"


# ---------------------------------------------------------------------------
# SendVerificationCodeRequestDTO
# ---------------------------------------------------------------------------


class TestSendVerificationCodeRequestDTO:
    def test_valid_identifier_accepted(self):
        dto = SendVerificationCodeRequestDTO.model_validate({"identifier": "alice"})
        assert dto.identifier == "alice"

    def test_identifier_stripped(self):
        dto = SendVerificationCodeRequestDTO.model_validate(
            {"identifier": "  alice@example.com  "}
        )
        assert dto.identifier == "alice@example.com"

    def test_empty_identifier_raises(self):
        with pytest.raises(ValidationError):
            SendVerificationCodeRequestDTO.model_validate({"identifier": ""})


# ---------------------------------------------------------------------------
# RefreshTokenRequestDTO
# ---------------------------------------------------------------------------


class TestRefreshTokenRequestDTO:
    def test_valid_token_accepted(self):
        dto = RefreshTokenRequestDTO.model_validate({"refresh_token": "some.jwt.token"})
        assert dto.refresh_token == "some.jwt.token"

    def test_token_stripped(self):
        dto = RefreshTokenRequestDTO.model_validate(
            {"refresh_token": "  some.jwt.token  "}
        )
        assert dto.refresh_token == "some.jwt.token"

    def test_empty_token_raises(self):
        with pytest.raises(ValidationError):
            RefreshTokenRequestDTO.model_validate({"refresh_token": ""})


# ---------------------------------------------------------------------------
# ActivateByTokenRequestDTO
# ---------------------------------------------------------------------------


class TestActivateByTokenRequestDTO:
    def test_valid_token_accepted(self):
        dto = ActivateByTokenRequestDTO.model_validate({"token": "abc123"})
        assert dto.token == "abc123"

    def test_token_stripped(self):
        dto = ActivateByTokenRequestDTO.model_validate({"token": "  abc123  "})
        assert dto.token == "abc123"

    def test_empty_token_raises(self):
        with pytest.raises(ValidationError):
            ActivateByTokenRequestDTO.model_validate({"token": ""})


# ---------------------------------------------------------------------------
# WeatherQueryDTO
# ---------------------------------------------------------------------------


class TestWeatherQueryDTO:
    def test_valid_coords_accepted(self):
        dto = WeatherQueryDTO.model_validate({"lat": 53.34, "lon": -6.26})
        assert dto.lat == 53.34
        assert dto.lon == -6.26

    def test_missing_lat_raises(self):
        with pytest.raises(ValidationError):
            WeatherQueryDTO.model_validate({"lon": -6.26})

    def test_missing_lon_raises(self):
        with pytest.raises(ValidationError):
            WeatherQueryDTO.model_validate({"lat": 53.34})


# ---------------------------------------------------------------------------
# Response VOs
# ---------------------------------------------------------------------------


class TestUserVO:
    def test_valid_data_accepted(self):
        vo = UserVO.model_validate(
            {
                "id": 1,
                "username": "alice",
                "email": "alice@example.com",
                "avatar_url": None,
                "is_active": True,
                "created_at": "2024-01-01T00:00:00",
            }
        )
        assert vo.id == 1
        assert vo.is_active is True


class TestAuthTokenVO:
    def test_valid_token_vo(self):
        vo = AuthTokenVO.model_validate(
            {
                "access_token": "access",
                "refresh_token": "refresh",
                "expires_in": 900,
                "token_type": "Bearer",
            }
        )
        assert vo.token_type == "Bearer"

    def test_default_token_type_is_bearer(self):
        vo = AuthTokenVO.model_validate(
            {
                "access_token": "access",
                "refresh_token": "refresh",
                "expires_in": 900,
            }
        )
        assert vo.token_type == "Bearer"


class TestStationVO:
    def test_valid_station_vo(self):
        vo = StationVO.model_validate(
            {
                "number": 42,
                "contract_name": "dublin",
                "name": "Test St",
                "address": "1 Test Rd",
                "latitude": 53.34,
                "longitude": -6.26,
                "banking": True,
                "bonus": False,
                "bike_stands": 20,
            }
        )
        assert vo.number == 42


class TestAvailabilityVO:
    def test_valid_availability_vo(self):
        vo = AvailabilityVO.model_validate(
            {
                "number": 42,
                "available_bikes": 5,
                "available_bike_stands": 15,
                "status": "OPEN",
                "last_update": 1700000000000,
                "timestamp": "2024-01-01T10:00:00",
                "requested_at": "2024-01-01T10:00:00",
            }
        )
        assert vo.available_bikes == 5


class TestWeatherDataVO:
    def test_extra_fields_allowed(self):
        """WeatherDataVO uses extra='allow' so arbitrary keys pass through."""
        vo = WeatherDataVO.model_validate(
            {"current": {"temp": 15}, "hourly": [], "extra_key": "should be ok"}
        )
        assert vo.model_extra.get("extra_key") == "should be ok"


class TestSendVerificationCodeMessageVO:
    def test_default_message(self):
        vo = SendVerificationCodeMessageVO.model_validate({})
        assert vo.message == "verification code sent"
