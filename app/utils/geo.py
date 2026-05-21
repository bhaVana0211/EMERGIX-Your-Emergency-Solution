import math


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance in km between two coordinates using Haversine formula."""
    R = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def get_hospitals_within_radius(hospitals, user_lat: float, user_lng: float,
                                 radius_km: float = 10.0):
    """Filter hospitals by radius and return with distance, sorted by proximity."""
    results = []
    for h in hospitals:
        if h.latitude and h.longitude:
            dist = haversine_distance(user_lat, user_lng, h.latitude, h.longitude)
            if dist <= radius_km:
                results.append((h, dist))
    results.sort(key=lambda x: x[1])
    return results


def build_maps_url(user_lat: float, user_lng: float, dest_lat: float, dest_lng: float) -> str:
    """Build Google Maps directions URL."""
    return (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={user_lat},{user_lng}"
        f"&destination={dest_lat},{dest_lng}"
        f"&travelmode=driving"
    )


def validate_coordinates(lat, lng):
    """Validate that lat/lng are within valid range."""
    try:
        lat, lng = float(lat), float(lng)
        return -90 <= lat <= 90 and -180 <= lng <= 180
    except (TypeError, ValueError):
        return False
