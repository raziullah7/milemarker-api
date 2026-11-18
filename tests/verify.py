"""An independent check of a 200 answer from GET /api/v1/route/.

Written from the documents alone: rules R1 to R16 of docs/test-cases.md (section 4) and the
response contract in docs/backend-architecture.md (section 11). It imports only the standard
library, never `config`, `stations` or `trips`, so a mistake shared by the planner and its own
tests cannot also hide here. The endpoint tests and scripts/live_check.py both use it.

Money, gallons and prices are compared as exact decimals. The rules promise exact sums ("add
up exactly", "equals the sum"), and binary floating point cannot even hold 0.01. Read the JSON
with json.loads(text, parse_float=Decimal); a body already parsed with floats also works,
because each float is turned back into the shortest text that reads as it, which is the text
the server wrote.
"""

import csv
import math
import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from itertools import pairwise
from pathlib import Path

# The truck of requirements.md, section 2, and the search radius of D-11.
RANGE_MILES = 500
MILES_PER_GALLON = 10
TANK_GALLONS = 50
SEARCH_RADIUS_MILES = 5
DEFAULT_STOP_COST = Decimal(10)

CENT = Decimal("0.01")
TANK_SLACK = Decimal("0.05")  # R2: per-stop gallons are rounded to cents, so the walk may drift
FIRST_FILL_WARNING_MILES = 25  # R10, FR-14
LINE_GAP_MILES = 0.51  # R13: half-mile points, plus a little for coordinates cut to 5 decimals
SERVERS = frozenset({"router.project-osrm.org", "routing.openstreetmap.de"})
# fmt: off
LOWER_48_AND_DC = frozenset({
    "AL", "AZ", "AR", "CA", "CO", "CT", "DC", "DE", "FL", "GA", "ID", "IL", "IN", "IA", "KS",
    "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM",
    "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA",
    "WA", "WV", "WI", "WY",
})
# fmt: on
LABEL = re.compile(r"[^,]+, ([A-Z]{2})")  # R16: "City, ST"

# GE-01 fixes one degree of longitude on the equator at 69.094 miles, which is a sphere of
# this radius. R13 only needs it to tell 0.5 miles from 1.0, so the exact figure hardly matters.
EARTH_RADIUS_MILES = 3958.8

# R14: the most decimals each kind of figure may have.
MILES, GALLONS, MONEY, COORDINATE = 1, 2, 2, 5

# One verifier line lists this many problems of its rule, then counts the rest, so a rule
# broken on every point of a 5,000-point line still prints as one readable line.
SHOWN_PROBLEMS = 3


@dataclass(frozen=True)
class Listing:
    """What the CSV says about one station: its lowest price, and the details of the first
    row at that price, trimmed (R5, D-6)."""

    price: Decimal
    name: str
    address: str
    city: str
    state: str


def load_prices(csv_path: str | Path) -> dict[str, Listing]:
    """Station ID (the CSV's text, such as "7") to its Listing, read from the fuel CSV."""
    prices: dict[str, Listing] = {}
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            row = {key: (value or "").strip() for key, value in row.items()}
            listing = Listing(
                price=Decimal(row["Retail Price"]),
                name=row["Truckstop Name"],
                address=row["Address"],
                city=row["City"],
                state=row["State"],
            )
            station = row["OPIS Truckstop ID"]
            # Strictly lower only: on a tie the row seen first keeps the station.
            if station not in prices or listing.price < prices[station].price:
                prices[station] = listing
    return prices


def verify_response(body: dict, prices: dict[str, Listing], stop_cost=None) -> list[str]:
    """One line per broken rule, each starting with its ID ("R4: ..."); [] when all hold.

    `stop_cost` is what the request sent (text or number), or None if it sent none. Every
    rule is checked every time, so one broken rule never hides another.
    """
    lines = []
    for rule, check in RULES:
        try:
            problems = check(body, prices, stop_cost)
        except Exception as exc:
            # A body too malformed for a rule to read breaks that rule. Saying so, rather than
            # raising, keeps the remaining rules running.
            problems = [f"could not be checked ({type(exc).__name__}: {exc})"]
        if problems:
            lines.append(f"{rule}: {_join(problems)}")
    return lines


