# Synthetic Obstruction Model

HighPoint currently approximates near-field clutter (trees, houses, etc.) with a
lightweight synthetic model so the visibility pipeline can operate without
land-cover datasets. This document captures the assumptions behind the model
and how the configuration parameters interact with the visibility metrics.

## Conceptual Model

* **Clear moat** – The terrain within `obstruction_start_m` of a candidate is
  assumed to be free of obstacles so the observer has somewhere to stand.
* **Tree belt** – Immediately beyond that radius every terrain sample is topped
  with a uniform canopy of height `obstruction_height_m`.
* **Observer eye height** – The observer stands at
  `candidate.elevation_m + observer_eye_height_m` (default eye height 1.8 m).

Any ray that fails to clear the tree belt is capped at
`obstruction_start_m`, because the first row of synthetic trees blocks the view.

## Clearance Rule

To see past the tree belt, the ground must drop by at least the difference
between the canopy height and the observer eye height inside the clear moat:

```
candidate.elevation_m - terrain(distance ≤ obstruction_start_m)
    ≥ obstruction_height_m - observer_eye_height_m
```

If no samples inside the moat satisfy this inequality, the pipeline discards
the candidate because every ray terminates at the tree wall.

## How the Pipeline Uses the Rule

* `_trace_ray` in `highpoint.analysis.visibility` enforces the rule per ray.
  When the drop is sufficient the algorithm continues and adds the canopy
  height to each terrain sample beyond the moat, modelling trees on the slope.
* `compute_visibility_metrics` records how many rays clear the belt. When the
  count is zero the pipeline rejects the candidate before drivability scoring.

## Choosing Parameters

* Increase `obstruction_start_m` to represent wider clearings or viewpoints at
  the edge of cliffs. Remember that the terrain must drop somewhere within that
  radius to offset the tree height.
* Increase `obstruction_height_m` to simulate taller trees or nearby buildings.
  Doing so makes it harder for rays to clear the belt because the required
  terrain drop grows.
* Lower `observer_eye_height_m` only when modelling seated observers or
  platforms below eye level; the difference to the canopy height is what
  governs the clearance threshold.

These parameters provide a coarse but deterministic approximation until we
integrate vegetation/building datasets. When real obstruction data becomes
available we can replace the synthetic canopy with measured heights and keep
the same visibility plumbing.
