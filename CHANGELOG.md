# Changelog

Notable user-visible changes are recorded here. Commit history remains the source for line-level
detail.

## Unreleased - 2026-08-02

- Enforced CLI-over-YAML precedence and rejected unknown or angularly impossible configuration.
- Made azimuth tolerance functional and required contiguous FOV/distance-qualified results.
- Corrected pixel-center sampling, rotated affine coordinates, nodata handling, valid DEM coverage,
  cell elevation lookup, and UTM longitude boundaries.
- Rebuilt the deterministic toy DEM as a meaningful 4.8 km end-to-end visibility fixture.
- Made dataset downloads atomic and dry runs non-mutating; migrated GNIS ingestion to the current
  official populated-places product.
- Added OSMnx 1.x/2.x cache-builder compatibility, installed `highpoint` console entry point,
  export score completeness, strict CI, and broad regression coverage.
- Reconciled setup, configuration, algorithm, data-source, scoring, and limitation documentation.