# --- Reading figures ---------------------------------------------------------------------


def _is_number(value) -> bool:
    # JSON true and false arrive as Python bools, which are ints; they are not numbers.
    return isinstance(value, int | float | Decimal) and not isinstance(value, bool)


def _dec(value) -> Decimal:
    """A JSON number as an exact decimal."""
    if not _is_number(value):
        raise TypeError(f"{value!r} is not a number")
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)


def _same(a, b) -> bool:
    """Equal as the JSON means it: numbers by value, anything else exactly."""
    if _is_number(a) and _is_number(b):
        return _dec(a) == _dec(b)
    return type(a) is type(b) and a == b


def _show(value) -> str:
    """A value as the JSON wrote it: numbers bare, text quoted."""
    return str(value) if _is_number(value) else repr(value)


def _join(problems: list[str]) -> str:
    shown = "; ".join(problems[:SHOWN_PROBLEMS])
    hidden = len(problems) - SHOWN_PROBLEMS
    return f"{shown}; and {hidden} more" if hidden > 0 else shown


def _miles_between(a, b) -> float:
    """Great-circle miles between two [lng, lat] pairs (haversine)."""
    lng1, lat1, lng2, lat2 = (math.radians(float(x)) for x in (*a, *b))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(min(1.0, h)))


# --- The rules: each returns the problems it found, [] when it holds ----------------------


def _r1_range(body, prices, stop_cost):
    distance = _dec(body["summary"]["distance_miles"])
    marks = [_dec(stop["mile_marker"]) for stop in body["fuel_stops"]]
    problems = []
    for n, (here, there) in enumerate(zip(marks, [*marks[1:], distance], strict=True), 1):
        if there - here > RANGE_MILES:
            to = "the finish" if n == len(marks) else f"stop {n + 1}"
            problems.append(f"{there - here} miles from stop {n} (mile {here}) to {to}")
    return problems


def _r2_tank(body, prices, stop_cost):
    # Walk the trip from mile 0 with an empty tank (D-1), burning a gallon per 10 miles.
    problems = []
    tank, at = Decimal(0), Decimal(0)
    for n, stop in enumerate(body["fuel_stops"], 1):
        mile = _dec(stop["mile_marker"])
        tank -= (mile - at) / MILES_PER_GALLON
        at = mile
        if tank < -TANK_SLACK:
            problems.append(f"tank at {tank} gallons on reaching stop {n} (mile {mile})")
        tank += _dec(stop["gallons"])
        if tank > TANK_GALLONS + TANK_SLACK:
            problems.append(f"tank at {tank} gallons after stop {n}")
    tank -= (_dec(body["summary"]["distance_miles"]) - at) / MILES_PER_GALLON
    if tank < -TANK_SLACK:
        problems.append(f"tank at {tank} gallons on reaching the finish")
    return problems


def _r3_gallons(body, prices, stop_cost):
    summary = body["summary"]
    bought = sum(_dec(stop["gallons"]) for stop in body["fuel_stops"])
    gallons, distance = _dec(summary["gallons"]), _dec(summary["distance_miles"])
    problems = []
    if bought != gallons:
        problems.append(f"stops buy {bought} gallons, summary.gallons is {gallons}")
    if gallons != distance / MILES_PER_GALLON:
        problems.append(f"summary.gallons {gallons} is not distance_miles {distance} / 10")
    return problems


