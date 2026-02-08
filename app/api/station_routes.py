from flask import Blueprint, jsonify

from app.services.station_service import (
    StationNotFoundError,
    get_recent_station_availability,
    list_stations as list_stations_service,
)

station_bp = Blueprint("station", __name__, url_prefix="/api/stations")


@station_bp.get("/")
def list_stations():
    """返回所有站点信息。"""
    data = list_stations_service()
    return jsonify({"code": 0, "msg": "ok", "data": data}), 200


@station_bp.get("/<int:number>/availability")
def get_station_availability(number: int):
    """根据站点 number 返回最近一天内的 availability 记录。"""
    try:
        data = get_recent_station_availability(number)
    except StationNotFoundError as exc:
        return jsonify({"code": 1, "msg": exc.message, "data": None}), 404
    return jsonify({"code": 0, "msg": "ok", "data": data}), 200
