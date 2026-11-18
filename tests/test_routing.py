"""Tests for the routing client (RT-01 to RT-14). Every one uses httpx.MockTransport."""

import time

import httpx
import numpy as np
import pytest

from trips.exceptions import NoRoute, RoutingUnavailable
from trips.services.routing import fetch_route

START = (32.790439, -96.80439)
FINISH = (29.7652, -95.3657)
SERVER_1 = "router.project-osrm.org"
SERVER_2 = "routing.openstreetmap.de"

OK_ANSWER = {
    "code": "Ok",
    "routes": [
        {
            "distance": 1609344.0,
            "geometry": {
                "type": "LineString",
                "coordinates": [[-96.80439, 32.790439], [-95.3657, 29.7652]],
            },
        }
    ],
}
NO_ROUTE_ANSWER = {"code": "NoRoute", "message": "No route found between points"}


def ok() -> httpx.Response:
    return httpx.Response(200, json=OK_ANSWER)


def timeout(request: httpx.Request) -> httpx.Response:
    raise httpx.ReadTimeout("too slow", request=request)


def refuse(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("refused", request=request)


class Fake:
    """A fake routing service: one behaviour per server host, and a log of the requests."""

    def __init__(self, server_1, server_2=None):
        self.behaviours = {SERVER_1: server_1, SERVER_2: server_2}
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        behaviour = self.behaviours[request.url.host]
        if behaviour is None:
            raise AssertionError(f"{request.url.host} should not have been called")
        return behaviour(request) if callable(behaviour) else behaviour

    def client(self) -> httpx.Client:
        return httpx.Client(
            transport=httpx.MockTransport(self), headers={"User-Agent": "milemarker-api"}
        )

    def fetch(self):
        return fetch_route(START, FINISH, client=self.client())


def test_rt01_request_address(settings):
    fake = Fake(ok())
    fake.fetch()
    assert len(fake.requests) == 1
    url = fake.requests[0].url
    assert fake.requests[0].method == "GET"
    assert f"{url.scheme}://{url.host}{url.path}" == (
        "https://router.project-osrm.org/route/v1/driving/-96.80439,32.790439;-95.3657,29.7652"
    )
    assert url.query.decode() == "overview=full&geometries=geojson"


def test_rt02_route_result():
    route = Fake(ok()).fetch()
    assert route.distance_miles == 1000.0
    assert route.coords.shape == (2, 2)
    assert np.array_equal(route.coords, [[-96.80439, 32.790439], [-95.3657, 29.7652]])
    assert route.server == SERVER_1
    assert route.calls == 1


def test_rt03_server_error_tries_second_server():
    fake = Fake(httpx.Response(503), ok())
    route = fake.fetch()
    assert len(fake.requests) == 2
    url = fake.requests[1].url
    assert f"{url.scheme}://{url.host}{url.path}" == (
        "https://routing.openstreetmap.de/routed-car/route/v1/driving/"
        "-96.80439,32.790439;-95.3657,29.7652"
    )
    assert url.query.decode() == "overview=full&geometries=geojson"
    assert route.server == SERVER_2
    assert route.calls == 2


def test_rt04_too_many_requests_tries_second_server():
    route = Fake(httpx.Response(429), ok()).fetch()
    assert route.calls == 2


def test_rt05_timeout_tries_second_server():
    route = Fake(timeout, ok()).fetch()
    assert route.calls == 2


def test_rt06_refused_connection_tries_second_server():
    route = Fake(refuse, ok()).fetch()
    assert route.calls == 2


@pytest.mark.parametrize(
    "bad_answer",
    [
        httpx.Response(200, content=b"<html>not json</html>"),
        httpx.Response(200, json={"code": "Ok"}),
    ],
    ids=["not_json", "no_routes"],
)
def test_rt07_unreadable_answer_tries_second_server(bad_answer):
    route = Fake(bad_answer, ok()).fetch()
    assert route.calls == 2


@pytest.mark.parametrize("status", [400, 200])
def test_rt08_no_route_is_final(status):
    """OSRM answers "no road" with status 400; the code decides, whatever the status."""
    fake = Fake(httpx.Response(status, json=NO_ROUTE_ANSWER), None)
    with pytest.raises(NoRoute):
        fake.fetch()
    assert len(fake.requests) == 1


def test_rt08_no_segment_is_final_too():
    fake = Fake(httpx.Response(400, json={"code": "NoSegment"}), None)
    with pytest.raises(NoRoute):
        fake.fetch()
    assert len(fake.requests) == 1


def test_rt09_both_servers_error():
    fake = Fake(httpx.Response(500), httpx.Response(500))
    with pytest.raises(RoutingUnavailable) as caught:
        fake.fetch()
    assert caught.value.details["reason"] == "error"
    assert len(fake.requests) == 2


def test_rt10_both_servers_time_out():
    fake = Fake(timeout, timeout)
    with pytest.raises(RoutingUnavailable) as caught:
        fake.fetch()
    assert caught.value.details["reason"] == "timeout"
    assert len(fake.requests) == 2


class SlowBody(httpx.SyncByteStream):
    """A body that drips out for a full second, a few bytes at a time."""

    def __iter__(self):
        for _ in range(50):
            time.sleep(0.02)
            yield b" "


def slow(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, stream=SlowBody())


def test_rt11_total_deadline(settings):
    settings.ROUTING_DEADLINE_SECONDS = 0.2
    fake = Fake(slow, slow)
    started = time.monotonic()
    with pytest.raises(RoutingUnavailable) as caught:
        fake.fetch()
    assert time.monotonic() - started < 0.6
    assert caught.value.details["reason"] == "timeout"
    assert len(fake.requests) == 2


def test_rt12_user_agent_header():
    fake = Fake(httpx.Response(503), ok())
    fake.fetch()
    assert [r.headers["User-Agent"] for r in fake.requests] == ["milemarker-api"] * 2


def test_rt12_shared_client_sends_user_agent(monkeypatch):
    """With no client argument, the module's own client carries the configured name."""
    from trips.services import routing

    monkeypatch.setattr(routing, "_shared_client", None)
    shared = routing._get_shared_client()
    assert shared.headers["User-Agent"] == "milemarker-api"
    assert routing._get_shared_client() is shared
    shared.close()


def test_rt13_server_template_setting(settings):
    settings.ROUTING_SERVERS = [
        "https://example.test/route/{coords}?overview=full&geometries=geojson",
        *settings.ROUTING_SERVERS[1:],
    ]
    fake = Fake(ok())
    fake.behaviours["example.test"] = ok()
    route = fake.fetch()
    assert fake.requests[0].url.host == "example.test"
    assert route.server == "example.test"


def test_rt14_reason_is_timeout_only_if_every_attempt_timed_out():
    with pytest.raises(RoutingUnavailable) as first:
        Fake(timeout, httpx.Response(500)).fetch()
    with pytest.raises(RoutingUnavailable) as second:
        Fake(httpx.Response(500), timeout).fetch()
    assert first.value.details["reason"] == "error"
    assert second.value.details["reason"] == "error"
