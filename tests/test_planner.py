"""plan_trip() on the real stations and recorded roads: the checks on real data in brief 4E,
and warm_up(), which loads at start-up what the first request would otherwise wait for.

The routing call is replaced by a fake that returns a recorded road. The checks on real
data hold the real CSV's stations in memory (no database); each is the offline twin of a
live case in docs/test-cases.md, named in its docstring. The warm-up tests read the
stations from PostgreSQL, as a starting server does.
"""

import json
import logging
import math
from decimal import Decimal
from io import StringIO
from itertools import pairwise

import pytest
from django.core.management import call_command
from django.db import OperationalError

from stations import places
from stations.index import reset_index
from tests.conftest import load_road
from trips.exceptions import RouteLeavesUSA
from trips.services import planner, routing
from trips.services.planner import plan_trip, warm_up
from trips.services.routing import Route

DEFAULT_STOP_COST = Decimal("10")


@pytest.fixture(autouse=True)
def _fresh_index():
    """The station index is remembered per process; no test may leave one behind."""
    reset_index()
    yield
    reset_index()


@pytest.fixture
def recorded_road(monkeypatch):
    """recorded_road(name): the fake routing service returns that recorded road."""

    def use(name: str) -> None:
        coords, miles = load_road(name)
        route = Route(
            coords=coords, distance_miles=miles, server="router.project-osrm.org", calls=1
        )
        monkeypatch.setattr(routing, "fetch_route", lambda start, finish: route)

    return use


def trip(start: str, finish: str, stop_cost: Decimal = DEFAULT_STOP_COST) -> dict:
    """plan_trip's body as a client reads it: through JSON, numbers as exact decimals."""
    return json.loads(json.dumps(plan_trip(start, finish, stop_cost)), parse_float=Decimal)


def assert_valid_plan(body: dict) -> None:
    """A plan a truck can follow, whose figures add up."""
    summary, stops = body["summary"], body["fuel_stops"]
    marks = [stop["mile_marker"] for stop in stops] + [summary["distance_miles"]]

    assert all(b - a <= 500 for a, b in pairwise(marks))
    assert sum(stop["gallons"] for stop in stops) == summary["gallons"]
    assert summary["gallons"] == summary["distance_miles"] / 10
    assert summary["total_fuel_cost"] == sum(stop["cost"] for stop in stops)
    assert summary["lowest_possible_fuel_cost"] <= summary["total_fuel_cost"]
    assert (stops[0]["kind"], stops[0]["mile_marker"]) == ("start", 0)
    assert len({stop["station_id"] for stop in stops}) == len(stops)
    assert summary["stops"] == len(stops) >= math.ceil(summary["distance_miles"] / 500)


# --- Checks on real data ---------------------------------------------------------------


def test_new_york_to_los_angeles(recorded_road, use_real_stations):
    """Offline twin of P01."""
    recorded_road("nyc_la")
    body = trip("New York, NY", "Los Angeles, CA")

    assert_valid_plan(body)
    assert body["summary"]["stops"] < 10


def test_new_york_to_los_angeles_with_free_stops(recorded_road, use_real_stations):
    """Offline twin of P03: stop cost 0 buys the lowest possible bill, with more stops."""
    recorded_road("nyc_la")
    default = trip("New York, NY", "Los Angeles, CA")
    free = trip("New York, NY", "Los Angeles, CA", Decimal("0"))

    assert_valid_plan(free)
    assert free["summary"]["total_fuel_cost"] == free["summary"]["lowest_possible_fuel_cost"]
    assert free["summary"]["stops"] > default["summary"]["stops"]


def test_dallas_to_houston(recorded_road, use_real_stations):
    """Offline twin of P08: a trip under 500 miles still has a plan that costs something."""
    recorded_road("dal_hou")
    body = trip("Dallas, TX", "Houston, TX")

    assert_valid_plan(body)
    assert body["summary"]["total_fuel_cost"] > 0


def test_detroit_to_buffalo_leaves_the_usa(recorded_road, use_real_stations):
    """Offline twin of N11."""
    recorded_road("det_buf")

    with pytest.raises(RouteLeavesUSA) as caught:
        plan_trip("Detroit, MI", "Buffalo, NY", DEFAULT_STOP_COST)
    assert caught.value.details["miles_abroad"] == pytest.approx(252, rel=0.02)


def test_seattle_to_miami(recorded_road, use_real_stations):
    """Offline twin of P06."""
    recorded_road("sea_mia")
    body = trip("Seattle, WA", "Miami, FL")

    assert_valid_plan(body)
    assert body["summary"]["stops"] < 12


# --- warm_up() -------------------------------------------------------------------------


def start_afresh() -> None:
    """Forget what a running process keeps in memory, as if it had just started: the
    places table, the border outlines and the station index."""
    places.use_cities_file(None)
    planner._borders.cache_clear()
    reset_index()


@pytest.mark.django_db
def test_warm_up_leaves_nothing_for_the_first_request(recorded_road, django_assert_num_queries):
    call_command("load_stations", stdout=StringIO())
    start_afresh()
    warm_up()

    recorded_road("nyc_la")
    # The stations were read by warm_up(), so the first trip makes no query.
    with django_assert_num_queries(0):
        body = plan_trip("New York, NY", "Los Angeles, CA", DEFAULT_STOP_COST)
    assert body["meta"]["timings_ms"]["own"] <= 100


def warm_up_log(caplog) -> list[str]:
    """Run warm_up() from a fresh start; return what it logged."""
    start_afresh()
    with caplog.at_level(logging.INFO, logger=planner.__name__):
        warm_up()
    return [r.getMessage() for r in caplog.records if r.name == planner.__name__]


@pytest.mark.django_db
def test_warm_up_with_no_stations_loaded_raises_nothing(caplog):
    [line] = warm_up_log(caplog)

    assert "StationsNotLoaded" in line


def test_warm_up_with_no_database_raises_nothing(monkeypatch, caplog):
    def unreachable():
        raise OperationalError("connection refused")

    monkeypatch.setattr(planner, "get_index", unreachable)
    [line] = warm_up_log(caplog)

    assert "OperationalError" in line
