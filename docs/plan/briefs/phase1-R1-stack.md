# Brief R1: verify the stack

You are a research agent. Today is 18 Nov 2026. A small Django API is about to be built and the builders need **verified, current** facts about the libraries, because some of them were released recently. Use web search and page fetches against primary sources (official docs, release notes, PyPI JSON at `https://pypi.org/pypi/<name>/json`). Do not rely on memory. Do not write code into any project. Do not spawn other agents.

**Write your full report to `docs/plan/reports\phase1-R1-stack.md`.** Return to me only: a five-line summary and anything you could not confirm.

For every answer give the fact, the URL, and where it helps a copy-pasteable snippet. Mark anything unconfirmed as `NOT CONFIRMED`. Keep it tight: this is a reference sheet, not an essay.

## The project

Python 3.12, managed with `uv`. Django 6.1.x, Django REST Framework 3.18.x, PostgreSQL through Docker Compose, httpx, numpy, scipy, dj-database-url, psycopg 3, gunicorn. Dev: pytest, pytest-django, Ruff. One read-only GET endpoint, no auth, no users, no templates. One model (`FuelStation`).

## Questions

**A. Versions.** Latest stable version and release date on PyPI of: Django, djangorestframework, httpx, numpy, scipy, dj-database-url, psycopg (and `psycopg[binary]`), gunicorn, pytest, pytest-django, ruff. For each, the Python versions it supports, and whether it declares Django 6.1 support where relevant (pytest-django, dj-database-url, DRF).

**B. Django 6.1 for a minimal API project.**
1. What `django-admin startproject` generates in 6.1 that differs from 5.2 (new settings, changed defaults).
2. Anything deprecated or removed between 5.2 and 6.1 that a minimal API project could touch.
3. The minimal `INSTALLED_APPS` and `MIDDLEWARE` that DRF needs for an unauthenticated JSON API. Does DRF need `django.contrib.auth` and `contenttypes` installed when `UNAUTHENTICATED_USER` is `None` and there are no permission classes?
4. Which PostgreSQL versions Django 6.1 supports, and which driver the `django.db.backends.postgresql` engine prefers.
5. How to return JSON for 404 and 500 (`handler404`, `handler500`) so non-DRF errors have a JSON body.
6. Django's cache framework: the `LocMemCache` settings block, its `TIMEOUT` and `MAX_ENTRIES` options, and whether stored values are pickled (so numpy arrays can be stored).
7. `bulk_create` plus `transaction.atomic` to replace a table's contents; any 6.1 notes.

**C. Django REST Framework 3.18.**
1. Settings for: custom `EXCEPTION_HANDLER`, `DEFAULT_THROTTLE_CLASSES` with `AnonRateThrottle`, `DEFAULT_THROTTLE_RATES` format (is `60/min` valid?), `DEFAULT_RENDERER_CLASSES` (JSON only), `COERCE_DECIMAL_TO_STRING`, `UNAUTHENTICATED_USER`.
2. The signature of a custom exception handler, and how to catch `ValidationError`, `Throttled`, `MethodNotAllowed`, `NotFound` in it. What `Throttled.wait` holds.
3. Which cache the throttle uses, and how to override the rate in a test.
4. `serializers.DecimalField(max_digits, decimal_places, min_value, max_value)`: does it reject `nan` and `inf`? Should `min_value`/`max_value` be `Decimal` instances in 3.18?
5. How `Response` renders a Python `Decimal` and a `float` inside a plain dict. I need prices such as `3.00733333` to come out as JSON numbers with every digit kept.
6. Does a GET `APIView` reading `request.query_params` behave identically with and without a trailing slash, and what `APPEND_SLASH` does for an API client.

**D. pytest-django.**
1. Configuration under `[tool.pytest.ini_options]` in `pyproject.toml`.
2. How to write a **session-scoped** fixture that loads data into the test database once (`django_db_setup`, `django_db_blocker`), and how that interacts with per-test transactions.
3. Running against PostgreSQL: what the test database is called, what permission it needs, `--reuse-db`.
4. Marking tests that need no database so they run without PostgreSQL being up.

**E. Blocking the network in tests.** Options for failing any test that opens a non-local connection while still allowing `localhost` for PostgreSQL: the `pytest-socket` plugin (latest version, the `--disable-socket --allow-hosts=127.0.0.1,::1` flags, whether it works with psycopg 3 and httpx `MockTransport`) versus a hand-written fixture that patches `socket.socket.connect`. Recommend one.

**F. httpx.**
1. `httpx.MockTransport` with a handler function: a minimal example that returns JSON, raises a timeout, and counts calls.
2. `httpx.Timeout`: what each of connect/read/write/pool means, and that a plain `timeout=5` is per phase, not a total. The recommended way to enforce a **total** deadline of 5 seconds for one request.
3. Exception classes for: connect timeout, read timeout, connection refused, non-2xx (`raise_for_status`).
4. Setting a default `User-Agent` on a shared `httpx.Client`, and whether a module-level client is thread-safe.

**G. scipy and numpy.**
1. `scipy.spatial.cKDTree.query(x, k=1, distance_upper_bound=r)`: what it returns for points with no neighbour within `r` (distance and index values). Is `cKDTree` still the recommended class, or `KDTree`?
2. `scipy.optimize.linprog(c, A_ub, b_ub, bounds, method="highs")`: confirm the signature and the `success` and `fun` fields.
3. Wheels for Python 3.12 on Windows and on `python:3.12-slim` (manylinux) for the latest numpy and scipy.

**H. uv.**
1. Commands to create a project that is an application (not a package): `uv init` flags, `.python-version`, `uv add`, `uv add --dev`, `uv sync`, `uv run`, `uv lock`.
2. The current recommended Dockerfile pattern for a uv project (copying the uv binary from `ghcr.io/astral-sh/uv`, `uv sync --frozen --no-dev`, cache mounts, `UV_COMPILE_BYTECODE`).
3. Where dev dependencies live in `pyproject.toml` now (`[dependency-groups]` versus `[tool.uv]`).

**I. Docker and PostgreSQL.**
1. The current PostgreSQL major versions and the right official image tag to pin for a new project today (17 or newer). Any change in the data directory path for recent image versions.
2. A Compose healthcheck with `pg_isready` and `depends_on: condition: service_healthy`.
3. `dj-database-url`: `dj_database_url.config(default=..., conn_max_age=...)` and the URL form for psycopg 3.
4. gunicorn command for a Django WSGI app with one worker and four threads, binding `0.0.0.0:8000`.

**J. Ruff.** A minimal current `[tool.ruff]` block for a Django project (line length, the rule sets worth selecting, per-file ignores for migrations).
