"""Weather forecast API routes."""

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from app.contracts import WeatherDataVO, WeatherQueryDTO
from app.services.weather_service import WeatherAPIError, get_weather

weather_bp = Blueprint("weather", __name__, url_prefix="/api/weather")


def _validation_error_message(exc: ValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "invalid request"
    first = errors[0]
    msg = first.get("msg", "invalid request")
    loc = first.get("loc", ())
    if len(loc) >= 1 and loc[0] != "__root__":
        return f"{loc[0]}: {msg}"
    return str(msg)


@weather_bp.get("")
def get_weather_forecast():
    """
    Get weather forecast (unified forecast).

    Returns:
        JSON response containing weather forecast data.
    """
    try:
        raw_data = get_weather()
        data = WeatherDataVO.model_validate(raw_data).model_dump()
        return jsonify({"code": 0, "msg": "ok", "data": data}), 200
    except WeatherAPIError as exc:
        return jsonify({
            "code": 50001,
            "msg": exc.message,
            "data": None
        }), exc.status_code
