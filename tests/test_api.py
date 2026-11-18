"""The endpoint, GET /api/v1/route/: cases EP-01 to EP-40 and S04 of docs/test-cases.md.

The Django test client calls the real address, and PostgreSQL holds the stations each case
creates. The routing call is always replaced: by a fake fetch_route for most cases, and by
a fake transport under the real fetch_route where the retry between the two servers
matters (EP-08, EP-24, EP-28 to EP-30, S04).
"""

import json
import logging
import math
import time
import types
from decimal import ROUND_HALF_UP, Decimal
from io import StringIO

import httpx
import numpy as np
import pytest
from django.core.cache import cache
from django.core.cache.backends import locmem
from django.core.management import call_command
from django.test import RequestFactory
from django.urls import get_resolver

from stations.index import reset_index
from stations.models import FuelStation
from stations.places import Place
from tests.conftest import METRES_PER_MILE, SMALL_CSV, load_road
from tests.test_routing import Fake, slow, timeout
from trips import errors
from trips.services import planner, routing
from trips.services.routing import Route

pytestmark = pytest.mark.django_db

URL = "/api/v1/route/"
TRIP = {"start": "Dallas, TX", "finish": "Houston, TX"}
DALLAS = (32.790439, -96.80439)
SERVER_1 = "router.project-osrm.org"
SERVER_2 = "routing.openstreetmap.de"

# The test road (docs/test-cases.md, section 2.1) runs east along latitude 35 N from
# longitude 110 W. On a sphere of radius 3,958.8 miles a degree of longitude on the equator
# is 69.094094 miles; along 35 N it is that times cos(35 degrees).
ROAD_LAT = 35.0
ROAD_START_LNG = -110.0
MILES_PER_DEGREE = 69.094094 * math.cos(math.radians(ROAD_LAT))

# The architecture's error table (section 11): each code's status, and its details' keys.
STATUS_FOR_CODE = {
    "invalid_request": 400,
    "unknown_place": 400,
    "not_found": 404,
    "method_not_allowed": 405,
    "outside_coverage": 422,
    "route_leaves_usa": 422,
    "no_route": 422,
    "no_fuel_plan": 422,
    "rate_limited": 429,
    "internal_error": 500,
    "routing_unavailable": 502,
    "stations_not_loaded": 503,
}
DETAILS_FOR_CODE = {
    "invalid_request": {"fields"},
    "unknown_place": {"field", "query", "suggestions"},
    "not_found": set(),
    "method_not_allowed": set(),
    "outside_coverage": {"field", "query"},
    "route_leaves_usa": {"miles_abroad"},
    "no_route": set(),
    "no_fuel_plan": {"gap_start_mile", "gap_miles"},
    "rate_limited": {"retry_after_seconds"},
    "internal_error": set(),
    "routing_unavailable": {"reason"},
    "stations_not_loaded": set(),
}

CENT = Decimal("0.01")
# Rule R2 allows 0.05 gallons for rounding.
TANK_SLACK = Decimal("0.05")


# --- Test data -----------------------------------------------------------------------


def straight_road(miles: float) -> tuple[np.ndarray, float]:
    """The test road of `miles` miles as (coords, miles); coords are [lng, lat] rows, one
    every half mile, so the road is as dense as a real one."""
    marks = np.append(np.arange(0.0, miles, 0.5), miles)
    coords = np.column_stack(
        [ROAD_START_LNG + marks / MILES_PER_DEGREE, np.full(len(marks), ROAD_LAT)]
    )
    return coords, miles


def on_road(mile: float) -> tuple[float, float]:
    """(lat, lng) of the point `mile` miles along the test road."""
    return ROAD_LAT, ROAD_START_LNG + mile / MILES_PER_DEGREE


