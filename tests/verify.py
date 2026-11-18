"""An independent check of a 200 answer from GET /api/v1/route/.

Written from the documents alone: rules R1 to R17 of docs/test-cases.md (section 4) and the
response contract in docs/backend-architecture.md (section 11). It imports only the standard
library, never `config`, `stations` or `trips`, so a mistake shared by the planner and its own
tests cannot also hide here. The endpoint tests and scripts/live_check.py both use it.

It checks that a plan is consistent and possible, not that it is the cheapest: its figures
agree with each other, with the CSV and with the road, and the truck can drive it. That no
plan is cheaper is checked by the exactness tests EX-01 to EX-04 (tests/test_fuel.py),
against two exact methods that share no code with the planner.

Money, gallons and prices are compared as exact decimals. The rules promise exact sums ("add
up exactly", "equals the sum"), and binary floating point cannot even hold 0.01. Read the JSON
with json.loads(text, parse_float=Decimal); a body already parsed with floats also works,
because each float is turned back into the shortest text that reads as it, which is the text
the server wrote.
"""

import csv
import functools
import math
import re
from collections.abc import Iterable
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
FIRST_FILL_WARNING_MILES = 25  # R10, FR-14
LINE_GAP_MILES = 0.51  # R13: half-mile points, plus a little for coordinates cut to 5 decimals
COUNT_SHARE, COUNT_POINTS = Decimal("0.0025"), 2  # R13: how far the point count may be off
# R12: a marker is shown to 0.1 mile, so it can be 0.05 from its point's exact mile. The rest
# is room for the straight line between the last two points, measured from coordinates cut
# to 5 decimals.
MARKER_ON_LINE_MILES = 0.1
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

# R17: a station stands at its city's place, which is the mean of the city's rows, or for the
# few cities whose rows are far apart one of them (architecture section 6). A station stop is
# drawn at the road point nearest its station, within the search radius (section 7). The
# 0.01 is room for the stop's coordinates, cut to 5 decimals.
NEAR_PLACE_MILES = SEARCH_RADIUS_MILES + 0.01
CITIES_CSV = Path(__file__).resolve().parent.parent / "data" / "us_cities.csv"
# The five places the architecture (section 6) adds by hand, because data/us_cities.csv lacks
# them: (city, state, lat, lng). A copy of the values in stations/places.py, not an import.
HAND_ADDED_PLACES = (
    ("Port Wentworth", "GA", 32.1491, -81.1632),
    ("Henrico", "VA", 37.5131, -77.3465),
    ("Evergreen", "AL", 31.4335, -86.9569),
    ("Elizabethport", "NJ", 40.6501, -74.1871),
    ("University Park", "IL", 41.4400, -87.6834),
)
# A city's key (architecture section 6): capitals, these short forms written out, letters only.
CITY_SHORT_FORMS = {"ST": "SAINT", "STE": "SAINTE", "FT": "FORT", "MT": "MOUNT"}

# (state code, city key) to the (lat, lng) of every place of that city, for R17.
Places = dict[tuple[str, str], list[tuple[float, float]]]

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


def places_from(rows: Iterable[tuple[str, str, float, float]]) -> Places:
    """(city, state, lat, lng) rows as the places R17 checks against. A caller whose
    stations are invented gives these, one row for each place its stations stand at."""
    places: Places = {}
    for city, state, lat, lng in rows:
        places.setdefault((state, _city_key(city)), []).append((float(lat), float(lng)))
    return places


@functools.cache
def default_places() -> Places:
    """R17's places when the caller gives none: every row of data/us_cities.csv, and the
    five places added by hand where the file has no such city, as the application adds
    them. Read once."""
    with open(CITIES_CSV, newline="", encoding="utf-8-sig") as f:
        rows = [
            (row["CITY"], row["STATE_CODE"], row["LATITUDE"], row["LONGITUDE"])
            for row in csv.DictReader(f)
        ]
    places = places_from(rows)
    for key, spots in places_from(HAND_ADDED_PLACES).items():
        places.setdefault(key, spots)
    return places


@dataclass(frozen=True)
class _Given:
    """What the caller gave beside the body, for the rules that need it."""

    prices: dict[str, Listing]
    stop_cost: object
    places: Places | None  # None: default_places()
    routing_hosts: frozenset[str]


