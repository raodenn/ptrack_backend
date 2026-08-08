import math

def haversine_distance(lat1, lon1, lat2, lon2):
    """calculates great circle distance between two points on earth"""

    R = 6371.0 #Earths radius in km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    a = math.sin(dlat / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def compute_centroid(locations):
    denom = len(locations)
    total_lat = 0
    total_lon = 0

    for loc in locations:
        total_lat += loc.lat
        total_lon += loc.lon
    return (total_lat/denom, total_lon/denom)


