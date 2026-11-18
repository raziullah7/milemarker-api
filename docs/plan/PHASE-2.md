# Phase 2: Foundations and contracts

Baseline: `PLAN.md`, Phase 2. All of this phase is done by the controller.

## Inputs from Phase 1

From `reports/phase1-R1-stack.md` (each tested on Python 3.12 unless noted):

- Versions: Django 6.1.3, DRF 3.18.3, httpx 0.28.1, numpy 2.5.5, scipy 1.18.1, dj-database-url 3.1.2, psycopg 3.3.9, gunicorn 27.0.1, pytest 9.2.0, pytest-django 4.14.0, pytest-socket 0.8.1, Ruff 0.17.5.
- DRF runs with only `rest_framework` and our apps installed. No auth, contenttypes, sessions or admin.
- No `CommonMiddleware`: a redirect to add a slash is awkward for API clients. The route accepts both forms with `re_path(r"^api/v1/route/?$")`.
- `KDTree`, not `cKDTree`: scipy's own docs say to prefer it.
- httpx `timeout=` is per phase, not a total. The 5-second deadline needs a streamed read checked against a clock.
- `pytest-socket` blocks Python-level sockets (httpx, urllib) and allows localhost. It does not see psycopg, which connects in C. So it guards exactly what we need guarded: outside HTTP calls.
- gunicorn cannot run on Windows. It is used only inside Docker; locally the server is `manage.py runserver`.
- A `Decimal` in a plain response dict is rendered as a float, so a CSV price keeps every digit as a JSON number.
- The 6.1 project template adds a `MAILERS` block, which is deleted here.

Decision: PostgreSQL **17**, as the specs say. Version 18 is current and moved its data directory; 17 is supported until 2029 and uses the long-standing path.

## Tasks

| ID | Task | Depends on |
|---|---|---|
| 2.1 | uv project, Python 3.12, dependencies locked | — |
| 2.2 | Django project `config`, apps `stations` and `trips`, settings | 2.1 |
| 2.3 | `docker-compose.yml` with PostgreSQL 17, `.env.example` | — |
| 2.4 | Data files and `data/README.md` | — |
| 2.5 | Saved routes as test fixtures | — |
| 2.6 | Ruff and pytest configuration | 2.1 |
| 2.7 | Every module's interface as code | Phase 1 closed (R3's findings) |
| 2.8 | `tests/conftest.py` and the canary tests | 2.7 |

Task 2.1 was started early, while the last Phase 1 agent was still writing. The user asked for quality over speed, so everything else waits for Gate 1.

## Interfaces

As listed in `phase-material.md`, with these changes from R1: `KDTree` in place of `cKDTree`; the routing client takes its deadline from settings and enforces it with a streamed read.

## Gate 2 checklist

- [x] `docker compose up -d db` starts PostgreSQL and `manage.py migrate` succeeds against it.
- [x] `manage.py check` and Ruff are clean.
- [x] pytest runs against PostgreSQL.
- [x] Every module imports.
- [x] A deliberate test that opens an outside connection fails.
- [x] Committed.

## Result

Closed 18 Nov 2026. Every gate item passed.

### Gate evidence

| Gate item | Evidence |
|---|---|
| PostgreSQL starts and migrates | `docker compose up -d db`: container healthy (PostgreSQL 17). `manage.py migrate`: "No migrations to apply" (there is no model yet) |
| Django check and Ruff clean | "System check identified no issues"; `ruff check .`: "All checks passed"; `ruff format --check .`: all formatted |
| pytest runs against PostgreSQL | `uv run pytest`: 10 passed. PJ-03 runs `SELECT 1` on the test database |
| Every module imports | A script imported all 18 modules with Django set up |
| An outside connection fails | PJ-03: connecting to 192.0.2.1 raises `SocketConnectBlockedError` |

### What exists now

- Django 6.1.3 project `config`, apps `stations` and `trips`. Installed apps are only `rest_framework` and the two apps; there is no middleware.
- `docker-compose.yml` with PostgreSQL 17; settings read `DATABASE_URL`.
- `data/`: the fuel CSV, the places table with its licence, the border outlines, and a README naming each source.
- `tests/fixtures/roads/`: 17 recorded roads (1.24 MB gzipped). `tests/fixtures/stations_small.csv`: the seven-row CSV of the test catalogue.
- Every module's interface as code, with docstrings, raising `NotImplementedError`.
- `tests/test_project.py`: cases PJ-01 to PJ-05.

### Interface decisions made while writing the skeleton

These refine `phase-material.md` and are what Phase 3 builds against.

| Decision | Reason |
|---|---|
| `corridor` has two functions, `stations_along()` (every station near the road) and `thin()` | The planner needs both lists: the full one for the lowest possible bill and for the fallback, the thinned one for the plan |
| `stations/types.py` has `build_index()` | The database reader and the tests build an index the same way |
| `nearest_station()` breaks ties among stations within 0.01 mile of the nearest: cheapest, then lowest ID | Phase 1 decision 3 |
| `answer.py` defines `Stop` and takes the free-stops plan as (price, gallons) pairs | The answer builder needs no knowledge of how either plan was made |
| `fuel.py` raises `NoFuelPlan` itself | `trips/exceptions.py` is plain Python, so the fuel module stays free of Django |
| Business exceptions carry `code`, `message` and `details`, and no HTTP status | Architecture §3 |

### Deviations

- `ruff format` rewrote a code sample inside a research report. The report was restored, and `docs/` is now excluded from Ruff: it holds records, not application code.
- The answer builder (`answer.py`) will be built in Phase 3 by its own agent, not in Phase 4. It is pure and money-critical, and taking it out of Phase 4 leaves that phase with integration only.

### Carried into Phase 3

- The database must be running for the data-side tests: `docker compose up -d db`.
- `SocketConnectBlockedError` is the error the network block raises.