def _r4_money(body, prices, stop_cost):
    problems = []
    costs = []
    for n, stop in enumerate(body["fuel_stops"], 1):
        gallons, price, cost = (_dec(stop[k]) for k in ("gallons", "price_per_gallon", "cost"))
        due = (gallons * price).quantize(CENT, rounding=ROUND_HALF_UP)
        if cost != due:
            problems.append(f"stop {n} cost {cost}, but {gallons} x {price} rounds to {due}")
        costs.append(cost)
    total = _dec(body["summary"]["total_fuel_cost"])
    if total != sum(costs):
        problems.append(f"total_fuel_cost {total}, but the stop costs add up to {sum(costs)}")
    return problems


def _r5_prices_and_names(body, prices, stop_cost):
    problems = []
    for n, stop in enumerate(body["fuel_stops"], 1):
        listing = prices.get(str(stop["station_id"]))
        if listing is None:
            problems.append(f"stop {n}: station {stop['station_id']!r} is not in the CSV")
            continue
        price = _dec(stop["price_per_gallon"])
        if price != listing.price:
            problems.append(f"stop {n}: price {price}, the CSV's lowest is {listing.price}")
        for field in ("name", "address", "city", "state"):
            if stop[field] != getattr(listing, field):
                problems.append(
                    f"stop {n}: {field} {stop[field]!r}, the CSV has {getattr(listing, field)!r}"
                )
    return problems


def _r6_stops(body, prices, stop_cost):
    stops, start = body["fuel_stops"], body["summary"]["start"]
    if not stops:
        return ["no fuel_stops"]
    problems = []
    first = stops[0]
    if first["kind"] != "start":
        problems.append(f"stop 1 kind is {first['kind']!r}, not 'start'")
    if _dec(first["mile_marker"]) != 0:
        problems.append(f"stop 1 is at mile {first['mile_marker']}, not 0.0")
    if not (_same(first["lat"], start["lat"]) and _same(first["lng"], start["lng"])):
        problems.append(
            f"stop 1 at ({first['lat']}, {first['lng']}), the start is at "
            f"({start['lat']}, {start['lng']})"
        )
    for n, stop in enumerate(stops[1:], 2):
        if stop["kind"] != "station":
            problems.append(f"stop {n} kind is {stop['kind']!r}, not 'station'")
    orders = [stop["order"] for stop in stops]
    if orders != list(range(1, len(stops) + 1)):
        problems.append(f"order runs {orders}")
    marks = [_dec(stop["mile_marker"]) for stop in stops]
    for n, (a, b) in enumerate(pairwise(marks), 1):
        if not a < b:
            problems.append(f"stop {n + 1} at mile {b} does not come after stop {n} at mile {a}")
    distance = _dec(body["summary"]["distance_miles"])
    if marks[-1] >= distance:
        problems.append(f"last stop at mile {marks[-1]}, not below distance_miles {distance}")
    ids = [stop["station_id"] for stop in stops]
    repeated = sorted({str(i) for i in ids if ids.count(i) > 1})
    if repeated:
        problems.append(f"station_id repeated: {', '.join(repeated)}")
    return problems


def _r7_lowest_bill(body, prices, stop_cost):
    summary = body["summary"]
    total = _dec(summary["total_fuel_cost"])
    lowest = _dec(summary["lowest_possible_fuel_cost"])
    problems = []
    if lowest > total:
        problems.append(f"lowest_possible_fuel_cost {lowest} is above total_fuel_cost {total}")
    if not _dec(summary["lowest_possible_stops"]) >= 1:
        problems.append(f"lowest_possible_stops is {summary['lowest_possible_stops']}")
    if _dec(body["assumptions"]["stop_cost"]) == 0 and lowest != total:
        problems.append(f"stop_cost 0, yet total {total} differs from lowest possible {lowest}")
    return problems


def _r8_stop_count(body, prices, stop_cost):
    stops = _dec(body["summary"]["stops"])
    listed = len(body["fuel_stops"])
    distance = _dec(body["summary"]["distance_miles"])
    fewest = math.ceil(distance / RANGE_MILES)
    problems = []
    if stops != listed:
        problems.append(f"summary.stops {stops}, but {listed} fuel_stops")
    if stops < fewest:
        problems.append(f"{stops} stops cannot cover {distance} miles; at least {fewest}")
    return problems


