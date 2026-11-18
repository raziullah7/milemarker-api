"""Cases LD-01 to LD-12: the load_stations command, against PostgreSQL."""

import csv
import shutil
from decimal import Decimal
from io import StringIO

import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError

from stations import places
from stations.index import reset_index
from stations.models import FuelStation
from tests.conftest import SMALL_CSV

pytestmark = pytest.mark.django_db

CANADIAN_PROVINCES = {"AB", "BC", "MB", "NB", "NS", "ON", "QC", "SK", "YT"}


@pytest.fixture(autouse=True)
def _fresh_state():
    """Each test starts and ends with the default places table and no remembered index."""
    places.use_cities_file(None)
    reset_index()
    yield
    places.use_cities_file(None)
    reset_index()


def run_loader(*args: str) -> str:
    """Run load_stations and return what it printed."""
    out = StringIO()
    call_command("load_stations", *args, stdout=out)
    return out.getvalue()


def small_csv_plus(tmp_path, extra_row: str):
    """A copy of the small CSV with one more row at the end."""
    path = tmp_path / "stations.csv"
    path.write_text(SMALL_CSV.read_text(encoding="utf-8") + extra_row + "\n", encoding="utf-8")
    return path


def test_ld01_small_csv_counts():
    output = run_loader("--csv", str(SMALL_CSV))
    assert output.splitlines() == [
        "Rows read: 7",
        "Stations: 5",
        "In the lower 48 and DC: 4",
        "Placed from the places table: 3",
        "Placed from hand-added places: 1",
        "Saved: 4",
    ]


def test_ld02_cheapest_listing_wins():
    run_loader("--csv", str(SMALL_CSV))
    station = FuelStation.objects.get(opis_id=1)
    assert station.price == Decimal("3.40000000")
    assert station.name == "ALPHA TWO"


def test_ld03_price_tie_keeps_the_first_row():
    run_loader("--csv", str(SMALL_CSV))
    assert FuelStation.objects.get(opis_id=2).name == "BRAVO"


def test_ld04_city_is_stripped():
    run_loader("--csv", str(SMALL_CSV))
    assert FuelStation.objects.get(opis_id=1).city == "Dallas"


def test_ld05_canadian_station_is_not_saved():
    run_loader("--csv", str(SMALL_CSV))
    assert not FuelStation.objects.filter(opis_id=3).exists()


def test_ld06_price_keeps_every_digit():
    run_loader("--csv", str(SMALL_CSV))
    assert FuelStation.objects.get(opis_id=4).price == Decimal("3.00733333")


def test_ld07_stations_sit_at_their_city_centres():
    run_loader("--csv", str(SMALL_CSV))
    dallas = FuelStation.objects.get(opis_id=1)
    st_louis = FuelStation.objects.get(opis_id=5)
    assert (dallas.lat, dallas.lng) == (32.790439, -96.80439)
    assert (st_louis.lat, st_louis.lng) == pytest.approx((38.638595, -90.257751), abs=1e-6)


def test_ld08_unplaceable_station_fails_and_leaves_the_table_alone(tmp_path):
    run_loader("--csv", str(SMALL_CSV))
    bad_csv = small_csv_plus(tmp_path, "6,FOXTROT,I-35,Nowhereville,TX,100,3.25000000")

    with pytest.raises(CommandError) as caught:
        run_loader("--csv", str(bad_csv))

    assert "station 6 FOXTROT: Nowhereville, TX" in str(caught.value)
    assert sorted(FuelStation.objects.values_list("opis_id", flat=True)) == [1, 2, 4, 5]


def test_ld09_running_twice_replaces_the_table():
    run_loader("--csv", str(SMALL_CSV))
    run_loader("--csv", str(SMALL_CSV))
    assert FuelStation.objects.count() == 4


def test_ld10_csv_and_cities_options_are_read(tmp_path):
    stations_copy = tmp_path / "stations_copy.csv"
    shutil.copy(SMALL_CSV, stations_copy)
    # In the copy of the places table, Dallas sits somewhere the real table never puts it.
    cities_copy = tmp_path / "cities_copy.csv"
    with open(settings.CITIES_CSV, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        if (row["STATE_CODE"], row["CITY"]) == ("TX", "Dallas"):
            row["LATITUDE"], row["LONGITUDE"] = "1.5", "2.5"
    with open(cities_copy, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    run_loader("--csv", str(stations_copy), "--cities", str(cities_copy))

    dallas = FuelStation.objects.get(opis_id=1)
    assert (dallas.lat, dallas.lng) == (1.5, 2.5)
    # The command puts the default table back when it is done.
    assert places.locate_city("Dallas", "TX") == (32.790439, -96.80439)


def test_ld11_real_csv_counts():
    output = run_loader()
    assert output.splitlines() == [
        "Rows read: 8151",
        "Stations: 6738",
        "In the lower 48 and DC: 6626",
        "Placed from the places table: 6615",
        "Placed from hand-added places: 11",
        "Saved: 6626",
    ]
    assert FuelStation.objects.count() == 6626

    saved_ids = set(FuelStation.objects.values_list("opis_id", flat=True))
    dropped_states = set()
    dropped = 0
    with open(settings.STATIONS_CSV, encoding="utf-8-sig", newline="") as f:
        seen = set()
        for row in csv.DictReader(f):
            opis_id = int(row["OPIS Truckstop ID"])
            if opis_id not in saved_ids and opis_id not in seen:
                dropped += 1
                dropped_states.add(row["State"].strip())
            seen.add(opis_id)
    assert dropped == 112
    assert dropped_states == CANADIAN_PROVINCES


def test_ld12_real_csv_facts():
    with open(settings.STATIONS_CSV, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    prices_by_id: dict[str, list[str]] = {}
    for row in rows:
        prices_by_id.setdefault(row["OPIS Truckstop ID"], []).append(row["Retail Price"])

    listed_more_than_once = [p for p in prices_by_id.values() if len(p) > 1]
    at_more_than_one_price = [p for p in listed_more_than_once if len({Decimal(x) for x in p}) > 1]
    padded_cities = [r for r in rows if r["City"] != r["City"].strip()]

    assert len(listed_more_than_once) == 678
    assert len(at_more_than_one_price) == 597
    assert len(padded_cities) == 1256
