"""Terrain candidate generation utilities."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter, maximum_filter

from highpoint.data.terrain import TerrainGrid


@dataclass(frozen=True)
class TerrainCandidate:
    """Represents a potential scenic viewpoint candidate."""

    x: float
    y: float
    elevation_m: float
    row: int
    col: int


def identify_candidates(
    grid: TerrainGrid,
    neighborhood: int = 3,
    min_prominence_m: float = 10.0,
    min_slope_deg: float = 2.0,
) -> list[TerrainCandidate]:
    """
    Detect local maxima in the DEM as candidate viewpoints.

    A Gaussian blur smooths noise, then a maximum filter selects cells that equal the local max
    within the neighborhood window. Prominence and slope filters ensure we keep meaningful peaks.
    """
    if neighborhood < 1:
        raise ValueError("neighborhood must be at least 1")
    if grid.height < 2 or grid.width < 2:
        return []

    valid = np.isfinite(grid.elevations)
    if not valid.any():
        return []

    # Normalized smoothing prevents a single nodata cell from poisoning its neighborhood.
    weights = gaussian_filter(valid.astype(np.float64), sigma=1.0)
    values = gaussian_filter(np.where(valid, grid.elevations, 0.0), sigma=1.0)
    smoothed = np.divide(
        values,
        weights,
        out=np.full_like(values, np.nan, dtype=np.float64),
        where=weights > 0.0,
    )
    finite_smoothed = np.where(np.isfinite(smoothed), smoothed, -np.inf)
    local_max = maximum_filter(
        finite_smoothed,
        footprint=np.ones((neighborhood, neighborhood)),
    )
    mask = np.isclose(finite_smoothed, local_max) & valid

    resolution_x, resolution_y = grid.resolution
    gradient_y, gradient_x = np.gradient(smoothed, resolution_y, resolution_x)
    slope = np.degrees(np.arctan(np.hypot(gradient_x, gradient_y)))

    xs, ys = grid.coordinates()

    candidates: list[TerrainCandidate] = []
    for row, col in zip(*np.where(mask), strict=False):
        elevation = float(grid.elevations[row, col])
        neighborhood_slice = grid.elevations[
            max(row - neighborhood, 0) : row + neighborhood + 1,
            max(col - neighborhood, 0) : col + neighborhood + 1,
        ]
        local_min = float(np.nanmin(neighborhood_slice))
        prominence = elevation - local_min
        if prominence < min_prominence_m:
            continue
        slope_neighborhood = slope[
            max(row - neighborhood, 0) : row + neighborhood + 1,
            max(col - neighborhood, 0) : col + neighborhood + 1,
        ]
        if float(np.nanmax(slope_neighborhood)) < min_slope_deg:
            continue
        candidates.append(
            TerrainCandidate(
                x=float(xs[row, col]),
                y=float(ys[row, col]),
                elevation_m=elevation,
                row=row,
                col=col,
            ),
        )
    return candidates


def cluster_candidates(
    candidates: Sequence[TerrainCandidate],
    grid_size_m: float,
) -> list[TerrainCandidate]:
    """
    Down-sample candidates by grouping them into square bins of size ``grid_size_m``.

    The highest elevation candidate per bin is retained to reduce redundancy.
    """
    if not candidates:
        return []

    buckets: dict[tuple[int, int], TerrainCandidate] = {}
    for candidate in candidates:
        key = (
            int(candidate.x // grid_size_m),
            int(candidate.y // grid_size_m),
        )
        existing = buckets.get(key)
        if existing is None or candidate.elevation_m > existing.elevation_m:
            buckets[key] = candidate
    return list(buckets.values())
