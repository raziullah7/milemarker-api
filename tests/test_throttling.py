"""The rate limit, trips/throttling.py: 60 requests a minute for each client, each counted with
one atomic step, in a window that opens with the client's first request (architecture
section 10, "The rate-limit counter"; NFR-16; review QA-1, finding Q1-01).

These run on the in-memory cache, as the rest of the suite does. The same limit on Redis,
across two worker processes, is in tests/test_cache.py, with the limit during a fallback.
EP-34 (tests/test_api.py), HS-08 and HS-09 hold the rest: 61 requests in order, health
never limited, and the schema and docs counted with the route.
"""

import threading
import time
import types

import pytest
from django.conf import settings
from django.core.cache.backends import locmem
from django.test import Client

from tests.test_api import URL, assert_error

# Answered 400 invalid_request before any place lookup or routing call (section 9.1). The
# limit is checked before the parameters, so each one is counted.
ROUTING_FREE = {"start": "Dallas, TX"}


def status(client, **extra) -> int:
    """The status of one request that is counted but needs no stations or road."""
    return client.get(URL, ROUTING_FREE, **extra).status_code


class Clock:
    """time.time() moved on by the test instead of waited for: the limiter's clock and the
    in-memory cache's, which decides when a key has expired, alike."""

    def __init__(self, monkeypatch):
        self.moved = 0.0
        real = time.time
        monkeypatch.setattr(time, "time", lambda: real() + self.moved)

    def advance(self, seconds: float) -> None:
        self.moved += seconds


@pytest.fixture
def clock(monkeypatch) -> Clock:
    return Clock(monkeypatch)


def test_the_settings_name_this_limiter_at_the_same_rate():
    from trips.throttling import FixedWindowThrottle
    from trips.views import RouteView

    assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] == [
        "trips.throttling.FixedWindowThrottle"
    ]
    assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] == {"anon": "60/min"}
    [throttle] = RouteView().get_throttles()
    assert type(throttle) is FixedWindowThrottle
    assert (throttle.num_requests, throttle.duration) == (60, 60)


def slowed(operation):
    """A cache operation that first lets the other threads run, so that requests sent at once
    interleave between any two steps of the cache."""

    def slow(*args, **kwargs):
        time.sleep(0.002)
        return operation(*args, **kwargs)

    return slow


def at_once(requests: int, threads: int) -> list[int]:
    """The statuses of `requests` requests from one client, sent by `threads` threads that
    start together, each with a client of its own."""
    together = threading.Barrier(threads)
    statuses: list[int] = []

    def send() -> None:
        own = Client()
        together.wait()
        for _ in range(requests // threads):
            statuses.append(status(own))

    senders = [threading.Thread(target=send) for _ in range(threads)]
    for sender in senders:
        sender.start()
    for sender in senders:
        sender.join()
    return statuses


def test_a_burst_from_one_client_passes_exactly_60(monkeypatch):
    """Q1-01: many requests of one client at once. Every step of the in-memory cache is
    slowed, so the threads interleave between any two of them: the framework's limiter, which
    reads a client's history and writes it back, then counts most of them as one."""
    for name in ("get", "add", "set", "incr"):
        monkeypatch.setattr(locmem.LocMemCache, name, slowed(getattr(locmem.LocMemCache, name)))

    statuses = at_once(100, threads=20)

    assert len(statuses) == 100
    assert (statuses.count(400), statuses.count(429)) == (60, 40)


def test_the_window_opens_with_the_first_request_and_lasts_60_seconds(client, clock):
    assert status(client) == 400  # the window opens at T
    clock.advance(30)
    assert 429 not in [status(client) for _ in range(59)]
    assert status(client) == 429  # the 61st inside the window

    clock.advance(30)  # T + 60: the window is over, whenever its requests came
    statuses = [status(client) for _ in range(61)]
    assert 429 not in statuses[:60]
    assert statuses[60] == 429


def test_the_wait_is_the_time_left_in_the_window(client, clock):
    assert status(client) == 400  # the window opens at T
    clock.advance(20.5)
    assert 429 not in [status(client) for _ in range(59)]

    response = client.get(URL, ROUTING_FREE)
    # 39.5 seconds are left, given in whole seconds, rounded up.
    assert assert_error(response, "rate_limited") == {"retry_after_seconds": 40}
    assert response["Retry-After"] == "40"


def test_the_wait_is_at_least_a_second(client, monkeypatch):
    """Redis keeps time by its own clock, so it can still hold a window that the API's clock
    says is over. Here the limiter's clock runs half a second past the window's end while the
    cache still holds it: the wait is 1 second, not 0 or less."""
    assert 429 not in [status(client) for _ in range(60)]
    real = time.time
    monkeypatch.setattr("trips.throttling.time", types.SimpleNamespace(time=lambda: real() + 60.5))

    response = client.get(URL, ROUTING_FREE)
    assert assert_error(response, "rate_limited") == {"retry_after_seconds": 1}
    assert response["Retry-After"] == "1"


def test_two_clients_do_not_share_a_count(client):
    assert 429 not in [status(client) for _ in range(60)]
    assert status(client) == 429

    assert status(client, REMOTE_ADDR="203.0.113.2") == 400
    assert status(client) == 429
