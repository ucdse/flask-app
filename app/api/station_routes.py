from flask import Blueprint, jsonify

from app.contracts import AvailabilityVO, StationVO
from app.services.station_service import (
    StationNotFoundError,
    get_recent_station_availability,
    list_stations as list_stations_service,
    get_all_stations_latest_availability
)
from app.services.prediction_service import get_station_predictions, PredictionError

station_bp = Blueprint("station", __name__, url_prefix="/api/stations")


@station_bp.get("/")
def list_stations():
    """Return information for all stations."""
    raw_list = list_stations_service()
    data = [StationVO.model_validate(s).model_dump() for s in raw_list]
    return jsonify({"code": 0, "msg": "ok", "data": data}), 200


@station_bp.get("/<int:number>/availability")
def get_station_availability(number: int):
    """Return availability records for the given station number within the last day."""
    try:
        raw_list = get_recent_station_availability(number)
    except StationNotFoundError as exc:
        return jsonify({"code": 1, "msg": exc.message, "data": None}), 404
    data = [AvailabilityVO.model_validate(a).model_dump() for a in raw_list]
    return jsonify({"code": 0, "msg": "ok", "data": data}), 200

@station_bp.get("/status")
def get_all_stations_status():
    """Return the latest real-time status for all stations."""
    raw_list = get_all_stations_latest_availability()
    
    data = [AvailabilityVO.model_validate(a).model_dump() for a in raw_list]
    return jsonify({"code": 0, "msg": "ok", "data": data}), 200

@station_bp.get("/<int:number>/prediction")
def get_station_prediction(number: int):
    """Return the predicted available bikes for this station over a future period."""
    try:
        data = get_station_predictions(number)
        return jsonify({"code": 0, "msg": "ok", "data": data}), 200
    except PredictionError as exc:
        return jsonify({"code": 1, "msg": exc.message, "data": None}), 400
    except Exception as exc:
        return jsonify({"code": 1, "msg": "Prediction service unavailable", "data": None, "error": str(exc)}), 500