def add_station(opis_id: int, price: str, lat: float, lng: float, name: str = "") -> None:
    """Save one station at (lat, lng)."""
    FuelStation.objects.create(
        opis_id=opis_id,
        name=name or f"STATION {opis_id}",
        address=f"EXIT {opis_id}",
        city="Testville",
        state="TX",
        rack_id=1,
        price=Decimal(price),
        lat=lat,
        lng=lng,
    )


def road_answer(miles: float) -> httpx.Response:
    """The test road as the routing service sends it."""
    coords, _ = straight_road(miles)
    route = {
        "distance": miles * METRES_PER_MILE,
        "geometry": {"type": "LineString", "coordinates": coords.tolist()},
    }
    return httpx.Response(200, json={"code": "Ok", "routes": [route]})


class FakeRouting:
    """Stands in for routing.fetch_route: always returns one road, and counts the calls."""

    def __init__(self, coords: np.ndarray, miles: float):
        self.route = Route(coords=coords, distance_miles=miles, server=SERVER_1, calls=1)
        self.calls = 0

    def __call__(self, start: tuple[float, float], finish: tuple[float, float]) -> Route:
        self.calls += 1
        return self.route


@pytest.fixture(autouse=True)
def _fresh_index():
    """The station index is remembered per process; each case reads its own stations."""
    reset_index()
    yield
    reset_index()


@pytest.fixture
def use_road(monkeypatch):
    """use_road(coords, miles): the fake routing service returns that road from now on."""

    def use(coords: np.ndarray, miles: float) -> FakeRouting:
        fake = FakeRouting(coords, miles)
        monkeypatch.setattr(routing, "fetch_route", fake)
        return fake

    return use


@pytest.fixture
def use_servers(monkeypatch):
    """use_servers(fake): the real fetch_route sends its requests to `fake`, a Fake from
    tests/test_routing.py, so the retry between the two servers really runs."""
    clients = []

    def use(fake: Fake) -> Fake:
        clients.append(fake.client())
        monkeypatch.setattr(routing, "_shared_client", clients[-1])
        return fake

    yield use
    for client in clients:
        client.close()


@pytest.fixture
def ep01_stations() -> None:
    """EP-01's stations: the start station at Dallas (3.20), and three on the test road."""
    add_station(1, "3.20", *DALLAS, name="DALLAS START")
    for opis_id, mile, price in ((2, 200, "3.10"), (3, 450, "3.00"), (4, 700, "3.20")):
        add_station(opis_id, price, *on_road(mile))


@pytest.fixture
def ep01(ep01_stations, use_road) -> FakeRouting:
    """EP-01's world: its stations, and a 990-mile test road from the fake routing service."""
    return use_road(*straight_road(990.0))


# --- Reading responses ---------------------------------------------------------------


def read(response) -> dict:
    """The body as a client reads it, numbers as exact decimals."""
    return json.loads(response.content, parse_float=Decimal)


def without_meta(body: dict) -> dict:
    """The body as it is cached: everything but `meta`."""
    return {key: value for key, value in body.items() if key != "meta"}


def assert_error(response, code: str) -> dict:
    """EP-39: the standard error body, the status its code maps to, and the details' keys
    for that code. Returns the details."""
    body = json.loads(response.content)
    assert response.status_code == STATUS_FOR_CODE[code], body
    assert list(body) == ["error"]
    assert list(body["error"]) == ["code", "message", "details"]
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str)
    assert body["error"]["message"].strip()
    details = body["error"]["details"]
    assert isinstance(details, dict)
    assert set(details) == DETAILS_FOR_CODE[code]
    return details


