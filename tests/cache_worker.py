"""A process standing for one API worker, for the cache tests that need two (tests/test_cache.py,
"Two processes" in docs/test-cases.md, section 9.1).

It runs the real application with REDIS_URL from its environment, answers requests through
the Django test client, and holds EP-01's world: its four stations in memory, so it never
reads the database, and its own fake routing service, which counts its calls.

    python tests/cache_worker.py [key version]

It reads one JSON command per line on standard input and answers each with one JSON line:

    {"get": "/api/v1/route/", "params": {...}}   ->  {"status", "body", "calls"}
    {"advance": 30}                               ->  {}  (the cache's clock moves 30 s on)
    {"burst": "/api/v1/route/", "params": {...},
     "threads": 8, "each": 8}                     ->  {"statuses"}  (8 threads that start
                                                      together send 8 requests each)

Its log lines go to standard error, in the API's own format.
"""

import json
import os
import sys
import threading
import time
import types
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.test import Client  # noqa: E402

import config.cache  # noqa: E402
from stations import index  # noqa: E402
from stations.types import StationInfo, build_index  # noqa: E402
from tests.test_api import DALLAS, FakeRouting, on_road, straight_road  # noqa: E402
from trips.services import routing  # noqa: E402

if len(sys.argv) > 1:
    # Another release of the code: the same, with CACHE_KEY_VERSION raised (CA-03).
    settings.CACHES["default"]["VERSION"] = int(sys.argv[1])


def station(opis_id: int, price: str, lat: float, lng: float, name: str = "") -> tuple:
    """One of EP-01's stations, as tests/test_api.py's add_station saves it."""
    info = StationInfo(
        opis_id=opis_id,
        name=name or f"STATION {opis_id}",
        address=f"EXIT {opis_id}",
        city="Testville",
        state="TX",
        price=Decimal(price),
    )
    return info, lat, lng


index._index = build_index(
    [station(1, "3.20", *DALLAS, name="DALLAS START")]
    + [
        station(n, price, *on_road(mile))
        for n, mile, price in ((2, 200, "3.10"), (3, 450, "3.00"), (4, 700, "3.20"))
    ]
)
fake = FakeRouting(*straight_road(990.0))
routing.fetch_route = fake

# The cache's clock, which the tests move on rather than wait for.
moved = [0.0]
config.cache.time = types.SimpleNamespace(monotonic=lambda: time.monotonic() + moved[0])


def burst(path: str, params: dict, threads: int, each: int) -> list[int]:
    """The statuses of `each` requests from each of `threads` threads that start together,
    each thread with a client of its own, as a worker's threads answer requests at once."""
    together = threading.Barrier(threads)
    statuses: list[int] = []

    def send() -> None:
        own = Client(HTTP_HOST="127.0.0.1")
        together.wait()
        for _ in range(each):
            statuses.append(own.get(path, params).status_code)

    senders = [threading.Thread(target=send) for _ in range(threads)]
    for sender in senders:
        sender.start()
    for sender in senders:
        sender.join()
    return statuses


client = Client(HTTP_HOST="127.0.0.1")
for line in sys.stdin:
    command = json.loads(line)
    if "advance" in command:
        moved[0] += command["advance"]
        reply = {}
    elif "burst" in command:
        statuses = burst(command["burst"], command["params"], command["threads"], command["each"])
        reply = {"statuses": statuses}
    else:
        response = client.get(command["get"], command["params"])
        reply = {
            "status": response.status_code,
            "body": json.loads(response.content),
            "calls": fake.calls,
        }
    print(json.dumps(reply), flush=True)
