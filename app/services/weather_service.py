"""Weather forecast service, retrieves weather data from database."""

from datetime import datetime, timezone
from typing import Any

from app.models.weather import WeatherForecast


class WeatherAPIError(Exception):
    """Weather forecast database query error."""
    def __init__(self, message: str = "weather API error", status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def get_weather() -> dict[str, Any]:
    """
    Retrieves Dublin weather forecast data from database.
    
    Returns:
        Weather forecast data dictionary, simulating original API structure, containing current and hourly
    """
    try:
        now = datetime.utcnow()
        # Query weather data for hours >= current hour, sorted by time, limit 6 records (current hour + next 5 hours)
        forecasts = WeatherForecast.query.filter(
            WeatherForecast.forecast_time >= now.replace(minute=0, second=0, microsecond=0)
        ).order_by(WeatherForecast.forecast_time.asc()).limit(6).all()
        
        if not forecasts:
            raise WeatherAPIError("No weather data available in database", 404)
            
        current = forecasts[0]
        
        # Assemble into format expected by frontend (simulating OneCall API)
        return {
            "current": {
                "dt": int(current.forecast_time.replace(tzinfo=timezone.utc).timestamp()),
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
                    "dt": int(f.forecast_time.replace(tzinfo=timezone.utc).timestamp()),
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
