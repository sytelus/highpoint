"""Configuration models and helpers for HighPoint."""

from __future__ import annotations


import os
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator

from highpoint.simple_yaml import load_yaml


class TerrainConfig(BaseModel):
    """Settings that control terrain data acquisition and sampling."""

    source: str = Field(default="srtm1_arc_second", description="Configured terrain dataset key.")
    data_path: Optional[Path] = Field(
        default=None, description="Optional path to a pre-downloaded DEM GeoTIFF."
    )
    search_radius_km: float = Field(default=30.0, ge=1.0, description="Search radius around observer.")
    resolution_scale: float = Field(default=1.0, ge=0.1, le=4.0, description="DEM resampling scale.")
    max_visibility_km: float = Field(default=100.0, ge=1.0, description="Maximum ray length.")
    cluster_grid_m: float = Field(default=250.0, ge=50.0, description="Grid size for candidate clustering.")


class RoadConfig(BaseModel):
    """Settings related to road network filtering and distance calculations."""

    source: str = Field(default="osm_geofabrik", description="Configured road dataset key.")
    data_path: Optional[Path] = Field(
        default=None, description="Optional path to a GeoJSON/PBF road dataset snippet."
    )
    walking_speed_kmh: float = Field(default=4.8, ge=0.5, le=10.0)
    driving_speed_kmh: float = Field(default=60.0, ge=5.0, le=150.0)
    max_walk_minutes: float = Field(default=15.0, ge=1.0, le=180.0)
    max_drive_minutes: Optional[float] = Field(default=None, ge=1.0, le=600.0)


class VisibilityConfig(BaseModel):
    """User-driven visibility and obstruction preferences."""

    observer_eye_height_m: float = Field(default=1.8, ge=0.5, le=3.0)
    obstruction_start_m: float = Field(default=10.0, ge=0.0)
    obstruction_height_m: float = Field(default=15.0, ge=0.0)
    min_visibility_miles: float = Field(default=3.0, ge=0.1)
    min_field_of_view_deg: float = Field(default=30.0, ge=1.0, le=360.0)
    azimuth_deg: float = Field(default=0.0, ge=0.0, lt=360.0)
    azimuth_tolerance_deg: float = Field(
        default=45.0, ge=1.0, le=180.0, description="Half-width around azimuth to scan."
    )
    rays_full_circle: int = Field(default=72, ge=8, le=720, description="Rays for 360° scan.")


class OutputConfig(BaseModel):
    """Presentation preferences."""

    results_limit: int = Field(default=10, ge=1, le=100)
    rich_table: bool = Field(default=True)
    export_csv: Optional[Path] = Field(default=None)
    export_geojson: Optional[Path] = Field(default=None)
    render_png: Optional[Path] = Field(default=None)


class ObserverInput(BaseModel):
    """User-provided origin point."""

    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    altitude_m: float = Field(default=0.0)


class AppConfig(BaseModel):
    """Top-level configuration for the HighPoint pipeline."""

    observer: ObserverInput
    terrain: TerrainConfig = Field(default_factory=TerrainConfig)
    roads: RoadConfig = Field(default_factory=RoadConfig)
    visibility: VisibilityConfig = Field(default_factory=VisibilityConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)

    @validator("output")
    def validate_output_paths(cls, value: OutputConfig) -> OutputConfig:
        """Ensure export directories exist."""
        for path in [value.export_csv, value.export_geojson, value.render_png]:
            if path is not None:
                path.parent.mkdir(parents=True, exist_ok=True)
        return value


class DatasetRegistry(BaseModel):
    """Configuration for dataset sources loaded from YAML."""

    terrain: Dict[str, Any]
    roads: Dict[str, Any]

    @classmethod
    def from_yaml(cls, path: Path) -> "DatasetRegistry":
        raw = load_yaml(path)
        return cls(
            terrain=raw.get("terrain", {}),
            roads=raw.get("roads", {}),
        )

    def terrain_source(self, key: str) -> Dict[str, Any]:
        try:
            return self.terrain["sources"][key]
        except KeyError as exc:  # pragma: no cover - configuration error
            raise KeyError(f"Unknown terrain source '{key}'") from exc

    def road_source(self, key: str) -> Dict[str, Any]:
        try:
            return self.roads["sources"][key]
        except KeyError as exc:  # pragma: no cover - configuration error
            raise KeyError(f"Unknown road source '{key}'") from exc


def load_config(
    observer_lat: float,
    observer_lon: float,
    observer_alt: float,
    azimuth: float,
    min_visibility_miles: float,
    min_fov_deg: float,
    results_limit: int,
    dataset_config_path: Path = Path("configs/datasets.yaml"),
    config_path: Optional[Path] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> AppConfig:
    """
    Build AppConfig from primitive CLI values and keyword overrides.

    Parameters beyond the explicit arguments will be matched to nested configuration
    keys using dotted notation (e.g. ``terrain.search_radius_km=40``).
    """
    base = AppConfig(
        observer=ObserverInput(latitude=observer_lat, longitude=observer_lon, altitude_m=observer_alt),
        visibility=VisibilityConfig(
            azimuth_deg=azimuth,
            min_visibility_miles=min_visibility_miles,
            min_field_of_view_deg=min_fov_deg,
        ),
        output=OutputConfig(results_limit=results_limit),
    )

    merged: Dict[str, Any] = base.model_dump()

    if config_path:
        file_conf = load_yaml(config_path)
        merged = _deep_merge(merged, file_conf)

    if overrides:
        for dotted_key, value in overrides.items():
            if value is None:
                continue
            _apply_override(merged, dotted_key, value)

    config = AppConfig.model_validate(merged)
    return _resolve_relative_paths(config)


def _deep_merge(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in extra.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, dict)
        ):
            base[key] = _deep_merge(dict(base[key]), value)
        else:
            base[key] = value
    return base


def _apply_override(target: Dict[str, Any], dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    current = target
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


def _resolve_relative_paths(config: AppConfig) -> AppConfig:
    data_root = Path(os.environ.get("DATA_ROOT", "data"))
    terrain_path = config.terrain.data_path
    if terrain_path is not None and not terrain_path.is_absolute():
        terrain_update = config.terrain.model_copy(update={"data_path": data_root / terrain_path})
        return _resolve_relative_paths(
            config.model_copy(update={"terrain": terrain_update})
        )

    road_path = config.roads.data_path
    if road_path is not None and not road_path.is_absolute():
        roads_update = config.roads.model_copy(update={"data_path": data_root / road_path})
        return config.model_copy(update={"roads": roads_update})
    return config
