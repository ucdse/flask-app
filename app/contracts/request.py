"""请求 DTO（Data Transfer Objects），用于 API 入参校验与结构化。"""

import re
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


# ----- User / Auth -----


class UserRegistrationRequestDTO(BaseModel):
    """用户注册请求体。"""

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
    """登录请求体：identifier（用户名或邮箱）+ password。"""

    identifier: Annotated[str, Field(min_length=1, max_length=120)]
    password: Annotated[str, Field(min_length=1)]

    @field_validator("identifier", mode="before")
    @classmethod
    def identifier_strip(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


class RefreshTokenRequestDTO(BaseModel):
    """刷新令牌请求体。"""

    refresh_token: Annotated[str, Field(min_length=1)]

    @field_validator("refresh_token", mode="before")
    @classmethod
    def refresh_token_strip(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


class ActivateRequestDTO(BaseModel):
    """激活账户请求体：identifier + 6 位验证码。"""

    identifier: Annotated[str, Field(min_length=1, max_length=120)]
    code: Annotated[str, Field(min_length=6, max_length=6)]

    @field_validator("identifier", mode="before")
    @classmethod
    def identifier_strip(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator("code", mode="before")
    @classmethod
    def code_strip(cls, v: str) -> str:
        # 接受数值类型验证码，兼容之前 str(code).strip() 的行为
        return str(v).strip()

    @field_validator("code")
    @classmethod
    def code_six_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("code must be a 6-digit string.")
        return v


class SendVerificationCodeRequestDTO(BaseModel):
    """发送验证码请求体：identifier（用户名或邮箱）。"""

    identifier: Annotated[str, Field(min_length=1, max_length=120)]

    @field_validator("identifier", mode="before")
    @classmethod
    def identifier_strip(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


class ActivateByTokenRequestDTO(BaseModel):
    """通过邮件链接 Token 激活请求体。"""

    token: Annotated[str, Field(min_length=1)]

    @field_validator("token", mode="before")
    @classmethod
    def token_strip(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


# ----- Weather -----


class WeatherQueryDTO(BaseModel):
    """天气查询参数：经纬度。"""

    lat: float = Field(..., description="纬度")
    lon: float = Field(..., description="经度")
