"""Figures pinned after the independent verifier and the live run passed them.

Each trip runs through plan_trip on a recorded road with the real stations, so the result
never changes unless the code does. A change here is not necessarily a fault, but it must
be explained: these are the numbers a reviewer would see.
"""

from decimal import Decimal

import pytest

from stations.places import resolve
from tests.conftest import load_road
from trips.services import planner, routing
from trips.services.routing import Route

# (start, finish, recorded road, stop cost) -> (distance, stops, total, lowest, lowest stops)
PINNED = {
    ("New York, NY", "Los Angeles, CA", "nyc_la", "10"): (2800.7, 7, 867.29, 855.97, 18),
    ("New York, NY", "Los Angeles, CA", "nyc_la", "0"): (2800.7, 18, 855.97, 855.97, 18),
    ("New York, NY", "Los Angeles, CA", "nyc_la", "25"): (2800.7, 6, 886.19, 855.97, 18),
    ("Seattle, WA", "Miami, FL", "sea_mia", "10"): (3301.2, 8, 1042.31, 1026.28, 21),
    ("Chicago, IL", "Houston, TX", "chi_hou", "10"): (1086.9, 3, 331.24, 319.62, 11),
    ("Dallas, TX", "Houston, TX", "dal_hou", "10"): (238.1, 1, 68.19, 65.78, 2),
    ("Boston, MA", "Washington, DC", "bos_dc", "10"): (437.1, 3, 148.81, 145.92, 8),
}


def figures(start: str, finish: str, road: str, stop_cost: str, monkeypatch) -> tuple:
    coords, distance_miles = load_road(road)
    monkeypatch.setattr(
        routing,
        "fetch_route",
        lambda a, b: Route(coords, distance_miles, "router.project-osrm.org", 1),
    )
    summary = planner.plan_trip(start, finish, Decimal(stop_cost))["summary"]
    return (
        summary["distance_miles"],
        summary["stops"],
        summary["total_fuel_cost"],
        summary["lowest_possible_fuel_cost"],
        summary["lowest_possible_stops"],
    )


@pytest.mark.parametrize("trip", list(PINNED), ids=lambda t: f"{t[2]}-stop-cost-{t[3]}")
def test_pinned_figures(trip, use_real_stations, monkeypatch):
    # The start and finish must be real places, or the pin would test nothing.
    resolve(trip[0], "start")
    resolve(trip[1], "finish")
    assert figures(*trip, monkeypatch) == PINNED[trip]


# New York to Los Angeles at stop cost 10, stop by stop: (station_id, mile_marker, gallons,
# cost), as release 1.0 gives them (QB-15). The summary pins cannot see every change: stops
# 6 and 7 share a price, so 0.01 gallons moved from one to the other leaves the total as it
# is, but not these.
NEW_YORK_STOPS = [
    (72087, 0.0, 39.21, 127.0),
    (72445, 392.1, 46.17, 141.23),
    (70744, 853.8, 49.98, 148.39),
    (52548, 1353.6, 50.0, 144.95),
    (73101, 1739.7, 38.61, 121.58),
    (71712, 2120.8, 25.92, 85.08),
    (72965, 2498.9, 30.18, 99.06),
]


def test_pinned_stops_new_york_to_los_angeles(use_real_stations, monkeypatch):
    coords, distance_miles = load_road("nyc_la")
    monkeypatch.setattr(
        routing,
        "fetch_route",
        lambda a, b: Route(coords, distance_miles, "router.project-osrm.org", 1),
    )
    stops = planner.plan_trip("New York, NY", "Los Angeles, CA", Decimal("10"))["fuel_stops"]

    shown = [(s["station_id"], s["mile_marker"], s["gallons"], s["cost"]) for s in stops]
    assert shown == NEW_YORK_STOPS
