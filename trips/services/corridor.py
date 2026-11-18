"""Find the stations along a road. Pure functions; no Django.

The rules are in the architecture document, section 7.
"""

from dataclasses import dataclass

import numpy as np
from scipy.spatial import KDTree

from stations.sphere import arc, chord, to_xyz
from stations.types import StationIndex
from trips.services.geo import RoadPoints


@dataclass(frozen=True)
class Candidate:
    """A station the truck could stop at.

    mile             its mile marker: the marker of the road point nearest to it
    price            dollars per gallon
    station          its position in the StationIndex
    off_route_miles  how far its position is from that road point
    point            the position of that road point in the RoadPoints arrays
    """

    mile: float
    price: float
    station: int
    off_route_miles: float
    point: int


def stations_along(
    points: RoadPoints,
    index: StationIndex,
    radius_miles: float = 5.0,
    exclude: int | None = None,
) -> list[Candidate]:
    """Every station within `radius_miles` of the road (inclusive), with its mile marker.

    Left out: the station at index position `exclude` (the start station, which is
    already stop 1), and any station whose mile marker is 0 or the trip length, as the
    truck cannot use those.

    Sorted by mile, then price, then station ID.
    """
    # The tree measures straight lines on the unit sphere, so the radius is given as a
    # chord. scipy keeps only distances strictly below the bound; raising the bound by the
    # smallest step a float allows keeps a station exactly on the limit too.
    tree = KDTree(to_xyz(points.lat, points.lng))
    bound = np.nextafter(chord(radius_miles), np.inf)
    distance, nearest = tree.query(index.xyz, distance_upper_bound=bound)

    # A station with no road point in range comes back with distance inf.
    station = np.flatnonzero(np.isfinite(distance))
    point = nearest[station]
    mile = points.marker[point]
    usable = (mile > 0) & (mile < points.marker[-1])
    if exclude is not None:
        usable &= station != exclude
    station, point, mile = station[usable], point[usable], mile[usable]
    price = index.price[station]
    off_route = arc(distance[station])

    # np.lexsort sorts by its last key first. Index positions follow station-ID order,
    # so sorting by position sorts by station ID.
    order = np.lexsort((station, price, mile))
    return [
        Candidate(
            mile=float(mile[k]),
            price=float(price[k]),
            station=int(station[k]),
            off_route_miles=float(off_route[k]),
            point=int(point[k]),
        )
        for k in order
    ]


def thin(candidates: list[Candidate], window_miles: float = 10.0) -> list[Candidate]:
    """Drop the stations nobody would choose.

    A station is dropped if another within `window_miles` along the road (inclusive) is
    cheaper, or equally cheap and earlier in the list. Each station is compared with
    every station given, including ones that are themselves dropped.

    `candidates` must be in the order stations_along() returns. The result keeps that order.
    """
    mile = np.array([c.mile for c in candidates])
    price = np.array([c.price for c in candidates])
    # The list is sorted by mile, so the stations within the window of station i are one
    # slice of it: from the first at mile - window to the last at mile + window.
    first = np.searchsorted(mile, mile - window_miles, side="left")
    last = np.searchsorted(mile, mile + window_miles, side="right")

    kept = []
    for i, candidate in enumerate(candidates):
        # argmin gives the first of the cheapest in the window. Station i stays only if
        # that is itself: nothing nearby is cheaper, or equally cheap and earlier.
        if first[i] + int(np.argmin(price[first[i] : last[i]])) == i:
            kept.append(candidate)
    return kept
