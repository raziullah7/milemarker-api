"""A stand-in for the public OSRM routing server, answering from recorded roads.

The API plans a trip with one call to a public routing server, which is free and must not be
leaned on. This server answers the same two URL paths from the recordings in
tests/fixtures/roads, so the whole stack can run with no call to the internet.

    python scripts/fake_osrm.py [--host 0.0.0.0] [--port 5000] [--roads tests/fixtures/roads]

    GET  /route/v1/driving/{lng,lat;lng,lat}              the recorded road, or 400 NoRoute
    GET  /routed-car/route/v1/driving/{lng,lat;lng,lat}   the same, at the second server's path
    GET  /_requests                                       the route requests served so far
    POST /_reset                                          empties that log
    GET  /_health                                         200

Only the standard library is used, so it runs in the API image as it is.
"""

import argparse
import contextlib
import gzip
import json
import math
import re
import signal
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

# A request matches a recording when both of its points are within this many miles of the
# recording's own start and finish.
MATCH_MILES = 30
EARTH_RADIUS_MILES = 3958.8

ROUTE_PATH = re.compile(r"^/(?:routed-car/)?route/v1/driving/(?P<coords>[^/]+)$")
DEFAULT_ROADS = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "roads"


def miles_between(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance in miles between two [lng, lat] points (haversine)."""
    lng1, lat1, lng2, lat2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + (
        math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(h))


def load_roads(folder: Path) -> list[dict]:
    """Every *.json.gz recording in `folder`, read once.

    Each is {"name", "start", "finish", "body"}: the file's name without its extensions, the
    two waypoints' [lng, lat], and the unpacked answer exactly as recorded."""
    roads = []
    for path in sorted(folder.glob("*.json.gz")):
        body = gzip.decompress(path.read_bytes())
        waypoints = json.loads(body)["waypoints"]
        roads.append(
            {
                "name": path.name.removesuffix(".json.gz"),
                "start": tuple(waypoints[0]["location"]),
                "finish": tuple(waypoints[1]["location"]),
                "body": body,
            }
        )
    return roads


def parse_coords(text: str) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """The start and finish of "lng,lat;lng,lat", or None if the text is anything else."""
    points = unquote(text).split(";")
    if len(points) != 2:
        return None
    parsed = []
    for point in points:
        parts = point.split(",")
        if len(parts) != 2:
            return None
        try:
            lng, lat = float(parts[0]), float(parts[1])
        except ValueError:
            return None
        if not (math.isfinite(lng) and math.isfinite(lat)):
            return None
        parsed.append((lng, lat))
    return parsed[0], parsed[1]


def find_road(roads: list[dict], start, finish) -> dict | None:
    """The recording whose start and finish are both within MATCH_MILES of the request's,
    the closest overall if several are, else None. Direction matters: a road recorded one
    way does not answer for the other."""
    best, best_miles = None, None
    for road in roads:
        near_start = miles_between(road["start"], start)
        near_finish = miles_between(road["finish"], finish)
        if near_start <= MATCH_MILES and near_finish <= MATCH_MILES:
            total = near_start + near_finish
            if best is None or total < best_miles:
                best, best_miles = road, total
    return best


class FakeOsrm(ThreadingHTTPServer):
    """The server, holding the recordings and the log of route requests."""

    daemon_threads = True

    def __init__(self, address, roads: list[dict]):
        super().__init__(address, Handler)
        self.roads = roads
        self.log: list[dict] = []
        # Handlers run in threads; the log is appended to and emptied from several.
        self.lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    """One request."""

    server: FakeOsrm

    def do_GET(self):
        """Route requests, the log and the health check; anything else is a 404."""
        path = urlsplit(self.path).path
        if path == "/_health":
            self._send_json(200, {"status": "ok"})
        elif path == "/_requests":
            with self.server.lock:
                log = list(self.server.log)
            self._send_json(200, {"count": len(log), "requests": log})
        elif ROUTE_PATH.match(path):
            self._route(ROUTE_PATH.match(path).group("coords"))
        else:
            self._send_json(404, {"code": "NotFound", "message": "No such path."})

    def do_POST(self):
        """Only /_reset, which empties the log."""
        if urlsplit(self.path).path == "/_reset":
            with self.server.lock:
                self.server.log.clear()
            self._send_json(200, {"status": "reset"})
        else:
            self._send_json(404, {"code": "NotFound", "message": "No such path."})

    def _route(self, coords_text: str):
        """Answer a route request and record it in the log."""
        coords = parse_coords(coords_text)
        if coords is None:
            # Not logged: there are no coordinates to record, and the log counts roads asked for.
            self._send_json(
                400, {"code": "InvalidUrl", "message": "URL string malformed close to position 0."}
            )
            return
        start, finish = coords
        road = find_road(self.server.roads, start, finish)
        status = 200 if road else 400
        with self.server.lock:
            self.server.log.append(
                {
                    "path": urlsplit(self.path).path,
                    "start": list(start),
                    "finish": list(finish),
                    "matched": road["name"] if road else None,
                    "status": status,
                }
            )
        if road:
            self._send(200, road["body"])
        else:
            # The real server answers "no road" with status 400, which routing.py reads
            # from the code field.
            self._send_json(
                400, {"code": "NoRoute", "message": "No route found between the points."}
            )

    def _send_json(self, status: int, payload: dict):
        """Send `payload` as JSON."""
        self._send(status, json.dumps(payload).encode())

    def _send(self, status: int, body: bytes):
        """Send a JSON body with its length, so the connection can be reused."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        """Silence the per-request line on stderr: the request log is the record."""


def main():
    """Read the options, load the recordings and serve until stopped."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--roads", type=Path, default=DEFAULT_ROADS)
    args = parser.parse_args()

    server = FakeOsrm((args.host, args.port), load_roads(args.roads))
    # The first line of output says the socket is open; tests and Compose wait for it.
    print(
        f"listening on {args.host}:{args.port} with {len(server.roads)} recorded roads",
        flush=True,
    )
    # "docker stop" sends SIGTERM, which a process running as the container's first process
    # ignores unless it handles it; without this, stopping would wait out the 10 seconds.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    with contextlib.suppress(KeyboardInterrupt):
        server.serve_forever()


if __name__ == "__main__":
    main()
