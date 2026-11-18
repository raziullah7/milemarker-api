"""The verifier itself: cases VF-01 to VF-19 of docs/test-cases.md, section 2.11, the
verifier's cases of section 9.13 (QB-01 to QB-03, QB-08 to QB-10) and its options, VR-01,
VR-03 and VR-04 of section 9.14.

Correct answers come from the real endpoint, through Django's test client, with the real
stations in memory and the routing call replaced by a recorded road. VF-02 to VF-18 then each
break one thing in a copy of a correct answer and expect the rule that guards it to be
reported. VF-02 shows the unbroken answer reports nothing, so a rule that always fired could
not pass these tests.

VF-01 asks that every 200 of the endpoint tests passes the verifier. tests/test_api.py checks
each of its 200s with it, against the invented stations each test creates. Here VF-01 adds a
spread of real trips: each recorded road with the real stations, every answer verified
against the real CSV.
"""

import ast
import copy
import json
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import numpy as np
import pytest

from stations.index import reset_index
from stations.models import FuelStation
from stations.places import HAND_ADDED_PLACES
from tests.conftest import load_road
from tests.test_api import DALLAS, add_station, listed_prices, on_road, straight_road
from tests.verify import Listing, load_prices, places_from, verify_response
from trips.services import routing
from trips.services.corridor import stations_along
from trips.services.geo import resample
from trips.services.routing import Route

ROOT = Path(__file__).resolve().parent.parent
REAL_CSV = ROOT / "data" / "fuel-prices-for-be-assessment.csv"
SMALL_CSV = ROOT / "tests" / "fixtures" / "stations_small.csv"
URL = "/api/v1/route/"
SERVER_1 = "router.project-osrm.org"


@pytest.fixture(scope="module")
def prices() -> dict[str, Listing]:
    return load_prices(REAL_CSV)


@pytest.fixture
def ask(client, use_real_stations, monkeypatch):
    """ask(road, start, finish, stop_cost=None): the endpoint's 200 for that trip on that
    recorded road, numbers read as exact decimals."""

    def ask(road: str, start: str, finish: str, stop_cost: str | None = None) -> dict:
        coords, miles = load_road(road)
        recorded = Route(coords=coords, distance_miles=miles, server=SERVER_1, calls=1)
        monkeypatch.setattr(routing, "fetch_route", lambda start, finish: recorded)
        params = {"start": start, "finish": finish}
        if stop_cost is not None:
            params["stop_cost"] = stop_cost
        response = client.get(URL, params)
        assert response.status_code == 200, response.content
        return json.loads(response.content, parse_float=Decimal)

    return ask


@pytest.fixture
def good(ask) -> dict:
    """A correct answer to break: New York to Los Angeles at the default stop cost. Seven
    stops or so, the first fill-up nearby, a fresh routing call: every rule has something
    to hold on to."""
    return ask("nyc_la", "New York, NY", "Los Angeles, CA")


def rules(body: dict, prices: dict, stop_cost=None, **options) -> tuple[set[str], list[str]]:
    """The IDs of the rules reported, and the lines themselves for the failure message."""
    lines = verify_response(body, prices, stop_cost, **options)
    return {line.split(":", 1)[0] for line in lines}, lines


def agree(body: dict) -> dict:
    """Make what follows from fuel_stops agree with it again, after a test has changed it:
    the orders, each cost, the total, the stop count, the lowest bill (never above the
    total) and the map's stop Points. A wrong answer built with it is then wrong only in
    what the test changed."""
    summary, stops = body["summary"], body["fuel_stops"]
    for order, stop in enumerate(stops, 1):
        stop["order"] = order
        exact = stop["gallons"] * stop["price_per_gallon"]
        stop["cost"] = exact.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    summary["total_fuel_cost"] = sum(stop["cost"] for stop in stops)
    summary["stops"] = len(stops)
    summary["lowest_possible_fuel_cost"] = min(
        summary["lowest_possible_fuel_cost"], summary["total_fuel_cost"]
    )

    features = body["map"]["features"]
    route, template, start, finish = features[0], features[1], features[-2], features[-1]
    points = []
    for stop in stops:
        point = copy.deepcopy(template)
        for key in ("order", "name", "mile_marker", "price_per_gallon", "gallons", "cost"):
            point["properties"][key] = stop[key]
        point["properties"]["title"] = (
            f"{stop['order']}. {stop['name']}, {stop['city']} {stop['state']}"
        )
        point["geometry"]["coordinates"] = [stop["lng"], stop["lat"]]
        points.append(point)
    body["map"]["features"] = [route, *points, start, finish]
    return body


