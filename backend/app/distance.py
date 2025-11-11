"""
Distance calculation utilities using Haversine formula
"""
import math
from typing import Tuple


def haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """
    Calculate the great circle distance between two points on Earth
    using the Haversine formula

    Args:
        lat1, lon1: Coordinates of first point
        lat2, lon2: Coordinates of second point

    Returns:
        Distance in kilometers
    """
    # Radius of Earth in kilometers
    R = 6371.0

    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    # Haversine formula
    a = (
        math.sin(dlat / 2) ** 2 +
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c

    return distance


def calculate_bounding_box(
    lat: float, lon: float, distance_km: float
) -> Tuple[float, float, float, float]:
    """
    Calculate a bounding box (min_lat, max_lat, min_lon, max_lon)
    around a point within a given distance

    This is useful for efficient database queries before applying
    exact distance calculations

    Args:
        lat, lon: Center point coordinates
        distance_km: Radius in kilometers

    Returns:
        Tuple of (min_lat, max_lat, min_lon, max_lon)
    """
    # Approximate degrees per km (varies by latitude)
    # At latitude ~52° (Netherlands), 1° lat ≈ 111 km, 1° lon ≈ 70 km
    lat_degrees_per_km = 1 / 111.0
    lon_degrees_per_km = 1 / (111.0 * math.cos(math.radians(lat)))

    lat_offset = distance_km * lat_degrees_per_km
    lon_offset = distance_km * lon_degrees_per_km

    return (
        lat - lat_offset,  # min_lat
        lat + lat_offset,  # max_lat
        lon - lon_offset,  # min_lon
        lon + lon_offset   # max_lon
    )


def format_distance(distance_km: float) -> str:
    """
    Format distance for display

    Args:
        distance_km: Distance in kilometers

    Returns:
        Formatted string (e.g., "1.5 km" or "250 m")
    """
    if distance_km < 1.0:
        return f"{int(distance_km * 1000)} m"
    else:
        return f"{distance_km:.1f} km"
