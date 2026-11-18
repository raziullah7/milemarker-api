"""The health address, GET /api/v1/health/: cases HS-01, HS-02, HS-06 to HS-08 and the health
part of HS-10 of docs/test-cases.md, section 9.4; and QB-17 of section 9.13, the lock around
reading the station index, which health and the route share. HS-03 to HS-05, health on
Redis, are in tests/test_cache.py.

The cache is the in-memory one (REDIS_URL unset), and the stations come from PostgreSQL.
"""

import json
import threading
import time
from io import StringIO

import pytest
from django.core.management import call_command
from django.db import connection

from stations import index
from stations.index import get_index, reset_index
from tests.conftest import SMALL_CSV
from tests.test_api import URL, assert_error

HEALTH = "/api/v1/health/"
ROUTING_FREE = {"start": "Dallas, TX"}


@pytest.fixture(autouse=True)
def _fresh_index():
    """Each case starts as a process that has not read the stations yet."""
    reset_index()
    yield
    reset_index()


def load_small_csv() -> None:
    call_command("load_stations", "--csv", str(SMALL_CSV), stdout=StringIO())


@pytest.mark.django_db
def test_hs01_health_answers_ok_with_the_count_and_the_cache(client):
    load_small_csv()
    response = client.get(HEALTH)

    assert response.status_code == 200
    assert json.loads(response.content) == {"status": "ok", "stations": 4, "cache": "memory"}


def test_hs02_health_counts_the_real_stations(client, use_real_stations):
    assert json.loads(client.get(HEALTH).content)["stations"] == 6626


@pytest.mark.django_db
def test_hs06_no_stations_is_503_until_they_are_loaded(client):
    response = client.get(HEALTH)
    assert assert_error(response, "stations_not_loaded") == {}

    load_small_csv()
    response = client.get(HEALTH)
    assert response.status_code == 200
    assert json.loads(response.content)["stations"] == 4


@pytest.mark.django_db
def test_hs07_health_reads_the_stations_once(client, django_assert_num_queries):
    load_small_csv()

    with django_assert_num_queries(1):
        first = client.get(HEALTH)
    with django_assert_num_queries(0):
        second = client.get(HEALTH)
    for response in (first, second):
        assert response.status_code == 200
        assert json.loads(response.content)["stations"] == 4


@pytest.mark.django_db
def test_hs08_health_is_never_rate_limited(client):
    load_small_csv()

    assert {client.get(HEALTH).status_code for _ in range(100)} == {200}
    statuses = [client.get(URL, ROUTING_FREE).status_code for _ in range(61)]
    assert 429 not in statuses[:60]
    assert statuses[60] == 429
    assert client.get(HEALTH).status_code == 200


@pytest.mark.django_db
def test_hs10_health_answers_only_get(client):
    assert assert_error(client.post(HEALTH), "method_not_allowed") == {}


@pytest.mark.django_db(transaction=True)
def test_qb17_two_first_requests_read_the_stations_once(monkeypatch):
    """Review 9-Q0b, note N8. Two threads that both find no index yet must not each read
    the table. Building the index is slowed here, so without the lock both threads would
    be reading at the same time."""
    load_small_csv()
    built = []
    real_build = index.build_index

    def slow_build(stations):
        time.sleep(0.2)
        built.append(real_build(stations))
        return built[-1]

    monkeypatch.setattr(index, "build_index", slow_build)
    start_together = threading.Barrier(2)
    got = []

    def first_request() -> None:
        start_together.wait()
        try:
            got.append(get_index())
        finally:
            connection.close()

    threads = [threading.Thread(target=first_request) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(built) == 1
    assert got == [built[0], built[0]]
