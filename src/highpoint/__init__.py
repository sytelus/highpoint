"""
HighPoint package initialisation.

Exposes the public API for finding scenic viewpoints based on terrain visibility
and drivability constraints.
"""

from importlib import metadata


def get_version() -> str:
    """Return the installed package version, falling back to source version during development."""
    try:
        return metadata.version("highpoint")
    except metadata.PackageNotFoundError:  # pragma: no cover - only occurs during dev
        return "0.1.0"


__all__ = ["get_version"]
