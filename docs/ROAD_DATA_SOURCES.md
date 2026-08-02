# Road Data Sources

## Decision

HighPoint uses OpenStreetMap (OSM) road centerlines because they are current, widely available,
and contain access and highway classifications. The analysis input is a focused GeoJSON cache,
not a raw `.osm.pbf` extract and not a routable graph.

Alternatives considered include U.S. Census TIGER/Line (broad coverage but limited surface/access
detail) and state/local transportation GIS layers (often higher quality but inconsistent to
automate across regions).

## Build an Analysis Cache

The installed helper queries the OSM Overpass service through OSMnx and supports both OSMnx 1.x
and 2.x bounding-box APIs:

```bash
python -m highpoint.scripts.build_road_cache \
  --north 47.70 --south 47.40 --east -122.10 --west -122.60 \
  --output "$DATA_ROOT/highpoint/roads/cache/seattle.geojson"
```

The default custom filter excludes footways, steps, paths, cycleways, bridleways, tracks, service
roads, `motor_vehicle=no`, and `access=no/private`. It does not independently validate every surface,
seasonal-access, gate, or vehicle-class tag. Inspect or customize the resulting data when those
details matter.

HighPoint discovers `.geojson` files under `$DATA_ROOT/highpoint/roads/cache` and selects the file
with the greatest intersection with the requested search window. Discovery does not merge several
road caches or prove complete road coverage.

## Raw Regional Extracts

`python scripts/fetch_datasets.py --region washington` downloads the current Geofabrik Washington
`.osm.pbf` to `$DATA_ROOT/highpoint/roads/raw`. That file is retained as a source artifact, but the
current cache builder queries Overpass and does not ingest the PBF. Direct PBF-to-GeoJSON
conversion is tracked as future work; do not assume the raw download alone makes a run ready.

## Runtime Semantics

The pipeline reprojects cached line geometry into the DEM CRS and computes the shortest Euclidean
distance from each terrain candidate to any segment. Walk time is that straight-line distance
divided by the configured walking speed; it is not a trail route. Drive time is also heuristic and
does not use road connectivity, speed limits, closures, or traffic.

## Licensing and Attribution

OSM data is available under the Open Database License and requires attribution. Review the current
[OpenStreetMap copyright and license guidance](https://www.openstreetmap.org/copyright) before
redistributing derived caches or published maps. Record the extraction date, bounds, and custom
filter beside any long-lived external cache.

The checked-in `data/toy/roads_synthetic.geojson` contains only generated line geometry and is used
for deterministic offline tests.
