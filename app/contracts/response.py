"""Response VOs (View Objects) for structuring API return data."""

from typing import Any

from pydantic import BaseModel, ConfigDict


# ----- User / Auth -----


class UserVO(BaseModel):
    """User information response."""

    id: int
    username: str
    email: str
    avatar_url: str | None
    is_active: bool
    created_at: str | None


class AuthTokenVO(BaseModel):
    """Login/refresh token response."""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"


class SendVerificationCodeMessageVO(BaseModel):
    """Verification code sent response."""

    message: str = "verification code sent"


# ----- Weather -----


class WeatherDataVO(BaseModel):
    """Weather API response data (OpenWeatherMap structure, allows extra fields)."""

    model_config = ConfigDict(extra="allow")

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)


# ----- Station -----


class StationVO(BaseModel):
    """Station information response."""

    number: int
    contract_name: str
    name: str
    address: str
    latitude: float
    longitude: float
    banking: bool
    bonus: bool
    bike_stands: int


class AvailabilityVO(BaseModel):
    """Station availability record response."""

    number: int
    available_bikes: int
    available_bike_stands: int
    status: str
    last_update: int
    timestamp: str | None
    requested_at: str | None
