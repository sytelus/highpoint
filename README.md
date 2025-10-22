# HighPoint

HighPoint finds drivable scenic viewpoints that satisfy visibility goals such as minimum sight distance, field-of-view, and viewing direction. Feed it digital elevation models and OpenStreetMap road data and it ranks candidate locations that a sedan can reach within a configurable walking distance.

## Highlights

- Terrain visibility engine with obstruction controls, clustering, and scoring tuned for sub-minute runs.
- Dataset tooling that downloads SRTM DEM tiles and Geofabrik road extracts for toy, Washington, or full US coverage.
- Automatic dataset discovery: supply latitude/longitude and HighPoint picks the correct DEM tiles and road cache.
- Offline geocoding: resolve "Town, ST" strings to coordinates and elevation without internet (USGS GNIS powered).
- OmegaConf-based configs (`configs/toyrun.yaml`) and a Typer CLI (`main.py`) with rich table output, CSV/GeoJSON exports, and optional map rendering.

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

### Continental US (large download, be patient)

```
./scripts/download_us_data.sh
python main.py --location "Napa, CA" \
  --results 10 --render-png "$OUT_DIR/napa.png"
```

## Development

- Docs: see `docs/ALGORITHM.md`, `docs/TERRAIN_DATA_SOURCES.md`, `docs/ROAD_DATA_SOURCES.md`, `docs/GEOCODING.md`, and `docs/configuration.md` for research notes and environment details.
- Linting & tests: `make lint` and `make test` (or `pytest`).
- Configuration: override any knob via `configs/toyrun.yaml` or CLI flags (`python main.py --help`). Provide `--location "Town, ST"` (or set `observer.location` in YAML) to geocode latitude/longitude automatically; HighPoint falls back to explicit numeric coordinates when the gazetteer is unavailable.

## Examples & Outputs

- `--export-csv "$OUT_DIR/results.csv"` saves ranked viewpoints with metrics.
- `--export-geojson "$OUT_DIR/targets.geojson"` mirrors point data for GIS tools.
- `--render-png "$OUT_DIR/overview.png"` produces a quick terrain map of candidates.
