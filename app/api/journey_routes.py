from flask import Blueprint, jsonify, request
from app.services.journey_service import find_best_route

journey_bp = Blueprint("journey", __name__, url_prefix="/api/journey")

@journey_bp.post("/plan")
def plan_journey():
    """
    Plan a journey.
    Expected JSON Payload:
    {
        "start": { "lat": 53.34, "lon": -6.26 },
        "end":   { "lat": 53.33, "lon": -6.25 }
    }
    """
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"code": 400, "msg": "Missing JSON body", "data": None}), 400

    # Extract coordinates safely
    try:
        start_lat = payload["start"]["lat"]
        start_lon = payload["start"]["lon"]
        end_lat = payload["end"]["lat"]
        end_lon = payload["end"]["lon"]
    except (KeyError, TypeError):
        return jsonify({"code": 400, "msg": "Invalid format. Use {start: {lat, lon}, end: {lat, lon}}", "data": None}), 400

    # Call the logic
    result = find_best_route(start_lat, start_lon, end_lat, end_lon)

    if not result:
        return jsonify({"code": 404, "msg": "No suitable stations found", "data": None}), 404

    return jsonify({"code": 0, "msg": "ok", "data": result}), 200