"""响应 VO（View Objects），用于 API 返回数据结构化。"""

from typing import Any

from pydantic import BaseModel, ConfigDict


# ----- User / Auth -----


class UserVO(BaseModel):
    """用户信息响应。"""

    id: int
    username: str
    email: str
    avatar_url: str | None
    is_active: bool
    created_at: str | None


class AuthTokenVO(BaseModel):
    """登录/刷新令牌响应。"""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"


class SendVerificationCodeMessageVO(BaseModel):
    """发送验证码成功响应。"""

    message: str = "verification code sent"


# ----- Weather -----


class WeatherDataVO(BaseModel):
    """天气 API 返回数据（OpenWeatherMap 结构，允许额外字段）。"""

    model_config = ConfigDict(extra="allow")

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)


# ----- Station -----


class StationVO(BaseModel):
    """站点信息响应。"""

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
    """站点可用性记录响应。"""

    number: int
    available_bikes: int
    available_bike_stands: int
    status: str
    last_update: int
    timestamp: str | None
    requested_at: str | None
