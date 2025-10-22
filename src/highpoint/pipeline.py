"""High-level orchestration for the HighPoint viewpoint search."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from pyproj import Transformer

from highpoint.analysis.candidates import TerrainCandidate, cluster_candidates, identify_candidates
from highpoint.analysis.drivability import DrivabilityResult, evaluate_candidate_drivability
from highpoint.analysis.visibility import VisibilityMetrics, compute_visibility_metrics
from highpoint.config import AppConfig
from highpoint.data.discovery import (
    DatasetNotFoundError,
    compute_search_bounds,
    discover_roads_path,
    discover_terrain_paths,
    load_terrain_grid,
)
from highpoint.data.roads import RoadNetwork
from highpoint.data.terrain import TerrainGrid
from highpoint.utils import (
    great_circle_distance_m,
    meters_to_miles,
    miles_to_meters,
    utm_epsg_for_latlon,
)

LOG = logging.getLogger(__name__)


@dataclass
class ViewpointResult:
    """Complete evaluation result for a candidate viewpoint."""

    candidate: TerrainCandidate
    visibility: VisibilityMetrics
    drivability: DrivabilityResult | None
    candidate_latlon: tuple[float, float]
    access_latlon: tuple[float, float] | None
    access_altitude_m: float | None
    straight_line_miles: float
    score: float


@dataclass
class PipelineOutput:
    """Artifacts produced by the pipeline."""

    terrain: TerrainGrid
    road_network: RoadNetwork
    results: list[ViewpointResult]


def run_pipeline(config: AppConfig) -> PipelineOutput:
    """Execute the HighPoint pipeline end-to-end."""
    LOG.info("Loading terrain data...")
    terrain_grid, observer_xy, transformer_xy_to_ll = _load_terrain(config)

    LOG.info(
        "Loaded DEM window %dx%d px at %.1fm resolution",
        terrain_grid.width,
        terrain_grid.height,
        terrain_grid.resolution[0],
    )

    LOG.info("Generating terrain candidates...")
    candidates = identify_candidates(terrain_grid)
    clustered = cluster_candidates(candidates, config.terrain.cluster_grid_m)
    LOG.info("Identified %d raw candidates -> %d clustered", len(candidates), len(clustered))

    LOG.info("Loading road network...")
    road_network = _load_roads(config, terrain_grid.crs)

    results: list[ViewpointResult] = []
    inv_transform = transformer_xy_to_ll

    for candidate in clustered:
        metrics = compute_visibility_metrics(terrain_grid, candidate, config)
        drivability = evaluate_candidate_drivability(
            candidate_xy=(candidate.x, candidate.y),
            observer_xy=observer_xy,
            road_network=road_network,
            config=config,
        )
        if drivability is None:
            LOG.debug("Candidate at (%f, %f) rejected due to drivability", candidate.x, candidate.y)
            continue

        candidate_lonlat = tuple(inv_transform.transform(candidate.x, candidate.y))
        candidate_latlon = (candidate_lonlat[1], candidate_lonlat[0])
        access_latlon = None
        access_altitude = None
        if drivability.access_point:
            access_x, access_y = drivability.access_point.coordinate
            access_lonlat = tuple(inv_transform.transform(access_x, access_y))
            access_latlon = (access_lonlat[1], access_lonlat[0])
            access_altitude = float(
                _sample_elevation(terrain_grid, access_x, access_y) if terrain_grid else np.nan,
            )

        straight_line_m = great_circle_distance_m(
            (config.observer.latitude, config.observer.longitude),
            candidate_latlon,
        )

        score = _score_candidate(candidate, metrics, drivability, config)
        results.append(
            ViewpointResult(
                candidate=candidate,
                visibility=metrics,
                drivability=drivability,
                candidate_latlon=candidate_latlon,
                access_latlon=access_latlon,
                access_altitude_m=access_altitude,
                straight_line_miles=meters_to_miles(straight_line_m),
                score=score,
            ),
        )

    sorted_results = sorted(results, key=lambda item: item.score, reverse=True)
    return PipelineOutput(
        terrain=terrain_grid,
        road_network=road_network,
        results=sorted_results[: config.output.results_limit],
    )


def _load_terrain(config: AppConfig) -> tuple[TerrainGrid, tuple[float, float], Transformer]:
    terrain_cfg = config.terrain
    observer_lat = config.observer.latitude
    observer_lon = config.observer.longitude
    utm_epsg = utm_epsg_for_latlon(observer_lat, observer_lon)
    utm_crs = f"EPSG:{utm_epsg}"

    if terrain_cfg.data_path is None:
        paths, bounds_latlon = discover_terrain_paths(
            observer_lat,
            observer_lon,
            terrain_cfg.search_radius_km,
            prefer_source=terrain_cfg.source,
        )
    else:
        path = Path(terrain_cfg.data_path)
        if not path.exists():
            raise DatasetNotFoundError(
                "terrain",
                f"Configured terrain file {path} does not exist. Provide a valid GeoTIFF.",
            )
        paths = (path,)
        bounds_latlon = compute_search_bounds(
            observer_lat,
            observer_lon,
            terrain_cfg.search_radius_km,
        )

    grid = load_terrain_grid(
        paths,
        bounds_latlon,
        terrain_cfg.resolution_scale,
        utm_crs,
    )
    observer_xy = Transformer.from_crs("EPSG:4326", grid.crs, always_xy=True).transform(
        config.observer.longitude,
        config.observer.latitude,
    )
    return (
        grid,
        (observer_xy[0], observer_xy[1]),
        Transformer.from_crs(
            grid.crs,
            "EPSG:4326",
            always_xy=True,
        ),
    )


def _load_roads(config: AppConfig, target_crs: str) -> RoadNetwork:
    roads_cfg = config.roads
    if roads_cfg.data_path is None:
        path, _ = discover_roads_path(
            config.observer.latitude,
            config.observer.longitude,
            config.terrain.search_radius_km,
            prefer_source=roads_cfg.source,
        )
    else:
        path = Path(roads_cfg.data_path)
        if not path.exists():
            raise DatasetNotFoundError(
                "roads",
                f"Configured roads file {path} does not exist. Provide a GeoJSON cache.",
            )
    return RoadNetwork.from_geojson(path, target_crs=target_crs)


def _score_candidate(
    candidate: TerrainCandidate,
    metrics: VisibilityMetrics,
    drivability: DrivabilityResult,
    config: AppConfig,
) -> float:
    required_distance = miles_to_meters(config.visibility.min_visibility_miles)
    distance_score = min(1.0, metrics.max_distance_m / (required_distance * 1.5))
    fov_score = min(
        1.0,
        metrics.actual_fov_deg / max(config.visibility.min_field_of_view_deg, 1.0),
    )
    walk_penalty = max(0.0, 1.0 - (drivability.walk_minutes / config.roads.max_walk_minutes))
    elevation_bonus = float(np.tanh(candidate.elevation_m / 500.0))
    return (
        (distance_score * 0.4) + (fov_score * 0.3) + (walk_penalty * 0.2) + (elevation_bonus * 0.1)
    )


def _sample_elevation(grid: TerrainGrid, x: float, y: float) -> float:
    inv_transform = ~grid.transform
    col, row = inv_transform * (x, y)
    row_i = int(round(row))
    col_i = int(round(col))
    if 0 <= row_i < grid.height and 0 <= col_i < grid.width:
        return float(grid.elevations[row_i, col_i])
    return float("nan")
