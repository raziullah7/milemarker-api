"""Find the stations along a road. Pure functions; no Django.

The rules are in the architecture document, section 7.
"""

from dataclasses import dataclass

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
    raise NotImplementedError


def thin(candidates: list[Candidate], window_miles: float = 10.0) -> list[Candidate]:
    """Drop the stations nobody would choose.

    A station is dropped if another within `window_miles` along the road (inclusive) is
    cheaper, or equally cheap and earlier in the list. Each station is compared with
    every station given, including ones that are themselves dropped.

    `candidates` must be in the order stations_along() returns. The result keeps that order.
    """
    raise NotImplementedError