def assert_sound(body: dict) -> None:
    """The correctness rules (docs/test-cases.md, section 4) these cases lean on: R1 range,
    R2 tank, R3 gallons, R4 money, R6 stops, R7 lowest bill, R8 stop count, R15 meta.
    The independent verifier of the next phase checks all sixteen."""
    summary, stops, meta = body["summary"], body["fuel_stops"], body["meta"]
    distance = summary["distance_miles"]
    marks = [stop["mile_marker"] for stop in stops]

    assert all(b - a <= 500 for a, b in zip(marks, [*marks[1:], distance], strict=True))  # R1

    tank, at = Decimal(0), Decimal(0)  # R2
    for stop in stops:
        tank -= (stop["mile_marker"] - at) / 10
        at = stop["mile_marker"]
        assert tank >= -TANK_SLACK
        tank += stop["gallons"]
        assert tank <= 50 + TANK_SLACK
    assert tank - (distance - at) / 10 >= -TANK_SLACK

    assert sum(stop["gallons"] for stop in stops) == summary["gallons"] == distance / 10  # R3

    for stop in stops:  # R4
        exact = stop["gallons"] * stop["price_per_gallon"]
        assert stop["cost"] == exact.quantize(CENT, rounding=ROUND_HALF_UP)
    assert summary["total_fuel_cost"] == sum(stop["cost"] for stop in stops)

    first = stops[0]  # R6
    assert (first["kind"], first["mile_marker"]) == ("start", 0)
    assert (first["lat"], first["lng"]) == (summary["start"]["lat"], summary["start"]["lng"])
    assert all(stop["kind"] == "station" for stop in stops[1:])
    assert [stop["order"] for stop in stops] == list(range(1, len(stops) + 1))
    assert all(a < b for a, b in zip(marks, [*marks[1:], distance], strict=True))
    assert len({stop["station_id"] for stop in stops}) == len(stops)

    assert summary["lowest_possible_fuel_cost"] <= summary["total_fuel_cost"]  # R7
    assert summary["lowest_possible_stops"] >= 1
    if body["assumptions"]["stop_cost"] == 0:
        assert summary["lowest_possible_fuel_cost"] == summary["total_fuel_cost"]

    assert summary["stops"] == len(stops) >= math.ceil(distance / 500)  # R8

    assert meta["routing_calls"] in (0, 1, 2)  # R15
    assert not meta["cache_hit"] or meta["routing_calls"] == 0
    timings = meta["timings_ms"]
    assert min(timings["routing"], timings["own"], timings["total"]) >= 0
    assert meta["routing_calls"] > 0 or timings["routing"] == 0
    assert meta["routing_server"] in (SERVER_1, SERVER_2)


def plan(client, **params) -> dict:
    """GET the route with EP-01's request plus `params`; expect a sound 200 and return it."""
    response = client.get(URL, TRIP | params)
    assert response.status_code == 200, response.content
    body = read(response)
    assert_sound(body)
    return body


# --- EP-01 to EP-08: plans and caches ------------------------------------------------


def test_ep01_plan_on_the_test_road(client, ep01):
    body = plan(client)
    summary, stops, meta = body["summary"], body["fuel_stops"], body["meta"]

    assert list(body) == ["summary", "warnings", "assumptions", "fuel_stops", "map", "meta"]
    assert [stop["kind"] for stop in stops] == ["start", "station", "station"]
    assert [stop["station_id"] for stop in stops] == [1, 3, 4]
    assert [stop["mile_marker"] for stop in stops] == [0, 450, 700]
    for stop, gallons in zip(stops, (45, 50, 4), strict=True):
        assert abs(stop["gallons"] - gallons) <= Decimal("0.05")
    assert abs(summary["total_fuel_cost"] - Decimal("306.80")) <= Decimal("0.20")
    assert summary["distance_miles"] == Decimal("990.0")
    assert summary["gallons"] == Decimal("99.00")
    assert summary["first_fill_distance_miles"] == 0
    assert body["warnings"] == []
    assert (meta["routing_calls"], meta["cache_hit"]) == (1, False)
    assert meta["routing_server"] == SERVER_1
    assert ep01.calls == 1


def test_ep02_repeat_comes_from_the_answer_cache(client, ep01):
    first = plan(client)
    second = plan(client)

    assert (second["meta"]["routing_calls"], second["meta"]["cache_hit"]) == (0, True)
    assert second["meta"]["routing_server"] == SERVER_1
    assert without_meta(second) == without_meta(first)
    assert ep01.calls == 1


