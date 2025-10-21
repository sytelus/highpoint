# HighPoint

HighPoint finds drivable scenic viewpoints that satisfy visibility goals such as minimum sight distance, field-of-view, and viewing direction. Feed it digital elevation models and OpenStreetMap road data and it ranks candidate locations that a sedan can reach within a configurable walking distance.

## Highlights

- Terrain visibility engine with obstruction controls, clustering, and scoring tuned for sub-minute runs.
- Dataset tooling that downloads SRTM DEM tiles and Geofabrik road extracts for toy, Washington, or full US coverage.
- OmegaConf-based configs (`configs/toyrun.yaml`) and a Typer CLI (`main.py`) with rich table output, CSV/GeoJSON exports, and optional map rendering.

## Environment Variables

Set these once before working with the project:

```
export DATA_ROOT="$HOME/data/highpoint"   # where DEM/PBF/cache files live
export OUT_DIR="$HOME/output/highpoint"   # where reports and renders are written
mkdir -p "$DATA_ROOT" "$OUT_DIR"
```

## Setup

Run the installer (creates `.venv/`, upgrades pip, and installs all deps + dev extras):

```
./install.sh
```

Install toy data for the quick run (optional but recommended):

```
python scripts/fetch_datasets.py --region toy
```

## Quick Start Runs

### Toy Run (fully offline)

```
python main.py --config configs/toyrun.yaml --render-png "$OUT_DIR/toy.png"
```

### Washington State (choose the tile covering your area)

```
python scripts/fetch_datasets.py --region washington
python -m highpoint.scripts.build_road_cache --pbf "$DATA_ROOT/roads/raw/washington-latest.osm.pbf" \
  --bbox 47.4 47.7 -122.6 -122.1 --output "$DATA_ROOT/roads/cache/seattle.geojson"
python main.py 47.6 -122.3 --azimuth 0 --min-visibility 4 --terrain-file "$DATA_ROOT/terrain/raw/n47w123.tif" \
  --roads-file "$DATA_ROOT/roads/cache/seattle.geojson" --render-png "$OUT_DIR/seattle.png"
```

### Continental US (large download, be patient)

```
python scripts/fetch_datasets.py --region us
python -m highpoint.scripts.build_road_cache --pbf "$DATA_ROOT/roads/raw/us-latest.osm.pbf" \
  --bbox 37.5 38.0 -122.6 -121.8 --output "$DATA_ROOT/roads/cache/napa.geojson"
python main.py 37.8 -122.4 --terrain-file "$DATA_ROOT/terrain/raw/n38w123.tif" \
  --roads-file "$DATA_ROOT/roads/cache/napa.geojson" --results 10 --render-png "$OUT_DIR/napa.png"
```

## Development

- Docs: see `ALGORITHM.md`, `TERRAIN_DATA_SOURCES.md`, and `ROAD_DATA_SOURCES.md` for research notes.
- Linting & tests: `make lint` and `make test` (or `pytest`).
- Configuration: override any knob via `configs/toyrun.yaml` or CLI flags (`python main.py --help`).

## Examples & Outputs

- `--export-csv "$OUT_DIR/results.csv"` saves ranked viewpoints with metrics.
- `--export-geojson "$OUT_DIR/targets.geojson"` mirrors point data for GIS tools.
- `--render-png "$OUT_DIR/overview.png"` produces a quick terrain map of candidates.