# --- VF-01 -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("road", "start", "finish", "stop_cost"),
    [
        ("nyc_la", "New York, NY", "Los Angeles, CA", "10"),
        ("nyc_la", "New York, NY", "Los Angeles, CA", "0"),
        ("nyc_la", "New York, NY", "Los Angeles, CA", "25"),
        ("dal_hou", "Dallas, TX", "Houston, TX", None),
        ("sea_mia", "Seattle, WA", "Miami, FL", None),
        ("chi_hou", "Chicago, IL", "Houston, TX", None),
        ("bos_dc", "Boston, MA", "Washington, DC", None),
    ],
)
def test_vf01_real_trips_obey_every_rule(ask, prices, road, start, finish, stop_cost):
    body = ask(road, start, finish, stop_cost)

    assert verify_response(body, prices, stop_cost) == []


# The recorded roads that stay in the USA and have a fuel plan: GE-16's fifteen and three of
# the four added in Phase 10. The other three recordings give no 200: Detroit to Buffalo
# and to Boston run through Ontario, and Los Angeles to Seattle has no fuel plan.
ROADS_WITH_A_PLAN = {
    "bos_dc": ("Boston, MA", "Washington, DC"),
    "bos_sea": ("Boston, MA", "Seattle, WA"),
    "chi_hou": ("Chicago, IL", "Houston, TX"),
    "dal_hou": ("Dallas, TX", "Houston, TX"),
    "det_porthuron": ("Detroit, MI", "Port Huron, MI"),
    "elpaso_delrio": ("El Paso, TX", "Del Rio, TX"),
    "houlton_madawaska": ("Houlton, ME", "Madawaska, ME"),
    "intlfalls_baudette": ("International Falls, MN", "Baudette, MN"),
    "keywest_miami": ("Key West, FL", "Miami, FL"),
    "laredo_brownsville": ("Laredo, TX", "Brownsville, TX"),
    "montauk_nyc": ("Montauk, NY", "New York, NY"),
    "nyc_la": ("New York, NY", "Los Angeles, CA"),
    "sandiego_calexico": ("San Diego, CA", "Calexico, CA"),
    "sea_mia": ("Seattle, WA", "Miami, FL"),
    "sea_blaine": ("Seattle, WA", "Blaine, WA"),
    "la_nyc": ("Los Angeles, CA", "New York, NY"),
    "stl_winstonsalem": ("St. Louis, MO", "Winston-Salem, NC"),
    "dal_phx": ("Dallas, TX", "Phoenix, AZ"),
}


@pytest.mark.parametrize("stop_cost", ["0", "10", "25"])
@pytest.mark.parametrize("road", list(ROADS_WITH_A_PLAN))
def test_qb02_every_recorded_road_obeys_every_rule(ask, prices, road, stop_cost):
    """QB-02: the rules added after the second audit (R17, and the new R6 and R12) hold on
    every real answer the recordings give."""
    body = ask(road, *ROADS_WITH_A_PLAN[road], stop_cost)

    assert verify_response(body, prices, stop_cost) == []


# --- VF-02 to VF-18 ------------------------------------------------------------------------


def test_vf02_a_correct_answer_reports_nothing(good, prices):
    assert verify_response(good, prices) == []
    # The cases below need these to be true of the answer they break.
    assert len(good["fuel_stops"]) >= 3
    assert good["warnings"] == []


def test_vf03_a_stretch_over_500_miles(good, prices):
    bad = copy.deepcopy(good)
    stops = bad["fuel_stops"]
    stops[2]["mile_marker"] = stops[1]["mile_marker"] + Decimal("500.1")

    found, lines = rules(bad, prices)
    assert "R1" in found, lines


