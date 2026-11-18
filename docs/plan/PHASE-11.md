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

### Rulings on 11K's report

- Ruling: every Redis call gets a deadline of 0.4 seconds, kept by the cache class itself, and a call that misses it falls back like one that could not connect. Why: when the Redis container is stopped its name leaves Docker's DNS, and a name lookup has no socket timeout. Measured in a container on the Compose network: a name that does not exist takes 3.99 s to fail, 1.0 s with the resolver options `timeout:1 attempts:1`, and 3.16 s written with a trailing dot. All three break NFR-18's half second, in the very drill the gate asks for. 0.4 s is above the two socket timeouts together (0.1 + 0.25), so those still fire first for every fault they can see. Cost if wrong: one hand-over to a pool thread for each cache call, some tens of microseconds.
- Ruling: an `X-Request-ID` sent by the client is used only if it is 1 to 64 characters of letters, digits, `.`, `_` and `-`; otherwise the API makes its own. Why: the ID is written into every log line of the request, and the API can be reached with no nginx in front (from source, and in this phase). nginx's own IDs are 32 hexadecimal characters and pass.
- Ruling: the planner reads the station index before the answer cache, as 11K built it. Why: the answer's key carries the station fingerprint. The one visible difference, an empty station table answering `stations_not_loaded` even when another process cached the trip, is the more honest answer. Architecture section 2 is corrected to match.
- Noted: 11K ran `git stash push` and `git stash pop` once, against its brief. The controller checked: the stash list is empty and the working tree holds exactly the files the report lists.

### Rulings on 11S's report

- Accepted: the schema and docs addresses use the library's views with one mixin of ours (`trips/schema.py`). Why: without it the library answers a 429 or a 405 on those two addresses as plain text or HTML, and an `Accept` header it cannot serve as 406, which our handler would turn into a 500. Both are tested.
- Accepted: the library's enum post-processing is off, so each enum stays where it is declared. Why: with it on, the fields called `kind`, `type` and `code` raise collision warnings, and the document must validate with no warning.
- Ruling: `jsonschema` and `pyyaml`, which the schema tests import, are declared in the dev group. Why: they were installed only because the OpenAPI library needs them; a test must not depend on another package's dependencies. The controller added them; no version changed in the lock file.
- Ruling: Swagger UI stays pinned at 5.17.14. Why: the builder could not see the page; the controller opened `/api/v1/docs/` from the rebuilt image in a real browser and saw both operations drawn with no error. Not checked: whether a later release exists that fixes a known fault. Given to QA-3 in Phase 12, with the question of an integrity hash.
- Corrected by the controller, where the code was right and the document was not: architecture section 11 showed `station_id` as text (it is an integer), and said nothing of the empty `fields` that a request Django will not read answers with; the settings' opening comment said the service has no templates.
- Ruling: nginx's `api_unavailable` message is fixed now as "The API cannot be reached.", the wording the OpenAPI document shows, and written into `PHASE-12.md` for the builder of the front door.

### Rulings on the review (QA-1)

QA-1 found 0 Critical, 2 Important, 6 Minor and 7 Notes (`reports/phase11-Q1.md`). It also removed each safety in a scratch copy: the suite noticed all nine removals the brief lists, and a tenth.

| Finding | Ruling | Where |
|---|---|---|
| Q1-01 Important. The rate limit leaks when one client sends requests at once: 164 of 300 passed | Fixed. The framework's limiter reads, adds and writes back; ours counts with the cache's atomic increment, in a window that opens with the client's first request. The cache class passes `incr` through to Redis | Fix wave 11F |
| Q1-02 Important. Setting `DJANGO_ALLOWED_HOSTS` to the deployment's own name makes the health check fail, and in Phase 12 the stack would never start | Fixed. `127.0.0.1` is always allowed. The API builds no address from the host name, so the name the health check uses opens nothing | 11F |
| Q1-03 Minor. A Redis error that is neither a refused connection nor a timeout answers 500 on every request | Fixed for every error of the Redis client: each falls back. Stands for a cached value that can no longer be read after a change of code: `CACHE_KEY_VERSION` exists for that, and the comment beside it says so; catching every error of a read would hide real faults | 11F; the README says how to empty the cache (Phase 13) |
| Q1-04 Minor. A late success ends a fallback that has just begun | Fixed. Only the try made after the 30 seconds can end a fallback | 11F |
| Q1-05 Minor. gunicorn answers a request line over 4,094 bytes with its own HTML 414 | Fixed in part now: the limit is raised to gunicorn's highest, 8,190 bytes, so a long address reaches the API and gets its JSON 400. Above that gunicorn still answers in HTML, which gunicorn gives no way to change. From Phase 12 nginx refuses such a line first, in JSON; its own limit must sit below gunicorn's, and a test sends a 5,000-byte line through it | 11F; Phase 12 |
| Q1-06 Minor. The Redis canary fails when any key in databases 0 to 14 expires during the tests | Fixed. It compares key names: none new, and the canary still there | 11F |
| Q1-07 Minor. Bad values of `DJANGO_NUM_PROXIES`, `LOG_LEVEL` and `WEB_CONCURRENCY` are not refused at start, or not by name | Fixed. Each is checked as `ROUTING_SERVERS` is, and the refusal names the variable | 11F |
| Q1-08 Minor. The schema tests compare the parameters with numbers written in the tests | Fixed. The document takes each parameter's limits and default from the serializer, and a test changes a limit and sees the document follow | 11F |
| Q1-09 Note. The architecture said every address but health is rate limited | Fixed by the controller: an unknown address and a refused host are answered before any view and are not counted | done |
| Q1-10 Note. The document lacks `multipleOf`, the trimming of the two place names, and the form of a request ID | The trimming and the ID's form are added. `multipleOf: 0.01` stands out: validators test it with floating-point division, and would refuse sound values such as 0.07 | 11F |
| Q1-11 Note. The cache keys do not carry the routing server | Stands. Changing `ROUTING_SERVERS` on a live cache is an operator's act with a one-line remedy, restarting Redis, which keeps nothing. The end-to-end stack has a database of its own for this reason. Said in the README (Phase 13) | Phase 13 |
| Q1-12 Note. After `load_stations` on a running stack the workers keep the old stations | Stands, and is now said in architecture section 6: restart the API after loading changed data | done |
| Q1-13 Note. At one trusted proxy with no proxy in front, a forged address picks the bucket | Confirms the ruling to keep 0 in this phase. The Phase 12 brief already demands that nginx overwrite the header | Phase 12 |
| Q1-14 Note. The running image carries `pip` and `apt` from the base image | Stands. They come with the official image; nothing runs them, and the process cannot write where they would install | — |
| Q1-15 Note. gunicorn 27 opens a control socket in the app user's home | Given to QA-3 | Phase 12 |

Not checked by QA-1, and what covers it: the fresh start from `down -v`, the Postman collection and the repeats across both workers were run by the controller (ledger). The Python base image's digest was pulled by that digest in CI's image job.

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
