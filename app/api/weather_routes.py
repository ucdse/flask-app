"""天气预报API路由。"""

from flask import Blueprint, jsonify, request

from app.services.weather_service import WeatherAPIError, get_weather

weather_bp = Blueprint("weather", __name__, url_prefix="/api/weather")


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
    # 获取查询参数
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    
    # 验证参数
    if lat is None or lon is None:
        return jsonify({
            "code": 40001,
            "msg": "缺少必需参数: lat 和 lon",
            "data": None
        }), 400
    
    try:
        data = get_weather(lat, lon)
        return jsonify({
            "code": 0,
            "msg": "ok",
            "data": data
        }), 200
    except WeatherAPIError as exc:
        return jsonify({
            "code": 50001,
            "msg": exc.message,
            "data": None
        }), exc.status_code