def test_vf04_the_tank_overflows(good, prices):
    bad = copy.deepcopy(good)
    stops = bad["fuel_stops"]
    extra = Decimal("55.00") - stops[0]["gallons"]
    stops[0]["gallons"] += extra
    stops[2]["gallons"] -= extra

    found, lines = rules(bad, prices)
    assert "R2" in found, lines


def test_r2_allows_nothing_for_rounding(good, prices):
    """The shown gallons are rounded as a running total (architecture section 8), so the
    walk is exact: a tank one hundredth of a gallon over its size is reported."""
    bad = copy.deepcopy(good)
    stops = bad["fuel_stops"]
    # Taken back at stop 2, so the tank is as before from there on: the only fault is
    # 50.01 gallons after stop 1.
    extra = Decimal("50.01") - stops[0]["gallons"]
    stops[0]["gallons"] += extra
    stops[1]["gallons"] -= extra

    found, lines = rules(bad, prices)
    assert "R2" in found, lines


def test_vf05_gallons_do_not_add_up(good, prices):
    bad = copy.deepcopy(good)
    bad["fuel_stops"][1]["gallons"] += Decimal("0.01")

    found, lines = rules(bad, prices)
    assert "R3" in found, lines


def test_vf06_total_is_not_the_sum_of_the_costs(good, prices):
    bad = copy.deepcopy(good)
    bad["summary"]["total_fuel_cost"] += Decimal("0.01")

    found, lines = rules(bad, prices)
    assert "R4" in found, lines


def test_vf07_a_price_that_is_not_the_csvs(good, prices):
    bad = copy.deepcopy(good)
    stop = bad["fuel_stops"][1]
    text = str(stop["price_per_gallon"])
    stop["price_per_gallon"] = Decimal(text[:-1] + str((int(text[-1]) + 1) % 10))

    found, lines = rules(bad, prices)
    assert "R5" in found, lines


def test_vf08_stops_out_of_order(good, prices):
    bad = copy.deepcopy(good)
    stops = bad["fuel_stops"]
    stops[1], stops[2] = stops[2], stops[1]

    found, lines = rules(bad, prices)
    assert "R6" in found, lines


def test_vf09_lowest_bill_above_the_plans(good, prices):
    bad = copy.deepcopy(good)
    summary = bad["summary"]
    summary["lowest_possible_fuel_cost"] = summary["total_fuel_cost"] + Decimal("0.01")

    found, lines = rules(bad, prices)
    assert "R7" in found, lines


def test_vf10_stop_count_disagrees_with_the_stops(good, prices):
    bad = copy.deepcopy(good)
    bad["summary"]["stops"] += 1

    found, lines = rules(bad, prices)
    assert "R8" in found, lines


def test_vf11_a_different_tank(good, prices):
    bad = copy.deepcopy(good)
    bad["assumptions"]["tank_gallons"] = 60

    found, lines = rules(bad, prices)
    assert "R9" in found, lines


def test_vf12_far_first_fill_without_a_warning(good, prices):
    bad = copy.deepcopy(good)
    bad["summary"]["first_fill_distance_miles"] = Decimal("30.0")

    found, lines = rules(bad, prices)
    assert "R10" in found, lines


def test_vf13_a_stop_missing_from_the_map(good, prices):
    bad = copy.deepcopy(good)
    features = bad["map"]["features"]
    assert features[2]["properties"]["kind"] == "stop"
    del features[2]

    found, lines = rules(bad, prices)
    assert "R11" in found, lines


def test_vf14_a_stop_off_the_route_line(good, prices):
    bad = copy.deepcopy(good)
    # Moved in both places, so the map still agrees with fuel_stops and only R12 can see it.
    bad["fuel_stops"][1]["lat"] += Decimal("0.001")
    point = bad["map"]["features"][2]
    assert point["properties"]["order"] == 2
    point["geometry"]["coordinates"][1] += Decimal("0.001")

    found, lines = rules(bad, prices)
    assert "R12" in found, lines


