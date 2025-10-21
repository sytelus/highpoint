"""Configuration models and helpers for HighPoint."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, cast

from omegaconf import DictConfig, OmegaConf
from pydantic import BaseModel, Field, validator


class TerrainConfig(BaseModel):
    """Settings that control terrain data acquisition and sampling."""

    source: str = Field(
        default="srtm1_arc_second",
        description="Configured terrain dataset key.",
    )
    data_path: Path | None = Field(
        default=None,
        description="Optional path to a pre-downloaded DEM GeoTIFF.",
    )
    search_radius_km: float = Field(
        default=30.0,
        ge=1.0,
        description="Search radius around observer.",
    )
    resolution_scale: float = Field(
        default=1.0,
        ge=0.1,
        le=4.0,
        description="DEM resampling scale.",
    )
    max_visibility_km: float = Field(
        default=100.0,
        ge=1.0,
        description="Maximum ray length.",
    )
    cluster_grid_m: float = Field(
        default=250.0,
        ge=50.0,
        description="Grid size for candidate clustering.",
    )


class RoadConfig(BaseModel):
    """Settings related to road network filtering and distance calculations."""

    source: str = Field(default="osm_geofabrik", description="Configured road dataset key.")
    data_path: Path | None = Field(
        default=None,
        description="Optional path to a GeoJSON/PBF road dataset snippet.",
    )
    walking_speed_kmh: float = Field(default=4.8, ge=0.5, le=10.0)
    driving_speed_kmh: float = Field(default=60.0, ge=5.0, le=150.0)
    max_walk_minutes: float = Field(default=15.0, ge=1.0, le=180.0)
    max_drive_minutes: float | None = Field(default=None, ge=1.0, le=600.0)


class VisibilityConfig(BaseModel):
    """User-driven visibility and obstruction preferences."""

    observer_eye_height_m: float = Field(default=1.8, ge=0.5, le=3.0)
    obstruction_start_m: float = Field(default=10.0, ge=0.0)
    obstruction_height_m: float = Field(default=15.0, ge=0.0)
    min_visibility_miles: float = Field(default=3.0, ge=0.1)
    min_field_of_view_deg: float = Field(default=30.0, ge=1.0, le=360.0)
    azimuth_deg: float = Field(default=0.0, ge=0.0, lt=360.0)
    azimuth_tolerance_deg: float = Field(
        default=45.0,
        ge=1.0,
        le=180.0,
        description="Half-width around azimuth to scan.",
    )
    rays_full_circle: int = Field(default=72, ge=8, le=720, description="Rays for 360° scan.")


class OutputConfig(BaseModel):
    """Presentation preferences."""

    results_limit: int = Field(default=10, ge=1, le=100)
    rich_table: bool = Field(default=True)
    export_csv: Path | None = Field(default=None)
    export_geojson: Path | None = Field(default=None)
    render_png: Path | None = Field(default=None)


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
    def validate_output_paths(cls, value: OutputConfig) -> OutputConfig:  # noqa: N805
        """Ensure export directories exist."""
        for path in [value.export_csv, value.export_geojson, value.render_png]:
            if path is not None:
                path.parent.mkdir(parents=True, exist_ok=True)
        return value


class DatasetRegistry(BaseModel):
    """Configuration for dataset sources loaded from YAML."""

    terrain: dict[str, Any]
    roads: dict[str, Any]

    @classmethod
    def from_yaml(cls, path: Path) -> DatasetRegistry:
        cfg = OmegaConf.load(path)
        raw: dict[str, Any] = {}
        if cfg is not None:
            container = OmegaConf.to_container(cfg, resolve=True)
            if isinstance(container, dict):
                raw = cast(dict[str, Any], container)
        terrain = raw.get("terrain", {})
        roads = raw.get("roads", {})
        return cls(terrain=terrain, roads=roads)

    def terrain_source(self, key: str) -> dict[str, Any]:
        try:
            sources = cast(dict[str, Any], self.terrain["sources"])
            return cast(dict[str, Any], sources[key])
        except KeyError as exc:  # pragma: no cover - configuration error
            raise KeyError(f"Unknown terrain source '{key}'") from exc

    def road_source(self, key: str) -> dict[str, Any]:
        try:
            sources = cast(dict[str, Any], self.roads["sources"])
            return cast(dict[str, Any], sources[key])
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
    config_path: Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> AppConfig:
    """
    Build AppConfig from primitive CLI values and keyword overrides.

    Parameters beyond the explicit arguments will be matched to nested configuration
    keys using dotted notation (e.g. ``terrain.search_radius_km=40``).
    """
    base_dict = {
        "observer": {
            "latitude": observer_lat,
            "longitude": observer_lon,
            "altitude_m": observer_alt,
        },
        "visibility": {
            "azimuth_deg": azimuth,
            "min_visibility_miles": min_visibility_miles,
            "min_field_of_view_deg": min_fov_deg,
        },
        "output": {
            "results_limit": results_limit,
        },
    }

    config_cfg: DictConfig = OmegaConf.create(base_dict)

    if config_path:
        file_cfg = cast(DictConfig, OmegaConf.load(config_path))
        config_cfg = cast(DictConfig, OmegaConf.merge(config_cfg, file_cfg))

    if overrides:
        for dotted_key, value in overrides.items():
            if value is None:
                continue
            converted = str(value) if isinstance(value, Path) else value
            OmegaConf.update(config_cfg, dotted_key, converted, merge=True)

    container = OmegaConf.to_container(config_cfg, resolve=True)
    config_dict = cast(dict[str, Any], container)
    config = AppConfig.model_validate(config_dict)
    return _resolve_relative_paths(config)


def _resolve_relative_paths(config: AppConfig) -> AppConfig:
    data_root = Path(os.environ.get("DATA_ROOT", "data")).expanduser()
    if not data_root.is_absolute():
        data_root = (Path.cwd() / data_root).resolve()

    updates: dict[str, Any] = {}

    terrain_path = config.terrain.data_path
    if terrain_path is not None and not terrain_path.is_absolute():
        updates["terrain"] = config.terrain.model_copy(
            update={"data_path": data_root / terrain_path},
        )

    road_path = config.roads.data_path
    if road_path is not None and not road_path.is_absolute():
        updates["roads"] = config.roads.model_copy(
            update={"data_path": data_root / road_path},
        )

    if updates:
        return config.model_copy(update=updates)
    return config
