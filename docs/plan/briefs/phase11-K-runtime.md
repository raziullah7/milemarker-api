# Brief 11K: the backend runtime

A finished, tested Django API runs today as one gunicorn process with an in-memory cache, no middleware, any host accepted and its secret key written in the code. It is being brought to the standard of a service that is safe to put behind a TLS terminator and run. Everything you are to build is already specified and has test cases written. Your job is to build it to the specification, test first.

The repository root is the folder you were given; every path is relative to it.

## Rules

- **Your files:** everything under `config/`; `gunicorn.conf.py` (new); `Dockerfile`; `.dockerignore`; `docker-compose.yml`; `docker-compose.e2e.yml`; `.env.example`; `docker/entrypoint.sh` (to remove); `trips/views.py`, `trips/urls.py`, `trips/errors.py`, `trips/services/planner.py`; `stations/index.py`; any new module the work needs, placed in the layer the architecture document assigns it; `tests/conftest.py`, `tests/test_project.py` and new test files; `.github/workflows/ci.yml`; `Makefile`; and your report `docs/plan/reports/phase11-K.md`.
- **Not yours:** `pyproject.toml` and `uv.lock` (every dependency you need is installed: `redis`, `drf-spectacular`, `pytest-cov`, `mypy`, `pip-audit`); the documents under `docs/` other than your report; `tests/verify.py`; the fuel, geometry, corridor and answer modules. If you believe one of these must change, stop and say so in your reply.
- **The response of `GET /api/v1/route/` does not change:** not its body, not its status. Headers are added. The independent verifier and the regression pins must pass untouched.
- **No request to a public routing server, ever.** Use the stand-in: the end-to-end stack (`docker-compose.e2e.yml`) points the API at it. To check that the ordinary stack is alive, ask for a trip that is refused before routing (`start=Chicgo, IL`) or the health address, never a real trip.
- **Test first.** Each behaviour starts with a test that fails for the stated reason. The test cases are already written, with inputs and expected outputs: build to them. If a case is wrong or cannot be built as written, do not change it: say so in your report, with what you built instead.
- **Simplest thing that meets the specification.** No option, setting or abstraction the specification does not ask for.
- Match the code's style: a description at the top of each module, a docstring on each function, comments that say why, plain names.
- No git command that changes anything. No other agents.

## Read first, in full