def test_vf15_a_hole_in_the_route_line(good, prices):
    bad = copy.deepcopy(good)
    line = bad["map"]["features"][0]["geometry"]["coordinates"]
    del line[len(line) // 2]

    found, lines = rules(bad, prices)
    assert "R13" in found, lines


FORT_WORTH = (32.7469, -97.3268)
MILES_PER_DEGREE_OF_LATITUDE = 69.094094  # on a sphere of radius 3,958.8 miles


def test_r13_a_correct_short_road_passes(client, use_real_stations, monkeypatch, prices):
    """R13 allows 1% or 1 point, whichever is larger. A correct line has a point every half
    mile plus the end point: 22 points for a 10.3-mile road, against 2 x 10.3 + 1 = 21.6.
    1% of that is 0.216 of a point, so only the 1-point allowance lets it pass."""
    # Due north from Fort Worth. Only the line's spacing matters here, not where it goes.
    marks = np.append(np.arange(0.0, 10.3, 0.5), 10.3)
    coords = np.column_stack(
        [np.full(len(marks), FORT_WORTH[1]), FORT_WORTH[0] + marks / MILES_PER_DEGREE_OF_LATITUDE]
    )
    road = Route(coords=coords, distance_miles=10.3, server=SERVER_1, calls=1)
    monkeypatch.setattr(routing, "fetch_route", lambda start, finish: road)
    response = client.get(URL, {"start": "Fort Worth, TX", "finish": "Dallas, TX"})
    assert response.status_code == 200, response.content
    body = json.loads(response.content, parse_float=Decimal)

    assert len(body["map"]["features"][0]["geometry"]["coordinates"]) == 22
    assert verify_response(body, prices) == []


def test_r13_a_long_road_missing_a_point_still_fails(good, prices):
    """On a long road one point fewer is well inside 1%, so the count cannot see it. The
    one-mile gap it leaves is what R13 reports (VF-15 removes the middle point)."""
    bad = copy.deepcopy(good)
    line = bad["map"]["features"][0]["geometry"]["coordinates"]
    del line[len(line) // 3]

    found, lines = rules(bad, prices)
    assert "R13" in found, lines
    [r13] = [line for line in lines if line.startswith("R13")]
    assert "gaps over 0.51 miles: 1," in r13
    assert "line points" not in r13


def test_vf16_a_cost_with_three_decimals(good, prices):
    bad = copy.deepcopy(good)
    bad["fuel_stops"][1]["cost"] = Decimal("12.345")

    found, lines = rules(bad, prices)
    assert "R14" in found, lines


def test_vf17_cache_hit_with_a_routing_call(good, prices):
    bad = copy.deepcopy(good)
    bad["meta"]["cache_hit"] = True
    bad["meta"]["routing_calls"] = 1

    found, lines = rules(bad, prices)
    assert "R15" in found, lines


def test_vf18_a_start_outside_the_lower_48(good, prices):
    bad = copy.deepcopy(good)
    bad["summary"]["start"]["label"] = "Toronto, ON"

    found, lines = rules(bad, prices)
    assert "R16" in found, lines


# --- QB-01 to QB-03, QB-08 to QB-10: the second audit's findings on the verifier ------------


def test_qb01_a_station_far_from_the_road(good, prices):
    """Review 9-Q0b, finding Q0b-1. Stop 3 is given the cheapest station in the CSV, 742
    miles away, while keeping its point on the line. Every figure is made to agree, and
    its bill is below the lowest possible, so only R17 can see it."""
    bad = copy.deepcopy(good)
    stop = bad["fuel_stops"][2]
    assert (stop["city"], stop["state"], stop["price_per_gallon"]) == (
        "Utica",
        "IL",
        Decimal("2.969"),
    )
    far = prices["66341"]
    assert (far.city, far.state, far.price) == ("Harrold", "TX", Decimal("2.68733333"))
    stop["station_id"] = 66341
    for key in ("name", "address", "city", "state"):
        stop[key] = getattr(far, key)
    stop["price_per_gallon"] = far.price
    agree(bad)
    assert bad["summary"]["total_fuel_cost"] < good["summary"]["lowest_possible_fuel_cost"]

    found, lines = rules(bad, prices)
    assert found == {"R17"}, lines


def test_qb03_a_stop_drawn_further_along_than_its_marker(good, prices):
    """Review 9-Q0b, finding Q0b-2. Stop 4 is drawn 17 line points, about 8.5 miles,
    further along the road, with its mile marker kept. The stretch to it is then longer
    than the markers say."""
    bad = copy.deepcopy(good)
    stop = bad["fuel_stops"][3]
    line = bad["map"]["features"][0]["geometry"]["coordinates"]
    at = line.index([stop["lng"], stop["lat"]])
    stop["lng"], stop["lat"] = line[at + 17]
    agree(bad)

    found, lines = rules(bad, prices)
    assert "R12" in found, lines


def test_qb08_a_stop_that_buys_nothing(good, prices, use_real_stations):
    """Review 9-Q0b, finding Q0b-5. A station along the road that the plan does not use is
    added between stops 2 and 3, at its own road point, buying 0.00 gallons. A purchase
    that rounds to 0.00 is not shown as a stop (architecture section 8)."""
    bad = copy.deepcopy(good)
    stops = bad["fuel_stops"]
    coords, miles = load_road("nyc_la")
    road = resample(coords, round(miles, 1))
    used = {stop["station_id"] for stop in stops}
    between = [
        c
        for c in stations_along(road, use_real_stations)
        if stops[1]["mile_marker"] + 100 < c.mile < stops[2]["mile_marker"] - 100
        and use_real_stations.info[c.station].opis_id not in used
    ]
    extra = between[0]
    listing = prices[str(use_real_stations.info[extra.station].opis_id)]
    lng, lat = bad["map"]["features"][0]["geometry"]["coordinates"][extra.point]
    stops.insert(
        2,
        {
            "order": 3,
            "kind": "station",
            "station_id": use_real_stations.info[extra.station].opis_id,
            "name": listing.name,
            "address": listing.address,
            "city": listing.city,
            "state": listing.state,
            "mile_marker": Decimal(str(round(extra.mile, 1))),
            "lat": lat,
            "lng": lng,
            "price_per_gallon": listing.price,
            "gallons": Decimal("0.00"),
            "cost": Decimal("0.00"),
        },
    )
    agree(bad)

    found, lines = rules(bad, prices)
    assert found == {"R6"}, lines


def test_qb09_a_stop_that_buys_less_than_nothing(good, prices):
    """Review 9-Q0b, finding Q0b-5. Stop 3 buys -0.01 gallons at -0.03, and stop 4 buys
    0.01 gallons more."""
    bad = copy.deepcopy(good)
    stops = bad["fuel_stops"]
    stops[2]["gallons"] = Decimal("-0.01")
    stops[3]["gallons"] += Decimal("0.01")
    agree(bad)
    assert stops[2]["cost"] == Decimal("-0.03")

    found, lines = rules(bad, prices)
    assert "R6" in found, lines


def test_a_stop_buying_less_than_nothing_breaks_no_other_rule(ask, prices):
    """The review's own case for Q0b-5: at stop cost 0, stop 15 (1.75 gallons) buys -0.01
    instead and stop 16 buys 1.76 more. The tank never runs dry, so only R6 sees it."""
    bad = ask("nyc_la", "New York, NY", "Los Angeles, CA", "0")
    stops, summary = bad["fuel_stops"], bad["summary"]
    assert stops[14]["gallons"] == Decimal("1.75")
    stops[14]["gallons"] = Decimal("-0.01")
    stops[15]["gallons"] += Decimal("1.76")
    agree(bad)
    summary["lowest_possible_fuel_cost"] = summary["total_fuel_cost"]  # R7 at stop cost 0

    found, lines = rules(bad, prices, "0")
    assert found == {"R6"}, lines


def test_qb10_the_verifier_says_what_it_does_not_check():
    """Review 9-Q0b, note N1. The verifier checks that a plan holds together and can be
    driven; that it is the cheapest is the exactness tests' job, and its description must
    say so."""
    tree = ast.parse((ROOT / "tests" / "verify.py").read_text(encoding="utf-8"))
    description = " ".join(ast.get_docstring(tree).split())

    assert "consistent and possible" in description
    assert "not that it is the cheapest" in description
    assert "EX-01 to EX-04" in description


# --- VR-01, VR-03, VR-04: what the verifier's caller can name -------------------------------


def test_vr01_a_routing_host_the_caller_names(good, prices):
    """Settled point 2: R15 accepts the two public routing servers, and any host its caller
    names, such as the stand-in `fake-osrm` of the end-to-end run."""
    stand_in = copy.deepcopy(good)
    stand_in["meta"]["routing_server"] = "fake-osrm"

    found, lines = rules(stand_in, prices)
    assert found == {"R15"}, lines
    assert verify_response(stand_in, prices, routing_hosts=["fake-osrm"]) == []
    assert verify_response(good, prices, routing_hosts=["fake-osrm"]) == []


@pytest.mark.django_db
def test_vr03_the_places_the_caller_gives(client, monkeypatch):
    """Settled point 3: R17 checks against the places its caller gives. EP-01's stations
    are invented, all in Testville, TX, so the endpoint tests give their own places: one
    for each station, where it stands. The default places have no Testville."""
    reset_index()
    try:
        add_station(1, "3.20", *DALLAS, name="DALLAS START")
        for opis_id, mile, price in ((2, 200, "3.10"), (3, 450, "3.00"), (4, 700, "3.20")):
            add_station(opis_id, price, *on_road(mile))
        coords, miles = straight_road(990.0)
        road = Route(coords=coords, distance_miles=miles, server=SERVER_1, calls=1)
        monkeypatch.setattr(routing, "fetch_route", lambda start, finish: road)
        response = client.get(URL, {"start": "Dallas, TX", "finish": "Houston, TX"})
        assert response.status_code == 200, response.content
        body = json.loads(response.content, parse_float=Decimal)
        own = places_from((s.city, s.state, s.lat, s.lng) for s in FuelStation.objects.all())
        prices = listed_prices()
    finally:
        reset_index()
    assert [stop["kind"] for stop in body["fuel_stops"]] == ["start", "station", "station"]

    assert verify_response(body, prices, places=own) == []
    found, lines = rules(body, prices)
    assert found == {"R17"}, lines
    assert "stop 2" in lines[0]
    assert "stop 3" in lines[0]


@pytest.mark.parametrize(("state", "city"), list(HAND_ADDED_PLACES))
def test_vr04_the_hand_added_places_are_in_the_default_places(prices, state, city):
    """Settled point 3: the five places added by hand (architecture section 6) are part of
    R17's default places. A station stop at the position stations/places.py gives one
    passes R17; 20 miles north of it, it does not, so R17 did run."""
    lat, lng = HAND_ADDED_PLACES[(state, city)]
    stop = {"order": 2, "kind": "station", "city": city, "state": state}
    body = {"fuel_stops": [stop | {"lat": Decimal(str(lat)), "lng": Decimal(str(lng))}]}

    found, lines = rules(body, prices)
    assert "R17" not in found, lines

    body["fuel_stops"][0]["lat"] += Decimal("0.29")  # 20 miles
    found, lines = rules(body, prices)
    assert "R17" in found, lines


# --- VF-19, and the verifier's own reading of the CSV ----------------------------------------


def imported_modules(path: Path) -> set[str]:
    """The top-level name of every module a source file imports."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_vf19_the_verifier_imports_only_the_standard_library():
    """Nothing from config, stations or trips, not even by way of another test module."""
    imported = imported_modules(ROOT / "tests" / "verify.py")

    assert not imported & {"config", "stations", "trips"}
    assert imported <= set(sys.stdlib_module_names)


def test_the_live_runner_does_not_import_the_application():
    """The brief's rule for scripts/live_check.py: it talks to the server over HTTP only."""
    assert not imported_modules(ROOT / "scripts" / "live_check.py") & {
        "config",
        "stations",
        "trips",
    }


def test_prices_are_the_cheapest_listing_and_the_first_row_on_a_tie():
    """R5 is only as good as this reading, so it is checked on the small CSV of section 2.1,
    whose answers LD-02 to LD-06 give."""
    prices = load_prices(SMALL_CSV)

    assert prices["1"] == Listing(
        Decimal("3.40000000"), "ALPHA TWO", "I-30, EXIT 1", "Dallas", "TX"
    )
    assert prices["2"].name == "BRAVO"
    assert prices["4"].price == Decimal("3.00733333")
    assert set(prices) == {"1", "2", "3", "4", "5"}
