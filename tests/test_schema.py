"""The OpenAPI document and the Swagger page: cases HS-09 to HS-17 of docs/test-cases.md,
section 9.4, and the committed copy, docs/openapi.yaml, held to the code.

The document is produced from the code (trips/schema.py and the views) and read back from
the schema address, as a client would. Nothing here reaches a routing server: the roads are
recorded ones, and the stations of the 200 example are the real CSV's.
"""

import json
import re
from io import StringIO
from pathlib import Path

import pytest
import yaml
from django.conf import settings
from django.core.management import call_command
from jsonschema import Draft4Validator

from tests.conftest import load_road
from tests.test_api import TRIP, URL, assert_error
from tests.test_project import run_new_process
from trips import errors
from trips.middleware import GOOD_REQUEST_ID
from trips.serializers import RouteQuery
from trips.services import routing
from trips.services.routing import Route

SCHEMA = "/api/v1/schema/"
DOCS = "/api/v1/docs/"
HEALTH = "/api/v1/health/"
COMMITTED = Path(settings.BASE_DIR) / "docs" / "openapi.yaml"
REGENERATE = "uv run python manage.py spectacular --file docs/openapi.yaml"

# Described in the document's opening text, not on the route (row 18 of PHASE-9).
OPENING_TEXT_CODES = {"not_found", "method_not_allowed"}


def get_document(client) -> dict:
    response = client.get(SCHEMA)
    assert response.status_code == 200, response.content
    return yaml.safe_load(response.content)


@pytest.fixture
def document(client) -> dict:
    return get_document(client)


def operation(document: dict, path: str) -> dict:
    """The GET operation at `path`, whether or not the document spells it with a final slash."""
    paths = {key.rstrip("/"): value for key, value in document["paths"].items()}
    return paths[path.rstrip("/")]["get"]


def json_content(response: dict) -> dict:
    return response["content"]["application/json"]


def resolve(document: dict, node: dict) -> dict:
    """The schema a node stands for: through a $ref, or an allOf of one that adds a description."""
    if "allOf" in node:
        (node,) = node["allOf"]
    if "$ref" in node:
        return document["components"]["schemas"][node["$ref"].rsplit("/", 1)[1]]
    return node


def error_object(document: dict, response: dict) -> dict:
    """The `error` object's schema of an error response: `code`, `message` and `details`."""
    body = resolve(document, json_content(response)["schema"])
    assert list(body["properties"]) == ["error"]
    error = resolve(document, body["properties"]["error"])
    assert list(error["properties"]) == ["code", "message", "details"]
    return error


def check_against(document: dict, schema: dict, instance) -> list[str]:
    """What is wrong with `instance` against `schema`, which may point into the document."""
    validator = Draft4Validator({**schema, "components": document["components"]})
    return [error.message for error in validator.iter_errors(instance)]


def examples_of(response: dict) -> dict:
    return json_content(response).get("examples", {})


# --- HS-09, HS-10: rate limit and methods ---------------------------------------------


def test_hs09_schema_and_docs_are_rate_limited(client):
    for _ in range(60):
        assert client.get(URL, {"start": "Dallas, TX"}).status_code != 429
    for address in (SCHEMA, DOCS):
        response = client.get(address)
        assert response.status_code == 429
        assert response["Content-Type"].startswith("application/json")
        assert assert_error(response, "rate_limited")["retry_after_seconds"] > 0


@pytest.mark.parametrize("address", [SCHEMA, DOCS])
def test_hs10_post_is_method_not_allowed_in_the_standard_shape(client, address):
    response = client.post(address)
    assert response["Content-Type"].startswith("application/json")
    assert assert_error(response, "method_not_allowed") == {}


@pytest.mark.parametrize("address", [SCHEMA, DOCS])
def test_an_accept_header_never_makes_the_schema_or_docs_fail(client, address):
    response = client.get(address, headers={"Accept": "application/xml"})
    assert response.status_code == 200


def test_the_schema_can_be_asked_for_as_json(client):
    response = client.get(SCHEMA, headers={"Accept": "application/vnd.oai.openapi+json"})
    assert response.status_code == 200
    assert json.loads(response.content)["openapi"] == "3.0.3"


# --- HS-11 to HS-14: what the document says ------------------------------------------


def test_hs11_the_schema_is_an_openapi_3_0_3_document(client):
    response = client.get(SCHEMA)
    assert response.status_code == 200
    assert yaml.safe_load(response.content)["openapi"] == "3.0.3"
    assert response["X-Request-ID"]


