"""The cache on Redis, and its fallback to each process's own memory: cases CA-01 to CA-19
and CA-24, and the health answers that depend on Redis, HS-03 to HS-05, of
docs/test-cases.md, sections 9.3 and 9.4.

The rest of the suite runs on the in-memory cache (tests/conftest.py). These tests build the
API's own cache, config.cache.RedisWithFallback, on database 15 of the Redis at
REDIS_TEST_URL (default redis://127.0.0.1:6379/15), and flush that database and no other.
The Redis must be running: a test that cannot reach it fails, it is never skipped.

The Redises of section 9.1, all on 127.0.0.1, the one address the suite may connect to:

- live: database 15 of the real Redis;
- refusing: a port nothing listens on;
- silent: a listener that accepts connections, never answers, and counts them;
- switchable: a forwarder in front of the live Redis that can be switched off.

"Two processes" are two real Python processes (tests/cache_worker.py), each running the
application with REDIS_URL set to one of them. "At T + 30 s" moves the cache's clock on.
"""

import importlib.util
import json
import os
import pickle
import socket
import subprocess
import sys
import threading
import time
import types
from decimal import Decimal
from pathlib import Path

import pytest
import redis
from django.core.cache import caches

import config.cache
from tests.test_api import TRIP, URL, read, without_meta
from trips.services import routing

ROOT = Path(__file__).resolve().parent.parent
LIVE = os.environ.get("REDIS_TEST_URL", "redis://127.0.0.1:6379/15")
REFUSING = "redis://127.0.0.1:1/15"
HEALTH = "/api/v1/health/"
# Answered 400 invalid_request before any place lookup or routing call (section 9.1).
ROUTING_FREE = {"start": "Dallas, TX"}


# --- The Redises ----------------------------------------------------------------------


def redis_db(number: int) -> redis.Redis:
    """A client of database `number` of the live Redis. (A db argument would not do: the
    database in the address takes precedence over it.)"""
    return redis.Redis.from_url(f"{LIVE.rsplit('/', 1)[0]}/{number}")


@pytest.fixture
def live():
    """A client of the live Redis's database 15, emptied before and after the test."""
    client = redis.Redis.from_url(LIVE)
    # Never anything but database 15: the tests flush it.
    assert client.connection_pool.connection_kwargs["db"] == 15, LIVE
    client.flushdb()
    yield client
    client.flushdb()
    client.close()


def _live_address() -> tuple[str, int]:
    """The live Redis's host and port."""
    kwargs = redis.Redis.from_url(LIVE).connection_pool.connection_kwargs
    return kwargs["host"], kwargs["port"]


class SilentRedis:
    """A listener on 127.0.0.1 that accepts connections, never answers, and counts them.
    It stands for a Redis that hangs."""

    def __init__(self):
        self.server = socket.create_server(("127.0.0.1", 0))
        self.url = f"redis://127.0.0.1:{self.server.getsockname()[1]}/15"
        self.connections = 0
        self.held: list[socket.socket] = []
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self) -> None:
        """Take every connection and keep it open, saying nothing."""
        while True:
            try:
                connection, _ = self.server.accept()
            except OSError:
                return
            self.connections += 1
            self.held.append(connection)

    def close(self) -> None:
        """Stop listening and drop every connection held."""
        self.server.close()
        for connection in self.held:
            connection.close()


