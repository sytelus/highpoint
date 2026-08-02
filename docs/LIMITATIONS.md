# Known Limitations

HighPoint is a screening and ranking tool. Its output should be validated against current maps,
weather, access rules, and on-site conditions before travel.

## Visibility Model

- DEM rays model bare terrain only. Buildings, vegetation, snow, temporary structures, haze, and
  weather are absent unless approximated by the uniform synthetic obstruction belt.
- The obstruction belt assumes the same height in every direction beyond a clear radius. It is a
  deterministic stress model, not a land-cover inference.
- Earth curvature and atmospheric refraction are ignored. Error becomes more important as ray
  length grows.
- Azimuth uses geographic/projected north. HighPoint does not apply magnetic declination, so a
  physical compass bearing can differ by location and date.
- Angular FOV is discretized by the configured ray count. Higher ray counts improve angular
  fidelity and increase runtime.
- Nodata ends a ray conservatively. Valid-pixel bounds are checked, but internal holes in a DEM
  mosaic are not exhaustively diagnosed before analysis.

## Candidate and Ranking Semantics

- Candidates are smoothed local terrain maxima, then deduplicated in square bins. A scenic road
  turnout that is not near a DEM summit can be missed.
- Results are sorted by a heuristic score, not strictly by geographic distance from the starting
  point. The score favors sector visibility, FOV breadth, shorter walks, and elevation.
- Input `observer.altitude_m` is retained as location metadata but does not affect terrain
  visibility from a candidate viewpoint.
- No general runtime guarantee has been benchmarked. Large search windows, high-resolution DEMs,
  many candidates, dense road caches, or large ray counts can be slow.

## Roads and Travel

- The nearest access point is the Euclidean projection onto cached road geometry. It is not a
  walking route and can cross private land, water, cliffs, or other barriers.
- The default OSM filter is a coarse sedan-oriented filter. Missing or stale tags, gates, seasonal
  closures, road condition, legal access, and vehicle restrictions can invalidate a result.
- Drive distance is 1.35 times straight-line distance and drive time assumes one constant speed.
  Road connectivity, speed limits, ferries, traffic, closures, and turn restrictions are ignored.
- HighPoint discovers one intersecting road GeoJSON and does not prove that the entire search area
  has road coverage.

## Data and Geographic Scope

- Washington State is the initial target. Local UTM selection is unsuitable for polar regions and
  a single zone can distort very wide searches or searches crossing zone boundaries.
- Download helpers rely on current third-party services and product layouts. Network use is
  limited to explicit preparation commands; the analysis pipeline itself is offline.
- The current GNIS topical download does not provide elevation, and duplicate town/state names
  resolve to the first matching record.
- Raw Geofabrik PBF downloads are not ingested by the pipeline. A focused GeoJSON must be built
  separately with the OSMnx helper.

## Not a Safety or Access Authority

HighPoint does not determine land ownership, permits, opening hours, trail conditions, wildfire
closures, avalanche exposure, road safety, or whether a viewpoint is physically safe. Do not use
it as the sole basis for navigation or a safety-critical decision.