def test_hs12_the_route_parameters(document):
    parameters = {p["name"]: p for p in operation(document, "/api/v1/route/")["parameters"]}
    assert set(parameters) == {"start", "finish", "stop_cost"}
    for name in ("start", "finish"):
        assert parameters[name]["in"] == "query"
        assert parameters[name]["required"] is True
        assert parameters[name]["schema"]["type"] == "string"
        assert parameters[name]["schema"]["maxLength"] == 100
        assert parameters[name]["description"]
    stop_cost = parameters["stop_cost"]
    assert stop_cost["in"] == "query"
    assert stop_cost.get("required", False) is False
    assert stop_cost["schema"]["type"] == "number"
    assert (stop_cost["schema"]["minimum"], stop_cost["schema"]["maximum"]) == (0, 100)
    assert stop_cost["schema"]["default"] == 10
    assert stop_cost["description"]


# The document made in a new process whose RouteQuery has other limits and another default.
CHANGED_SERIALIZER_SCRIPT = """
from decimal import Decimal
import django
django.setup()
from django.core.management import call_command
from rest_framework import serializers
from trips.serializers import RouteQuery
RouteQuery._declared_fields["start"] = serializers.CharField(max_length=120)
RouteQuery._declared_fields["stop_cost"] = serializers.DecimalField(
    max_digits=6, decimal_places=3, min_value=Decimal("1"), max_value=Decimal("200"),
    default=Decimal("7.5"),
)
call_command("spectacular", "--format", "openapi-json")
"""


def test_hs12_the_parameters_follow_the_serializer():
    """Q1-08: the document takes each parameter's limits and default from RouteQuery, which
    checks them, so a changed limit cannot leave the document behind."""
    result = run_new_process(CHANGED_SERIALIZER_SCRIPT, DJANGO_SETTINGS_MODULE="config.settings")
    assert result.returncode == 0, result.stderr
    document = json.loads(result.stdout)
    parameters = {p["name"]: p for p in operation(document, "/api/v1/route/")["parameters"]}

    assert parameters["start"]["schema"]["maxLength"] == 120
    assert parameters["finish"]["schema"]["maxLength"] == 100
    stop_cost = parameters["stop_cost"]
    limits = {name: stop_cost["schema"][name] for name in ("minimum", "maximum", "default")}
    assert limits == {"minimum": 1, "maximum": 200, "default": 7.5}
    assert "1 to 200, at most 3 decimals, 7.5 when left out" in stop_cost["description"]


def test_the_place_names_are_trimmed_before_their_length_is_checked(document):
    """Q1-10: a name padded with spaces past 100 characters is accepted, and the document
    says why."""
    padded = " " * 5 + "a" * 100
    assert RouteQuery(data={"start": padded, "finish": "Houston, TX"}).is_valid()

    parameters = {p["name"]: p for p in operation(document, "/api/v1/route/")["parameters"]}
    assert "removed before its length is checked" in parameters["start"]["description"]
    # Ruled out: validators test multipleOf with floating-point division, and would refuse
    # sound values such as 0.07.
    assert "multipleOf" not in parameters["stop_cost"]["schema"]


def test_the_document_says_which_request_ids_are_kept(document):
    """Q1-10: "well-formed" was never defined."""
    sentence = "1 to 64 characters of letters, digits, `.`, `_` and `-`"
    assert sentence in document["info"]["description"]
    for path in ("/api/v1/route/", "/api/v1/health/"):
        for response in operation(document, path)["responses"].values():
            assert sentence in response["headers"]["X-Request-ID"]["description"]
    # What the sentence says is what the API does (trips/middleware.py).
    assert GOOD_REQUEST_ID.pattern == "[A-Za-z0-9._-]{1,64}"


@pytest.mark.django_db
def test_hs13_the_200_body_is_described_and_a_real_one_fits(client, document, ep01_world):
    response200 = operation(document, "/api/v1/route/")["responses"]["200"]
    schema = json_content(response200)["schema"]
    body = json.loads(client.get(URL, TRIP).content)

    assert check_against(document, schema, body) == []
    top = document["components"]["schemas"][schema["$ref"].rsplit("/", 1)[1]]
    assert list(top["properties"]) == [
        "summary",
        "warnings",
        "assumptions",
        "fuel_stops",
        "map",
        "meta",
    ]
    assert set(top["required"]) == set(top["properties"])

    broken = {**body, "summary": {**body["summary"], "stops": "three"}}
    assert check_against(document, schema, broken), "the schema must be able to fail"


