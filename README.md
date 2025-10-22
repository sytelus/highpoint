# HighPoint

HighPoint finds drivable scenic viewpoints that satisfy visibility goals such as minimum sight distance, field-of-view, and viewing direction. Feed it digital elevation models and OpenStreetMap road data and it ranks candidate locations that a sedan can reach within a configurable walking distance.

## Highlights

- Terrain visibility engine with obstruction controls, clustering, and scoring tuned for sub-minute runs.
- Dataset tooling that downloads SRTM DEM tiles and Geofabrik road extracts for toy, Washington, or full US coverage.
- Automatic dataset discovery: supply latitude/longitude and HighPoint picks the correct DEM tiles and road cache.
- Offline geocoding: resolve "Town, ST" strings to coordinates and elevation without internet (USGS GNIS powered).
- OmegaConf-based configs (`configs/toyrun.yaml`) and a Typer CLI (`main.py`) with rich panels, CSV/GeoJSON exports, and optional map rendering. Candidate scoring is documented in `docs/SCORING.md`.

## Environment Variables

Set these once before working with the project. HighPoint stores downloads under `$DATA_ROOT/highpoint` unless you override paths via configs or CLI flags (the toy run continues to read the checked-in samples under `data/toy/`).

```
export DATA_ROOT="$HOME/data"             # HighPoint uses $DATA_ROOT/highpoint internally
export OUT_DIR="$HOME/output/highpoint"   # where reports and renders are written
mkdir -p "$DATA_ROOT/highpoint" "$OUT_DIR"
```

## Setup

Run the installer (creates `.venv/`, upgrades pip, and installs all deps + dev extras):

```
./install.sh
```

Install toy data for the quick run (optional but recommended). This keeps the miniature fixtures in-repo for debugging while the larger datasets live under `$DATA_ROOT/highpoint`:

```
./scripts/download_toy_data.sh
```

Build the offline gazetteer once (downloads the USGS GNIS populated places file) so `--location "Town, ST"` works without network access:

```
python scripts/fetch_gazetteer.py
```

## Quick Start Runs

### Toy Run (fully offline)

```
export DATA_ROOT="$(pwd)/data"
python main.py --config configs/toyrun.yaml --render-png "$OUT_DIR/toy.png"
```

### Washington State (auto-detected tiles)

```
./scripts/download_washington_data.sh
python main.py --location "Seattle, WA" --azimuth 0 --min-visibility 4 \
  --render-png "$OUT_DIR/seattle.png"
```

HighPoint inspects the downloads under `$DATA_ROOT/highpoint` and picks the DEM tiles and road cache covering the requested radius. If required files are missing you'll get a friendly message with the exact download command.

Need a custom driving area? Use `python -m highpoint.scripts.build_road_cache --north <lat> --south <lat> --east <lon> --west <lon>` to clip a GeoJSON cache once, then rerun `main.py` and HighPoint will detect it automatically.

## Configuration & Overrides

1. Copy `configs/toyrun.yaml` to a new file (for example `configs/my_run.yaml`) and edit the values that matter to you. Every option, default, and CLI flag is described in detail in `docs/configuration.md`.
2. Run with `python main.py --config configs/my_run.yaml` or supply an absolute path. You can still override single values with dotted keys such as `--terrain.search_radius_km=12` or `--visibility.min_visibility_miles=5`.
3. Prefer `--location "Town, ST"` (or `observer.location` in YAML) when you want automatic geocoding. The CLI falls back to explicit latitude/longitude if the gazetteer is missing.
4. Keep `DATA_ROOT` pointing at a location where terrain and road datasets should be cached, and set `OUT_DIR` to the folder that should receive renders/exports.

After tweaking configuration, the report panels call out the key computed metrics, and `docs/SCORING.md` explains how those metrics combine into the final score.

## Documentation

- `docs/ALGORITHM.md` – end-to-end pipeline overview.
- `docs/TERRAIN_DATA_SOURCES.md` – terrain dataset sourcing and preprocessing notes.
- `docs/ROAD_DATA_SOURCES.md` – road data guidance, including cache-building workflow.
- `docs/GEOCODING.md` – offline GNIS geocoding workflow for `--location`.
- `docs/configuration.md` – full reference for environment variables, YAML fields, and CLI overrides.
- `docs/SCORING.md` – scoring formula, component weights, and customisation tips.
- `docs/OBSTRUCTION_MODEL.md` – how the synthetic tree belt works and how to tune the obstruction settings.

### Continental US (large download, be patient)

```
./scripts/download_us_data.sh
python main.py --location "Napa, CA" \
  --results 10 --render-png "$OUT_DIR/napa.png"
```

## Development

- Docs: see the [Documentation](#documentation) section above for direct links to every guide.
- Linting & tests: `make lint` and `make test` (or `pytest`).
- Configuration: override any knob via `configs/toyrun.yaml` or CLI flags (`python main.py --help`). Provide `--location "Town, ST"` (or set `observer.location` in YAML) to geocode latitude/longitude automatically; HighPoint falls back to explicit numeric coordinates when the gazetteer is unavailable.

## Examples & Outputs

- `--export-csv "$OUT_DIR/results.csv"` saves ranked viewpoints with metrics.
- `--export-geojson "$OUT_DIR/targets.geojson"` mirrors point data for GIS tools.
- `--render-png "$OUT_DIR/overview.png"` produces a quick terrain map of candidates.
