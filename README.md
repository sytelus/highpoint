# HighPoint

HighPoint finds drivable scenic viewpoints that satisfy visibility goals such as minimum sight distance, field-of-view, and viewing direction. Feed it digital elevation models and OpenStreetMap road data and it ranks candidate locations that a sedan can reach within a configurable walking distance.

## Highlights

- Terrain visibility engine with obstruction controls, clustering, and scoring tuned for sub-minute runs.
- Dataset tooling that downloads SRTM DEM tiles and Geofabrik road extracts for toy, Washington, or full US coverage.
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

## Quick Start Runs

### Toy Run (fully offline)

```
export DATA_ROOT="$(pwd)/data"
python main.py --config configs/toyrun.yaml --render-png "$OUT_DIR/toy.png"
```

### Washington State (choose the tile covering your area)

```
./scripts/download_washington_data.sh
python -m highpoint.scripts.build_road_cache \
  --north 47.7 --south 47.4 --east -122.1 --west -122.6 \
  --output "$DATA_ROOT/highpoint/roads/cache/seattle.geojson"
python main.py 47.6 -122.3 --azimuth 0 --min-visibility 4 \
  --terrain-file "$DATA_ROOT/highpoint/terrain/raw/n47w123.tif" \
  --roads-file "$DATA_ROOT/highpoint/roads/cache/seattle.geojson" \
  --render-png "$OUT_DIR/seattle.png"
```

### Continental US (large download, be patient)

```
./scripts/download_us_data.sh
python -m highpoint.scripts.build_road_cache \
  --north 38.0 --south 37.5 --east -121.8 --west -122.6 \
  --output "$DATA_ROOT/highpoint/roads/cache/napa.geojson"
python main.py 37.8 -122.4 \
  --terrain-file "$DATA_ROOT/highpoint/terrain/raw/n38w123.tif" \
  --roads-file "$DATA_ROOT/highpoint/roads/cache/napa.geojson" \
  --results 10 --render-png "$OUT_DIR/napa.png"
```

## Development

- Docs: see `docs/ALGORITHM.md`, `docs/TERRAIN_DATA_SOURCES.md`, `docs/ROAD_DATA_SOURCES.md`, and `docs/configuration.md` for research notes and environment details.
- Linting & tests: `make lint` and `make test` (or `pytest`).
- Configuration: override any knob via `configs/toyrun.yaml` or CLI flags (`python main.py --help`).

## Examples & Outputs

- `--export-csv "$OUT_DIR/results.csv"` saves ranked viewpoints with metrics.
- `--export-geojson "$OUT_DIR/targets.geojson"` mirrors point data for GIS tools.
- `--render-png "$OUT_DIR/overview.png"` produces a quick terrain map of candidates.
