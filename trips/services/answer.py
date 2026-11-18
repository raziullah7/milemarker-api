"""Build the response body from a finished plan. Pure functions; no Django.

All rounding happens here, in decimal arithmetic, so that every figure in a response can
be reproduced from the response with a calculator. The rules are in the architecture
document, section 8 ("Money and rounding") and section 11 (the response).
"""

import itertools
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from stations.types import Place, StationInfo
from trips.services.corridor import SEARCH_RADIUS_MILES
from trips.services.fuel import MILES_PER_GALLON, RANGE_MILES, TANK_GALLONS
from trips.services.geo import RoadPoints

# A first fill-up station further from the start than this earns a warning.
FAR_FIRST_FILL_MILES = 25.0

# Map marker colours, in the "marker-color" property geojson.io reads.
STOP_COLOUR = "#d9480f"
START_COLOUR = "#2b8a3e"
FINISH_COLOUR = "#1864ab"

CENT = Decimal("0.01")


@dataclass(frozen=True)
class Stop:
    """One purchase in the chosen plan, before rounding.

    info       the station it is priced at
    mile       its mile marker (0.0 for the start)
    lat, lng   where it is drawn: the start place for stop 1, otherwise the road point
               nearest the station
    gallons    exact gallons bought
    """

    info: StationInfo
    mile: float
    lat: float
    lng: float
    gallons: float


def build_answer(
    *,
    start: Place,
    finish: Place,
    distance_miles: float,
    road: RoadPoints,
    stops: list[Stop],
    cheapest: list[tuple[Decimal, float]],
    first_fill_miles: float,
    stop_cost: Decimal,
) -> dict:
    """The response body without `meta`, with its keys in this order:
    summary, warnings, assumptions, fuel_stops, map.

    distance_miles    the trip length, already rounded to 0.1 mile
    stops             the chosen plan in order; stops[0] is the fill-up at the start
    cheapest          the free-stops plan as (exact price, exact gallons) pairs, for
                      lowest_possible_fuel_cost and lowest_possible_stops
    first_fill_miles  distance from the start place to the station stop 1 is priced at
    stop_cost         the stop cost the plan was chosen with

    Rounding, for the plan and for `cheapest` alike: gallons to 2 decimals as a running
    total that ends on distance_miles / 10 exactly; each cost = gallons x exact price,
    rounded half-up to cents; the total is the sum of the costs.
    """
    distance = _miles(distance_miles)
    # The distance has at most 1 decimal, so the total has at most 2 and is exact.
    total_gallons = _decimal(distance) / _decimal(MILES_PER_GALLON)
    gallons, costs = _bill([(stop.info.price, stop.gallons) for stop in stops], total_gallons)
    # A purchase that rounds to 0.00 gallons is not shown as a stop. Its fuel is not lost:
    # it stays in the running total, so a later purchase shows it. Stop 1 always stays,
    # as it is the start.
    kept = [
        (stop, amount, cost)
        for k, (stop, amount, cost) in enumerate(zip(stops, gallons, costs, strict=True))
        if k == 0 or amount > 0
    ]
    total_cost = sum(cost for _, _, cost in kept)

    lowest_gallons, lowest_costs = _bill(cheapest, total_gallons)
    lowest_cost = sum(lowest_costs)
    # Stops are counted as the plan's are: a purchase shown as 0.00 gallons is no stop, though
    # its fuel is in the bill above. So at stop cost 0, where the plan is the free-stops
    # plan, the two counts are equal.
    lowest_stops = max(1, sum(amount > 0 for amount in lowest_gallons))
    # Each bill is rounded stop by stop, so when the two plans' exact bills are within a
    # cent or two, the free-stops bill can come out above the plan's. The plan's own bill
    # can be bought, so the lowest possible is never more than it: show the plan's figures.
    if lowest_cost > total_cost:
        lowest_cost, lowest_stops = total_cost, len(kept)

    first_fill = _miles(first_fill_miles)
    # The rounded figure decides, so the warning always agrees with the figure shown.
    warnings = []
    if first_fill > FAR_FIRST_FILL_MILES:
        station = stops[0].info
        warnings.append(
            f"The nearest listed fuel station to the start is {station.name} in "
            f"{station.city}, {station.state}, {first_fill:.1f} miles away. "
            "The first fill-up is priced there."
        )

    fuel_stops = [
        {
            "order": order,
            "kind": "start" if order == 1 else "station",
            "station_id": stop.info.opis_id,
            "name": stop.info.name,
            "address": stop.info.address,
            "city": stop.info.city,
            "state": stop.info.state,
            "mile_marker": _miles(stop.mile),
            "lat": _coordinate(stop.lat),
            "lng": _coordinate(stop.lng),
            "price_per_gallon": float(stop.info.price),
            "gallons": float(amount),
            "cost": float(cost),
        }
        for order, (stop, amount, cost) in enumerate(kept, start=1)
    ]

    return {
        "summary": {
            "start": _place(start),
            "finish": _place(finish),
            "distance_miles": distance,
            "gallons": float(sum(amount for _, amount, _ in kept)),
            "total_fuel_cost": float(total_cost),
            "stops": len(fuel_stops),
            "lowest_possible_fuel_cost": float(lowest_cost),
            "lowest_possible_stops": lowest_stops,
            "first_fill_distance_miles": first_fill,
        },
        "warnings": warnings,
        "assumptions": {
            "range_miles": int(RANGE_MILES),
            "miles_per_gallon": int(MILES_PER_GALLON),
            "tank_gallons": int(TANK_GALLONS),
            "starting_fuel_gallons": 0,
            "stop_cost": float(stop_cost),
            "search_radius_miles": int(SEARCH_RADIUS_MILES),
        },
        "fuel_stops": fuel_stops,
        "map": _map(start, finish, distance, road, fuel_stops),
    }


