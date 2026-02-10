"""天气预报服务，调用 OpenWeatherMap API 获取天气数据。"""

import requests
from typing import Any

from config import OPENWEATHER_API_BASE_URL, OPENWEATHER_API_KEY


class WeatherAPIError(Exception):
    """天气预报API调用错误。"""
    def __init__(self, message: str = "weather API error", status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def get_weather(lat: float, lon: float) -> dict[str, Any]:
    """
    根据经纬度获取天气预报数据。
    
    Args:
        lat: 纬度
        lon: 经度
    
    Returns:
        天气预报数据字典
    
    Raises:
        WeatherAPIError: 当API调用失败时抛出
    """
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHER_API_KEY,
        "exclude": "minutely",
    }
    
    try:
        response = requests.get(OPENWEATHER_API_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to fetch weather data: {str(e)}"
        status_code = 500
        if hasattr(e.response, 'status_code'):
            status_code = e.response.status_code
        raise WeatherAPIError(error_msg, status_code)
