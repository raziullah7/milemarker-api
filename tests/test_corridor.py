"""Station search along the road. Test IDs (CO-01 ...) refer to docs/test-cases.md.

Every case uses the equator road of docs/test-cases.md section 2.1, radius 5 and thinning 10.
"""

from decimal import Decimal

import numpy as np
import pytest

from stations.types import StationIndex, StationInfo, build_index
from trips.services.corridor import Candidate, stations_along, thin
from trips.services.geo import RoadPoints

# Miles in one degree on the equator: a point at mile m has longitude m / MILES_PER_DEGREE.
MILES_PER_DEGREE = 69.094094


def equator_road() -> RoadPoints:
    """2,001 points along the equator from longitude 0, one every half mile, 1,000 miles."""
    marker = np.arange(2001) * 0.5
    return RoadPoints(lat=np.zeros(2001), lng=marker / MILES_PER_DEGREE, marker=marker)


ROAD = equator_road()


def station(station_id: int, mile: float, price: str, north: float = 0.0):
    """A station at `mile` along the equator road, `north` miles off it (negative is south)."""
    info = StationInfo(
        opis_id=station_id,
        name=f"STATION {station_id}",
        address="",
        city="",
        state="",
        price=Decimal(price),
    )
    return info, north / MILES_PER_DEGREE, mile / MILES_PER_DEGREE


def search(*stations, exclude_id: int | None = None) -> tuple[StationIndex, list[Candidate]]:
    """Index the stations and search the equator road; `exclude_id` is a station ID."""
    index = build_index(stations)
    ids = [info.opis_id for info in index.info]
    exclude = None if exclude_id is None else ids.index(exclude_id)
    return index, stations_along(ROAD, index, exclude=exclude)


def kept_ids(*stations, exclude_id: int | None = None) -> list[int]:
    """The IDs of the stations left after the search and the thinning, in order."""
    index, found = search(*stations, exclude_id=exclude_id)
    return [index.info[c.station].opis_id for c in thin(found)]


# --- stations_along ----------------------------------------------------------


def test_co01_a_station_on_the_road():
    index, found = search(station(1, 100, "3.00"))

    assert len(found) == 1
    [c] = found
    assert c.mile == 100.0
    assert c.price == 3.00
    assert index.info[c.station].opis_id == 1
    assert c.off_route_miles == pytest.approx(0.0, abs=1e-9)
    assert c.point == 200


def test_co02_just_inside_the_limit_to_the_north():
    _, [c] = search(station(1, 100, "3.00", north=4.9))

    assert c.off_route_miles == pytest.approx(4.9, abs=0.001)


def test_co03_just_inside_the_limit_to_the_south():
    _, [c] = search(station(1, 100, "3.00", north=-4.9))

    assert c.off_route_miles == pytest.approx(4.9, abs=0.001)


def test_co04_just_outside_the_limit():
    _, found = search(station(1, 100, "3.00", north=5.1))

    assert found == []


def test_co05_the_mile_is_the_nearest_road_points():
    _, [c] = search(station(1, 100.2, "3.00", north=3.0))

    assert c.mile == 100.0
    assert c.off_route_miles == pytest.approx(3.007, abs=0.001)


def test_co06_behind_the_start_is_dropped():
    _, found = search(station(1, -3, "3.00"))

    assert found == []


def test_co07_beyond_the_finish_is_dropped():
    _, found = search(station(1, 1003, "3.00"))

    assert found == []


def test_co08_the_start_station_is_left_out():
    assert kept_ids(station(1, 50, "3.00"), station(2, 300, "3.00"), exclude_id=1) == [2]


def test_co09_sorted_by_mile():
    stations = (station(1, 300, "3.00"), station(2, 100, "3.00"), station(3, 200, "3.00"))
    index, found = search(*stations)

    assert [index.info[c.station].opis_id for c in found] == [2, 3, 1]
    assert kept_ids(*stations) == [2, 3, 1]


# --- thin --------------------------------------------------------------------


def test_co10_same_position_the_cheaper_stays():
    assert kept_ids(station(3, 100, "3.20"), station(8, 100, "3.10")) == [8]


def test_co11_same_position_and_price_the_lower_id_stays():
    assert kept_ids(station(7, 100, "3.00"), station(4, 100, "3.00")) == [4]


def test_co12_a_cheaper_station_within_ten_miles():
    assert kept_ids(station(1, 100, "3.00"), station(2, 105, "3.10")) == [1]


def test_co13_the_cheaper_one_may_come_later():
    assert kept_ids(station(1, 100, "3.10"), station(2, 105, "3.00")) == [2]


def test_co14_equally_cheap_the_earlier_stays_whatever_the_id():
    assert kept_ids(station(9, 100, "3.00"), station(1, 105, "3.00")) == [9]


@pytest.mark.parametrize(
    ("second_mile", "expected"),
    [
        (110, [1]),  # exactly 10 miles counts as within
        (110.5, [1, 2]),
    ],
)
def test_co15_ten_miles_is_within(second_mile, expected):
    assert kept_ids(station(1, 100, "3.00"), station(2, second_mile, "3.10")) == expected


def test_co16_a_dropped_station_still_drops_others():
    stations = (station(1, 100, "3.00"), station(2, 108, "3.05"), station(3, 116, "3.08"))

    # Station 3 is 16 miles from station 1 but 8 from station 2, which is cheaper.
    assert kept_ids(*stations) == [1]
