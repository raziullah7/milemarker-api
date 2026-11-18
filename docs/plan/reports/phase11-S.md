# Report 11S: the OpenAPI document and the Swagger page

Status: done, with the concerns at the end.

## What was built

| File | Change |
|---|---|
| `trips/schema.py` (new) | The declarations (`route_schema`, `health_schema`), the description serializers, the real examples, and the two views of the new addresses |
| `docs/openapi.yaml` (new) | Written by `manage.py spectacular --file docs/openapi.yaml`, 1,245 lines |
| `tests/test_schema.py` (new) | 23 tests |
| `config/settings.py` | `drf_spectacular` in `INSTALLED_APPS`; `TEMPLATES` (`APP_DIRS`); `DEFAULT_SCHEMA_CLASS`; a `SPECTACULAR_SETTINGS` block |
| `config/urls.py` | The two routes, before the include of `trips.urls` |
| `trips/views.py` | One import and two decorators (`@route_schema`, `@health_schema`) |

Nothing else was touched. The route's response is unchanged: the decorators only attach declarations.

### Settings

`SPECTACULAR_SETTINGS` holds the title, the opening text (the addresses, the rate limit, the error shape, `not_found` and `method_not_allowed`, `X-Request-ID`), version `2.0.0`, and four deliberate choices:

- `SERVE_INCLUDE_SCHEMA: False`. The document lists the route and health. The schema and docs addresses are described in the opening text.
- `POSTPROCESSING_HOOKS: []`. The default hook lifts every enum into a component and then warns that the fields called `kind`, `type` and `code` collide (three warnings, `--fail-on-warn` fails). With the hook off each enum stays inline, where it is declared, and the document reads better. The enum fields are declared with `_only(...)` in `trips/schema.py`.
- `SWAGGER_UI_DIST`: see below.
- `SWAGGER_UI_FAVICON_HREF: ""`, so the page does not ask the CDN for a favicon.

### The two views

`config/urls.py` uses `SchemaView` and `DocsView` from `trips/schema.py`, which are the library's views with one mixin. The library's own views failed two of the cases:

1. HS-09 and HS-10 want a 429 and a 405 in the standard JSON shape. The library's views render errors with their own renderer (the Swagger page's is HTML, the document's YAML), giving the plain text `429 Too Many Requests`. The mixin makes any error answer JSON.
2. An `Accept` header that the renderers cannot match (for example `application/xml`) made the library answer 406, which the API's handler turns into a 500 `internal_error`. The mixin answers with the first renderer instead. `Accept: application/vnd.oai.openapi+json` still gives JSON.

Both have a test. Both addresses are rate limited like the route (HS-09), through the default throttle class; they share its counter.

## What was declared, and where each fact came from

| Declared | Source |
|---|---|
| `start`, `finish`: required, string, 1 to 100 characters, spaces trimmed | `RouteQuery` in `trips/serializers.py` (`CharField(max_length=100)`, trimmed, not blank) |
| `stop_cost`: number, 0 to 100, at most 2 decimals, default 10, empty is an error | `RouteQuery`, `DEFAULT_STOP_COST`, its docstring |
| 200 body: keys, order and meaning | `build_answer` in `trips/services/answer.py` and `_with_meta` in `trips/services/planner.py`; every figure's rounding from the docstrings there |
| Map: a `oneOf` of three feature kinds (route line, stop, start/finish), their properties | `_map` in `answer.py` |
| Assumptions | `build_answer`, `RANGE_MILES`, `MILES_PER_GALLON`, `TANK_GALLONS`, `SEARCH_RADIUS_MILES` |
| Error body shape and every code's status | `trips/errors.py` (`STATUS_FOR_CODE`, `handler`, `error_body`) |
| Each code's `details` keys | The exception classes in `stations/exceptions.py` and `trips/exceptions.py`, and `handler` for `rate_limited` and `invalid_request` |
| Error examples (11 of the 12 codes the route can carry) | Captured by running the real code: the real price table, recorded roads, the Django test client, with `fetch_route` replaced. Messages are the code's own |
| 200 example: Chicago, IL to Houston, TX | The same run (`chi_hou` recorded road, real stations, stop cost 10). 3 stops. Shortened in one place: the route line keeps 9 of its 2,177 points |
| `api_unavailable` as sent by the proxy | Architecture section 11 and D-24 |
| Health: 200 and 503, `cache` values | `health()` in `planner.py` and section 11. Not rate limited: `throttle_classes = ()` |
| `X-Request-ID` on every documented answer; `Retry-After` on the 429 | `trips/middleware.py`; `Throttled` in `trips/errors.py` |
| Opening text: 60 a minute, shared by the route, schema and docs | `DEFAULT_THROTTLE_RATES`; HS-09 |

