"""Two exact methods for the fuel plan, used only by the tests (cases EX-01 and EX-02).

They share no code with trips/services/fuel.py, so agreement with them is evidence that
the plan is right, not that the same mistake was made twice.

lp_cost     the lowest fuel cost when stops are free, from a linear-programming solver
brute_cost  the lowest fuel cost plus stop cost, from every subset of stations, each
            subset priced by the same solver

`miles` and `prices` are parallel lists in increasing order of mile, and miles[0] is 0,
the start, where the truck arrives with an empty tank.
"""

import itertools

import numpy as np
from scipy.optimize import linprog

RANGE_MILES = 500.0
MILES_PER_GALLON = 10.0
TANK_GALLONS = 50.0

# The solver is exact to about 1e-7 gallons, and every real purchase in the tests is far
# larger, so a smaller purchase in its answer is rounding, not a stop.
NEGLIGIBLE_GALLONS = 1e-6


def _solve(
    miles: list[float], prices: list[float], total_miles: float
) -> tuple[float, list[float]] | None:
    """The cheapest purchases when stops are free: (fuel cost, gallons at each station).

    The unknowns are the gallons bought at each station. After buying at stations 0..j the
    truck has bought sum(x[0..j]) and burnt miles[j] / 10, so:
      - it reaches the next station (or the finish):  sum(x[0..j]) >= next mile / 10
      - it does not overfill at station j:            sum(x[0..j]) - miles[j] / 10 <= 50
    Returns None when no purchases satisfy both.
    """
    n = len(miles)
    next_mile = np.array([*miles[1:], total_miles])
    bought_by = np.tril(np.ones((n, n)))  # row j picks out x[0..j]
    a_ub = np.vstack([-bought_by, bought_by])
    b_ub = np.concatenate(
        [-next_mile / MILES_PER_GALLON, TANK_GALLONS + np.array(miles) / MILES_PER_GALLON]
    )
    result = linprog(prices, A_ub=a_ub, b_ub=b_ub, bounds=(0, None), method="highs")
    if result.status == 2:  # the solver's code for "infeasible"
        return None
    assert result.success, result.message
    return float(result.fun), [float(x) for x in result.x]


def lp_cost(miles: list[float], prices: list[float], total_miles: float) -> float | None:
    """The true lowest fuel cost with free stops, or None when no plan exists."""
    solved = _solve(miles, prices, total_miles)
    return None if solved is None else solved[0]


def _has_gap(miles: list[float], total_miles: float) -> bool:
    """True if some stretch between neighbouring stations, or to the finish, exceeds the range."""
    ends = [*miles[1:], total_miles]
    return any(end - start > RANGE_MILES for start, end in zip(miles, ends, strict=True))


def brute_cost(
    miles: list[float], prices: list[float], total_miles: float, stop_cost: float
) -> float | None:
    """The lowest fuel cost plus stop_cost per stop, over every subset of stations.

    Each subset always holds the start. It is priced by the solver, and charged stop_cost
    for each of its stations that buys more than a negligible amount. Returns None when no
    subset, not even all the stations, gives a plan.
    """
    best = None
    for size in range(len(miles)):
        for chosen in itertools.combinations(range(1, len(miles)), size):
            subset = [0, *chosen]
            sub_miles = [miles[i] for i in subset]
            if _has_gap(sub_miles, total_miles):
                continue  # no plan can use only these stations; skip the solver call
            cost, gallons = _solve(sub_miles, [prices[i] for i in subset], total_miles)
            stops = sum(1 for g in gallons if g > NEGLIGIBLE_GALLONS)
            if best is None or cost + stop_cost * stops < best:
                best = cost + stop_cost * stops
    return best
