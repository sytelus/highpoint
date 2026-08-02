"""Build a clipped road GeoJSON cache using OpenStreetMap data."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from pathlib import Path
from typing import cast

import networkx as nx
import osmnx as ox
import typer

from highpoint.config import data_root

GraphFromBBox = Callable[..., nx.MultiDiGraph]
GRAPH_FROM_BBOX = cast(GraphFromBBox, ox.graph_from_bbox)

SEDAN_HIGHWAY_FILTER = (
    '["highway"]["highway"!~"footway|steps|path|cycleway|bridleway|track|service"]'
    '["motor_vehicle"!~"no"]["access"!~"no|private"]'
)


def _default_output() -> Path:
    return (data_root(create=False) / "roads" / "cache" / "roads.geojson").resolve()


app = typer.Typer(help="Build a cached GeoJSON of drivable roads using OpenStreetMap data.")


def _graph_from_bbox(
    *,
    north: float,
    south: float,
    east: float,
    west: float,
    network_type: str,
    custom_filter: str | None,
) -> nx.MultiDiGraph:
    """Call the OSMnx 1.x or 2.x bounding-box API as installed."""
    parameters = inspect.signature(GRAPH_FROM_BBOX).parameters
    if "bbox" in parameters:
        return GRAPH_FROM_BBOX(
            bbox=(west, south, east, north),
            network_type=network_type,
            custom_filter=custom_filter,
        )
    return GRAPH_FROM_BBOX(
        north,
        south,
        east,
        west,
        network_type=network_type,
        custom_filter=custom_filter,
    )


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
    if south >= north:
        raise typer.BadParameter("--south must be less than --north")
    if west >= east:
        raise typer.BadParameter("--west must be less than --east")

    graph = _graph_from_bbox(
        north=north,
        south=south,
        east=east,
        west=west,
        network_type=network_type,
        custom_filter=custom_filter,
    )
    edges = ox.graph_to_gdfs(
        graph,
        edges=True,
        nodes=False,
        fill_edge_geometry=True,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    edges.to_file(output, driver="GeoJSON")
    typer.echo(f"Road GeoJSON written to {output}")


if __name__ == "__main__":
    app()