def _bill(
    purchases: list[tuple[Decimal, float]], total_gallons: Decimal
) -> tuple[list[Decimal], list[Decimal]]:
    """Round (exact price, exact gallons) purchases to (gallons, costs) in the response.

    Gallons are rounded as a running total, half-up to 2 decimals: purchase k shows the
    rounded total of the first k purchases less the rounded total of the first k - 1.
    The last running total is total_gallons exactly, so the shown gallons add up to it
    with no adjustment. Rounding a running total never moves it by more than half a
    hundredth, so a full 50-gallon tank shows as 50.00, never more. Each cost is then its
    rounded gallons x its exact price, so anyone can check it from the response.
    """
    running = list(itertools.accumulate(_decimal(amount) for _, amount in purchases))
    running[-1] = total_gallons
    rounded = [_half_up(total, CENT) for total in running]
    gallons = [after - before for before, after in itertools.pairwise([Decimal(0), *rounded])]
    costs = [
        _half_up(amount * price, CENT)
        for amount, (price, _) in zip(gallons, purchases, strict=True)
    ]
    return gallons, costs


def _map(
    start: Place, finish: Place, distance_miles: float, road: RoadPoints, fuel_stops: list[dict]
) -> dict:
    """The route, the stops, the start and the finish as a GeoJSON FeatureCollection."""
    line = [
        [_coordinate(lng), _coordinate(lat)]
        for lng, lat in zip(road.lng.tolist(), road.lat.tolist(), strict=True)
    ]
    features = [_feature("LineString", line, {"kind": "route", "distance_miles": distance_miles})]
    for stop in fuel_stops:
        properties = {
            "kind": "stop",
            "order": stop["order"],
            "title": f"{stop['order']}. {stop['name']}, {stop['city']} {stop['state']}",
            "name": stop["name"],
            "mile_marker": stop["mile_marker"],
            "price_per_gallon": stop["price_per_gallon"],
            "gallons": stop["gallons"],
            "cost": stop["cost"],
            "marker-color": STOP_COLOUR,
        }
        features.append(_feature("Point", [stop["lng"], stop["lat"]], properties))
    for kind, place, colour in (("start", start, START_COLOUR), ("finish", finish, FINISH_COLOUR)):
        properties = {
            "kind": kind,
            "title": f"{kind.capitalize()}: {place.label}",
            "marker-color": colour,
        }
        coordinates = [_coordinate(place.lng), _coordinate(place.lat)]
        features.append(_feature("Point", coordinates, properties))
    return {"type": "FeatureCollection", "features": features}


def _feature(geometry_type: str, coordinates: list, properties: dict) -> dict:
    """One GeoJSON feature. Properties come before the geometry, so the short part is
    read first and the route's long list of coordinates comes last."""
    return {
        "type": "Feature",
        "properties": properties,
        "geometry": {"type": geometry_type, "coordinates": coordinates},
    }


def _place(place: Place) -> dict:
    """A start or finish place as the summary shows it."""
    return {"label": place.label, "lat": _coordinate(place.lat), "lng": _coordinate(place.lng)}


def _decimal(number: float) -> Decimal:
    """A float as the decimal it prints as: 10.004 is read as 10.004, not as the binary
    value 10.00399999... that Decimal(10.004) would give."""
    return Decimal(str(number))


def _half_up(number: Decimal, step: Decimal) -> Decimal:
    """Round to a multiple of `step`, halves going up, as a person rounds by hand."""
    return number.quantize(step, rounding=ROUND_HALF_UP)


def _miles(miles: float) -> float:
    """Miles to 1 decimal.

    Miles and coordinates are measurements, not money: nothing a reader checks with a
    calculator depends on which way a half rounds (the trip length arrives already
    rounded), so Python's round() (to the nearest, ties to even) is enough for them.
    """
    return round(float(miles), 1)


def _coordinate(degrees: float) -> float:
    """A latitude or longitude to 5 decimals, about a metre.

    Every coordinate in the response goes through here, so a stop placed on a road point
    has exactly the coordinates that point has in the route line. round() and not
    Decimal: a coast-to-coast line has over 11,000 numbers, and round() takes a third of
    the time (measured: 4 ms against 12 ms).
    """
    return round(float(degrees), 5)
