# Terrain Data Sources

## Summary

HighPoint requires a 3D surface model of Washington State with roughly 30 m or finer resolution. The NASA Shuttle Radar Topography Mission (SRTM) 1 Arc-Second DEM is the best balance between coverage, licensing, and availability. It covers all of the United States at 1 arc-second (~30 m) resolution, stores heights in meters, and is freely redistributable for non-commercial use. Several mirrors exist; we recommend the USGS 3DEP download interface for canonical access and the AWS Public Dataset mirror for automation.

## Candidates Considered

* **USGS 3DEP 1/3 Arc-Second DEM**: 10 m resolution GeoTIFFs with superb quality, but the volume is large (hundreds of GB for Washington) and requires stitching many tiles. Useful for premium accuracy, but heavy for initial prototypes.
* **NASA SRTM 1 Arc-Second (Chosen)**: 30 m resolution, consistent coverage, and the AWS mirror offers anonymous HTTPS downloads and Cloud-Optimized GeoTIFFs. Works well with rasterio and GDAL without preprocessing.
* **Copernicus EU-DEM**: 25 m resolution, but coverage outside Europe is limited. Discarded because our MVP focuses on Washington State.
* **Mapzen Terrain (retired)**: Historic dataset derived from SRTM with 90 m resolution; superseded by better options.

## Acquisition Instructions

1. Install GDAL 3.4+ and rasterio (`pip install rasterio`).
2. Visit `https://prd-tnm.s3.amazonaws.com/index.html?prefix=StagedProducts/Elevation/1/TIFF/current/` and identify the tiles covering Washington (filenames start with `USGS_1_nXXwYYY`). Download needed tiles with `curl -O`.
3. Optionally clip or mosaic using GDAL:
       gdalwarp USGS_1_n47w123.tif USGS_1_n48w123.tif -t_srs EPSG:32610 -r bilinear -dstnodata -9999 washington_dem.tif
4. Store raw downloads under `$DATA_ROOT/highpoint/terrain/raw/` and cached reprojected mosaics under `$DATA_ROOT/highpoint/terrain/cache/`.

## Synthetic Fixture

For unit and integration tests we rely on a synthetic GeoTIFF generated on demand via `scripts/make_synthetic_dem.py`. The utility writes `data/toy/dem_synthetic.tif` inside the repository (kept under version control), a 2 km × 2 km grid with a gradual slope and a single hill peak, enabling deterministic visibility assertions.

## Data Handling Notes

* Elevations use meters relative to mean sea level; treat `-32768` as the no-data sentinel.
* Reproject tiles into the local UTM zone (EPSG:32610 for western Washington, EPSG:32611 for eastern). Store both the original and reprojected CRS metadata, as line-of-sight math requires meter units.
* Cache downloads and derived rasters with deterministic filenames keyed by tile extent and resolution so repeated runs avoid network access.
* Document every dataset version in `configs/datasets.yaml` to ensure reproducible runs.
