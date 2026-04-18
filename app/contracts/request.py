"""Request DTOs (Data Transfer Objects) for API input validation and structuring."""

import re
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


# ----- User / Auth -----


class UserRegistrationRequestDTO(BaseModel):
    """User registration request body."""

    username: Annotated[str, Field(min_length=3, max_length=64)]
    email: Annotated[str, Field(max_length=120)]
    password: Annotated[str, Field(min_length=8, max_length=128)]
    avatar_url: str | None = None

    @field_validator("username", mode="before")
    @classmethod
    def username_strip(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator("username")
    @classmethod
    def username_pattern(cls, v: str) -> str:
        if not USERNAME_PATTERN.match(v):
            raise ValueError("username can only contain letters, numbers, '_', '-' and '.'.")
        return v

    @field_validator("email", mode="before")
    @classmethod
    def email_strip_lower(cls, v: str) -> str:
        return v.strip().lower() if isinstance(v, str) else v

    @field_validator("email")
    @classmethod
    def email_format(cls, v: str) -> str:
        if not EMAIL_PATTERN.match(v):
            raise ValueError("email format is invalid.")
        return v

    @field_validator("avatar_url")
    @classmethod
    def avatar_url_length(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        s = v.strip()
        if len(s) > 255:
            raise ValueError("avatar_url length must be <= 255.")
        return s if s else None


class LoginRequestDTO(BaseModel):
    """Login request body: identifier (username or email) + password."""

    identifier: Annotated[str, Field(min_length=1, max_length=120)]
    password: Annotated[str, Field(min_length=1)]

    @field_validator("identifier", mode="before")
    @classmethod
    def identifier_strip(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


class RefreshTokenRequestDTO(BaseModel):
    """Refresh token request body."""

    refresh_token: Annotated[str, Field(min_length=1)]

    @field_validator("refresh_token", mode="before")
    @classmethod
    def refresh_token_strip(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


class ActivateRequestDTO(BaseModel):
    """Account activation request body: identifier + 6-digit verification code."""

    identifier: Annotated[str, Field(min_length=1, max_length=120)]
    code: Annotated[str, Field(min_length=6, max_length=6)]

    @field_validator("identifier", mode="before")
    @classmethod
    def identifier_strip(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator("code", mode="before")
    @classmethod
    def code_strip(cls, v: str) -> str:
        # Accept numeric verification code, compatible with previous str(code).strip() behavior
        return str(v).strip()

    @field_validator("code")
    @classmethod
    def code_six_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("code must be a 6-digit string.")
        return v


class SendVerificationCodeRequestDTO(BaseModel):
    """Verification code sending request body: identifier (username or email)."""

    identifier: Annotated[str, Field(min_length=1, max_length=120)]

    @field_validator("identifier", mode="before")
    @classmethod
    def identifier_strip(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


class ActivateByTokenRequestDTO(BaseModel):
    """Account activation request body via email link token."""

    token: Annotated[str, Field(min_length=1)]

    @field_validator("token", mode="before")
    @classmethod
    def token_strip(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


# ----- Weather -----


class WeatherQueryDTO(BaseModel):
    """Weather query parameters: latitude and longitude."""

    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
