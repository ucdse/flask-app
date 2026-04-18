"""API Request DTOs and Response VOs, based on Pydantic."""

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
    SendVerificationCodeMessageVO,
    UserVO,
    WeatherDataVO,
    StationVO,
    AvailabilityVO,
)

__all__ = [
    # Request DTOs
    "UserRegistrationRequestDTO",
    "LoginRequestDTO",
    "RefreshTokenRequestDTO",
    "ActivateRequestDTO",
    "SendVerificationCodeRequestDTO",
    "ActivateByTokenRequestDTO",
    "WeatherQueryDTO",
    # Response VOs
    "UserVO",
    "AuthTokenVO",
    "SendVerificationCodeMessageVO",
    "WeatherDataVO",
    "StationVO",
    "AvailabilityVO",
]
