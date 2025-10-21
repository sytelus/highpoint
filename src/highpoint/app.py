"""Command-line entry point for HighPoint."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import typer

from highpoint.config import AppConfig, load_config
from highpoint.simple_yaml import load_yaml
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
    latitude: float | None = typer.Argument(None, help="Observer latitude in decimal degrees."),
    longitude: float | None = typer.Argument(None, help="Observer longitude in decimal degrees."),
    altitude: float | None = typer.Option(
        None, "--altitude", "-a", help="Observer altitude above sea level in meters."
    ),
    azimuth: float | None = typer.Option(
        None,
        "--azimuth",
        "-d",
        help="Desired viewing azimuth in compass degrees (0=N).",
    ),
    min_visibility: float | None = typer.Option(
        None,
        "--min-visibility",
        "-k",
        help="Minimum clear visibility distance in miles.",
    ),
    min_fov: float | None = typer.Option(
        None,
        "--min-fov",
        "-g",
        help="Minimum field-of-view in degrees.",
    ),
    results: int | None = typer.Option(
        None, "--results", "-n", help="Number of target viewpoints to return."
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Optional OmegaConf YAML configuration to load before applying CLI overrides.",
    ),
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
    search_radius: float | None = typer.Option(
        None,
        "--search-radius",
        help="Search radius in kilometers around the observer.",
    ),
    walk_limit: float | None = typer.Option(
        None, "--max-walk", help="Maximum walking time in minutes."
    ),
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

    file_config: Dict[str, Any] = {}
    if config_file:
        file_config = load_yaml(config_file)

    def get_from_file(path: list[str], default: Any = None) -> Any:
        node: Any = file_config
        for part in path:
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    observer_lat = latitude if latitude is not None else get_from_file(["observer", "latitude"])
    observer_lon = longitude if longitude is not None else get_from_file(["observer", "longitude"])
    if observer_lat is None or observer_lon is None:
        raise typer.BadParameter("Latitude and longitude must be supplied via CLI or config file.")

    observer_alt = altitude if altitude is not None else get_from_file(["observer", "altitude_m"], 0.0)
    azimuth_val = azimuth if azimuth is not None else get_from_file(["visibility", "azimuth_deg"], 0.0)
    min_visibility_val = (
        min_visibility
        if min_visibility is not None
        else get_from_file(["visibility", "min_visibility_miles"], 3.0)
    )
    min_fov_val = min_fov if min_fov is not None else get_from_file(["visibility", "min_field_of_view_deg"], 30.0)
    results_val = results if results is not None else get_from_file(["output", "results_limit"], 5)

    overrides_raw = {
        "terrain.search_radius_km": search_radius,
        "roads.max_walk_minutes": walk_limit,
        "roads.max_drive_minutes": drive_limit,
        "terrain.data_path": terrain_file,
        "roads.data_path": roads_file,
        "output.export_csv": export_csv,
        "output.export_geojson": export_geojson,
        "output.render_png": render_png,
    }
    overrides = {
        key: (str(value) if isinstance(value, Path) else value)
        for key, value in overrides_raw.items()
        if value is not None
    }

    config = load_config(
        observer_lat=observer_lat,
        observer_lon=observer_lon,
        observer_alt=observer_alt,
        azimuth=azimuth_val,
        min_visibility_miles=min_visibility_val,
        min_fov_deg=min_fov_val,
        results_limit=results_val,
        config_path=config_file,
        overrides=overrides,
    )

    logging.getLogger(__name__).info("Starting HighPoint pipeline")
    output = run_pipeline(config)
    emit_report(output.results, config)

    if config.output.render_png:
        render_map(output.results, terrain=output.terrain, output_path=config.output.render_png)


if __name__ == "__main__":  # pragma: no cover
    app()
