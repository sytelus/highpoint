from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from affine import Affine

from highpoint.analysis.candidates import TerrainCandidate
from highpoint.analysis.drivability import DrivabilityResult
from highpoint.analysis.visibility import VisibilityMetrics
from highpoint.config import AppConfig
from highpoint.data.roads import RoadAccessPoint
from highpoint.data.terrain import TerrainGrid
from highpoint.pipeline import ViewpointResult
from highpoint.render.map import render_map
from highpoint.reporting.report import emit_report


def _result() -> ViewpointResult:
    return ViewpointResult(
        candidate=TerrainCandidate(x=1.0, y=2.0, elevation_m=300.0, row=0, col=0),
        visibility=VisibilityMetrics(
            max_distance_m=2_000.0,
            mean_distance_m=1_500.0,
            median_distance_m=1_400.0,
            actual_fov_deg=45.0,
            ray_results={0.0: 2_000.0},
            rays_with_clearance=1,
            total_rays=1,
        ),
        drivability=DrivabilityResult(
            access_point=RoadAccessPoint(
                coordinate=(1.0, 1.0),
                distance_m=100.0,
                walking_minutes=2.0,
            ),
            walk_minutes=2.0,
            drive_minutes=10.0,
            drive_distance_km=8.0,
        ),
        candidate_latlon=(47.0, -122.0),
        access_latlon=(47.1, -122.1),
        access_altitude_m=250.0,
        straight_line_miles=5.0,
        score=0.75,
    )


def test_exports__include_ranking_inputs_and_score(tmp_path: Path) -> None:
    csv_path = tmp_path / "results.csv"
    geojson_path = tmp_path / "results.geojson"
    config = AppConfig.model_validate(
        {
            "observer": {"latitude": 47.0, "longitude": -122.0},
            "output": {
                "rich_table": False,
                "export_csv": csv_path,
                "export_geojson": geojson_path,
            },
        },
    )

    emit_report([_result()], config)

    with csv_path.open(newline="", encoding="utf-8") as handle:
        csv_row = next(csv.DictReader(handle))
    geojson: dict[str, Any] = json.loads(geojson_path.read_text(encoding="utf-8"))
    properties = geojson["features"][0]["properties"]

    assert csv_row["score"] == "0.75"
    assert csv_row["straight_line_miles"] == "5.0"
    assert properties["score"] == 0.75
    assert properties["access_altitude_m"] == 250.0


def test_rich_report__renders_summary_and_profile(capsys: pytest.CaptureFixture[str]) -> None:
    config = AppConfig.model_validate(
        {"observer": {"latitude": 47.0, "longitude": -122.0}},
    )

    emit_report([_result()], config)

    output = capsys.readouterr().out
    assert "Rank 1" in output
    assert "Minimum clear-sector field-of-view" in output
    assert "360° visibility profiles" in output


def test_rich_report_without_results__states_empty(capsys: pytest.CaptureFixture[str]) -> None:
    config = AppConfig.model_validate(
        {"observer": {"latitude": 47.0, "longitude": -122.0}},
    )

    emit_report([], config)

    assert "No viewpoints found" in capsys.readouterr().out


def test_render_map_with_generator__retains_results(tmp_path: Path) -> None:
    terrain = TerrainGrid(
        elevations=np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32),
        transform=Affine.translation(0.0, 2.0) * Affine.scale(1.0, -1.0),
        crs="EPSG:32610",
    )
    output_path = tmp_path / "map.png"

    render_map((_result() for _ in range(1)), terrain=terrain, output_path=output_path)

    assert output_path.is_file()
    assert output_path.stat().st_size > 0