def test_ep03_new_stop_cost_reuses_the_road(client, ep01):
    plan(client)
    body = plan(client, stop_cost="0")
    summary = body["summary"]

    assert (body["meta"]["routing_calls"], body["meta"]["cache_hit"]) == (0, False)
    assert body["assumptions"]["stop_cost"] == 0
    assert summary["stops"] == 4
    assert abs(summary["total_fuel_cost"] - Decimal("304.30")) <= Decimal("0.20")
    assert summary["total_fuel_cost"] == summary["lowest_possible_fuel_cost"]
    assert ep01.calls == 1


def test_ep04_stop_cost_is_keyed_to_two_decimals(client, ep01):
    seen = []
    for stop_cost in (None, "10", "10.00", "10.5", "10.50"):
        params = {} if stop_cost is None else {"stop_cost": stop_cost}
        meta = plan(client, **params)["meta"]
        seen.append((meta["cache_hit"], meta["routing_calls"]))

    assert seen == [(False, 1), (True, 0), (True, 0), (False, 0), (True, 0)]


def test_ep05_other_spellings_of_the_same_trip_hit_the_cache(client, ep01):
    plan(client)
    body = plan(client, start="dallas tx", finish="houston, texas")

    assert body["meta"]["cache_hit"] is True
    assert body["summary"]["start"]["label"] == "Dallas, TX"
    assert body["summary"]["finish"]["label"] == "Houston, TX"


def test_ep06_the_reverse_trip_is_another_trip(client, ep01):
    plan(client)
    meta = plan(client, start="Houston, TX", finish="Dallas, TX")["meta"]

    assert (meta["routing_calls"], meta["cache_hit"]) == (1, False)
    assert ep01.calls == 2


def move_clock(monkeypatch, seconds: float) -> None:
    """Make the in-memory cache see the clock `seconds` ahead. It checks expiry with
    time.time() from its own module, so only that reference is replaced."""
    real_time = time.time
    monkeypatch.setattr(locmem, "time", types.SimpleNamespace(time=lambda: real_time() + seconds))


def test_ep07_cached_trips_last_24_hours(client, ep01, monkeypatch):
    plan(client)

    move_clock(monkeypatch, 23 * 3600 + 59 * 60)
    assert plan(client)["meta"]["cache_hit"] is True

    move_clock(monkeypatch, 24 * 3600 + 1)
    meta = plan(client)["meta"]
    assert (meta["routing_calls"], meta["cache_hit"]) == (1, False)
    assert ep01.calls == 2


def test_ep08_errors_are_not_cached(client, ep01_stations, use_servers):
    use_servers(Fake(httpx.Response(500), httpx.Response(500)))
    assert_error(client.get(URL, TRIP), "routing_unavailable")

    use_servers(Fake(road_answer(990.0)))
    meta = plan(client)["meta"]
    assert (meta["routing_calls"], meta["cache_hit"]) == (1, False)


# --- EP-09 to EP-14: the parameters ----------------------------------------------------


def test_ep09_finish_missing(client, ep01):
    details = assert_error(client.get(URL, {"start": "Dallas, TX"}), "invalid_request")

    assert "finish" in details["fields"]
    assert ep01.calls == 0


@pytest.mark.parametrize("start", ["", "   "])
def test_ep10_start_empty_or_blank(client, ep01, start):
    response = client.get(URL, {"start": start, "finish": "Houston, TX"})

    assert "start" in assert_error(response, "invalid_request")["fields"]
    assert ep01.calls == 0


def test_ep11_no_parameters(client, ep01):
    details = assert_error(client.get(URL), "invalid_request")

    assert {"start", "finish"} <= set(details["fields"])
    assert all(isinstance(m, str) for messages in details["fields"].values() for m in messages)
    assert ep01.calls == 0


