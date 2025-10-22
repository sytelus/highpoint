from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from highpoint.config import PROJECT_ROOT
from highpoint.data.geocode import (
    GazetteerUnavailableError,
    TownGazetteer,
    TownNotFoundError,
    resolve_town,
)


def _prepare_gazetteer(tmp_path: Path) -> Path:
    dataset = PROJECT_ROOT / "data" / "toy" / "gnis_populated_places.csv"
    target = tmp_path / "highpoint" / "geo"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy(dataset, target / dataset.name)
    return target / dataset.name


def test_resolve_town_returns_record(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    dataset = _prepare_gazetteer(tmp_path)
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    record = resolve_town("Issaquah, WA", dataset_path=dataset)
    assert pytest.approx(record.latitude, rel=1e-5) == 47.5301
    assert pytest.approx(record.longitude, rel=1e-5) == -122.0326
    assert record.elevation_m and record.elevation_m > 100.0


def test_gazetteer_is_case_insensitive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    dataset = _prepare_gazetteer(tmp_path)
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    gazetteer = TownGazetteer(dataset_path=dataset)
    record = gazetteer.resolve("issaquah washington")
    assert record.name == "Issaquah"
    assert record.state == "WA"


def test_gazetteer_missing_dataset(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    with pytest.raises(GazetteerUnavailableError):
        TownGazetteer()


def test_gazetteer_not_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    dataset = _prepare_gazetteer(tmp_path)
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    gazetteer = TownGazetteer(dataset_path=dataset)
    with pytest.raises(TownNotFoundError) as excinfo:
        gazetteer.resolve("Atlantis, WA")
    assert "Atlantis" in str(excinfo.value)
