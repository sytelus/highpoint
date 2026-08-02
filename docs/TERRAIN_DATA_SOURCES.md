# Terrain Data Sources

## Decision

HighPoint defaults to USGS-hosted SRTM 1 Arc-Second GeoTIFFs. Their approximately 30 m spacing is
a practical balance for regional screening and has consistent U.S. coverage. USGS 3DEP 1/3
Arc-Second data is a higher-resolution alternative but requires substantially more storage and
processing. Copernicus and local lidar products can also work when converted to georeferenced
GeoTIFFs with elevation units compatible with the model.

The source catalog in `configs/datasets.yaml` records these choices for maintainers. It is not a
lockfile and is not read by the analysis configuration loader.

## Download

For the bundled regional definitions:

```bash
python scripts/fetch_datasets.py --region washington
# or preview without creating directories or files
python scripts/fetch_datasets.py --region washington --dry-run
```

Terrain tiles are written atomically under `$DATA_ROOT/highpoint/terrain/raw`; a failed transfer
does not leave a partial file that a later run mistakes for a completed download. A filename
manifest is written after a successful non-dry run.

The configured official directory is the [USGS National Map staged elevation products](https://prd-tnm.s3.amazonaws.com/index.html?prefix=StagedProducts/Elevation/1/TIFF/current/).
For a smaller request, download only the tiles intersecting the intended search radius.

## Loading and Coverage

HighPoint scans repository toy data plus `$DATA_ROOT/highpoint/terrain/raw` and `terrain/cache` for
`.tif` and `.tiff` files that intersect the requested latitude/longitude window. It merges selected
tiles, converts declared nodata to `NaN`, reprojects to local UTM, and optionally resamples.

Selected tiles must use compatible source CRS/resolution metadata. The loader verifies that the
bounding extent of valid pixels—not padded nodata—covers the requested window. It does not yet
detect every internal hole in a mosaic or persist the derived reprojection as a reusable cache.

Elevation values are interpreted as meters. Earth curvature, atmospheric refraction, vegetation,
and structures are not part of the DEM ray trace; see [LIMITATIONS.md](LIMITATIONS.md).

## Synthetic Fixture

`data/toy/dem_synthetic.tif` is a deterministic 160×160 raster at 30 m spacing (4.8 km square).
It contains a gentle regional slope and a compact rocky summit with a long-distance horizon. The
source is `generate_synthetic_dem` in `src/highpoint/data/terrain.py`; regenerate the tracked file
with:

```bash
python scripts/make_synthetic_dem.py data/toy/dem_synthetic.tif
```

Do not edit the binary artifact directly. Update the generator, rebuild it, and run the toy
pipeline and tests together.
