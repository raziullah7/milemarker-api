"""The verifier itself: cases VF-01 to VF-19 of docs/test-cases.md, section 2.11.

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
from decimal import Decimal
from pathlib import Path

import numpy as np
import pytest

from tests.conftest import load_road
from tests.verify import Listing, load_prices, verify_response
from trips.services import routing
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


def rules(body: dict, prices: dict, stop_cost=None) -> tuple[set[str], list[str]]:
    """The IDs of the rules reported, and the lines themselves for the failure message."""
    lines = verify_response(body, prices, stop_cost)
    return {line.split(":", 1)[0] for line in lines}, lines


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
