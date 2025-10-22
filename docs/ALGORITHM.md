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

1. **Region preparation**: Determine a bounding box centered on the observer that covers the search radius. Fetch or load cached DEM tiles and road network vectors, reproject them into a local UTM zone for meter-based calculations, and fall back to synthetic fixtures when files are missing (used by the toy configuration and tests).
2. **Terrain candidate detection**: Resample the DEM to the requested resolution scale (e.g., downsample when high resolution causes slowdowns). Apply a Gaussian blur followed by a maximum filter to isolate local maxima. Evaluate slope and prominence within a configurable neighborhood and emit each surviving cell as a `TerrainCandidate`.
3. **Visibility estimation**: For every candidate, trace radial samples across 360° (default 72 rays) using `_trace_ray`. Each step interpolates elevations via `scipy.ndimage.map_coordinates`, enforces the synthetic “tree belt” model (no obstruction inside `obstruction_start_m`, dense trees of height `obstruction_height_m` beyond), and records the furthest visible point. A ray must drop by at least `obstruction_height_m - observer_eye_height_m` within the clear radius to see past the tree belt; candidates with zero qualifying rays are discarded. Distances within the requested azimuth sector feed mean/median calculations, and the proportion meeting the minimum visibility threshold yields the effective field-of-view.
4. **Candidate clustering**: Reduce redundancy by binning candidates into grid cells with configurable meter spacing and retaining the highest point from each bin. This keeps runtime predictable without invoking heavier clustering algorithms.
5. **Drivability scoring**: Walk the filtered road geometries, project each line segment, and compute the nearest access point along the network. Translate walking distance into minutes using the configured walking speed. Driving minutes are estimated heuristically from straight-line distance (scaled by 1.35×) to capture reasonable travel cost while remaining offline-friendly. Reject candidates beyond the walking or optional driving thresholds.
6. **Composite ranking**: Rank the remaining candidates with a weighted blend of visibility distance, field-of-view coverage, walking effort, and elevation bonus. Return the top N along with straight-line distance, walking/driving estimates, and access point metadata.

## Performance Considerations

* DEM tiles can be large; we cache them and operate on clipped windows to keep peak memory usage reasonable even on laptops.
* Visibility ray casting is the dominant cost. We cap the number of azimuth samples (default 72 rays spanning 360°) and short-circuit once terrain occludes the line of sight to maintain sub-minute runtimes for the default search radius.
* Road proximity queries iterate over the relatively small set of pre-filtered road segments. Although this is O(n) in the number of segments, trimming the network to a focused bounding box keeps latency low without additional spatial indexes.

## Testing Strategy

* Synthetic DEM grids ensure visibility metrics behave as expected without external downloads.
* GeoJSON fixtures with fabricated road networks validate walking distance and drivability filters.
* Integration-style tests run the core pipeline with synthetic assets and verify that results include drivability summaries and visibility coverage.

## Future Enhancements

* Add NLCD-based vegetation height estimates to improve obstruction realism.
* Parallelize per-candidate visibility calculations using `joblib` or `ray`.
* Persist cached tiles and graphs across runs for faster repeat queries.
