"""天气预报API路由。"""

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
    获取天气预报。

    查询参数:
        lat (float): 纬度，必填
        lon (float): 经度，必填

    返回:
        JSON响应，包含天气预报数据
    """
    raw = {
        "lat": request.args.get("lat"),
        "lon": request.args.get("lon"),
    }
    try:
        dto = WeatherQueryDTO.model_validate(raw)
    except ValidationError as exc:
        return jsonify({
            "code": 40001,
            "msg": _validation_error_message(exc),
            "data": None
        }), 400

    try:
        raw_data = get_weather(dto.lat, dto.lon)
        data = WeatherDataVO.model_validate(raw_data).model_dump()
        return jsonify({"code": 0, "msg": "ok", "data": data}), 200
    except WeatherAPIError as exc:
        return jsonify({
            "code": 50001,
            "msg": exc.message,
            "data": None
        }), exc.status_code
