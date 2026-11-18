# Brief 11S: the OpenAPI document and the Swagger page

The API has one route and three small addresses beside it. It is to describe itself: an OpenAPI document produced from the code, an interactive page for it, and a committed copy that a test holds to the code.

The repository root is the folder you were given; every path is relative to it.

## Rules

- **Your files:** `trips/schema.py` (new), `docs/openapi.yaml` (new), `tests/test_schema.py` (new), your report `docs/plan/reports/phase11-S.md`, and only these lines elsewhere: in `config/settings.py` the installed app, the `TEMPLATES` entry, the schema class in the REST framework settings and a `SPECTACULAR_SETTINGS` block; in `config/urls.py` the two routes; in `trips/views.py` the decorators that attach the declarations. Change nothing else. `pyproject.toml` and `uv.lock` are not yours: `drf-spectacular` 0.30.0 is installed.
- **The response of `GET /api/v1/route/` does not change.** You describe it; you do not alter it.
- No network beyond this machine: no request to a routing server. No containers started or stopped. No git command that changes anything. No other agents.
- Test first: each behaviour starts with a test that fails for the stated reason.
- Every field, type, example and sentence in the document must be true of the running code. Take them from the code and from architecture section 11, not from memory. Where the two disagree, the code is right: say so in your report.

## Read first

- `docs/backend-architecture.md` section 11 in full: the request, the 200 body field by field, the error table, "Other addresses", and "The OpenAPI document (D-20)", which records what a trial of the library on this Django found.
- `docs/requirements.md`: FR-19, D-20, acceptance check 15.
- `docs/test-cases.md` section 9.4: the HS cases on the schema and docs addresses. Build to them; if one is wrong, say so in your report instead of changing it.
- `docs/plan/PHASE-9.md`, "Points raised by the test design, settled", row 18: what the route lists and what goes in the opening text. And "Gaps found while writing the specs, settled", rows 6 to 8.
- `trips/views.py`, `trips/serializers.py`, `trips/errors.py`, `trips/services/answer.py` (it builds the 200 body), `trips/services/planner.py` (it adds `meta`), `config/urls.py`, `trips/urls.py`.

## Build

1. **The declarations, in `trips/schema.py`.** The route view is a plain `APIView`, so the library cannot guess anything: declare the three query parameters with their limits and defaults; the 200 body in full (summary, warnings, assumptions, fuel stops, the map as GeoJSON, meta), every field with its type and a one-line description; and the error body. On the route, list 400, 422, 429, 500, 502 and 503, each with every code it can carry and what `details` holds for that code, and at least one real example each. That includes 503 `api_unavailable`, described as sent by the proxy when the API cannot be reached. `not_found` and `method_not_allowed` are described in the document's opening text, not on the route. Declare the health address too. Give the 200 a real, shortened example taken from a real answer (use a recorded road through the test helpers, not a request to a server).
2. **The two addresses:** `/api/v1/schema/` and `/api/v1/docs/`, placed before the include of `trips.urls`, whose last pattern matches everything. Both are rate limited like any other address. The Swagger page's script comes from a CDN: pin it to one exact version with `SWAGGER_UI_DIST`, and say in your report which version and why that one.
3. **The committed document, `docs/openapi.yaml`,** written by `manage.py spectacular --file`. A test produces the document from the code and fails, with a message saying how to regenerate it, if it differs from the committed file.
4. **Tests, in `tests/test_schema.py`:** the HS cases; `spectacular --validate --fail-on-warn` reporting nothing; the document naming every error code in `trips/errors.py` (read the table from the code, so a code added later without documentation fails the test); the document's 200 example passing the independent verifier in `tests/verify.py` if it is a whole answer, or matching the real answer field for field if it is shortened; the Swagger page answering 200 as HTML and naming the pinned version.

## Prove it

`uv run pytest` in full, `uv run pytest -m slow`, `uv run mypy`, `uv run ruff check .`, `uv run ruff format --check .`: clean. `uv run python manage.py spectacular --validate --fail-on-warn`: no warning or error. `uv run python manage.py check --deploy --fail-level WARNING`: still no issue. Use `127.0.0.1`, never `localhost`, for the database. One pytest process at a time, in the foreground.

## Your report: `docs/plan/reports/phase11-S.md`

What you declared and where each fact came from; every place the code and architecture section 11 disagreed; the pinned Swagger version; the commands with their output; anything you are unsure of.

Reply to the controller with: status, test counts, and any concern.
