"""The fuel plan: where to stop and how much to buy. Pure Python; no Django, no numpy.

The trip is a line from mile 0 to mile `total_miles`. Stations sit on it at their mile
markers, each with a price. The truck starts with an empty tank and may arrive empty.
The method, and why it gives the cheapest plan, is in the architecture document, section 8.

In every function `miles` and `prices` are parallel lists in increasing order of mile.
miles[0] must be 0.0: it is the start, priced at the station nearest the start place.
Several stations may share one mile marker.
"""

from dataclasses import dataclass

RANGE_MILES = 500.0
MILES_PER_GALLON = 10.0
TANK_GALLONS = RANGE_MILES / MILES_PER_GALLON


@dataclass(frozen=True)
class Purchase:
    """Fuel bought at one station. `index` is the station's position in the miles and
    prices lists; `gallons` is exact, not rounded."""

    index: int
    gallons: float


def find_gap(miles: list[float], total_miles: float) -> tuple[float, float] | None:
    """The first stretch with no station that is longer than the truck's range.

    Returns (the mile where it starts, its length), or None if there is no such stretch.
    A plan exists exactly when this returns None. A stretch of exactly 500 miles is allowed.
    """
    raise NotImplementedError


def plan_stops(
    miles: list[float],
    prices: list[float],
    total_miles: float,
    stop_cost: float,
) -> list[Purchase]:
    """The plan with the lowest fuel cost plus `stop_cost` for every stop made.

    `stop_cost` only steers the choice of stops; it is not part of any purchase.
    Returns the purchases in order of mile. Every purchase is for more than zero gallons,
    and the first is always at index 0, because the truck starts empty.

    Raises NoFuelPlan, with where the gap starts and its length, if find_gap() finds one.

    Written as a loop from the last station back to the first, not as a function that
    calls itself, so it never depends on the interpreter's recursion limit.
    """
    raise NotImplementedError


def cheapest_fuel(miles: list[float], prices: list[float], total_miles: float) -> list[Purchase]:
    """The plan with the lowest fuel cost when stops are free.

    The greedy rule: at each stop, if a cheaper station is within range, buy just enough
    to reach the nearest such station; otherwise fill the tank and drive to the cheapest
    station within range. The finish counts as a station with a price of zero.

    Same return value and same error as plan_stops(). Purchases may be very small.
    """
    raise NotImplementedError
