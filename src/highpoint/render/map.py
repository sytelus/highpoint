"""Simple matplotlib rendering for HighPoint results."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Optional

import matplotlib.pyplot as plt
import numpy as np

from highpoint.data.terrain import TerrainGrid
from highpoint.pipeline import ViewpointResult

LOG = logging.getLogger(__name__)


def render_map(
    results: Iterable[ViewpointResult],
    terrain: Optional[TerrainGrid],
    output_path: Path,
) -> None:
    """Render a PNG overview map if matplotlib is available."""
    fig, ax = plt.subplots(figsize=(6, 6), dpi=150)

    if terrain is not None:
        xs, ys = terrain.coordinates()
        elev = terrain.elevations
        image = ax.pcolormesh(xs, ys, elev, shading="auto", cmap="terrain")
        fig.colorbar(image, ax=ax, label="Elevation (m)")

    candidates_x = [result.candidate.x for result in results]
    candidates_y = [result.candidate.y for result in results]

    ax.scatter(candidates_x, candidates_y, marker="o", color="crimson", label="Candidate")

    for idx, result in enumerate(results, start=1):
        ax.text(result.candidate.x, result.candidate.y, str(idx), color="white", fontsize=8)
        if result.drivability and result.drivability.access_point:
            access_x, access_y = result.drivability.access_point.coordinate
            ax.scatter(access_x, access_y, marker="^", color="navy", label="Access point" if idx == 1 else None)

    ax.set_xlabel("Easting (m)")
    ax.set_ylabel("Northing (m)")
    ax.set_title("HighPoint Candidate Overview")
    ax.legend(loc="upper right")
    ax.set_aspect("equal")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    LOG.info("Rendered map saved to %s", output_path)
