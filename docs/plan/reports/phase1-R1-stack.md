# R1: stack verification (18 Nov 2026)

Method: PyPI JSON API, official docs, and empirical tests in a throwaway venv under the session scratchpad (Python 3.12, Windows, nothing installed into any project). "TESTED" = I ran it with the exact versions in table A. The Docker daemon was NOT running, so nothing was tested against a real PostgreSQL.

## A. Versions (PyPI JSON: https://pypi.org/pypi/<name>/json)

| Package | Latest stable | Released | requires-python | Notes |
|---|---|---|---|---|
| Django | 6.1.3 | 2026-11-03 | >=3.12 | Py 3.12-3.15 (3.15 added in 6.1.3): https://docs.djangoproject.com/en/6.1/faq/install/ |
| djangorestframework | 3.18.3 | 2026-10-06 | >=3.10 | Classifiers: Django 5.2, 6.0, 6.1; Py 3.10-3.15 |
| httpx | 0.28.1 | 2024-12-06 | >=3.8 | Newest non-dev release (only 1.0.dev* after it). Classifiers Py 3.9-3.12; works on 3.12 (TESTED) |
| numpy | 2.5.5 | 2026-11-15 | >=3.12 | |
| scipy | 1.18.1 | 2026-08-21 | >=3.12 | |
| dj-database-url | 3.1.2 | 2026-02-19 | >=3.10 | Classifiers: Django 4.2, 5.2, "6" (no explicit 6.1); installs and imports with Django 6.1.3 |
| psycopg | 3.3.9 | 2026-11-12 | >=3.10 | Py 3.10-3.15 |
| psycopg-binary | 3.3.9 | 2026-11-12 | >=3.10 | `psycopg[binary]` pulls the same version |
| gunicorn | 27.0.1 | 2026-11-12 | >=3.10 | POSIX only: `import fcntl` fails on Windows (TESTED). Run only in Docker/Linux |
| pytest | 9.2.0 | 2026-10-27 | >=3.10 | |
| pytest-django | 4.14.0 | 2026-08-10 | >=3.10 | Classifiers list Django 5.2 and 6.0 only; changelog does not mention 6.1 (https://pytest-django.readthedocs.io/en/latest/changelog.html). Ran fine against Django 6.1.3 (TESTED) |
| ruff | 0.17.5 | 2026-11-12 | >=3.7 | |
| pytest-socket | 0.8.1 | 2026-08-19 | >=3.10 | |

- DRF declares Django 6.1: 3.18.0 (7 Aug 2026) added it and dropped Django 4.2/5.0/5.1; 3.18.2 added Python 3.15 (https://www.django-rest-framework.org/community/release-notes/).
- Django 6.1 needs Python >=3.12 (6.0 dropped <3.12: https://docs.djangoproject.com/en/6.1/releases/6.0/).
- All of the above co-installed cleanly with `uv pip install` on Python 3.12 (TESTED).

## B. Django 6.1

1. **startproject, 5.2 vs 6.1.** I diffed `settings.py-tpl` on the stable branches (https://raw.githubusercontent.com/django/django/stable/6.1.x/django/conf/project_template/project_name/settings.py-tpl vs `.../stable/5.2.x/...`), TESTED:
   - `DEFAULT_AUTO_FIELD` lines removed from the template (6.0 change; the default is now `BigAutoField`; https://docs.djangoproject.com/en/6.1/ref/settings/).
   - New block at the end: `MAILERS = {'default': {'BACKEND': 'django.core.mail.backends.console.EmailBackend'}}` (6.1; `EMAIL_*` settings are deprecated). Delete it for this project.
   - 6.0: `startproject` creates the target directory if missing. Nothing else differs.
2. **Deprecated or removed 5.2 to 6.1** (https://docs.djangoproject.com/en/6.1/releases/6.1/ and /6.0/). Nothing hits this project. Notables: `EMAIL_*` settings and `mail.get_connection` deprecated; `values_list(flat=True)` with no field and `select_related()` with no args deprecated; `transaction.savepoint()` deprecated; SQL aliases always quoted; `first()`/`last()` no longer add pk ordering after `order_by()` clears it. Removed in 6.0: positional args to `Model.save()`, `CheckConstraint(check=)` (use `condition=`), Python <3.12.
3. **Minimal INSTALLED_APPS/MIDDLEWARE.** TESTED (APIClient, JSON-only renderer, `UNAUTHENTICATED_USER=None`, empty auth and permission classes, throttle on, custom handler): works with `INSTALLED_APPS = ["rest_framework", "<your app>"]` and NO `django.contrib.auth`, NO `contenttypes`, NO sessions. `MIDDLEWARE` may be empty; add `CommonMiddleware` only if you want `APPEND_SLASH` (see C6). DRF docs: `UNAUTHENTICATED_USER` defaults to `django.contrib.auth.models.AnonymousUser`; set it to None to drop auth (https://www.django-rest-framework.org/api-guide/settings/). Also set `DEFAULT_AUTHENTICATION_CLASSES: []` and `DEFAULT_PERMISSION_CLASSES: []`.
   ```python
   INSTALLED_APPS = ["rest_framework", "stations"]
   MIDDLEWARE = ["django.middleware.common.CommonMiddleware"]  # optional
   ```
4. **PostgreSQL.** Django 6.1 supports PostgreSQL 15+ (14 dropped): https://docs.djangoproject.com/en/6.1/ref/databases/ and the 6.1 notes. Driver: psycopg 3 (3.1.12+) recommended; psycopg2 2.9.9+ still accepted but "likely to be deprecated". The single engine `django.db.backends.postgresql` serves both. Client-side binding is the default on psycopg 3.
5. **JSON 404/500** (https://docs.djangoproject.com/en/6.1/ref/urls/), TESTED with DEBUG=False:
   ```python
   from django.http import JsonResponse
   def not_found(request, exception): return JsonResponse({"error": "not_found"}, status=404)
   def server_error(request): return JsonResponse({"error": "server_error"}, status=500)
   handler404 = "config.urls.not_found"
   handler500 = "config.urls.server_error"
   ```
   handler404 takes `(request, exception)`, handler500 takes `(request)`. Used only when `DEBUG=False`. In tests use `APIClient(raise_request_exception=False)` to get the 500 body. DRF errors go through `EXCEPTION_HANDLER` instead; a handler returning None falls through to handler500.
6. **LocMemCache** (https://docs.djangoproject.com/en/6.1/topics/cache/):
   ```python
   CACHES = {"default": {
       "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
       "LOCATION": "stations",       # only needed with more than one locmem cache
       "TIMEOUT": 300,               # default 300 s; None = never expire; 0 = do not cache
       "OPTIONS": {"MAX_ENTRIES": 1000, "CULL_FREQUENCY": 3},  # defaults 300 and 3; LRU culling
   }}
   ```
   Per-process and thread-safe; no sharing across gunicorn workers. **Values are pickled.** The docs page does not say so for locmem (NOT CONFIRMED on the docs), but the source does: `pickle.dumps(value, HIGHEST_PROTOCOL)` on set, `pickle.loads` on get (https://raw.githubusercontent.com/django/django/stable/6.1.x/django/core/cache/backends/locmem.py). TESTED: a numpy array round-trips equal, and every `get` returns a fresh copy (`v is cache.get(k)` is False), so mutation is safe but a big array is unpickled on each get.
7. **bulk_create + atomic** (https://docs.djangoproject.com/en/6.1/ref/models/querysets/#bulk-create, https://docs.djangoproject.com/en/6.1/topics/db/transactions/). No 6.1 note in the bulk_create section. Signature: `bulk_create(objs, batch_size=None, ignore_conflicts=False, update_conflicts=False, update_fields=None, unique_fields=None)`; no `save()` or signals; default is as many rows per query as the DB allows (docs give no PostgreSQL batch guidance; `batch_size=2000` is my judgement).
   ```python
   from django.db import transaction
   with transaction.atomic():
       FuelStation.objects.all().delete()
       FuelStation.objects.bulk_create(rows, batch_size=2000)
   ```
   Exception inside the block rolls everything back. Only 6.1 note nearby: `QuerySet.delete()` gained `DB_*` `on_delete` variants (irrelevant with no FKs).

## C. DRF 3.18

1. **Settings** (https://www.django-rest-framework.org/api-guide/settings/, /throttling/):
   ```python
   REST_FRAMEWORK = {
       "EXCEPTION_HANDLER": "config.api.exception_handler",
       "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
       "DEFAULT_THROTTLE_RATES": {"anon": "60/min"},   # "60/min" is valid (TESTED)
       "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
       "COERCE_DECIMAL_TO_STRING": False,   # default True; serializer DecimalField only
       "UNAUTHENTICATED_USER": None,
       "DEFAULT_AUTHENTICATION_CLASSES": [],
       "DEFAULT_PERMISSION_CLASSES": [],
   }
   ```
   Rate format `num/period`; per the docs the period is s/m/h/d and longer forms (`min`, `minute`, `hour`, `day`) are accepted; source `parse_rate` uses `period[0]` (TESTED). Defaults: handler `rest_framework.views.exception_handler`; renderers JSON + BrowsableAPI; throttle classes `[]`.
2. **Exception handler** (https://www.django-rest-framework.org/api-guide/exceptions/): `def handler(exc, context)`; return a `Response`, or `None` (Django then returns 500, so your handler500 runs). `ValidationError` 400, `NotFound` 404 (Django `Http404` is converted to it), `MethodNotAllowed(method)` 405, `Throttled(wait=None, detail=None, code=None)` 429. TESTED pattern:
   ```python
   from rest_framework.views import exception_handler as drf_handler
   from rest_framework.exceptions import Throttled

   def exception_handler(exc, context):
       resp = drf_handler(exc, context)
       if resp is None:
           return None
       body = {"error": type(exc).__name__, "detail": exc.detail}  # str, list or dict
       if isinstance(exc, Throttled):
           body["retry_after"] = exc.wait
       resp.data = body
       return resp
   ```
   `Throttled.wait` = seconds until the request would be allowed (observed `60` for a 1-minute window, TESTED; may be None). The default handler (read from source) sets `Retry-After: %d` from `exc.wait`, so headers survive when you only replace `resp.data`. For `ValidationError`, `.detail` is a list or dict.
3. **Throttle cache.** Default Django cache (`CACHES["default"]`); override by subclassing with `cache = caches["alias"]`. Under LocMem the counters are per process, so N gunicorn workers allow about N times the rate. The docs add that throttling is non-atomic and not a security measure. Test override, TESTED (3rd request returned 429, `Retry-After: 60`):
   ```python
   from django.core.cache import cache
   from rest_framework.throttling import AnonRateThrottle

   def test_throttle(monkeypatch):
       cache.clear()
       monkeypatch.setitem(AnonRateThrottle.THROTTLE_RATES, "anon", "2/min")
       ...
   ```
   Reason (from source, `SimpleRateThrottle.get_rate`, not separately tested): `THROTTLE_RATES` is a class attribute captured from settings at import, so `override_settings(REST_FRAMEWORK=...)` will not change it. Clear the cache between tests (autouse fixture) or throttle state leaks.
4. **DecimalField.** TESTED on 3.18.3: `nan`, `NaN`, `sNaN`, `inf`, `-Infinity` are all rejected ("A valid number is required.", code `invalid`), with `min_value=Decimal("0")` and with `min_value=0`. Both int and Decimal limits behaved identically, so I could NOT confirm that Decimal is required; the 3.15.0 release notes warn about using Decimal for these arguments and no 3.18.x entry changes it. Use `Decimal("0")` / `Decimal("9")` (safe either way). `max_digits` and `decimal_places` are enforced ("no more than 5 decimal places").
5. **Rendering Decimal and float in a plain dict.** `rest_framework/utils/encoders.py` `JSONEncoder.default` does `float(obj)` for `Decimal` (TESTED). With the JSON renderer, regardless of `COERCE_DECIMAL_TO_STRING` (it affects serializer fields only): `Decimal("3.00733333")` renders `3.00733333`; float `3.00733333` renders `3.00733333`. Caveat: precision is a double's, so `Decimal("3.0073333300000001")` renders `3.0073333300000002` and `Decimal("0.10")` renders `0.1`. Keep to 15 significant digits or fewer. `float("nan")` or `inf` raises `ValueError: Out of range float values are not JSON compliant` (a 500); never emit them.
6. **Trailing slash.** TESTED with `path("api/v/", View)` and `CommonMiddleware`: `GET /api/v?q=1` gives 301 to `/api/v/?q=1` (query kept); `GET /api/v/?q=1` gives 200; a route registered without slash (`api/vns`) 404s when requested with a slash. `request.query_params` is identical once the final URL is reached. `APPEND_SLASH` defaults to True, needs `CommonMiddleware`, and acts only when no pattern matches (https://docs.djangoproject.com/en/6.1/ref/settings/). A 301 is awkward for API clients. Recommendation: pick one canonical form, drop `CommonMiddleware`, and if both must work register `re_path(r"^api/v/?$", ...)`.

## D. pytest-django

1. `pyproject.toml` (config style from https://pytest-django.readthedocs.io/en/latest/configuring_django.html; I TESTED the same keys in pytest.ini):
   ```toml
   [tool.pytest.ini_options]
   DJANGO_SETTINGS_MODULE = "config.settings"
   pythonpath = ["."]
   python_files = ["test_*.py"]
   addopts = "-ra --disable-socket --allow-hosts=127.0.0.1,::1"
   ```
   Without `manage.py` in the cwd, `pythonpath` is required (otherwise "could not find a Django project", TESTED). The docs example uses a `[tool.pytest]` table; `[tool.pytest.ini_options]` also works with pytest 9.2.
2. **Session fixture** (https://pytest-django.readthedocs.io/en/latest/database.html), TESTED on in-memory SQLite:
   ```python
   @pytest.fixture(scope="session")
   def django_db_setup(django_db_setup, django_db_blocker):
       with django_db_blocker.unblock():
           FuelStation.objects.bulk_create([...])
   ```
   Seed rows are committed once, outside any per-test transaction. `@pytest.mark.django_db` tests run in a transaction that is rolled back, so they see the seed and their own writes vanish (TESTED: test_1 created a row, test_2 still counted 2). `transaction=True` tests flush tables at teardown and would erase the seed (pytest-django behaviour, not tested here).
3. **PostgreSQL.** Test DB is `test_` + `DATABASES["default"]["NAME"]` (Django default for `TEST["NAME"]`; NOT CONFIRMED on the pytest-django page). The role needs `CREATEDB` to create/drop it (NOT CONFIRMED from docs; the Django databases page lists no privileges). The postgres image's `POSTGRES_USER` is a superuser, so it works out of the box. `--reuse-db` keeps the DB between runs; after schema changes use `--reuse-db --create-db`; without `--reuse-db` it is recreated each run (database docs). NOT TESTED on real PostgreSQL.
4. **No-DB tests.** DB access is blocked unless a test has `@pytest.mark.django_db` or uses `db`/`transactional_db`; an unmarked ORM call raises `RuntimeError: Database access not allowed...` (TESTED). Unmarked tests passed alongside DB tests. That the test DB is only created when a selected test needs it is the documented lazy behaviour of the db fixtures, NOT directly tested against PostgreSQL. Run just those with `pytest -m "not django_db"` or by path.

## E. Blocking the network in tests

pytest-socket 0.8.1 (https://github.com/miketheman/pytest-socket). TESTED:
- `--disable-socket --allow-hosts=127.0.0.1,::1`: connecting to a non-allowed IP raises `SocketConnectBlockedError` (plus a `UserWarning`); `127.0.0.1` is allowed; `httpx.MockTransport` works (no socket opened); real httpx calls are blocked.
- README says DNS resolution is blocked; in my test `socket.getaddrinfo("example.com", 80)` was NOT blocked (the later connect to the IP is). Do not rely on DNS blocking.
- **psycopg 3 is not intercepted.** It connects through libpq in C, not Python's `socket`. TESTED: `psycopg.connect(host=192.0.2.1, connect_timeout=1)` under the flags above was NOT blocked (it went out and raised `ConnectionTimeout`). So the plugin neither breaks nor guards the database connection; the allow-list is irrelevant to it. It guards Python-level sockets only (httpx, urllib, requests).
- README caveat: sockets are disabled in `pytest_runtest_setup`; a session fixture first set up inside a test runs under that test's restrictions.
- Hand-written fixture patching `socket.socket.connect` to allow only loopback gives the same coverage for Python sockets in about 12 lines (NOT TESTED).
- **Recommendation:** pytest-socket in `addopts` (one line, maintained, per-test `@pytest.mark.enable_socket`). State plainly that DB traffic is out of its scope.

## F. httpx 0.28.1

1. MockTransport (TESTED):
   ```python
   import httpx
   calls = []

   def handler(request: httpx.Request) -> httpx.Response:
       calls.append(request)
       if request.url.path == "/slow":
           raise httpx.ReadTimeout("boom", request=request)
       return httpx.Response(200, json={"ok": True})

   client = httpx.Client(transport=httpx.MockTransport(handler), timeout=5)
   assert client.get("http://x/a").json() == {"ok": True} and len(calls) == 1
   ```
2. Timeouts (https://www.python-httpx.org/advanced/timeouts/): connect = time to establish the socket (`ConnectTimeout`); read = wait for a chunk of incoming data (`ReadTimeout`); write = wait to send a chunk (`WriteTimeout`); pool = wait for a pooled connection (`PoolTimeout`). `timeout=5` expands to `Timeout(connect=5, read=5, write=5, pool=5)` (TESTED). They are per phase, not total: against a local server dripping 1 byte per 0.1 s for 10 s, `Client(timeout=1.0).get()` returned 200 after 10.0 s (TESTED). The docs describe no total deadline. **Total deadline, sync** (TESTED: aborted at 1.0 s for a 1.0 s budget; granularity is the gap between chunks, so a stall can overrun by up to one read timeout):
   ```python
   import time, httpx

   def get_within(client, url, total=5.0):
       deadline = time.monotonic() + total
       with client.stream("GET", url, timeout=httpx.Timeout(total)) as r:
           buf = bytearray()
           for chunk in r.iter_bytes():
               buf += chunk
               if time.monotonic() > deadline:
                   raise httpx.ReadTimeout("total deadline exceeded", request=r.request)
           return r, bytes(buf)
   ```
   Hard cap needs async: `async with asyncio.timeout(5): await client.get(url, timeout=None)` (TESTED, 1.0 s cap).
3. Exceptions (MROs TESTED): `ConnectTimeout` and `ReadTimeout` both subclass `TimeoutException`, then `TransportError`, `RequestError`, `HTTPError`. Connection refused is `httpx.ConnectError` (`NetworkError`, `TransportError`; TESTED on 127.0.0.1:1). `resp.raise_for_status()` raises `httpx.HTTPStatusError` (subclass of `HTTPError`, NOT of `RequestError`). Catch `httpx.HTTPError` for all.
4. Default header: `httpx.Client(headers={"User-Agent": "milemarker/1.0"})` (https://www.python-httpx.org/advanced/clients/); built-in default is `python-httpx/0.28.1` (TESTED). Thread safety: a maintainer says "HTTPX is intended to be thread-safe" and one shared client pools better (https://github.com/encode/httpx/discussions/1633); closing a client while other threads send breaks it. The official docs pages do not state this. A module-level client is fine under gunicorn `gthread`.

## G. scipy and numpy

1. `cKDTree.query(x, k=1, eps=0.0, p=2.0, distance_upper_bound=inf, workers=1)`; missing neighbours get distance `inf` and index `self.n` (https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.query.html). TESTED: 2-point tree, `distance_upper_bound=0.5` gives `dist [0.1, inf]`, `idx [0, 2]`. Mask with `np.isfinite(dist)` or `idx < tree.n`. **cKDTree vs KDTree:** the installed scipy 1.18.1 docstring says `cKDTree` is functionally identical, the two names exist only for backward compatibility, and "prefer `KDTree`" if SciPy <1.6 is not a concern (read from the installed package; the online KDTree page did not repeat it). `KDTree` subclasses `cKDTree`. Use `KDTree`.
2. `linprog(c, A_ub=None, b_ub=None, A_eq=None, b_eq=None, bounds=(0, None), method='highs', callback=None, options=None, x0=None, integrality=None)` (https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html; signature TESTED via `inspect`). Result fields: `x`, `fun` (= `c @ x`), `success` (True only when optimal), `status` (0 ok, 1 iteration limit, 2 infeasible, 3 unbounded, 4 numerical), `message`. TESTED: `linprog([1,1], A_ub=[[-1,-2]], b_ub=[-4], bounds=[(0,None)]*2, method="highs")` gives success True, fun 2.0, x [0, 2]. Check `success`/`status` before reading `fun`/`x`. Docs suggest choosing `highs-ds` or `highs-ipm` explicitly in new code.
3. Wheels for cp312 (PyPI JSON, e.g. https://pypi.org/pypi/numpy/2.5.5/json): numpy 2.5.5 and scipy 1.18.1 both ship `win_amd64` and `manylinux_2_27/2_28` x86_64 and aarch64 wheels, so `python:3.12-slim` needs no compiler. psycopg-binary 3.3.9 ships `win_amd64` and `manylinux_2_17` x86_64 and aarch64. Windows installs TESTED; Linux container installs NOT run.

## H. uv (0.11.19 here; all TESTED unless noted)

1. Application project:
   ```
   uv init --app --python 3.12 --no-readme          # add --name milemarker-api, --vcs none if wanted
   uv add "django>=6.1,<6.2" "djangorestframework>=3.18,<3.19" httpx numpy scipy dj-database-url "psycopg[binary]" gunicorn
   uv add --dev pytest pytest-django pytest-socket ruff
   uv lock
   uv sync
   uv run pytest
   ```
   `uv init --app` wrote `.python-version` (`3.12`), `main.py`, `pyproject.toml` (`requires-python = ">=3.12"`), `.gitignore` and a git repo, with NO `[build-system]`. `--package` adds a build system; other flags: `--lib`, `--no-package`, `--bare`, `--vcs`, `--name`. (The docs page https://docs.astral.sh/uv/concepts/projects/init/ was summarised by my fetch tool as app = src layout + build system; that matches `--package`, so trust the tested output.) `uv sync --frozen --no-dev` and `uv run --no-dev ...` worked.
2. Dockerfile pattern (https://docs.astral.sh/uv/guides/integration/docker/; docs advise pinning the uv image tag or digest and adding `.venv` to `.dockerignore`):
   ```dockerfile
   FROM python:3.12-slim
   COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /uvx /bin/
   ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1 PYTHONUNBUFFERED=1
   WORKDIR /app
   RUN --mount=type=cache,target=/root/.cache/uv \
       --mount=type=bind,source=uv.lock,target=uv.lock \
       --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
       uv sync --frozen --no-install-project
   COPY . /app
   RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked
   ENV PATH="/app/.venv/bin:$PATH"
   CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4"]
   ```
   `UV_NO_DEV=1` replaces `--no-dev` (docs). The pyproject.toml bind mount is my addition (docs show only uv.lock). The `uv:0.11.19` image tag is assumed from the installed version, NOT CONFIRMED to exist on ghcr.io. Dockerfile not built (daemon down).
3. Dev dependencies live in `[dependency-groups] dev = [...]` (PEP 735); `tool.uv.dev-dependencies` is legacy and to be deprecated (https://docs.astral.sh/uv/concepts/projects/dependencies/). `uv add --dev pytest` produced `[dependency-groups] dev = ["pytest>=9.2.0"]`.

## I. Docker and PostgreSQL

1. Tags (https://hub.docker.com/_/postgres and https://hub.docker.com/v2/repositories/library/postgres/tags, 18 Nov 2026): 18.7 is current (`latest`, `18`, `18-trixie`), also 17.12, 16.16, 15.20, 14.25 and 19rc2 (release candidate). Community EOL (https://www.postgresql.org/support/versioning/): 18 on 14 Nov 2030, 17 on 8 Nov 2029, 16 on 9 Nov 2028, 15 on 11 Nov 2027, 14 on 12 Nov 2026. Pin `postgres:18` (or `18.7`); 17 also fine, Django 6.1 needs >=15. **Data dir change (18+):** `PGDATA` is `/var/lib/postgresql/18/docker` and the `VOLUME` is `/var/lib/postgresql`, so mount the volume at `/var/lib/postgresql`, not `/var/lib/postgresql/data` (right for <=17): https://hub.docker.com/_/postgres.
2. Healthcheck (standard Compose syntax; NOT from a fetched primary page and NOT TESTED because the daemon was down):
   ```yaml
   services:
     db:
       image: postgres:18
       environment: {POSTGRES_USER: app, POSTGRES_PASSWORD: app, POSTGRES_DB: app}
       volumes: ["pgdata:/var/lib/postgresql"]
       healthcheck:
         test: ["CMD-SHELL", "pg_isready -U app -d app"]
         interval: 5s
         timeout: 3s
         retries: 10
     api:
       build: .
       depends_on:
         db: {condition: service_healthy}
   volumes:
     pgdata: {}
   ```
3. dj-database-url 3.1.2 (https://github.com/jazzband/dj-database-url): `config()` reads `DATABASE_URL`, `default=` is used only if it is unset; `conn_max_age` sets `CONN_MAX_AGE` (default 0); `conn_health_checks` sets `CONN_HEALTH_CHECKS`; `parse(url, ...)` takes a string. `postgres://` and `postgresql://` map to `django.db.backends.postgresql`; the README lists no `postgresql+psycopg://` scheme (NOT CONFIRMED, not needed). The engine is driver-agnostic and Django picks psycopg 3 when installed, so use a plain URL:
   ```python
   import dj_database_url
   DATABASES = {"default": dj_database_url.config(
       default="postgresql://app:app@localhost:5432/app",
       conn_max_age=60, conn_health_checks=True)}
   ```
   Not run against a database.
4. gunicorn (https://gunicorn.org/reference/settings/; the old docs.gunicorn.org host 301-redirects there): `--threads` default 1, "only affects the Gthread worker type", `threads > 1` with the sync worker switches to gthread; default workers 1; default bind 127.0.0.1:8000.
   `gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1 --threads 4`
   Does not run on Windows (needs `fcntl`). One worker keeps the LocMem cache and throttle counters in a single process.

## J. Ruff 0.17.5 (https://docs.astral.sh/ruff/configuration/; config TESTED with `ruff check`, it flagged I001 and F401)

```toml
[tool.ruff]
line-length = 100            # default is 88
target-version = "py312"     # optional; inferred from requires-python (TESTED: 3.12)
extend-exclude = ["**/migrations/*.py"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "DJ", "SIM", "PT", "RUF"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["E501"]
```

Prefix meanings (E/W pycodestyle, F pyflakes, I isort, B bugbear, UP pyupgrade, DJ flake8-django, SIM simplify, PT pytest-style, RUF ruff-specific) confirmed at https://docs.astral.sh/ruff/rules/. For migrations use either `extend-exclude` (as above) or a per-file ignore such as `"**/migrations/*.py" = ["E501", "RUF012"]`, not both. Ruff's built-in default set (E4, E7, E9, F) is NOT CONFIRMED from a primary source this session.

## NOT CONFIRMED or not tested

- Everything against a real PostgreSQL (Docker daemon not running): `test_<NAME>` database naming, CREATEDB requirement, `--reuse-db`, Compose healthcheck, dj-database-url end to end, psycopg under pytest-socket against a local DB.
- pytest-django officially supporting Django 6.1 (not declared; works in my tests).
- dj-database-url declaring Django 6.1 (classifier says "Django :: 6").
- `postgresql+psycopg://` scheme in dj-database-url (not needed).
- That `ghcr.io/astral-sh/uv:0.11.19` exists; the Dockerfile was not built.
- numpy/scipy/psycopg-binary installs inside a Linux container (wheel files exist on PyPI).
- Whether `transaction=True` tests erase session-seeded data (expected, untested).
- Whether DRF 3.18 requires `Decimal` min/max values (both worked).
- Ruff default rule set.
- The pickling of LocMemCache values is shown by source, not by the docs page.
- I briefly wrote two scratch files into the home directory (deleted at once); all other test files are in the session scratchpad only.
