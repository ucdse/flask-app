"""天气预报服务，从数据库获取天气数据。"""

from datetime import datetime
from typing import Any

from app.models.weather import WeatherForecast


class WeatherAPIError(Exception):
    """天气预报数据库查询错误。"""
    def __init__(self, message: str = "weather API error", status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def get_weather() -> dict[str, Any]:
    """
    从数据库获取都柏林未来的天气预报数据。
    
    Returns:
        天气预报数据字典，模拟原 API 的结构，包含 current 和 hourly
    """
    try:
        now = datetime.utcnow()
        # 查询大于等于当前小时的天气，按时间排序，取前 6 条 (包含当前小时 + 未来5小时)
        forecasts = WeatherForecast.query.filter(
            WeatherForecast.forecast_time >= now.replace(minute=0, second=0, microsecond=0)
        ).order_by(WeatherForecast.forecast_time.asc()).limit(6).all()
        
        if not forecasts:
            return {"current": {}, "hourly": []}
            
        current = forecasts[0]
        
        # 组装为前端期望的格式 (模拟 OneCall API)
        return {
            "current": {
                "dt": int(current.forecast_time.timestamp()),
                "temp": current.temperature,
                "feels_like": current.feels_like,
                "pressure": current.pressure,
                "humidity": current.humidity,
                "uvi": current.uvi,
                "clouds": current.clouds,
                "visibility": current.visibility,
                "wind_speed": current.wind_speed,
                "wind_deg": current.wind_deg,
                "weather": [
                    {
                        "id": current.weather_code,
                        "description": current.description,
                        "icon": current.icon
                    }
                ]
            },
            "hourly": [
                {
                    "dt": int(f.forecast_time.timestamp()),
                    "temp": f.temperature,
                    "feels_like": f.feels_like,
                    "pressure": f.pressure,
                    "humidity": f.humidity,
                    "uvi": f.uvi,
                    "clouds": f.clouds,
                    "visibility": f.visibility,
                    "wind_speed": f.wind_speed,
                    "wind_deg": f.wind_deg,
                    "pop": f.pop,
                    "weather": [
                        {
                            "id": f.weather_code,
                            "description": f.description,
                            "icon": f.icon
                        }
                    ]
                }
                for f in forecasts
            ]
        }
            
    except Exception as e:
        error_msg = f"Failed to fetch weather data from database: {str(e)}"
        raise WeatherAPIError(error_msg, 500)
