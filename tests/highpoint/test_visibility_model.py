"""Tests for the synthetic obstruction visibility model."""

from __future__ import annotations

import math

import numpy as np
import pytest
from affine import Affine

from highpoint.analysis.candidates import TerrainCandidate
from highpoint.analysis.visibility import compute_visibility_metrics
from highpoint.analysis.drivability import DrivabilityResult
from highpoint.config import AppConfig
from highpoint.data.roads import RoadAccessPoint, RoadNetwork
from highpoint.data.terrain import TerrainGrid
from highpoint.pipeline import PipelineOutput, run_pipeline


class _IdentityTransformer:
    def transform(self, x: float, y: float) -> tuple[float, float]:  # pragma: no cover - helper
        return x, y


def _make_grid(
    size: int = 40,
    elevation: float = 100.0,
    drop_after_columns: int | None = None,
    drop_amount: float = 0.0,
) -> tuple[TerrainGrid, TerrainCandidate]:
    cell_size = 10.0
    elevations = np.full((size, size), elevation, dtype=np.float32)
    transform = Affine(cell_size, 0.0, 0.0, 0.0, -cell_size, cell_size * size)
    grid = TerrainGrid(elevations=elevations, transform=transform, crs="EPSG:32610")
    xs, ys = grid.coordinates()
    row = size // 2
    col = size // 2
    if drop_after_columns is not None:
        elevations[:, col + drop_after_columns :] -= drop_amount
    candidate = TerrainCandidate(
        x=float(xs[row, col]),
        y=float(ys[row, col]),
        elevation_m=float(elevations[row, col]),
        row=row,
        col=col,
    )
    return grid, candidate


@pytest.fixture
def base_config() -> AppConfig:
    return AppConfig(
        observer={"latitude": 0.0, "longitude": 0.0, "altitude_m": 0.0},
        terrain={"max_visibility_km": 2.0},
        visibility={
            "obstruction_start_m": 30.0,
            "obstruction_height_m": 45.0,
            "rays_full_circle": 8,
        },
    )


def test_visibility_requires_drop__flat_terrain_rejected(base_config: AppConfig) -> None:
    grid, candidate = _make_grid()

    metrics = compute_visibility_metrics(grid, candidate, base_config)

    assert metrics.rays_with_clearance == 0
    assert math.isclose(metrics.max_distance_m, base_config.visibility.obstruction_start_m)


def test_pipeline_discards_candidate_without_clearance(
    monkeypatch: pytest.MonkeyPatch,
    base_config: AppConfig,
) -> None:
    grid, candidate = _make_grid()

    road_network = RoadNetwork.synthetic(target_crs=grid.crs)
    drivability = DrivabilityResult(
        access_point=RoadAccessPoint(
            coordinate=(candidate.x, candidate.y),
            distance_m=0.0,
            walking_minutes=1.0,
        ),
        walk_minutes=1.0,
        drive_minutes=15.0,
        drive_distance_km=5.0,
    )

    monkeypatch.setattr("highpoint.pipeline._load_terrain", lambda cfg: (grid, (0.0, 0.0), _IdentityTransformer()))
    monkeypatch.setattr("highpoint.pipeline._load_roads", lambda cfg, target_crs: road_network)
    monkeypatch.setattr("highpoint.pipeline.identify_candidates", lambda g: [candidate])
    monkeypatch.setattr("highpoint.pipeline.cluster_candidates", lambda cands, _: list(cands))
    monkeypatch.setattr("highpoint.pipeline.evaluate_candidate_drivability", lambda **_: drivability)

    output: PipelineOutput = run_pipeline(base_config)

    assert output.results == []


def test_visibility_drop_met__extends_view_distance(base_config: AppConfig) -> None:
    grid, candidate = _make_grid(drop_after_columns=1, drop_amount=120.0)

    metrics = compute_visibility_metrics(grid, candidate, base_config)

    assert metrics.rays_with_clearance > 0
    assert metrics.max_distance_m > base_config.visibility.obstruction_start_m
