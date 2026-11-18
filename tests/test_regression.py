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