def every_field_is_described(document: dict) -> list[str]:
    """Each property of each schema in the document that has no description."""
    missing = []
    for name, schema in document["components"]["schemas"].items():
        for field, definition in schema.get("properties", {}).items():
            if "description" not in definition and "$ref" not in definition:
                missing.append(f"{name}.{field}")
    return missing


def test_every_field_has_a_description(document):
    assert every_field_is_described(document) == []


def test_hs14_the_error_responses(document):
    route = operation(document, "/api/v1/route/")
    assert set(route["responses"]) == {"200", "400", "422", "429", "500", "502", "503"}

    expected = {
        "400": {"invalid_request", "unknown_place"},
        "422": {"outside_coverage", "route_leaves_usa", "no_route", "no_fuel_plan"},
        "429": {"rate_limited"},
        "500": {"internal_error"},
        "502": {"routing_unavailable"},
        "503": {"stations_not_loaded"},
    }
    for status, codes in expected.items():
        response = route["responses"][status]
        error = error_object(document, response)
        assert set(error["properties"]["code"]["enum"]) == codes, status
        assert {e["value"]["error"]["code"] for e in examples_of(response).values()} == codes

    assert "api_unavailable" not in json.dumps(document)

    opening = document["info"]["description"]
    for code in OPENING_TEXT_CODES:
        assert code in opening
    assert "404" in opening
    assert "405" in opening


@pytest.mark.django_db
def test_hs14_a_real_400_fits_the_400_schema(client, document, ep01_world):
    response = client.get(URL, {"start": "Chicgo, IL", "finish": "Houston, TX"})
    assert response.status_code == 400
    schema = json_content(operation(document, "/api/v1/route/")["responses"]["400"])["schema"]
    assert check_against(document, schema, json.loads(response.content)) == []


def test_the_request_id_header_is_described(document):
    route = operation(document, "/api/v1/route/")
    for status, response in route["responses"].items():
        assert "X-Request-ID" in response["headers"], status
    assert "Retry-After" in route["responses"]["429"]["headers"]
    for response in operation(document, "/api/v1/health/")["responses"].values():
        assert "X-Request-ID" in response["headers"]


def test_every_code_in_the_error_table_is_documented(document):
    """Read from trips/errors.py, so a code added there without documentation fails here."""
    route = operation(document, "/api/v1/route/")
    opening = document["info"]["description"]
    for code, status in errors.STATUS_FOR_CODE.items():
        if code in OPENING_TEXT_CODES:
            assert code in opening, code
            continue
        response = route["responses"].get(str(status))
        assert response is not None, f"{code}: the route lists no {status}"
        error = error_object(document, response)
        assert code in error["properties"]["code"]["enum"], code
        assert code in {e["value"]["error"]["code"] for e in examples_of(response).values()}, code


def test_every_example_fits_its_schema_and_its_status(document):
    count = 0
    for path, item in document["paths"].items():
        for method, op in item.items():
            for status, response in op["responses"].items():
                if "content" not in response:
                    continue
                schema = json_content(response)["schema"]
                for name, example in examples_of(response).items():
                    where = f"{method} {path} {status} {name}"
                    assert check_against(document, schema, example["value"]) == [], where
                    count += 1
                    if "error" in example["value"]:
                        code = example["value"]["error"]["code"]
                        assert errors.STATUS_FOR_CODE[code] == int(status)
    assert count >= 14


def test_the_health_address_is_described(document):
    health = operation(document, "/api/v1/health/")
    assert set(health["responses"]) == {"200", "503"}
    assert "429" not in health["responses"]
    ok = examples_of(health["responses"]["200"])
    assert {e["value"]["cache"] for e in ok.values()} >= {"redis"}
    assert (
        check_against(
            document,
            json_content(health["responses"]["200"])["schema"],
            {"status": "ok", "stations": 4, "cache": "memory"},
        )
        == []
    )
    assert {
        e["value"]["error"]["code"] for e in examples_of(health["responses"]["503"]).values()
    } == {"stations_not_loaded"}


@pytest.mark.django_db
def test_a_real_health_answer_fits_its_schema(client, document, ep01_world):
    schema = json_content(operation(document, "/api/v1/health/")["responses"]["200"])["schema"]
    assert check_against(document, schema, json.loads(client.get(HEALTH).content)) == []


# --- The 200 example is a real answer, shortened -----------------------------------------


