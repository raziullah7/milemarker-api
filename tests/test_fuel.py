"""The fuel plan. Test IDs (FU-01 ..., EX-01 ...) refer to docs/test-cases.md, sections 2.6
and 2.7. Purchases are written (index, gallons); gallons and costs match within 1e-9."""

import functools
import itertools
import random
from collections.abc import Callable

import pytest

from tests.exact import brute_cost, lp_cost
from trips.exceptions import NoFuelPlan
from trips.services.fuel import Purchase, cheapest_fuel, find_gap, plan_stops

# Inputs used by more than one case: (miles, prices, total_miles).
FU03 = ([0.0, 100.0], [4.00, 3.00], 400.0)
FU04 = ([0.0, 300.0], [3.00, 4.00], 700.0)
FU07 = ([0.0, 10.0], [3.10, 3.00], 400.0)
FU12 = ([0.0], [3.00], 501.0)
FU13 = ([0.0, 100.0], [3.00, 3.00], 700.0)
FU14 = ([0.0, 503.0], [3.20, 3.00], 990.0)
FU16 = ([0.0], [3.00], 500.1)
FU20 = ([0.0, 100.0, 105.0, 400.0, 650.0], [4.00, 3.00, 3.01, 3.50, 2.50], 900.0)


def fuel_cost(purchases: list[Purchase], prices: list[float]) -> float:
    """Gallons x price over the plan; the stop cost is never part of it."""
    return sum(p.gallons * prices[p.index] for p in purchases)


def assert_plan(
    purchases: list[Purchase],
    prices: list[float],
    expected: list[tuple[int, float]],
    expected_cost: float,
) -> None:
    """The purchases are exactly the expected (index, gallons) pairs, and cost what they should."""
    assert [p.index for p in purchases] == [index for index, _ in expected]
    assert [p.gallons for p in purchases] == pytest.approx([g for _, g in expected], abs=1e-9)
    assert fuel_cost(purchases, prices) == pytest.approx(expected_cost, abs=1e-9)


# ---------------------------------------------------------------- FU: hand-worked cases


def test_fu01_finish_within_range_of_the_start():
    miles, prices, total = [0.0], [3.00], 300.0
    assert_plan(plan_stops(miles, prices, total, 0), prices, [(0, 30)], 90.00)


def test_fu02_finish_exactly_one_tank_away():
    miles, prices, total = [0.0], [3.00], 500.0
    assert_plan(plan_stops(miles, prices, total, 0), prices, [(0, 50)], 150.00)


def test_fu03_cheaper_station_ahead():
    miles, prices, total = FU03
    assert_plan(plan_stops(miles, prices, total, 0), prices, [(0, 10), (1, 30)], 130.00)


def test_fu04_dearer_station_ahead_fill_up_first():
    miles, prices, total = FU04
    assert_plan(plan_stops(miles, prices, total, 0), prices, [(0, 50), (1, 20)], 230.00)


def test_fu05_dearer_station_skipped_when_finish_in_range():
    miles, prices, total = [0.0, 200.0], [3.00, 5.00], 450.0
    assert_plan(plan_stops(miles, prices, total, 0), prices, [(0, 45)], 135.00)


def test_fu06_equal_prices():
    miles, prices, total = [0.0, 250.0], [3.00, 3.00], 600.0
    purchases = plan_stops(miles, prices, total, 0)
    assert sum(p.gallons for p in purchases) == pytest.approx(60, abs=1e-9)
    assert fuel_cost(purchases, prices) == pytest.approx(180.00, abs=1e-9)


def test_fu07_small_saving_taken_when_stops_are_free():
    miles, prices, total = FU07
    assert_plan(plan_stops(miles, prices, total, 0), prices, [(0, 1), (1, 39)], 120.10)


def test_fu08_small_saving_still_worth_a_3_dollar_stop():
    miles, prices, total = FU07
    assert_plan(plan_stops(miles, prices, total, 3), prices, [(0, 1), (1, 39)], 120.10)


def test_fu09_small_saving_not_worth_a_10_dollar_stop():
    miles, prices, total = FU07
    assert_plan(plan_stops(miles, prices, total, 10), prices, [(0, 40)], 124.00)


def test_fu10_two_stations_at_one_mile():
    miles, prices, total = [0.0, 100.0, 100.0], [4.00, 3.00, 3.50], 400.0
    assert_plan(plan_stops(miles, prices, total, 0), prices, [(0, 10), (1, 30)], 130.00)


