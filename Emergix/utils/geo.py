"""
EMERGIX — Geospatial Utilities
Haversine distance calculation and coordinate validation.
"""

import math


def haversine_distance(lat1, lng1, lat2, lng2):
    """
    Calculate the great-circle distance between two points
    on the Earth's surface using the Haversine formula.
    Returns distance in kilometers.
    """
    R = 6371.0  # Earth's radius in km

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(dlng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return round(R * c, 2)


def validate_coordinates(lat, lng):
    """Validate that coordinates are within valid ranges."""
    try:
        lat = float(lat)
        lng = float(lng)
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            return True, lat, lng
        return False, None, None
    except (TypeError, ValueError):
        return False, None, None


def find_nearby_hospitals(hospitals, user_lat, user_lng, radius_km=10):
    """
    Filter hospitals within radius_km of user location.
    Uses Haversine formula for distance calculation (SQLite fallback).
    Returns list of (hospital, distance_km) tuples sorted by distance.
    """
    nearby = []
    for hospital in hospitals:
        if hospital.latitude and hospital.longitude:
            dist = haversine_distance(user_lat, user_lng, hospital.latitude, hospital.longitude)
            if dist <= radius_km:
                nearby.append((hospital, dist))
    nearby.sort(key=lambda x: x[1])
    return nearby