@pytest.mark.parametrize(
    ("stop_cost", "shown"), [("0", "0.0"), ("0.01", "0.01"), ("99.99", "99.99"), ("100", "100.0")]
)
def test_ep12_stop_cost_limits_are_allowed(client, ep01, stop_cost, shown):
    response = client.get(URL, TRIP | {"stop_cost": stop_cost})

    assert response.status_code == 200
    assert_sound(read(response))
    # A JSON float, so 0 is written 0.0 and 100 is written 100.0.
    assert repr(json.loads(response.content)["assumptions"]["stop_cost"]) == shown


@pytest.mark.parametrize("stop_cost", ["-0.01", "100.01", "10.555", "abc", "nan", "inf", ""])
def test_ep13_bad_stop_cost(client, ep01, stop_cost):
    details = assert_error(client.get(URL, TRIP | {"stop_cost": stop_cost}), "invalid_request")

    assert "stop_cost" in details["fields"]
    assert ep01.calls == 0


def test_ep14_unknown_parameters_are_ignored(client, ep01):
    with_units = plan(client, units="km")
    assert with_units["meta"]["cache_hit"] is False

    cache.clear()
    assert without_meta(plan(client)) == without_meta(with_units)


# --- EP-15 to EP-20: places ------------------------------------------------------------


def test_ep15_unknown_start(client, ep01):
    response = client.get(URL, {"start": "Chicgo, IL", "finish": "Houston, TX"})
    details = assert_error(response, "unknown_place")

    assert (details["field"], details["query"]) == ("start", "Chicgo, IL")
    assert "Chicago, IL" in details["suggestions"]
    assert ep01.calls == 0


def test_ep16_both_unknown_names_the_start(client, ep01):
    response = client.get(URL, {"start": "Chicgo, IL", "finish": "Nowhere, ZZ"})

    assert assert_error(response, "unknown_place")["field"] == "start"
    assert ep01.calls == 0


def test_ep17_unknown_finish(client, ep01):
    response = client.get(URL, {"start": "Dallas, TX", "finish": "Houstn, TX"})
    details = assert_error(response, "unknown_place")

    assert details["field"] == "finish"
    assert "Houston, TX" in details["suggestions"]
    assert ep01.calls == 0


@pytest.mark.parametrize(
    ("params", "field", "query"),
    [
        ({"start": "Honolulu, HI", "finish": "Houston, TX"}, "start", "Honolulu, HI"),
        ({"start": "Dallas, TX", "finish": "Anchorage, AK"}, "finish", "Anchorage, AK"),
    ],
)
def test_ep18_outside_coverage(client, ep01, params, field, query):
    details = assert_error(client.get(URL, params), "outside_coverage")

    assert details == {"field": field, "query": query}
    assert ep01.calls == 0


def test_ep19_same_place(client, ep01):
    response = client.get(URL, {"start": "Dallas, TX", "finish": "dallas texas"})

    assert "finish" in assert_error(response, "invalid_request")["fields"]
    assert ep01.calls == 0


def test_ep20_a_road_under_half_a_mile_is_the_same_place(client, ep01_stations, use_road):
    fake = use_road(*straight_road(0.4))
    response = client.get(URL, {"start": "Dallas, TX", "finish": "Fort Worth, TX"})

    assert "finish" in assert_error(response, "invalid_request")["fields"]
    assert fake.calls == 1


# --- EP-21 to EP-27: the road and the plan ---------------------------------------------


def test_ep21_detroit_to_buffalo_leaves_the_usa(client, ep01_stations, use_road):
    use_road(*load_road("det_buf"))
    response = client.get(URL, {"start": "Detroit, MI", "finish": "Buffalo, NY"})

    details = assert_error(response, "route_leaves_usa")

    assert details["miles_abroad"] == pytest.approx(252, rel=0.02)


