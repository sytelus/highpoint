"""Download and preprocess the USGS GNIS populated places gazetteer."""

from __future__ import annotations

import csv
import io
import tempfile
import zipfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlretrieve

import typer

from highpoint.config import data_root
from highpoint.data.geocode import STATE_ABBREVIATIONS

GNIS_URL = (
    "https://prd-tnm.s3.amazonaws.com/StagedProducts/GeographicNames/Topical/"
    "PopulatedPlaces_National_Text.zip"
)

app = typer.Typer(help="Download the USGS GNIS gazetteer and build an offline lookup CSV.")


@app.command()
def main(
    output: Path | None = typer.Option(None, help="Optional custom output path for the CSV."),
) -> None:
    """
    Download the GNIS national gazetteer, filter to populated places, and write a compact CSV.

    The resulting file is suitable for offline lookups via ``TownGazetteer``.
    """
    root = data_root() / "geo"
    root.mkdir(parents=True, exist_ok=True)
    destination = output or (root / "gnis_populated_places.csv")
    destination.parent.mkdir(parents=True, exist_ok=True)

    typer.echo(f"Downloading GNIS national file to build gazetteer at {destination} ...")
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
        delete=False,
    ) as output_file:
        output_tmp_path = Path(output_file.name)
    rows_written = 0
    try:
        urlretrieve(GNIS_URL, tmp_path)
        with zipfile.ZipFile(tmp_path) as archive:
            try:
                national = archive.open("Text/PopulatedPlaces_National.txt")
            except KeyError as exc:  # pragma: no cover - corrupted download
                raise RuntimeError("Populated places file not found in GNIS archive.") from exc
            with (
                io.TextIOWrapper(national, encoding="utf-8") as source,
                output_tmp_path.open(
                    "w",
                    encoding="utf-8",
                    newline="",
                ) as sink,
            ):
                reader = csv.DictReader(source, delimiter="|")
                writer = csv.DictWriter(
                    sink,
                    fieldnames=(
                        "feature_id",
                        "name",
                        "state",
                        "latitude",
                        "longitude",
                        "elevation_m",
                    ),
                )
                writer.writeheader()
                for row in reader:
                    state_name = row.get("state_name", "").strip().upper()
                    state = STATE_ABBREVIATIONS.get(state_name, "")
                    name = row.get("feature_name", "").strip()
                    lat = row.get("prim_lat_dec", "").strip()
                    lon = row.get("prim_long_dec", "").strip()
                    if not name or not state or not lat or not lon:
                        continue
                    writer.writerow(
                        {
                            "feature_id": row.get("feature_id", "").strip(),
                            "name": name,
                            "state": state,
                            "latitude": lat,
                            "longitude": lon,
                            "elevation_m": "",
                        },
                    )
                    rows_written += 1
        if rows_written == 0:
            raise RuntimeError("GNIS archive contained no usable populated-place records.")
        output_tmp_path.replace(destination)
    except (HTTPError, URLError) as exc:  # pragma: no cover - network failure
        raise RuntimeError(
            f"Failed to download GNIS dataset ({exc.reason}). Try again later.",
        ) from exc
    finally:
        tmp_path.unlink(missing_ok=True)
        output_tmp_path.unlink(missing_ok=True)
    typer.echo(f"Wrote {rows_written} populated places to {destination}")


if __name__ == "__main__":
    app()