def _r9_assumptions(body, prices, stop_cost):
    sent = DEFAULT_STOP_COST if stop_cost is None else Decimal(str(stop_cost).strip())
    expected = {
        "range_miles": RANGE_MILES,
        "miles_per_gallon": MILES_PER_GALLON,
        "tank_gallons": TANK_GALLONS,
        "starting_fuel_gallons": 0,
        "stop_cost": sent,
        "search_radius_miles": SEARCH_RADIUS_MILES,
    }
    assumptions = body["assumptions"]
    problems = []
    if set(assumptions) != set(expected):
        problems.append(f"keys are {sorted(assumptions)}, expected {sorted(expected)}")
    for key, value in expected.items():
        if key in assumptions and not _same(assumptions[key], value):
            problems.append(f"{key} is {_show(assumptions[key])}, expected {value}")
    return problems


def _r10_first_fill(body, prices, stop_cost):
    distance = _dec(body["summary"]["first_fill_distance_miles"])
    warnings = body["warnings"]
    problems = []
    if distance < 0:
        problems.append(f"first_fill_distance_miles is {distance}")
    if distance <= FIRST_FILL_WARNING_MILES:
        if warnings != []:
            problems.append(f"first fill-up {distance} miles away, yet warnings {warnings!r}")
        return problems
    if not (isinstance(warnings, list) and len(warnings) == 1 and isinstance(warnings[0], str)):
        problems.append(f"first fill-up {distance} miles away needs one warning, got {warnings!r}")
        return problems
    name = body["fuel_stops"][0]["name"]
    # The distance as the response writes it, so 30.0 must read "30.0", not "30".
    for needed in (name, str(distance)):
        if needed not in warnings[0]:
            problems.append(f"warning {warnings[0]!r} does not contain {needed!r}")
    return problems


def _r11_map(body, prices, stop_cost):
    summary, stops, geo = body["summary"], body["fuel_stops"], body["map"]
    problems = []
    if geo.get("type") != "FeatureCollection":
        problems.append(f"map type is {geo.get('type')!r}, not 'FeatureCollection'")
    features = geo["features"]
    if len(features) != len(stops) + 3:
        problems.append(
            f"{len(features)} features; expected the route, {len(stops)} stops, start and finish"
        )
        return problems  # the features can no longer be paired with what they stand for

    def check_feature(n, feature, geometry, kind):
        found = []
        if feature.get("type") != "Feature":
            found.append(f"feature {n} type is {feature.get('type')!r}")
        if feature["geometry"]["type"] != geometry:
            found.append(f"feature {n} is a {feature['geometry']['type']}, not a {geometry}")
        props = feature["properties"]
        if props.get("kind") != kind:
            found.append(f"feature {n} kind is {props.get('kind')!r}, not {kind!r}")
        if geometry == "Point":
            for key in ("title", "marker-color"):
                if not (isinstance(props.get(key), str) and props[key]):
                    found.append(f"feature {n} has no {key}")
        return found

    def at(n, feature, lng, lat):
        coords = feature["geometry"]["coordinates"]
        if not (len(coords) == 2 and _same(coords[0], lng) and _same(coords[1], lat)):
            return [f"feature {n} at {coords}, expected [lng, lat] [{lng}, {lat}]"]
        return []

    route = features[0]
    problems += check_feature(0, route, "LineString", "route")
    if not _same(route["properties"].get("distance_miles"), summary["distance_miles"]):
        problems.append(
            f"route distance_miles {route['properties'].get('distance_miles')}, "
            f"summary has {summary['distance_miles']}"
        )

    for n, (stop, point) in enumerate(zip(stops, features[1 : len(stops) + 1], strict=True), 1):
        problems += check_feature(n, point, "Point", "stop")
        props = point["properties"]
        for key in ("order", "name", "mile_marker", "price_per_gallon", "gallons", "cost"):
            if key not in props or not _same(props[key], stop[key]):
                problems.append(
                    f"feature {n} {key} {_show(props.get(key))}, stop has {_show(stop[key])}"
                )
        title = f"{stop['order']}. {stop['name']}, {stop['city']} {stop['state']}"
        if props.get("title") != title:
            problems.append(f"feature {n} title {props.get('title')!r}, expected {title!r}")
        problems += at(n, point, stop["lng"], stop["lat"])

    for n, kind in ((len(stops) + 1, "start"), (len(stops) + 2, "finish")):
        problems += check_feature(n, features[n], "Point", kind)
        problems += at(n, features[n], summary[kind]["lng"], summary[kind]["lat"])
    return problems


