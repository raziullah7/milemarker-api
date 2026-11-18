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
def use_real_stations(real_index, monkeypatch):
    """Make get_index() return the real stations for one test, without touching the database."""
    from stations import index

    monkeypatch.setattr(index, "_index", real_index)
    return real_index
