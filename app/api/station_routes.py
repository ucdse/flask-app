from datetime import datetime, timedelta

from flask import Blueprint, jsonify

from app.extensions import db
from app.models import Availability, Station

station_bp = Blueprint("station", __name__, url_prefix="/api/stations")


def availability_to_dict(a: Availability) -> dict:
    """将 Availability 模型转为可 JSON 序列化的字典。"""
    return {
        "number": a.number,
        "available_bikes": a.available_bikes,
        "available_bike_stands": a.available_bike_stands,
        "status": a.status,
        "last_update": a.last_update,
        "timestamp": a.timestamp.isoformat() if a.timestamp else None,
        "requested_at": a.requested_at.isoformat() if a.requested_at else None,
    }


def station_to_dict(s: Station) -> dict:
    """将 Station 模型转为可 JSON 序列化的字典。"""
    return {
        "number": s.number,
        "contract_name": s.contract_name,
        "name": s.name,
        "address": s.address,
        "latitude": s.latitude,
        "longitude": s.longitude,
        "banking": s.banking,
        "bonus": s.bonus,
        "bike_stands": s.bike_stands,
    }


@station_bp.get("/")
def list_stations():
    """返回所有站点信息。"""
    stations = db.session.execute(db.select(Station).order_by(Station.number)).scalars().all()
    data = [station_to_dict(s) for s in stations]
    return jsonify({"code": 0, "msg": "ok", "data": data}), 200


@station_bp.get("/<int:number>/availability")
def get_station_availability(number: int):
    """根据站点 number 返回最近一天内的 availability 记录。"""
    # 校验站点是否存在
    station = db.session.get(Station, number)
    if station is None:
        return jsonify({"code": 1, "msg": "station not found", "data": None}), 404

    # 最近一天：以当前时间为界，往前推 24 小时（与 Availability.requested_at 的 datetime.now() 一致，用本地时间）
    now = datetime.now()
    since = now - timedelta(days=1)

    stmt = (
        db.select(Availability)
        .where(Availability.number == number)
        .where(Availability.requested_at >= since)
        .order_by(Availability.requested_at.asc())
    )
    rows = db.session.execute(stmt).scalars().all()
    data = [availability_to_dict(a) for a in rows]

    return jsonify({"code": 0, "msg": "ok", "data": data}), 200
