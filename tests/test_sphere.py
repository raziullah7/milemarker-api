"""Distance maths on a sphere. Test IDs (GE-01 ...) refer to docs/test-cases.md."""

import numpy as np
import pytest

from stations.sphere import EARTH_RADIUS_MILES, arc, chord, haversine_miles, to_xyz

NEW_YORK = (40.74838, -73.996705)
LOS_ANGELES = (33.973093, -118.247896)


def test_ge01_one_degree_of_longitude_on_the_equator():
    assert haversine_miles(0, 0, 0, 1) == pytest.approx(69.094, abs=0.001)


def test_ge02_equator_to_pole():
    assert haversine_miles(0, 0, 90, 0) == pytest.approx(6218.47, abs=0.01)


def test_ge03_a_point_is_no_distance_from_itself():
    assert haversine_miles(*NEW_YORK, *NEW_YORK) == 0.0


def test_ge04_points_on_the_unit_sphere():
    points = [(0, 0), (90, 0), NEW_YORK, LOS_ANGELES]
    xyz = to_xyz([p[0] for p in points], [p[1] for p in points])
    assert xyz.shape == (4, 3)
    assert np.linalg.norm(xyz, axis=1) == pytest.approx(1.0, abs=1e-12)

    # The straight line between two points matches the ground distance between them.
    straight = np.linalg.norm(xyz[2] - xyz[3])
    assert straight == pytest.approx(chord(haversine_miles(*NEW_YORK, *LOS_ANGELES)), abs=1e-12)


def test_ge04_a_single_point_has_shape_one_by_three():
    assert to_xyz(40.0, -74.0).shape == (1, 3)


@pytest.mark.parametrize("miles", [0, 0.5, 5, 500, 3000])
def test_ge05_arc_reverses_chord(miles):
    assert arc(chord(miles)) == pytest.approx(miles, abs=1e-9)


def test_ge05_opposite_points_are_a_diameter_apart():
    half_way_round = np.pi * EARTH_RADIUS_MILES  # 12,436.94 miles
    assert half_way_round == pytest.approx(12436.94, abs=0.01)
    assert chord(half_way_round) == pytest.approx(2.0, abs=1e-6)


def test_haversine_broadcasts_over_arrays():
    lat = np.array([0.0, 0.0])
    lng = np.array([1.0, 2.0])
    assert haversine_miles(0, 0, lat, lng) == pytest.approx([69.094, 138.188], abs=0.001)
