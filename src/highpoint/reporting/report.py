"""Result presentation utilities."""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, List, Optional

from rich.console import Console
from rich.table import Table

from highpoint.config import AppConfig
from highpoint.pipeline import ViewpointResult
from highpoint.utils import meters_to_miles

LOG = logging.getLogger(__name__)


def emit_report(results: List[ViewpointResult], config: AppConfig) -> None:
    """Format and emit results based on configuration."""
    if config.output.rich_table:
        _render_rich_table(results)
    else:
        _render_plain(results)

    if config.output.export_csv:
        _export_csv(results, config.output.export_csv)
    if config.output.export_geojson:
        _export_geojson(results, config.output.export_geojson)


def _render_rich_table(results: Iterable[ViewpointResult]) -> None:
    table = Table(title="HighPoint Recommended Viewpoints")
    table.add_column("Rank", justify="right")
    table.add_column("Lat, Lon")
    table.add_column("Elevation (m)")
    table.add_column("Visibility Mean (mi)")
    table.add_column("Visibility Median (mi)")
    table.add_column("Max FOV (deg)")
    table.add_column("Walk (min)")
    table.add_column("Drive (min)")
    table.add_column("Access Lat, Lon")

    console = Console()
    for idx, result in enumerate(results, start=1):
        visibility_mean = meters_to_miles(result.visibility.mean_distance_m)
        visibility_median = meters_to_miles(result.visibility.median_distance_m)
        walk = f"{result.drivability.walk_minutes:.1f}" if result.drivability else "-"
        drive = (
            f"{result.drivability.drive_minutes:.1f}" if result.drivability and result.drivability.drive_minutes else "-"
        )
        access_latlon = (
            f"{result.access_latlon[0]:.5f}, {result.access_latlon[1]:.5f}"
            if result.access_latlon
            else "-"
        )
        table.add_row(
            str(idx),
            f"{result.candidate_latlon[0]:.5f}, {result.candidate_latlon[1]:.5f}",
            f"{result.candidate.elevation_m:.1f}",
            f"{visibility_mean:.2f}",
            f"{visibility_median:.2f}",
            f"{result.visibility.actual_fov_deg:.1f}",
            walk,
            drive,
            access_latlon,
        )
    console.print(table)


def _render_plain(results: Iterable[ViewpointResult]) -> None:
    for idx, result in enumerate(results, start=1):
        LOG.info(
            "[%d] lat=%.5f lon=%.5f elevation=%.1fm visibility_mean=%.2fmi visibility_median=%.2fmi fov=%.1f walk=%.1fmin",
            idx,
            result.candidate_latlon[0],
            result.candidate_latlon[1],
            result.candidate.elevation_m,
            meters_to_miles(result.visibility.mean_distance_m),
            meters_to_miles(result.visibility.median_distance_m),
            result.visibility.actual_fov_deg,
            result.drivability.walk_minutes if result.drivability else float("nan"),
        )


def _export_csv(results: Iterable[ViewpointResult], path: Path) -> None:
    fieldnames = [
        "rank",
        "candidate_lat",
        "candidate_lon",
        "candidate_elevation_m",
        "visibility_mean_m",
        "visibility_median_m",
        "visibility_max_m",
        "visibility_actual_fov_deg",
        "walk_minutes",
        "drive_minutes",
        "access_lat",
        "access_lon",
        "access_altitude_m",
        "straight_line_miles",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for idx, result in enumerate(results, start=1):
            writer.writerow(
                {
                    "rank": idx,
                    "candidate_lat": result.candidate_latlon[0],
                    "candidate_lon": result.candidate_latlon[1],
                    "candidate_elevation_m": result.candidate.elevation_m,
                    "visibility_mean_m": result.visibility.mean_distance_m,
                    "visibility_median_m": result.visibility.median_distance_m,
                    "visibility_max_m": result.visibility.max_distance_m,
                    "visibility_actual_fov_deg": result.visibility.actual_fov_deg,
                    "walk_minutes": result.drivability.walk_minutes if result.drivability else None,
                    "drive_minutes": result.drivability.drive_minutes if result.drivability else None,
                    "access_lat": result.access_latlon[0] if result.access_latlon else None,
                    "access_lon": result.access_latlon[1] if result.access_latlon else None,
                    "access_altitude_m": result.access_altitude_m,
                    "straight_line_miles": result.straight_line_miles,
                }
            )
    LOG.info("CSV exported to %s", path)


def _export_geojson(results: Iterable[ViewpointResult], path: Path) -> None:
    features = []
    for idx, result in enumerate(results, start=1):
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [result.candidate_latlon[1], result.candidate_latlon[0]],
                },
                "properties": {
                    "rank": idx,
                    "elevation_m": result.candidate.elevation_m,
                    "visibility_mean_m": result.visibility.mean_distance_m,
                    "visibility_median_m": result.visibility.median_distance_m,
                    "visibility_max_m": result.visibility.max_distance_m,
                    "fov_deg": result.visibility.actual_fov_deg,
                    "walk_minutes": result.drivability.walk_minutes if result.drivability else None,
                    "drive_minutes": result.drivability.drive_minutes if result.drivability else None,
                    "access_lat": result.access_latlon[0] if result.access_latlon else None,
                    "access_lon": result.access_latlon[1] if result.access_latlon else None,
                },
            }
        )
        if result.access_latlon:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [result.access_latlon[1], result.access_latlon[0]],
                    },
                    "properties": {
                        "rank": idx,
                        "type": "access_point",
                        "altitude_m": result.access_altitude_m,
                    },
                }
            )
    collection = {"type": "FeatureCollection", "features": features}
    with path.open("w", encoding="utf-8") as handle:
        json.dump(collection, handle, indent=2)
    LOG.info("GeoJSON exported to %s", path)
