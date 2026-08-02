# Viewpoint Search Algorithm

## Coordinate and Data Preparation

HighPoint computes a geodesic latitude/longitude bounding box around the observer, selects
intersecting DEM tiles and a road GeoJSON, and reprojects the DEM to the local UTM zone. Raster
nodata values become `NaN`; valid pixels must cover the requested window. The road geometries are
reprojected to the same CRS so all proximity calculations use meters.

Explicit toy paths use the same loading path as external files. Missing real data raises a
`DatasetNotFoundError`; analysis never substitutes toy data implicitly.

## Candidate Generation

`identify_candidates` performs normalized Gaussian smoothing so nodata cells do not poison nearby
terrain. A maximum filter finds local summits. Local relief supplies a prominence check, and the
maximum slope in the surrounding window prevents a symmetric summit from being rejected merely
because its exact peak cell has zero gradient.

`cluster_candidates` then bins projected coordinates into `terrain.cluster_grid_m` squares and
keeps the highest summit per bin. Clustering happens before the expensive visibility pass.

## Visibility

For each clustered candidate, `compute_visibility_metrics` traces
`visibility.rays_full_circle` evenly spaced rays. `_trace_ray` samples cell centers with bilinear
interpolation and maintains the greatest terrain elevation angle seen so far. A sample is visible
when it establishes a new horizon. Tracing stops at the configured maximum distance, the raster
boundary, or nodata; unknown terrain is not treated as transparent.

The synthetic obstruction model adds a uniform height beyond `obstruction_start_m`. A ray can see
past that belt only when terrain inside the clear radius drops enough to compensate for the
difference between obstruction height and observer eye height. See
[OBSTRUCTION_MODEL.md](OBSTRUCTION_MODEL.md).

The requested analysis sector spans `azimuth_deg ± azimuth_tolerance_deg`. Mean, median, and
maximum distances use only rays in that sector. `actual_fov_deg` is the longest contiguous run of
sector rays that reach `min_visibility_miles`, capped at the sector width. A candidate is rejected
unless this contiguous width reaches `min_field_of_view_deg`. This single condition enforces both
the visibility-distance and FOV requirements.

Angular results are quantized by `360 / rays_full_circle`. Configuration validation prevents a ray
step wider than the requested minimum FOV.

## Road Access

For each visibility-qualified candidate, `RoadNetwork.nearest_access_point` projects the point
onto every cached road segment and keeps the nearest straight-line location. Distance divided by
the configured walking speed yields walk minutes. Candidates beyond `max_walk_minutes` are
rejected.

HighPoint does not currently route over a road graph. It estimates drive distance as 1.35 times the
straight-line distance from the observer to the access point and divides by the configured speed.
An optional `max_drive_minutes` can filter on that estimate.

## Ranking

Qualifying candidates are scored with visibility distance, contiguous FOV, walking effort, and
elevation, then sorted by descending score. `output.results_limit` is applied last. The result set
is therefore the best-scoring qualifying set, not necessarily the geographically nearest set. The
formula is documented in [SCORING.md](SCORING.md).

## Complexity and Performance

- Candidate detection is proportional to the number of raster cells.
- Visibility work is approximately candidates × rays × samples per ray and is the dominant cost.
- Road proximity is candidates × cached road segments because no spatial index is used yet.

The code clips data and clusters candidates to bound this work, but no general sub-minute guarantee
is claimed. Performance depends on search radius, DEM resolution, candidate count, ray count, and
road-cache size and should be measured on the intended workload.

## Test Strategy

- Affine, nodata, reprojection, coverage, and UTM-boundary tests protect geospatial preparation.
- Synthetic peaks and obstruction profiles cover candidate and line-of-sight edge cases.
- Known ray patterns verify sector tolerance and contiguous FOV rather than aggregate ray counts.
- Pipeline tests prove that obstruction, visibility/FOV, walk, and drive filters reject candidates
  at the correct stage.
- CLI, configuration precedence, typo rejection, report exports, downloader atomicity, and OSMnx
  compatibility have focused regression tests.
- The checked-in toy DEM and road grid exercise the same end-to-end code path without network
  access.

Known modeling boundaries are collected in [LIMITATIONS.md](LIMITATIONS.md).
