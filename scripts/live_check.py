"""Puts a running Mile Marker API through the live cases of docs/test-cases.md.

    uv run python scripts/live_check.py [--base-url http://127.0.0.1:8000] [--only P01,N03]
                                        [--markdown]

The cases are P01 to P20 and N01 to N26 (section 3) and S01 to S03 (section 5), kept below
as data: each one's request, expected status, and every figure or error code the document
names, in the document's own words for the table and as checks for the machine. The code
after them only sends requests, reads answers and compares.

It talks to the server over HTTP and reads the fuel CSV; it imports nothing from the
application. Every 200 is also checked against rules R1 to R16 by tests/verify.py, and every
error against the standard error body of backend-architecture.md, section 11.

Prints one line per case (with --markdown, one table row ready to paste into the document)
and exits 0 only if every case passed.
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
# Run as a script, Python only looks in scripts/; the verifier lives in tests/.
sys.path.insert(0, str(ROOT))
from tests.verify import load_prices, verify_response  # noqa: E402

D = Decimal
PRICES_CSV = ROOT / "data" / "fuel-prices-for-be-assessment.csv"

# Section 3: the routing servers ask for at most one request a second and the API allows 60
# a minute, so requests are spaced, and the rate-limit case waits for the window to empty.
GAP_SECONDS = 1.2
RATE_WINDOW_SECONDS = 60
# A routing call may take two attempts of 5 s each (NFR-12), plus our own work.
REQUEST_TIMEOUT_SECONDS = 30
NEAR = D("0.02")  # "≈ value, pass within 2%"


# --- The cases, as data -------------------------------------------------------------------


@dataclass(frozen=True)
class Ref:
    """A figure in an answer: a dotted path into the JSON body ("fuel_stops.0.name"), or the
    name of one of FIGURES. With `case`, it is read from that earlier case's answer."""

    path: str
    case: str | None = None


@dataclass(frozen=True)
class Check:
    """`figure op value`, for example summary.stops < 10. A plain string figure is a path in
    this case's answer; `value` is a literal or a Ref."""

    figure: str | Ref
    op: str
    value: object = None


@dataclass(frozen=True)
class Case:
    id: str
    uc: str
    request: str  # the Request (or, for S cases, Input) column, as the document writes it
    status: int | None  # None for S cases, which send nothing and read earlier answers
    expected: str  # the Expected column, word for word
    checks: tuple[Check, ...]
    sends: tuple[str, ...] = ()  # "METHOD /path?query", unencoded as the document shows it
    burst: int = 0  # send up to this many with no pause, stopping at the first `status`
    requirement: str = ""  # S cases: the Requirement column


C = Check


def plain(id: str, uc: str, url: str, status: int, expected: str, *checks: Check) -> Case:
    """The common case: one GET, shown in the table as its own URL."""
    return Case(id, uc, f"`{url}`", status, expected, checks, sends=(f"GET {url}",))


NY_LA = "/api/v1/route/?start=New York, NY&finish=Los Angeles, CA"
DAL_HOU = "/api/v1/route/?start=Dallas, TX&finish=Houston, TX"


def code(name: str) -> Check:
    return C("error.code", "==", name)


def fields_has(name: str) -> Check:
    return C("error.details.fields", "has", name)


