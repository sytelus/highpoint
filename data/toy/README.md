Missing toy data assets can be restored by the dataset fetch script:

    python scripts/fetch_datasets.py --region toy

This creates the 4.8 km square `dem_synthetic.tif` and sample road GeoJSON when either
fixture is missing. To rebuild only the DEM after changing its generator, run
`python scripts/make_synthetic_dem.py data/toy/dem_synthetic.tif`.
