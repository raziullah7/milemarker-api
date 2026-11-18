"""Road geometry: mile markers and the border check. Test IDs (GE-06 ...) refer to docs/test-cases.md."""

import time
from pathlib import Path

import numpy as np
import pytest

from stations.sphere import haversine_miles
from tests.conftest import load_road
from trips.services.geo import RoadPoints, load_borders, longest_run_abroad, resample

BORDERS_FILE = Path(__file__).resolve().parent.parent / "data" / "borders.json"


def recorded_road(name: str) -> RoadPoints:
    """A recorded road re-spaced as the API does it, on the service's length rounded to 0.1 mile."""
    coords, miles = load_road(name)
    return resample(coords, round(miles, 1))


def box(south: float, north: float, west: float, east: float) -> np.ndarray:
    """A closed rectangular outline, rows of [lng, lat]."""
    return np.array([[west, south], [east, south], [east, north], [west, north], [west, south]])


def road_due_north(lng: float, from_lat: float, to_lat: float) -> RoadPoints:
    """A straight road along one line of longitude, its length measured by our own sums."""
    coords = np.array([[lng, from_lat], [lng, to_lat]])
    return resample(coords, float(haversine_miles(from_lat, lng, to_lat, lng)))


# The test boxes of GE-10 and GE-13, standing in for the two countries.
CANADA_BOX = box(45.0, 46.0, -80.0, -79.0)
MEXICO_BOX = box(30.0, 31.0, -106.0, -105.0)


@pytest.fixture(scope="module")
def real_borders() -> dict[str, np.ndarray]:
    return load_borders(BORDERS_FILE)


# --- resample ----------------------------------------------------------------


def test_ge06_one_degree_along_the_equator():
    road = resample(np.array([[0.0, 0.0], [1.0, 0.0]]), 69.1)

    assert len(road.lat) == len(road.lng) == len(road.marker) == 140
    assert (road.lat[0], road.lng[0]) == (0.0, 0.0)
    assert road.lat[-1] == pytest.approx(0.0, abs=1e-12)
    assert road.lng[-1] == pytest.approx(1.0, abs=1e-12)
    assert road.marker[0] == 0.0
    assert road.marker[-1] == 69.1
    assert np.all(np.diff(road.marker) > 0)


def test_ge07_a_repeated_point_changes_nothing():
    plain = resample(np.array([[0.0, 0.0], [1.0, 0.0]]), 69.1)
    repeated = resample(np.array([[0.0, 0.0], [0.5, 0.0], [0.5, 0.0], [1.0, 0.0]]), 69.1)

    assert len(repeated.marker) == len(plain.marker)
    np.testing.assert_allclose(repeated.lat, plain.lat, rtol=0, atol=1e-9)
    np.testing.assert_allclose(repeated.lng, plain.lng, rtol=0, atol=1e-9)
    np.testing.assert_allclose(repeated.marker, plain.marker, rtol=0, atol=1e-9)


def test_ge08_a_corner_keeps_every_point_on_the_road():
    road = resample(np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]]), 138.2)

    assert len(road.marker) == 278
    assert road.marker[-1] == 138.2
    # East along the equator to longitude 1, then north along longitude 1.
    on_first = (np.abs(road.lat) <= 1e-9) & (road.lng >= -1e-9) & (road.lng <= 1 + 1e-9)
    on_second = (np.abs(road.lng - 1) <= 1e-9) & (road.lat >= -1e-9) & (road.lat <= 1 + 1e-9)
    assert np.all(on_first | on_second)


def test_ge09_new_york_to_los_angeles():
    coords, _ = load_road("nyc_la")
    road = resample(coords, 2800.7)

    assert len(road.marker) == pytest.approx(5594, abs=1)
    assert road.marker[-1] == 2800.7
    lat, lng = coords[:, 1], coords[:, 0]
    own_length = haversine_miles(lat[:-1], lng[:-1], lat[1:], lng[1:]).sum()
    assert own_length == pytest.approx(2800.7, rel=0.002)


# --- longest_run_abroad ------------------------------------------------------


def test_ge10_one_stretch_through_a_box():
    road = road_due_north(-79.5, 44.0, 47.0)
    borders = {"CAN": CANADA_BOX, "MEX": MEXICO_BOX}

    assert longest_run_abroad(road, borders) == pytest.approx(69.1, abs=4)


def test_ge11_the_longest_run_not_the_sum():
    # One C-shaped outline: the road along 79.5 W is inside it from 45.0 to 45.2 N and
    # again from 45.5 to 45.7 N, and outside it in the notch between.
    c_shape = np.array(
        [
            [-80.0, 45.0],
            [-78.0, 45.0],
            [-78.0, 45.7],
            [-80.0, 45.7],
            [-80.0, 45.5],
            [-79.0, 45.5],
            [-79.0, 45.2],
            [-80.0, 45.2],
            [-80.0, 45.0],
        ]
    )
    road = road_due_north(-79.5, 44.0, 47.0)

    assert longest_run_abroad(road, {"CAN": c_shape, "MEX": MEXICO_BOX}) == pytest.approx(
        13.8, abs=4
    )


def test_ge12_middle_latitudes_are_not_sampled():
    # The box stands in for both countries: neither is tested between 32.8 and 41.6 N.
    middle_box = box(35.0, 36.0, -80.0, -79.0)
    road = road_due_north(-79.5, 34.0, 37.0)

    assert longest_run_abroad(road, {"CAN": middle_box, "MEX": middle_box}) == 0.0


def test_ge13_one_stretch_through_mexico():
    road = road_due_north(-105.5, 29.0, 32.0)
    borders = {"CAN": CANADA_BOX, "MEX": MEXICO_BOX}

    assert longest_run_abroad(road, borders) == pytest.approx(69.1, abs=4)


def test_ge14_detroit_to_buffalo_runs_through_ontario(real_borders):
    assert longest_run_abroad(recorded_road("det_buf"), real_borders) == pytest.approx(
        252, rel=0.02
    )


def test_ge15_detroit_to_boston_runs_through_ontario(real_borders):
    assert longest_run_abroad(recorded_road("det_bos"), real_borders) == pytest.approx(
        234, rel=0.02
    )


@pytest.mark.parametrize(
    "name",
    [
        "bos_dc",
        "bos_sea",
        "chi_hou",
        "dal_hou",
        "det_porthuron",
        "elpaso_delrio",
        "houlton_madawaska",
        "intlfalls_baudette",
        "keywest_miami",
        "laredo_brownsville",
        "montauk_nyc",
        "nyc_la",
        "sandiego_calexico",
        "sea_mia",
        "sea_blaine",
    ],
)
def test_ge16_roads_that_stay_in_the_usa(name, real_borders):
    assert longest_run_abroad(recorded_road(name), real_borders) <= 25


def test_ge17_load_borders():
    borders = load_borders(str(BORDERS_FILE))

    assert set(borders) == {"CAN", "MEX"}
    for outline in borders.values():
        assert outline.ndim == 2
        assert outline.shape[1] == 2
        assert len(outline) >= 4  # at least a triangle, closed


def test_border_check_is_fast_enough(real_borders):
    # The design measured 40 ms on this road, the one that follows the border longest.
    # 200 ms catches a gross slowdown without making the suite flaky.
    road = recorded_road("bos_sea")
    runs = []
    for _ in range(3):
        started = time.perf_counter()
        longest_run_abroad(road, real_borders)
        runs.append(time.perf_counter() - started)

    assert min(runs) < 0.2
