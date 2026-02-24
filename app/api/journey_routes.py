import googlemaps

from flask import Blueprint, jsonify, request
from app.services.journey_service import find_best_route

from config import GOOGLE_MAPS_API_KEY

journey_bp = Blueprint("journey", __name__, url_prefix="/api/journey")

# Initialise Client
gmaps = None
if GOOGLE_MAPS_API_KEY:
    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
else:
    print("WARNING: GOOGLE_MAPS_API_KEY not found in config.")

@journey_bp.post("/plan")
def plan_journey():
    """
    Plan a journey using either coordinates or text addresses.

    Expected JSON Payload (Option A - Text):
    {
        "start_address": "O'Connell Street, Dublin",
        "end_address": "UCD Belfield"
    }

    Expected JSON Payload (Option B - Coords, for testing):
    {
        "start": { "lat": 53.34, "lon": -6.26 },
        "end":   { "lat": 53.33, "lon": -6.25 }
    }
    """
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"code": 400, "msg": "Missing JSON body", "data": None}), 400

    start_lat, start_lon = None, None
    end_lat, end_lon = None, None

    try:
        # --- PATH A: User provided text addresses (Requires Google Maps) ---
        if "start_address" in payload and "end_address" in payload:
            if not gmaps:
                return jsonify({"code": 500, "msg": "Server Geocoding not configured", "data": None}), 500

            # 1. Geocode Start Address
            start_result = gmaps.geocode(payload["start_address"])
            if not start_result:
                return jsonify(
                    {"code": 404, "msg": f"Could not find location: {payload['start_address']}", "data": None}), 404

            start_loc = start_result[0]['geometry']['location']
            start_lat, start_lon = start_loc['lat'], start_loc['lng']

            # 2. Geocode End Address
            end_result = gmaps.geocode(payload["end_address"])
            if not end_result:
                return jsonify(
                    {"code": 404, "msg": f"Could not find location: {payload['end_address']}", "data": None}), 404

            end_loc = end_result[0]['geometry']['location']
            end_lat, end_lon = end_loc['lat'], end_loc['lng']

        # --- PATH B: User provided raw coordinates (Legacy/Testing) ---
        elif "start" in payload and "end" in payload:

            start_node = payload["start"]
            end_node = payload["end"]

            # 1. Type Validation: Ensure both nodes are actually dictionaries
            if not isinstance(start_node, dict) or not isinstance(end_node, dict):
                return jsonify({
                    "code": 400,
                    "msg": "Bad Request: 'start' and 'end' must be JSON objects containing coordinates.",
                    "data": None
                }), 400

            # 2. Key Validation: Explicitly validate that both 'lat' and 'lon' exist
            if "lat" not in start_node or "lon" not in start_node or "lat" not in end_node or "lon" not in end_node:
                return jsonify({
                    "code": 400,
                    "msg": "Bad Request: Both 'start' and 'end' must contain 'lat' and 'lon' keys.",
                    "data": None
                }), 400

            # 3. Value Type Validation: Ensure the values can be converted to floats
            try:
                start_lat = float(start_node["lat"])
                start_lon = float(start_node["lon"])
                end_lat = float(end_node["lat"])
                end_lon = float(end_node["lon"])
            except (ValueError, TypeError):
                return jsonify({
                    "code": 400,
                    "msg": "Bad Request: Coordinate values must be numbers.",
                    "data": None
                }), 400

            # 4. Boundary Validation: Ensure coordinates are geographically valid
            if not (-90 <= start_lat <= 90) or not (-180 <= start_lon <= 180) or \
                    not (-90 <= end_lat <= 90) or not (-180 <= end_lon <= 180):
                return jsonify({
                    "code": 400,
                    "msg": "Bad Request: Latitude must be between -90 and 90, and longitude between -180 and 180.",
                    "data": None
                }), 400

        else:
            return jsonify({"code": 400, "msg": "Please provide 'start_address'/'end_address' OR 'start'/'end' coords",
                            "data": None}), 400

    except Exception as e:
        return jsonify({"code": 500, "msg": f"Error processing request: {str(e)}", "data": None}), 500

    # --- CORE LOGIC: Find the stations ---
     # Now that we have lat/lon (from either path), we call your service
    result = find_best_route(start_lat, start_lon, end_lat, end_lon)

    if not result:
        return jsonify({"code": 404, "msg": "No suitable stations found nearby", "data": None}), 404

    # We add the resolved coordinates to the response so the frontend knows
    # exactly where the Geocoder placed the pins.
    response_data = {
        "route_info": result,
        "search_context": {
            "start_resolved": {"lat": start_lat, "lon": start_lon},
            "end_resolved": {"lat": end_lat, "lon": end_lon}
        }
    }

    return jsonify({"code": 0, "msg": "ok", "data": response_data}), 200