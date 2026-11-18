"""Shared test helpers.

No test may reach beyond this machine: pytest-socket (see pyproject.toml) fails any test
that opens a connection to anything but localhost. Roads come from recorded answers in
tests/fixtures/roads, and the routing service is always replaced by a fake.
"""

import gzip
import json
from pathlib import Path

import numpy as np
import pytest
from django.core.cache import cache
from django.test import override_settings

FIXTURES = Path(__file__).parent / "fixtures"
SMALL_CSV = FIXTURES / "stations_small.csv"
METRES_PER_MILE = 1609.344

# Recorded answers from the OSRM public server, by short name.
ROADS = {
    "nyc_la": "New York to Los Angeles",
    "sea_mia": "Seattle to Miami",
    "bos_sea": "Boston to Seattle",
    "chi_hou": "Chicago to Houston",
    "dal_hou": "Dallas to Houston",
    "bos_dc": "Boston to Washington",
    "det_buf": "Detroit to Buffalo (through Ontario)",
    "det_bos": "Detroit to Boston (through Ontario)",
    "det_porthuron": "Detroit to Port Huron",
    "elpaso_delrio": "El Paso to Del Rio",
    "houlton_madawaska": "Houlton to Madawaska",
    "intlfalls_baudette": "International Falls to Baudette",
    "keywest_miami": "Key West to Miami",
    "laredo_brownsville": "Laredo to Brownsville",
    "montauk_nyc": "Montauk to New York",
    "sandiego_calexico": "San Diego to Calexico",
    "sea_blaine": "Seattle to Blaine",
    # Added for the end-to-end run: the trips of the Postman collection that had no recording.
    "la_nyc": "Los Angeles to New York",
    "stl_winstonsalem": "St. Louis to Winston-Salem",
    "dal_phx": "Dallas to Phoenix",
    "la_sea": "Los Angeles to Seattle (no fuel listed along it)",
}


def load_road_answer(name: str) -> dict:
    """The routing service's whole recorded answer for a road, as parsed JSON."""
    with gzip.open(FIXTURES / "roads" / f"{name}.json.gz", "rt", encoding="utf-8") as f:
        return json.load(f)


def load_road(name: str) -> tuple[np.ndarray, float]:
    """A recorded road as (coords, distance_miles). coords has rows of [lng, lat]."""
    route = load_road_answer(name)["routes"][0]
    coords = np.array(route["geometry"]["coordinates"], dtype=float)
    return coords, route["distance"] / METRES_PER_MILE


@pytest.fixture(scope="session", autouse=True)
def _in_memory_cache():
    """The whole suite runs on the in-memory cache, as the API does with REDIS_URL unset, even
    when REDIS_URL is set where the tests run. The fixture below empties the cache around
    every test, which on a shared Redis would flush it. Only the Redis tests use Redis
    (tests/test_cache.py), on a cache object of their own, in database 15."""
    from django.conf import settings

    memory = {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "TIMEOUT": settings.TRIP_CACHE_SECONDS,
        "VERSION": settings.CACHE_KEY_VERSION,
        "OPTIONS": {"MAX_ENTRIES": 500},
    }
    with override_settings(CACHES={"default": memory}):
        yield


@pytest.fixture(autouse=True)
def _empty_cache():
    """Each test starts with empty caches, so cached trips and rate-limit counts never leak."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(scope="session")
def real_index():
    """Every station in the supplied CSV, as the loader would place it, built without the
    database. Read once for the whole test run."""
    from django.conf import settings

    from stations import places
    from stations.management.commands.load_stations import (
        cheapest_listing_per_station,
        read_rows,
        station_fields,
    )
    from stations.types import StationInfo, build_index

    stations = []
    for row in cheapest_listing_per_station(read_rows(settings.STATIONS_CSV)):
        position = places.locate_city(row["City"], row["State"])
        if row["State"] in places.COVERED_STATES and position is not None:
            fields = station_fields(row)
            fields.pop("rack_id")
            stations.append((StationInfo(**fields), *position))
    return build_index(stations)


@pytest.fixture
def ep01_world(db, monkeypatch):
    """EP-01's world (docs/test-cases.md, section 2.10), for the tests of release 2: its four
    stations in the table, the station index read afresh, and a fake routing service that
    returns its 990-mile test road. Returns the fake, which counts its calls."""
    from stations.index import reset_index
    from tests.test_api import DALLAS, FakeRouting, add_station, on_road, straight_road
    from trips.services import routing

    reset_index()
    add_station(1, "3.20", *DALLAS, name="DALLAS START")
    for opis_id, mile, price in ((2, 200, "3.10"), (3, 450, "3.00"), (4, 700, "3.20")):
        add_station(opis_id, price, *on_road(mile))
    fake = FakeRouting(*straight_road(990.0))
    monkeypatch.setattr(routing, "fetch_route", fake)
    yield fake
    reset_index()


@pytest.fixture
def use_real_stations(real_index, monkeypatch):
    """Make get_index() return the real stations for one test, without touching the database."""
    from stations import index

    monkeypatch.setattr(index, "_index", real_index)
    return real_index
