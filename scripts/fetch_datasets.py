"""Fetch terrain and road datasets required by HighPoint."""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlretrieve

import typer

from highpoint.data.roads import RoadNetwork
from highpoint.data.terrain import generate_synthetic_dem, save_grid_to_geotiff

SRTM_BASE = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1/TIFF/current"
GEOFABRIK_BASE = "https://download.geofabrik.de"

app = typer.Typer(help="Download HighPoint terrain and road datasets.")
PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class RegionConfig:
    name: str
    bbox: tuple[float, float, float, float] | None
    terrain_tiles: list[str] | None
    roads_url: str | None
    description: str


REGIONS = {
    "toy": RegionConfig(
        name="toy",
        bbox=None,
        terrain_tiles=None,
        roads_url=None,
        description="Synthetic 2km x 2km DEM and small GeoJSON road grid for tests.",
    ),
    "washington": RegionConfig(
        name="washington",
        bbox=(45.5, 49.0, -125.0, -116.0),
        terrain_tiles=None,
        roads_url=f"{GEOFABRIK_BASE}/north-america/us/washington-latest.osm.pbf",
        description=(
            "Washington State coverage using SRTM 1 arc-second tiles and Geofabrik " "OSM extract."
        ),
    ),
    "us": RegionConfig(
        name="us",
        bbox=(24.0, 50.0, -125.0, -66.0),
        terrain_tiles=None,
        roads_url=f"{GEOFABRIK_BASE}/north-america/us-latest.osm.pbf",
        description="Contiguous United States coverage (large downloads).",
    ),
}


def data_root() -> Path:
    base = Path(os.environ.get("DATA_ROOT", Path.home() / "data")).expanduser()
    root = (base / "highpoint").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def ensure_directories(root: Path) -> None:
    for path in [
        root / "terrain" / "raw",
        root / "terrain" / "cache",
        root / "roads" / "raw",
        root / "roads" / "cache",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def tiles_for_bbox(lat_min: float, lat_max: float, lon_min: float, lon_max: float) -> list[str]:
    """Return SRTM tile identifiers for the provided bounding box."""
    tiles: list[str] = []
    lat_start = math.floor(lat_min)
    lat_end = math.ceil(lat_max)
    lon_start = math.floor(lon_min)
    lon_end = math.ceil(lon_max)

    for lat in range(lat_start, lat_end):
        for lon in range(lon_start, lon_end):
            lat_prefix = "n" if lat >= 0 else "s"
            lon_prefix = "e" if lon >= 0 else "w"
            tile = f"{lat_prefix}{abs(lat):02d}{lon_prefix}{abs(lon):03d}"
            tiles.append(tile)
    return tiles


def tile_url(tile: str) -> str:
    return f"{SRTM_BASE}/{tile}/USGS_1_{tile}.tif"


def download(url: str, destination: Path, dry_run: bool) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        typer.echo(f"Skipping existing {destination}")
        return

    typer.echo(f"{'DRY RUN: would download' if dry_run else 'Downloading'} {url}")
    if dry_run:
        return
    try:
        urlretrieve(url, destination)
    except Exception as exc:  # pragma: no cover - network errors not in tests
        raise RuntimeError(f"Failed to download {url}") from exc


def create_toy_assets(dry_run: bool) -> None:
    toy_dir = PROJECT_ROOT / "data" / "toy"
    dem_path = toy_dir / "dem_synthetic.tif"
    roads_path = toy_dir / "roads_synthetic.geojson"
    typer.echo("Generating synthetic DEM and road assets in repository toy directory.")
    toy_dir.mkdir(parents=True, exist_ok=True)
    if dem_path.exists() and roads_path.exists():
        typer.echo("Toy assets already exist; skipping regeneration.")
        return
    if dry_run:
        typer.echo("DRY RUN: skipping synthetic asset creation.")
        return
    dem = generate_synthetic_dem()
    save_grid_to_geotiff(dem, dem_path)
    road_network = RoadNetwork.synthetic()
    features = []
    for line in road_network.geometries:
        features.append(
            {
                "type": "Feature",
                "geometry": json.loads(json.dumps(line.__geo_interface__)),
                "properties": {"source": "synthetic"},
            },
        )
    geojson = {"type": "FeatureCollection", "features": features}
    roads_path.write_text(json.dumps(geojson, indent=2), encoding="utf-8")


@app.command()
def main(
    region: str = typer.Option(
        "toy",
        "--region",
        "-r",
        help="Dataset region: toy, washington, us.",
        case_sensitive=False,
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print actions without downloading."),
) -> None:
    """
    Download terrain and road datasets for the specified region.

    Use --dry-run to preview downloads and derived assets without making changes.
    """
    root = data_root()
    ensure_directories(root)
    key = region.lower()
    if key not in REGIONS:
        typer.echo(f"Unknown region '{region}'. Choose from: {', '.join(REGIONS)}", err=True)
        raise typer.Exit(code=1)

    cfg = REGIONS[key]
    typer.echo(f"Preparing datasets for region '{cfg.name}': {cfg.description}")

    if cfg.name == "toy":
        create_toy_assets(dry_run=dry_run)
        typer.echo("Toy dataset ready.")
        raise typer.Exit(code=0)

    tiles = cfg.terrain_tiles or tiles_for_bbox(*cfg.bbox)  # type: ignore[arg-type]
    typer.echo(f"Preparing to download {len(tiles)} SRTM tiles.")
    manifest_lines = []
    for tile in tiles:
        url = tile_url(tile)
        filename = root / "terrain" / "raw" / f"{tile}.tif"
        download(url, filename, dry_run=dry_run)
        manifest_lines.append(filename.name)

    if cfg.roads_url:
        roads_dest = root / "roads" / "raw" / Path(cfg.roads_url).name
        download(cfg.roads_url, roads_dest, dry_run=dry_run)

    if not dry_run:
        manifest_path = root / "terrain" / f"{cfg.name}_tiles.txt"
        manifest_path.write_text("\n".join(sorted(manifest_lines)), encoding="utf-8")
        typer.echo(f"Tile manifest written to {manifest_path}")

    typer.echo("Download complete.")


if __name__ == "__main__":
    app()
