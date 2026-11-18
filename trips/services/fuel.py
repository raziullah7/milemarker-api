"""The fuel plan: where to stop and how much to buy. Pure Python; no Django, no numpy.

The trip is a line from mile 0 to mile `total_miles`. Stations sit on it at their mile
markers, each with a price. The truck starts with an empty tank and may arrive empty.
The method, and why it gives the cheapest plan, is in the architecture document, section 8.

In every function `miles` and `prices` are parallel lists in increasing order of mile.
miles[0] must be 0.0: it is the start, priced at the station nearest the start place.
Several stations may share one mile marker.
"""

from dataclasses import dataclass
from typing import NamedTuple

from trips.exceptions import NoFuelPlan

RANGE_MILES = 500.0
MILES_PER_GALLON = 10.0
TANK_GALLONS = RANGE_MILES / MILES_PER_GALLON

# Costs closer than this are the same cost. The same total reached by two different sums
# can differ in its last binary digits, and that must not decide between two plans.
SAME_COST_DOLLARS = 1e-9


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
    ends = [*miles[1:], total_miles]
    for start, end in zip(miles, ends, strict=True):
        if end - start > RANGE_MILES:
            return start, end - start
    return None


# An entry of plan_stops' table: (a station where the truck stops to buy, the station where
# it last filled the tank, or None if it arrived there empty).
_Entry = tuple[int, int | None]


class _Choice(NamedTuple):
    """The best way on to the finish from one entry of plan_stops' table."""

    cost: float  # fuel from here to the finish, plus the stop cost of every stop, this one too
    stops: int  # stops from here to the finish, this one included
    gallons: float  # bought at this stop
    next_entry: _Entry | None  # the entry of the next stop; None if the next stop is the finish


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
    _require_plan(miles, total_miles)

    # best[(u, filled_at)] is the best way on for a truck that stops to buy at station u.
    # It reached u either with an empty tank (filled_at is None) or with what is left of a
    # full tank bought at station filled_at: the two moves of section 8 leave no other
    # case. Every entry depends only on entries of later stations, so filling the table
    # from the last station back means each one is ready when it is needed.
    best: dict[_Entry, _Choice | None] = {}

    for u in range(len(miles) - 1, -1, -1):
        ahead = _reachable_from(miles, u)

        # Move 2 leaves u with a full tank, so its best next stop is the same however the
        # truck reached u. Find it once: the dearer station v whose entry (v, u) is best.
        fill_to, after_fill = None, None
        for v in ahead:
            if prices[v] > prices[u] and _is_better(best[(v, u)], after_fill):
                fill_to, after_fill = v, best[(v, u)]

        # A tank is only filled to carry fuel past a dearer station, so a tank from
        # station k is only ever carried to u if u is dearer than k.
        filled_ats = [None]
        for k in range(u - 1, -1, -1):
            if miles[u] - miles[k] > RANGE_MILES:
                break
            if prices[k] < prices[u]:
                filled_ats.append(k)

        for filled_at in filled_ats:
            # Where the fuel now in the tank was bought, and how far it goes from there.
            # The miles still to buy for are then (mile - tank_from) - tank_miles: the same
            # subtraction as the range tests in find_gap() and _reachable_from(). So "the
            # tank already reaches v" and "v is in range of where the tank was filled" never
            # disagree, not even in the last binary digit, and no plan is lost on a stretch
            # of exactly 500 miles.
            if filled_at is None:
                tank_from, tank_miles = miles[u], 0.0
                fill_gallons = TANK_GALLONS
            else:
                tank_from, tank_miles = miles[filled_at], RANGE_MILES
                fill_gallons = (miles[u] - miles[filled_at]) / MILES_PER_GALLON

            # Options are offered in order of their next stop, the finish last, and only a
            # strictly better one replaces the choice: so on a tie the earlier station stays.
            choice = None
            for v in ahead:
                option = None
                if prices[v] <= prices[u]:
                    # Move 1: buy just enough to reach v, and arrive there empty. If the
                    # tank already reaches v this stop would buy nothing, so it is no option.
                    short_miles = miles[v] - tank_from - tank_miles
                    if short_miles > 0:
                        gallons = short_miles / MILES_PER_GALLON
                        option = _buy_then(
                            gallons, prices[u], stop_cost, best[(v, None)], (v, None)
                        )
                elif v == fill_to and fill_gallons > 0:
                    # Move 2: fill the tank, to carry this cheaper fuel past v.
                    option = _buy_then(fill_gallons, prices[u], stop_cost, after_fill, (v, u))
                if _is_better(option, choice):
                    choice = option

            short_miles = total_miles - tank_from - tank_miles
            if total_miles - miles[u] <= RANGE_MILES and short_miles > 0:
                # Buy just enough to reach the finish.
                gallons = short_miles / MILES_PER_GALLON
                option = _Choice(stop_cost + gallons * prices[u], 1, gallons, None)
                if _is_better(option, choice):
                    choice = option

            best[(u, filled_at)] = choice

    # Follow the choices from the start, where the truck arrives empty. find_gap() has
    # passed, so the start always has a choice.
    purchases = []
    entry = (0, None)
    while entry is not None:
        choice = best[entry]
        purchases.append(Purchase(entry[0], choice.gallons))
        entry = choice.next_entry
    return purchases


