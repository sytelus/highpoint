"""High-level orchestration for the HighPoint viewpoint search."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import numpy as np
from pyproj import Transformer
from rasterio import open as raster_open

from highpoint.analysis.candidates import TerrainCandidate, cluster_candidates, identify_candidates
from highpoint.analysis.drivability import DrivabilityResult, evaluate_candidate_drivability
from highpoint.analysis.visibility import VisibilityMetrics, compute_visibility_metrics
from highpoint.config import AppConfig
from highpoint.data.roads import RoadNetwork
from highpoint.data.terrain import TerrainGrid, TerrainLoader, generate_synthetic_dem
from highpoint.utils import great_circle_distance_m, meters_to_miles, miles_to_meters, utm_epsg_for_latlon

LOG = logging.getLogger(__name__)


@dataclass
class ViewpointResult:
    """Complete evaluation result for a candidate viewpoint."""

    candidate: TerrainCandidate
    visibility: VisibilityMetrics
    drivability: Optional[DrivabilityResult]
    candidate_latlon: Tuple[float, float]
    access_latlon: Optional[Tuple[float, float]]
    access_altitude_m: Optional[float]
    straight_line_miles: float
    score: float


@dataclass
class PipelineOutput:
    """Artifacts produced by the pipeline."""

    terrain: TerrainGrid
    road_network: RoadNetwork
    results: List[ViewpointResult]


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

    results: List[ViewpointResult] = []
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
                _sample_elevation(terrain_grid, access_x, access_y) if terrain_grid else np.nan
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
            )
        )

    sorted_results = sorted(results, key=lambda item: item.score, reverse=True)
    return PipelineOutput(
        terrain=terrain_grid,
        road_network=road_network,
        results=sorted_results[: config.output.results_limit],
    )


def _load_terrain(config: AppConfig) -> Tuple[TerrainGrid, Tuple[float, float], Transformer]:
    terrain_cfg = config.terrain
    if terrain_cfg.data_path is None:
        LOG.warning("No terrain path configured; using synthetic DEM fixture.")
        grid = generate_synthetic_dem()
        transformer = Transformer.from_crs("EPSG:4326", grid.crs, always_xy=True)
    else:
        path = Path(terrain_cfg.data_path)
        with raster_open(path) as dataset:
            dataset_crs = dataset.crs.to_string()  # type: ignore[union-attr]
        observer_lat = config.observer.latitude
        observer_lon = config.observer.longitude
        utm_epsg = utm_epsg_for_latlon(observer_lat, observer_lon)
        utm_crs = f"EPSG:{utm_epsg}"
        to_utm = Transformer.from_crs("EPSG:4326", utm_crs, always_xy=True)
        observer_x, observer_y = to_utm.transform(observer_lon, observer_lat)
        radius_m = terrain_cfg.search_radius_km * 1000.0
        bounds_utm = (
            observer_x - radius_m,
            observer_y - radius_m,
            observer_x + radius_m,
            observer_y + radius_m,
        )
        to_dataset = Transformer.from_crs(utm_crs, dataset_crs, always_xy=True)
        corners = [
            (bounds_utm[0], bounds_utm[1]),
            (bounds_utm[0], bounds_utm[3]),
            (bounds_utm[2], bounds_utm[1]),
            (bounds_utm[2], bounds_utm[3]),
        ]
        transformed = [to_dataset.transform(x, y) for x, y in corners]
        xs, ys = zip(*transformed)
        dataset_bounds = (min(xs), min(ys), max(xs), max(ys))
        loader = TerrainLoader(path)
        grid = loader.read(
            bounds=dataset_bounds,
            resolution_scale=terrain_cfg.resolution_scale,
            target_crs=utm_crs,
        )
        if grid.width == 0 or grid.height == 0:
            grid = loader.read(
                bounds=None,
                resolution_scale=terrain_cfg.resolution_scale,
                target_crs=utm_crs,
            )
        transformer = to_utm
    observer_xy = Transformer.from_crs("EPSG:4326", grid.crs, always_xy=True).transform(
        config.observer.longitude, config.observer.latitude
    )
    return grid, (observer_xy[0], observer_xy[1]), Transformer.from_crs(
        grid.crs, "EPSG:4326", always_xy=True
    )


def _load_roads(config: AppConfig, target_crs: str) -> RoadNetwork:
    roads_cfg = config.roads
    if roads_cfg.data_path is None:
        LOG.warning("No roads path configured; using synthetic road network.")
        return RoadNetwork.synthetic(target_crs)
    return RoadNetwork.from_geojson(Path(roads_cfg.data_path), target_crs=target_crs)


def _score_candidate(
    candidate: TerrainCandidate,
    metrics: VisibilityMetrics,
    drivability: DrivabilityResult,
    config: AppConfig,
) -> float:
    required_distance = miles_to_meters(config.visibility.min_visibility_miles)
    distance_score = min(1.0, metrics.max_distance_m / (required_distance * 1.5))
    fov_score = min(
        1.0, metrics.actual_fov_deg / max(config.visibility.min_field_of_view_deg, 1.0)
    )
    walk_penalty = max(0.0, 1.0 - (drivability.walk_minutes / config.roads.max_walk_minutes))
    elevation_bonus = np.tanh(candidate.elevation_m / 500.0)
    return (distance_score * 0.4) + (fov_score * 0.3) + (walk_penalty * 0.2) + (elevation_bonus * 0.1)


def _sample_elevation(grid: TerrainGrid, x: float, y: float) -> float:
    inv_transform = ~grid.transform
    col, row = inv_transform * (x, y)
    row_i = int(round(row))
    col_i = int(round(col))
    if 0 <= row_i < grid.height and 0 <= col_i < grid.width:
        return float(grid.elevations[row_i, col_i])
    return float("nan")