class SwitchableRedis:
    """A forwarder on 127.0.0.1 in front of the live Redis. Switched on, it passes each
    connection through. Switched off, it closes each new connection at once and counts it,
    and drops every connection it was passing through."""

    def __init__(self):
        self.server = socket.create_server(("127.0.0.1", 0))
        self.url = f"redis://127.0.0.1:{self.server.getsockname()[1]}/15"
        self.on = False
        self.refused = 0
        self.open: list[socket.socket] = []
        threading.Thread(target=self._accept, daemon=True).start()

    def switch(self, on: bool) -> None:
        """Switch on or off. Switching off drops the connections passed through so far."""
        self.on = on
        if not on:
            for connection in self.open:
                connection.close()
            self.open = []

    def _accept(self) -> None:
        """Pass each connection through, or close it at once."""
        while True:
            try:
                client, _ = self.server.accept()
            except OSError:
                return
            if not self.on:
                self.refused += 1
                client.close()
                continue
            upstream = socket.create_connection(_live_address())
            self.open += [client, upstream]
            for source, target in ((client, upstream), (upstream, client)):
                threading.Thread(target=self._pump, args=(source, target), daemon=True).start()

    @staticmethod
    def _pump(source: socket.socket, target: socket.socket) -> None:
        """Copy bytes one way until either side closes."""
        try:
            while data := source.recv(65536):
                target.sendall(data)
        except OSError:
            pass
        for side in (source, target):
            side.close()

    def close(self) -> None:
        """Stop listening and drop every connection."""
        self.switch(False)
        self.server.close()


@pytest.fixture
def silent():
    server = SilentRedis()
    yield server
    server.close()


@pytest.fixture
def switchable(live):
    server = SwitchableRedis()
    yield server
    server.close()


# --- This process on Redis --------------------------------------------------------------