def test_fu11_stop_cost_prefers_one_stop_over_two():
    miles, prices, total = [0.0, 495.0, 503.0], [3.20, 3.10, 3.00], 990.0
    assert_plan(plan_stops(miles, prices, total, 10), prices, [(0, 49.5), (1, 49.5)], 311.85)


def test_fu12_finish_one_mile_out_of_range():
    with pytest.raises(NoFuelPlan) as caught:
        plan_stops(*FU12, 0)
    assert caught.value.details == pytest.approx({"gap_start_mile": 0.0, "gap_miles": 501.0})


def test_fu13_gap_after_the_last_station():
    with pytest.raises(NoFuelPlan) as caught:
        plan_stops(*FU13, 0)
    assert caught.value.details == pytest.approx({"gap_start_mile": 100.0, "gap_miles": 600.0})


def test_fu14_first_station_out_of_range():
    with pytest.raises(NoFuelPlan) as caught:
        plan_stops(*FU14, 10)
    assert caught.value.details == pytest.approx({"gap_start_mile": 0.0, "gap_miles": 503.0})


def test_fu15_stretches_of_exactly_500_miles_are_allowed():
    miles, prices, total = [0.0, 500.0], [3.00, 4.00], 1000.0
    assert_plan(plan_stops(miles, prices, total, 0), prices, [(0, 50), (1, 50)], 350.00)


def test_fu16_a_tenth_of_a_mile_too_far():
    with pytest.raises(NoFuelPlan) as caught:
        plan_stops(*FU16, 0)
    assert caught.value.details == pytest.approx({"gap_start_mile": 0.0, "gap_miles": 500.1})


def test_fu17_stop_that_saves_more_than_it_costs():
    miles, prices, total = FU07
    assert_plan(plan_stops(miles, prices, total, 3.89), prices, [(0, 1), (1, 39)], 120.10)


def test_fu18_stop_that_saves_less_than_it_costs():
    miles, prices, total = FU07
    assert_plan(plan_stops(miles, prices, total, 3.91), prices, [(0, 40)], 124.00)


def test_fu19_very_short_trip():
    miles, prices, total = [0.0], [3.00], 0.5
    assert_plan(plan_stops(miles, prices, total, 10), prices, [(0, 0.05)], 0.15)


def test_fu20_top_up_to_carry_cheap_fuel_past_a_dearer_station():
    miles, prices, total = FU20
    expected = [(0, 10), (1, 50), (2, 0.5), (3, 4.5), (4, 25)]
    assert_plan(plan_stops(miles, prices, total, 0), prices, expected, 269.755)


def test_fu21_fu20_without_the_station_at_mile_105():
    miles, prices, total = [0.0, 100.0, 400.0, 650.0], [4.00, 3.00, 3.50, 2.50], 900.0
    expected = [(0, 10), (1, 50), (2, 5), (3, 25)]
    assert_plan(plan_stops(miles, prices, total, 0), prices, expected, 270.00)


@pytest.mark.parametrize(
    ("trip", "expected", "expected_cost"),
    [
        (FU03, [(0, 10), (1, 30)], 130.00),
        (FU04, [(0, 50), (1, 20)], 230.00),
        (FU07, [(0, 1), (1, 39)], 120.10),
        (FU20, [(0, 10), (1, 50), (2, 0.5), (3, 4.5), (4, 25)], 269.755),
    ],
    ids=["fu03", "fu04", "fu07", "fu20"],
)
def test_fu22_cheapest_fuel_matches_the_hand_worked_plans(trip, expected, expected_cost):
    miles, prices, total = trip
    assert_plan(cheapest_fuel(miles, prices, total), prices, expected, expected_cost)


def test_fu23_cheapest_fuel_keeps_a_tiny_purchase():
    miles, prices, total = [0.0, 0.03], [3.50, 3.00], 300.0
    purchases = cheapest_fuel(miles, prices, total)
    assert_plan(purchases, prices, [(0, 0.003), (1, 29.997)], 90.0015)
    # Only one purchase is 0.005 gallons or more: the start's would show as 0.00 gallons.
    assert sum(1 for p in purchases if p.gallons >= 0.005) == 1