def test_ep22_border_limit_is_25_miles(client, ep01, monkeypatch):
    monkeypatch.setattr(planner, "longest_run_abroad", lambda road, borders: 25.0)
    plan(client)

    # The road that passed is cached and would skip the check, so start afresh.
    cache.clear()
    monkeypatch.setattr(planner, "longest_run_abroad", lambda road, borders: 25.1)
    details = assert_error(client.get(URL, TRIP), "route_leaves_usa")
    assert details == {"miles_abroad": 25.1}


def test_ep23_border_is_checked_before_the_fuel_plan(client, ep01_stations, use_road):
    coords, miles = load_road("det_bos")
    assert round(miles, 1) == 706.5
    use_road(coords, miles)
    response = client.get(URL, {"start": "Detroit, MI", "finish": "Boston, MA"})

    assert_error(response, "route_leaves_usa")


def test_ep24_no_road_between_the_points(client, ep01_stations, use_servers):
    fake = use_servers(Fake(httpx.Response(400, json={"code": "NoRoute"}), None))

    assert_error(client.get(URL, TRIP), "no_route")
    assert len(fake.requests) == 1


def test_ep25_no_station_for_more_than_500_miles(client, use_road):
    add_station(1, "3.20", *DALLAS)
    add_station(2, "3.00", *on_road(503))
    use_road(*straight_road(990.0))
    details = assert_error(client.get(URL, TRIP), "no_fuel_plan")

    # Rounded to 0.1 mile; the exact gap on this road is 502.99999...
    assert details == {"gap_start_mile": 0.0, "gap_miles": 503.0}


def test_ep26_full_list_is_used_when_the_thinned_list_has_no_plan(client, use_road):
    add_station(1, "3.20", *DALLAS)
    add_station(2, "3.10", *on_road(495))
    add_station(3, "3.00", *on_road(503))
    use_road(*straight_road(990.0))
    body = plan(client)

    assert [stop["station_id"] for stop in body["fuel_stops"]] == [1, 2]
    assert abs(body["summary"]["total_fuel_cost"] - Decimal("311.85")) <= Decimal("0.20")


def test_ep27_stop_cost_zero_keeps_stations_thinning_would_drop(client, use_road):
    add_station(1, "4.00", *DALLAS)
    road_stations = ((2, 100, "3.00"), (3, 105, "3.01"), (4, 400, "3.50"), (5, 650, "2.50"))
    for opis_id, mile, price in road_stations:
        add_station(opis_id, price, *on_road(mile))
    use_road(*straight_road(900.0))
    summary = plan(client, stop_cost="0")["summary"]

    assert summary["total_fuel_cost"] == summary["lowest_possible_fuel_cost"]
    # Skipping the mile-105 station would cost about 270.00.
    assert abs(summary["total_fuel_cost"] - Decimal("269.76")) <= Decimal("0.05")


# --- EP-28 to EP-30: the two routing servers --------------------------------------------


def test_ep28_both_servers_fail(client, ep01_stations, use_servers):
    fake = use_servers(Fake(httpx.Response(500), httpx.Response(500)))

    assert assert_error(client.get(URL, TRIP), "routing_unavailable") == {"reason": "error"}
    assert len(fake.requests) == 2


def test_ep29_both_servers_time_out(client, ep01_stations, use_servers):
    fake = use_servers(Fake(timeout, timeout))

    assert assert_error(client.get(URL, TRIP), "routing_unavailable") == {"reason": "timeout"}
    assert len(fake.requests) == 2


def test_ep30_second_server_answers(client, ep01_stations, use_servers):
    use_servers(Fake(httpx.Response(503), road_answer(990.0)))
    meta = plan(client)["meta"]

    assert meta["routing_calls"] == 2
    assert meta["routing_server"] == SERVER_2


# --- EP-31 to EP-40: stations, failures, limits, addresses, timings ----------------------


