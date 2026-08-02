from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from highpoint.config import VisibilityConfig, data_root, load_config


def test_cli_values_override_yaml__explicit_values_win(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATA_ROOT", str(tmp_path / "data"))
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
observer:
  latitude: 10.0
  longitude: 20.0
  altitude_m: 30.0
visibility:
  azimuth_deg: 90.0
  min_visibility_miles: 4.0
  min_field_of_view_deg: 30.0
output:
  results_limit: 20
""".strip(),
        encoding="utf-8",
    )

    config = load_config(
        observer_lat=47.0,
        observer_lon=-122.0,
        observer_alt=100.0,
        azimuth=180.0,
        min_visibility_miles=2.0,
        min_fov_deg=10.0,
        results_limit=3,
        config_path=config_path,
    )

    assert config.observer.latitude == 47.0
    assert config.observer.longitude == -122.0
    assert config.observer.altitude_m == 100.0
    assert config.visibility.azimuth_deg == 180.0
    assert config.visibility.min_visibility_miles == 2.0
    assert config.visibility.min_field_of_view_deg == 10.0
    assert config.output.results_limit == 3


def test_unknown_yaml_key__validation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATA_ROOT", str(tmp_path / "data"))
    config_path = tmp_path / "config.yaml"
    config_path.write_text("terrain:\n  search_raduis_km: 4\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="search_raduis_km"):
        load_config(
            observer_lat=47.0,
            observer_lon=-122.0,
            observer_alt=0.0,
            azimuth=0.0,
            min_visibility_miles=1.0,
            min_fov_deg=10.0,
            results_limit=3,
            config_path=config_path,
        )


def test_relative_output_path__uses_project_subdirectory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_base = tmp_path / "outputs"
    monkeypatch.setenv("DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("OUT_DIR", str(output_base))

    config = load_config(
        observer_lat=47.0,
        observer_lon=-122.0,
        observer_alt=0.0,
        azimuth=0.0,
        min_visibility_miles=1.0,
        min_fov_deg=10.0,
        results_limit=3,
        overrides={"output.export_csv": Path("reports/results.csv")},
    )

    expected = (output_base / "highpoint" / "reports" / "results.csv").resolve()
    assert config.output.export_csv == expected
    assert expected.parent.is_dir()


def test_data_root_without_create__does_not_touch_disk(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = tmp_path / "datasets"
    monkeypatch.setenv("DATA_ROOT", str(base))

    resolved = data_root(create=False)

    assert resolved == (base / "highpoint").resolve()
    assert not resolved.exists()


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"min_field_of_view_deg": 100.0}, "azimuth_tolerance_deg"),
        (
            {"min_field_of_view_deg": 10.0, "rays_full_circle": 8},
            "rays_full_circle",
        ),
    ],
)
def test_unrepresentable_visibility_settings__validation_fails(
    values: dict[str, float | int],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        VisibilityConfig.model_validate(values)