CASES = [
    plain(
        "P01",
        "UC-01",
        NY_LA,
        200,
        "distance_miles ≈ 2,800.7, pass within 2%; stops fewer than 10 (design: 7); "
        "total_fuel_cost ≈ 865.93, pass within 2%; lowest_possible_fuel_cost ≈ 854.65, pass "
        "within 2%; first_fill_distance_miles ≈ 3.1, pass within 2%; warnings `[]`; labels "
        "`New York, NY`, `Los Angeles, CA`; routing_calls 1; cache_hit false",
        C("summary.distance_miles", "≈", D("2800.7")),
        C("summary.stops", "<", 10),
        C("summary.total_fuel_cost", "≈", D("865.93")),
        C("summary.lowest_possible_fuel_cost", "≈", D("854.65")),
        C("summary.first_fill_distance_miles", "≈", D("3.1")),
        C("warnings", "==", []),
        C("summary.start.label", "==", "New York, NY"),
        C("summary.finish.label", "==", "Los Angeles, CA"),
        C("meta.routing_calls", "==", 1),
        C("meta.cache_hit", "==", False),
    ),
    Case(
        "P02",
        "UC-04",
        "P01's request again",
        200,
        "summary identical to P01's; routing_calls 0; cache_hit true; round trip under 50 ms",
        (
            C("summary", "==", Ref("summary", "P01")),
            C("meta.routing_calls", "==", 0),
            C("meta.cache_hit", "==", True),
            C("round_trip_ms", "<", 50),
        ),
        sends=(f"GET {NY_LA}",),
    ),
    plain(
        "P03",
        "UC-03",
        f"{NY_LA}&stop_cost=0",
        200,
        "stops more than P01's (design: 17); total_fuel_cost equals P01's "
        "lowest_possible_fuel_cost and this response's own; assumptions.stop_cost 0.0; "
        "routing_calls 0; cache_hit false",
        C("summary.stops", ">", Ref("summary.stops", "P01")),
        C("summary.total_fuel_cost", "==", Ref("summary.lowest_possible_fuel_cost", "P01")),
        C("summary.total_fuel_cost", "==", Ref("summary.lowest_possible_fuel_cost")),
        C("assumptions.stop_cost", "==", D("0.0")),
        C("meta.routing_calls", "==", 0),
        C("meta.cache_hit", "==", False),
    ),
    plain(
        "P04",
        "UC-03",
        f"{NY_LA}&stop_cost=25",
        200,
        "stops no more than P01's (design: 6); total_fuel_cost not below P01's, ≈ 884.79, "
        "pass within 2%; routing_calls 0",
        C("summary.stops", "<=", Ref("summary.stops", "P01")),
        C("summary.total_fuel_cost", ">=", Ref("summary.total_fuel_cost", "P01")),
        C("summary.total_fuel_cost", "≈", D("884.79")),
        C("meta.routing_calls", "==", 0),
    ),
    plain(
        "P05",
        "UC-05",
        "/api/v1/route/?start=Los Angeles, CA&finish=New York, NY",
        200,
        "first_fill_distance_miles over 100, ≈ 121, pass within 2%; one warning, naming "
        "fuel_stops[0].name and the distance; routing_calls 1",
        C("summary.first_fill_distance_miles", ">", 100),
        C("summary.first_fill_distance_miles", "≈", D(121)),
        C("warnings", "len==", 1),
        C("warnings.0", "has", Ref("fuel_stops.0.name")),
        C("warnings.0", "has", Ref("summary.first_fill_distance_miles")),
        C("meta.routing_calls", "==", 1),
    ),
    plain(
        "P06",
        "UC-01",
        "/api/v1/route/?start=Seattle, WA&finish=Miami, FL",
        200,
        "distance_miles ≈ 3,301.2, pass within 2%; stops fewer than 12",
        C("summary.distance_miles", "≈", D("3301.2")),
        C("summary.stops", "<", 12),
    ),
    plain(
        "P07",
        "UC-01",
        "/api/v1/route/?start=Chicago, IL&finish=Houston, TX",
        200,
        "distance_miles ≈ 1,086.9, pass within 2%",
        C("summary.distance_miles", "≈", D("1086.9")),
    ),
    plain(
        "P08",
        "UC-02",
        DAL_HOU,
        200,
        "distance_miles ≈ 238.1, pass within 2%; total_fuel_cost above 0",
        C("summary.distance_miles", "≈", D("238.1")),
        C("summary.total_fuel_cost", ">", 0),
    ),
    plain(
        "P09",
        "UC-01",
        "/api/v1/route/?start=Boston, MA&finish=Washington, DC",
        200,
        "distance_miles ≈ 437.1, pass within 2%",
        C("summary.distance_miles", "≈", D("437.1")),
    ),
    plain(
        "P10",
        "UC-06",
        "/api/v1/route/?start=st. louis, mo&finish=Winston-Salem, North Carolina",
        200,
        "summary.start.label `Saint Louis, MO`; summary.finish.label `Winston Salem, NC`",
        C("summary.start.label", "==", "Saint Louis, MO"),
        C("summary.finish.label", "==", "Winston Salem, NC"),
    ),
    plain(
        "P11",
        "UC-06",
        "/api/v1/route/?start=Dallas TX&finish=Phoenix, Arizona, USA",
        200,
        "labels `Dallas, TX`, `Phoenix, AZ`",
        C("summary.start.label", "==", "Dallas, TX"),
        C("summary.finish.label", "==", "Phoenix, AZ"),
    ),
    plain(
        "P12",
        "UC-02",
        "/api/v1/route/?start=Fort Worth, TX&finish=Dallas, TX",
        200,
        "stops 1; fuel_stops[0] kind `start`, mile_marker 0.0, gallons = distance_miles ÷ 10; "
        "distance_miles under 50",
        C("summary.stops", "==", 1),
        C("fuel_stops.0.kind", "==", "start"),
        C("fuel_stops.0.mile_marker", "==", D("0.0")),
        C("fuel_stops.0.gallons", "==", Ref("distance_miles / 10")),
        C("summary.distance_miles", "<", 50),
    ),
    plain(
        "P13",
        "UC-05",
        "/api/v1/route/?start=Houston, TX&finish=Dallas, TX",
        200,
        "first_fill_distance_miles over 25; one warning",
        C("summary.first_fill_distance_miles", ">", 25),
        C("warnings", "len==", 1),
    ),
    plain(
        "P14",
        "UC-04",
        "/api/v1/route/?start=new york city, ny&finish=Los Angeles, California",
        200,
        "summary identical to P01's, labels `New York, NY` and `Los Angeles, CA`; "
        "routing_calls 0; cache_hit true",
        C("summary", "==", Ref("summary", "P01")),
        C("summary.start.label", "==", "New York, NY"),
        C("summary.finish.label", "==", "Los Angeles, CA"),
        C("meta.routing_calls", "==", 0),
        C("meta.cache_hit", "==", True),
    ),
    plain(
        "P15",
        "UC-03",
        f"{NY_LA}&stop_cost=100",
        200,
        "stops at least 6 and no more than P04's; total_fuel_cost not below P04's; "
        "assumptions.stop_cost 100.0; routing_calls 0",
        C("summary.stops", ">=", 6),
        C("summary.stops", "<=", Ref("summary.stops", "P04")),
        C("summary.total_fuel_cost", ">=", Ref("summary.total_fuel_cost", "P04")),
        C("assumptions.stop_cost", "==", D("100.0")),
        C("meta.routing_calls", "==", 0),
    ),
    plain(
        "P16",
        "UC-04",
        f"{DAL_HOU}&units=km",
        200,
        "summary identical to P08's; routing_calls 0; cache_hit true",
        C("summary", "==", Ref("summary", "P08")),
        C("meta.routing_calls", "==", 0),
        C("meta.cache_hit", "==", True),
    ),
    plain(
        "P17",
        "UC-06",
        "/api/v1/route/?start=Washington, D.C.&finish=Boston, MA",
        200,
        "summary.start.label `Washington, DC`",
        C("summary.start.label", "==", "Washington, DC"),
    ),
    plain(
        "P18",
        "UC-06",
        "/api/v1/route/?start=Santa Fe, New Mexico&finish=Denver, CO",
        200,
        "summary.start.label `Santa Fe, NM`",
        C("summary.start.label", "==", "Santa Fe, NM"),
    ),
    plain(
        "P19",
        "UC-02, UC-05",
        "/api/v1/route/?start=Los Angeles, CA&finish=Las Vegas, NV",
        200,
        "distance_miles ≈ 276.2, pass within 2%; stops 1; first_fill_distance_miles ≈ 121, "
        "pass within 2%; one warning",
        C("summary.distance_miles", "≈", D("276.2")),
        C("summary.stops", "==", 1),
        C("summary.first_fill_distance_miles", "≈", D(121)),
        C("warnings", "len==", 1),
    ),
    plain(
        "P20",
        "UC-02",
        "/api/v1/route/?start=Los Angeles, CA&finish=San Francisco, CA",
        200,
        "distance_miles under 500; stops 1; one warning",
        C("summary.distance_miles", "<", 500),
        C("summary.stops", "==", 1),
        C("warnings", "len==", 1),
    ),
    plain(
        "N01",
        "UC-15",
        "/api/v1/route/?start=New York, NY",
        400,
        "`invalid_request`; details.fields has `finish`",
        code("invalid_request"),
        fields_has("finish"),
    ),
    plain(
        "N02",
        "UC-15",
        "/api/v1/route/?start=&finish=Los Angeles, CA",
        400,
        "`invalid_request`; details.fields has `start`",
        code("invalid_request"),
        fields_has("start"),
    ),
    plain(
        "N03",
        "UC-07",
        "/api/v1/route/?start=Chicgo, IL&finish=Houston, TX",
        400,
        "`unknown_place`; field `start`; query `Chicgo, IL`; suggestions include "
        "`Chicago, IL`, at most 5",
        code("unknown_place"),
        C("error.details.field", "==", "start"),
        C("error.details.query", "==", "Chicgo, IL"),
        C("error.details.suggestions", "has", "Chicago, IL"),
        C("error.details.suggestions", "len<=", 5),
    ),
    plain(
        "N04",
        "UC-07",
        "/api/v1/route/?start=Dallas, TX&finish=Chicago",
        400,
        '`unknown_place`; field `finish`; suggestions `["Chicago, IL"]`',
        code("unknown_place"),
        C("error.details.field", "==", "finish"),
        C("error.details.suggestions", "==", ["Chicago, IL"]),
    ),
    plain(
        "N05",
        "UC-07",
        "/api/v1/route/?start=Dallas, TX&finish=Springfield, ZZ",
        400,
        "`unknown_place`; field `finish`; at most 5 suggestions",
        code("unknown_place"),
        C("error.details.field", "==", "finish"),
        C("error.details.suggestions", "len<=", 5),
    ),
    plain(
        "N06",
        "UC-08",
        "/api/v1/route/?start=Honolulu, HI&finish=Los Angeles, CA",
        422,
        "`outside_coverage`; field `start`; query `Honolulu, HI`",
        code("outside_coverage"),
        C("error.details.field", "==", "start"),
        C("error.details.query", "==", "Honolulu, HI"),
    ),
    plain(
        "N07",
        "UC-08",
        "/api/v1/route/?start=Seattle, WA&finish=Anchorage, AK",
        422,
        "`outside_coverage`; field `finish`",
        code("outside_coverage"),
        C("error.details.field", "==", "finish"),
    ),
    plain(
        "N08",
        "UC-08",
        "/api/v1/route/?start=Toronto, ON&finish=Buffalo, NY",
        422,
        "`outside_coverage`; field `start`",
        code("outside_coverage"),
        C("error.details.field", "==", "start"),
    ),
    plain(
        "N09",
        "UC-16",
        "/api/v1/route/?start=Dallas, TX&finish=dallas texas",
        400,
        "`invalid_request`; details.fields has `finish`",
        code("invalid_request"),
        fields_has("finish"),
    ),
    Case(
        "N10",
        "UC-15",
        f"`{NY_LA}&stop_cost=-1`, then with `101`, `abc`, `nan`",
        400,
        "`invalid_request`; details.fields has `stop_cost`",
        (code("invalid_request"), fields_has("stop_cost")),
        sends=tuple(f"GET {NY_LA}&stop_cost={v}" for v in ("-1", "101", "abc", "nan")),
    ),
    plain(
        "N11",
        "UC-09",
        "/api/v1/route/?start=Detroit, MI&finish=Buffalo, NY",
        422,
        "`route_leaves_usa`; miles_abroad ≈ 252, pass within 2%",
        code("route_leaves_usa"),
        C("error.details.miles_abroad", "≈", D(252)),
    ),
    plain(
        "N12",
        "UC-10",
        "/api/v1/route/?start=Los Angeles, CA&finish=Seattle, WA",
        422,
        "`no_fuel_plan`; gap_start_mile 0.0; gap_miles ≈ 886, pass within 2%",
        code("no_fuel_plan"),
        C("error.details.gap_start_mile", "==", D("0.0")),
        C("error.details.gap_miles", "≈", D(886)),
    ),
    Case(
        "N13",
        "UC-17",
        f"POST, then PUT, PATCH, DELETE: `{NY_LA}`",
        405,
        "`method_not_allowed`; standard error body",
        (code("method_not_allowed"),),
        sends=tuple(f"{method} {NY_LA}" for method in ("POST", "PUT", "PATCH", "DELETE")),
    ),
    plain(
        "N14",
        "UC-17",
        "/api/v1/routes/?start=New York, NY&finish=Los Angeles, CA",
        404,
        "`not_found`; standard error body",
        code("not_found"),
    ),
    Case(
        "N15",
        "UC-18",
        "P01's request repeated with no pause; run last",
        429,
        "`rate_limited` by the 61st at the latest; details.retry_after_seconds above 0",
        (
            code("rate_limited"),
            C("attempts", "<=", 61),
            C("error.details.retry_after_seconds", ">", 0),
        ),
        sends=(f"GET {NY_LA}",),
        burst=61,
    ),
    plain(
        "N16",
        "UC-07",
        "/api/v1/route/?start=Chicgo, IL&finish=Nowhere, ZZ",
        400,
        "`unknown_place`; field `start`",
        code("unknown_place"),
        C("error.details.field", "==", "start"),
    ),
    plain(
        "N17",
        "UC-15",
        "/api/v1/route/?start=Nowhere, ZZ",
        400,
        "`invalid_request` (the missing finish is found before places are looked up); "
        "details.fields has `finish`",
        code("invalid_request"),
        fields_has("finish"),
    ),
    plain(
        "N18",
        "UC-08",
        "/api/v1/route/?start=Tijuana, Mexico&finish=San Diego, CA",
        422,
        "`outside_coverage`; field `start`",
        code("outside_coverage"),
        C("error.details.field", "==", "start"),
    ),
    plain(
        "N19",
        "UC-08",
        "/api/v1/route/?start=Miami, FL&finish=San Juan, PR",
        422,
        "`outside_coverage`; field `finish`",
        code("outside_coverage"),
        C("error.details.field", "==", "finish"),
    ),
    plain(
        "N20",
        "UC-15",
        "/api/v1/route/?start=   &finish=Los Angeles, CA",
        400,
        "`invalid_request`; details.fields has `start`",
        code("invalid_request"),
        fields_has("start"),
    ),
    Case(
        "N21",
        "UC-15",
        f"`{NY_LA}&stop_cost=100.01`, then with `10.555`, then with `stop_cost=` empty",
        400,
        "`invalid_request`; details.fields has `stop_cost`",
        (code("invalid_request"), fields_has("stop_cost")),
        sends=tuple(f"GET {NY_LA}&stop_cost={v}" for v in ("100.01", "10.555", "")),
    ),
    plain(
        "N22",
        "UC-09",
        "/api/v1/route/?start=Detroit, MI&finish=Boston, MA",
        422,
        "`route_leaves_usa`; miles_abroad ≈ 234, pass within 2%",
        code("route_leaves_usa"),
        C("error.details.miles_abroad", "≈", D(234)),
    ),
    plain(
        "N23",
        "UC-10",
        "/api/v1/route/?start=San Francisco, CA&finish=Portland, OR",
        422,
        "`no_fuel_plan`; gap_start_mile 0.0; gap_miles ≈ 554, pass within 2%",
        code("no_fuel_plan"),
        C("error.details.gap_start_mile", "==", D("0.0")),
        C("error.details.gap_miles", "≈", D(554)),
    ),
    plain(
        "N24",
        "UC-15",
        "/api/v1/route/",
        400,
        "`invalid_request`; details.fields has `start` and `finish`",
        code("invalid_request"),
        fields_has("start"),
        fields_has("finish"),
    ),
    plain(
        "N25",
        "UC-16",
        "/api/v1/route/?start=New York City, NY&finish=Manhattan, NY",
        400,
        "`invalid_request`; details.fields has `finish`",
        code("invalid_request"),
        fields_has("finish"),
    ),
    plain(
        "N26",
        "UC-07",
        "/api/v1/route/?start=75201&finish=Dallas, TX",
        400,
        "`unknown_place`; field `start`",
        code("unknown_place"),
        C("error.details.field", "==", "start"),
    ),
    Case(
        "S01",
        "UC-01",
        "P01 and P06, each a new trip",
        None,
        "meta.timings_ms.own 100 or less; round trip minus meta.timings_ms.routing 100 ms or less",
        (
            C(Ref("meta.timings_ms.own", "P01"), "<=", 100),
            C(Ref("round_trip_ms - timings_ms.routing", "P01"), "<=", 100),
            C(Ref("meta.timings_ms.own", "P06"), "<=", 100),
            C(Ref("round_trip_ms - timings_ms.routing", "P06"), "<=", 100),
        ),
        requirement="NFR-1",
    ),
    Case(
        "S02",
        "UC-04",
        "P02",
        None,
        "Round trip under 50 ms; meta.timings_ms.total under 50; routing_calls 0",
        (
            C(Ref("round_trip_ms", "P02"), "<", 50),
            C(Ref("meta.timings_ms.total", "P02"), "<", 50),
            C(Ref("meta.routing_calls", "P02"), "==", 0),
        ),
        requirement="NFR-11",
    ),
    Case(
        "S03",
        "UC-03",
        "P03 (road cached, new stop cost)",
        None,
        "routing_calls 0; round trip 100 ms or less",
        (
            C(Ref("meta.routing_calls", "P03"), "==", 0),
            C(Ref("round_trip_ms", "P03"), "<=", 100),
        ),
        requirement="NFR-1, NFR-2",
    ),
]

