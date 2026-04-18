from datetime import datetime

from app.extensions import db


class WeatherForecast(db.Model):
    """
    Stores hourly weather forecast data.
    Mainly used for caching/storing Dublin's future forecasts to avoid frequently calling external APIs.
    """
    __tablename__ = "weather_forecast"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Forecast target time (e.g. 2023-10-01 14:00:00)
    forecast_time = db.Column(db.DateTime, unique=True, index=True, nullable=False)
    
    # Temperature in Celsius
    temperature = db.Column(db.Float, nullable=False)
    
    # Weather status code (e.g. 800 means clear)
    weather_code = db.Column(db.Integer, nullable=False)
    
    # Weather description (e.g. "scattered clouds")
    description = db.Column(db.String(100), nullable=True)
    
    # Optional: ICON code (e.g. "01d", "10n")
    icon = db.Column(db.String(20), nullable=True)

    # Additional key meteorological indicators
    feels_like = db.Column(db.Float, nullable=True)
    pressure = db.Column(db.Integer, nullable=True)
    humidity = db.Column(db.Integer, nullable=True)
    uvi = db.Column(db.Float, nullable=True)
    clouds = db.Column(db.Integer, nullable=True)
    visibility = db.Column(db.Integer, nullable=True)
    wind_speed = db.Column(db.Float, nullable=True)
    wind_deg = db.Column(db.Integer, nullable=True)
    pop = db.Column(db.Float, nullable=True, default=0.0)

    # Time when this data was scraped
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "forecast_time": self.forecast_time.isoformat() if self.forecast_time else None,
            "temperature": self.temperature,
            "weather_code": self.weather_code,
            "description": self.description,
            "icon": self.icon,
            "feels_like": self.feels_like,
            "pressure": self.pressure,
            "humidity": self.humidity,
            "uvi": self.uvi,
            "clouds": self.clouds,
            "visibility": self.visibility,
            "wind_speed": self.wind_speed,
            "wind_deg": self.wind_deg,
            "pop": self.pop,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
        }
