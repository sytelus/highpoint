# Configuration Reference

HighPoint reads configuration from OmegaConf-compatible YAML files and a small set of environment variables. This document captures the knobs a maintainer or user can adjust.

## Environment Variables

| Variable   | Default                  | Description |
|------------|--------------------------|-------------|
| `DATA_ROOT` | `./data` (resolved relative to the current working directory) | Base directory that HighPoint expands to `$DATA_ROOT/highpoint` for terrain and road downloads. The loader creates missing directories automatically and resolves relative entries in YAML configs under this root. Point this to a fast local disk when working with full-resolution DEM tiles. |
| `OUT_DIR`  | `./out/<project-name>` if unset, create manually per README | Directory where CLI runs should persist reports, CSV/GeoJSON exports, and rendered PNGs. When running inside VS Code, the `ToyRun` debug configuration writes into this directory. |

All file-based configuration in `configs/*.yaml` may refer to paths relative to `DATA_ROOT`.

## YAML Configuration

Use the samples in `configs/` as starting points:

- `configs/toyrun.yaml` – minimal offline configuration for demos and automated checks. Uses the checked-in synthetic fixtures under `data/toy/`.
- `configs/datasets.yaml` – catalog of terrain and road dataset sources, including mirrors, cache folders, and descriptions.

Configuration sources are merged in the following order:

1. CLI primitives (`latitude`, `longitude`, `--search-radius`, etc.).
2. YAML file provided with `--config/-c` (when present).
3. CLI override flags (`--terrain-file`, `--roads-file`, `--render-png`, etc.) expressed as OmegaConf dotted keys.

### Observer (top-level `observer`)

| Key | Type | Default | CLI override | Description |
|-----|------|---------|--------------|-------------|
| `latitude` | float | *required* | positional argument | Observer latitude in decimal degrees. Ignored if `observer.location` is set. |
| `longitude` | float | *required* | positional argument | Observer longitude in decimal degrees. Ignored if `observer.location` is set. |
| `altitude_m` | float | `0.0` | `--altitude/-a` | Observer altitude above sea level in metres. |
| `location` | string | `null` | `--location/-L` | Optional `"Town, ST"` string resolved via the offline GNIS gazetteer (`scripts/fetch_gazetteer.py`). Overrides `latitude`/`longitude` and provides an altitude when available. |

### Terrain (`terrain`)

| Key | Type | Default | CLI override | Description |
|-----|------|---------|--------------|-------------|
| `source` | string | `"srtm1_arc_second"` | n/a | Named dataset from `configs/datasets.yaml`; used by automation scripts. |
| `data_path` | path/null | `null` | `--terrain-file` | Optional path to a GeoTIFF; when omitted HighPoint auto-discovers tiles under `$DATA_ROOT/highpoint` or `data/`. |
| `search_radius_km` | float | `30.0` | `--search-radius` | Radius around the observer to crop DEM/roads. |
| `resolution_scale` | float | `1.0` | `--terrain.resolution_scale=<value>` | Resamples DEM resolutions (values <1 sharpen, >1 coarsen). |
| `max_visibility_km` | float | `100.0` | `--terrain.max_visibility_km=<value>` | Maximum ray length used in visibility tracing. |
| `cluster_grid_m` | float | `250.0` | `--terrain.cluster_grid_m=<value>` | Grid size for clustering nearby candidates. |

### Roads (`roads`)

| Key | Type | Default | CLI override | Description |
|-----|------|---------|--------------|-------------|
| `source` | string | `"osm_geofabrik"` | n/a | Named road dataset entry in `configs/datasets.yaml`. |
| `data_path` | path/null | `null` | `--roads-file` | Optional cached GeoJSON; auto-discovery falls back to `$DATA_ROOT/highpoint/roads/cache`. |
| `walking_speed_kmh` | float | `4.8` | `--roads.walking_speed_kmh=<value>` | Assumed walk speed for access time calculations. |
| `driving_speed_kmh` | float | `60.0` | `--roads.driving_speed_kmh=<value>` | Base driving speed for straight-line estimates. |
| `max_walk_minutes` | float | `15.0` | `--max-walk` | Maximum acceptable walking time from access point to candidate. |
| `max_drive_minutes` | float/null | `null` | `--max-drive` | Optional maximum allowable driving time (null disables the limit). |

### Visibility (`visibility`)

| Key | Type | Default | CLI override | Description |
|-----|------|---------|--------------|-------------|
| `observer_eye_height_m` | float | `1.8` | `--visibility.observer_eye_height_m=<value>` | Height of the observer above ground. |
| `obstruction_start_m` | float | `10.0` | `--visibility.obstruction_start_m=<value>` | Radius of the clear “moat” around the viewpoint; synthetic trees begin just outside this distance. |
| `obstruction_height_m` | float | `15.0` | `--visibility.obstruction_height_m=<value>` | Height of the synthetic tree canopy beyond the moat. Rays must drop by at least `(obstruction_height_m - observer_eye_height_m)` within the moat to clear it (see `docs/OBSTRUCTION_MODEL.md`). |
| `min_visibility_miles` | float | `3.0` | `--min-visibility/-k` | Required unobstructed viewing distance. |
| `min_field_of_view_deg` | float | `30.0` | `--min-fov/-g` | Desired continuous field-of-view around the target azimuth. |
| `azimuth_deg` | float | `0.0` | `--azimuth/-d` | Centreline direction of interest (0 = North). |
| `azimuth_tolerance_deg` | float | `45.0` | `--visibility.azimuth_tolerance_deg=<value>` | Half-width around `azimuth_deg` to evaluate when using partial sectors. |
| `rays_full_circle` | int | `72` | `--visibility.rays_full_circle=<value>` | Number of rays sampled over 360°. Higher values improve fidelity at the cost of runtime. |

### Output (`output`)

| Key | Type | Default | CLI override | Description |
|-----|------|---------|--------------|-------------|
| `results_limit` | int | `10` | `--results/-n` | Number of viewpoints to keep after scoring. |
| `rich_table` | bool | `true` | `--output.rich_table=<true|false>` | Toggles rich console reporting. |
| `export_csv` | path/null | `null` | `--export-csv` | Optional CSV export path. |
| `export_geojson` | path/null | `null` | `--export-geojson` | Optional GeoJSON export path. |
| `render_png` | path/null | `null` | `--render-png` | Optional terrain overview rendering path. |

### Location Resolution and Data Discovery

- When `observer.location` is provided (e.g. `observer.location: "Issaquah, WA"`), HighPoint uses the offline GNIS gazetteer to fill in latitude, longitude, and (when available) elevation. Both the CLI (`--location`) and YAML option prefer the gazetteer result over explicit coordinates.
- If `terrain.data_path` or `roads.data_path` are omitted, HighPoint scans `$DATA_ROOT/highpoint` and the repository `data/` directory for matching files. Missing assets trigger a friendly error with the exact `scripts/fetch_datasets.py` or `build_road_cache` command needed to resolve the gap.

### Editing Workflow

1. Copy `configs/toyrun.yaml` to a new file alongside your project, adjust the tables above, and run with `--config <path>`.
2. Override individual values from the command line using dotted keys (example: `--terrain.resolution_scale=0.5`).
3. Persist environment-specific paths via `DATA_ROOT` and `OUT_DIR` so the CLI stays portable across systems.
