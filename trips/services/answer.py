"""Build the response body from a finished plan. Pure functions; no Django.

All rounding happens here, in decimal arithmetic, so that every figure in a response can
be reproduced from the response with a calculator. The rules are in the architecture
document, section 8 ("Money and rounding") and section 11 (the response).
"""

from dataclasses import dataclass
from decimal import Decimal

from stations.places import Place
from stations.types import StationInfo
from trips.services.geo import RoadPoints

# A first fill-up station further from the start than this earns a warning.
FAR_FIRST_FILL_MILES = 25.0

# A purchase smaller than this is not counted as a stop in the lowest-possible figures.
SMALLEST_COUNTED_GALLONS = 0.005


@dataclass(frozen=True)
class Stop:
    """One purchase in the chosen plan, before rounding.

    info       the station it is priced at
    mile       its mile marker (0.0 for the start)
    lat, lng   where it is drawn: the start place for stop 1, otherwise the road point
               nearest the station
    gallons    exact gallons bought
    """

    info: StationInfo
    mile: float
    lat: float
    lng: float
    gallons: float


def build_answer(
    *,
    start: Place,
    finish: Place,
    distance_miles: float,
    road: RoadPoints,
    stops: list[Stop],
    cheapest: list[tuple[Decimal, float]],
    first_fill_miles: float,
    stop_cost: Decimal,
) -> dict:
    """The response body without `meta`, with its keys in this order:
    summary, warnings, assumptions, fuel_stops, map.

    distance_miles    the trip length, already rounded to 0.1 mile
    stops             the chosen plan in order; stops[0] is the fill-up at the start
    cheapest          the free-stops plan as (exact price, exact gallons) pairs, for
                      lowest_possible_fuel_cost and lowest_possible_stops
    first_fill_miles  distance from the start place to the station stop 1 is priced at
    stop_cost         the stop cost the plan was chosen with

    Rounding, for the plan and for `cheapest` alike: each purchase's gallons to 2
    decimals, with any difference from distance_miles / 10 added to the largest
    purchase; each cost = gallons x exact price, rounded half-up to cents; the total is
    the sum of the costs.
    """
    raise NotImplementedError
