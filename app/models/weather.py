from datetime import datetime

from app.extensions import db


class WeatherForecast(db.Model):
    """
    存储天气预报的小时级数据。
    主要用于缓存/存储都柏林未来的预报，避免频繁调用外部 API。
    """
    __tablename__ = "weather_forecast"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # 预报目标时间 (例如 2023-10-01 14:00:00)
    forecast_time = db.Column(db.DateTime, unique=True, index=True, nullable=False)
    
    # 摄氏度
    temperature = db.Column(db.Float, nullable=False)
    
    # 天气状态码 (如 800 代表晴朗)
    weather_code = db.Column(db.Integer, nullable=False)
    
    # 天气描述 (如 "scattered clouds")
    description = db.Column(db.String(100), nullable=True)
    
    # Optional: ICON code (e.g. "01d", "10n")
    icon = db.Column(db.String(20), nullable=True)

    # 追加的关键气象指标
    feels_like = db.Column(db.Float, nullable=True)
    pressure = db.Column(db.Integer, nullable=True)
    humidity = db.Column(db.Integer, nullable=True)
    uvi = db.Column(db.Float, nullable=True)
    clouds = db.Column(db.Integer, nullable=True)
    visibility = db.Column(db.Integer, nullable=True)
    wind_speed = db.Column(db.Float, nullable=True)
    wind_deg = db.Column(db.Integer, nullable=True)
    pop = db.Column(db.Float, nullable=True, default=0.0)

    # Scraper 抓取这条数据的时间
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