@pytest.fixture
def use_redis(settings, monkeypatch):
    """use_redis(url): from now on this test's process runs on the API's own cache class at
    `url`, set up exactly as config/settings.py sets it up when REDIS_URL is `url`, with a
    fresh per-process state: no fallback, no warning given yet, an empty own memory."""
    monkeypatch.setattr(config.cache, "_processes", {})

    def use(url: str) -> None:
        monkeypatch.setenv("REDIS_URL", url)
        spec = importlib.util.spec_from_file_location(
            "settings_under_test", ROOT / "config" / "settings.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        settings.CACHES = module.CACHES

    return use


class Clock:
    """The cache's clock, moved on by the test instead of waited for."""

    def __init__(self, monkeypatch):
        self.moved = 0.0
        monkeypatch.setattr(
            config.cache,
            "time",
            types.SimpleNamespace(monotonic=lambda: time.monotonic() + self.moved),
        )

    def advance(self, seconds: float) -> None:
        self.moved += seconds


@pytest.fixture
def clock(monkeypatch) -> Clock:
    return Clock(monkeypatch)


def fallback_lines(caplog) -> list[str]:
    """What config/cache.py logged, as (level, message) pairs."""
    return [
        (r.levelname, r.getMessage()) for r in caplog.records if r.name == config.cache.__name__
    ]


# --- Two processes ----------------------------------------------------------------------

WORKER = ROOT / "tests" / "cache_worker.py"


class Worker:
    """One process standing for one API worker, on the Redis at `url` (tests/cache_worker.py)."""

    def __init__(self, url: str, log: Path, key_version: int | None = None):
        self.log = log
        self.log_file = log.open("w", encoding="utf-8")
        args = [sys.executable, str(WORKER)] + ([str(key_version)] if key_version else [])
        self.process = subprocess.Popen(
            args,
            cwd=ROOT,
            env=os.environ | {"DJANGO_SETTINGS_MODULE": "config.settings", "REDIS_URL": url},
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.log_file,
            text=True,
        )

    def _ask(self, command: dict) -> dict:
        self.process.stdin.write(json.dumps(command) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        assert line, self.log.read_text(encoding="utf-8")
        return json.loads(line)

    def get(self, params: dict = TRIP, path: str = URL) -> dict:
        """One request: {"status", "body", "calls"}, calls being its fake's routing calls so far."""
        return self._ask({"get": path, "params": params})

    def advance(self, seconds: float) -> None:
        """Move its cache's clock on."""
        self._ask({"advance": seconds})

    def burst(self, threads: int, each: int, params: dict = ROUTING_FREE) -> list[int]:
        """`each` requests from each of `threads` threads that start together; their statuses."""
        command = {"burst": URL, "params": params, "threads": threads, "each": each}
        return self._ask(command)["statuses"]

    def stop(self) -> str:
        """End the process; return its log."""
        if self.process.poll() is None:
            self.process.stdin.close()
            self.process.wait(timeout=30)
        self.process.stdout.close()
        self.log_file.close()
        return self.log.read_text(encoding="utf-8")


@pytest.fixture
def workers(tmp_path):
    """workers(url, key_version=None): start one more worker process on the Redis at `url`."""
    started: list[Worker] = []

    def start(url: str, key_version: int | None = None) -> Worker:
        started.append(Worker(url, tmp_path / f"worker-{len(started)}.log", key_version))
        return started[-1]

    yield start
    for worker in started:
        worker.stop()


def meta(answer: dict) -> tuple[int, bool]:
    """(routing_calls, cache_hit) of a worker's 200."""
    assert answer["status"] == 200, answer
    return answer["body"]["meta"]["routing_calls"], answer["body"]["meta"]["cache_hit"]


def warnings_in(log: str) -> list[str]:
    """The fallback warnings in a worker's log."""
    return [line for line in log.splitlines() if " WARNING " in line and "config.cache" in line]


# --- CA-01 to CA-05: shared by every worker, and never stale ---------------------------


def test_ca01_a_trip_planned_by_one_worker_is_a_hit_on_the_other(live, workers):
    a, b = workers(LIVE), workers(LIVE)
    first = a.get()
    second = b.get()

    assert meta(first) == (1, False)
    assert meta(second) == (0, True)
    assert second["calls"] == 0
    assert without_meta(second["body"]) == without_meta(first["body"])


def test_ca02_the_road_is_shared_too(live, workers):
    a, b = workers(LIVE), workers(LIVE)
    a.get()
    other_stop_cost = b.get(TRIP | {"stop_cost": "0"})

    assert meta(other_stop_cost) == (0, False)
    assert other_stop_cost["calls"] == 0


def test_ca03_a_new_key_version_reads_nothing_cached_under_the_old(live, workers, settings):
    version = settings.CACHE_KEY_VERSION
    a, b = workers(LIVE), workers(LIVE, key_version=version + 1)
    a.get()
    answer = b.get()

    assert meta(answer) == (1, False)
    assert answer["calls"] == 1
    keys = [key.decode() for key in live.keys("*")]
    assert keys
    assert {key.split(":")[1] for key in keys} == {str(version), str(version + 1)}


def test_ca04_new_prices_are_never_served_from_an_old_answer(live, use_redis, client, ep01_world):
    from stations.index import reset_index
    from stations.models import FuelStation

    use_redis(LIVE)
    assert read(client.get(URL, TRIP))["meta"]["cache_hit"] is False

    FuelStation.objects.filter(opis_id=4).update(price=Decimal("3.15"))
    reset_index()
    repriced = read(client.get(URL, TRIP))
    assert (repriced["meta"]["routing_calls"], repriced["meta"]["cache_hit"]) == (0, False)
    [stop] = [s for s in repriced["fuel_stops"] if s["mile_marker"] == 700]
    assert stop["price_per_gallon"] == Decimal("3.15")

    reset_index()  # read again, with no change
    assert read(client.get(URL, TRIP))["meta"]["cache_hit"] is True


def test_ca05_an_answer_outlives_the_process_that_made_it(live, workers):
    a = workers(LIVE)
    assert meta(a.get()) == (1, False)
    a.stop()

    c = workers(LIVE)
    answer = c.get()
    assert meta(answer) == (0, True)
    assert answer["calls"] == 0


# --- CA-06 to CA-13: when Redis cannot be reached ---------------------------------------


def test_ca06_a_refused_redis_costs_no_request(use_redis, client, ep01_world):
    in_memory = read(client.get(URL, TRIP))
    caches["default"].clear()
    use_redis(REFUSING)

    first = client.get(URL, TRIP)
    second = client.get(URL, TRIP)

    assert (first.status_code, second.status_code) == (200, 200)
    assert read(first)["meta"]["routing_calls"] == 1
    assert without_meta(read(first)) == without_meta(in_memory)
    assert read(second)["meta"]["cache_hit"] is True  # from this process's own memory


def timed_get(client, params: dict = TRIP) -> tuple[float, object]:
    """(seconds, response) of one request."""
    started = time.perf_counter()
    response = client.get(URL, params)
    return time.perf_counter() - started, response


def test_ca07_a_hung_redis_adds_at_most_half_a_second(live, silent, use_redis, client, ep01_world):
    use_redis(LIVE)
    with_redis_up, response = timed_get(client)
    assert response.status_code == 200

    use_redis(silent.url)  # a fresh, empty memory: the same work as the request above
    with_redis_hung, response = timed_get(client)

    assert response.status_code == 200
    assert with_redis_hung <= with_redis_up + 0.5, (with_redis_hung, with_redis_up)


def test_ca08_after_the_first_request_a_hung_redis_is_left_alone(
    silent, use_redis, client, ep01_world
):
    use_redis(silent.url)
    timings = []
    for n in range(20):
        # New trips (another stop cost) and repeats, in turn.
        seconds, response = timed_get(client, TRIP | {"stop_cost": str(n // 2)})
        assert response.status_code == 200
        timings.append(seconds)
        assert silent.connections == 1

    # Requests 2 to 20 do not wait for Redis: each takes less than one command timeout.
    assert max(timings[1:]) < 0.25, timings


def test_ca09_redis_is_tried_again_every_30_seconds(silent, use_redis, client, clock, ep01_world):
    use_redis(silent.url)
    client.get(URL, ROUTING_FREE)  # falls back at T
    assert silent.connections == 1

    seen = []
    for at in (1, 29, 30, 59, 60):
        clock.advance(at - clock.moved)
        before = silent.connections
        assert client.get(URL, ROUTING_FREE).status_code == 400
        seen.append(silent.connections - before)

    assert seen == [0, 0, 1, 0, 1]


def test_ca10_back_on_redis_after_30_seconds(switchable, workers):
    a, b = workers(switchable.url), workers(switchable.url)
    assert a.get(ROUTING_FREE)["status"] == 400  # A falls back at T

    switchable.switch(True)
    assert meta(b.get()) == (1, False)  # B caches the answer in Redis
    a.advance(30)
    answer = a.get()
    health = a.get({}, path=HEALTH)

    assert meta(answer) == (0, True)  # from Redis: A's own memory never held it
    assert answer["calls"] == 0
    assert health["body"]["cache"] == "redis"
    log = a.stop()
    assert len(warnings_in(log)) == 1
    assert (
        len([line for line in log.splitlines() if " INFO " in line and "config.cache" in line]) == 1
    )


def test_ca11_one_warning_per_outage(switchable, use_redis, client, clock, caplog, ep01_world):
    use_redis(switchable.url)
    for _ in range(10):
        assert client.get(URL, TRIP).status_code == 200
    clock.advance(30)
    assert client.get(URL, TRIP).status_code == 200  # the try fails
    assert [level for level, _ in fallback_lines(caplog)] == ["WARNING"]

    switchable.switch(True)
    clock.advance(30)
    assert client.get(URL, TRIP).status_code == 200
    switchable.switch(False)
    assert client.get(URL, TRIP).status_code == 200

    assert [level for level, _ in fallback_lines(caplog)] == ["WARNING", "INFO", "WARNING"]


def test_ca12_each_worker_logs_one_warning(switchable, workers):
    a, b = workers(switchable.url), workers(switchable.url)
    for worker in (a, b):
        for _ in range(5):
            assert worker.get()["status"] == 200

    assert [len(warnings_in(worker.stop())) for worker in (a, b)] == [1, 1]


def test_ca13_with_redis_url_unset_redis_is_never_touched(client, caplog, monkeypatch, ep01_world):
    connections = []
    monkeypatch.setattr(
        redis.connection.AbstractConnection, "connect", lambda self: connections.append(self)
    )

    client.get(URL, TRIP)
    second = read(client.get(URL, TRIP))

    assert second["meta"]["cache_hit"] is True
    assert connections == []
    assert fallback_lines(caplog) == []
    assert json.loads(client.get(HEALTH).content)["cache"] == "memory"


# --- CA-14 and CA-15: the rate-limit counters --------------------------------------------


def test_ca14_the_rate_limit_is_counted_across_workers(live, workers):
    a, b = workers(LIVE), workers(LIVE)
    statuses = [a.get(ROUTING_FREE)["status"] for _ in range(30)]
    statuses += [b.get(ROUTING_FREE)["status"] for _ in range(30)]

    assert 429 not in statuses
    assert a.get(ROUTING_FREE)["status"] == 429


def test_ca15_during_an_outage_each_worker_counts_alone(workers):
    a, b = workers(REFUSING), workers(REFUSING)
    statuses = [a.get(ROUTING_FREE)["status"] for _ in range(61)]

    assert 429 not in statuses[:60]
    assert statuses[60] == 429
    assert b.get(ROUTING_FREE)["status"] == 400


def test_a_burst_across_two_workers_passes_exactly_60(live, workers):
    """Q1-01: one client's requests at once, on two worker processes of eight threads each,
    sharing the live Redis. The framework's limiter read a client's history and wrote it back,
    so requests sent together overwrote each other's entries: the review saw 164 of 300 pass."""
    a, b = workers(LIVE), workers(LIVE)
    for worker in (a, b):  # each on Redis, its connections made, before the burst
        assert worker.get({}, path=HEALTH)["body"]["cache"] == "redis"

    statuses: dict[str, list[int]] = {}
    senders = [
        threading.Thread(target=lambda n=name, w=worker: statuses.update({n: w.burst(8, 8)}))
        for name, worker in (("a", a), ("b", b))
    ]
    for sender in senders:
        sender.start()
    for sender in senders:
        sender.join()

    for worker in (a, b):  # neither fell back, so neither counted alone
        assert worker.get({}, path=HEALTH)["body"]["cache"] == "redis"
    both = statuses["a"] + statuses["b"]
    assert len(both) == 128
    assert (both.count(400), both.count(429)) == (60, 68)


def test_the_rate_limit_keys_expire_in_redis(live, use_redis, client):
    """Q1-01: the window's start lives as long as the window, and the count longer, so the
    count cannot expire under an increment. Django's Redis increment checks that the key
    exists and then increments it; a key that expired in between would come back with no
    expiry at all."""
    use_redis(LIVE)
    for _ in range(3):
        assert client.get(URL, ROUTING_FREE).status_code == 400

    keys = [key.decode() for key in live.keys("*")]
    [start] = [key for key in keys if "throttle_anon_start_" in key]
    [count] = [key for key in keys if "throttle_anon_count_" in key]
    assert 0 < live.ttl(start) <= 60 < live.ttl(count) <= 120
    assert int(live.get(count)) == 3


@pytest.mark.parametrize("on_redis", [True, False], ids=["redis", "own memory"])
def test_incr_is_one_atomic_step_on_redis_and_on_the_fallback(live, monkeypatch, on_redis):
    """Q1-01: the limiter counts with incr. The class used to build it from a read and a
    write, so increments sent at once were lost; now it passes incr through to Redis's own,
    and to its memory's, each atomic."""
    monkeypatch.setattr(config.cache, "_processes", {})
    cache = config.cache.RedisWithFallback(LIVE if on_redis else REFUSING, PARAMS)
    assert cache.add("count", 0) is True
    together = threading.Barrier(8)

    def count() -> None:
        together.wait()
        for _ in range(50):
            cache.incr("count")

    threads = [threading.Thread(target=count) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert cache.get("count") == 400
    assert cache.decr("count", 400) == 0
    with pytest.raises(ValueError, match="not found"):
        cache.incr("never-set")
    # A key that is not held is an answer, not a failure of Redis.
    assert cache.falling_back is not on_redis


# --- CA-16 to CA-19 and CA-24 -------------------------------------------------------------


def redis_keys() -> dict[int, set[bytes]]:
    """The key names in databases 0 to 14 of the live Redis."""
    return {db: set(redis_db(db).keys("*")) for db in range(15)}


def unchanged(before: dict, after: dict) -> bool:
    """Whether no database but 15 gained a key between the two looks. Names are compared,
    not counts: a key that expired in between is no change (Q1-06)."""
    return all(after[db] <= before[db] for db in before)


@pytest.fixture(scope="module", autouse=True)
def canary():
    """CA-16: a key placed in database 0 before the Redis tests is still there after them,
    and no database but 15 gained a key while they ran."""
    zero = redis_db(0)
    before = redis_keys()
    zero.set("canary", "still here")
    yield
    assert zero.get("canary") == b"still here"
    zero.delete("canary")
    assert unchanged(before, redis_keys())


def test_ca16_a_key_that_expires_while_the_tests_run_is_no_change():
    """Q1-06: the stack's own keys can expire while the suite runs, a rate-limit count a
    minute after the stack was last used above all. That is no change; a key that was not
    there before is. Database 14, which nothing uses; each key lives a second or two, longer
    than one look at the fifteen databases."""
    fourteen = redis_db(14)
    fourteen.set("ca16-expires", "x", px=1000)
    try:
        before = redis_keys()
        while fourteen.exists("ca16-expires"):  # which also removes it, once expired
            time.sleep(0.05)
        assert unchanged(before, redis_keys())

        fourteen.set("ca16-new", "x", px=2000)
        assert not unchanged(before, redis_keys())
    finally:
        fourteen.delete("ca16-expires", "ca16-new")


def test_a_redis_that_answers_with_an_error_costs_no_request(use_redis, client, caplog, ep01_world):
    """Q1-03: every error of the Redis client falls back as a refused connection does, not
    only a refused connection or a timeout. Here Redis answers with an error, because the
    database asked for does not exist (Redis has 16)."""
    use_redis(f"{LIVE.rsplit('/', 1)[0]}/99")

    first = client.get(URL, TRIP)
    second = client.get(URL, TRIP)

    assert (first.status_code, second.status_code) == (200, 200)
    assert read(second)["meta"]["cache_hit"] is True  # from this process's own memory
    assert health(client)["cache"] == "fallback"
    assert [level for level, _ in fallback_lines(caplog)] == ["WARNING"]


def test_a_cached_value_that_cannot_be_read_back_is_not_caught(live, monkeypatch):
    """The ruling on Q1-03 stops at errors of the Redis client. A value that can no longer be
    read after a change of code is left to raise: CACHE_KEY_VERSION exists for that, and
    catching every error of a read would hide real faults."""
    monkeypatch.setattr(config.cache, "_processes", {})
    cache = config.cache.RedisWithFallback(LIVE, PARAMS)
    live.set(":1:unreadable", b"not a pickle")

    with pytest.raises(pickle.UnpicklingError):
        cache.get("unreadable")
    assert not cache.falling_back


def test_a_late_answer_to_a_call_sent_before_the_outage_does_not_end_it(monkeypatch, caplog):
    """Q1-04, the review's sequence. Call a goes to Redis just before the outage and is slow.
    Call b, sent after it, is refused, and the process falls back. Then a's answer comes. Only
    the try made after the 30 seconds can end a fallback: a's answer changes nothing, and the
    next call keeps to memory. No real Redis: a stand-in answers the calls."""
    monkeypatch.setattr(config.cache, "_processes", {})
    cache = config.cache.RedisWithFallback(REFUSING, PARAMS)
    sent, fallen_back = threading.Event(), threading.Event()
    asked = []

    class StandIn:
        """Django's Redis cache, as the outage begins: the first call is slow and answers,
        every later one is refused."""

        def get(self, key, default=None, version=None):
            asked.append(key)
            if len(asked) > 1:
                raise redis.exceptions.ConnectionError("Connection refused.")
            sent.set()
            fallen_back.wait(timeout=0.35)  # within the 0.4-second deadline
            return "from Redis"

    monkeypatch.setattr(cache, "_redis", StandIn())
    answers = {}
    a = threading.Thread(target=lambda: answers.update(a=cache.get("a")))
    a.start()
    assert sent.wait(timeout=1)
    assert cache.get("b", "from memory") == "from memory"
    fallen_back.set()
    a.join()

    assert answers["a"] == "from Redis"
    assert cache.falling_back
    assert cache.get("c", "from memory") == "from memory"
    assert asked == ["a", "b"]  # c did not touch Redis
    assert [level for level, _ in fallback_lines(caplog)] == ["WARNING"]


def test_ca17_redis_url_set_for_the_whole_suite_flushes_nothing():
    """A pytest of its own, with REDIS_URL naming database 0 of the live Redis: the fixture
    that empties the cache around every test runs, and database 0 keeps its canary,
    because the suite runs on the in-memory cache whatever REDIS_URL says."""
    zero = redis_db(0)
    zero.set("canary-17", "still here")
    try:
        result = subprocess.run(
            [
                *(sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q"),
                "tests/test_sphere.py",
                "tests/test_project.py::test_the_suite_runs_on_the_in_memory_cache",
            ],
            cwd=ROOT,
            env=os.environ | {"REDIS_URL": f"{LIVE.rsplit('/', 1)[0]}/0"},
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert zero.get("canary-17") == b"still here"
    finally:
        zero.delete("canary-17")


def test_ca18_cached_entries_live_24_hours(live, use_redis, client, ep01_world):
    use_redis(LIVE)
    assert client.get(URL, TRIP).status_code == 200

    keys = [key.decode() for key in live.keys("*")]
    [road] = [k for k in keys if ":road:" in k]
    [answer] = [k for k in keys if ":answer:" in k]
    for key in (road, answer):
        assert 86_000 < live.ttl(key) <= 86_400


def test_ca19_two_identical_new_requests_are_both_routed(monkeypatch, ep01_world):
    from django.test import Client

    from stations.index import get_index

    get_index()  # loaded here, so the two threads below never need the database

    def slow_fetch(start, finish):
        time.sleep(0.5)
        return ep01_world(start, finish)

    monkeypatch.setattr(routing, "fetch_route", slow_fetch)
    together = threading.Barrier(2)
    statuses = []

    def request() -> None:
        together.wait()
        statuses.append(Client().get(URL, TRIP).status_code)

    threads = [threading.Thread(target=request) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert statuses == [200, 200]
    assert ep01_world.calls == 2  # D-22: no lock makes the second wait for the first


def test_ca24_short_timeouts_and_no_retry(silent):
    params = {"TIMEOUT": 86_400, "VERSION": 1}
    cache = config.cache.RedisWithFallback(silent.url, params)
    options = cache._redis._cache._pool_options
    assert (options["socket_connect_timeout"], options["socket_timeout"]) == (0.1, 0.25)
    assert options["retry"].get_retries() == 0

    started = time.perf_counter()
    assert cache.get("anything") is None
    seconds = time.perf_counter() - started

    assert 0.25 <= seconds <= 0.5, seconds
    assert silent.connections == 1  # the read was not retried
    assert cache.falling_back


PARAMS = {"TIMEOUT": 86_400, "VERSION": 1}


@pytest.mark.parametrize("on_redis", [True, False], ids=["redis", "own memory"])
def test_every_cache_operation_works_on_redis_and_on_the_fallback(live, monkeypatch, on_redis):
    monkeypatch.setattr(config.cache, "_processes", {})
    cache = config.cache.RedisWithFallback(LIVE if on_redis else REFUSING, PARAMS)

    assert cache.add("a", 1) is True
    assert cache.add("a", 2) is False
    cache.set("b", [1, 2])
    assert cache.get_many(["a", "b", "c"]) == {"a": 1, "b": [1, 2]}
    assert cache.touch("a", 60) is True
    assert cache.delete("a") is True
    assert cache.get("a", "gone") == "gone"
    cache.clear()
    assert cache.get("b") is None
    assert cache.falling_back is not on_redis
    assert bool(live.keys("*")) is False


def test_a_redis_whose_name_takes_seconds_to_fail_costs_no_more_than_the_deadline(
    monkeypatch, caplog
):
    """Ruling on 11K's report: every Redis call has a deadline. A stopped Redis container's
    name leaves Docker's DNS, and a name lookup has no socket timeout: here it takes 2 s to
    fail. No real connection is made."""
    real_getaddrinfo = socket.getaddrinfo
    lookups = []

    def slow_lookup(host, *args, **kwargs):
        if host != "redis-gone":
            return real_getaddrinfo(host, *args, **kwargs)
        lookups.append(host)
        time.sleep(2)
        raise socket.gaierror(-2, "Name or service not known")

    monkeypatch.setattr(socket, "getaddrinfo", slow_lookup)
    monkeypatch.setattr(config.cache, "_processes", {})
    cache = config.cache.RedisWithFallback("redis://redis-gone:6379/15", PARAMS)

    started = time.perf_counter()
    assert cache.get("anything", "from memory") == "from memory"
    first = time.perf_counter() - started
    started = time.perf_counter()
    assert cache.get("anything", "from memory") == "from memory"
    second = time.perf_counter() - started

    assert first <= 0.5, first
    assert cache.falling_back
    assert [level for level, _ in fallback_lines(caplog)] == ["WARNING"]
    assert second < 0.05, second
    assert lookups == ["redis-gone"]  # the second read did not touch Redis


def test_an_error_in_the_pool_thread_falls_back_as_before(monkeypatch, caplog):
    """The Redis operation runs on the process's own pool thread; the error it raises there
    (a refused connection) reaches the caller and falls back as before."""
    from django.core.cache.backends.redis import RedisCache

    threads = []
    real_get = RedisCache.get

    def recording_get(self, *args, **kwargs):
        threads.append(threading.current_thread())
        return real_get(self, *args, **kwargs)

    monkeypatch.setattr(RedisCache, "get", recording_get)
    monkeypatch.setattr(config.cache, "_processes", {})
    cache = config.cache.RedisWithFallback(REFUSING, PARAMS)

    assert cache.get("anything", "from memory") == "from memory"
    assert cache.falling_back
    assert [level for level, _ in fallback_lines(caplog)] == ["WARNING"]
    [thread] = threads
    assert thread is not threading.current_thread()


def test_the_threads_of_one_process_share_one_fallback(monkeypatch, caplog):
    """Django makes one cache object per thread. Those of one process share the fallback:
    once one has found Redis gone, the others keep to memory too, with no warning of
    their own, and they share the memory."""
    monkeypatch.setattr(config.cache, "_processes", {})
    first, second = (config.cache.RedisWithFallback(REFUSING, PARAMS) for _ in range(2))

    first.set("shared", "yes")

    assert second.falling_back
    assert second.get("shared") == "yes"
    assert [level for level, _ in fallback_lines(caplog)] == ["WARNING"]


# --- HS-03 to HS-05: health and Redis -----------------------------------------------------


def health(client) -> dict:
    response = client.get(HEALTH)
    assert response.status_code == 200
    return json.loads(response.content)


def test_hs03_health_on_redis(live, use_redis, client, ep01_world):
    use_redis(LIVE)

    assert health(client)["cache"] == "redis"


def test_hs04_health_with_redis_refused(use_redis, client, caplog, ep01_world):
    use_redis(REFUSING)

    assert health(client) == {"status": "ok", "stations": 4, "cache": "fallback"}
    assert [level for level, _ in fallback_lines(caplog)] == ["WARNING"]


def test_hs05_health_follows_redis_away_and_back(switchable, use_redis, client, clock, ep01_world):
    switchable.switch(True)
    use_redis(switchable.url)
    assert health(client)["cache"] == "redis"

    switchable.switch(False)  # at T
    assert health(client)["cache"] == "fallback"  # health's own read finds Redis gone
    switchable.switch(True)
    clock.advance(10)
    assert health(client)["cache"] == "fallback"
    clock.advance(20)
    assert health(client)["cache"] == "redis"
