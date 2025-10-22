"""Download and preprocess the USGS GNIS populated places gazetteer."""

from __future__ import annotations

import csv
import io
import math
import tempfile
import zipfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlretrieve

import typer

from highpoint.config import data_root

GNIS_URL = "https://geonames.usgs.gov/docs/stategaz/NationalFile.zip"

app = typer.Typer(help="Download the USGS GNIS gazetteer and build an offline lookup CSV.")


def _feet_to_meters(value: str) -> float | None:
    if not value:
        return None
    try:
        feet = float(value)
    except ValueError:
        return None
    if math.isnan(feet):
        return None
    return round(feet * 0.3048, 3)


@app.command()
def main(output: Path | None = typer.Option(None, help="Optional custom output path for the CSV.")) -> None:
    """
    Download the GNIS national gazetteer, filter to populated places, and write a compact CSV.

    The resulting file is suitable for offline lookups via ``TownGazetteer``.
    """
    root = data_root() / "geo"
    root.mkdir(parents=True, exist_ok=True)
    destination = output or (root / "gnis_populated_places.csv")

    typer.echo(f"Downloading GNIS national file to build gazetteer at {destination} ...")
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)
    try:
        urlretrieve(GNIS_URL, tmp_path)
        with zipfile.ZipFile(tmp_path) as archive:
            try:
                national = archive.open("NationalFile.txt")
            except KeyError as exc:  # pragma: no cover - corrupted download
                raise RuntimeError("NationalFile.txt not found in GNIS archive.") from exc
            with io.TextIOWrapper(national, encoding="utf-8") as source, destination.open(
                "w",
                encoding="utf-8",
                newline="",
            ) as sink:
                reader = csv.DictReader(source, delimiter="|")
                writer = csv.DictWriter(
                    sink,
                    fieldnames=("feature_id", "name", "state", "latitude", "longitude", "elevation_m"),
                )
                writer.writeheader()
                rows_written = 0
                for row in reader:
                    if row.get("FEATURE_CLASS") != "Populated Place":
                        continue
                    state = row.get("STATE_ALPHA", "").strip()
                    name = row.get("FEATURE_NAME", "").strip()
                    lat = row.get("PRIM_LAT_DEC", "").strip()
                    lon = row.get("PRIM_LONG_DEC", "").strip()
                    elev = _feet_to_meters(row.get("ELEV_IN_FT", "").strip())
                    if not name or not state or not lat or not lon:
                        continue
                    writer.writerow(
                        {
                            "feature_id": row.get("FEATURE_ID", "").strip(),
                            "name": name,
                            "state": state,
                            "latitude": lat,
                            "longitude": lon,
                            "elevation_m": "" if elev is None else elev,
                        },
                    )
                    rows_written += 1
    except HTTPError as exc:  # pragma: no cover - network failure
        raise RuntimeError(
            f"Failed to download GNIS dataset ({exc.code} {exc.reason}). Try again later.",
        ) from exc
    finally:
        tmp_path.unlink(missing_ok=True)
    typer.echo(f"Wrote {rows_written} populated places to {destination}")


if __name__ == "__main__":
    app()