def verify_response(
    body: dict,
    prices: dict[str, Listing],
    stop_cost=None,
    *,
    places: Places | None = None,
    routing_hosts: Iterable[str] = (),
) -> list[str]:
    """One line per broken rule, each starting with its ID ("R4: ..."); [] when all hold.

    `stop_cost` is what the request sent (text or number), or None if it sent none.
    `places` is what R17 checks station stops against, as places_from() makes it; None
    means default_places(). `routing_hosts` is a list of routing servers R15 accepts beside
    the two public ones, such as ["fake-osrm"], the stand-in of the end-to-end run; a bare
    string raises TypeError. Every rule is checked every time, so one broken rule never
    hides another.
    """
    if isinstance(routing_hosts, str):
        # A bare "fake-osrm" would otherwise be read as the set of its letters.
        raise TypeError("routing_hosts is a list of host names, not one name")
    given = _Given(prices, stop_cost, places, frozenset(routing_hosts))
    lines = []
    for rule, check in RULES:
        try:
            problems = check(body, given)
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


def _city_key(city: str) -> str:
    """A city's name as the places table matches it (architecture section 6): capitals, St,
    Ste, Ft and Mt (with or without a dot) written out, then letters only. So "St. Louis"
    and "Saint Louis" are one city, as are "Winston-Salem" and "Winston Salem"."""
    written_out = re.sub(
        r"\b(ST|STE|FT|MT)\b\.?", lambda m: CITY_SHORT_FORMS[m.group(1)], city.upper()
    )
    return re.sub(r"[^A-Z]", "", written_out)


def _miles_between(a, b) -> float:
    """Great-circle miles between two [lng, lat] pairs (haversine)."""
    lng1, lat1, lng2, lat2 = (math.radians(float(x)) for x in (*a, *b))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(min(1.0, h)))


# --- The rules: each returns the problems it found, [] when it holds ----------------------


def _r1_range(body, given):
    distance = _dec(body["summary"]["distance_miles"])
    marks = [_dec(stop["mile_marker"]) for stop in body["fuel_stops"]]
    problems = []
    for n, (here, there) in enumerate(zip(marks, [*marks[1:], distance], strict=True), 1):
        if there - here > RANGE_MILES:
            to = "the finish" if n == len(marks) else f"stop {n + 1}"
            problems.append(f"{there - here} miles from stop {n} (mile {here}) to {to}")
    return problems


def _r2_tank(body, given):
    # Walk the trip from mile 0 with an empty tank (D-1), burning a gallon per 10 miles.
    # The gallons are rounded as a running total, so the walk is exact: no allowance.
    problems = []
    tank, at = Decimal(0), Decimal(0)
    for n, stop in enumerate(body["fuel_stops"], 1):
        mile = _dec(stop["mile_marker"])
        tank -= (mile - at) / MILES_PER_GALLON
        at = mile
        if tank < 0:
            problems.append(f"tank at {tank} gallons on reaching stop {n} (mile {mile})")
        tank += _dec(stop["gallons"])
        if tank > TANK_GALLONS:
            problems.append(f"tank at {tank} gallons after stop {n}")
    tank -= (_dec(body["summary"]["distance_miles"]) - at) / MILES_PER_GALLON
    if tank < 0:
        problems.append(f"tank at {tank} gallons on reaching the finish")
    return problems


def _r3_gallons(body, given):
    summary = body["summary"]
    bought = sum(_dec(stop["gallons"]) for stop in body["fuel_stops"])
    gallons, distance = _dec(summary["gallons"]), _dec(summary["distance_miles"])
    problems = []
    if bought != gallons:
        problems.append(f"stops buy {bought} gallons, summary.gallons is {gallons}")
    if gallons != distance / MILES_PER_GALLON:
        problems.append(f"summary.gallons {gallons} is not distance_miles {distance} / 10")
    return problems


def _r4_money(body, given):
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


def _r5_prices_and_names(body, given):
    problems = []
    for n, stop in enumerate(body["fuel_stops"], 1):
        listing = given.prices.get(str(stop["station_id"]))
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


def _r6_stops(body, given):
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
    # A purchase that rounds to 0.00 gallons is not shown as a stop (architecture section 8),
    # except the fill-up at the start, which is always shown.
    gallons = [_dec(stop["gallons"]) for stop in stops]
    if gallons[0] < 0:
        problems.append(f"stop 1 buys {gallons[0]} gallons, less than 0")
    for n, amount in enumerate(gallons[1:], 2):
        if not amount > 0:
            problems.append(f"stop {n} buys {amount} gallons, not more than 0")
    return problems


