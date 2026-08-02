# HighPoint

HighPoint ranks scenic terrain viewpoints near a supplied location. It combines a digital
elevation model (DEM), a drivable-road GeoJSON, a synthetic obstruction model, and configurable
visibility goals. The current implementation is designed for Washington State and for offline,
local-first analysis after datasets have been prepared.

## Features

- Finds and clusters terrain summits before running 360-degree line-of-sight sampling.
- Requires a contiguous clear field of view around a requested azimuth and rejects candidates
  that do not meet the configured distance and FOV goals.
- Filters candidates by straight-line walking distance to sedan-accessible road geometries.
- Estimates drive time offline and exports ranked results to the terminal, CSV, GeoJSON, or PNG.
- Includes a checked-in 4.8 km synthetic DEM, road grid, gazetteer, and VS Code toy-run profile.
- Discovers local DEM tiles and road caches without contacting a service during analysis.

HighPoint is an approximate planning tool, not a navigation or safety system. Read
[docs/LIMITATIONS.md](docs/LIMITATIONS.md) before relying on its results.

## Setup

Python 3.11 or newer is required. Linux and WSL are the supported and CI-tested workflows:

```bash
./install.sh
source .venv/bin/activate
```

Equivalent pip installation is also supported:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Native Windows and macOS may work when binary wheels are available for the geospatial
dependencies, but they are not currently exercised in CI. On native Windows, create and activate
the environment with `py -3.11 -m venv .venv` and `.venv\Scripts\Activate.ps1` before running the
same pip command.

## Environment

`DATA_ROOT` is the base directory for large datasets; HighPoint uses its `highpoint/`
subdirectory. `OUT_DIR` is the base output directory; relative export paths are placed under its
`highpoint/` subdirectory.

```bash
export DATA_ROOT="$HOME/data"
export OUT_DIR="$HOME/output"
mkdir -p "$DATA_ROOT" "$OUT_DIR"
```

When unset, the defaults are `data/highpoint/` and `out/highpoint/` in the repository.

## Toy Run

The toy assets are checked in, so this run is fully offline:

```bash
python main.py --config configs/toyrun.yaml --render-png toy.png
```

The relative PNG path resolves to `$OUT_DIR/highpoint/toy.png`. The installed console command is
equivalent:

```bash
highpoint --config configs/toyrun.yaml --export-csv toy-results.csv
```

To restore missing deterministic fixtures, run `python scripts/fetch_datasets.py --region toy`.
The VS Code **HighPoint ToyRun** launch configuration provides the same end-to-end workflow.

## Real Data Workflow

1. Download DEM tiles and the raw Geofabrik extract:

   ```bash
   python scripts/fetch_datasets.py --region washington
   ```

2. Build a focused GeoJSON road cache. The analysis pipeline does not ingest the downloaded PBF
   directly:

   ```bash
   python -m highpoint.scripts.build_road_cache \
     --north 47.75 --south 47.45 --east -121.95 --west -122.55
   ```

3. Supply coordinates, or build the offline GNIS gazetteer and use a town name:

   ```bash
   python scripts/fetch_gazetteer.py
   highpoint --location "Seattle, WA" --azimuth 270 --min-visibility 4
   ```

   Numeric coordinates use named options so negative longitudes are unambiguous:

   ```bash
   highpoint --latitude 47.6062 --longitude -122.3321 --search-radius 10
   ```

Advanced settings belong in an OmegaConf YAML file. The CLI exposes the common path, search,
visibility, travel, and output overrides shown by `highpoint --help`; arbitrary dotted CLI options
are not supported.

## Development

Run the complete local quality gate from the WSL/Linux environment:

```bash
make lint
make test
python main.py --config configs/toyrun.yaml
```

The checks cover Ruff, Black, strict mypy, branch-aware pytest coverage, and the offline toy
pipeline. Build a distributable wheel with `python -m pip wheel --no-deps .`.

## Documentation

- [Project goals](PROJECT.md)
- [Configuration reference](docs/configuration.md)
- [Algorithm and test strategy](docs/ALGORITHM.md)
- [Known limitations](docs/LIMITATIONS.md)
- [Synthetic obstruction model](docs/OBSTRUCTION_MODEL.md)
- [Candidate scoring](docs/SCORING.md)
- [Terrain sources](docs/TERRAIN_DATA_SOURCES.md)
- [Road sources](docs/ROAD_DATA_SOURCES.md)
- [Offline geocoding](docs/GEOCODING.md)
- [Change log](CHANGELOG.md)
