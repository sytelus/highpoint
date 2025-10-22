# Offline Geocoding

HighPoint converts user-friendly place strings (for example, `Issaquah, WA`) into latitude/longitude/elevation values without contacting external services. This is powered by the U.S. Geological Survey's Geographic Names Information System (GNIS) populated places extract, which is published as a periodically refreshed pipe-delimited text file and includes 3DEP-derived elevation estimates for each feature.citeturn0search0turn0search3turn0search5

## Workflow

1. Download the national GNIS extract with `python scripts/fetch_gazetteer.py`. The script fetches the official `NationalFile.zip`, filters for `FEATURE_CLASS == "Populated Place"`, and emits a compact CSV (`gnis_populated_places.csv`) under `$DATA_ROOT/highpoint/geo/`.citeturn0search0turn0search2
2. `TownGazetteer` (in `highpoint.data.geocode`) loads that CSV, normalises names, and serves lookups via `resolve_town("Town, ST")`, returning coordinates and altitude in metres. Cached parsing keeps repeated lookups fast.

The GNIS dataset covers more than two million named U.S. features and is refreshed every other month; re-run the fetch script any time you need an updated snapshot.citeturn0search3