def _r7_lowest_bill(body, given):
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


def _r8_stop_count(body, given):
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


def _r9_assumptions(body, given):
    stop_cost = given.stop_cost
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


def _r10_first_fill(body, given):
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


def _r11_map(body, given):
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


def _r12_stops_on_line(body, given):
    line = body["map"]["features"][0]["geometry"]["coordinates"]
    positions: dict[tuple, list[int]] = {}
    for i, (lng, lat) in enumerate(line):
        positions.setdefault((_dec(lng), _dec(lat)), []).append(i)
    # The line has a point every half mile of its own length, plus its end point, and its
    # markers are scaled so the end is distance_miles (architecture section 5). Its own
    # length is the half miles before the last point plus the last stretch along the road.
    # That stretch is at most half a mile and at least the straight line between the last
    # two points: less when the road bends there, by over 0.2 miles on a recorded road.
    distance = float(_dec(body["summary"]["distance_miles"]))
    shortest = 0.5 * (len(line) - 2) + _miles_between(line[-2], line[-1])
    longest = 0.5 * (len(line) - 1)
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
        mile = float(_dec(stop["mile_marker"]))
        low, high = (0.5 * previous * distance / length for length in (longest, shortest))
        if not low - MARKER_ON_LINE_MILES <= mile <= high + MARKER_ON_LINE_MILES:
            problems.append(
                f"stop {order} at mile {mile}, but line position {previous} is mile "
                f"{low:.2f} to {high:.2f}"
            )
    return problems


def _r13_line_spacing(body, given):
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
    # Points are half a mile apart, so a line repeats none, with one exception: the end point
    # can fall within a metre of the last half-mile point and be cut to the same 5 decimals
    # (every test road of a whole number of miles ends so). Repeats would let a line look
    # longer than it is, and R12 takes its scale from the number of points.
    repeats = [
        i
        for i, (a, b) in enumerate(pairwise(line[:-1]))
        if (_dec(a[0]), _dec(a[1])) == (_dec(b[0]), _dec(b[1]))
    ]
    if repeats:
        problems.append(f"repeated points: {len(repeats)}, the first after point {repeats[0]}")
    # A point every half mile plus the end point can be almost a whole point away from
    # 2d + 1. The road's own length and the routing service's figure for it differ too, by
    # 0.18% at most on the recorded roads.
    expected = 2 * distance + 1
    if abs(len(line) - expected) > max(expected * COUNT_SHARE, COUNT_POINTS):
        problems.append(
            f"{len(line)} line points, expected {expected} within {COUNT_SHARE:%} or "
            f"{COUNT_POINTS} points, whichever is larger"
        )
    return problems


def _r14_precision(body, given):
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


def _r15_meta(body, given):
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
    if meta["routing_server"] not in SERVERS | given.routing_hosts:
        problems.append(f"routing_server is {meta['routing_server']!r}")
    return problems


def _r16_labels(body, given):
    problems = []
    for place in ("start", "finish"):
        label = body["summary"][place]["label"]
        match = LABEL.fullmatch(label) if isinstance(label, str) else None
        if not match or match.group(1) not in LOWER_48_AND_DC:
            problems.append(
                f"summary.{place}.label {label!r} is not 'City, ST' in the lower 48 or DC"
            )
    return problems


def _r17_stations_near_their_places(body, given):
    # R12 puts a stop on the line; this puts its station near that point. Without it a
    # plan could buy at a station hundreds of miles from the road and draw it on the line.
    places = default_places() if given.places is None else given.places
    problems = []
    for stop in body["fuel_stops"]:
        if stop["kind"] != "station":
            continue
        where = f"stop {stop['order']} ({stop['city']}, {stop['state']})"
        rows = places.get((stop["state"], _city_key(stop["city"])))
        if not rows:
            problems.append(f"{where}: no such place in the places data")
            continue
        # Where the station can stand: the mean of the city's rows, or any one of them.
        mean = (sum(lat for lat, _ in rows) / len(rows), sum(lng for _, lng in rows) / len(rows))
        point = (stop["lng"], stop["lat"])
        nearest = min(_miles_between(point, (lng, lat)) for lat, lng in [mean, *rows])
        if nearest > NEAR_PLACE_MILES:
            problems.append(
                f"{where} is {nearest:.2f} miles from where a station of that place stands, "
                f"more than {NEAR_PLACE_MILES}"
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
    ("R17", _r17_stations_near_their_places),
)