def test_the_200_example_is_a_real_answer_shortened(
    client, document, use_real_stations, monkeypatch
):
    example = list(examples_of(operation(document, "/api/v1/route/")["responses"]["200"]).values())
    assert len(example) == 1
    shown = example[0]["value"]
    start, finish = shown["summary"]["start"]["label"], shown["summary"]["finish"]["label"]

    road = {
        ("Chicago, IL", "Houston, TX"): "chi_hou",
        ("Dallas, TX", "Houston, TX"): "dal_hou",
    }[(start, finish)]
    coords, miles = load_road(road)
    monkeypatch.setattr(
        routing,
        "fetch_route",
        lambda *_a, **_k: Route(coords, miles, "router.project-osrm.org", 1),
    )
    real = json.loads(client.get(URL, {"start": start, "finish": finish}).content)

    # Shortened in one place: the route line keeps some of its points, in order, and always
    # its first and last. Every other value is the real answer's, and `meta`'s timings are
    # those of the run the example was taken from.
    line = shown["map"]["features"][0]["geometry"]["coordinates"]
    real_line = real["map"]["features"][0]["geometry"]["coordinates"]
    assert len(line) < len(real_line)
    assert line[0] == real_line[0]
    assert line[-1] == real_line[-1]
    remaining = iter(real_line)
    assert all(point in remaining for point in line), "the example's points are not the road's"

    real["map"]["features"][0]["geometry"]["coordinates"] = line
    assert shown["meta"].keys() == real["meta"].keys()
    assert shown["meta"]["timings_ms"].keys() == real["meta"]["timings_ms"].keys()
    assert {k: v for k, v in shown["meta"].items() if k != "timings_ms"} == {
        k: v for k, v in real["meta"].items() if k != "timings_ms"
    }
    timings = shown["meta"]["timings_ms"]
    assert timings["routing"] + timings["own"] == pytest.approx(timings["total"], abs=0.11)
    assert {k: v for k, v in shown.items() if k != "meta"} == {
        k: v for k, v in real.items() if k != "meta"
    }


# --- HS-15, HS-16: valid, and the same as the committed copy -----------------------------


def generate(tmp_path: Path, *options: str) -> tuple[str, str]:
    """Run `manage.py spectacular` writing to a file; return the file's text and stderr."""
    target, stderr = tmp_path / "openapi.yaml", StringIO()
    call_command("spectacular", *options, file=str(target), stderr=stderr)
    return target.read_text(encoding="utf-8"), stderr.getvalue()


def test_hs15_the_document_is_valid_and_raises_no_warning(tmp_path):
    _, stderr = generate(tmp_path, "--validate", "--fail-on-warn")
    assert stderr == ""


def committed_matches(generated: str) -> str | None:
    """None when the committed file is the generated document, else the message to show."""
    committed = COMMITTED.read_text(encoding="utf-8")
    if committed.replace("\r\n", "\n") == generated.replace("\r\n", "\n"):
        return None
    return f"docs/openapi.yaml is not what the code produces. Regenerate it with: {REGENERATE}"


def test_hs16_the_committed_document_is_the_one_the_code_produces(tmp_path):
    generated, _ = generate(tmp_path)
    assert committed_matches(generated) is None, committed_matches(generated)


def test_hs16_a_changed_description_is_caught_and_says_how_to_regenerate(tmp_path):
    generated, _ = generate(tmp_path)
    changed = generated.replace("Where the trip starts", "Where the journey starts", 1)
    assert changed != generated, "the parameter description this test changes is gone"
    message = committed_matches(changed)
    assert message is not None
    assert REGENERATE in message


def test_the_view_serves_the_document_the_command_writes(client, tmp_path):
    generated, _ = generate(tmp_path)
    served = client.get(SCHEMA).content.decode("utf-8")
    assert yaml.safe_load(served) == yaml.safe_load(generated)


# --- HS-17: the Swagger page ---------------------------------------------------------------


def test_hs17_the_swagger_page_loads_one_pinned_version_from_the_cdn(client):
    response = client.get(DOCS)
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/html")
    page = response.content.decode("utf-8")

    pinned = settings.SPECTACULAR_SETTINGS["SWAGGER_UI_DIST"]
    assert re.fullmatch(r"https://cdn\.jsdelivr\.net/npm/swagger-ui-dist@\d+\.\d+\.\d+", pinned)
    assert f'src="{pinned}/swagger-ui-bundle.js"' in page
    assert f'href="{pinned}/swagger-ui.css"' in page
    assert "@latest" not in page
    assert SCHEMA in page