def test_ep31_stations_not_loaded_then_loaded_without_a_restart(client, use_road):
    fake = use_road(*straight_road(238.0))
    assert_error(client.get(URL, TRIP), "stations_not_loaded")
    assert fake.calls == 0

    call_command("load_stations", "--csv", str(SMALL_CSV), stdout=StringIO())
    stops = plan(client)["fuel_stops"]
    assert len(stops) == 1
    assert (stops[0]["station_id"], stops[0]["price_per_gallon"]) == (1, Decimal("3.4"))


def test_ep32_places_are_checked_before_stations(client):
    response = client.get(URL, {"start": "Chicgo, IL", "finish": "Houston, TX"})

    assert_error(response, "unknown_place")


@pytest.mark.parametrize("debug", [False, True])
def test_ep33_unexpected_failure(client, ep01_stations, monkeypatch, settings, caplog, debug):
    settings.DEBUG = debug

    def fail(start, finish):
        raise RuntimeError("boom")

    monkeypatch.setattr(routing, "fetch_route", fail)
    with caplog.at_level(logging.ERROR):
        response = client.get(URL, TRIP)

    assert_error(response, "internal_error")
    assert b"boom" not in response.content
    assert b"Traceback" not in response.content
    # The failure is logged in full, traceback included.
    [record] = [r for r in caplog.records if r.exc_info]
    assert isinstance(record.exc_info[1], RuntimeError)


def test_ep34_rate_limit(client, ep01):
    statuses = [client.get(URL, TRIP).status_code for _ in range(60)]
    assert 429 not in statuses

    response = client.get(URL, TRIP)
    details = assert_error(response, "rate_limited")
    assert details["retry_after_seconds"] > 0
    assert response["Retry-After"] == str(details["retry_after_seconds"])


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_ep35_only_get(client, ep01, method):
    response = getattr(client, method)(f"{URL}?start=Dallas, TX&finish=Houston, TX")

    assert assert_error(response, "method_not_allowed") == {}


@pytest.mark.parametrize("debug", [False, True])
@pytest.mark.parametrize("path", ["/api/v1/routes/", "/api/v2/route/"])
def test_ep36_unknown_address(client, settings, debug, path):
    settings.DEBUG = debug

    assert assert_error(client.get(path), "not_found") == {}


def test_ep37_first_fill_station_far_from_the_start(client, use_road):
    # 30 miles due north of Dallas: a degree of latitude is 69.094094 miles.
    add_station(1, "3.20", DALLAS[0] + 30 / 69.094094, DALLAS[1], name="NORTH STAR")
    for opis_id, mile, price in ((2, 200, "3.10"), (3, 450, "3.00"), (4, 700, "3.20")):
        add_station(opis_id, price, *on_road(mile))
    use_road(*straight_road(990.0))
    body = plan(client)

    assert body["summary"]["first_fill_distance_miles"] == Decimal("30.0")
    [warning] = body["warnings"]
    assert "NORTH STAR" in warning
    assert "30.0" in warning


def test_ep38_tied_start_stations(client, use_road):
    add_station(20, "3.30", *DALLAS)
    add_station(30, "3.25", *DALLAS)
    for opis_id, mile, price in ((2, 200, "3.10"), (3, 450, "3.00"), (4, 700, "3.20")):
        add_station(opis_id, price, *on_road(mile))
    use_road(*straight_road(990.0))

    first = plan(client)["fuel_stops"][0]
    assert (first["station_id"], first["price_per_gallon"]) == (30, Decimal("3.25"))

    FuelStation.objects.filter(opis_id=20).update(price=Decimal("3.25"))
    reset_index()
    cache.clear()
    assert plan(client)["fuel_stops"][0]["station_id"] == 20


def test_ep39_error_table_matches_the_architecture():
    """Every error test above checks its body with assert_error; this checks the table."""
    assert errors.STATUS_FOR_CODE == STATUS_FOR_CODE


