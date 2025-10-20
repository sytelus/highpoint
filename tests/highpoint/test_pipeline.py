from __future__ import annotations

from highpoint.analysis.visibility import compute_visibility_metrics
from highpoint.config import load_config
from highpoint.data.terrain import TerrainCandidate, generate_synthetic_dem
from highpoint.pipeline import run_pipeline


def test_pipeline_generates_results_with_synthetic_data() -> None:
    config = load_config(
        observer_lat=47.0,
        observer_lon=-122.0,
        observer_alt=150.0,
        azimuth=0.0,
        min_visibility_miles=1.0,
        min_fov_deg=20.0,
        results_limit=3,
        overrides={
            "terrain.search_radius_km": 5.0,
            "roads.max_walk_minutes": 30.0,
            "roads.max_drive_minutes": None,
        },
    )

    output = run_pipeline(config)

    assert output.results, "pipeline should return at least one candidate"
    top = output.results[0]
    assert top.drivability is not None
    assert top.visibility.max_distance_m > 0.0
    assert top.visibility.actual_fov_deg >= 0.0


def test_visibility_metrics_cover_sector() -> None:
    grid = generate_synthetic_dem()
    xs, ys = grid.coordinates()
    row = grid.height // 2
    col = grid.width // 2
    candidate = TerrainCandidate(x=float(xs[row, col]), y=float(ys[row, col]), elevation_m=float(grid.elevations[row, col]), row=row, col=col)
    config = load_config(
        observer_lat=47.0,
        observer_lon=-122.0,
        observer_alt=0.0,
        azimuth=0.0,
        min_visibility_miles=0.5,
        min_fov_deg=45.0,
        results_limit=1,
        overrides={"terrain.search_radius_km": 5.0},
    )

    metrics = compute_visibility_metrics(grid, candidate, config)

    assert metrics.max_distance_m > 0.0
    assert metrics.actual_fov_deg <= 360.0