# backend-architecture.md, section 11: each error code's status. The codes after it carry
# no details, so their `details` must be {} (EP-39).
STATUS_FOR_CODE = {
    "invalid_request": 400,
    "unknown_place": 400,
    "not_found": 404,
    "method_not_allowed": 405,
    "outside_coverage": 422,
    "route_leaves_usa": 422,
    "no_route": 422,
    "no_fuel_plan": 422,
    "rate_limited": 429,
    "internal_error": 500,
    "routing_unavailable": 502,
    "stations_not_loaded": 503,
}
WITHOUT_DETAILS = {
    "not_found",
    "method_not_allowed",
    "no_route",
    "internal_error",
    "stations_not_loaded",
}


# --- Asking ----------------------------------------------------------------------------------


@dataclass
class Answer:
    method: str
    url: str  # path and query, unencoded, as in the case
    status: int  # 0 when no answer came back at all
    body: object  # the JSON with exact decimals; None if there was no JSON
    ms: Decimal  # round trip, from sending the request to having the whole body
    attempts: int = 1
    note: str = ""  # why there is no answer, if there is none


def split(url: str) -> tuple[str, list[tuple[str, str]]]:
    """Path and query parameters of an unencoded URL. The document writes values such as
    `Washington, D.C.` and `   ` raw; httpx encodes them when sending."""
    path, _, query = url.partition("?")
    params = [pair.partition("=")[::2] for pair in query.split("&")] if query else []
    return path, params


