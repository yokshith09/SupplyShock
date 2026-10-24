"""Geo helpers. Owner: D2."""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from typing import Any

EARTH_RADIUS_KM = 6371.0088
DEFAULT_BUFFER = 1.2


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points, in km."""
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlmb = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))


def _lat_lon(point: Any) -> tuple[float, float]:
    """Accept a GeoPoint-like object, a dict with lat/lon, or a (lat, lon) tuple."""
    if isinstance(point, dict):
        return float(point["lat"]), float(point["lon"])
    if isinstance(point, (tuple, list)):
        return float(point[0]), float(point[1])
    return float(point.lat), float(point.lon)


def distance_km(a: Any, b: Any) -> float:
    lat1, lon1 = _lat_lon(a)
    lat2, lon2 = _lat_lon(b)
    return haversine_km(lat1, lon1, lat2, lon2)


def within_radius(point: Any, center: Any, radius_km: float, buffer: float = DEFAULT_BUFFER) -> bool:
    """True if point is within radius_km * buffer of center."""
    return distance_km(point, center) <= radius_km * buffer
