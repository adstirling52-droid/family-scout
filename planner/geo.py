"""Straight-line distances from Livingston."""

from math import asin, cos, radians, sin, sqrt

from planner.config import HOME, RADIUS_MILES

EARTH_MILES = 3958.8


def haversine_miles(origin: tuple[float, float], point: tuple[float, float]) -> float:
    lat1, lon1 = origin
    lat2, lon2 = point
    phi1, phi2 = radians(lat1), radians(lat2)
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    h = sin(dlat / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlon / 2) ** 2
    return 2 * EARTH_MILES * asin(sqrt(h))


def miles_from_home(lat: float, lon: float) -> float:
    return haversine_miles(HOME, (lat, lon))


def within_radius(lat: float, lon: float, radius: float = RADIUS_MILES) -> bool:
    return miles_from_home(lat, lon) <= radius


def format_miles(miles: float) -> str:
    if miles < 0.8:
        return "under a mile"
    rounded = int(round(miles))
    unit = "mile" if rounded == 1 else "miles"
    return f"about {rounded} {unit}"