class Asker:
    """Sends requests to the server, keeping the documented gap between them."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS)
        self.last_done = 0.0

    def ask(self, send: str, paced: bool = True) -> Answer:
        method, _, url = send.partition(" ")
        if paced:
            time.sleep(max(0.0, self.last_done + GAP_SECONDS - time.monotonic()))
        path, params = split(url)
        started = time.perf_counter()
        try:
            response = self.client.request(method, self.base_url + path, params=params)
        except httpx.HTTPError as exc:
            self.last_done = time.monotonic()
            return Answer(method, url, 0, None, D(0), note=f"{type(exc).__name__}: {exc}")
        ms = D(f"{(time.perf_counter() - started) * 1000:.1f}")
        self.last_done = time.monotonic()
        try:
            body = json.loads(response.text, parse_float=Decimal)
        except ValueError:
            body = None
        return Answer(method, url, response.status_code, body, ms)

    def burst(self, send: str, limit: int, until: int) -> tuple[Answer, list[Answer]]:
        """Up to `limit` requests back to back, stopping at the first with status `until`.
        Returns that last answer, its attempt number set, and the answers before it."""
        answers = []
        for _ in range(limit):
            answers.append(self.ask(send, paced=False))
            if answers[-1].status == until:
                break
        answers[-1].attempts = len(answers)
        return answers[-1], answers[:-1]


# --- Reading answers ---------------------------------------------------------------------


class Missing:
    def __repr__(self) -> str:
        return "missing"


MISSING = Missing()


def dig(body, path: str):
    value = body
    for part in path.split("."):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


# Figures that are not a path in the body.
FIGURES = {
    "attempts": lambda a: a.attempts,
    "round_trip_ms": lambda a: a.ms,
    "round_trip_ms - timings_ms.routing": lambda a: a.ms - dig(a.body, "meta.timings_ms.routing"),
    "distance_miles / 10": lambda a: dig(a.body, "summary.distance_miles") / 10,
}


def read(ref: Ref, answer: Answer | None, done: dict[str, Answer]):
    source = answer if ref.case is None else done.get(ref.case)
    if source is None:
        return MISSING
    try:
        figure = FIGURES.get(ref.path)
        return figure(source) if figure else dig(source.body, ref.path)
    except (KeyError, IndexError, TypeError, ValueError, ArithmeticError):
        return MISSING


def same(a, b) -> bool:
    # JSON false must not pass for 0, nor true for 1, as Python's == would let them.
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    return a == b


def contains(whole, part) -> bool:
    # Text holds a figure as the JSON wrote it, so a distance of 121.3 reads "121.3".
    return str(part) in whole if isinstance(whole, str) else part in whole


OPS = {
    "==": same,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "≈": lambda a, b: abs(a - b) <= abs(b) * NEAR,
    "has": contains,
    "len==": lambda a, b: len(a) == b,
    "len<=": lambda a, b: len(a) <= b,
}


def name(ref: Ref) -> str:
    return f"{ref.case}'s {ref.path}" if ref.case else ref.path


def as_ref(figure: str | Ref) -> Ref:
    return figure if isinstance(figure, Ref) else Ref(figure)


def label(check: Check) -> str:
    value = name(check.value) if isinstance(check.value, Ref) else show(check.value)
    op = {"≈": "≈", "len==": "count ==", "len<=": "count <="}.get(check.op, check.op)
    suffix = " (±2%)" if check.op == "≈" else ""
    return f"{name(as_ref(check.figure))} {op} {value}{suffix}"


def show(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, dict):
        return "{" + ", ".join(map(str, value)) + "}"
    if isinstance(value, list):
        # Quoted, because place names hold commas: ["Chicago, IL", "Cisco, IL"].
        return (
            "[" + ", ".join(json.dumps(v) if isinstance(v, str) else show(v) for v in value) + "]"
        )
    return str(value)


def judge(check: Check, answer: Answer | None, done: dict[str, Answer]) -> tuple[bool, str]:
    """Whether the check holds, and the actual figure as text."""
    actual = read(as_ref(check.figure), answer, done)
    expected = read(check.value, answer, done) if isinstance(check.value, Ref) else check.value
    if actual is MISSING or expected is MISSING:
        missing = check.figure if actual is MISSING else check.value
        ref = as_ref(missing)
        return False, f"{ref.case} not run" if ref.case and ref.case not in done else "missing"
    try:
        held = OPS[check.op](actual, expected)
    except TypeError:
        held = False
    if isinstance(actual, dict) and isinstance(check.value, Ref):
        # Whole sections are compared; name only the keys that differ.
        differ = [k for k in {**actual, **expected} if actual.get(k) != expected.get(k)]
        return held, "identical" if held else f"differs in {', '.join(differ)}"
    return held, show(actual)


def error_body_problems(status: int, body) -> list[str]:
    """backend-architecture.md, section 11: every error has the same body. EP-39 spells out
    what that means."""
    if not (isinstance(body, dict) and list(body) == ["error"] and isinstance(body["error"], dict)):
        return ['body is not {"error": {...}}']
    error = body["error"]
    if set(error) != {"code", "message", "details"}:
        return [f"error keys are {sorted(error)}, not code, message, details"]
    problems = []
    if STATUS_FOR_CODE.get(error["code"]) != status:
        problems.append(f"code {error['code']!r} does not belong to status {status}")
    if not (isinstance(error["message"], str) and error["message"].strip()):
        problems.append("message is empty")
    if not isinstance(error["details"], dict):
        problems.append("details is not an object")
    elif error["code"] in WITHOUT_DETAILS and error["details"]:
        problems.append(f"details should be empty for {error['code']}")
    return problems


# --- Running a case ----------------------------------------------------------------------


@dataclass
class Outcome:
    case: Case
    actual: str = ""
    failures: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures


def stop_cost_sent(url: str):
    """What the request sent as stop_cost, or None: the verifier's R9 needs it."""
    return dict(split(url)[1]).get("stop_cost")


