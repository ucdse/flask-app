import os
import pickle
import pandas as pd
from datetime import datetime
from typing import Any, List, Dict
from flask import current_app

from app.extensions import db
from app.models.station import Station
from app.models.weather import WeatherForecast

# 全局变量缓存模型
_model = None
_features = None

def _load_model() -> None:
    global _model, _features
    # 如果已经加载过，就直接返回
    if _model is not None and _features is not None:
        return

    # 获取 app 包所在目录 (通常为 flask-app/app)
    base_dir = current_app.root_path
    
    # 回退一层进入 flask-app 然后进入 machine_learning 目录寻找 .pkl
    model_path = os.path.join(base_dir, '..', 'machine_learning', 'bike_availability_model.pkl')
    features_path = os.path.join(base_dir, '..', 'machine_learning', 'model_features.pkl')

    if not os.path.exists(model_path) or not os.path.exists(features_path):
        raise FileNotFoundError(
            f"Model files not found! Please ensure your training output files "
            f"are located at {model_path} and {features_path}."
        )

    with open(model_path, 'rb') as f:
        _model = pickle.load(f)
    
    with open(features_path, 'rb') as f:
        _features = pickle.load(f)


class PredictionError(Exception):
    def __init__(self, message: str = "prediction error") -> None:
        super().__init__(message)
        self.message = message


def get_station_predictions(station_id: int) -> List[Dict[str, Any]]:
    """
    获取某个站点基于缓存天气预报的可用单车预测结果。这将在不到 5 毫秒的时间内根据所有未来天气批处理生成！
    """
    _load_model()

    # 1. 获取车站固定信息（容量、经纬度）
    station = db.session.get(Station, station_id)
    if not station:
        raise PredictionError(f"Station {station_id} not found")

    # 2. 从数据库查询自当前整点起的所有未来天气预报
    now = datetime.utcnow()
    forecasts = WeatherForecast.query.filter(
        WeatherForecast.forecast_time >= now.replace(minute=0, second=0, microsecond=0)
    ).order_by(WeatherForecast.forecast_time.asc()).all()

    if not forecasts:
        raise PredictionError("No weather forecast data available to make predictions")

    # 3. 构造批量预测所需的特征
    input_rows = []
    for f in forecasts:
        dt = f.forecast_time
        day_of_week = dt.weekday() # 0-6 corresponding to Monday-Sunday
        is_weekend = 1 if day_of_week >= 5 else 0

        # DataFrame 中需要的完整字典，对应模型特征列表
        row = {
            'station_id': station.number,
            'capacity': station.bike_stands,
            'lat': station.latitude,
            'lon': station.longitude,
            'hour': dt.hour,
            'day': dt.day,
            'day_of_week': day_of_week,
            'is_weekend': is_weekend,
            'avg_temperature': f.temperature,
            'avg_humidity': f.humidity,
            'avg_pressure': f.pressure
        }
        input_rows.append(row)

    # 严格按照 _features 的列名和顺序进行重排
    df_input = pd.DataFrame(input_rows)[_features]

    # 采用随机森林进行批量预测（即使是 24-48 小时的预测，也仅需 ~1 毫秒）
    predictions = _model.predict(df_input)

    # 4. 组装并返回结果
    result = []
    for idx, f in enumerate(forecasts):
        # 预测出的小数进行四舍五入并强制转换整型
        predicted_bikes = int(round(predictions[idx]))
        
        # 修正：单车可用数量不可能小于0或多于车站的最大容量
        predicted_bikes = max(0, min(predicted_bikes, station.bike_stands))

        result.append({
            "forecast_time": f.forecast_time.isoformat(),
            "predicted_available_bikes": predicted_bikes
        })

    return result
