"""Utility helpers for geographic computations and units."""

from __future__ import annotations

import math

from pyproj import Geod

MILES_TO_METERS = 1609.344
KILOMETERS_TO_MILES = 0.621371

WGS84 = Geod(ellps="WGS84")


def miles_to_meters(miles: float) -> float:
    return miles * MILES_TO_METERS


def meters_to_miles(meters: float) -> float:
    return meters / MILES_TO_METERS


def kilometers_to_miles(kilometers: float) -> float:
    return kilometers * KILOMETERS_TO_MILES


def great_circle_distance_m(origin: tuple[float, float], dest: tuple[float, float]) -> float:
    """Return great-circle distance in meters between two lat/lon points."""
    _, _, distance = WGS84.inv(origin[1], origin[0], dest[1], dest[0])
    return float(distance)


def utm_epsg_for_latlon(lat: float, lon: float) -> int:
    """Return EPSG code for the UTM zone covering the provided coordinate."""
    zone = min(60, max(1, int((lon + 180) / 6) + 1))
    epsg = 32600 + zone if lat >= 0 else 32700 + zone
    return epsg


def unit_vector(azimuth_deg: float) -> tuple[float, float]:
    """Return unit vector in azimuth direction (degrees clockwise from north)."""
    radians = math.radians(azimuth_deg)
    return math.sin(radians), math.cos(radians)
