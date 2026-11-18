"""The routing service client: the only code in the project that makes a network call.

It asks a public OSRM server for the road between two points. If that server fails, it
asks a second one, once. Settings (config/settings.py): ROUTING_SERVERS,
ROUTING_DEADLINE_SECONDS, ROUTING_USER_AGENT. The rules are in the architecture
document, section 9.
"""

import json
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
import numpy as np
from django.conf import settings

from trips.exceptions import NoRoute, RoutingUnavailable

METRES_PER_MILE = 1609.344


@dataclass(frozen=True, eq=False)
class Route:
    """A road as the routing service returned it.

    coords          shape (n, 2), each row [lng, lat] (GeoJSON order)
    distance_miles  the service's own figure for the road's length
    server          host name of the server that answered
    calls           how many requests were made to get it: 1 or 2
    """

    coords: np.ndarray
    distance_miles: float
    server: str
    calls: int


def fetch_route(
    start: tuple[float, float],
    finish: tuple[float, float],
    *,
    client: httpx.Client | None = None,
) -> Route:
    """The driving road from `start` to `finish`, each a (lat, lng) pair.

    Tries each server in ROUTING_SERVERS in order, at most one request each. The next
    server is tried only after a timeout, a connection error, a 5xx or 429 status, or a
    200 that cannot be read as a route. Each attempt is timed by the HTTP library while
    connecting and waiting for the answer, and by ROUTING_DEADLINE_SECONDS, from sending
    the request, while the answer is read (see _attempt).

    Raises NoRoute, with no further attempt, if a server answers that no road joins the
    points. Raises RoutingUnavailable, with no further attempt and reason "error", if a
    server refuses the request with any other status. Raises RoutingUnavailable if every
    server failed: reason "timeout" when every attempt timed out, "error" otherwise.

    `client` is for tests, which pass one built on a fake transport. Without it a shared
    client is used, so connections are reused between requests.
    """
    if client is None:
        client = _get_shared_client()
    coords = ";".join(f"{_number(lng)},{_number(lat)}" for lat, lng in (start, finish))

    timeouts = []  # one True/False per failed attempt: did it fail by timing out?
    for calls, template in enumerate(settings.ROUTING_SERVERS, start=1):
        url = template.format(coords=coords)
        try:
            points, distance_miles = _attempt(client, url)
        except _AttemptFailed as failure:
            timeouts.append(failure.timed_out)
            continue
        return Route(
            coords=points,
            distance_miles=distance_miles,
            server=urlparse(template).hostname,
            calls=calls,
        )

    reason = "timeout" if timeouts and all(timeouts) else "error"
    raise RoutingUnavailable("The routing service could not be reached.", reason=reason)


class _AttemptFailed(Exception):
    """One request to one server did not give a usable answer; try the next server."""

    def __init__(self, timed_out: bool):
        super().__init__()
        self.timed_out = timed_out


_shared_client: httpx.Client | None = None


def _get_shared_client() -> httpx.Client:
    """The one client used when the caller passes none, created on first use."""
    global _shared_client
    if _shared_client is None:
        _shared_client = httpx.Client(headers={"User-Agent": settings.ROUTING_USER_AGENT})
    return _shared_client


def _number(value: float) -> str:
    """A coordinate with at most 6 decimals, no trailing zeros and no exponent."""
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _attempt(client: httpx.Client, url: str) -> tuple[np.ndarray, float]:
    """One request. Returns (points, miles), or raises NoRoute, RoutingUnavailable or
    _AttemptFailed."""
    deadline = time.monotonic() + settings.ROUTING_DEADLINE_SECONDS
    # httpx timeouts apply to each phase separately (connecting, waiting for the headers,
    # each read), so a server dripping bytes could outlast them. The clock check bounds the
    # reading of the body. A server slow both to answer and to send can still keep one
    # attempt going for about twice the deadline. The phases are not given less: the
    # servers take up to about 3 seconds to start answering a coast-to-coast request.
    timeouts = httpx.Timeout(settings.ROUTING_DEADLINE_SECONDS)
    try:
        with client.stream("GET", url, timeout=timeouts) as response:
            # The headers have arrived; a slow connection may already have used the time.
            if time.monotonic() > deadline:
                raise _AttemptFailed(timed_out=True)
            body = bytearray()
            for chunk in response.iter_bytes():
                body += chunk
                if time.monotonic() > deadline:
                    raise _AttemptFailed(timed_out=True)
            status = response.status_code
    except httpx.TimeoutException as error:
        raise _AttemptFailed(timed_out=True) from error
    except httpx.HTTPError as error:
        raise _AttemptFailed(timed_out=False) from error

    # OSRM says "no road" with status 400. The code is what matters, so it is read
    # whatever the status, short of a server error.
    if status < 500 and _osrm_code(body) in ("NoRoute", "NoSegment"):
        raise NoRoute("No road joins the start and the finish.")
    if status >= 500 or status == 429:
        # The server's own trouble: the other server may answer.
        raise _AttemptFailed(timed_out=False)
    if status != 200:
        # A refusal of the request itself, which the other server would refuse too.
        raise RoutingUnavailable("The routing service refused the request.", reason="error")
    return _read_route(body)


def _osrm_code(body: bytes) -> str | None:
    """The `code` field of an OSRM answer, or None if the body is not such an answer."""
    try:
        return json.loads(body).get("code")
    except (ValueError, AttributeError):
        return None


def _read_route(body: bytes) -> tuple[np.ndarray, float]:
    """The first route's points and length in miles, or _AttemptFailed if unusable."""
    try:
        route = json.loads(body)["routes"][0]
        points = np.array(route["geometry"]["coordinates"], dtype=float)
        metres = float(route["distance"])
    except (ValueError, KeyError, IndexError, TypeError):
        raise _AttemptFailed(timed_out=False) from None
    # A length of 0 is a route (both points on one spot); the planner decides what it means.
    if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] != 2 or not metres >= 0:
        raise _AttemptFailed(timed_out=False)
    return points, metres / METRES_PER_MILE
