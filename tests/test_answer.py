"""The answer builder: rounding, the order of the response, and the map.

Test IDs (AN-01 ...) and rules (R3 ...) refer to docs/test-cases.md, sections 2.8 and 4.
Each answer is read back from its JSON text with numbers as exact decimals, the way the
correctness rules read a response.
"""

import dataclasses
import itertools
import json
import math
from decimal import ROUND_HALF_UP, Decimal

import numpy as np
import pytest

from stations.places import Place
from stations.types import StationInfo
from trips.services.answer import Stop, build_answer
from trips.services.geo import RoadPoints

START = Place("New York, NY", 40.74838, -73.99671)
FINISH = Place("Los Angeles, CA", 33.97309, -118.2479)

# Name, city and state of stops 1, 2 and 3 in the plans below.
STATIONS = [
    ("DELTA", "Henrico", "VA"),
    ("SHEETZ #639", "Youngstown", "OH"),
    ("ECHO", "Saint Louis", "MO"),
]

WARNING_25_1 = (
    "The nearest listed fuel station to the start is DELTA in Henrico, VA, 25.1 miles away. "
    "The first fill-up is priced there."
)


def _road(distance_miles: float) -> RoadPoints:
    """A straight road with a point every half mile, ending exactly on distance_miles.

    The builder only reads the arrays, so the road's shape does not matter. Both
    coordinates change along it and have many decimals, so rounding shows.
    """
    marker = np.append(np.arange(0.0, distance_miles, 0.5), distance_miles)
    return RoadPoints(
        lat=35.0 + marker / 111.123456, lng=-110.0 + marker / 91.987654, marker=marker
    )


def _plan(
    gallons: list[float], prices: list[str], distance_miles: float, start: Place = START
) -> tuple[RoadPoints, list[Stop]]:
    """A road and a plan on it: stop 1 at the start place, stop k + 1 at mile 100 * k."""
    road = _road(distance_miles)
    stops = []
    for k, (amount, price) in enumerate(zip(gallons, prices, strict=True)):
        name, city, state = STATIONS[k]
        info = StationInfo(100 + k, name, f"I-80, EXIT {k}", city, state, Decimal(price))
        if k == 0:
            stops.append(Stop(info, 0.0, start.lat, start.lng, amount))
        else:
            point = 200 * k  # the road point at mile 100 * k
            lat, lng = float(road.lat[point]), float(road.lng[point])
            stops.append(Stop(info, float(road.marker[point]), lat, lng, amount))
    return road, stops


def _answer(road: RoadPoints, stops: list[Stop], **changes) -> dict:
    """build_answer on a plan, with any argument replaced by `changes`.

    By default the trip is the road's length and the free-stops plan is the plan itself.
    """
    arguments = {
        "start": START,
        "finish": FINISH,
        "distance_miles": float(road.marker[-1]),
        "road": road,
        "stops": stops,
        "cheapest": [(stop.info.price, stop.gallons) for stop in stops],
        "first_fill_miles": 3.1,
        "stop_cost": Decimal("10"),
    }
    return build_answer(**(arguments | changes))


def _json(answer: dict) -> dict:
    """The answer as a client reads it: through its JSON text, numbers as exact decimals."""
    return json.loads(json.dumps(answer), parse_float=Decimal)


