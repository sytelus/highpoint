"""Road network loading and access checks."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, MultiLineString


def _read_geo_dataframe(path: Path, **kwargs: object) -> gpd.GeoDataFrame:
    """Load a GeoDataFrame ensuring Arrow-backed IO when supported."""

    try:
        return gpd.read_file(path, use_arrow=True, **kwargs)
    except TypeError:
        # Older GeoPandas/Pyogrio releases may not recognise the flag.
        return gpd.read_file(path, **kwargs)
    except ValueError as exc:
        # Some builds raise when Arrow support is unavailable despite the flag.
        if "use_arrow" in str(exc).lower():
            return gpd.read_file(path, **kwargs)
        raise


@dataclass
class RoadAccessPoint:
    """Details about the nearest drivable location relative to a terrain candidate."""

    coordinate: tuple[float, float]
    distance_m: float
    walking_minutes: float


class RoadNetwork:
    """Vector road dataset with proximity utilities."""

    def __init__(
        self,
        geometries: Iterable[LineString],
        crs: str,
    ) -> None:
        self._geometries: list[LineString] = list(geometries)
        if not self._geometries:
            raise ValueError("RoadNetwork requires at least one geometry.")
        self.crs = crs

    @property
    def geometries(self) -> list[LineString]:
        """Expose underlying geometries (used for synthetic exports)."""
        return list(self._geometries)

    @classmethod
    def from_geojson(cls, path: Path, target_crs: str) -> RoadNetwork:
        """Load road geometries from GeoJSON and reproject to target CRS."""
        gdf = _read_geo_dataframe(path)
        if gdf.empty:
            raise ValueError(f"GeoJSON at {path} contains no features.")
        inferred_projected = _looks_projected(gdf)
        if gdf.crs is None:
            if inferred_projected:
                gdf = gdf.set_crs(target_crs, allow_override=True)
            else:
                gdf = gdf.set_crs("EPSG:4326", allow_override=True).to_crs(target_crs)
        else:
            crs_epsg = gdf.crs.to_epsg()
            if inferred_projected and crs_epsg in {4326, 4979}:
                gdf = gdf.set_crs(target_crs, allow_override=True)
            else:
                gdf = gdf.to_crs(target_crs)
        lines: list[LineString] = []
        for geom in gdf.geometry:
            if isinstance(geom, LineString):
                lines.append(geom)
            elif isinstance(geom, MultiLineString):
                lines.extend(segment for segment in geom.geoms if isinstance(segment, LineString))
        return cls(lines, crs=target_crs)

    @classmethod
    def synthetic(cls, target_crs: str = "EPSG:32610") -> RoadNetwork:
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
        point_xy: tuple[float, float],
        walking_speed_kmh: float,
    ) -> RoadAccessPoint:
        """Find the shortest walking route from a projected coordinate to the road network."""
        target_x, target_y = point_xy
        best_distance_sq = np.inf
        best_coordinate: tuple[float, float] | None = None

        for geom in self._geometries:
            coords = np.asarray(geom.coords, dtype=np.float64)
            if len(coords) < 2:
                continue
            segments_start = coords[:-1]
            segments_end = coords[1:]
            for start, end in zip(segments_start, segments_end, strict=False):
                dx = end[0] - start[0]
                dy = end[1] - start[1]
                segment_length_sq = dx * dx + dy * dy
                if segment_length_sq == 0.0:
                    candidate_x, candidate_y = float(start[0]), float(start[1])
                else:
                    numerator = ((target_x - start[0]) * dx) + ((target_y - start[1]) * dy)
                    t = numerator / segment_length_sq
                    t = min(1.0, max(0.0, t))
                    candidate_x = float(start[0] + t * dx)
                    candidate_y = float(start[1] + t * dy)
                diff_x = candidate_x - target_x
                diff_y = candidate_y - target_y
                distance_sq = diff_x * diff_x + diff_y * diff_y
                if distance_sq < best_distance_sq:
                    best_distance_sq = distance_sq
                    best_coordinate = (candidate_x, candidate_y)

        if best_coordinate is None:  # pragma: no cover - defensive
            raise RuntimeError("Failed to determine nearest road.")

        best_distance = float(np.sqrt(best_distance_sq))
        walking_minutes = (best_distance / 1000.0) / walking_speed_kmh * 60.0
        return RoadAccessPoint(
            coordinate=best_coordinate,
            distance_m=best_distance,
            walking_minutes=walking_minutes,
        )


def estimate_driving_time_minutes(
    observer_xy: tuple[float, float],
    road_point_xy: tuple[float, float],
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


def _looks_projected(gdf: gpd.GeoDataFrame) -> bool:
    minx, miny, maxx, maxy = gdf.total_bounds
    return any(abs(value) > 360 for value in (minx, miny, maxx, maxy))
