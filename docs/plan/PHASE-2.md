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

- [ ] `docker compose up -d db` starts PostgreSQL and `manage.py migrate` succeeds against it.
- [ ] `manage.py check` and Ruff are clean.
- [ ] pytest runs against PostgreSQL.
- [ ] Every module imports.
- [ ] A deliberate test that opens an outside connection fails.
- [ ] Committed.

## Result

(Filled in when the phase closes.)
