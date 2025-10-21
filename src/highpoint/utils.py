"""Utility helpers for geographic computations and units."""

from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np
from numpy.typing import NDArray
from pyproj import Geod, Transformer

EARTH_RADIUS_M = 6_371_000
MILES_TO_METERS = 1609.344
FEET_TO_METERS = 0.3048
KILOMETERS_TO_MILES = 0.621371

WGS84 = Geod(ellps="WGS84")


def miles_to_meters(miles: float) -> float:
    return miles * MILES_TO_METERS


def meters_to_miles(meters: float) -> float:
    return meters / MILES_TO_METERS


def feet_to_meters(feet: float) -> float:
    return feet * FEET_TO_METERS


def kilometers_to_miles(kilometers: float) -> float:
    return kilometers * KILOMETERS_TO_MILES


def azimuth_range(center_deg: float, span_deg: float) -> tuple[float, float]:
    """Return start/end azimuth degrees bounded to [0, 360)."""
    half = span_deg / 2.0
    start = (center_deg - half) % 360.0
    end = (center_deg + half) % 360.0
    return start, end


def great_circle_distance_m(origin: tuple[float, float], dest: tuple[float, float]) -> float:
    """Return great-circle distance in meters between two lat/lon points."""
    _, _, distance = WGS84.inv(origin[1], origin[0], dest[1], dest[0])
    return float(distance)


def utm_epsg_for_latlon(lat: float, lon: float) -> int:
    """Return EPSG code for the UTM zone covering the provided coordinate."""
    zone = int((lon + 180) / 6) + 1
    epsg = 32600 + zone if lat >= 0 else 32700 + zone
    return epsg


def project_to_utm(lat: float, lon: float) -> Transformer:
    """Construct a transformer to and from the best-guess UTM zone for a coordinate."""
    epsg = utm_epsg_for_latlon(lat, lon)
    return Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)


def unit_vector(azimuth_deg: float) -> tuple[float, float]:
    """Return unit vector in azimuth direction (degrees clockwise from north)."""
    radians = math.radians(azimuth_deg)
    return math.sin(radians), math.cos(radians)


def to_numpy_coords(points: Iterable[tuple[float, float]]) -> NDArray[np.float64]:
    """Convert coordinate iterable to numpy array of shape (n, 2)."""
    return np.array(list(points), dtype=np.float64)
