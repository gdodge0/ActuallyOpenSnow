"""Geographic utility functions."""

from __future__ import annotations

import math


def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Calculate the great-circle distance between two points.

    Uses the haversine formula to calculate the distance between two points
    on the Earth's surface specified by latitude and longitude.

    Args:
        lat1: Latitude of the first point in degrees.
        lon1: Longitude of the first point in degrees.
        lat2: Latitude of the second point in degrees.
        lon2: Longitude of the second point in degrees.

    Returns:
        Distance in meters.
    """
    # Earth's radius in meters
    R = 6_371_000

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Haversine formula
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def coords_are_equivalent(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    threshold_meters: float = 100.0,
) -> bool:
    """Check if two coordinate pairs are within a threshold distance.

    Args:
        lat1: Latitude of the first point in degrees.
        lon1: Longitude of the first point in degrees.
        lat2: Latitude of the second point in degrees.
        lon2: Longitude of the second point in degrees.
        threshold_meters: Maximum distance in meters to consider equivalent.
            Defaults to 100 meters.

    Returns:
        True if the points are within the threshold distance.
    """
    return haversine_distance(lat1, lon1, lat2, lon2) <= threshold_meters


def round_coords(lat: float, lon: float, precision: int = 4) -> tuple[float, float]:
    """Round coordinates to a given decimal precision.

    Args:
        lat: Latitude in degrees.
        lon: Longitude in degrees.
        precision: Number of decimal places (default 4 ≈ 11m resolution).

    Returns:
        Tuple of (rounded_lat, rounded_lon).
    """
    return round(lat, precision), round(lon, precision)


def normalize_longitude(lon: float) -> float:
    """Normalize longitude to the range [-180, 180].

    Args:
        lon: Longitude in degrees.

    Returns:
        Normalized longitude in [-180, 180].
    """
    while lon > 180:
        lon -= 360
    while lon < -180:
        lon += 360
    return lon

