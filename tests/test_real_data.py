"""Checks that need several modules at once, on the real stations and recorded roads.

Test IDs refer to docs/test-cases.md.
"""

import pytest

from stations.index import nearest_station
from stations.places import resolve
from tests.conftest import load_road
from trips.services.corridor import stations_along, thin
from trips.services.geo import resample


def test_real_index_holds_every_us_station(real_index):
    assert len(real_index) == 6626


def test_co17_stations_along_new_york_to_los_angeles(real_index):
    coords, distance_miles = load_road("nyc_la")
    road = resample(coords, round(distance_miles, 1))
    start = resolve("New York, NY", "start")
    start_station, _ = nearest_station(real_index, start.lat, start.lng)

    along = stations_along(road, real_index, exclude=start_station)
    kept = thin(along)

    # Measured during design: 363 before thinning, 98 after. The finished rules place a
    # few cities differently and scale the mile markers, which moves a station or two
    # across a limit, so the counts pass within 5%.
    assert len(along) == pytest.approx(363, rel=0.05)
    assert len(kept) == pytest.approx(98, rel=0.05)
    assert all(0 < c.mile < road.marker[-1] for c in along)
    assert all(c.off_route_miles <= 5.0 for c in along)
    assert start_station not in {c.station for c in along}
