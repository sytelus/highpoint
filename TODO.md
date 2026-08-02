# Remaining Work

- Ingest local Geofabrik PBF extracts directly so regional road preparation does not require a
  separate Overpass query.
- Add measured vegetation/building obstruction layers and keep the synthetic belt as an explicit
  fallback.
- Integrate an optional offline/remote router for connected drive and walk distances.
- Add spatial indexing and a reproducible benchmark suite before publishing runtime targets.
- Detect internal DEM coverage holes and persist deterministic reprojected/mosaicked caches.
- Curate small legally redistributable real-data fixtures for CLI integration tests.
- Add magnetic-declination and Earth-curvature/refraction options for long-distance bearings.
