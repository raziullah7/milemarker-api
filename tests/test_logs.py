"""The log lines and the request ID: cases CF-13 to CF-15 and CF-36 of docs/test-cases.md,
section 9.2 (architecture section 18, "Logs").

The lines are read as the API writes them: from the console handler of the settings'
LOGGING, its stream swapped for one the test reads.
"""

import io
import logging
import re
from decimal import Decimal

import pytest

from tests.test_api import TRIP, URL, read
from trips.services import routing

# A time, a level and the request's ID in brackets, then the logger and the message.
LINE = re.compile(
    r"^(?P<time>\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3}) (?P<level>[A-Z]+) "
    r"\[(?P<id>[^\]]+)\] (?P<logger>[\w.]+): (?P<message>.*)$"
)
TRIP_LINE = re.compile(
    r'^trip start="(?P<start>[^"]+)" finish="(?P<finish>[^"]+)" stop_cost=(?P<stop_cost>\S+) '
    r"miles=(?P<miles>\S+) stops=(?P<stops>\d+) total=(?P<total>\S+) "
    r"routing_calls=(?P<routing_calls>\d) cache_hit=(?P<cache_hit>true|false) "
    r"own_ms=(?P<own_ms>\S+)$"
)


@pytest.fixture
def log():
    """The API's log while the test runs: log() gives the lines written so far, each parsed
    by LINE (lines that are not, such as a traceback's, are kept as plain text)."""
    [handler] = [h for h in logging.getLogger().handlers if h.name == "console"]
    stream = io.StringIO()
    previous = handler.setStream(stream)

    def lines() -> list:
        return [LINE.match(line) or line for line in stream.getvalue().splitlines()]

    yield lines
    handler.setStream(previous)


def records(log) -> list[re.Match]:
    """The log's lines that start a record: those with a time, a level and an ID."""
    return [line for line in log() if isinstance(line, re.Match)]


def test_cf13_the_request_id_sent_is_on_every_line_and_the_answer(client, log, ep01_world):
    response = client.get(URL, TRIP, headers={"X-Request-ID": "cf-13"})

    assert response.status_code == 200
    assert response["X-Request-ID"] == "cf-13"
    lines = log()
    assert lines
    for line in lines:
        assert isinstance(line, re.Match), line
        assert line["id"] == "cf-13"


def test_cf14_with_no_request_id_the_api_makes_one(client, log, ep01_world):
    first = client.get(URL, TRIP)
    first_lines = records(log)
    second = client.get(URL, TRIP)
    second_lines = records(log)[len(first_lines) :]

    ids = first["X-Request-ID"], second["X-Request-ID"]
    assert all(ids)
    assert ids[0] != ids[1]
    assert first_lines
    assert second_lines
    assert {line["id"] for line in first_lines} == {ids[0]}
    assert {line["id"] for line in second_lines} == {ids[1]}


# Ruling on 11K's report: a sent ID is used only if it is 1 to 64 letters, digits, ".", "_"
# and "-". The ID is written into every line of the request, and the API can be reached with
# no nginx in front. A request refused before any lookup, so it needs no stations.
ROUTING_FREE = {"start": "Dallas, TX"}


@pytest.mark.parametrize("sent", ["nginx.ID_42-x", "a" * 64, "0123456789abcdef0123456789abcdef"])
def test_a_well_formed_request_id_is_kept(client, log, sent):
    response = client.get(URL, ROUTING_FREE, headers={"X-Request-ID": sent})

    assert response["X-Request-ID"] == sent
    assert [line["id"] for line in records(log)] == [sent]


@pytest.mark.parametrize(
    "sent", ["a" * 65, "has space", "[bracket]", ""], ids=["too long", "space", "bracket", "empty"]
)
def test_any_other_request_id_is_replaced_by_the_apis_own(client, log, sent):
    response = client.get(URL, ROUTING_FREE, headers={"X-Request-ID": sent})

    made = response["X-Request-ID"]
    assert re.fullmatch(r"[0-9a-f]{32}", made), made
    assert [line["id"] for line in records(log)] == [made]


def test_cf15_one_line_per_planned_trip(client, log, ep01_world):
    body = read(client.get(URL, TRIP, headers={"X-Request-ID": "cf-15"}))

    [line] = [line for line in records(log) if line["logger"] == "trips"]
    assert (line["level"], line["id"]) == ("INFO", "cf-15")
    trip = TRIP_LINE.match(line["message"])
    assert trip, line["message"]
    assert (trip["start"], trip["finish"], trip["stop_cost"]) == ("Dallas, TX", "Houston, TX", "10")
    assert (trip["routing_calls"], trip["cache_hit"]) == ("1", "false")
    summary = body["summary"]
    # As numbers: the body is read with exact decimals.
    assert Decimal(trip["miles"]) == summary["distance_miles"] == 990
    assert int(trip["stops"]) == summary["stops"] == 3
    assert Decimal(trip["total"]) == summary["total_fuel_cost"]
    assert Decimal(trip["own_ms"]) == body["meta"]["timings_ms"]["own"]


def test_cf36_every_200_and_every_error_is_logged_once(client, log, monkeypatch, ep01_world):
    client.get(URL, TRIP)
    client.get(URL, TRIP)
    trips = [TRIP_LINE.match(line["message"]) for line in records(log) if line["logger"] == "trips"]
    assert [(t["routing_calls"], t["cache_hit"]) for t in trips] == [("1", "false"), ("0", "true")]

    before = len(records(log))
    client.get(URL, {"start": "Chicgo, IL", "finish": "Houston, TX"})
    [line] = records(log)[before:]
    assert line["level"] == "WARNING"
    assert "unknown_place" in line["message"]
    for figure in ("miles=", "stops=", "total="):
        assert figure not in line["message"]

    def fail(start, finish):
        raise RuntimeError("boom")

    monkeypatch.setattr(routing, "fetch_route", fail)
    before = len(records(log))
    client.get(URL, {"start": "Houston, TX", "finish": "Dallas, TX"})  # a road not cached
    [line] = records(log)[before:]
    assert line["level"] == "ERROR"
    # In full: the traceback follows the line.
    assert any("RuntimeError: boom" in str(text) for text in log())
