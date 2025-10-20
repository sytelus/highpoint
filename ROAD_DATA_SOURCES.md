# Road Data Sources

## Summary

The HighPoint pipeline needs a drivable road network for Washington State with tags that differentiate surface quality. OpenStreetMap (OSM) provides comprehensive coverage, and Geofabrik’s regional extracts supply regularly updated `.osm.pbf` files. We use these extracts via the `osmnx` Python library, which simplifies filtering to sedan-accessible roads and converts geometries into a `networkx` graph for routing and proximity queries.

## Candidates Considered

* **OpenStreetMap via Geofabrik (Chosen)**: Weekly updates, permissive ODbL license, rich tagging (`highway`, `surface`, `access`). Download size for Washington is ~350 MB compressed. Works with osmnx, pyrosm, or direct osmium/gdal tooling.
* **US Census TIGER/Line**: National coverage, but missing surface attributes and often misaligned in mountainous regions. Rejected because drivability inference would be unreliable.
* **State of Washington DOT GIS Services**: High-quality shapefiles with road classifications, but terms of use restrict redistribution and automation is harder.

## Acquisition Instructions

1. Install `osmnx>=1.6` (`pip install osmnx`), which pulls in geopandas, shapely, and pyproj.
2. Download the Washington extract:
       wget https://download.geofabrik.de/north-america/us/washington-latest.osm.pbf -P assets/roads/raw/
3. Build a cached graph file focused on the area of interest:
       python -m highpoint.scripts.build_road_cache --pbf assets/roads/raw/washington-latest.osm.pbf --bbox 47.4 47.7 -122.6 -122.1 --output assets/roads/cache/seattle.graphml
   The script filters for `highway` values in the sedan-friendly set and removes segments tagged with `access=no/private` or `surface` in `{unpaved, track, dirt, gravel, grass}` unless the caller opts in.

## Synthetic Fixture

Tests use `assets/sample_data/roads_synthetic.geojson`, a small GeoJSON file with a grid of paved and unpaved roads. It supports deterministic unit tests for drivability checks without external downloads.

## Data Handling Notes

* Store raw `.osm.pbf` files under `assets/roads/raw/` and derived graphs or GeoPackage exports under `assets/roads/cache/`.
* When building caches, reproject geometries into the same UTM zone as the DEM for accurate distance calculations.
* Keep a manifest in `configs/datasets.yaml` noting the extract date, bounding boxes, and filters applied.
* Respect the ODbL license attribution requirements in user-facing documentation.
