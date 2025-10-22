from __future__ import annotations

from pathlib import Path

import pytest

from highpoint.data.discovery import (
    DatasetNotFoundError,
    discover_roads_path,
    discover_terrain_paths,
    load_terrain_grid,
)
from highpoint.utils import utm_epsg_for_latlon


def test_discover_terrain_paths_finds_repo_tile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    lat = 46.9480
    lon = -122.9920
    paths, bounds = discover_terrain_paths(lat, lon, radius_km=5.0)
    assert any(path.name.endswith("dem_synthetic.tif") for path in paths)
    epsg = utm_epsg_for_latlon(lat, lon)
    grid = load_terrain_grid(paths, bounds, resolution_scale=1.0, target_crs=f"EPSG:{epsg}")
    assert grid.width > 0 and grid.height > 0


def test_discover_roads_path_finds_repo_cache(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    path, _ = discover_roads_path(46.9480, -122.9920, radius_km=5.0)
    assert path.name.endswith("roads_synthetic.geojson")


def test_discover_terrain_paths_missing_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    with pytest.raises(DatasetNotFoundError) as excinfo:
        discover_terrain_paths(10.0, 10.0, radius_km=5.0)
    message = str(excinfo.value)
    assert "scripts/fetch_datasets.py" in message
