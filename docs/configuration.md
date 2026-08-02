# Configuration Reference

HighPoint merges an optional OmegaConf YAML file with explicit CLI values and validates the result
with Pydantic. Unknown keys are errors so misspelled settings cannot be silently ignored.

## Environment Variables

| Variable | Default | Behavior |
|---|---|---|
| `DATA_ROOT` | `<repository>/data` | HighPoint uses and creates `$DATA_ROOT/highpoint` for large terrain, road, and gazetteer data. A relative input path first resolves to an existing repository path; otherwise it resolves under this project-specific data directory. |
| `OUT_DIR` | `<repository>/out` | HighPoint uses and creates `$OUT_DIR/highpoint` for relative CSV, GeoJSON, and PNG paths. Explicit absolute output paths are preserved. |

Neither variable contains a credential, so token rotation does not apply. Keep secrets out of these
paths and out of YAML files; `.env*` files are ignored by Git.

## Precedence

Configuration is applied from lowest to highest precedence:

1. Pydantic model defaults.
2. The YAML file supplied with `--config`.
3. Explicit common CLI values such as `--latitude`, `--min-fov`, and `--results`.
4. Explicit path/travel CLI overrides such as `--terrain-file`, `--max-walk`, and `--export-csv`.

Advanced settings that do not have a named CLI option must be placed in YAML. HighPoint does not
accept arbitrary dotted CLI flags.

`configs/toyrun.yaml` is an application configuration. `configs/datasets.yaml` is a human-readable
source catalog and is not merged into application runs.

## Observer

| Key | Type | Default | CLI | Description |
|---|---:|---:|---|---|
| `observer.latitude` | float | required | `--latitude` | Latitude in decimal degrees. |
| `observer.longitude` | float | required | `--longitude` | Longitude in decimal degrees. |
| `observer.altitude_m` | float | `0.0` | `--altitude`, `-a` | Starting-point altitude. It is currently metadata and does not change candidate visibility. |
| `observer.location` | string/null | `null` | `--location`, `-L` | Offline GNIS query such as `"Issaquah, WA"`. A resolved location replaces numeric coordinates. |

If a requested location cannot be found or the gazetteer is missing, the CLI reports an error. It
does not silently fall back to unrelated numeric coordinates.

## Terrain

| Key | Type | Default | CLI | Description |
|---|---:|---:|---|---|
| `terrain.source` | string | `srtm1_arc_second` | YAML only | Dataset label included in discovery diagnostics. Selection itself is spatial. |
| `terrain.data_path` | path/null | `null` | `--terrain-file` | DEM GeoTIFF. When omitted, intersecting `.tif`/`.tiff` files are discovered. |
| `terrain.search_radius_km` | float | `30.0` | `--search-radius` | Radius cropped around the observer; minimum 1 km. |
| `terrain.resolution_scale` | float | `1.0` | YAML only | Values above 1 reduce raster dimensions; values below 1 upsample. Range: 0.1–4.0. |
| `terrain.max_visibility_km` | float | `100.0` | YAML only | Maximum length of each visibility ray. |
| `terrain.cluster_grid_m` | float | `250.0` | YAML only | Square-bin size used to deduplicate nearby candidates. |

All DEMs in a merged request must have compatible CRS/resolution metadata. Valid (non-nodata)
pixels must cover the search window; padded nodata does not count as coverage.

## Roads

| Key | Type | Default | CLI | Description |
|---|---:|---:|---|---|
| `roads.source` | string | `osm_geofabrik` | YAML only | Dataset label included in discovery diagnostics. |
| `roads.data_path` | path/null | `null` | `--roads-file` | Drivable-road GeoJSON. Discovery scans repository toy data and `$DATA_ROOT/highpoint/roads/cache`. |
| `roads.walking_speed_kmh` | float | `4.8` | YAML only | Speed used to convert straight-line road distance into walk minutes. |
| `roads.driving_speed_kmh` | float | `60.0` | YAML only | Speed used by the offline drive-time estimate. |
| `roads.max_walk_minutes` | float | `15.0` | `--max-walk` | Maximum walk from the nearest road geometry. |
| `roads.max_drive_minutes` | float/null | `null` | `--max-drive` | Optional maximum estimated drive time; `null` disables it. |

## Visibility

| Key | Type | Default | CLI | Description |
|---|---:|---:|---|---|
| `visibility.observer_eye_height_m` | float | `1.8` | YAML only | Eye height above the candidate DEM elevation. |
| `visibility.obstruction_start_m` | float | `30.0` | YAML only | Clear radius before the synthetic obstruction belt begins. |
| `visibility.obstruction_height_m` | float | `3.0` | YAML only | Uniform synthetic height added beyond the clear radius. |
| `visibility.min_visibility_miles` | float | `3.0` | `--min-visibility`, `-k` | Minimum clear distance that a ray must reach. |
| `visibility.min_field_of_view_deg` | float | `10.0` | `--min-fov`, `-g` | Minimum contiguous qualifying angular width. |
| `visibility.azimuth_deg` | float | `0.0` | `--azimuth`, `-d` | Desired direction in geographic/grid degrees, where 0 is north. Magnetic declination is not applied. |
| `visibility.azimuth_tolerance_deg` | float | `45.0` | YAML only | Half-width of the sector evaluated around the desired azimuth. |
| `visibility.rays_full_circle` | int | `72` | YAML only | Number of evenly spaced 360-degree rays. |

The FOV must fit inside twice the azimuth tolerance. The angular step
(`360 / rays_full_circle`) must be no wider than the requested minimum FOV; invalid combinations
are rejected.

## Output

| Key | Type | Default | CLI | Description |
|---|---:|---:|---|---|
| `output.results_limit` | int | `10` | `--results`, `-n` | Maximum qualifying results after scoring. |
| `output.rich_table` | bool | `true` | YAML only | Use Rich terminal panels instead of log lines. |
| `output.export_csv` | path/null | `null` | `--export-csv` | Ranked CSV path. |
| `output.export_geojson` | path/null | `null` | `--export-geojson` | Candidate and access-point GeoJSON path. |
| `output.render_png` | path/null | `null` | `--render-png` | Terrain overview PNG path. |

## Example

```yaml
observer:
  latitude: 46.9480
  longitude: -122.9920
terrain:
  data_path: data/toy/dem_synthetic.tif
  search_radius_km: 2.0
roads:
  data_path: data/toy/roads_synthetic.geojson
visibility:
  min_visibility_miles: 0.5
  min_field_of_view_deg: 25.0
  azimuth_deg: 270.0
  azimuth_tolerance_deg: 60.0
output:
  export_csv: seattle-results.csv
```

Run it with `highpoint --config path/to/config.yaml`. Named CLI options override the corresponding
values when both are present.
