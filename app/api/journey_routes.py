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

            # Explicitly validate that both 'lat' and 'lon' exist in the payload
            if "lat" not in start_node or "lon" not in start_node or "lat" not in end_node or "lon" not in end_node:
                return jsonify({
                    "code": 400,
                    "msg": "Bad Request: Both 'start' and 'end' must contain 'lat' and 'lon' keys.",
                    "data": None
                }), 400

            start_lat = payload["start"]["lat"]
            start_lon = payload["start"]["lon"]
            end_lat = payload["end"]["lat"]
            end_lon = payload["end"]["lon"]

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