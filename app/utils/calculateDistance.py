import math


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculates the distance (in km) between two points using the Haversine formula.
    """
    R = 6371  # Earth radius in kilometers

    # The vertical and horizontal separation in radians
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    # The square of half the straight-line distance (chord) through the Earth
    a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) * math.sin(dlon / 2))

    #  The angle (in radians) separating the two points at the Earth's center
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c