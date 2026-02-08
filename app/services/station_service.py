from datetime import datetime, timedelta
from typing import Any

from app.extensions import db
from app.models import Availability, Station


class StationNotFoundError(Exception):
    def __init__(self, message: str = "station not found") -> None:
        super().__init__(message)
        self.message = message


def _availability_to_dict(availability: Availability) -> dict[str, Any]:
    return {
        "number": availability.number,
        "available_bikes": availability.available_bikes,
        "available_bike_stands": availability.available_bike_stands,
        "status": availability.status,
        "last_update": availability.last_update,
        "timestamp": availability.timestamp.isoformat() if availability.timestamp else None,
        "requested_at": availability.requested_at.isoformat() if availability.requested_at else None,
    }


def _station_to_dict(station: Station) -> dict[str, Any]:
    return {
        "number": station.number,
        "contract_name": station.contract_name,
        "name": station.name,
        "address": station.address,
        "latitude": station.latitude,
        "longitude": station.longitude,
        "banking": station.banking,
        "bonus": station.bonus,
        "bike_stands": station.bike_stands,
    }


def list_stations() -> list[dict[str, Any]]:
    stations = db.session.execute(db.select(Station).order_by(Station.number)).scalars().all()
    return [_station_to_dict(station) for station in stations]


def get_recent_station_availability(number: int, lookback: timedelta = timedelta(days=1)) -> list[dict[str, Any]]:
    station = db.session.get(Station, number)
    if station is None:
        raise StationNotFoundError()

    since = datetime.now() - lookback
    stmt = (
        db.select(Availability)
        .where(Availability.number == number)
        .where(Availability.requested_at >= since)
        .order_by(Availability.requested_at.asc())
    )
    rows = db.session.execute(stmt).scalars().all()
    return [_availability_to_dict(availability) for availability in rows]
