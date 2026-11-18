"""The routing service client: the only code in the project that makes a network call.

It asks a public OSRM server for the road between two points. If that server fails, it
asks a second one, once. Settings (config/settings.py): ROUTING_SERVERS,
ROUTING_DEADLINE_SECONDS, ROUTING_USER_AGENT. The rules are in the architecture
document, section 9.
"""

from dataclasses import dataclass

import httpx
import numpy as np


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

    Tries each server in ROUTING_SERVERS in order, at most one request each. A server is
    given up on after a timeout, a connection error, a 5xx or 429 status, or an answer
    that cannot be read as a route. Each attempt has a total deadline of
    ROUTING_DEADLINE_SECONDS, measured from sending the request to reading its last byte.

    Raises NoRoute, with no further attempt, if a server answers that no road joins the
    points. Raises RoutingUnavailable if every server failed: reason "timeout" when every
    attempt timed out, "error" otherwise.

    `client` is for tests, which pass one built on a fake transport. Without it a shared
    client is used, so connections are reused between requests.
    """
    raise NotImplementedError
