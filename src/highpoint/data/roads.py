"""Road network loading and access checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import geopandas as gpd
import numpy as np
from numpy.typing import NDArray
from pyproj import Transformer
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points


@dataclass
class RoadAccessPoint:
    """Details about the nearest drivable location relative to a terrain candidate."""

    coordinate: Tuple[float, float]
    distance_m: float
    walking_minutes: float


class RoadNetwork:
    """Vector road dataset with proximity utilities."""

    def __init__(
        self,
        geometries: Iterable[LineString],
        crs: str,
        transformer_to_projected: Optional[Transformer] = None,
    ) -> None:
        self._geometries: List[LineString] = list(geometries)
        if not self._geometries:
            raise ValueError("RoadNetwork requires at least one geometry.")
        self.crs = crs
        self._transformer = transformer_to_projected

    @classmethod
    def from_geojson(cls, path: Path, target_crs: str) -> "RoadNetwork":
        """Load road geometries from GeoJSON and reproject to target CRS."""
        gdf = gpd.read_file(path)
        if gdf.empty:
            raise ValueError(f"GeoJSON at {path} contains no features.")
        gdf = gdf.to_crs(target_crs)
        lines = [geom for geom in gdf.geometry if isinstance(geom, LineString)]
        return cls(lines, crs=target_crs)

    @classmethod
    def synthetic(cls, target_crs: str = "EPSG:32610") -> "RoadNetwork":
        """Construct a small synthetic road grid for tests."""
        base_x, base_y = 500000, 5_200_000
        lines = [
            LineString([(base_x, base_y), (base_x + 1_200, base_y)]),
            LineString([(base_x + 600, base_y - 1_200), (base_x + 600, base_y + 1_200)]),
            LineString([(base_x - 400, base_y + 800), (base_x + 1_600, base_y + 800)]),
        ]
        return cls(lines, crs=target_crs)

    def nearest_access_point(
        self,
        point_xy: Tuple[float, float],
        walking_speed_kmh: float,
    ) -> RoadAccessPoint:
        """Find the shortest walking route from a projected coordinate to the road network."""
        target = Point(point_xy)
        best_distance = np.inf
        best_point: Optional[Point] = None
        for geom in self._geometries:
            candidate = nearest_points(target, geom)[1]
            distance = candidate.distance(target)
            if distance < best_distance:
                best_distance = distance
                best_point = candidate
        if best_point is None:  # pragma: no cover - defensive
            raise RuntimeError("Failed to determine nearest road.")
        walking_minutes = (best_distance / 1000.0) / walking_speed_kmh * 60.0
        return RoadAccessPoint(coordinate=(best_point.x, best_point.y), distance_m=best_distance, walking_minutes=walking_minutes)


def estimate_driving_time_minutes(
    observer_xy: Tuple[float, float],
    road_point_xy: Tuple[float, float],
    driving_speed_kmh: float,
) -> float:
    """
    Estimate driving time using straight-line distance adjusted with heuristic factor.

    Without full routing we approximate actual road distance as 1.35x the Euclidean distance.
    """
    dx = observer_xy[0] - road_point_xy[0]
    dy = observer_xy[1] - road_point_xy[1]
    straight_distance_m = float(np.hypot(dx, dy))
    adjusted_distance_km = straight_distance_m / 1000.0 * 1.35
    return (adjusted_distance_km / driving_speed_kmh) * 60.0
