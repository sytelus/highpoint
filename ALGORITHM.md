# Visibility Candidate Algorithm

## Purpose

This document captures the end-to-end approach used by HighPoint to transform user input into ranked scenic viewpoints. It lists the data dependencies, configuration parameters, computational steps, and the primary trade-offs between accuracy and runtime so future contributors can reason about changes with the same baseline.

## Inputs and Parameters

* Required user inputs: observer latitude, observer longitude, observer altitude in meters, desired viewing azimuth in degrees (0–360), minimum field-of-view in degrees, minimum clear visibility distance in miles, number of targets to return, desired walking time threshold in minutes.
* Optional user inputs: maximum driving time in minutes, obstruction start distance in meters (default 10 m), obstruction maximum height in meters (default 15 m), observer eye height in meters (default 1.8 m), walking speed in km/h (default 4.8), driving speed in km/h (default 60), resolution scale factor for terrain sampling (default 1.0).
* Configurable system parameters: digital elevation model (DEM) resolution in meters (default 30 m, matching NASA SRTM 1 Arc-Second for the United States), terrain search radius in kilometers (default 30 km), candidate clustering grid size in meters (default 250 m), maximum line-of-sight evaluation range in kilometers (default 100 km).

## Data Dependencies

Terrain: NASA Shuttle Radar Topography Mission (SRTM 1 Arc-Second) GeoTIFF tiles deliver 30 m resolution DEM coverage for Washington State and are freely downloadable via USGS EarthExplorer. For faster prototyping we can use the AWS-hosted SRTM tiles mirrored in the `us-west-2` region. Files arrive as GeoTIFF with elevation in meters and WGS84 geographic coordinates.

Road network: OpenStreetMap extracts provide detailed road centerlines, including surface tags that differentiate paved and unpaved roads. Geofabrik publishes Washington State extracts as zipped `.osm.pbf` files updated weekly. These can be ingested via `osmnx`, which wraps `networkx` and `shapely` to process drivable networks quickly.

Land cover (optional obstruction modeling): United States National Land Cover Database (NLCD 2019) and Microsoft's US Building Footprints (GeoJSON) can approximate vegetation and building heights. The initial implementation approximates obstructions using configurable synthetic parameters without requiring these datasets, but the pipeline exposes hooks for future integration.

## Processing Pipeline

1. **Region preparation**: Determine a bounding box centered on the observer that covers the search radius. Fetch or load cached DEM tiles and road network vectors, reproject them into a local UTM zone for meter-based calculations, and cache to disk.
2. **Terrain precomputation**: Resample the DEM to the requested resolution scale (e.g., downsample when high resolution causes slowdowns). Generate hillshade and gradient rasters to speed up line-of-sight checks. Identify candidate summit pixels via local maxima detection with a configurable neighborhood window. Each summit becomes a target seed.
3. **Visibility estimation**: For each seed, trace radial samples across the requested azimuth sector using a horizon-scanning algorithm. We cast discrete rays (typical step 1–2 resolution cells) until the visibility distance meets or exceeds the requested minimum or terrain occludes the ray beyond the obstruction height threshold. Track average and max distances plus actual field-of-view coverage that satisfies the visibility requirement. Use numpy arrays for vectorized rays to keep runtime below one minute for the default radius.
4. **Candidate clustering**: Group adjacent seeds within the clustering grid size using DBSCAN or simple grid binning. Retain the highest-elevation point per cluster to avoid redundant viewpoints.
5. **Drivability scoring**: For each cluster representative, query the road network graph for the nearest drivable node that matches sedan-accessible filters (`highway` in {motorway, trunk, primary, secondary, tertiary, residential, service, unclassified} and `surface` not in {unpaved, track}). Compute geodesic distance from the terrain point to that node and translate into walking time using the configured walking speed. Also compute a shortest-path length from observer to the node when possible. Reject candidates beyond the walking-time threshold.
6. **Composite ranking**: Rank remaining candidates by a weighted score combining visibility distance, field-of-view coverage, elevation, and total travel effort. Return the top N and attach contextual metrics.

## Performance Considerations

* DEM tiles can be large; we cache them and work in chunks to keep peak memory usage under ~2 GB on a modern laptop.
* Visibility ray casting is the dominant cost. We limit the number of azimuth samples (default 72 rays spanning 360°, higher resolution for the requested viewing sector) and rely on vectorized operations to avoid Python loops.
* Road proximity queries rely on `scipy.spatial.KDTree` built over projected coordinates. Building the tree costs O(n log n) but only happens once per run.

## Testing Strategy

* Synthetic DEM grids with known slopes ensure the line-of-sight logic yields expected distances.
* Fixtures with fabricated road networks validate walking distance and drivability filters.
* Property-style tests randomize observer locations inside the synthetic grid to verify stability.
* Integration tests run the CLI against synthetic assets and assert that the output table matches expected metrics within tolerance.

## Future Enhancements

* Add NLCD-based vegetation height estimates to improve obstruction realism.
* Parallelize per-candidate visibility calculations using `joblib` or `ray`.
* Persist cached tiles and graphs across runs for faster repeat queries.
