"""Road geometry: mile markers along the road, and whether the road leaves the USA.

Pure functions over numpy arrays; no Django. The rules are in the architecture document,
sections 5 and 14.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from stations.sphere import haversine_miles

# Canada reaches no further south than about 41.7 N, and Mexico no further north than
# about 32.7 N, so a point between these latitudes cannot be in either.
CANADA_ONLY_NORTH_OF = 41.6
MEXICO_ONLY_SOUTH_OF = 32.8


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
    lng, lat = coords[:, 0], coords[:, 1]
    segment = haversine_miles(lat[:-1], lng[:-1], lat[1:], lng[1:])

    # np.interp expects distances that rise from one point to the next, so a repeated
    # point (a segment of length zero) is dropped. It adds nothing to the road.
    keep = np.concatenate([[True], segment > 0])
    lng, lat = lng[keep], lat[keep]
    along = np.concatenate([[0.0], np.cumsum(segment[segment > 0])])

    own_miles = along[-1]
    marks = np.append(np.arange(0.0, own_miles, step_miles), own_miles)
    marker = marks * (total_miles / own_miles)
    # Scaling can leave the last marker a rounding error away from the trip length.
    marker[-1] = total_miles
    return RoadPoints(
        lat=np.interp(marks, along, lat),
        lng=np.interp(marks, along, lng),
        marker=marker,
    )


def load_borders(path: str | Path) -> dict[str, np.ndarray]:
    """Read the border outlines file: {"CAN": outline, "MEX": outline}.

    Each outline is an array of shape (n, 2), rows of [lng, lat], closed or not.
    """
    with open(path, encoding="utf-8") as f:
        outlines = json.load(f)
    return {country: np.array(outline, dtype=float) for country, outline in outlines.items()}


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
    marks = np.arange(0.0, points.marker[-1], sample_every_miles)
    lat = np.interp(marks, points.marker, points.lat)
    lng = np.interp(marks, points.marker, points.lng)

    abroad = np.zeros(len(marks), dtype=bool)
    north = lat > CANADA_ONLY_NORTH_OF
    south = lat < MEXICO_ONLY_SOUTH_OF
    abroad[north] = _inside(lng[north], lat[north], borders["CAN"])
    abroad[south] = _inside(lng[south], lat[south], borders["MEX"])

    longest = run = 0
    for is_abroad in abroad.tolist():
        run = run + 1 if is_abroad else 0
        longest = max(longest, run)
    return longest * sample_every_miles


def _inside(lng: np.ndarray, lat: np.ndarray, outline: np.ndarray) -> np.ndarray:
    """Which points lie inside the outline, by ray casting.

    A ray from each point runs due east. It crosses the outline's edges an odd number of
    times if the point is inside, an even number if it is outside.
    """
    # Edge k runs from vertex k to vertex k + 1, and the last vertex joins the first, so
    # an open outline is closed. A closed one gains an edge of length zero, never crossed.
    x1, y1 = outline[:, 0], outline[:, 1]
    x2, y2 = np.roll(x1, -1), np.roll(y1, -1)

    # Speed: keep only edges some ray could cross. An edge is crossed at latitude y when
    # one end is above y and the other is not, so a flat edge is never crossed, and an
    # edge must span part of the points' latitudes and reach east of the westmost point.
    if len(lat) == 0:
        return np.zeros(0, dtype=bool)
    useful = (
        (y1 != y2)
        & (np.minimum(y1, y2) <= lat.max())
        & (np.maximum(y1, y2) > lat.min())
        & (np.maximum(x1, x2) > lng.min())
    )
    x1, y1, x2, y2 = x1[useful], y1[useful], x2[useful], y2[useful]

    # One row per point, one column per edge.
    y = lat[:, None]
    spans = (y1 > y) != (y2 > y)
    # The longitude where each edge's line meets the point's latitude. No edge is flat,
    # so the division is safe; the value only counts where the edge spans that latitude.
    crossing_lng = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
    crossings = spans & (lng[:, None] < crossing_lng)
    return crossings.sum(axis=1) % 2 == 1