@pytest.mark.parametrize(
    ("miles", "total", "expected"),
    [
        ([0.0], 500.0, None),
        ([0.0], 500.1, (0.0, 500.1)),
        ([0.0, 100.0], 700.0, (100.0, 600.0)),
        ([0.0, 503.0], 990.0, (0.0, 503.0)),
        ([0.0, 495.0, 503.0], 990.0, None),
    ],
)
def test_fu24_find_gap(miles, total, expected):
    gap = find_gap(miles, total)
    if expected is None:
        assert gap is None
    else:
        assert gap == pytest.approx(expected)


@pytest.mark.parametrize(
    ("trip", "gap"),
    [
        (FU12, (0.0, 501.0)),
        (FU13, (100.0, 600.0)),
        (FU14, (0.0, 503.0)),
        (FU16, (0.0, 500.1)),
    ],
    ids=["fu12", "fu13", "fu14", "fu16"],
)
@pytest.mark.parametrize(
    "planner",
    [functools.partial(plan_stops, stop_cost=10), cheapest_fuel],
    ids=["plan_stops", "cheapest_fuel"],
)
def test_fu25_no_plan_from_either_planner(planner, trip, gap):
    with pytest.raises(NoFuelPlan) as caught:
        planner(*trip)
    details = caught.value.details
    assert (details["gap_start_mile"], details["gap_miles"]) == pytest.approx(gap)


# Not yet in docs/test-cases.md: the tie rule of brief 3C. On equal cost the plan with fewer
# stops wins, then the one whose next stop is the earlier station.
@pytest.mark.parametrize(
    ("total", "expected"),
    [
        (400.0, [(0, 40)]),  # one stop or two, all at $3.00: one stop
        (600.0, [(0, 10), (1, 50)]),  # two stops either way: the earlier second stop
    ],
)
def test_fu26_ties_go_to_fewer_stops_then_the_earlier_station(total, expected):
    miles, prices = [0.0, 100.0, 200.0], [3.00, 3.00, 3.00]
    assert_plan(plan_stops(miles, prices, total, 0), prices, expected, 3.00 * total / 10)


# ---------------------------------------------------------------- EX: against exact methods
#
# EX-02 prices every subset of stations with the solver: a trip of 10 stations is 512
# solver calls. At the size docs/test-cases.md gives (250 trips of up to 10 stations) that
# is 13,506 calls, 16 to 26 seconds on the development laptop, over the 20 seconds the
# default run allows. So the default run uses 250 trips of up to 8 stations, and the full
# size runs with: uv run pytest -m slow tests/test_fuel.py

EX02_MOST_STATIONS = 8
EX02_MOST_STATIONS_FULL = 10
STOP_COSTS = [1, 5, 10, 25, 60]
TOLERANCE = 1e-6  # dollars

Trip = tuple[list[float], list[float], float]  # (miles, prices, total_miles)


def random_trip(
    rng: random.Random, most_stations: int, shortest: float, longest: float, tie_share: float
) -> Trip:
    """A trip of 1 to `most_stations` stations at random 0.1-mile markers, with random
    3-decimal prices; in `tie_share` of trips the prices come from three values only, so
    that many tie."""
    n = rng.randint(1, most_stations)
    total = rng.uniform(shortest, longest)
    miles = [0.0, *sorted(round(rng.uniform(1, total - 1), 1) for _ in range(n - 1))]
    prices = [round(rng.uniform(2.6, 4.5), 3) for _ in range(n)]
    if rng.random() < tie_share:
        prices = [rng.choice([2.90, 3.10, 3.30]) for _ in range(n)]
    return miles, prices, total


def ex01_trips() -> list[Trip]:
    """EX-01's 400 trips: 1 to 28 stations over 50 to 3,000 miles, 30% with tied prices.
    The seed is fixed, so every call gives the same trips."""
    rng = random.Random(1)
    return [random_trip(rng, 28, 50, 3000, tie_share=0.3) for _ in range(400)]


def ex02_trips(most_stations: int) -> list[tuple[Trip, float]]:
    """EX-02's 250 trips: 1 to `most_stations` stations over 100 to 1,800 miles, each with
    a stop cost. The seed is fixed, so every call gives the same trips."""
    rng = random.Random(2)
    return [
        (random_trip(rng, most_stations, 100, 1800, 0.0), rng.choice(STOP_COSTS))
        for _ in range(250)
    ]


