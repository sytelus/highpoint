"""Offline gazetteer lookup utilities for town-to-coordinate resolution."""

from __future__ import annotations

import csv
import logging
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from highpoint.config import PROJECT_ROOT, data_root

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class TownRecord:
    """Resolved town metadata suitable for configuring the observer."""

    name: str
    state: str
    latitude: float
    longitude: float
    elevation_m: float | None


class TownNotFoundError(LookupError):
    """Raised when the gazetteer cannot resolve the requested town."""

    def __init__(self, query: str, suggestions: Iterable[str] | None = None) -> None:
        self.query = query
        self.suggestions = list(suggestions or [])
        message = f"Towns matching '{query}' were not found in the offline gazetteer."
        if self.suggestions:
            hints = ", ".join(self.suggestions)
            message += f" Did you mean: {hints}?"
        super().__init__(message)


class GazetteerUnavailableError(FileNotFoundError):
    """Raised when no gazetteer dataset is available on disk."""


class TownGazetteer:
    """Loads a GNIS-derived dataset and resolves town/state pairs."""

    _state_abbrev = {
        "ALABAMA": "AL",
        "ALASKA": "AK",
        "ARIZONA": "AZ",
        "ARKANSAS": "AR",
        "CALIFORNIA": "CA",
        "COLORADO": "CO",
        "CONNECTICUT": "CT",
        "DELAWARE": "DE",
        "DISTRICT OF COLUMBIA": "DC",
        "FLORIDA": "FL",
        "GEORGIA": "GA",
        "HAWAII": "HI",
        "IDAHO": "ID",
        "ILLINOIS": "IL",
        "INDIANA": "IN",
        "IOWA": "IA",
        "KANSAS": "KS",
        "KENTUCKY": "KY",
        "LOUISIANA": "LA",
        "MAINE": "ME",
        "MARYLAND": "MD",
        "MASSACHUSETTS": "MA",
        "MICHIGAN": "MI",
        "MINNESOTA": "MN",
        "MISSISSIPPI": "MS",
        "MISSOURI": "MO",
        "MONTANA": "MT",
        "NEBRASKA": "NE",
        "NEVADA": "NV",
        "NEW HAMPSHIRE": "NH",
        "NEW JERSEY": "NJ",
        "NEW MEXICO": "NM",
        "NEW YORK": "NY",
        "NORTH CAROLINA": "NC",
        "NORTH DAKOTA": "ND",
        "OHIO": "OH",
        "OKLAHOMA": "OK",
        "OREGON": "OR",
        "PENNSYLVANIA": "PA",
        "RHODE ISLAND": "RI",
        "SOUTH CAROLINA": "SC",
        "SOUTH DAKOTA": "SD",
        "TENNESSEE": "TN",
        "TEXAS": "TX",
        "UTAH": "UT",
        "VERMONT": "VT",
        "VIRGINIA": "VA",
        "WASHINGTON": "WA",
        "WEST VIRGINIA": "WV",
        "WISCONSIN": "WI",
        "WYOMING": "WY",
    }

    def __init__(self, dataset_path: Path | None = None) -> None:
        self.dataset_path = dataset_path or self._default_dataset_path()
        if not self.dataset_path.exists():
            raise GazetteerUnavailableError(
                f"Offline gazetteer not found at {self.dataset_path}. "
                "Run `python scripts/fetch_gazetteer.py` to download USGS GNIS data.",
            )
        self._entries = self._load_entries(self.dataset_path)
        self._keys = set(self._entries)

    @staticmethod
    def _default_dataset_path() -> Path:
        root_candidate = data_root() / "geo" / "gnis_populated_places.csv"
        if root_candidate.exists():
            return root_candidate
        # When DATA_ROOT is explicitly set we treat the missing dataset as an error so callers
        # receive a clear GazetteerUnavailableError rather than silently falling back.
        if "DATA_ROOT" in os.environ:
            return root_candidate
        repo_candidate = PROJECT_ROOT / "data" / "toy" / "gnis_populated_places.csv"
        return repo_candidate

    @classmethod
    @lru_cache(maxsize=1)
    def _load_entries(cls, dataset_path: Path) -> dict[tuple[str, str], list[TownRecord]]:
        index: dict[tuple[str, str], list[TownRecord]] = {}
        with dataset_path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            required = {"name", "state", "latitude", "longitude"}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError(
                    f"Gazetteer file {dataset_path} missing required columns: {sorted(required)}",
                )
            for row in reader:
                try:
                    name = row["name"].strip()
                    state = row["state"].strip().upper()
                    lat = float(row["latitude"])
                    lon = float(row["longitude"])
                except (KeyError, ValueError) as exc:  # pragma: no cover - defensive
                    LOG.debug("Skipping invalid gazetteer row %s (%s)", row, exc)
                    continue
                elev_raw = row.get("elevation_m", "") if row.get("elevation_m") is not None else ""
                try:
                    elevation = float(elev_raw) if elev_raw != "" else None
                except ValueError:
                    elevation = None
                key = (cls._normalize(name), state)
                record = TownRecord(
                    name=name,
                    state=state,
                    latitude=lat,
                    longitude=lon,
                    elevation_m=elevation,
                )
                index.setdefault(key, []).append(record)
        return index

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", text.strip().lower()).strip()

    def resolve(self, query: str) -> TownRecord:
        """Return a single TownRecord for ``query`` such as ``'Issaquah, WA'``."""
        name, state = self._parse_query(query)
        key = (self._normalize(name), state)
        matches = self._entries.get(key)
        if matches:
            return matches[0]

        suggestions = []
        for candidate_key, records in self._entries.items():
            cand_name, cand_state = candidate_key
            if cand_state != state:
                continue
            if cand_name.startswith(self._normalize(name)):
                suggestions.append(f"{records[0].name}, {cand_state}")

        raise TownNotFoundError(query, suggestions[:5])

    def _parse_query(self, query: str) -> tuple[str, str]:
        if not query or not query.strip():
            raise TownNotFoundError(query)
        cleaned = query.strip()
        parts = [part.strip() for part in cleaned.split(",") if part.strip()]
        if len(parts) == 2:
            town_part, state_part = parts
        else:
            tokens = cleaned.rsplit(" ", 1)
            if len(tokens) != 2:
                raise TownNotFoundError(query)
            town_part, state_part = tokens
        state_abbrev = self._normalize_state(state_part)
        return town_part, state_abbrev

    def _normalize_state(self, state_text: str) -> str:
        state_clean = state_text.strip().upper()
        if len(state_clean) == 2 and state_clean.isalpha():
            return state_clean
        normalized_query = self._normalize(state_text)
        for name, abbrev in self._state_abbrev.items():
            if normalized_query == self._normalize(name):
                return abbrev
        raise TownNotFoundError(state_text)


def resolve_town(query: str, dataset_path: Path | None = None) -> TownRecord:
    """
    Convenience wrapper around TownGazetteer for one-off lookups.

    The dataset is cached across calls to avoid repeated CSV parsing.
    """
    gazetteer = TownGazetteer(dataset_path=dataset_path)
    return gazetteer.resolve(query)
