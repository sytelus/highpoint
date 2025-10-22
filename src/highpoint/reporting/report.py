"""Result presentation utilities."""

from __future__ import annotations

import csv
import json
import logging
import math
from collections.abc import Iterable
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from highpoint.config import AppConfig
from highpoint.pipeline import ViewpointResult
from highpoint.utils import kilometers_to_miles, meters_to_miles

LOG = logging.getLogger(__name__)


def emit_report(results: list[ViewpointResult], config: AppConfig) -> None:
    """Format and emit results based on configuration."""
    if config.output.rich_table:
        _render_rich_panels(results, config)
    else:
        _render_plain(results)

    if config.output.export_csv:
        _export_csv(results, config.output.export_csv)
    if config.output.export_geojson:
        _export_geojson(results, config.output.export_geojson)


def _render_rich_panels(results: Iterable[ViewpointResult], config: AppConfig) -> None:
    console = Console()
    results_seq = list(results)
    if not results_seq:
        console.print(Text("No viewpoints found.", style="yellow"))
        return

    for idx, result in enumerate(results_seq, start=1):
        visibility_mean = meters_to_miles(result.visibility.mean_distance_m)
        visibility_median = meters_to_miles(result.visibility.median_distance_m)
        walk = f"{result.drivability.walk_minutes:.1f}" if result.drivability else "n/a"
        drive_minutes = result.drivability.drive_minutes if result.drivability else None
        drive = f"{drive_minutes:.1f}" if drive_minutes is not None else "n/a"
        if result.drivability and result.drivability.drive_distance_km is not None:
            drive_distance = f"{kilometers_to_miles(result.drivability.drive_distance_km):.2f}"
        else:
            drive_distance = "n/a"
        straight_line = f"{result.straight_line_miles:.2f}"
        location = _format_location(result.candidate_latlon, result.candidate.elevation_m)
        access = (
            _format_location(result.access_latlon, result.access_altitude_m)
            if result.access_latlon
            else "n/a"
        )
        lines = [
            f"Coords: {location}",
            (
                "Visibility: "
                f"mean {visibility_mean:.2f} mi | median {visibility_median:.2f} mi | "
                f"FOV {result.visibility.actual_fov_deg:.1f}°"
            ),
            (
                "Travel: "
                f"walk {walk} min | drive {drive} min | "
                f"drive dist {drive_distance} mi | straight {straight_line} mi"
            ),
        ]
        if access != "n/a":
            lines.append(f"Access: {access}")
        panel = Panel(
            Text("\n".join(lines)),
            title=f"Rank {idx}",
            border_style="cyan",
            expand=False,
        )
        console.print(panel)

    min_fov_rank, min_fov_result = min(
        enumerate(results_seq, start=1),
        key=lambda item: item[1].visibility.actual_fov_deg,
    )
    console.print(
        Text(
            (
                f"Minimum clear-sector field-of-view: rank {min_fov_rank} "
                f"with {min_fov_result.visibility.actual_fov_deg:.1f}° "
                f"(target ≥ {config.visibility.min_field_of_view_deg:.1f}°)."
            ),
            style="bold green",
        ),
    )

    console.print(
        Text(
            "360° visibility profiles (legend: |<20%, i<40%, ;<60%, .<80%, space ≥80%)",
            style="bold cyan",
        ),
    )
    for idx, result in enumerate(results_seq[:2], start=1):
        profile, markers = _visibility_profile(result, config)
        if not profile:
            continue
        panel_text = Text()
        panel_text.append(markers + "\n", style="yellow")
        panel_text.append(profile, style="cyan")
        subtitle = " ".join(
            [f"{label}@{angle}°" for label, angle in (("N", 0), ("E", 90), ("S", 180), ("W", 270))],
        )
        console.print(
            Panel(
                panel_text,
                title=(
                    f"Rank {idx} • "
                    f"{result.candidate_latlon[0]:.5f}, {result.candidate_latlon[1]:.5f} "
                    f"({result.candidate.elevation_m:.1f} m)"
                ),
                subtitle=subtitle,
                expand=False,
            ),
        )


def _render_plain(results: Iterable[ViewpointResult]) -> None:
    for idx, result in enumerate(results, start=1):
        LOG.info(
            (
                "[%d] location=%s visibility_mean=%.2fmi "
                "visibility_median=%.2fmi fov=%.1f walk=%.1fmin drive=%.1fmin straight=%.2fmi"
            ),
            idx,
            _format_location(result.candidate_latlon, result.candidate.elevation_m),
            meters_to_miles(result.visibility.mean_distance_m),
            meters_to_miles(result.visibility.median_distance_m),
            result.visibility.actual_fov_deg,
            result.drivability.walk_minutes if result.drivability else float("nan"),
            result.drivability.drive_minutes if result.drivability else float("nan"),
            result.straight_line_miles,
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
        "drive_distance_km",
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
                    "drive_minutes": (
                        result.drivability.drive_minutes if result.drivability else None
                    ),
                    "drive_distance_km": (
                        result.drivability.drive_distance_km if result.drivability else None
                    ),
                    "access_lat": result.access_latlon[0] if result.access_latlon else None,
                    "access_lon": result.access_latlon[1] if result.access_latlon else None,
                    "access_altitude_m": result.access_altitude_m,
                    "straight_line_miles": result.straight_line_miles,
                },
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
                    "drive_minutes": (
                        result.drivability.drive_minutes if result.drivability else None
                    ),
                    "drive_distance_km": (
                        result.drivability.drive_distance_km if result.drivability else None
                    ),
                    "access_lat": result.access_latlon[0] if result.access_latlon else None,
                    "access_lon": result.access_latlon[1] if result.access_latlon else None,
                },
            },
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
                },
            )

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(geojson, handle, indent=2)
    LOG.info("GeoJSON exported to %s", path)


def _format_location(
    latlon: tuple[float, float] | None,
    elevation_m: float | None,
) -> str:
    if latlon is None:
        return "n/a"
    elev_text = "n/a"
    if elevation_m is not None and not math.isnan(elevation_m):
        elev_text = f"{elevation_m:.1f} m"
    return f"{latlon[0]:.5f}, {latlon[1]:.5f} ({elev_text})"


def _visibility_profile(
    result: ViewpointResult,
    config: AppConfig,
) -> tuple[str, str]:
    rays = result.visibility.ray_results
    if not rays:
        return "", ""
    max_distance_m = config.terrain.max_visibility_km * 1000.0
    angles = sorted(rays.keys())
    symbols: list[str] = []
    for angle in angles:
        distance = max(0.0, rays[angle])
        ratio = 0.0 if max_distance_m == 0 else min(distance / max_distance_m, 1.0)
        symbols.append(_symbol_for_ratio(ratio))
    profile = "".join(symbols)
    markers = [" "] * len(profile)
    for label, target_angle in (("N", 0.0), ("E", 90.0), ("S", 180.0), ("W", 270.0)):
        idx = _closest_angle_index(angles, target_angle)
        markers[idx] = label
    return profile, "".join(markers)


def _symbol_for_ratio(ratio: float) -> str:
    for threshold, symbol in (
        (0.20, "|"),
        (0.40, "i"),
        (0.60, ";"),
        (0.80, "."),
    ):
        if ratio < threshold:
            return symbol
    return " "


def _closest_angle_index(angles: list[float], target: float) -> int:
    def angular_distance(candidate: float, goal: float) -> float:
        diff = abs(candidate - goal) % 360.0
        return min(diff, 360.0 - diff)

    return min(range(len(angles)), key=lambda idx: angular_distance(angles[idx], target))
