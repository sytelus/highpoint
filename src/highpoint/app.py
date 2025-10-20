"""Command-line entry point for HighPoint."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer

from highpoint.config import AppConfig, load_config
from highpoint.pipeline import run_pipeline
from highpoint.render.map import render_map
from highpoint.reporting.report import emit_report

app = typer.Typer(help="HighPoint: find drivable scenic viewpoints with clear visibility.")


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    )


@app.command()
def main(
    latitude: float = typer.Argument(..., help="Observer latitude in decimal degrees."),
    longitude: float = typer.Argument(..., help="Observer longitude in decimal degrees."),
    altitude: float = typer.Option(0.0, "--altitude", "-a", help="Observer altitude above sea level in meters."),
    azimuth: float = typer.Option(
        0.0,
        "--azimuth",
        "-d",
        help="Desired viewing azimuth in compass degrees (0=N).",
    ),
    min_visibility: float = typer.Option(
        3.0,
        "--min-visibility",
        "-k",
        help="Minimum clear visibility distance in miles.",
    ),
    min_fov: float = typer.Option(
        30.0,
        "--min-fov",
        "-g",
        help="Minimum field-of-view in degrees.",
    ),
    results: int = typer.Option(5, "--results", "-n", help="Number of target viewpoints to return."),
    terrain_file: Optional[Path] = typer.Option(
        None,
        "--terrain-file",
        help="Path to a projected DEM GeoTIFF covering the search area.",
    ),
    roads_file: Optional[Path] = typer.Option(
        None,
        "--roads-file",
        help="Path to a GeoJSON snippet of drivable roads in the search area.",
    ),
    search_radius: float = typer.Option(
        30.0,
        "--search-radius",
        help="Search radius in kilometers around the observer.",
    ),
    walk_limit: float = typer.Option(15.0, "--max-walk", help="Maximum walking time in minutes."),
    drive_limit: Optional[float] = typer.Option(
        None,
        "--max-drive",
        help="Optional maximum driving time from observer to access point in minutes.",
    ),
    export_csv: Optional[Path] = typer.Option(None, "--export-csv", help="Optional CSV export path."),
    export_geojson: Optional[Path] = typer.Option(
        None, "--export-geojson", help="Optional GeoJSON export path."
    ),
    render_png: Optional[Path] = typer.Option(None, "--render-png", help="Optional overview PNG path."),
    log_level: str = typer.Option("INFO", "--log-level", help="Logging level (DEBUG, INFO, ...)."),
) -> None:
    """Compute visibility-aware scenic viewpoints."""
    _configure_logging(log_level)

    overrides = {
        "terrain.search_radius_km": search_radius,
        "roads.max_walk_minutes": walk_limit,
        "roads.max_drive_minutes": drive_limit,
        "terrain.data_path": str(terrain_file) if terrain_file else None,
        "roads.data_path": str(roads_file) if roads_file else None,
        "output.export_csv": export_csv,
        "output.export_geojson": export_geojson,
        "output.render_png": render_png,
    }

    config = load_config(
        observer_lat=latitude,
        observer_lon=longitude,
        observer_alt=altitude,
        azimuth=azimuth,
        min_visibility_miles=min_visibility,
        min_fov_deg=min_fov,
        results_limit=results,
        overrides=overrides,
    )

    logging.getLogger(__name__).info("Starting HighPoint pipeline")
    output = run_pipeline(config)
    emit_report(output.results, config)

    if config.output.render_png:
        render_map(output.results, terrain=output.terrain, output_path=config.output.render_png)


if __name__ == "__main__":  # pragma: no cover
    app()
