"""Host checking, the middleware and the client's address: cases HM-01 to HM-10 of
docs/test-cases.md, section 9.5.

The Django test client sends the Host each case names. The routing call is replaced by
EP-01's fake (tests/conftest.py, ep01_world), and the stations come from PostgreSQL.
"""

import json
from io import StringIO

import pytest
from django.conf import settings as django_settings
from django.core.management import call_command
from django.urls import get_resolver

from tests.conftest import SMALL_CSV
from tests.test_api import TRIP, URL, assert_error, read, without_meta
from tests.test_project import settings_with

pytestmark = pytest.mark.django_db

HEALTH = "/api/v1/health/"
# Answered 400 invalid_request before any place lookup or routing call (section 9.1).
ROUTING_FREE = {"start": "Dallas, TX"}


@pytest.fixture
def small_csv() -> None:
    """The small CSV in the table, so health has stations to count."""
    from stations.index import reset_index

    call_command("load_stations", "--csv", str(SMALL_CSV), stdout=StringIO())
    reset_index()
    yield
    reset_index()


def assert_refused_host(response) -> None:
    """HM-02: 400 invalid_request in the error shape with empty details, as JSON."""
    assert response.status_code == 400
    assert response["Content-Type"] == "application/json"
    body = json.loads(response.content)
    assert body["error"]["code"] == "invalid_request"
    assert body["error"]["message"].strip()
    assert body["error"]["details"] == {}
    assert list(body) == ["error"]


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "[::1]", "127.0.0.1:8000"])
def test_hm01_the_default_hosts_are_answered(client, small_csv, host):
    assert client.get(HEALTH, headers={"host": host}).status_code == 200


@pytest.mark.parametrize("debug", [False, True])
@pytest.mark.parametrize(
    ("path", "params"),
    [(URL, TRIP), (HEALTH, {}), ("/nowhere", {})],
    ids=["route", "health", "nowhere"],
)
def test_hm02_a_foreign_host_gets_400_in_the_error_shape(
    client, settings, ep01_world, debug, path, params
):
    settings.DEBUG = debug

    assert_refused_host(client.get(path, params, headers={"host": "evil.example"}))
    assert ep01_world.calls == 0


def test_hm03_allowed_hosts_from_the_setting(client, settings, small_csv):
    settings.ALLOWED_HOSTS = ["api.example"]

    assert client.get(HEALTH, headers={"host": "api.example"}).status_code == 200
    assert_refused_host(client.get(HEALTH, headers={"host": "localhost"}))


def test_127_0_0_1_is_answered_whatever_the_variable_says(client, settings, small_csv):
    """Q1-02: the container's health check asks under 127.0.0.1. Set to the deployment's own
    name alone, the variable would refuse it, and the stack would never be healthy. The host
    names come from config/settings.py as a new process reads them from the variable."""
    settings.ALLOWED_HOSTS = settings_with(DJANGO_ALLOWED_HOSTS="api.example")["ALLOWED_HOSTS"]

    assert client.get(HEALTH, headers={"host": "api.example"}).status_code == 200
    assert client.get(HEALTH, headers={"host": "127.0.0.1"}).status_code == 200
    assert_refused_host(client.get(HEALTH, headers={"host": "other.example"}))


def test_hm04_both_forms_of_the_route_answer_with_no_redirect(client, ep01_world):
    with_slash = client.get(URL, TRIP)
    without_slash = client.get(URL.rstrip("/"), TRIP)

    assert (with_slash.status_code, without_slash.status_code) == (200, 200)
    assert without_meta(read(with_slash)) == without_meta(read(without_slash))


@pytest.mark.parametrize("path", ["/api/v1/routes", "/api/v1/routes/"])
def test_hm05_a_near_miss_is_404_not_a_redirect(client, path):
    assert assert_error(client.get(path), "not_found") == {}


def test_hm06_middleware_slash_redirect_and_error_handlers():
    assert "django.middleware.security.SecurityMiddleware" in django_settings.MIDDLEWARE
    assert "django.middleware.common.CommonMiddleware" in django_settings.MIDDLEWARE
    assert django_settings.APPEND_SLASH is False

    import config.urls

    assert config.urls.handler400 == "trips.views.bad_request"
    assert not hasattr(config.urls, "handler403")  # nothing in the API can answer 403
    view = get_resolver().resolve_error_handler(400)
    from django.core.exceptions import SuspiciousOperation
    from django.test import RequestFactory

    response = view(RequestFactory().get("/"), exception=SuspiciousOperation("bad"))
    assert_refused_host(response)


def test_hm07_behind_one_proxy_each_forwarded_address_is_its_own_client(client, settings):
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": 1}

    def send(address: str) -> int:
        return client.get(URL, ROUTING_FREE, headers={"X-Forwarded-For": address}).status_code

    assert 429 not in [send("203.0.113.1") for _ in range(60)]
    assert send("203.0.113.2") == 400  # another client, another bucket (Q0a-04)
    assert send("203.0.113.1") == 429


def test_hm08_with_no_proxy_trusted_the_forwarded_address_is_ignored(client):
    statuses = [
        client.get(URL, ROUTING_FREE, headers={"X-Forwarded-For": f"203.0.113.{n}"}).status_code
        for n in range(61)
    ]

    assert 429 not in statuses[:60]
    assert statuses[60] == 429


def compact(response) -> bool:
    """Whether the body is written in the one compact form: no space after a ":" or a ","
    outside strings (Q0a-24)."""
    body = json.loads(response.content)
    return response.content == json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode()


def test_hm09_every_error_body_is_compact(client, settings, small_csv):
    assert compact(client.get("/nowhere"))
    assert compact(client.get(URL, ROUTING_FREE))
    assert compact(client.get(HEALTH, headers={"host": "evil.example"}))
    settings.DEBUG = True
    assert compact(client.get("/nowhere"))


def test_hm10_django_sets_the_security_headers_on_every_answer(client, ep01_world):
    answers = [
        client.get(URL, TRIP),
        client.get("/nowhere"),
        client.get(URL, {"start": "Chicgo, IL", "finish": "Houston, TX"}),
        client.get(HEALTH),
    ]

    assert [a.status_code for a in answers] == [200, 404, 400, 200]
    for answer in answers:
        assert answer["X-Content-Type-Options"] == "nosniff"
        assert answer["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert answer["X-Frame-Options"] == "DENY"


# Of section 9.6, the front door, the two cases whose point the API settles alone. The rest
# need a reverse proxy, which is not part of this submission.


def test_px16_no_cross_origin_headers(client, ep01_world):
    """PX-16, the API's part: nothing is meant to call the API from another origin (D-17),
    so the API grants no other origin anything."""
    other = {"Origin": "http://other.example"}
    answers = [
        client.get(URL, TRIP, headers=other),
        client.get(URL, {"start": "Chicgo, IL", "finish": "Houston, TX"}, headers=other),
    ]

    assert [a.status_code for a in answers] == [200, 400]
    for answer in answers:
        assert not [name for name in answer.headers if name.lower().startswith("access-control-")]


def test_px17_no_redirect_to_https_and_no_hsts(client, ep01_world):
    """PX-17, the API's part: TLS, HSTS and the redirect belong to what is put in front (D-23)."""
    for response in (client.get(URL, TRIP), client.get(HEALTH)):
        assert response.status_code == 200
        assert "Strict-Transport-Security" not in response.headers