def _r12_stops_on_line(body, prices, stop_cost):
    line = body["map"]["features"][0]["geometry"]["coordinates"]
    positions: dict[tuple, list[int]] = {}
    for i, (lng, lat) in enumerate(line):
        positions.setdefault((_dec(lng), _dec(lat)), []).append(i)
    problems = []
    previous = -1
    for stop in body["fuel_stops"]:
        if stop["kind"] != "station":
            continue
        order = stop["order"]
        found = positions.get((_dec(stop["lng"]), _dec(stop["lat"])))
        if not found:
            problems.append(f"stop {order} at [{stop['lng']}, {stop['lat']}] is not on the line")
            continue
        # A road can pass the same point twice; the stop must be at a pass after the last stop.
        later = [i for i in found if i > previous]
        if not later:
            problems.append(f"stop {order} is at line position {found[0]}, not after {previous}")
            continue
        previous = later[0]
        mile, expected = _dec(stop["mile_marker"]), Decimal(previous) / 2
        if abs(mile - expected) > expected * Decimal("0.005") + Decimal("0.05"):
            problems.append(
                f"stop {order} at mile {mile}, but line position {previous} is mile {expected}"
            )
    return problems


def _r13_line_spacing(body, prices, stop_cost):
    line = body["map"]["features"][0]["geometry"]["coordinates"]
    distance = _dec(body["summary"]["distance_miles"])
    problems = []
    gaps = [
        (i, gap)
        for i, gap in enumerate(_miles_between(a, b) for a, b in pairwise(line))
        if gap > LINE_GAP_MILES
    ]
    if gaps:
        i, gap = gaps[0]
        problems.append(
            f"gaps over {LINE_GAP_MILES} miles: {len(gaps)}, the first {gap:.3f} after point {i}"
        )
    expected = 2 * distance + 1
    if abs(len(line) - expected) > expected / 100:
        problems.append(f"{len(line)} line points, expected {expected} within 1%")
    return problems


