"""Line-of-sight visibility computations."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.ndimage import map_coordinates

from highpoint.analysis.candidates import TerrainCandidate
from highpoint.config import AppConfig
from highpoint.data.terrain import TerrainGrid
from highpoint.utils import azimuth_range, miles_to_meters, unit_vector


@dataclass
class VisibilityMetrics:
    """Visibility statistics along discrete rays."""

    max_distance_m: float
    mean_distance_m: float
    median_distance_m: float
    actual_fov_deg: float
    ray_results: dict[float, float]
    rays_with_clearance: int
    total_rays: int

    @property
    def has_clear_drop(self) -> bool:
        """Return True when at least one ray clears the obstruction belt."""

        return self.rays_with_clearance > 0


def compute_visibility_metrics(
    grid: TerrainGrid,
    candidate: TerrainCandidate,
    config: AppConfig,
) -> VisibilityMetrics:
    """Compute visibility statistics for a candidate viewpoint."""
    visibility_cfg = config.visibility
    cell_size = min(abs(grid.transform.a), abs(grid.transform.e))
    max_distance = config.terrain.max_visibility_km * 1000.0
    max_steps = int(max_distance / cell_size)
    viewer_height = candidate.elevation_m + visibility_cfg.observer_eye_height_m

    az_step = 360.0 / visibility_cfg.rays_full_circle
    angles = [i * az_step for i in range(visibility_cfg.rays_full_circle)]

    ray_results: dict[float, float] = {}
    max_distance_m = 0.0
    distances_for_sector: list[float] = []
    distances_meeting_requirement: list[float] = []
    rays_with_clearance = 0

    sector_start, sector_end = azimuth_range(
        visibility_cfg.azimuth_deg,
        visibility_cfg.min_field_of_view_deg,
    )
    min_required_distance = miles_to_meters(visibility_cfg.min_visibility_miles)

    for angle in angles:
        distance, clearance_met = _trace_ray(
            grid=grid,
            candidate=candidate,
            viewer_height=viewer_height,
            angle_deg=angle,
            cell_size=cell_size,
            max_steps=max_steps,
            obstruction_start=visibility_cfg.obstruction_start_m,
            obstruction_height=visibility_cfg.obstruction_height_m,
        )
        ray_results[angle] = distance
        max_distance_m = max(max_distance_m, distance)
        if clearance_met:
            rays_with_clearance += 1
        if _angle_in_sector(angle, sector_start, sector_end):
            distances_for_sector.append(distance)
            if distance >= min_required_distance:
                distances_meeting_requirement.append(distance)

    mean_distance_m = float(np.mean(distances_for_sector)) if distances_for_sector else 0.0
    median_distance_m = float(np.median(distances_for_sector)) if distances_for_sector else 0.0

    actual_fov_deg = (
        len(distances_meeting_requirement) * az_step if distances_meeting_requirement else 0.0
    )

    return VisibilityMetrics(
        max_distance_m=max_distance_m,
        mean_distance_m=mean_distance_m,
        median_distance_m=median_distance_m,
        actual_fov_deg=actual_fov_deg,
        ray_results=ray_results,
        rays_with_clearance=rays_with_clearance,
        total_rays=len(angles),
    )


def _trace_ray(
    grid: TerrainGrid,
    candidate: TerrainCandidate,
    viewer_height: float,
    angle_deg: float,
    cell_size: float,
    max_steps: int,
    obstruction_start: float,
    obstruction_height: float,
) -> tuple[float, bool]:
    """Return the visible distance and whether clearance was achieved for one ray."""

    unit_dx, unit_dy = unit_vector(angle_deg)
    inv_transform = ~grid.transform

    visible_distance = 0.0
    max_slope = -math.inf

    eye_height = viewer_height - candidate.elevation_m
    drop_required = max(0.0, obstruction_height - eye_height)
    clearance_met = drop_required == 0.0

    for step in range(1, max_steps + 1):
        distance = step * cell_size
        x = candidate.x + unit_dx * distance
        y = candidate.y + unit_dy * distance
        col, row = inv_transform * (x, y)
        if row < 0 or row >= grid.height or col < 0 or col >= grid.width:
            break

        sample = float(
            map_coordinates(grid.elevations, [[row], [col]], order=1, mode="nearest")[0],
        )
        if np.isnan(sample):
            continue

        if distance <= obstruction_start and not clearance_met:
            drop = candidate.elevation_m - sample
            if drop >= drop_required:
                clearance_met = True

        obstacle_height = sample
        if distance > obstruction_start:
            if not clearance_met:
                return obstruction_start, False
            obstacle_height += obstruction_height

        slope = (obstacle_height - viewer_height) / distance
        if slope > max_slope:
            max_slope = slope
            visible_distance = distance

    if not clearance_met:
        return min(visible_distance, obstruction_start), False
    return visible_distance, True


def _angle_in_sector(angle: float, start: float, end: float) -> bool:
    if start <= end:
        return start <= angle <= end
    return angle >= start or angle <= end
