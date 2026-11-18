"""plan_trip(): the one function the API layer calls.

It runs the steps of the request flow in order (architecture document, sections 2 and 5)
and owns the two caches (section 10). Everything it calls is in the modules beside it
and in the stations app; the rules themselves live there, not here.
"""

import functools
import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from importlib import import_module
from urllib.parse import quote

import numpy as np
from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError, connection

from stations.exceptions import StationsNotLoaded
from stations.index import get_index, nearest_station
from stations.places import Place, resolve
from stations.types import StationIndex
from trips.exceptions import InvalidRequest, RouteLeavesUSA
from trips.services import routing
from trips.services.answer import Stop, build_answer
from trips.services.corridor import (
    SEARCH_RADIUS_MILES,
    THIN_WINDOW_MILES,
    Candidate,
    stations_along,
    thin,
)
from trips.services.fuel import Purchase, cheapest_fuel, find_gap, plan_stops
from trips.services.geo import RoadPoints, load_borders, longest_run_abroad, resample

# A road shorter than this joins two points that are, for a truck, one place.
SHORTEST_TRIP_MILES = 0.5

# A road may run through Canada or Mexico for this many miles in a row, no more (D-4).
MOST_MILES_ABROAD = 25.0

SAME_PLACE = "Start and finish are the same place."

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Road:
    """What the road cache holds for one trip."""

    points: RoadPoints
    distance_miles: float  # the routing service's length, rounded to 0.1 mile
    server: str  # host name of the routing server that supplied it


@dataclass(frozen=True)
class _FuelList:
    """The stations a plan is chosen from, in the form the fuel routines take.

    Entry 0 is the start: mile 0.0, priced at the start station. Entry k > 0 is
    candidates[k - 1]. `stations` holds each entry's position in the StationIndex.
    """

    candidates: list[Candidate]
    miles: list[float]
    prices: list[float]
    stations: list[int]


def plan_trip(start_text: str, finish_text: str, stop_cost: Decimal) -> dict:
    """Plan a trip and return the whole response body, including `meta`.

    Order of work, so that nothing knowable before the routing call is raised after it:
    resolve start, resolve finish, same-place check, answer cache, stations loaded and
    nearest station to the start, road (cache or one routing call), border check,
    stations along the road, fuel plan, answer.

    Raises the errors in stations/exceptions.py and trips/exceptions.py.
    """
    started = time.perf_counter()

    # 1. Places. Start first, so when both are bad the error names the start.
    start = resolve(start_text, "start")
    finish = resolve(finish_text, "finish")

    # 2. Same place.
    if _spot(start) == _spot(finish):
        raise InvalidRequest(SAME_PLACE, fields={"finish": [SAME_PLACE]})

    # 3. Answer cache. The body shows both labels, so they are part of its key: two places
    # can share coordinates (Ackermanville and Flicksville, PA do) and must not serve each
    # other's label. The road depends only on the coordinates.
    trip_key = f"{_spot(start)};{_spot(finish)}"
    labels = f"{quote(start.label)};{quote(finish.label)}"
    answer_key = f"answer:{trip_key}:{labels}:{stop_cost:.2f}"
    cached = cache.get(answer_key)
    if cached is not None:
        body, server = cached
        return _with_meta(body, started, server, cache_hit=True)

    # 4. Stations, and the one nearest the start, where the first fill-up is priced.
    index = get_index()
    start_station, first_fill_miles = nearest_station(index, start.lat, start.lng)

    # 5. The road: from the cache, or from one routing call.
    road_key = f"road:{trip_key}"
    road = cache.get(road_key)
    routing_calls, routing_seconds = 0, 0.0
    if road is None:
        road, routing_calls, routing_seconds = _fetch_road(start, finish)
        cache.set(road_key, road, settings.TRIP_CACHE_SECONDS)

    # 6. Stations along the road.
    along = stations_along(
        road.points, index, radius_miles=SEARCH_RADIUS_MILES, exclude=start_station
    )
    every_station = _fuel_list(index, start_station, along)

    # 7. The free-stops plan. It raises NoFuelPlan if no plan exists at all.
    free_plan = cheapest_fuel(every_station.miles, every_station.prices, road.distance_miles)

    # 8. The plan.
    if stop_cost == 0:
        chosen_from, purchases = every_station, free_plan
    else:
        chosen_from, purchases = _plan_with_stop_cost(
            index, every_station, road.distance_miles, stop_cost
        )

    # 9. The answer.
    body = build_answer(
        start=start,
        finish=finish,
        distance_miles=road.distance_miles,
        road=road.points,
        stops=_stops(purchases, chosen_from, index, start, road.points),
        cheapest=[
            (index.info[every_station.stations[p.index]].price, p.gallons) for p in free_plan
        ],
        first_fill_miles=first_fill_miles,
        stop_cost=stop_cost,
    )

    # 10. Cache the body, then add meta.
    cache.set(answer_key, (body, road.server), settings.TRIP_CACHE_SECONDS)
    return _with_meta(
        body,
        started,
        road.server,
        cache_hit=False,
        routing_calls=routing_calls,
        routing_seconds=routing_seconds,
    )


