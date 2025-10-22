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
       wget https://download.geofabrik.de/north-america/us/washington-latest.osm.pbf -P $DATA_ROOT/highpoint/roads/raw/
3. Build a cached GeoJSON focused on the area of interest:
       python -m highpoint.scripts.build_road_cache --north 47.7 --south 47.4 --east -122.1 --west -122.6 --output $DATA_ROOT/highpoint/roads/cache/seattle.geojson
   The script issues an Overpass API query via OSMnx, filters for sedan-friendly `highway` values, drops segments tagged with `access=no/private` or `surface` in `{unpaved, track, dirt, gravel, grass}`, reprojects to the target UTM CRS, and writes GeoJSON for the pipeline. For large study areas you can build multiple bounding boxes and merge the GeoJSON files.

HighPoint automatically discovers GeoJSON caches under `$DATA_ROOT/highpoint/roads/cache`. If a run references a bounding box without a matching cache, the CLI prints a friendly message with the exact `build_road_cache` invocation to generate it.

## Synthetic Fixture

Tests use the repository copy `data/toy/roads_synthetic.geojson`, a small GeoJSON file with a grid of paved and unpaved roads. It supports deterministic unit tests for drivability checks without external downloads.

## Data Handling Notes

* Store raw `.osm.pbf` files under `$DATA_ROOT/highpoint/roads/raw/` and derived GeoJSON caches under `$DATA_ROOT/highpoint/roads/cache/`.
* When building caches, reproject geometries into the same UTM zone as the DEM for accurate distance calculations.
* Keep a manifest in `configs/datasets.yaml` noting the extract date, bounding boxes, and filters applied.
* Respect the ODbL license attribution requirements in user-facing documentation.
