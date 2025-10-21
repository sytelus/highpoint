"""Build a clipped road GeoJSON cache using OpenStreetMap data."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

import osmnx as ox
import typer

SEDAN_HIGHWAY_FILTER = (
    '["highway"]["highway"!~"footway|steps|path|cycleway|bridleway|track|service"]["motor_vehicle"!~"no"]["access"!~"private"]'
)

app = typer.Typer(help="Build a cached GeoJSON of drivable roads using OpenStreetMap data.")


@app.command()
def main(
    north: float = typer.Option(..., help="Northern latitude of bounding box."),
    south: float = typer.Option(..., help="Southern latitude of bounding box."),
    east: float = typer.Option(..., help="Eastern longitude of bounding box."),
    west: float = typer.Option(..., help="Western longitude of bounding box."),
    output: Path = typer.Option(
        Path(os.environ.get("DATA_ROOT", "data")) / "roads" / "cache" / "roads.geojson",
        help="Output GeoJSON path for the filtered network.",
    ),
    network_type: str = typer.Option("drive", help="OSMnx network type to request."),
    custom_filter: Optional[str] = typer.Option(
        SEDAN_HIGHWAY_FILTER, help="Custom Overpass filter for drivable roads."
    ),
) -> None:
    """
    Fetch a drivable road network from OpenStreetMap and export as GeoJSON.

    Requires network connectivity. Bounding box values must be given in decimal degrees.
    """
    graph = ox.graph_from_bbox(
        north=north,
        south=south,
        east=east,
        west=west,
        network_type=network_type,
        custom_filter=custom_filter,
    )
    _, edges = ox.graph_to_gdfs(graph, edges=True, nodes=False, fill_edge_geometry=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    edges.to_file(output, driver="GeoJSON")
    typer.echo(f"Road GeoJSON written to {output}")


if __name__ == "__main__":
    app()
