from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from affine import Affine

from highpoint.analysis.candidates import identify_candidates
from highpoint.data.terrain import TerrainGrid, TerrainLoader
from highpoint.pipeline import _sample_elevation
from highpoint.utils import utm_epsg_for_latlon


def test_rotated_grid_coordinates__apply_full_affine_transform() -> None:
    transform = Affine(10.0, 2.0, 100.0, 3.0, -20.0, 200.0)
    grid = TerrainGrid(
        elevations=np.zeros((2, 2), dtype=np.float32),
        transform=transform,
        crs="EPSG:32610",
    )

    xs, ys = grid.coordinates()

    expected_x, expected_y = transform * (0.5, 0.5)
    assert xs[0, 0] == pytest.approx(expected_x)
    assert ys[0, 0] == pytest.approx(expected_y)
    assert grid.resolution == pytest.approx((np.hypot(10.0, 3.0), np.hypot(2.0, -20.0)))


def test_terrain_loader_nodata__normalizes_to_nan(tmp_path: Path) -> None:
    dataset_path = tmp_path / "nodata.tif"
    data = np.array([[10.0, -9999.0], [20.0, 30.0]], dtype=np.float32)
    with rasterio.open(
        dataset_path,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype="float32",
        crs="EPSG:32610",
        transform=Affine.translation(0.0, 20.0) * Affine.scale(10.0, -10.0),
        nodata=-9999.0,
    ) as destination:
        destination.write(data, 1)

    grid = TerrainLoader(dataset_path).read()

    assert np.isnan(grid.elevations[0, 1])
    assert np.isfinite(grid.elevations[[0, 1, 1], [0, 0, 1]]).all()


def test_terrain_loader_outside_bounds__raises(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dem.tif"
    data = np.ones((2, 2), dtype=np.float32)
    with rasterio.open(
        dataset_path,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype="float32",
        crs="EPSG:32610",
        transform=Affine.translation(0.0, 20.0) * Affine.scale(10.0, -10.0),
    ) as destination:
        destination.write(data, 1)

    with pytest.raises(ValueError, match="do not intersect"):
        TerrainLoader(dataset_path).read(bounds=(100.0, 100.0, 110.0, 110.0))


def test_symmetric_peak__is_retained_by_neighborhood_slope() -> None:
    coordinates = np.arange(21, dtype=np.float64) - 10.0
    xx, yy = np.meshgrid(coordinates, coordinates)
    elevations = 100.0 + 80.0 * np.exp(-((xx**2 + yy**2) / 18.0))
    elevations[0, 0] = np.nan
    grid = TerrainGrid(
        elevations=elevations.astype(np.float32),
        transform=Affine.translation(0.0, 420.0) * Affine.scale(10.0, -20.0),
        crs="EPSG:32610",
    )

    candidates = identify_candidates(grid, min_prominence_m=1.0, min_slope_deg=1.0)

    assert any(candidate.row == 10 and candidate.col == 10 for candidate in candidates)


def test_sample_elevation_at_cell_center__uses_containing_cell() -> None:
    elevations = np.arange(9, dtype=np.float32).reshape(3, 3)
    transform = Affine.translation(100.0, 300.0) * Affine.scale(10.0, -10.0)
    grid = TerrainGrid(elevations=elevations, transform=transform, crs="EPSG:32610")
    x, y = transform * (1.5, 1.5)

    assert _sample_elevation(grid, x, y) == 4.0


@pytest.mark.parametrize(("longitude", "expected"), [(-180.0, 32601), (180.0, 32660)])
def test_utm_zone_at_longitude_boundary__stays_valid(longitude: float, expected: int) -> None:
    assert utm_epsg_for_latlon(10.0, longitude) == expected
