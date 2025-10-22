"""Automatic dataset discovery and loading helpers."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Geod, Transformer
from rasterio.crs import CRS
from rasterio.merge import merge as raster_merge
from rasterio.transform import Affine, array_bounds
from rasterio.warp import (
    Resampling as WarpResampling,
)
from rasterio.warp import (
    calculate_default_transform,
    reproject,
    transform_bounds,
)

from highpoint.config import PROJECT_ROOT, data_root
from highpoint.data.roads import _looks_projected, _read_geo_dataframe
from highpoint.data.terrain import TerrainGrid
from highpoint.utils import utm_epsg_for_latlon

LOG = logging.getLogger(__name__)
GEOD = Geod(ellps="WGS84")

SearchBounds = tuple[float, float, float, float]  # (lat_min, lat_max, lon_min, lon_max)


class DatasetNotFoundError(RuntimeError):
    """Raised when required terrain or road datasets cannot be located."""

    def __init__(self, dataset_type: str, message: str) -> None:
        self.dataset_type = dataset_type
        super().__init__(message)


@dataclass(frozen=True)
class TerrainAsset:
    path: Path
    bounds: tuple[float, float, float, float]


@dataclass(frozen=True)
class RoadAsset:
    path: Path
    bounds: tuple[float, float, float, float]


def compute_search_bounds(latitude: float, longitude: float, radius_km: float) -> SearchBounds:
    """Compute a latitude/longitude bounding box around a point with a radius in km."""
    radius_m = radius_km * 1000.0
    lon_north, lat_north, _ = GEOD.fwd(longitude, latitude, 0.0, radius_m)
    lon_south, lat_south, _ = GEOD.fwd(longitude, latitude, 180.0, radius_m)
    lon_east, lat_east, _ = GEOD.fwd(longitude, latitude, 90.0, radius_m)
    lon_west, lat_west, _ = GEOD.fwd(longitude, latitude, 270.0, radius_m)
    lat_min = min(latitude, lat_north, lat_south, lat_east, lat_west)
    lat_max = max(latitude, lat_north, lat_south, lat_east, lat_west)
    lon_min = min(longitude, lon_north, lon_south, lon_east, lon_west)
    lon_max = max(longitude, lon_north, lon_south, lon_east, lon_west)
    return (lat_min, lat_max, lon_min, lon_max)


def discover_terrain_paths(
    latitude: float,
    longitude: float,
    radius_km: float,
    prefer_source: str | None = None,
    search_dirs: Sequence[Path] | None = None,
) -> tuple[tuple[Path, ...], SearchBounds]:
    """
    Identify DEM files that intersect the requested search window.

    Returns a tuple of paths and the computed lat/lon bounds. Raises DatasetNotFoundError
    when no candidates exist or coverage is insufficient.
    """
    bounds = compute_search_bounds(latitude, longitude, radius_km)
    directories = _terrain_directories(search_dirs)
    entries = _terrain_entries(tuple(str(path) for path in directories))

    candidates = [asset for asset in entries if _bounds_intersect(asset.bounds, bounds)]

    if not candidates:
        message = _missing_terrain_message(
            latitude,
            longitude,
            radius_km,
            directories,
            prefer_source,
        )
        raise DatasetNotFoundError("terrain", message)

    paths = tuple(asset.path for asset in candidates)
    LOG.debug(
        "Resolved %d terrain file(s) for %.4f°, %.4f° radius %.1f km",
        len(paths),
        latitude,
        longitude,
        radius_km,
    )
    return paths, bounds


def load_terrain_grid(
    paths: Sequence[Path],
    bounds_latlon: SearchBounds,
    resolution_scale: float,
    target_crs: str,
) -> TerrainGrid:
    """
    Merge one or more DEM rasters into the target CRS and clip to bounds.

    If the requested bounds produce no pixels, the full extent of the rasters is used
    before signalling insufficient coverage.
    """
    datasets = [rasterio.open(path) for path in paths]
    try:
        source_crs = datasets[0].crs
        if source_crs is None:
            raise DatasetNotFoundError(
                "terrain",
                f"DEM {paths[0]} is missing CRS metadata.",
            )
        lat_min, lat_max, lon_min, lon_max = bounds_latlon
        bounds_source = transform_bounds(
            "EPSG:4326",
            source_crs,
            lon_min,
            lat_min,
            lon_max,
            lat_max,
            densify_pts=21,
        )
        try:
            merged, transform = raster_merge(datasets, bounds=bounds_source)
        except ValueError:
            LOG.debug(
                "Bounds %s produced empty mosaic; falling back to full extent.",
                bounds_latlon,
            )
            merged, transform = raster_merge(datasets)
    finally:
        for dataset in datasets:
            dataset.close()

    array = merged[0].astype(np.float32)
    out_transform = transform
    current_crs = source_crs

    if CRS.from_user_input(current_crs).to_string() != target_crs:
        bounds_proj = array_bounds(array.shape[0], array.shape[1], out_transform)
        dest_transform, dest_width, dest_height = calculate_default_transform(
            current_crs,
            target_crs,
            array.shape[1],
            array.shape[0],
            *bounds_proj,
        )
        destination = np.empty((dest_height, dest_width), dtype=np.float32)
        reproject(
            source=array,
            destination=destination,
            src_transform=out_transform,
            src_crs=current_crs,
            dst_transform=dest_transform,
            dst_crs=target_crs,
            resampling=WarpResampling.bilinear,
            dst_nodata=np.nan,
            num_threads=1,
        )
        array = destination
        out_transform = dest_transform
        current_crs = target_crs

    if resolution_scale != 1.0:
        scale = 1.0 / resolution_scale
        out_height = max(1, int(round(array.shape[0] * scale)))
        out_width = max(1, int(round(array.shape[1] * scale)))
        destination = np.empty((out_height, out_width), dtype=np.float32)
        reproject(
            source=array,
            destination=destination,
            src_transform=out_transform,
            src_crs=current_crs,
            dst_transform=out_transform * Affine.scale(resolution_scale),
            dst_crs=current_crs,
            resampling=WarpResampling.average,
            dst_nodata=np.nan,
            num_threads=1,
        )
        array = destination
        out_transform = out_transform * Affine.scale(resolution_scale)

    crs_value = (
        current_crs
        if isinstance(current_crs, str)
        else CRS.from_user_input(current_crs).to_string()
    )
    grid = TerrainGrid(elevations=array, transform=out_transform, crs=crs_value)

    _validate_grid_coverage(grid, bounds_latlon)
    return grid


def discover_roads_path(
    latitude: float,
    longitude: float,
    radius_km: float,
    prefer_source: str | None = None,
    search_dirs: Sequence[Path] | None = None,
) -> tuple[Path, SearchBounds]:
    """
    Identify a cached road GeoJSON covering the requested window.

    Returns the selected path and the search bounds. Raises DatasetNotFoundError when none
    were found.
    """
    bounds = compute_search_bounds(latitude, longitude, radius_km)
    directories = _roads_directories(search_dirs)
    approx_epsg = utm_epsg_for_latlon(latitude, longitude)
    entries = _road_entries(tuple(str(path) for path in directories), approx_epsg)

    covering: list[tuple[RoadAsset, float]] = []
    for asset in entries:
        if _bounds_intersect(asset.bounds, bounds):
            coverage = _coverage_fraction(asset.bounds, bounds)
            covering.append((asset, coverage))

    if not covering:
        message = _missing_roads_message(
            latitude,
            longitude,
            radius_km,
            directories,
            prefer_source,
            bounds,
        )
        raise DatasetNotFoundError("roads", message)

    covering.sort(key=lambda item: item[1], reverse=True)
    best_asset = covering[0][0]
    LOG.debug(
        "Resolved road dataset %s for %.4f°, %.4f° radius %.1f km",
        best_asset.path,
        latitude,
        longitude,
        radius_km,
    )
    return best_asset.path, bounds


def _validate_grid_coverage(grid: TerrainGrid, bounds_latlon: SearchBounds) -> None:
    grid_bounds = _grid_bounds_latlon(grid)
    if not _bounds_contains(grid_bounds, bounds_latlon, tolerance=1e-3):
        raise DatasetNotFoundError(
            "terrain",
            (
                "DEM mosaic does not fully cover the requested search window. "
                "Ensure the necessary tiles are downloaded."
            ),
        )


def _terrain_directories(search_dirs: Sequence[Path] | None) -> list[Path]:
    if search_dirs is not None:
        return [path for path in search_dirs if path.exists()]

    dirs: list[Path] = []
    repo_data = PROJECT_ROOT / "data"
    for sub in ("terrain",):
        candidate = repo_data / sub
        if candidate.exists():
            dirs.append(candidate)
    toy_dir = repo_data / "toy"
    if toy_dir.exists():
        dirs.append(toy_dir)

    root = data_root()
    for sub in ("terrain/raw", "terrain/cache"):
        candidate = root / sub
        if candidate.exists():
            dirs.append(candidate)
    return dirs


def _roads_directories(search_dirs: Sequence[Path] | None) -> list[Path]:
    if search_dirs is not None:
        return [path for path in search_dirs if path.exists()]

    dirs: list[Path] = []
    repo_data = PROJECT_ROOT / "data"
    toy_dir = repo_data / "toy"
    if toy_dir.exists():
        dirs.append(toy_dir)

    root = data_root()
    for sub in ("roads/cache",):
        candidate = root / sub
        if candidate.exists():
            dirs.append(candidate)
    return dirs


@lru_cache(maxsize=4)
def _terrain_entries(dir_key: tuple[str, ...]) -> list[TerrainAsset]:
    entries: list[TerrainAsset] = []
    for directory_str in dir_key:
        directory = Path(directory_str)
        if not directory.exists():
            continue
        for pattern in ("*.tif", "*.tiff"):
            for path in directory.rglob(pattern):
                try:
                    bounds = _raster_bounds_latlon(path)
                except Exception as exc:  # pragma: no cover - corrupted or unsupported files
                    LOG.debug("Skipping terrain candidate %s (%s)", path, exc)
                    continue
                entries.append(TerrainAsset(path=path, bounds=bounds))
    return entries


@lru_cache(maxsize=4)
def _road_entries(dir_key: tuple[str, ...], approx_epsg: int) -> list[RoadAsset]:
    entries: list[RoadAsset] = []
    for directory_str in dir_key:
        directory = Path(directory_str)
        if not directory.exists():
            continue
        for path in directory.rglob("*.geojson"):
            try:
                bounds = _vector_bounds_latlon(path, approx_epsg)
            except Exception as exc:  # pragma: no cover - corrupted or unsupported files
                LOG.debug("Skipping road candidate %s (%s)", path, exc)
                continue
            entries.append(RoadAsset(path=path, bounds=bounds))
    return entries


def _raster_bounds_latlon(path: Path) -> tuple[float, float, float, float]:
    with rasterio.open(path) as dataset:
        dataset_bounds = dataset.bounds
        dataset_crs = dataset.crs
        if dataset_crs is None:
            raise ValueError(f"Raster at {path} has no CRS.")
        bounds_latlon = transform_bounds(dataset_crs, "EPSG:4326", *dataset_bounds, densify_pts=21)
    lat_min, lon_min, lat_max, lon_max = (
        bounds_latlon[1],
        bounds_latlon[0],
        bounds_latlon[3],
        bounds_latlon[2],
    )
    return (lat_min, lat_max, lon_min, lon_max)


def _vector_bounds_latlon(path: Path, approx_epsg: int) -> tuple[float, float, float, float]:
    gdf = _read_geo_dataframe(path, rows=0)
    if gdf.empty:
        gdf = _read_geo_dataframe(path)
    if gdf.empty:
        raise ValueError(f"Vector dataset at {path} contains no geometries.")
    src_crs = gdf.crs
    vector_bounds = gdf.total_bounds
    if src_crs is None:
        assumed = CRS.from_epsg(approx_epsg)
        bounds_latlon = transform_bounds(
            assumed,
            "EPSG:4326",
            *vector_bounds,
            densify_pts=21,
        )
    else:
        epsg = src_crs.to_epsg() if hasattr(src_crs, "to_epsg") else None
        if epsg in {4326, 4979} and _looks_projected(gdf):
            assumed = CRS.from_epsg(approx_epsg)
            bounds_latlon = transform_bounds(
                assumed,
                "EPSG:4326",
                *vector_bounds,
                densify_pts=21,
            )
        else:
            bounds_latlon = transform_bounds(
                src_crs,
                "EPSG:4326",
                *vector_bounds,
                densify_pts=21,
            )
    lat_min, lon_min, lat_max, lon_max = (
        bounds_latlon[1],
        bounds_latlon[0],
        bounds_latlon[3],
        bounds_latlon[2],
    )
    return (lat_min, lat_max, lon_min, lon_max)


def _project_bounds(
    bounds_latlon: SearchBounds,
    target_crs: str,
) -> tuple[float, float, float, float]:
    lat_min, lat_max, lon_min, lon_max = bounds_latlon
    transformer = Transformer.from_crs("EPSG:4326", target_crs, always_xy=True)
    corners = [
        transformer.transform(lon_min, lat_min),
        transformer.transform(lon_min, lat_max),
        transformer.transform(lon_max, lat_min),
        transformer.transform(lon_max, lat_max),
    ]
    xs, ys = zip(*corners, strict=False)
    return (min(xs), min(ys), max(xs), max(ys))


def _grid_bounds_latlon(grid: TerrainGrid) -> tuple[float, float, float, float]:
    bounds_projected = array_bounds(grid.height, grid.width, grid.transform)
    projected = (
        bounds_projected[0],
        bounds_projected[1],
        bounds_projected[2],
        bounds_projected[3],
    )
    transformed = transform_bounds(grid.crs, "EPSG:4326", *projected, densify_pts=21)
    lat_min, lon_min, lat_max, lon_max = (
        transformed[1],
        transformed[0],
        transformed[3],
        transformed[2],
    )
    return (lat_min, lat_max, lon_min, lon_max)


def _bounds_intersect(a: SearchBounds, b: SearchBounds) -> bool:
    a_lat_min, a_lat_max, a_lon_min, a_lon_max = a
    b_lat_min, b_lat_max, b_lon_min, b_lon_max = b
    return not (
        a_lat_max <= b_lat_min
        or a_lat_min >= b_lat_max
        or a_lon_max <= b_lon_min
        or a_lon_min >= b_lon_max
    )


def _coverage_fraction(dataset_bounds: SearchBounds, request_bounds: SearchBounds) -> float:
    lat_overlap = max(
        0.0,
        min(dataset_bounds[1], request_bounds[1]) - max(dataset_bounds[0], request_bounds[0]),
    )
    lon_overlap = max(
        0.0,
        min(dataset_bounds[3], request_bounds[3]) - max(dataset_bounds[2], request_bounds[2]),
    )
    area_overlap = lat_overlap * lon_overlap
    request_area = (request_bounds[1] - request_bounds[0]) * (request_bounds[3] - request_bounds[2])
    if request_area == 0.0:
        return 0.0
    return area_overlap / request_area


def _bounds_contains(
    container: SearchBounds,
    target: SearchBounds,
    *,
    tolerance: float = 0.0,
) -> bool:
    return (
        container[0] - tolerance <= target[0]
        and container[1] + tolerance >= target[1]
        and container[2] - tolerance <= target[2]
        and container[3] + tolerance >= target[3]
    )


def _missing_terrain_message(
    latitude: float,
    longitude: float,
    radius_km: float,
    directories: Sequence[Path],
    prefer_source: str | None,
) -> str:
    locations = (
        "\n  ".join(str(path) for path in directories) or "  (no terrain directories were found)"
    )
    source_hint = f" '{prefer_source}'" if prefer_source else ""
    return (
        f"No terrain{source_hint} tiles cover latitude {latitude:.4f}°, longitude {longitude:.4f}° "
        f"within {radius_km:.1f} km.\n"
        f"HighPoint looked in:\n{locations}\n"
        "Download the required DEM tiles via "
        "`python scripts/fetch_datasets.py --region washington` or provide "
        "`--terrain-file` pointing to a GeoTIFF that covers the area."
    )


def _missing_roads_message(
    latitude: float,
    longitude: float,
    radius_km: float,
    directories: Sequence[Path],
    prefer_source: str | None,
    bounds: SearchBounds,
) -> str:
    lat_min, lat_max, lon_min, lon_max = bounds
    locations = (
        "\n  ".join(str(path) for path in directories) or "  (no road cache directories were found)"
    )
    source_hint = f" '{prefer_source}'" if prefer_source else ""
    suggestion = (
        "python -m highpoint.scripts.build_road_cache "
        f"--north {lat_max:.4f} --south {lat_min:.4f} "
        f"--east {lon_max:.4f} --west {lon_min:.4f}"
    )
    return (
        f"No road{source_hint} cache covers latitude {latitude:.4f}°, "
        f"longitude {longitude:.4f}° within {radius_km:.1f} km.\n"
        f"HighPoint looked in:\n{locations}\n"
        f"Create a cache with `{suggestion}` or supply `--roads-file` pointing to a "
        "GeoJSON snippet."
    )
