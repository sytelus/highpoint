"""Generate a synthetic DEM GeoTIFF for testing without external downloads."""

from __future__ import annotations

from pathlib import Path

import typer

from highpoint.data.terrain import generate_synthetic_dem, save_grid_to_geotiff

PROJECT_ROOT = Path(__file__).resolve().parent.parent

app = typer.Typer(help="Create synthetic DEM assets for tests or demos.")


@app.command()
def main(
    output: Path = typer.Argument(
        PROJECT_ROOT / "data" / "toy" / "dem_synthetic.tif",
        help="Output GeoTIFF path.",
    ),
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    grid = generate_synthetic_dem()
    save_grid_to_geotiff(grid, output)
    typer.echo(f"Synthetic DEM written to {output}")


if __name__ == "__main__":
    app()