- `docs/backend-architecture.md` sections 2, 3, 10, 11, 12, 13, 16 and 18. Section 18 ("Running it") is the specification of most of this work.
- `docs/requirements.md`: FR-20, NFR-16 to NFR-25, D-15, D-16, D-17, D-21 to D-23, acceptance checks 11 to 16.
- `docs/test-cases.md` section 9.1 (test data) and sections 9.2 (CF), 9.3 (CA), 9.4 (HS: the health cases only; the schema and docs cases are another builder's) and 9.5 (HM). Of section 9.6 (PX) build only what does not need nginx.
- `docs/plan/PHASE-9.md`: the three "settled" sections, and in "Rulings on the audits" the findings fixed in Phase 11: Q0a-03, Q0a-06, Q0a-13, Q0a-17, Q0a-21, Q0a-22, Q0a-24, Q0a-25, N4, N8 (the station index).
- `docs/plan/PHASE-11.md`: the two rulings, and the gate you are building toward.
- The code you are changing, and `tests/conftest.py`, `tests/test_api.py`, `tests/test_project.py`, `tests/test_planner.py`.

## What to build

1. **Settings from the environment** (NFR-20, the configuration table of section 18): `DJANGO_SECRET_KEY` (random at start-up when unset), `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_NUM_PROXIES`, `DATABASE_URL`, `REDIS_URL`, `ROUTING_SERVERS` (done), `WEB_CONCURRENCY`, `LOG_LEVEL`. `.env.example` lists each with the process that reads it, and the Compose variables `API_PORT`, `POSTGRES_PORT`, `REDIS_PORT`, `BIND_ADDRESS`. Compose passes each setting through to the containers, so a value in `.env` reaches them.
2. **Host checking and middleware** (D-21, finding Q0a-03): the security middleware; the middleware that actually checks the host, with its slash redirect off so both URL forms still answer with no redirect; a 400 handler that answers `invalid_request` with empty details in the error shape. One existing test forbids `DJANGO_ALLOWED_HOSTS`: it is reversed on purpose; say so in your report. Security headers on the API's answers come from Django, with `Referrer-Policy: strict-origin-when-cross-origin`.
3. **The deployment check** (NFR-21): `manage.py check --deploy --fail-level WARNING` passes. Each check you silence has its reason written beside it; silence only what cannot apply to a service with no cookies, no sessions and TLS ended in front of it.
4. **The cache** (D-15, D-16, section 10): a cache class in `config/cache.py` on Django's built-in Redis backend that falls back to the process's own memory when Redis cannot be reached, stays away from Redis for 30 seconds, logs one warning per outage and one line on return, with the two timeouts and no retries. `CACHE_KEY_VERSION`. The station fingerprint in the answer's key. With `REDIS_URL` unset, the in-memory cache as today. The rate-limit counters use the same cache.
5. **The health address** (FR-20, section 11): its three `cache` values, its 503, no rate limit.
6. **Logs and the request ID** (NFR-24, section 18): the format, the request ID on every line and in the response header, the one line per planned trip exactly as specified, one WARNING line per error answer, an unexpected failure logged once in full.
7. **gunicorn** (`gunicorn.conf.py`): two workers by default from `WEB_CONCURRENCY`, four threads, no preload, an access log on standard output that carries the request ID, a graceful stop of 30 seconds.
8. **Start and stop** (NFR-22, section 18): a `setup` service that migrates and loads the stations once and exits; the API starts after it succeeds; health checks and start order as the section's table gives them; Compose waits at least 30 seconds before killing a container; Redis as the section specifies it (no persistence, 256 MB, least recently used), published on `127.0.0.1` only. `docker/entrypoint.sh` goes.
9. **The image** (NFR-25, findings Q0a-21, Q0a-22): built in stages; a `runtime` stage that holds only what runs, as a user that cannot write to the code, and a `test` stage with the tests, the recordings and the test tools. Base images pinned by digest. The stand-in routing server and the `test` service use the test stage.
10. **Small fixes ruled into this phase:** one compact JSON form for every error answer (Q0a-24); the stale comment on the routing deadline in the settings (N4); a lock around building the station index (N8).
11. **CI and the Makefile:** a Redis service in the checks job; the deployment check as a step; the end-to-end job waits on the health address; anything else the new stack needs. `make dev` starts the database and Redis.

## Two rulings that are yours to honour, not to revisit

- **The API keeps its published port in this phase,** on `127.0.0.1`, and the Compose file leaves `DJANGO_NUM_PROXIES` at 0. nginx comes in the next phase. Test the setting itself: with it at 1, the client is the last forwarded address and separate addresses get separate buckets; at 0, forwarded addresses are ignored, as today.
- **The suite never sets `REDIS_URL`.** Every existing test runs on the in-memory cache. The Redis tests build their own cache object on database 15 of the Redis at `REDIS_TEST_URL` (default `redis://127.0.0.1:6379/15`) and flush only that database. The suite allows connections to `127.0.0.1` only. In the container `test` service Redis is at another address: find a sound way for the Redis tests to run there too, with none skipped, and say what you chose and why.

## Traps

- The last pattern in `trips/urls.py` matches everything. A route added after it is never reached.
- `tests/conftest.py` empties the cache around every test. Pointed at a shared Redis that is a flush of everything in it.
- Overriding the REST framework's settings in a test: pass a copy of the dictionary. Changing it in place does not make the framework reload it, and the change leaks into later tests.
- Each worker loads the places, the borders and the stations as it starts, about 1.3 seconds. Without preload that is deliberate: with it, workers would share an open database connection and an HTTP client.
- On this machine, never use `localhost` for the database or Redis: it stalls each connection for seconds. Use `127.0.0.1`.
- Redis-py retries three times with backoff by default. The specification says no retries; prove the timing with a test against an address that does not answer.
- `docker compose down` on the end-to-end files stops the database too. Leave the ordinary stack running when you finish.

## Prove it

1. `uv run pytest` in full, with Redis running (`docker compose up -d db redis`): none skipped. `uv run pytest --cov`: at or above the floor of 98%. `uv run pytest -m slow`, `uv run mypy`, `uv run ruff check .`, `uv run ruff format --check .`: clean.
2. `uv run python manage.py check --deploy --fail-level WARNING`: no issue.
3. From `docker compose down -v`: `docker compose up --build -d` with no `.env`. Show the services, the setup's exit code, and the health answer.
4. The end-to-end stack: twenty repeats of New York to Los Angeles, all cache hits after the first, with the stand-in's log showing one routing request; then the whole Postman collection under Newman (`make e2e`).
5. The drill, on the end-to-end stack: stop Redis; five requests, all 200; the API's log shows one warning per worker; health says `fallback`. Start Redis; within about 35 seconds health says `redis`; a repeat is a cache hit again.
6. `docker compose --profile test run --rm test`: the suite in a container.
7. Leave the ordinary stack running, and say what state you left it in.

Run one pytest process at a time, in the foreground. Leave nothing running in the background.

## Your report: `docs/plan/reports/phase11-K.md`

What you built, file by file. For each test-case section, the cases built, and any you could not build as written with what you built instead. The commands of "Prove it" with their output. Every decision the specification left to you. Anything you are unsure of.

Reply to the controller with: status, the test counts, the outcome of each "Prove it" step in a line, and any concern.
