# HighPoint Project Goals

## Purpose

HighPoint helps a user find nearby scenic viewpoints for a normal passenger car. Given a starting
location, a viewing direction, a minimum visible distance, and a minimum field of view, it should
return a small ranked set of terrain points that meet those visibility goals and are within a
configurable walk of a drivable road.

Washington State is the initial supported region. The design should remain usable elsewhere when
equivalent terrain, road, and gazetteer data are supplied.

## Functional Goals

1. Accept latitude, longitude, optional starting altitude, viewing azimuth, minimum visibility,
   minimum field of view, and result count through a Python API, YAML configuration, and CLI.
2. Discover or load free DEM data, reproject it to a local meter-based CRS, and generate a small
   set of representative terrain candidates efficiently.
3. Trace terrain visibility around each candidate. A qualifying result must provide the requested
   contiguous field of view within the configured tolerance around the desired direction.
4. Approximate nearby obstructions when measured vegetation and building heights are unavailable.
   Observer eye height, clear radius, and synthetic obstruction height must be configurable.
5. Use current OpenStreetMap-derived road geometry to find the nearest plausible access point and
   enforce a configurable walking limit. Offline drive distance and time may be estimates until a
   routing engine is integrated.
6. Report candidate and access coordinates, elevations, mean/median/maximum visibility, field of
   view, straight-line distance, estimated drive and walk times, and ranking score. CSV, GeoJSON,
   and a compact terrain PNG should be available.
7. Provide a fast, deterministic, offline toy run that demonstrates the complete workflow on a
   laptop and can be launched from VS Code.

## Engineering Goals

- Keep the importable implementation under `src/highpoint/`, end-user entry points small, and
  dataset preparation code under `scripts/` or `highpoint.scripts` as appropriate.
- Keep large downloaded and generated datasets outside Git under `$DATA_ROOT/highpoint` and place
  relative outputs under `$OUT_DIR/highpoint`.
- Prefer readable typed code and deterministic algorithms over premature optimization. Validate
  performance claims with benchmarks before publishing them.
- Reject invalid or misspelled configuration instead of silently falling back.
- Cover geospatial transforms, visibility boundaries, data discovery, CLI behavior, exports, and
  the toy pipeline with inexpensive regression tests.
- Keep implementation, defaults, README examples, detailed documentation, and limitations in
  agreement.

## Current Scope Boundary

The current model is a terrain-screening and ranking aid. It does not account for magnetic
declination, Earth curvature/refraction, measured vegetation/building heights, road routing,
weather, land ownership, trail safety, or legal access. These boundaries and the implications of
the heuristic scoring model are maintained in [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

Implementation details and design trade-offs are documented in [docs/ALGORITHM.md](docs/ALGORITHM.md),
[docs/OBSTRUCTION_MODEL.md](docs/OBSTRUCTION_MODEL.md), and [docs/SCORING.md](docs/SCORING.md).