def cheapest_fuel(miles: list[float], prices: list[float], total_miles: float) -> list[Purchase]:
    """The plan with the lowest fuel cost when stops are free.

    The greedy rule: at each stop, if a cheaper station is within range, buy just enough
    to reach the nearest such station; otherwise fill the tank and drive to the cheapest
    station within range. The finish counts as a station with a price of zero.

    Same return value and same error as plan_stops(). Purchases may be very small.
    """
    _require_plan(miles, total_miles)
    # Priced at zero, the finish is "a cheaper station" from every stop in range of it, so
    # the truck never buys more than it needs to arrive.
    stop_miles = [*miles, total_miles]
    stop_prices = [*prices, 0.0]
    finish = len(miles)

    purchases = []
    here = 0
    # The tank is tracked as the mile where its fuel runs out, not as gallons, so no
    # rounding builds up from stop to stop and "already enough" is an exact comparison.
    tank_lasts_to = miles[0]
    while here != finish:
        ahead = _reachable_from(stop_miles, here)
        cheaper = next((v for v in ahead if stop_prices[v] < stop_prices[here]), None)
        if cheaper is not None:
            next_stop, buy_to = cheaper, stop_miles[cheaper]
        else:
            # min() keeps the first of equal prices, so ties go to the nearest station.
            next_stop = min(ahead, key=lambda v: stop_prices[v])
            buy_to = stop_miles[here] + RANGE_MILES
        # The tank may already reach buy_to, with fuel carried from a cheaper station.
        if buy_to > tank_lasts_to:
            purchases.append(Purchase(here, (buy_to - tank_lasts_to) / MILES_PER_GALLON))
            tank_lasts_to = buy_to
        here = next_stop
    return purchases


def _require_plan(miles: list[float], total_miles: float) -> None:
    """Raise NoFuelPlan if find_gap() finds a stretch the truck cannot cross."""
    gap = find_gap(miles, total_miles)
    if gap is not None:
        start, length = gap
        raise NoFuelPlan(
            f"No fuel station is listed for {length:.1f} miles from mile {start:.1f}, "
            f"more than the truck's range of {RANGE_MILES:.0f} miles.",
            gap_start_mile=start,
            gap_miles=length,
        )


def _reachable_from(miles: list[float], u: int) -> range:
    """The indices after u that a full tank bought at u reaches: miles are in order, so
    they run from u + 1 up to the first one out of range."""
    v = u + 1
    while v < len(miles) and miles[v] - miles[u] <= RANGE_MILES:
        v += 1
    return range(u + 1, v)


def _buy_then(
    gallons: float, price: float, stop_cost: float, rest: _Choice | None, entry: _Entry
) -> _Choice | None:
    """Stop here and buy `gallons` at `price`, then go on as `rest`, the choice at the next
    stop's table entry. None if there is no way on from there."""
    if rest is None:
        return None
    return _Choice(stop_cost + gallons * price + rest.cost, rest.stops + 1, gallons, entry)


def _is_better(option: _Choice | None, choice: _Choice | None) -> bool:
    """True if `option` should replace `choice`: it costs less, or the same with fewer
    stops. On a full tie `choice` stays; it was offered first, so its next stop is earlier."""
    if option is None:
        return False
    if choice is None:
        return True
    if abs(option.cost - choice.cost) > SAME_COST_DOLLARS:
        return option.cost < choice.cost
    return option.stops < choice.stops