The tests hold the document to the code: a real 200 and a real 400 validate against their schemas (jsonschema, with a case that must fail); every example validates against its schema and sits under the status its code maps to; the codes are read from `trips.errors.STATUS_FOR_CODE`, so a new code without a response, an enum entry and an example fails; the 200 example is compared field for field with a fresh answer to the same request, the route line aside (its points must be, in order, points of the real road); every schema property has a description.

## Where the code and architecture section 11 disagree

The code is right in each; the document says what the code does. Two disagreements.

1. **`station_id`.** The section's example shows `"station_id": "…"`, which reads as text. The code gives the OPIS ID as an **integer** (`73127`). Declared as `integer`. (`tests/verify.py` converts with `str()` itself.)
2. **`details` of a request Django cannot read.** The section says `fields` is empty for "a host that is not allowed" and for a request nginx refuses. A host that is not allowed does give `details: {}`. But a request Django refuses, for example one with more than 1,000 parameters, gives `details: {"fields": {}}` (`SuspiciousOperation` in `handler`). Declared: `fields` is optional and may be empty.

The `api_unavailable` example message ("The API cannot be reached.") is mine: the section gives `"…"`, and nginx's configuration is not in this repository, so the real wording cannot be read. The document says the message is the proxy's, but the example text is not from the running proxy.

Also stale, but outside my files: the docstring at the top of `config/settings.py` says the service has no templates. It now has one (the Swagger page's). I did not change it.

## Test-case notes (docs/test-cases.md 9.4)

Built to the cases as written. HS-16's second half ("a parameter's description changed in `trips/schema.py` alone") is tested on the generated text, so the suite stays green; I also made the real edit once by hand (changed "Where the trip starts" in `schema.py`), ran the test, saw it fail with the regenerate message, and restored the file. HS-18 (browser) is not run: no network.

## Swagger version

`SWAGGER_UI_DIST = https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14`. 5.17.14 is the last release of the 5.17 line and is the version drf-spectacular's own documentation uses in its examples; I know it to exist on npm and it works with the OpenAPI 3.0.3 the document uses. I could not look at npm or the CDN from here (no network), so I did not pick a newer one I could not confirm. A later 5.x can replace it by changing one line; the committed document does not depend on it. The test requires a full `x.y.z` version, so `latest` or `5` fails it.

## Commands and output

```
uv run pytest                      567 passed, 1 deselected in 129.00s   (544 before, +23)
uv run pytest -m slow              1 passed, 567 deselected in 30.07s
uv run mypy                        Success: no issues found in 6 source files
uv run ruff check .                All checks passed!
uv run ruff format --check .       65 files already formatted
uv run python manage.py spectacular --validate --fail-on-warn     no output, exit 0
uv run python manage.py check --deploy --fail-level WARNING       System check identified no issues (3 silenced).
```

The database address was `postgresql://milemarker:milemarker@127.0.0.1:5432/milemarker_s`. No container was started or stopped, and nothing is left running.

## Concerns

- **The page was not seen in a browser.** The test proves the HTML names the pinned script and style and the schema address; whether 5.17.14 renders this document was not checked (no network).
- **`jsonschema` and `pyyaml`** are used by the new tests. Both are installed because `drf-spectacular` needs them, but neither is in `pyproject.toml`'s own dependency lists. I may not edit that file; if drf-spectacular ever dropped them the tests would fail on import.
- **`# ruff: noqa: E501`** at the top of `trips/schema.py`: the file is prose-heavy, and the generated example is a pretty-printed literal. The test files already ignore E501 in `pyproject.toml`; I could not add this file there.
- **The proxy's wording** for `api_unavailable` (see above).
- Both new addresses answer HEAD and OPTIONS as the framework does, like the route.
