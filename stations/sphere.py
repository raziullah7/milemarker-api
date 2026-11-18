"""Distance maths on a sphere. Pure functions over numbers and numpy arrays; no Django.

Two ideas are used everywhere in the project:

* The haversine formula gives the distance over the ground between two points.
* A point can also be written as x, y, z on a sphere of radius 1. The straight line
  between two such points (the "chord") grows with the ground distance between them,
  so a nearest-neighbour search on x, y, z finds the nearest point on the ground.
  chord() and arc() convert between the two measures.

Every function takes degrees, latitude first, and accepts floats or numpy arrays.
"""

import numpy as np

EARTH_RADIUS_MILES = 3958.8


def haversine_miles(lat1, lng1, lat2, lng2):
    """Distance over the ground in miles between (lat1, lng1) and (lat2, lng2).

    Broadcasts like numpy: arrays of points in, an array of distances out.
    """
    lat1, lng1, lat2, lng2 = (np.radians(v) for v in (lat1, lng1, lat2, lng2))
    half = (
        np.sin((lat2 - lat1) / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin((lng2 - lng1) / 2) ** 2
    )
    # Rounding can push `half` a hair above 1 for opposite points; clip keeps arcsin valid.
    return 2 * EARTH_RADIUS_MILES * np.arcsin(np.sqrt(np.clip(half, 0.0, 1.0)))


def to_xyz(lat, lng) -> np.ndarray:
    """Points on the unit sphere, as an array of shape (n, 3). A single point gives shape (1, 3)."""
    lat = np.radians(np.atleast_1d(np.asarray(lat, dtype=float)))
    lng = np.radians(np.atleast_1d(np.asarray(lng, dtype=float)))
    return np.column_stack([np.cos(lat) * np.cos(lng), np.cos(lat) * np.sin(lng), np.sin(lat)])


def chord(miles):
    """Straight-line distance on the unit sphere that corresponds to `miles` over the ground."""
    return 2 * np.sin(np.asarray(miles, dtype=float) / (2 * EARTH_RADIUS_MILES))


def arc(chord_length):
    """The reverse of chord(): miles over the ground for a straight line on the unit sphere."""
    half = np.clip(np.asarray(chord_length, dtype=float) / 2, 0.0, 1.0)
    return 2 * EARTH_RADIUS_MILES * np.arcsin(half)
