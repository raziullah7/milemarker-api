# Phase 11: Backend runtime

Baseline: `PLAN.md`, Part 2, Phase 11. The riskiest change of Part 2, so it comes before the viewer.

## Inputs from Phase 10

- `main` and `next` are at the same commit. CI is green: lint, format, types, the migration check, 463 tests with a coverage floor of 98%, the slow test, a dependency audit, the image build, and the Postman collection on the stand-in routing server.
- `scripts/fake_osrm.py` and `docker-compose.e2e.yml` run the whole stack with no public routing call. Two public calls remain; this phase uses none.
- `ROUTING_SERVERS` already comes from the environment. The database and the API are published on `127.0.0.1` only. The default database address is `127.0.0.1`, never `localhost`.
- Carried in: CI's end-to-end job waits on the route address until the health address exists; `check --deploy` needs `--fail-level WARNING`; the stand-in must run from the test image once the running image no longer holds the tests.
- Cut line: if Gate 11 has not passed by Thursday 19 Nov, noon, Redis and the second worker are dropped and the rest goes ahead on one worker.

## Tasks

| ID | Task | Who | Owns |
|---|---|---|---|
| 11K | The runtime: Redis with the fallback, two workers, the one-off setup, settings from the environment, host checking, the health address, the request ID and logs, the image in stages, start order and shutdown, and CI for all of it | Opus | `config/`, `gunicorn.conf.py`, `Dockerfile`, `.dockerignore`, both Compose files, `.env.example`, `trips/views.py`, `trips/urls.py`, `trips/errors.py`, `trips/services/planner.py`, `stations/index.py`, any new module it needs, `tests/conftest.py`, `tests/test_project.py`, new test files, `.github/workflows/ci.yml`, `Makefile` |
| 11S | The OpenAPI document and the Swagger page | Sonnet, after 11K | `trips/schema.py`, `docs/openapi.yaml`, `tests/test_schema.py`, and the lines of `config/settings.py`, `config/urls.py` and `trips/views.py` that wire it in |
| QA-1 | Independent, adversarial review of the cache, the rate limit and start-up | Opus | `reports/phase11-Q1.md` |

11S starts when the controller has checked 11K, because both touch the settings and the address table. Briefs: `briefs/phase11-K-runtime.md`, `briefs/phase11-S-openapi.md`, `briefs/phase11-Q1-review.md`.

## Rulings

- Ruling: in this phase the API keeps its published port, on `127.0.0.1`, and `DJANGO_NUM_PROXIES` stays 0 in the Compose file. Why: nginx arrives in Phase 12; until then the API is what the host talks to, and trusting a forwarded address with no proxy in front would reopen the bypass. Phase 12 moves the port to nginx and sets the variable to 1.
- Ruling: the test suite never sets `REDIS_URL`, so every existing test runs on the in-memory cache. The Redis tests build their own cache object on database 15 of the Redis at `REDIS_TEST_URL` (default `redis://127.0.0.1:6379/15`). Why: the suite empties the cache between tests, which on a shared Redis would be a flush. Cost if wrong: a fault that shows only when the whole application runs on Redis is found by the end-to-end run, not the suite.

## Gate 11 checklist

- [ ] The controller has read every diff.
- [ ] The suite passes, with the Redis tests against a real Redis and against a dead address, timed; none skipped. Coverage is at or above the floor. The slow test, mypy and Ruff are clean.
- [ ] `manage.py check --deploy --fail-level WARNING` passes, and each silenced check has its reason beside it.
- [ ] From `down -v`, `docker compose up --build` with no `.env` starts the database, Redis, the setup (exits 0) and the API; the health address answers 200 with `"cache": "redis"`.
- [ ] Twenty repeats of one trip are all cache hits, across both workers.
- [ ] Drill: Redis stopped, requests still 200, each worker logs one warning, health says `fallback`; Redis started, health says `redis` again within about 30 seconds.
- [ ] A foreign `Host` gets 400 in the error shape.
- [ ] The end-to-end run passes: the Postman collection and the live-check cases on the stand-in.
- [ ] The suite passes in a container.
- [ ] The OpenAPI document is committed, valid, and a test fails if it and the code disagree; the Swagger page renders.
- [ ] QA-1's findings are ruled, fixed, and re-read by a reviewer who did not write the fixes.
- [ ] CI is green on `next`. `next` is merged into `main`.
- [ ] Committed.

## Result

(Filled in when the phase closes.)