def has_no_plan(planner: Callable[..., list[Purchase]], *args: object) -> bool:
    """True if the planner raises NoFuelPlan for these arguments."""
    try:
        planner(*args)
    except NoFuelPlan:
        return True
    return False


def test_ex01_free_stops_match_linear_programming():
    trips = ex01_trips()
    feasible = 0
    for miles, prices, total in trips:
        exact = lp_cost(miles, prices, total)
        if exact is None:
            assert find_gap(miles, total) is not None
            assert has_no_plan(plan_stops, miles, prices, total, 0)
            assert has_no_plan(cheapest_fuel, miles, prices, total)
            continue
        feasible += 1
        plan = plan_stops(miles, prices, total, 0)
        assert fuel_cost(plan, prices) == pytest.approx(exact, abs=TOLERANCE)
        cheapest = cheapest_fuel(miles, prices, total)
        assert fuel_cost(cheapest, prices) == pytest.approx(exact, abs=TOLERANCE)
    # Both outcomes must occur, or half of the check is idle.
    assert 0 < feasible < len(trips)


def check_ex02(most_stations: int) -> None:
    """plan_stops' fuel + stop cost x stops equals the brute-force minimum on every trip."""
    trips = ex02_trips(most_stations)
    feasible = 0
    for (miles, prices, total), stop_cost in trips:
        exact = brute_cost(miles, prices, total, stop_cost)
        if exact is None:
            assert has_no_plan(plan_stops, miles, prices, total, stop_cost)
            continue
        feasible += 1
        plan = plan_stops(miles, prices, total, stop_cost)
        objective = fuel_cost(plan, prices) + stop_cost * len(plan)
        assert objective == pytest.approx(exact, abs=TOLERANCE)
    assert 0 < feasible < len(trips)


def test_ex02_stop_cost_matches_brute_force():
    check_ex02(EX02_MOST_STATIONS)


@pytest.mark.slow
def test_ex02_stop_cost_matches_brute_force_full_size():
    check_ex02(EX02_MOST_STATIONS_FULL)


def assert_drivable(miles: list[float], total: float, plan: list[Purchase]) -> None:
    """Drive the plan mile by mile: the tank never goes below empty or above full, the
    gallons cover the trip exactly, and no stretch without a purchase exceeds 500 miles."""
    assert plan[0].index == 0
    assert [p.index for p in plan] == sorted({p.index for p in plan})
    tank, here = 0.0, 0.0
    for purchase in plan:
        assert purchase.gallons > 0
        assert miles[purchase.index] - here <= 500
        tank -= (miles[purchase.index] - here) / 10
        assert tank >= -1e-9
        tank += purchase.gallons
        assert tank <= 50 + 1e-9
        here = miles[purchase.index]
    assert total - here <= 500
    assert tank - (total - here) / 10 >= -1e-9
    assert sum(p.gallons for p in plan) == pytest.approx(total / 10, abs=1e-9)


def test_ex03_every_plan_can_be_driven():
    # The planners are deterministic, so planning the EX-01 and EX-02 trips again gives
    # exactly the plans those cases checked. Without the slow exact methods this is quick,
    # so it covers the full-size EX-02 trips as well as the default ones.
    for miles, prices, total in ex01_trips():
        if find_gap(miles, total) is None:
            assert_drivable(miles, total, plan_stops(miles, prices, total, 0))
            assert_drivable(miles, total, cheapest_fuel(miles, prices, total))
    for most_stations in (EX02_MOST_STATIONS, EX02_MOST_STATIONS_FULL):
        for (miles, prices, total), stop_cost in ex02_trips(most_stations):
            if find_gap(miles, total) is None:
                assert_drivable(miles, total, plan_stops(miles, prices, total, stop_cost))


def test_ex04_higher_stop_cost_never_means_more_stops_or_less_fuel_money():
    rng = random.Random(4)
    checked = 0
    while checked < 100:
        miles, prices, total = random_trip(rng, 28, 50, 3000, tie_share=0.3)
        if find_gap(miles, total) is not None:
            continue  # EX-04 needs trips that have a plan
        checked += 1
        plans = [plan_stops(miles, prices, total, stop_cost) for stop_cost in [0, 5, 10, 25, 60]]
        stops = [len(plan) for plan in plans]
        costs = [fuel_cost(plan, prices) for plan in plans]
        assert stops == sorted(stops, reverse=True)
        for lower, higher in itertools.pairwise(costs):
            assert higher >= lower - 1e-9
