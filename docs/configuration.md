# Configuration Reference

HighPoint reads configuration from OmegaConf-compatible YAML files and a small set of environment variables. This document captures the knobs a maintainer or user can adjust.

## Environment Variables

| Variable   | Default                  | Description |
|------------|--------------------------|-------------|
| `DATA_ROOT` | `./data` (resolved relative to the current working directory) | Base directory that HighPoint expands to `$DATA_ROOT/highpoint` for terrain and road downloads. The loader creates missing directories automatically and resolves relative entries in YAML configs under this root. Point this to a fast local disk when working with full-resolution DEM tiles. |
| `OUT_DIR`  | `./out/<project-name>` if unset, create manually per README | Directory where CLI runs should persist reports, CSV/GeoJSON exports, and rendered PNGs. When running inside VS Code, the `ToyRun` debug configuration writes into this directory. |

All file-based configuration in `configs/*.yaml` may refer to paths relative to `DATA_ROOT`.

## YAML Configuration

* `configs/toyrun.yaml` – minimal offline configuration for demos and automated checks. Uses the checked-in synthetic fixtures under `data/toy/`.
* `configs/datasets.yaml` – catalog of terrain and road dataset sources, including mirrors, cache folders, and descriptions.

Configs are merged in the following order:

1. CLI primitives (latitude, longitude, visibility goals, etc.).
2. YAML file provided with `--config/-c` (when present).
3. CLI override flags (`--terrain-file`, `--roads-file`, `--render-png`, etc.), applied via OmegaConf dotted keys.

Field descriptions and defaults are defined in `highpoint.config.AppConfig` and its nested models.
