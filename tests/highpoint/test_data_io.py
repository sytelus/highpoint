from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from affine import Affine
from scripts.fetch_datasets import tiles_for_bbox
from shapely.geometry import LineString

from highpoint.config import load_config
from highpoint.data.roads import RoadNetwork
from highpoint.data.terrain import TerrainLoader, generate_synthetic_dem, save_grid_to_geotiff
from highpoint.pipeline import run_pipeline

gpd = pytest.importorskip("geopandas")
rasterio = pytest.importorskip("rasterio")


def test_tiles_for_bbox__returns_unique_tile_ids() -> None:
    tiles = tiles_for_bbox(47.1, 47.9, -123.5, -122.2)
    assert set(tiles) == {"n47w124", "n47w123"}


def test_terrain_loader_reprojects_to_target_crs(tmp_path: Path) -> None:
    dataset_path = tmp_path / "latlon_dem.tif"
    transform = Affine.translation(-122.5, 47.6) * Affine.scale(0.00025, -0.00025)
    data = np.linspace(100, 120, 100, dtype=np.float32).reshape(10, 10)
    with rasterio.open(
        dataset_path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(data, 1)

    loader = TerrainLoader(dataset_path)
    bounds = (-122.5, 47.6 - 0.002, -122.45, 47.6)
    grid = loader.read(bounds=bounds, target_crs="EPSG:32610")

    assert grid.crs == "EPSG:32610"
    assert grid.elevations.shape[0] > 0 and grid.elevations.shape[1] > 0
    assert np.isfinite(grid.elevations).any()


def test_road_network_from_geojson__loads_lines(tmp_path: Path) -> None:
    geojson_path = tmp_path / "roads.geojson"
    gdf = gpd.GeoDataFrame(
        {"name": ["Test Road"]},
        geometry=[LineString([(500000, 5_200_000), (500500, 5_200_500)])],
        crs="EPSG:32610",
    )
    gdf.to_file(geojson_path, driver="GeoJSON")

    network = RoadNetwork.from_geojson(geojson_path, target_crs="EPSG:32610")
    result = network.nearest_access_point((500100, 5_200_050), walking_speed_kmh=5.0)

    assert 0.0 <= result.distance_m <= 200.0


def test_load_config_with_file_and_overrides(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    config_path = Path("configs/toyrun.yaml")
    config = load_config(
        observer_lat=47.6,
        observer_lon=-122.3,
        observer_alt=100,
        azimuth=0.0,
        min_visibility_miles=1.0,
        min_fov_deg=25.0,
        results_limit=3,
        config_path=config_path,
        overrides={"output.results_limit": 2},
    )

    assert config.output.results_limit == 2
    assert config.terrain.data_path is not None
    assert config.terrain.data_path.is_absolute()
    assert config.terrain.data_path.exists()


def test_pipeline_with_external_files(tmp_path: Path) -> None:
    dem_path = tmp_path / "dem.tif"
    grid = generate_synthetic_dem()
    save_grid_to_geotiff(grid, dem_path)

    lines = [
        LineString(
            [
                (grid.transform.c + 200, grid.transform.f - 200),
                (grid.transform.c + 800, grid.transform.f - 200),
            ],
        ),
    ]
    road_geojson = tmp_path / "roads.geojson"
    gdf = gpd.GeoDataFrame({}, geometry=lines, crs="EPSG:32610")
    gdf.to_file(road_geojson, driver="GeoJSON")

    config = load_config(
        observer_lat=46.95,
        observer_lon=-122.99,
        observer_alt=0.0,
        azimuth=0.0,
        min_visibility_miles=0.5,
        min_fov_deg=30.0,
        results_limit=3,
        overrides={
            "terrain.data_path": str(dem_path),
            "roads.data_path": str(road_geojson),
            "terrain.search_radius_km": 3.0,
            "roads.max_walk_minutes": 20.0,
            "visibility.obstruction_start_m": 5.0,
            "visibility.obstruction_height_m": 1.8,
        },
    )

    output = run_pipeline(config)

    assert output.results
    for result in output.results:
        assert result.drivability is not None
        assert result.drivability.drive_minutes is not None
        assert result.drivability.drive_distance_km is not None
