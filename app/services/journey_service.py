import googlemaps

from app.extensions import db
from app.models import Station, Availability
from app.utils.calculateDistance import calculate_distance

from config import GOOGLE_MAPS_API_KEY

gmaps = None
if GOOGLE_MAPS_API_KEY:
    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)


def get_matrix_durations(origins, destinations, mode="walking"):
    """
    Helper: Gets a matrix of durations from Google Maps.
    origins: list of (lat, lon) tuples
    destinations: list of (lat, lon) tuples
    Returns: A list of lists (matrix) where matrix[i][j] is duration in seconds.
    """
    if not gmaps:
        # Return infinity so routes are marked impossible instead of 0 minutes
        return [[float('inf')] * len(destinations) for _ in range(len(origins))]

    try:
        # Google Distance Matrix accepts lists of coords
        matrix = gmaps.distance_matrix(origins=origins, destinations=destinations, mode=mode)

        results = []
        if matrix['status'] == 'OK':
            for row in matrix['rows']:
                row_durations = []
                for element in row['elements']:
                    if element['status'] == 'OK':
                        row_durations.append(element['duration']['value'])
                    else:
                        row_durations.append(float('inf'))  # Route impossible
                results.append(row_durations)
            return results
        else:
            # Explicit fallback if top-level status is not OK (e.g., quota exceeded)
            print(f"Matrix API returned non-OK status: {matrix.get('status')}")
            return [[float('inf')] * len(destinations) for _ in range(len(origins))]

    except Exception as e:
        print(f"Matrix API Error: {e}")
        return [[float('inf')] * len(destinations) for _ in range(len(origins))]


def find_best_route(start_lat, start_lon, end_lat, end_lon):
    """
    Finds the Global Minimum Duration: Min(Walk1 + Cycle + Walk2).
    """
    stations = db.session.query(Station).all()

    # --- Step 1: Crude Filtering (Haversine) ---
    # We still need this to narrow down 100+ stations to top 5
    candidates_start = []
    candidates_end = []

    for station in stations:
        av = db.session.query(Availability).filter_by(number=station.number).order_by(
            Availability.last_update.desc()).first()
        if not av: continue

        if av.available_bikes > 0:
            dist = calculate_distance(start_lat, start_lon, station.latitude, station.longitude)
            candidates_start.append((station, dist))

        if av.available_bike_stands > 0:
            dist = calculate_distance(end_lat, end_lon, station.latitude, station.longitude)
            candidates_end.append((station, dist))

    # Keep top 5 closest by Haversine
    candidates_start.sort(key=lambda x: x[1])
    candidates_end.sort(key=lambda x: x[1])

    top_starts = [x[0] for x in candidates_start[:5]]  # Just the station objects
    top_ends = [x[0] for x in candidates_end[:5]]

    if not top_starts or not top_ends:
        return None

    # --- Step 2: Get Precise Walking Times ---
    # Batch Call 1: User -> All 5 Start Stations
    start_coords = [(s.latitude, s.longitude) for s in top_starts]
    walk_times_start = get_matrix_durations([(start_lat, start_lon)], start_coords, mode="walking")[0]

    # Batch Call 2: All 5 End Stations -> User
    end_coords = [(s.latitude, s.longitude) for s in top_ends]
    walk_times_end = get_matrix_durations(end_coords, [(end_lat, end_lon)], mode="walking")
    # Note: result is [[time_to_dest], [time_to_dest]...], we flatten it:
    walk_times_end = [row[0] for row in walk_times_end]

    # --- Step 3: Get Cycling Times (The 5x5 Grid) ---
    # Batch Call 3: All Start Stations -> All End Stations
    cycle_matrix = get_matrix_durations(start_coords, end_coords, mode="bicycling")

    # --- Step 4: Find the Global Minimum ---
    best_route = None
    min_total_duration = float('inf')

    # Iterate through all 25 combinations (5 starts * 5 ends)
    for i, start_station in enumerate(top_starts):
        for j, end_station in enumerate(top_ends):

            t_walk1 = walk_times_start[i]
            t_cycle = cycle_matrix[i][j]
            t_walk2 = walk_times_end[j]

            total_time = t_walk1 + t_cycle + t_walk2

            if total_time < min_total_duration:
                min_total_duration = total_time
                best_route = {
                    "start_station": {
                        "number": start_station.number,
                        "name": start_station.name,
                        "address": start_station.address,
                        "coords": {"lat": start_station.latitude, "lon": start_station.longitude},
                        "walking_time": t_walk1
                    },
                    "end_station": {
                        "number": end_station.number,
                        "name": end_station.name,
                        "address": end_station.address,
                        "coords": {"lat": end_station.latitude, "lon": end_station.longitude},
                        "walking_time": t_walk2
                    },
                    "cycling_route": {
                        "cycling_time": t_cycle,
                    },
                    "total_duration": total_time
                }

    # Explicitly catch API failures before returning
    if min_total_duration == float('inf'):
        raise RuntimeError("Routing API unavailable due to upstream Distance Matrix failure.")
    return best_route