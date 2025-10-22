# Candidate Scoring

HighPoint ranks each clustered viewpoint with a numeric score in the range 0–1.0 before presenting the top `output.results_limit` candidates. The score is a weighted blend of visibility quality, usable field-of-view, walking effort, and site elevation.

## Formula

For every candidate we compute:

| Component | Expression | Weight | Purpose |
|-----------|------------|--------|---------|
| Distance score | `min(1, max_distance_m / (required_distance_m * 1.5))` | 0.40 | Rewards long clear lines of sight; capped once the longest ray reaches 150 % of the requested minimum visibility. |
| Field-of-view score | `min(1, actual_fov_deg / min_required_fov_deg)` | 0.30 | Measures how much of the requested sector is unobstructed. |
| Walk penalty | `max(0, 1 - (walk_minutes / max_walk_minutes))` | 0.20 | Penalises viewpoints that exceed the configured walking limit; zero once the walk reaches or exceeds the cap. |
| Elevation bonus | `tanh(elevation_m / 500)` | 0.10 | Provides a gentle bonus for higher sites without letting elevation dominate the ranking. |

The final score is the weighted sum of those four terms:

```
score = 0.4 * distance_score
      + 0.3 * fov_score
      + 0.2 * walk_penalty
      + 0.1 * elevation_bonus
```

A score closer to 1.0 suggests a well-balanced candidate that meets distance and FOV goals while remaining relatively accessible.

## Inputs and Defaults

- `required_distance_m` comes from `visibility.min_visibility_miles`.
- `min_required_fov_deg` comes from `visibility.min_field_of_view_deg` (never below 1°).
- `max_walk_minutes` comes from `roads.max_walk_minutes`.
- `actual_fov_deg` counts the degrees of azimuth whose rays meet the distance requirement.
- `max_distance_m` is the longest unobstructed ray for the candidate.
- `walk_minutes` is estimated walking time from the nearest road access point.
- `elevation_m` is the DEM elevation at the candidate cell.

All of these values are reported in the rich CLI panels and CSV/GeoJSON exports for traceability.

## Adjusting the Score

To emphasise different priorities you have a few options:

1. **Change configuration inputs** – tightening `visibility.min_visibility_miles`, widening `visibility.min_field_of_view_deg`, or lowering `roads.max_walk_minutes` shifts the underlying component scores without a code change.
2. **Fork the weighting** – edit `_score_candidate` in `src/highpoint/pipeline.py` if you want alternative weights or new terms (e.g., driving time or curvature). When adding factors, also update this document so others understand the new behaviour.
3. **Post-filtering** – downstream scripts can apply additional filters to the exported CSV/GeoJSON if a one-off report needs different constraints.

Whichever approach you adopt, keep the scoring interpretation section of the README and this document in sync to maintain a self-contained explanation for users.*** End Patch
