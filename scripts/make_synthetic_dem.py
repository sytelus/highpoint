"""Generate a synthetic DEM GeoTIFF for testing without external downloads."""

from __future__ import annotations

from pathlib import Path

import typer

from highpoint.data.terrain import generate_synthetic_dem, save_grid_to_geotiff

app = typer.Typer(help="Create synthetic DEM assets for tests or demos.")


@app.command()
def main(
    output: Path = typer.Argument(
        Path("assets/sample_data/dem_synthetic.tif"), help="Output GeoTIFF path."
    )
) -> None:
    grid = generate_synthetic_dem()
    save_grid_to_geotiff(grid, output)
    typer.echo(f"Synthetic DEM written to {output}")


if __name__ == "__main__":
    app()
