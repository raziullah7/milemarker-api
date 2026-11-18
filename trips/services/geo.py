"""Road geometry: mile markers along the road, and whether the road leaves the USA.

Pure functions over numpy arrays; no Django. The rules are in the architecture document,
sections 5 and 14.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True, eq=False)
class RoadPoints:
    """A road as evenly spaced points, each with its distance from the start.

    lat, lng  degrees
    marker    miles from the start; marker[0] is 0.0 and marker[-1] is the trip length exactly
    """

    lat: np.ndarray
    lng: np.ndarray
    marker: np.ndarray


def resample(coords: np.ndarray, total_miles: float, step_miles: float = 0.5) -> RoadPoints:
    """Re-space a road to one point every `step_miles`, plus its last point.

    coords       shape (n, 2), rows of [lng, lat], as the routing service returns them
    total_miles  the trip length the markers must end on

    The road is measured with our own distance sums and re-spaced on those. The markers
    are then scaled so the last one is `total_miles`, and the last marker is set to
    `total_miles` exactly. Repeated points in `coords` are harmless.
    """
    raise NotImplementedError


def load_borders(path: str | Path) -> dict[str, np.ndarray]:
    """Read the border outlines file: {"CAN": outline, "MEX": outline}.

    Each outline is an array of shape (n, 2), rows of [lng, lat], closed or not.
    """
    raise NotImplementedError


def longest_run_abroad(
    points: RoadPoints,
    borders: dict[str, np.ndarray],
    sample_every_miles: float = 2.0,
) -> float:
    """Miles in the longest unbroken stretch of road inside Canada or Mexico.

    The road is sampled every `sample_every_miles`, not at every point: testing every
    half-mile point is too slow. A sample is only tested if it is north of 41.6 degrees
    (against the "CAN" outline) or south of 32.8 degrees (against "MEX"), the only
    latitudes where either country can be. A stretch of k consecutive samples abroad
    counts as k x sample_every_miles.
    """
    raise NotImplementedError
