from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from typer.testing import CliRunner

from highpoint.app import app
from highpoint.config import AppConfig
from highpoint.data.discovery import DatasetNotFoundError
from highpoint.data.geocode import TownRecord


def test_cli_help__lists_primary_options() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "--location" in result.output
    assert "--longitude" in result.output
    assert "--terrain-file" in result.output
    assert "--export-csv" in result.output


def test_invalid_log_level__returns_usage_error() -> None:
    result = CliRunner().invoke(
        app,
        ["--latitude", "47.0", "--longitude", "-122.0", "--log-level", "LOUD"],
    )

    assert result.exit_code == 2
    assert "Unknown logging level 'LOUD'" in result.output


def test_cli_with_config_and_overrides__runs_pipeline_and_renderer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[AppConfig] = []
    rendered: list[Path] = []

    def fake_run(config: AppConfig) -> Any:
        captured.append(config)
        return SimpleNamespace(results=[], terrain=None)

    def fake_report(_results: list[Any], _config: AppConfig) -> None:
        return None

    def fake_render(_results: list[Any], *, terrain: Any, output_path: Path) -> None:
        del terrain
        rendered.append(output_path)

    monkeypatch.setenv("DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("OUT_DIR", str(tmp_path / "outputs"))
    monkeypatch.setattr("highpoint.app.run_pipeline", fake_run)
    monkeypatch.setattr("highpoint.app.emit_report", fake_report)
    monkeypatch.setattr("highpoint.app.render_map", fake_render)

    result = CliRunner().invoke(
        app,
        [
            "--config",
            "configs/toyrun.yaml",
            "--min-fov",
            "5",
            "--results",
            "2",
            "--render-png",
            "map.png",
        ],
    )

    assert result.exit_code == 0
    assert captured[0].visibility.min_field_of_view_deg == 5.0
    assert captured[0].output.results_limit == 2
    assert rendered == [(tmp_path / "outputs" / "highpoint" / "map.png").resolve()]


def test_location__uses_gazetteer_coordinates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[AppConfig] = []

    class FakeGazetteer:
        def resolve(self, query: str) -> TownRecord:
            assert query == "Example, WA"
            return TownRecord("Example", "WA", 47.5, -122.5, 123.0)

    def fake_run(config: AppConfig) -> Any:
        captured.append(config)
        return SimpleNamespace(results=[], terrain=None)

    monkeypatch.setattr("highpoint.app.TownGazetteer", FakeGazetteer)
    monkeypatch.setattr("highpoint.app.run_pipeline", fake_run)
    monkeypatch.setattr("highpoint.app.emit_report", lambda *_: None)

    result = CliRunner().invoke(app, ["--location", "Example, WA"])

    assert result.exit_code == 0
    assert captured[0].observer.latitude == 47.5
    assert captured[0].observer.longitude == -122.5
    assert captured[0].observer.altitude_m == 123.0


def test_dataset_error__returns_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(_config: AppConfig) -> Any:
        raise DatasetNotFoundError("terrain", "missing DEM")

    monkeypatch.setattr("highpoint.app.run_pipeline", fail)

    result = CliRunner().invoke(
        app,
        ["--latitude", "47.0", "--longitude", "-122.0"],
    )

    assert result.exit_code == 1
    assert "missing DEM" in result.output


def test_missing_location__returns_usage_error() -> None:
    result = CliRunner().invoke(app, [])

    assert result.exit_code == 2
    assert "Latitude and longitude" in result.output