def test_ep40_timings(client, ep01):
    first = plan(client)["meta"]["timings_ms"]
    assert list(first) == ["routing", "own", "total"]
    assert min(first.values()) >= 0

    meta = plan(client)["meta"]
    assert (meta["routing_calls"], meta["cache_hit"]) == (0, True)
    assert meta["timings_ms"]["routing"] == 0


# --- S04 and the brief's own requirements ----------------------------------------------


def test_s04_both_servers_too_slow(client, ep01_stations, use_servers, settings):
    """S04 with the deadline shortened from 5 s to 0.2 s, so the test takes under a second."""
    settings.ROUTING_DEADLINE_SECONDS = 0.2
    fake = use_servers(Fake(slow, slow))

    started = time.monotonic()
    response = client.get(URL, TRIP)
    elapsed = time.monotonic() - started

    assert assert_error(response, "routing_unavailable") == {"reason": "timeout"}
    assert len(fake.requests) == 2
    assert elapsed < 1.0


def test_a_road_that_leaves_the_usa_is_not_cached(client, ep01_stations, use_road):
    fake = use_road(*load_road("det_buf"))
    detroit_to_buffalo = {"start": "Detroit, MI", "finish": "Buffalo, NY"}
    for _ in range(2):
        assert_error(client.get(URL, detroit_to_buffalo), "route_leaves_usa")

    assert fake.calls == 2


def test_routing_server_is_remembered_with_the_road_and_the_answer(
    client, ep01_stations, use_servers
):
    use_servers(Fake(httpx.Response(503), road_answer(990.0)))
    plan(client)

    road_cached = plan(client, stop_cost="0")["meta"]
    answer_cached = plan(client, stop_cost="0")["meta"]
    assert (road_cached["cache_hit"], road_cached["routing_server"]) == (False, SERVER_2)
    assert (answer_cached["cache_hit"], answer_cached["routing_server"]) == (True, SERVER_2)


def test_any_accept_header_gets_json(client, ep01):
    html_only = {"Accept": "text/html"}

    response = client.get(URL, TRIP, headers=html_only)
    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    assert_sound(read(response))

    assert_error(client.get(URL, {"start": "Dallas, TX"}, headers=html_only), "invalid_request")


def test_places_sharing_coordinates_keep_their_own_labels(client, ep01, monkeypatch):
    real_resolve = planner.resolve
    dallas = real_resolve("Dallas, TX", "start")
    twins = {name: Place(name, dallas.lat, dallas.lng) for name in ("Alpha, TX", "Beta, TX")}
    monkeypatch.setattr(
        planner, "resolve", lambda text, field: twins.get(text) or real_resolve(text, field)
    )

    alpha = plan(client, start="Alpha, TX")
    beta = plan(client, start="Beta, TX")

    assert alpha["summary"]["start"]["label"] == "Alpha, TX"
    assert beta["summary"]["start"]["label"] == "Beta, TX"
    assert beta["map"]["features"][-2]["properties"]["title"] == "Start: Beta, TX"
    # A different answer, on the same road: the road cache is keyed by coordinates only.
    assert (beta["meta"]["cache_hit"], beta["meta"]["routing_calls"]) == (False, 0)


def test_stop_cost_minus_zero_is_zero(client, ep01):
    response = client.get(URL, TRIP | {"stop_cost": "-0"})
    assert repr(json.loads(response.content)["assumptions"]["stop_cost"]) == "0.0"

    cache.clear()
    plan(client, stop_cost="0")
    assert plan(client, stop_cost="-0")["meta"]["cache_hit"] is True


def test_trailing_slash_is_optional(client, ep01):
    response = client.get(URL.rstrip("/"), TRIP)

    assert response.status_code == 200
    assert_sound(read(response))


def test_handler500_answers_in_the_standard_body():
    """Failures outside the REST framework reach Django's handler500 (when DEBUG is off)."""
    handler = get_resolver().resolve_error_handler(500)

    assert_error(handler(RequestFactory().get(URL)), "internal_error")
