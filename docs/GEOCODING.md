# Offline Geocoding

HighPoint resolves U.S. place names locally after a one-time download from the U.S. Geological
Survey's Geographic Names Information System (GNIS).

## Build the Gazetteer

```bash
python scripts/fetch_gazetteer.py
```

The script downloads the official national **Populated Places** topical archive, converts state
names to postal abbreviations, and atomically writes
`$DATA_ROOT/highpoint/geo/gnis_populated_places.csv`. An interrupted conversion does not replace an
existing usable CSV.

The current topical product contains feature IDs, names, states, and coordinates but no elevation
column. HighPoint leaves `elevation_m` empty for downloaded records; supply `--altitude` or
`observer.altitude_m` when that metadata matters. The checked-in toy gazetteer includes sample
elevations for deterministic tests.

USGS documents the current product formats and states that downloads are refreshed every other
month on its [Download GNIS Data](https://www.usgs.gov/us-board-on-geographic-names/download-gnis-data)
page. Re-run the command when a refreshed local snapshot is needed.

## Use

```bash
highpoint --location "Issaquah, WA"
```

`TownGazetteer` accepts `Town, ST`, `Town ST`, or a full state name and performs case-insensitive
exact lookup. Prefix matches are used only to produce up to five suggestions after an exact lookup
fails. Duplicate GNIS names currently resolve to the first record in the source file.

If `DATA_ROOT` is explicitly set and its gazetteer is missing, HighPoint reports the missing path;
it does not silently fall back to the toy file. When `DATA_ROOT` is unset, the toy gazetteer is used
for the bundled example locations.
