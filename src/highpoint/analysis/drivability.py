"""Drivability checks for candidate viewpoints."""

from __future__ import annotations

from dataclasses import dataclass

from highpoint.config import AppConfig
from highpoint.data.roads import RoadAccessPoint, RoadNetwork, estimate_driving_time_minutes


@dataclass
class DrivabilityResult:
    """Summary of accessibility for a candidate."""

    access_point: RoadAccessPoint
    walk_minutes: float
    drive_minutes: float | None
    drive_distance_km: float | None


def evaluate_candidate_drivability(
    candidate_xy: tuple[float, float],
    observer_xy: tuple[float, float],
    road_network: RoadNetwork,
    config: AppConfig,
) -> DrivabilityResult | None:
    """
    Determine whether a terrain candidate is accessible within configured thresholds.

    Returns None when walking exceeds the configured maximum or, if provided, driving time
    exceeds the optional limit.
    """
    roads_cfg = config.roads
    access = road_network.nearest_access_point(candidate_xy, roads_cfg.walking_speed_kmh)

    if access.walking_minutes > roads_cfg.max_walk_minutes:
        return None

    drive_minutes: float | None
    drive_distance_km: float | None

    drive_minutes = estimate_driving_time_minutes(
        observer_xy=observer_xy,
        road_point_xy=access.coordinate,
        driving_speed_kmh=roads_cfg.driving_speed_kmh,
    )
    drive_distance_km = (
        drive_minutes / 60.0 * roads_cfg.driving_speed_kmh if drive_minutes is not None else None
    )

    if (
        roads_cfg.max_drive_minutes is not None
        and drive_minutes is not None
        and drive_minutes > roads_cfg.max_drive_minutes
    ):
        return None

    return DrivabilityResult(
        access_point=access,
        walk_minutes=access.walking_minutes,
        drive_minutes=drive_minutes,
        drive_distance_km=drive_distance_km,
    )