def examine(case: Case, answer: Answer, prices, done) -> tuple[list[str], list[tuple[str, str]]]:
    """Failures and (figure, actual) pairs for one answer to a case that sends requests."""
    if answer.status == 0:
        return [f"no answer ({answer.note})"], []
    failures = []
    if answer.status != case.status:
        failures.append(f"status {answer.status}, expected {case.status}")
    if answer.status == 200 and isinstance(answer.body, dict):
        failures += verify_response(answer.body, prices, stop_cost_sent(answer.url))
    elif answer.status != 200:
        failures += [f"error body: {p}" for p in error_body_problems(answer.status, answer.body)]
    figures = []
    for check in case.checks:
        held, actual = judge(check, answer, done)
        if not held:
            failures.append(f"{label(check)} (actual {actual})")
        if check.figure not in ("error.code", "attempts"):
            figures.append((name(as_ref(check.figure)), actual))
    return failures, figures


def headline(answer: Answer) -> str:
    """Status, and the error code if there is one."""
    if answer.status == 0:
        return "no answer"
    try:
        return f"{answer.status} {answer.body['error']['code']}"
    except (KeyError, TypeError):
        return str(answer.status)


def run(case: Case, asker: Asker, prices, done: dict[str, Answer]) -> Outcome:
    outcome = Outcome(case)
    if not case.sends:  # an S case: it reads answers that earlier cases received
        results = [judge(check, None, done) for check in case.checks]
        outcome.failures = [
            f"{label(check)} (actual {actual})"
            for check, (held, actual) in zip(case.checks, results, strict=True)
            if not held
        ]
        outcome.actual = "; ".join(
            f"{name(as_ref(check.figure))} {actual}"
            for check, (_, actual) in zip(case.checks, results, strict=True)
        )
        return outcome

    answers, before = [], []
    for send in case.sends:
        if case.burst:
            last, before = asker.burst(send, case.burst, case.status)
            answers.append(last)
        else:
            answers.append(asker.ask(send))

    figures: dict[str, list[str]] = {}
    for n, answer in enumerate(answers, 1):
        failures, found = examine(case, answer, prices, done)
        where = f"request {n} ({answer.method} {answer.url}): " if len(answers) > 1 else ""
        outcome.failures += [where + failure for failure in failures]
        for figure, actual in found:
            figures.setdefault(figure, []).append(actual)

    # The burst's earlier answers are P01's 200s; each is still a 200, so it is verified.
    for n, answer in enumerate(before, 1):
        if answer.status != 200:
            outcome.failures.append(f"burst request {n}: status {answer.status}, before any 429")
        elif lines := verify_response(answer.body, prices, stop_cost_sent(answer.url)):
            outcome.failures += [f"burst request {n}: {line}" for line in lines]

    heads = [headline(answer) for answer in answers]
    status = heads[0] if len(set(heads)) == 1 else " / ".join(heads)
    if len(answers) > 1 and len(set(heads)) == 1:
        status += f" (all {len(answers)})"
    if case.burst:
        status += f" at request {answers[0].attempts}"
    parts = [status]
    for figure, values in figures.items():
        shown = values[0] if len(set(values)) == 1 else " / ".join(values)
        parts.append(f"{figure} {shown}")
    if answers[-1].status == 200 and "round_trip_ms" not in figures:
        parts.append(f"round trip {answers[-1].ms} ms")
    outcome.actual = "; ".join(parts)
    done[case.id] = answers[-1]
    return outcome


