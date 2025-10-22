"""Build a clipped road GeoJSON cache using OpenStreetMap data."""

from __future__ import annotations

import os
from pathlib import Path

import osmnx as ox
import typer

SEDAN_HIGHWAY_FILTER = (
    '["highway"]["highway"!~"footway|steps|path|cycleway|bridleway|track|service"]'
    '["motor_vehicle"!~"no"]["access"!~"private"]'
)


def _default_output() -> Path:
    base = Path(os.environ.get("DATA_ROOT", Path.home() / "data")).expanduser()
    return (base / "highpoint" / "roads" / "cache" / "roads.geojson").resolve()


app = typer.Typer(help="Build a cached GeoJSON of drivable roads using OpenStreetMap data.")


@app.command()
def main(
    north: float = typer.Option(..., help="Northern latitude of bounding box."),
    south: float = typer.Option(..., help="Southern latitude of bounding box."),
    east: float = typer.Option(..., help="Eastern longitude of bounding box."),
    west: float = typer.Option(..., help="Western longitude of bounding box."),
    output: Path = typer.Option(
        _default_output(),
        help="Output GeoJSON path for the filtered network.",
    ),
    network_type: str = typer.Option("drive", help="OSMnx network type to request."),
    custom_filter: str | None = typer.Option(
        SEDAN_HIGHWAY_FILTER,
        help="Custom Overpass filter for drivable roads.",
    ),
) -> None:
    """
    Fetch a drivable road network from OpenStreetMap and export as GeoJSON.

    Requires network connectivity. Bounding box values must be given in decimal degrees.
    """
    bbox = (north, south, east, west)
    graph = ox.graph_from_bbox(
        bbox=bbox,
        network_type=network_type,
        custom_filter=custom_filter,
    )
    _, edges = ox.graph_to_gdfs(graph, edges=True, nodes=False, fill_edge_geometry=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    edges.to_file(output, driver="GeoJSON")
    typer.echo(f"Road GeoJSON written to {output}")


if __name__ == "__main__":
    app()
