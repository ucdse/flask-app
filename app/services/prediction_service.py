import os
import pickle
import pandas as pd
from datetime import datetime
from typing import Any, List, Dict
from flask import current_app

from app.extensions import db
from app.models.station import Station
from app.models.weather import WeatherForecast

# Global variable to cache the model
_model = None
_features = None

def _load_model() -> None:
    global _model, _features
    # If already loaded, return directly
    if _model is not None and _features is not None:
        return

    # Get the directory where the app package is located (usually flask-app/app)
    base_dir = current_app.root_path
    
    # Go back one level to flask-app then enter machine_learning directory to find .pkl
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
    Get available bike predictions for a station based on cached weather forecasts.
    """
    _load_model()

    # 1. Get station fixed information (capacity, lat/lon)
    station = db.session.get(Station, station_id)
    if not station:
        raise PredictionError(f"Station {station_id} not found")

    # 2. Query all future weather forecasts from the current hour from the database
    now = datetime.utcnow()
    forecasts = WeatherForecast.query.filter(
        WeatherForecast.forecast_time >= now.replace(minute=0, second=0, microsecond=0)
    ).order_by(WeatherForecast.forecast_time.asc()).all()

    if not forecasts:
        raise PredictionError("No weather forecast data available to make predictions")

    # 3. Construct features required for batch prediction
    input_rows = []
    for f in forecasts:
        dt = f.forecast_time
        day_of_week = dt.weekday() # 0-6 corresponding to Monday-Sunday
        is_weekend = 1 if day_of_week >= 5 else 0

        # Complete dictionary required in DataFrame, corresponding to model feature list
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

    # Reorder strictly according to _features column names and order
    df_input = pd.DataFrame(input_rows)[_features]

    # Use random forest for batch prediction (even for 24-48 hour predictions, it takes only ~1 millisecond)
    predictions = _model.predict(df_input)

    # 4. Assemble and return results
    result = []
    for idx, f in enumerate(forecasts):
        # Round the predicted decimals and forcefully convert to integer
        predicted_bikes = int(round(predictions[idx]))
        
        # Correction: available bikes count cannot be less than 0 or more than station's maximum capacity
        predicted_bikes = max(0, min(predicted_bikes, station.bike_stands))

        result.append({
            "forecast_time": f.forecast_time.isoformat(),
            "predicted_available_bikes": predicted_bikes
        })

    return result