# --- Printing --------------------------------------------------------------------------


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def line(outcome: Outcome, markdown: bool) -> str:
    case = outcome.case
    result = "PASS" if outcome.passed else "FAIL: " + "; ".join(outcome.failures)
    if not markdown:
        return " | ".join((case.id, case.request, case.expected, outcome.actual, result))
    if case.requirement:  # section 5's columns: ID, UC, Requirement, Input, Expected, ...
        first = (case.id, case.uc, case.requirement, case.request)
    else:  # section 3's: ID, UC, Request, Status, Expected, ...
        each = " each" if len(case.sends) > 1 else ""
        first = (case.id, case.uc, case.request, f"{case.status}{each}")
    cells = (*first, case.expected, outcome.actual, result)
    return "| " + " | ".join(cell(c) for c in cells) + " |"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--only", help="comma-separated case IDs, such as P01,N03")
    parser.add_argument("--markdown", action="store_true", help="print table rows")
    args = parser.parse_args(argv)
    # The cases quote the document's "≈" and "÷"; a Windows console would refuse them.
    sys.stdout.reconfigure(encoding="utf-8")

    chosen = CASES
    if args.only:
        wanted = {i.strip().upper() for i in args.only.split(",") if i.strip()}
        unknown = wanted - {case.id for case in CASES}
        if unknown:
            parser.error(f"no such case: {', '.join(sorted(unknown))}")
        chosen = [case for case in CASES if case.id in wanted]

    # Section 3's order: every case that sends requests, then the burst after the rate-limit
    # window has emptied so it counts only its own requests, then the S cases, which only
    # read answers already received.
    order = (
        [case for case in chosen if case.sends and not case.burst]
        + [case for case in chosen if case.burst]
        + [case for case in chosen if not case.sends]
    )
    prices = load_prices(PRICES_CSV)
    asker = Asker(args.base_url)
    done: dict[str, Answer] = {}
    outcomes = []
    for case in order:
        if case.burst:
            time.sleep(RATE_WINDOW_SECONDS)
        outcomes.append(run(case, asker, prices, done))
        print(line(outcomes[-1], args.markdown), flush=True)

    failed = [o.case.id for o in outcomes if not o.passed]
    print(
        f"\n{len(outcomes)} cases: {len(outcomes) - len(failed)} passed, {len(failed)} failed"
        + (f" ({', '.join(failed)})" if failed else ""),
        flush=True,
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