def _r14_precision(body, prices, stop_cost):
    summary, assumptions = body["summary"], body["assumptions"]
    figures = []  # (where, value, most decimals allowed, or None for any)
    for place in ("start", "finish"):
        for axis in ("lat", "lng"):
            figures.append((f"summary.{place}.{axis}", summary[place][axis], COORDINATE))
    figures += [
        ("summary.distance_miles", summary["distance_miles"], MILES),
        ("summary.gallons", summary["gallons"], GALLONS),
        ("summary.total_fuel_cost", summary["total_fuel_cost"], MONEY),
        ("summary.stops", summary["stops"], None),
        ("summary.lowest_possible_fuel_cost", summary["lowest_possible_fuel_cost"], MONEY),
        ("summary.lowest_possible_stops", summary["lowest_possible_stops"], None),
        ("summary.first_fill_distance_miles", summary["first_fill_distance_miles"], MILES),
        ("assumptions.range_miles", assumptions["range_miles"], MILES),
        ("assumptions.miles_per_gallon", assumptions["miles_per_gallon"], None),
        ("assumptions.tank_gallons", assumptions["tank_gallons"], GALLONS),
        ("assumptions.starting_fuel_gallons", assumptions["starting_fuel_gallons"], GALLONS),
        ("assumptions.stop_cost", assumptions["stop_cost"], MONEY),
        ("assumptions.search_radius_miles", assumptions["search_radius_miles"], MILES),
    ]
    stop_figures = {
        "order": None,
        "mile_marker": MILES,
        "lat": COORDINATE,
        "lng": COORDINATE,
        "price_per_gallon": None,  # every digit the CSV has; R5 checks them
        "gallons": GALLONS,
        "cost": MONEY,
    }
    for n, stop in enumerate(body["fuel_stops"], 1):
        figures += [(f"fuel_stops[{n - 1}].{k}", stop[k], d) for k, d in stop_figures.items()]

    # The map's shape is R11's business; here every number it does hold is checked.
    property_figures = {"distance_miles": MILES, **stop_figures}
    for n, feature in enumerate(body["map"]["features"]):
        geometry = feature["geometry"]
        points = geometry["coordinates"]
        if geometry["type"] == "Point":
            points = [points]
        for pair in points:
            figures += [(f"map feature {n} coordinate", x, COORDINATE) for x in pair]
        for key, most in property_figures.items():
            if key in feature["properties"]:
                figures.append((f"map feature {n} {key}", feature["properties"][key], most))

    meta = body["meta"]
    figures.append(("meta.routing_calls", meta["routing_calls"], None))
    figures += [(f"meta.timings_ms.{k}", v, None) for k, v in meta["timings_ms"].items()]

    problems = []
    for where, value, most in figures:
        if not _is_number(value):
            problems.append(f"{where} is {value!r}, not a JSON number")
        elif most is not None and max(0, -_dec(value).as_tuple().exponent) > most:
            problems.append(f"{where} is {value}, more than {most} decimals")
    return problems


def _r15_meta(body, prices, stop_cost):
    meta = body["meta"]
    calls, hit, timings = meta["routing_calls"], meta["cache_hit"], meta["timings_ms"]
    problems = []
    if not (_is_number(calls) and calls in (0, 1, 2)):
        problems.append(f"routing_calls is {calls!r}")
    if not isinstance(hit, bool):
        problems.append(f"cache_hit is {hit!r}, not true or false")
    if hit is True and calls != 0:
        problems.append(f"cache_hit true with routing_calls {calls}")
    for key in ("routing", "own", "total"):
        value = timings.get(key)
        if not (_is_number(value) and value >= 0):
            problems.append(f"timings_ms.{key} is {value!r}")
    if calls == 0 and timings.get("routing") != 0:
        problems.append(f"no routing call, yet timings_ms.routing is {timings.get('routing')!r}")
    if meta["routing_server"] not in SERVERS:
        problems.append(f"routing_server is {meta['routing_server']!r}")
    return problems


def _r16_labels(body, prices, stop_cost):
    problems = []
    for place in ("start", "finish"):
        label = body["summary"][place]["label"]
        match = LABEL.fullmatch(label) if isinstance(label, str) else None
        if not match or match.group(1) not in LOWER_48_AND_DC:
            problems.append(
                f"summary.{place}.label {label!r} is not 'City, ST' in the lower 48 or DC"
            )
    return problems


RULES = (
    ("R1", _r1_range),
    ("R2", _r2_tank),
    ("R3", _r3_gallons),
    ("R4", _r4_money),
    ("R5", _r5_prices_and_names),
    ("R6", _r6_stops),
    ("R7", _r7_lowest_bill),
    ("R8", _r8_stop_count),
    ("R9", _r9_assumptions),
    ("R10", _r10_first_fill),
    ("R11", _r11_map),
    ("R12", _r12_stops_on_line),
    ("R13", _r13_line_spacing),
    ("R14", _r14_precision),
    ("R15", _r15_meta),
    ("R16", _r16_labels),
)
