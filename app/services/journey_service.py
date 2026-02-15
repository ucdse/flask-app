from app.extensions import (db)
from app.models import Station, Availability
from app.services.station_service import list_stations
from app.utils.calculateDistance import calculate_distance

def find_best_route(start_lat, start_lon, end_lat, end_lon):
    """
    Finds the best start and end stations for a journey.
    """
    # 1. Get all stations
    # Ideally, we want the station AND its latest availability
    stations = db.session.query(Station).all()

    best_start_station = None
    min_start_dist = float('inf')  # Infinity

    best_end_station = None
    min_end_dist = float('inf')

    for station in stations:
        # Get latest availability for this station
        # This is a simple way; for production, we would join tables to be faster
        av = db.session.query(Availability) \
            .filter(Availability.number == station.number) \
            .order_by(Availability.last_update.desc()) \
            .first()

        if not av:
            continue  # Skip broken stations

        # --- Find Start Station (Needs Bikes) ---
        dist_to_start = calculate_distance(start_lat, start_lon, station.latitude, station.longitude)
        if av.available_bikes > 0 and dist_to_start < min_start_dist:
            min_start_dist = dist_to_start
            best_start_station = station

        # --- Find End Station (Needs Parking) ---
        dist_to_end = calculate_distance(end_lat, end_lon, station.latitude, station.longitude)
        if av.available_bike_stands > 0 and dist_to_end < min_end_dist:
            min_end_dist = dist_to_end
            best_end_station = station

    if not best_start_station or not best_end_station:
        return None

    # Return a clean dictionary
    return {
        "start_station": {
            "name": best_start_station.address,
            "coords": {"lat": best_start_station.latitude, "lon": best_start_station.longitude},
            "distance_km": round(min_start_dist, 2)
        },
        "end_station": {
            "name": best_end_station.address,
            "coords": {"lat": best_end_station.latitude, "lon": best_end_station.longitude},
            "distance_km": round(min_end_dist, 2)
        }
    }