def warm_up() -> None:
    """Load now what the first request would otherwise wait for: the places table, the
    border outlines, the URL configuration (which imports the views and, through them,
    scipy) and the station index. Called once when the server starts (config/wsgi.py).

    The server may start before load_stations has run, or before the database is up. Then
    one line is logged and nothing is raised: the first request that needs the stations
    reads them, as it would have without this.
    """
    resolve("New York, NY", "start")  # any lookup reads the places table, once
    _borders()
    import_module(settings.ROOT_URLCONF)
    try:
        get_index()
    except (StationsNotLoaded, DatabaseError) as error:
        logger.warning(
            "Stations not loaded at start-up (%s); the first request that needs them will "
            "load them.",
            type(error).__name__,
        )
    # The thread that starts the server never serves a request, so the connection opened
    # above would otherwise sit idle for the life of the process.
    connection.close()


def _spot(place: Place) -> str:
    """A place's coordinates to 4 decimals (about 10 metres): what makes two places one,
    and what the cache keys are made of."""
    return f"{place.lat:.4f},{place.lng:.4f}"


def _fetch_road(start: Place, finish: Place) -> tuple[_Road, int, float]:
    """One routing call, then the checks a road must pass before it may be cached.

    Returns (the road, routing calls made, seconds spent inside the routing call).
    """
    before = time.perf_counter()
    route = routing.fetch_route((start.lat, start.lng), (finish.lat, finish.lng))
    routing_seconds = time.perf_counter() - before

    distance_miles = round(route.distance_miles, 1)
    if distance_miles < SHORTEST_TRIP_MILES:
        raise InvalidRequest(SAME_PLACE, fields={"finish": [SAME_PLACE]})

    points = resample(route.coords, distance_miles)
    miles_abroad = longest_run_abroad(points, _borders())
    if miles_abroad > MOST_MILES_ABROAD:
        raise RouteLeavesUSA(
            f"The road runs through Canada or Mexico for {miles_abroad:.0f} miles in a row. "
            "Only trips that stay in the USA are planned.",
            miles_abroad=miles_abroad,
        )
    return _Road(points, distance_miles, route.server), route.calls, routing_seconds


@functools.cache
def _borders() -> dict[str, np.ndarray]:
    """The Canada and Mexico outlines, read from settings.BORDERS_FILE once per process."""
    return load_borders(settings.BORDERS_FILE)


def _fuel_list(index: StationIndex, start_station: int, candidates: list[Candidate]) -> _FuelList:
    """The start station at mile 0.0, then each candidate, as a _FuelList."""
    return _FuelList(
        candidates=candidates,
        miles=[0.0] + [c.mile for c in candidates],
        prices=[float(index.price[start_station])] + [c.price for c in candidates],
        stations=[start_station] + [c.station for c in candidates],
    )


def _plan_with_stop_cost(
    index: StationIndex, every_station: _FuelList, distance_miles: float, stop_cost: Decimal
) -> tuple[_FuelList, list[Purchase]]:
    """The plan for a stop cost above zero, and the list it was chosen from.

    It is chosen on the thinned list, unless thinning dropped a station the trip cannot
    do without. Then it is chosen on every station: slower, but it never reports "no plan"
    wrongly (architecture, section 8).
    """
    thinned = thin(every_station.candidates, window_miles=THIN_WINDOW_MILES)
    chosen_from = _fuel_list(index, every_station.stations[0], thinned)
    if find_gap(chosen_from.miles, distance_miles) is not None:
        chosen_from = every_station
    purchases = plan_stops(chosen_from.miles, chosen_from.prices, distance_miles, float(stop_cost))
    return chosen_from, purchases


def _stops(
    purchases: list[Purchase],
    chosen_from: _FuelList,
    index: StationIndex,
    start: Place,
    road: RoadPoints,
) -> list[Stop]:
    """Each purchase as a Stop, at the exact price of its station.

    The first purchase is the fill-up at the start: drawn at the start place, mile 0.0.
    Every other is drawn at the road point nearest its station, so it sits on the line.
    """
    stops = []
    for purchase in purchases:
        info = index.info[chosen_from.stations[purchase.index]]
        if purchase.index == 0:
            stops.append(Stop(info, 0.0, start.lat, start.lng, purchase.gallons))
        else:
            candidate = chosen_from.candidates[purchase.index - 1]
            lat, lng = float(road.lat[candidate.point]), float(road.lng[candidate.point])
            stops.append(Stop(info, candidate.mile, lat, lng, purchase.gallons))
    return stops


def _with_meta(
    body: dict,
    started: float,
    server: str,
    *,
    cache_hit: bool,
    routing_calls: int = 0,
    routing_seconds: float = 0.0,
) -> dict:
    """The body with `meta` added last. Built for every response and never cached.

    `own` is `total` less the time inside the routing call, so the three add up.
    """
    total_ms = round((time.perf_counter() - started) * 1000, 1)
    routing_ms = round(routing_seconds * 1000, 1)
    meta = {
        "routing_calls": routing_calls,
        "cache_hit": cache_hit,
        "routing_server": server,
        "timings_ms": {
            "routing": routing_ms,
            "own": round(total_ms - routing_ms, 1),
            "total": total_ms,
        },
    }
    return {**body, "meta": meta}
