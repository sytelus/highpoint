"""Line-of-sight visibility computations."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.ndimage import map_coordinates

from highpoint.analysis.candidates import TerrainCandidate
from highpoint.config import AppConfig
from highpoint.data.terrain import TerrainGrid
from highpoint.utils import miles_to_meters, unit_vector


@dataclass(frozen=True)
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
    rays_with_clearance = 0

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
        if clearance_met:
            rays_with_clearance += 1

    sector_rays = sorted(
        (
            (_signed_angular_offset(angle, visibility_cfg.azimuth_deg), distance)
            for angle, distance in ray_results.items()
            if abs(_signed_angular_offset(angle, visibility_cfg.azimuth_deg))
            <= visibility_cfg.azimuth_tolerance_deg + 1e-9
        ),
        key=lambda item: item[0],
    )
    distances_for_sector = [distance for _, distance in sector_rays]
    clear_rays = [distance >= min_required_distance for distance in distances_for_sector]
    sector_width = min(360.0, visibility_cfg.azimuth_tolerance_deg * 2.0)

    max_distance_m = max(distances_for_sector, default=0.0)
    mean_distance_m = float(np.mean(distances_for_sector)) if distances_for_sector else 0.0
    median_distance_m = float(np.median(distances_for_sector)) if distances_for_sector else 0.0
    actual_fov_deg = min(
        sector_width,
        _longest_clear_run(
            clear_rays,
            circular=math.isclose(sector_width, 360.0),
        )
        * az_step,
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
        # Affine inversion returns pixel-corner coordinates, while scipy interpolation
        # treats integer indices as pixel centers.
        row_index = row - 0.5
        col_index = col - 0.5
        if (
            row_index < 0
            or row_index > grid.height - 1
            or col_index < 0
            or col_index > grid.width - 1
        ):
            break

        sample = float(
            map_coordinates(
                grid.elevations,
                [[row_index], [col_index]],
                order=1,
                mode="nearest",
            )[0],
        )
        if np.isnan(sample):
            # Unknown terrain cannot safely be treated as transparent line of sight.
            break

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


def _signed_angular_offset(angle: float, center: float) -> float:
    """Return the shortest signed offset from ``center`` in ``[-180, 180)``."""
    return (angle - center + 180.0) % 360.0 - 180.0


def _longest_clear_run(clear_rays: list[bool], *, circular: bool) -> int:
    """Return the longest contiguous run of clear angular samples."""
    if not clear_rays:
        return 0

    samples = clear_rays * 2 if circular else clear_rays
    longest = 0
    current = 0
    for is_clear in samples:
        current = current + 1 if is_clear else 0
        longest = max(longest, current)
    return min(longest, len(clear_rays))
