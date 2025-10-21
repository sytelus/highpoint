"""Digital elevation model loading and convenience utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple

import numpy as np
import rasterio
from numpy.typing import NDArray
from rasterio.enums import Resampling
from rasterio.transform import Affine
from rasterio.windows import from_bounds


@dataclass(frozen=True)
class TerrainGrid:
    """Represents a DEM subset in a projected coordinate system."""

    elevations: NDArray[np.float32]
    transform: Affine
    crs: str

    @property
    def resolution(self) -> Tuple[float, float]:
        """Return pixel size in projected units."""
        return self.transform.a, -self.transform.e

    @property
    def height(self) -> int:
        return self.elevations.shape[0]

    @property
    def width(self) -> int:
        return self.elevations.shape[1]

    def coordinates(self) -> Tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Return meshgrid arrays of x, y projected coordinates at cell centers."""
        rows = np.arange(self.height, dtype=np.float64)
        cols = np.arange(self.width, dtype=np.float64)
        col_grid, row_grid = np.meshgrid(cols, rows)
        xs = self.transform.c + (col_grid + 0.5) * self.transform.a
        ys = self.transform.f + (row_grid + 0.5) * self.transform.e
        return xs, ys

    def subset(self, bounds: Tuple[float, float, float, float]) -> "TerrainGrid":
        """Return a clipped grid within projected bounds (minx, miny, maxx, maxy)."""
        window = from_bounds(*bounds, transform=self.transform)
        row_off = int(window.row_off)
        col_off = int(window.col_off)
        height = int(window.height)
        width = int(window.width)
        sub = self.elevations[row_off : row_off + height, col_off : col_off + width]
        new_transform = self.transform * Affine.translation(col_off, row_off)
        return TerrainGrid(elevations=sub, transform=new_transform, crs=self.crs)


class TerrainLoader:
    """Responsible for loading and resampling DEM tiles."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read(
        self,
        bounds: Tuple[float, float, float, float] | None = None,
        resolution_scale: float = 1.0,
        target_crs: str | None = None,
    ) -> TerrainGrid:
        """
        Read DEM data optionally clipped to bounds and resampled via averaging.

        Bounds are expressed in the dataset CRS (typically meters after reprojection).
        """
        with rasterio.open(self.path) as dataset:
            transform = dataset.transform
            array: NDArray[np.float32]
            if bounds is not None:
                window = from_bounds(*bounds, transform=transform)
            else:
                window = None

            if resolution_scale == 1.0:
                array = dataset.read(1, window=window, out_dtype=np.float32)
                out_transform = dataset.window_transform(window) if window else transform
            else:
                scale = 1.0 / resolution_scale
                out_shape = (
                    int(dataset.height * scale),
                    int(dataset.width * scale),
                )
                array = dataset.read(
                    1,
                    out_shape=out_shape,
                    resampling=Resampling.average,
                    out_dtype=np.float32,
                    window=window,
                )
                if window:
                    out_transform = dataset.window_transform(window)
                else:
                    out_transform = transform
                out_transform = out_transform * Affine.scale(resolution_scale)

            src_crs = dataset.crs
            if target_crs and src_crs and src_crs.to_string() != target_crs:
                from rasterio.warp import Resampling, calculate_default_transform, reproject
                if window is not None:
                    src_bounds = rasterio.windows.bounds(window, transform)
                else:
                    src_bounds = dataset.bounds
                dest_transform, dest_width, dest_height = calculate_default_transform(
                    src_crs, target_crs, array.shape[1], array.shape[0], *src_bounds
                )
                destination = np.empty((dest_height, dest_width), dtype=np.float32)
                reproject(
                    source=array,
                    destination=destination,
                    src_transform=out_transform,
                    src_crs=src_crs,
                    dst_transform=dest_transform,
                    dst_crs=target_crs,
                    resampling=Resampling.bilinear,
                    dst_nodata=np.nan,
                )
                array = destination
                out_transform = dest_transform
                crs_out = target_crs
            else:
                crs_out = src_crs.to_string() if src_crs else target_crs or ""

            return TerrainGrid(
                elevations=array,
                transform=out_transform,
                crs=crs_out,
            )


def generate_synthetic_dem(
    size: Tuple[int, int] = (40, 40),
    base_height: float = 50.0,
    peak_height: float = 200.0,
) -> TerrainGrid:
    """
    Create a synthetic DEM with a gentle slope and a single peak for tests.

    The grid uses an arbitrary 30 m resolution and EPSG:32610 projection.
    """
    rows, cols = size
    y = np.linspace(0, 1, rows)
    x = np.linspace(0, 1, cols)
    xx, yy = np.meshgrid(x, y)
    slope = base_height + 20 * yy
    center = np.exp(-((xx - 0.5) ** 2 + (yy - 0.4) ** 2) * 12.0)
    elevations = slope + center * (peak_height - base_height)
    transform = Affine.translation(500000, 5_200_000) * Affine.scale(30, -30)
    return TerrainGrid(
        elevations=elevations.astype(np.float32),
        transform=transform,
        crs="EPSG:32610",
    )


def save_grid_to_geotiff(grid: TerrainGrid, path: Path) -> None:
    """Persist a TerrainGrid to disk for reuse or inspection."""
    path.parent.mkdir(parents=True, exist_ok=True)
    height, width = grid.elevations.shape
    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": rasterio.float32,
        "crs": grid.crs,
        "transform": grid.transform,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(grid.elevations, 1)


def flatten_coordinates(grid: TerrainGrid) -> NDArray[np.float64]:
    """Return Nx2 array of projected coordinates for each cell."""
    xs, ys = grid.coordinates()
    stacked = np.column_stack((xs.ravel(), ys.ravel()))
    return stacked


def iter_coordinates(grid: TerrainGrid) -> Iterable[Tuple[float, float]]:
    """Yield projected coordinate tuples for each cell."""
    xs, ys = grid.coordinates()
    for x, y in zip(xs.ravel(), ys.ravel()):
        yield float(x), float(y)
