from __future__ import annotations

import networkx as nx
import pytest

from highpoint.scripts import build_road_cache


def test_graph_from_bbox_with_osmnx_2__uses_bbox_keyword(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = nx.MultiDiGraph()
    received: list[tuple[float, float, float, float]] = []

    def modern(
        *,
        bbox: tuple[float, float, float, float],
        network_type: str,
        custom_filter: str | None,
    ) -> nx.MultiDiGraph:
        del network_type, custom_filter
        received.append(bbox)
        return graph

    monkeypatch.setattr(build_road_cache, "GRAPH_FROM_BBOX", modern)

    result = build_road_cache._graph_from_bbox(
        north=48.0,
        south=47.0,
        east=-121.0,
        west=-123.0,
        network_type="drive",
        custom_filter=None,
    )

    assert result is graph
    assert received == [(-123.0, 47.0, -121.0, 48.0)]


def test_graph_from_bbox_with_osmnx_1__uses_positional_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = nx.MultiDiGraph()
    received: list[tuple[float, float, float, float]] = []

    def legacy(
        north: float,
        south: float,
        east: float,
        west: float,
        *,
        network_type: str,
        custom_filter: str | None,
    ) -> nx.MultiDiGraph:
        del network_type, custom_filter
        received.append((north, south, east, west))
        return graph

    monkeypatch.setattr(build_road_cache, "GRAPH_FROM_BBOX", legacy)

    result = build_road_cache._graph_from_bbox(
        north=48.0,
        south=47.0,
        east=-121.0,
        west=-123.0,
        network_type="drive",
        custom_filter=None,
    )

    assert result is graph
    assert received == [(48.0, 47.0, -121.0, -123.0)]
