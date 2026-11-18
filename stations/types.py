"""The shapes station data and places take in memory. Pure data classes; no Django.

They live here, not next to the model or the places table, so that the trip-planning
code can use them without importing anything from Django.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

import numpy as np

from stations.sphere import to_xyz


@dataclass(frozen=True)
class Place:
    """A resolved place (stations/places.py). `label` is "City, ST" in the table's own
    spelling."""

    label: str
    lat: float
    lng: float


@dataclass(frozen=True)
class StationInfo:
    """One station as the CSV describes it. `price` keeps every digit the file has."""

    opis_id: int
    name: str
    address: str
    city: str
    state: str
    price: Decimal


@dataclass(frozen=True, eq=False)
class StationIndex:
    """Every station, held as parallel arrays for fast searching.

    Position k in each array, and info[k], describe the same station.
    Stations are in station-ID order, so results never depend on chance.

    lat, lng  degrees
    price     dollars per gallon as floats, for arithmetic; info[k].price is the exact figure
    xyz       the same positions on the unit sphere, shape (n, 3) (see stations/sphere.py)
    """

    lat: np.ndarray
    lng: np.ndarray
    price: np.ndarray
    xyz: np.ndarray
    info: tuple[StationInfo, ...]

    def __len__(self) -> int:
        return len(self.info)


def build_index(stations: Sequence[tuple[StationInfo, float, float]]) -> StationIndex:
    """Make a StationIndex from (info, lat, lng) triples.

    The triples are sorted by station ID first. Used by stations/index.py with rows
    from the database, and by tests with hand-made stations.
    """
    ordered = sorted(stations, key=lambda s: s[0].opis_id)
    lat = np.array([s[1] for s in ordered], dtype=float)
    lng = np.array([s[2] for s in ordered], dtype=float)
    return StationIndex(
        lat=lat,
        lng=lng,
        price=np.array([float(s[0].price) for s in ordered], dtype=float),
        xyz=to_xyz(lat, lng) if len(ordered) else np.empty((0, 3)),
        info=tuple(s[0] for s in ordered),
    )
