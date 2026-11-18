"""Tests for the routing client (RT-01 to RT-14, and QB-04 to QB-06, QB-16 and QB-23 of
docs/test-cases.md, section 9.13). Every request goes to httpx.MockTransport."""

import threading
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
# Both points snapped to one spot on the road: a route of length zero.
ZERO_LENGTH_ANSWER = {
    "code": "Ok",
    "routes": [
        {
            "distance": 0,
            "geometry": {
                "type": "LineString",
                "coordinates": [[-96.80439, 32.790439], [-96.80439, 32.790439]],
            },
        }
    ],
}


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


def test_qb16_two_first_requests_share_one_client(monkeypatch):
    """Review 9-Q0b, note N8. Two requests that both find no shared client yet must not
    each make one: the one made in vain would never be closed. Making a client is slowed
    here, so without a lock both threads would be making one at the same time."""
    from trips.services import routing

    made = []
    real_client = httpx.Client

    def slow_client(**options):
        time.sleep(0.2)
        made.append(real_client(**options))
        return made[-1]

    monkeypatch.setattr(routing, "_shared_client", None)
    monkeypatch.setattr(httpx, "Client", slow_client)
    start_together = threading.Barrier(2)
    got = []

    def first_request():
        start_together.wait()
        got.append(routing._get_shared_client())

    threads = [threading.Thread(target=first_request) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    for client in made:
        client.close()

    assert len(made) == 1
    assert got == [made[0], made[0]]


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


def test_any_other_refusal_ends_the_request_at_once():
    """Review 5Q2, finding 5, and QB-06. A 400 that is not "no road" means the request
    itself is wrong, and the second server would refuse it too (architecture section 9),
    so it is not asked."""
    invalid = {"code": "InvalidQuery", "message": "Query string malformed close to position 9"}
    fake = Fake(httpx.Response(400, json=invalid), None)
    with pytest.raises(RoutingUnavailable) as caught:
        fake.fetch()
    assert caught.value.details["reason"] == "error"
    assert len(fake.requests) == 1


@pytest.mark.parametrize(
    "answer",
    [
        httpx.Response(302, headers={"Location": "https://router.project-osrm.org/elsewhere"}),
        httpx.Response(403),
        httpx.Response(404),
    ],
    ids=["302", "403", "404"],
)
def test_qb04_an_answer_about_one_server_tries_the_other(answer):
    """Review 9-Q0b, finding Q0b-3. A redirect, a refusal of this client, or a path that is
    not there concerns the server that answered, not the request. The second server is
    there for exactly that."""
    route = Fake(answer, ok()).fetch()
    assert route.server == SERVER_2
    assert route.calls == 2


@pytest.mark.parametrize("status", [204, 301, 307, 408, 410, 451])
def test_qb05_any_other_answer_that_is_not_a_route_tries_the_other(status):
    route = Fake(httpx.Response(status), ok()).fetch()
    assert route.calls == 2


def test_qb23_no_road_is_final_whatever_the_status_below_500():
    """Review 10R, finding R10-09. "No road" is read from the body, short of a server
    error: a 404 carrying it ends the request with NoRoute, server 2 never asked."""
    fake = Fake(httpx.Response(404, json=NO_ROUTE_ANSWER), None)
    with pytest.raises(NoRoute):
        fake.fetch()
    assert len(fake.requests) == 1


def test_qb23_a_server_error_saying_no_road_tries_the_other():
    """R10-09: a 5xx is the server's own trouble, whatever its body says."""
    route = Fake(httpx.Response(503, json=NO_ROUTE_ANSWER), ok()).fetch()
    assert route.server == SERVER_2
    assert route.calls == 2


def test_a_road_of_length_zero_is_a_route():
    """Review 5Q2, finding 5. The planner, not the client, decides what a zero-length road
    means: start and finish are the same place (EP-20)."""
    fake = Fake(httpx.Response(200, json=ZERO_LENGTH_ANSWER), None)
    route = fake.fetch()
    assert route.distance_miles == 0.0
    assert route.coords.shape == (2, 2)
    assert route.calls == 1
