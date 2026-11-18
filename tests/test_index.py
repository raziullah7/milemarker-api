"""Cases LD-13 to LD-18: the in-memory station index, loaded from PostgreSQL."""

from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command

from stations import places
from stations.exceptions import StationsNotLoaded
from stations.index import get_index, nearest_station, reset_index
from stations.places import resolve
from tests.conftest import SMALL_CSV

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _fresh_state():
    """The index is remembered per process, so forget it around every test."""
    places.use_cities_file(None)
    reset_index()
    yield
    reset_index()


def load(csv_path=None) -> None:
    args = ["--csv", str(csv_path)] if csv_path else []
    call_command("load_stations", *args, stdout=StringIO())


def small_csv_plus(tmp_path, extra_row: str):
    path = tmp_path / "stations.csv"
    path.write_text(SMALL_CSV.read_text(encoding="utf-8") + extra_row + "\n", encoding="utf-8")
    return path


def test_ld13_index_is_in_station_id_order_with_exact_prices():
    load(SMALL_CSV)
    index = get_index()
    assert [s.opis_id for s in index.info] == [1, 2, 4, 5]
    assert [s.price for s in index.info] == [
        Decimal("3.40000000"),
        Decimal("3.20000000"),
        Decimal("3.00733333"),
        Decimal("3.10000000"),
    ]


def test_ld14_index_is_remembered(django_assert_num_queries):
    load(SMALL_CSV)
    first = get_index()
    with django_assert_num_queries(0):
        second = get_index()
    assert second is first


def test_ld15_empty_table_is_not_remembered():
    with pytest.raises(StationsNotLoaded):
        get_index()
    load(SMALL_CSV)
    assert len(get_index()) == 4


def test_ld16_nearest_station_and_its_distance():
    load(SMALL_CSV)
    index = get_index()

    k, miles = nearest_station(index, 32.7469, -97.3268)
    assert index.info[k].opis_id == 2
    assert miles == pytest.approx(0.0, abs=0.001)

    k, miles = nearest_station(index, 33.224629, -96.80439)  # 30 miles north of Dallas
    assert index.info[k].opis_id == 1
    assert miles == pytest.approx(30.0, abs=0.05)


def test_ld17_ties_go_to_the_cheaper_then_the_lower_id(tmp_path):
    dallas = resolve("Dallas, TX", "start")

    load(small_csv_plus(tmp_path, "7,FOXTROT,I-30,Dallas,TX,100,3.30000000"))
    index = get_index()
    k, _ = nearest_station(index, dallas.lat, dallas.lng)
    assert index.info[k].opis_id == 7

    reset_index()
    load(small_csv_plus(tmp_path, "7,FOXTROT,I-30,Dallas,TX,100,3.40000000"))
    index = get_index()
    k, _ = nearest_station(index, dallas.lat, dallas.lng)
    assert index.info[k].opis_id == 1


def test_ld18_real_stations_nearest_to_los_angeles_and_new_york():
    load()
    index = get_index()

    los_angeles = resolve("Los Angeles, CA", "start")
    _, miles = nearest_station(index, los_angeles.lat, los_angeles.lng)
    assert miles == pytest.approx(121, rel=0.02)

    new_york = resolve("New York, NY", "start")
    _, miles = nearest_station(index, new_york.lat, new_york.lng)
    assert miles == pytest.approx(3.1, rel=0.02)