def _cents(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def test_an01_gallons_are_rounded_as_a_running_total():
    # Running totals 10.004, 30.008, 40.000 round to 10.00, 30.01, 40.00.
    road, stops = _plan([10.004, 20.004, 9.992], ["3.00", "3.10", "3.20"], 400.0)
    body = _json(_answer(road, stops))
    gallons = [s["gallons"] for s in body["fuel_stops"]]

    assert gallons == [Decimal("10.00"), Decimal("20.01"), Decimal("9.99")]
    assert list(itertools.accumulate(gallons)) == [
        Decimal("10.00"),
        Decimal("30.01"),
        Decimal("40.00"),
    ]
    assert [s["cost"] for s in body["fuel_stops"]] == [
        Decimal("30.00"),
        Decimal("62.03"),
        Decimal("31.97"),
    ]
    assert body["summary"]["total_fuel_cost"] == Decimal("124.00")
    assert body["summary"]["gallons"] == Decimal("40.00")


def test_an02_a_running_total_can_round_up_first():
    # Running totals 10.006, 30.012, 40.000 round to 10.01, 30.01, 40.00.
    road, stops = _plan([10.006, 20.006, 9.988], ["3.00", "3.10", "3.20"], 400.0)
    body = _json(_answer(road, stops))
    gallons = [s["gallons"] for s in body["fuel_stops"]]

    assert gallons == [Decimal("10.01"), Decimal("20.00"), Decimal("9.99")]
    assert list(itertools.accumulate(gallons)) == [
        Decimal("10.01"),
        Decimal("30.01"),
        Decimal("40.00"),
    ]
    assert [s["cost"] for s in body["fuel_stops"]] == [
        Decimal("30.03"),
        Decimal("62.00"),
        Decimal("31.97"),
    ]
    assert body["summary"]["total_fuel_cost"] == Decimal("124.00")


def test_rounding_difference_falls_where_the_running_total_crosses_a_cent():
    # Running totals 20.004, 30.008, 40.010 round to 20.00, 30.01, 40.01, so the extra
    # hundredth is shown on the second purchase, not on the largest. Rounded one by one,
    # all three would round down, and the old rule gave the 0.01 to the 20.004 purchase.
    road, stops = _plan([20.004, 10.004, 10.002], ["3.00", "3.10", "3.20"], 400.1)
    body = _json(_answer(road, stops))

    assert [s["gallons"] for s in body["fuel_stops"]] == [
        Decimal("20.00"),
        Decimal("10.01"),
        Decimal("10.00"),
    ]
    assert [s["cost"] for s in body["fuel_stops"]] == [
        Decimal("60.00"),
        Decimal("31.03"),
        Decimal("32.00"),
    ]
    assert body["summary"]["gallons"] == Decimal("40.01")


def test_an03_cost_rounds_half_up_in_decimal_arithmetic():
    assert round(1.00 * 3.005, 2) == 3.00  # the floating-point answer this must not give

    road, stops = _plan([1.00], ["3.005"], 10.0)
    body = _json(_answer(road, stops))

    assert body["fuel_stops"][0]["cost"] == Decimal("3.01")
    assert body["summary"]["total_fuel_cost"] == Decimal("3.01")


def test_an04_price_keeps_every_digit_of_the_csv():
    road, stops = _plan([2.50], ["3.00733333"], 25.0)
    answer = _answer(road, stops)

    assert _json(answer)["fuel_stops"][0]["cost"] == Decimal("7.52")
    assert '"price_per_gallon": 3.00733333,' in json.dumps(answer)


@pytest.mark.parametrize(
    ("first_fill_miles", "expected"),
    [
        (25.0, []),
        (25.1, [WARNING_25_1]),
        # Shown as 25.0, so no warning: rule R10 reads the figure the response shows.
        (25.04, []),
    ],
)
def test_an05_warning_only_when_first_fill_is_over_25_miles(first_fill_miles, expected):
    road, stops = _plan([10.0, 30.0], ["3.00", "3.10"], 400.0)
    body = _json(_answer(road, stops, first_fill_miles=first_fill_miles))

    assert body["warnings"] == expected


def test_an06_keys_are_in_the_documented_order():
    road, stops = _plan([10.0, 20.0, 10.0], ["3.00", "3.10", "3.20"], 400.0)
    answer = _answer(road, stops)

    assert list(answer) == ["summary", "warnings", "assumptions", "fuel_stops", "map"]
    assert list(answer["summary"]) == [
        "start",
        "finish",
        "distance_miles",
        "gallons",
        "total_fuel_cost",
        "stops",
        "lowest_possible_fuel_cost",
        "lowest_possible_stops",
        "first_fill_distance_miles",
    ]
    assert list(answer["summary"]["start"]) == ["label", "lat", "lng"]
    assert list(answer["assumptions"]) == [
        "range_miles",
        "miles_per_gallon",
        "tank_gallons",
        "starting_fuel_gallons",
        "stop_cost",
        "search_radius_miles",
    ]
    assert list(answer["fuel_stops"][0]) == [
        "order",
        "kind",
        "station_id",
        "name",
        "address",
        "city",
        "state",
        "mile_marker",
        "lat",
        "lng",
        "price_per_gallon",
        "gallons",
        "cost",
    ]
    assert list(answer["map"]) == ["type", "features"]


@pytest.mark.parametrize(
    ("stop_cost", "shown"),
    [(Decimal("10"), 10.0), (Decimal("0"), 0.0), (Decimal("12.5"), 12.5)],
)
def test_an07_assumptions(stop_cost, shown):
    road, stops = _plan([10.0, 30.0], ["3.00", "3.10"], 400.0)
    assumptions = _answer(road, stops, stop_cost=stop_cost)["assumptions"]

    assert json.dumps(assumptions) == json.dumps(
        {
            "range_miles": 500,
            "miles_per_gallon": 10,
            "tank_gallons": 50,
            "starting_fuel_gallons": 0,
            "stop_cost": shown,
            "search_radius_miles": 5,
        }
    )
    assert type(assumptions["stop_cost"]) is float


def test_an08_start_stop_then_station_stops_on_the_road():
    road, stops = _plan([10.0, 20.0, 10.0], ["3.00", "3.10", "3.20"], 400.0)
    body = _json(_answer(road, stops))
    first, second, third = body["fuel_stops"]
    line = body["map"]["features"][0]["geometry"]["coordinates"]

    assert first["order"] == 1
    assert first["kind"] == "start"
    assert first["mile_marker"] == 0
    assert [first["lat"], first["lng"]] == [Decimal("40.74838"), Decimal("-73.99671")]
    assert (first["station_id"], first["name"], first["address"]) == (100, "DELTA", "I-80, EXIT 0")
    assert (first["city"], first["state"], first["price_per_gallon"]) == ("Henrico", "VA", 3)

    assert [second["order"], third["order"]] == [2, 3]
    assert [second["kind"], third["kind"]] == ["station", "station"]
    assert [second["mile_marker"], third["mile_marker"]] == [100, 200]
    # Each sits on the route line, at its own road point (rule R12).
    assert [second["lng"], second["lat"]] == line[200]
    assert [third["lng"], third["lat"]] == line[400]


def test_an09_map_holds_the_route_then_the_stops_then_start_and_finish():
    road, stops = _plan([10.0, 20.0, 10.0], ["3.00", "3.10", "3.20"], 400.0)
    body = _json(_answer(road, stops))
    features = body["map"]["features"]

    assert body["map"]["type"] == "FeatureCollection"
    assert len(features) == 1 + 3 + 2
    assert all(f["type"] == "Feature" for f in features)

    route = features[0]
    assert route["geometry"]["type"] == "LineString"
    assert route["properties"] == {"kind": "route", "distance_miles": Decimal("400.0")}
    assert len(route["geometry"]["coordinates"]) == len(road.lat)
    # [lng, lat]: the road starts at longitude -110, latitude 35.
    assert route["geometry"]["coordinates"][0] == [Decimal("-110.0"), Decimal("35.0")]

    sheetz = features[2]
    assert sheetz["geometry"]["type"] == "Point"
    assert sheetz["properties"] == {
        "kind": "stop",
        "order": 2,
        "title": "2. SHEETZ #639, Youngstown OH",
        "name": "SHEETZ #639",
        "mile_marker": Decimal("100.0"),
        "price_per_gallon": Decimal("3.1"),
        "gallons": Decimal("20.0"),
        "cost": Decimal("62.0"),
        "marker-color": "#d9480f",
    }
    stop = body["fuel_stops"][1]
    assert sheetz["geometry"]["coordinates"] == [stop["lng"], stop["lat"]]
    assert [f["properties"]["order"] for f in features[1:4]] == [1, 2, 3]

    start, finish = features[4], features[5]
    assert start["properties"] == {
        "kind": "start",
        "title": "Start: New York, NY",
        "marker-color": "#2b8a3e",
    }
    assert start["geometry"] == {
        "type": "Point",
        "coordinates": [Decimal("-73.99671"), Decimal("40.74838")],
    }
    assert finish["properties"] == {
        "kind": "finish",
        "title": "Finish: Los Angeles, CA",
        "marker-color": "#1864ab",
    }
    assert finish["geometry"] == {
        "type": "Point",
        "coordinates": [Decimal("-118.2479"), Decimal("33.97309")],
    }


def test_an10_miles_and_coordinates_are_rounded():
    start = Place("New York, NY", 40.748380123, -73.996705)
    road, stops = _plan([10.0, 30.0], ["3.00", "3.10"], 400.0, start)
    stops[1] = dataclasses.replace(stops[1], mile=100.04)
    body = _json(_answer(road, stops, start=start, first_fill_miles=3.149))

    assert body["summary"]["start"]["lat"] == Decimal("40.74838")
    assert body["fuel_stops"][0]["lat"] == Decimal("40.74838")
    assert body["fuel_stops"][1]["mile_marker"] == Decimal("100.0")
    assert body["summary"]["first_fill_distance_miles"] == Decimal("3.1")


def test_an11_tiny_free_stop_purchase_is_not_counted_but_its_fuel_is():
    road, stops = _plan([30.0], ["3.50"], 300.0)
    cheapest = [(Decimal("3.50"), 0.003), (Decimal("3.00"), 29.997)]
    summary = _json(_answer(road, stops, cheapest=cheapest))["summary"]

    assert summary["lowest_possible_stops"] == 1
    assert summary["lowest_possible_fuel_cost"] == Decimal("90.00")


def test_purchase_rounding_to_zero_gallons_is_not_a_stop():
    # The middle purchase rounds to 0.00 gallons; its fuel is in the 30.00 of the last.
    road, stops = _plan([10.0, 0.003, 29.997], ["3.00", "3.10", "3.20"], 400.0)
    body = _json(_answer(road, stops))
    summary, fuel_stops = body["summary"], body["fuel_stops"]
    stop_points = body["map"]["features"][1:-2]

    assert [s["name"] for s in fuel_stops] == ["DELTA", "ECHO"]
    assert [s["order"] for s in fuel_stops] == [1, 2]
    assert all(s["gallons"] > 0 for s in fuel_stops)
    assert summary["stops"] == 2
    assert [p["properties"]["title"] for p in stop_points] == [
        "1. DELTA, Henrico VA",
        "2. ECHO, Saint Louis MO",
    ]
    assert sum(s["gallons"] for s in fuel_stops) == summary["gallons"]
    assert summary["gallons"] == summary["distance_miles"] / 10
    assert summary["total_fuel_cost"] == sum(s["cost"] for s in fuel_stops)


def test_lowest_bill_is_never_shown_above_the_plans_bill():
    # Both bills are 119.99 exactly. Rounding the free-stops plan moves 0.005 gallons
    # onto the dearer purchase (10.00 at 4.50, 30.00 at 2.50), which shows as 120.00.
    road, stops = _plan([40.0], ["2.99975"], 400.0)
    cheapest = [(Decimal("4.50"), 9.995), (Decimal("2.50"), 30.005)]
    summary = _json(_answer(road, stops, cheapest=cheapest))["summary"]

    assert summary["total_fuel_cost"] == Decimal("119.99")
    assert summary["lowest_possible_fuel_cost"] == Decimal("119.99")
    assert summary["lowest_possible_stops"] == summary["stops"] == 1


def test_free_stops_plan_equal_to_the_plan_gives_equal_figures():
    # Stop cost 0: the free-stops plan is the plan itself, tiny middle purchase included.
    road, stops = _plan([10.0, 0.003, 29.997], ["3.00", "3.10", "3.20"], 400.0)
    summary = _json(_answer(road, stops, stop_cost=Decimal("0")))["summary"]

    assert summary["lowest_possible_fuel_cost"] == summary["total_fuel_cost"]
    assert summary["lowest_possible_stops"] == summary["stops"] == 2


# Decimals allowed per field name (rule R14). Prices are left out: they keep every digit.
DECIMALS = {
    "distance_miles": 1,
    "mile_marker": 1,
    "first_fill_distance_miles": 1,
    "gallons": 2,
    "cost": 2,
    "total_fuel_cost": 2,
    "lowest_possible_fuel_cost": 2,
    "stop_cost": 2,
    "lat": 5,
    "lng": 5,
    "coordinates": 5,
}
NUMBERS = set(DECIMALS) | {
    "price_per_gallon",
    "order",
    "station_id",
    "stops",
    "lowest_possible_stops",
    "range_miles",
    "miles_per_gallon",
    "tank_gallons",
    "starting_fuel_gallons",
    "search_radius_miles",
}


def _leaves(node, key=None):
    """Every (field name, value) below `node`; values inside a list take the list's name."""
    if isinstance(node, dict):
        for name, value in node.items():
            yield from _leaves(value, name)
    elif isinstance(node, list):
        for value in node:
            yield from _leaves(value, key)
    else:
        yield key, node


@pytest.mark.parametrize("first_fill_miles", [3.149, 47.26])
def test_complete_answer_obeys_the_correctness_rules(first_fill_miles):
    road, stops = _plan([10.004, 20.004, 9.992], ["3.00733333", "3.10", "3.20"], 400.0)
    cheapest = [(Decimal("3.00733333"), 0.004), (Decimal("3.10"), 29.996), (Decimal("2.9"), 10.0)]
    body = _json(
        _answer(
            road,
            stops,
            cheapest=cheapest,
            first_fill_miles=first_fill_miles,
            stop_cost=Decimal("12.5"),
        )
    )
    summary, fuel_stops, features = body["summary"], body["fuel_stops"], body["map"]["features"]

    # R3 Gallons
    assert sum(s["gallons"] for s in fuel_stops) == summary["gallons"]
    assert summary["gallons"] == summary["distance_miles"] / 10

    # R4 Money
    for s in fuel_stops:
        assert s["cost"] == _cents(s["gallons"] * s["price_per_gallon"])
    assert summary["total_fuel_cost"] == sum(s["cost"] for s in fuel_stops)

    # R6 Stops
    assert fuel_stops[0]["kind"] == "start"
    assert fuel_stops[0]["mile_marker"] == 0
    assert [fuel_stops[0]["lat"], fuel_stops[0]["lng"]] == [
        summary["start"]["lat"],
        summary["start"]["lng"],
    ]
    assert all(s["kind"] == "station" for s in fuel_stops[1:])
    assert [s["order"] for s in fuel_stops] == list(range(1, len(fuel_stops) + 1))
    markers = [s["mile_marker"] for s in fuel_stops]
    assert all(a < b for a, b in itertools.pairwise(markers))
    assert markers[-1] < summary["distance_miles"]
    assert len({s["station_id"] for s in fuel_stops}) == len(fuel_stops)

    # R8 Stop count
    assert summary["stops"] == len(fuel_stops)
    assert summary["stops"] >= math.ceil(summary["distance_miles"] / 500)

    # R9 Assumptions
    assert body["assumptions"] == {
        "range_miles": 500,
        "miles_per_gallon": 10,
        "tank_gallons": 50,
        "starting_fuel_gallons": 0,
        "stop_cost": Decimal("12.5"),
        "search_radius_miles": 5,
    }

    # R10 First fill-up
    first_fill = summary["first_fill_distance_miles"]
    assert first_fill >= 0
    if first_fill > 25:
        assert len(body["warnings"]) == 1
        assert fuel_stops[0]["name"] in body["warnings"][0]
        assert str(first_fill) in body["warnings"][0]
    else:
        assert body["warnings"] == []

    # R11 Map
    assert body["map"]["type"] == "FeatureCollection"
    route = features[0]
    assert route["geometry"]["type"] == "LineString"
    assert route["properties"]["kind"] == "route"
    assert route["properties"]["distance_miles"] == summary["distance_miles"]
    points = features[1:]
    assert len(points) == len(fuel_stops) + 2
    for point, s in zip(points[:-2], fuel_stops, strict=True):
        props = point["properties"]
        assert props["kind"] == "stop"
        for field in ("order", "name", "mile_marker", "price_per_gallon", "gallons", "cost"):
            assert props[field] == s[field]
        assert props["title"] == f"{s['order']}. {s['name']}, {s['city']} {s['state']}"
        assert point["geometry"]["coordinates"] == [s["lng"], s["lat"]]
    start, finish = points[-2], points[-1]
    assert start["properties"]["kind"] == "start"
    assert start["geometry"]["coordinates"] == [summary["start"]["lng"], summary["start"]["lat"]]
    assert finish["properties"]["kind"] == "finish"
    assert finish["geometry"]["coordinates"] == [
        summary["finish"]["lng"],
        summary["finish"]["lat"],
    ]
    for point in points:
        assert point["geometry"]["type"] == "Point"
        assert "title" in point["properties"]
        assert "marker-color" in point["properties"]

    # R14 Precision
    for name, value in _leaves(body):
        if name in NUMBERS:
            assert isinstance(value, int | Decimal), name
            assert not isinstance(value, bool), name
        if name in DECIMALS and isinstance(value, Decimal):
            assert -value.as_tuple().exponent <= DECIMALS[name], (name, value)
