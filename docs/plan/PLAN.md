# Mile Marker API: Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` to run each phase file task by task.

## Context

The Spotter take-home (Backend Django Engineer) is due **Friday 20 Nov 2026, 8 pm**. The two specs are finished (`docs/requirements.md`, `docs/backend-architecture.md`) and no code exists.

This file is the **baseline**: what gets delivered and how each thing is proven. It does not say how each phase is carried out. That is written just before each phase starts, in its own file, so each one can use what the earlier phases learned.

**Goal:** a working, tested `GET /api/v1/route/` that returns the route, the fuel stops and the total fuel cost, in this repository, with the documents and Postman collection needed to demonstrate it.

**Spec:** `docs/requirements.md` and `docs/backend-architecture.md`, as corrected in Phase 1.

## How the plan is organised

| File | What it holds | When it is written |
|---|---|---|
| `docs/plan/PLAN.md` | This baseline: deliverables, how each is proven, the gates | Now. Changes only if a deliverable changes. |
| `docs/plan/PHASE-N.md` | How phase N is done: inputs from earlier phases, tasks with owner and files, interfaces, the exact tests with input and expected output, commands, gate checklist | By the controller, at the start of phase N |

Each phase file is closed with a **Result** section: the evidence for every "done when" line, what deviated, and any decision taken. The next phase file starts from that.

The plan files live in `docs/plan/`, with every other document. Briefs given to agents are in `docs/plan/briefs/`, their reports in `docs/plan/reports/`, and the research scripts behind the measurements in `docs/plan/research/scripts/`. Only the scripts' cached data is left out of version control.

I do not pause between phases. I stop only if a gate fails in a way that changes a deliverable in this file.

## How the work is run

**Controller (the main session):** owns every interface, writes every phase file, dispatches the agents, reads every diff, runs every test itself, and makes every commit. An agent's "tests pass" is a claim until the controller has run them.

**Agents:** Opus where a subtle mistake becomes a wrong figure or a missed fault; Sonnet where the spec fully decides the output. Agents never commit, never add a dependency, and never edit a file they do not own. Parallel agents never share a file.

| Phase | Agent task | Model |
|---|---|---|
| 1 | Verify the stack against primary docs (Django 6.1, DRF 3.18, uv, pytest-django, httpx, scipy) | Sonnet |
| 1 | Verify Postman format, test scripts, map view and Newman | Sonnet |
| 1 | Write `use-cases.md` and `test-cases.md` from the specs, before any code | Opus |
| 1 | Write `prd.md` | Sonnet |
| 3 | Data side: places, model, loader, in-memory index | Sonnet |
| 3 | Geometry, station search, border test | Opus |
| 3 | Fuel plan with its exact cross-checks | Opus |
| 3 | Routing client | Sonnet |
| 4 | `plan_trip`, endpoint, errors, cache, rate limit | Opus |
| 5 | Independent response verifier and live test runner | Opus |
| 5 | Whole-project review against both specs | Opus |
| 6 | Dockerfile and one-command start | Sonnet |
| 7 | Postman collection | Sonnet |
| 7 | README, data notes, measured numbers into the docs | Sonnet |

Fourteen agent runs: six Opus, eight Sonnet. Fix-up work returns to the agent that owns the file; after two failed attempts the controller takes over.

## Two decisions that change the specs

**1. Database: PostgreSQL.** (Your decision.)
PostgreSQL is the only database, run through Docker Compose and configured by one `DATABASE_URL` setting. There is no SQLite fallback. The consequence: running the project, and the tests that use the database, needs Docker running. The README leads with `docker compose up`, which starts PostgreSQL and the API together. Tests of the pure modules (fuel, geometry, station search, routing) need no database. Docker Compose and PostgreSQL move from nice-to-have to the foundations (Phase 2), and the one-command start is Phase 6.

**2. An independent read of the specs found 21 things a builder would have had to guess.** A fresh Opus reviewer read only the two spec files and re-ran parts of the research. Its findings are answered in Appendix A and go into the specs in Phase 1, before anything is built. The two that mattered most: the retry server uses a different URL path, so the fallback would have failed silently; and the border check as written would have taken up to 149 ms on its own, breaking the 100 ms limit.

## Rules every phase inherits

- Range 500 miles, 10 miles per gallon, tank 50 gallons. Truck starts empty; start fuel priced at the listed station nearest the start.
- Search radius 5 miles. Thinning window 10 miles. Stop cost default $10, allowed 0 to 100.
- One routing call per new route, one retry on the second server, never more than two. No other network call at request time.
- The fuel, geometry and station-search modules import nothing from Django.
- The CSV is the only source of stations and prices. No API key anywhere. No secret committed.
- No test reaches beyond this machine; a test fixture blocks every connection except the local database.
- Every figure in a response can be reproduced from the response with a calculator.
- Our own work per new request 100 ms or less. Cached repeat 50 ms or less.

## Deliverables

| Deliverable | Where | Proven by |
|---|---|---|
| Working API | `milemarker-api/` | Phases 4, 5 and 8 |
| Corrected requirements and architecture | `docs/requirements.md`, `docs/backend-architecture.md` | Phase 1 gate |
| PRD | `docs/prd.md` | Phase 1 gate |
| Use cases, each traced to requirements and test cases | `docs/use-cases.md` | Phase 1 gate |
| Test cases with input, expected and actual output | `docs/test-cases.md` | Phase 5 gate |
| Automated tests: unit, exactness, integration, verifier | `tests/` | Every gate from Phase 3 |
| Live test runner | `scripts/live_check.py` | Phase 5 gate |
| Postman collection for the demo | `docs/postman/` | Newman, Phase 7 gate |
| PostgreSQL through Docker Compose | `docker-compose.yml` | Phase 2 gate |
| One-command start | `Dockerfile`, `docker-compose.yml` | Phase 6 gate |
| README and data notes | `README.md`, `data/README.md` | Fresh clone, Phase 8 |
| Public repository | `github.com/raziullah7/milemarker-api` | Clone from GitHub, Phase 8 |

## Phases

### Phase 1: Research, corrected specs, test design

**Delivers**
- The project folder with its own git repository, and the docs moved into it.
- Both specs updated with every decision in Appendix A and the database decision.
- Verified notes on the stack and on Postman, each fact with its source.
- The list of cities whose rows in the places table are more than 10 miles apart, with the row to use for each.
- `prd.md`, `use-cases.md`, and `test-cases.md` with inputs and expected outputs filled in and actual outputs empty.

**Done when**
- Every requirement ID appears in at least one use case or test case.
- Every test case states its exact input and its expected output.
- Every line of Appendix A has a matching line in a spec.
- The "no fuel on the road" case (Los Angeles to Seattle) is confirmed on a real route.

### Phase 2: Foundations and contracts

**Delivers**
- An empty Django 6.1 project that runs, with dependencies locked.
- A Compose file with a PostgreSQL 17 service, and settings that read `DATABASE_URL`.
- The data files in `data/`, with their sources and licences written down.
- Saved real routes as test fixtures.
- Every module's interface as code: signatures, data classes, exceptions, docstrings.
- Shared test fixtures, including the one that blocks outside connections.
- The repository's own commit identity (see "What approving this covers").

**Done when**
- `docker compose up -d db` starts PostgreSQL and `manage.py migrate` succeeds against it.
- `manage.py check` and Ruff are clean, and pytest runs against PostgreSQL.
- Every module imports.
- A deliberate test that opens an outside connection fails.

### Phase 3: Core modules (four agents in parallel)

**Delivers** each with unit tests written first:
- Data side: place lookup, station model, loader, in-memory index.
- Geometry: mile markers, station search, border test.
- Fuel plan.
- Routing client.

**Done when**
- The loader on the real CSV reports 8,151 rows, 6,738 stations, 6,626 saved, none unplaced.
- All 58 research place names resolve, and the everyday spellings in Appendix A do too.
- The fuel plan matches a linear-programming solver on 300 random trips and a brute-force search on 150, and passes the hand-worked cases in Appendix B.
- Detroit to Buffalo registers over 200 miles abroad; routes that stay in the USA register a run under 25.
- The border test takes 40 ms or less on the longest saved route.
- The routing client builds the correct URL for each server and retries only when it should.
- The three pure modules import nothing from Django.

### Phase 4: The API

**Delivers**
- `GET /api/v1/route/`, the error responses, the two caches and the rate limit.
- Integration tests on the real stations and saved routes, with routing faked.

**Done when**
- The integration tests pass, including every error code and the cache behaviour.
- The first live call, New York to Los Angeles, returns fewer than 10 stops and a total within 2% of $866.
- A repeat makes no routing call, and so does the same trip with a different stop cost.

### Phase 5: QA (two independent agents, neither wrote the code)

**Delivers**
- A response verifier written from the spec alone, with its own tests.
- A live runner that executes every positive and negative case and prints input, expected, actual, pass or fail.
- `test-cases.md` with the actual outputs filled in.
- A whole-project review, every finding closed.
- The passing figures pinned as regression tests.

**Done when**
- Every live case passes, or has a recorded reason.
- The verifier finds no broken rule in any successful response.
- Every review finding is fixed and re-tested, or recorded as a known limit.
- Both speed limits are met on five runs.

### Phase 6: One-command start

**Delivers**
- A Dockerfile for the API, and the API added to the Compose file beside PostgreSQL.
- Starting Compose waits for the database, migrates, loads the stations and serves.

**Done when**
- From a clean start with no volumes, `docker compose up` answers the New York to Los Angeles case and its cached repeat.
- The whole test suite passes inside the container.
- Starting it a second time does not duplicate stations.

### Phase 7: Demo and docs (two agents in parallel)

**Delivers**
- The Postman collection, each request with its own checks.
- README, `.env.example`, data notes.
- The docs updated with figures measured on the finished API and the final folder layout.

**Done when**
- Newman runs the collection and every check passes.
- The map of the New York to Los Angeles answer draws, in Postman or geojson.io.

### Phase 8: Final verification (controller)

**Delivers**
- An evidence table for the ten acceptance checks in requirements §9.
- The public repository `raziullah7/milemarker-api`, created and pushed only after everything above has passed.
- A final report: what passed, what did not, what is left for you.

**Done when**
- A fresh local clone passes by following the README literally.
- Every acceptance check has recorded evidence.
- Nothing is left uncommitted.
- A clone taken from GitHub starts with `docker compose up` and answers the New York to Los Angeles case.

### After Phase 8, only on your word

OpenAPI page, map page, CI, Redis.

## How it is tested

| Level | What it proves | Network |
|---|---|---|
| Unit | Each module does what its interface says | none |
| Exactness | The fuel plan is the cheapest possible, against two exact methods | none |
| Integration | The modules agree on real stations and real saved routes | none |
| Independent verification | Every response obeys nine rules, checked by code the builders did not write | none |
| Live | Real server, real routing service: 12 positive and 15 negative cases, input and output recorded | paced |
| In the container | The suite passes on PostgreSQL inside the Docker image | none |
| Collection | The Postman collection passes under Newman | paced |
| Fresh clone | A stranger can run it from the README | paced |

The cases themselves are in Appendix B and become `docs/test-cases.md` in Phase 1.

## What approving this covers

- **New folder:** the project, as its own git repository, holding the code and every document including this plan.
- **Files brought in:** the fuel CSV from Downloads; `us_cities.csv` (1.75 MB, MIT) and the Natural Earth outlines (public domain), both already on this machine from the research.
- **Packages:** Django, Django REST Framework, httpx, numpy, scipy, dj-database-url, psycopg, gunicorn, pytest, pytest-django and Ruff from PyPI through uv. Newman from npm through `npx`. The `python:3.12-slim` and `postgres:17` images through Docker.
- **Live routing calls:** fewer than 100 across all phases, one per 1.2 seconds, to the two free OSRM servers.
- **Local commits on `main`** after each gate.
- **The public repository:** in Phase 8, once everything has passed, I create `github.com/raziullah7/milemarker-api` as public and push `main` to it. `gh` is already signed in as raziullah7, and the name is free. Nothing is pushed before that point.
- **Commit author:** set for this repository only to **Razi Ullah** with raziullah7's GitHub no-reply address (`50240668+raziullah7@users.noreply.github.com`), so commits link to the account and expose no personal email. The machine-wide git setting is not touched.
- **Commit trailer:** by default each commit message ends with `Co-Authored-By: Claude Fable 5.2`, which Spotter will see in the public history. Tell me if you want it left off.

## Left for you

- **Docker Desktop must be running** from Phase 2 on, because PostgreSQL needs it.
- Recording the Loom and sending both links in the hiring thread.

---

## Appendix A: decisions from the independent read

Each goes into a spec in Phase 1.

| # | Was unclear or wrong | Decision |
|---|---|---|
| 1 | The retry server's path | It is `/routed-car/route/v1/driving/`, not the main server's path. Both full templates are settings and both are tested. |
| 2 | Border test cost | Sample the road every 2 miles and only test points north of 41.6° or south of 32.8°. At half-mile spacing it took 115 to 149 ms on its own. |
| 3 | The first fill-up | Nearest station is measured from the resolved start place, before routing. That station is removed from the stations along the road, so it cannot appear twice. It is stop 1, at mile 0, at the start point. |
| 4 | "Far" in FR-14 | `summary.first_fill_distance_miles` is always returned. A `warnings` list carries a sentence when it is over 25 miles. |
| 5 | What the cache stores | Two caches. The road is cached by the two coordinate pairs; the answer by those plus the stop cost. `meta` is rebuilt on every response and labels come from the current request. Changing only the stop cost makes no routing call. |
| 6 | Rounding | Trip length is rounded to 0.1 mile first. Stop gallons are rounded to 2 decimals and adjusted so they sum to distance ÷ 10 exactly. Cost is those gallons × the CSV price, rounded half-up to cents with `Decimal`. Prices are shown exactly as in the CSV. |
| 7 | "Lowest possible" bill | Computed with the simple greedy rule on every station along the road, not the thinned list. It is exact when stops are free and takes under 1 ms. |
| 8 | Thinning hiding a valid plan | Whether a plan exists is decided on the full list by scanning the gaps. If the thinned list has no plan but the full one does, the plan is recomputed on the full list. |
| 9 | Ties | Stations are read in station-ID order and candidates sorted by mile, price, ID. Among equally cheap stations within 10 miles the first is kept. A price tie in the loader keeps the first row in the file. |
| 10 | Order of checks | Shape, resolve both places, same-place check, answer cache, stations loaded, road cache or routing call, border, search, plan. Nothing knowable before the routing call is raised after it. |
| 11 | Place spellings | Accepted: `Dallas TX`, `Dallas, TX, USA`, `Phoenix, Arizona`, `Washington, D.C.`, `New York City, NY`, `St.Louis, MO`, `Sault Ste. Marie, MI`. A Canadian province or Mexican state gives `outside_coverage`, not suggestions. |
| 12 | Cities listed under several counties | Rows more than 10 miles apart are not averaged. A short hand-checked table names the row to use. Orlando's rows are 48 miles apart. |
| 13 | Hand-added places | They live in the place lookup, so they work as a start or finish as well as a station city. |
| 14 | Error details | Every error names the field and the text that failed. Shapes are fixed per code. Validation errors, rate limiting, 404, 405 and 500 all use the same body. |
| 15 | Routing failures | Retry on timeout, connection error, 5xx and 429. No retry when OSRM answers that there is no road. One code, `routing_unavailable` (502), with the reason in the details. Each attempt has a 5-second total deadline. |
| 16 | The in-memory index | An empty table is never remembered, so loading stations after the server has started works without a restart. |
| 17 | Layering | Station data classes and the sphere maths live in Django-free modules. `lng` is used everywhere. HTTP status codes are mapped in one API-layer file, not carried by business exceptions. Building the response is a pure module separate from `plan_trip`. |
| 18 | The fuel routine | Written as a loop, not recursion, so no interpreter limit is changed. A separate function reports where an impossible gap starts. |
| 19 | No fuel on the road | The CSV has no station on I-5 through California. Los Angeles to Seattle therefore has no plan. The API says so plainly in a 422, the README explains it, and it is a test case. To be confirmed on a real route in Phase 1. |
| 20 | Coordinates as input (FR-17) | Dropped to nice-to-have. Nothing in the design can decide whether a bare coordinate is inside the lower 48. |
| 21 | Test independence, and NFR-9 | The brute-force check scores each subset with the LP solver, so it shares no code with the routine under test. NFR-9 is reworded to "Docker, or uv with a running PostgreSQL". |

---

Approved 18 Nov 2026, after Part 1 closed. Part 1 above is unchanged and stays the record of Phases 1 to 8.

# Part 2: production readiness, map viewer, CI


## Context

Part 1 (Phases 1 to 8) is finished: the API works, 348 tests pass, and `main` is public at `github.com/raziullah7/milemarker-api`. It is a valid submission today.

Four things were deferred and are now wanted: CI, an OpenAPI page, a map page, and Redis. You also asked for a Makefile, production-level quality, and independent QA agents against everything. Two gaps from Part 1 are closed here as well: the Docker files, README, Postman collection and the twelve post-review fixes were only ever reviewed by me.

**Deadline:** Friday 20 Nov 2026, 8 pm. About 50 hours from now, and the Loom still has to be recorded.

**Goal:** the same API, hardened to a standard that is safe to put behind a TLS terminator and run; a map viewer that looks excellent; CI; and every part reviewed by an agent that did not write it.

**Spec:** `docs/requirements.md` and `docs/backend-architecture.md`, updated in Phase 9 before any code, as in Part 1.

## Your decisions

| Question | Your answer |
|---|---|
| Deploy to a public URL? | No. Ready to deploy, runs anywhere with Docker. |
| The web app | A map viewer only, as a separate React app. It must look really good: a 3D globe that flies into the route, with the details appearing as animation. |
| `make` on this machine | Install GNU make with winget. |

## How `main` stays safe

- Today's `main` is tagged `v1.0.0` and the tag is pushed. That is the fallback submission.
- All work happens on a branch, `next`. It is pushed to GitHub so CI can run on it.
- `next` is merged into `main` only at a gate that has passed. `main` is a valid submission at every moment.
- **Cut lines.** If the Redis and two-worker work has not passed its gate by Thursday noon, it is dropped and the rest goes ahead on one worker. If the globe has not passed by Thursday 8 pm, the viewer ships as a flat map with the same data. Friday is for the Loom and for fixes found while recording, nothing new.

## Target architecture

| Service | What it is | Host port | Role |
|---|---|---|---|
| `db` | `postgres:17` | 5432, local only | Seed data |
| `redis` | Redis, no persistence, capped memory | none | The two caches and the rate-limit counters, shared by every worker |
| `setup` | The API image, runs once | none | `migrate`, then `load_stations`, then exits |
| `api` | gunicorn, 2 workers × 4 threads | **none** | `/api/v1/...`; starts after `setup` succeeds |
| `web` | nginx, unprivileged | **8000** | Serves the viewer at `/`, passes `/api/` to `api`, compresses responses |
| `test` | The test image | none | The suite in a container, as now |

- **Same origin, no CORS.** The viewer calls `/api/v1/route/`. `http://127.0.0.1:8000/api/v1/route/` keeps working for the README, Postman and the live-check script; it now passes through nginx.
- **If Redis is down, the API still answers.** A small cache class falls back to each process's own memory, which is exactly today's behaviour, and logs one warning. No client ever sees a 500 because of Redis.
- **Rate limit behind the proxy.** nginx replaces `X-Forwarded-For` with the address it saw, and the API trusts exactly one proxy. The API has no host port, so the bypass found in Part 1 stays closed. A test forges the header to prove it.
- **Cached answers cannot go stale.** The cache now outlives the process, so the answer's key includes a fingerprint of the station data and a version number.
- **New addresses:** `/api/v1/health/`, `/api/v1/schema/` (OpenAPI), `/api/v1/docs/` (Swagger page), and the viewer at `/?start=…&finish=…`.
- **A local stand-in for the routing server.** `scripts/fake_osrm.py` serves the 17 saved real roads. With it, the whole stack, Newman and the viewer's browser tests run with no call to the public servers.

## What "production level" means here

| Built | Not built, with the reason |
|---|---|
| Settings from the environment (`DJANGO_ALLOWED_HOSTS`, `REDIS_URL`, `ROUTING_SERVERS`, `WEB_CONCURRENCY`, `LOG_LEVEL`); a fresh clone still needs no `.env` | TLS, HSTS, a secrets manager: there is no deployment. The README says where TLS would end. |
| `manage.py check --deploy` clean in CI; each silenced check has a written reason | Separate liveness and readiness endpoints: nothing acts on the difference. One health endpoint. |
| Security middleware and headers; host checking on; no key in code | Metrics, tracing, JSON logs, error tracking: no operator to read them. |
| A health endpoint; health checks and start order in Compose; graceful shutdown that does not cut a request mid routing call | A lock against two identical new requests at once: it would let 8 waiting threads tie up the server to save one free routing call. Stays a written known limit. |
| Multi-stage image holding only what runs; non-root; nginx in front of gunicorn | Kubernetes manifests, autoscaling, a CDN. |
| Response compression (the map is 133 KB of JSON) | Strict typing of the Django layer: the stubs do not yet declare support for Django 6.1. |
| Logs with time, level and a request ID; one line per planned trip | |
| CI: lint, format, types on the pure modules, tests with coverage and a floor, deploy check, migration check, image build, end-to-end on the stand-in routing server, dependency audit; Dependabot; pre-commit | |
| A licence file (MIT, for the code; the data files keep their own terms) | |

## Phases

Each phase gets its `PHASE-N.md` written just before it starts and closed with a Result section, as in Part 1. Agents never commit; I read every diff, run every check myself, and make every commit.

### Phase 9: Preparation, specs, baseline audit

**Delivers**
- Tag `v1.0.0`, branch `next`, this plan appended to `docs/plan/PLAN.md` as Part 2.
- GNU make installed. All new Python dependencies added in one go by me, so no agent touches `pyproject.toml` afterwards.
- A short trial of `drf-spectacular` on Django 6.1 and DRF 3.18 (it declares support only up to 6.0 and 3.17). If it fails, the OpenAPI document is written by hand and served with the same Swagger page.
- Both specs updated first: the four deferred requirements promoted, the new ones added, FR-18 reworded (the viewer is an address, `/?start=…&finish=…`, not a link added to the response, so the response contract does not change), new decisions recorded.
- New test cases written into `docs/test-cases.md` before any code, with inputs and expected outputs.
- **QA-0, two independent read-only audits of what exists now:** the delivery side (settings, Docker files, README, Postman collection, the repository as a public artifact), and all code changed since the Phase 5 review.

**Done when** the trial's result is recorded; every audit finding has a ruling (fix in a named phase, or a reason it stands); every new requirement ID appears in a test case.

### Phase 10: Test harness, Makefile, CI

**Delivers**
- The stand-in routing server, and `ROUTING_SERVERS` read from the environment.
- A second Compose file for end-to-end runs: the stand-in in place of the public servers, and the API on a network with no route out.
- The `Makefile` (targets below), pre-commit hooks, Dependabot.
- GitHub Actions on every push and pull request: the backend checks listed above. Web checks are added in Phase 12.

**Done when** CI is green on `next`; the end-to-end run passes Newman's Demo folder and the live-check cases that have saved roads; the stand-in's request count matches the expected routing calls; `make test`, `make lint` and `make up` work on this machine.

### Phase 11: Backend runtime (the riskiest change, so it goes early)

**Delivers**
- Redis with the fallback; two workers; `gunicorn.conf.py`; the `setup` service; settings from the environment; middleware; the health endpoint; logging; the multi-stage image; health checks; graceful shutdown.
- The OpenAPI schema and Swagger page, with the error shape and examples documented, and a test that the committed schema matches the code.
- Every fix ruled into this phase by QA-0.

**Done when**
- The full suite passes, plus Redis tests against a real Redis and against a dead address (timed, so a dead Redis cannot stall a request).
- From `down -v`, `docker compose up --build` with no `.env` starts everything.
- Twenty repeats of one trip are all cache hits across both workers.
- Drill: stop Redis, requests still return 200 with one warning logged; start it, the shared cache returns.
- `check --deploy` is clean.
- **QA-1 (independent, adversarial):** tries to break the cache and the rate limit, and deletes the fallback to check the tests notice. Findings fixed, then re-reviewed by a fresh agent, not by me.

### Phase 12: The map viewer and the front door

The stack, the storyboard and the checks are in "The viewer" at the end of this part. The builder uses the `frontend-design` skill.

**Delivers**
- A one-hour trial of the globe, the fly-in and the route reveal, before the full build.
- `web/`: the viewer, React + TypeScript (strict) + Vite, built into the nginx image.
- nginx: serves the viewer, passes `/api/` through, compresses, sets security headers, turns its own upstream errors into the API's JSON error shape.
- Compose: port 8000 moves from `api` to `web`.
- CI: web lint, type check, unit tests, build, and a headless browser run against the end-to-end stack.

**Done when**
- Newman passes through nginx; the 61st request in a minute with forged forwarded addresses gets 429; responses are compressed; with `api` stopped, the answer is JSON, not an HTML error page.
- The viewer's browser tests pass, including an accessibility check, a no-WebGL fallback and reduced motion.
- I have watched the animation in a browser on the running stack and recorded what I saw.
- **QA-2 (independent):** frontend code review and a keyboard-only walk through every state. **QA-3 (independent):** security review of nginx, Compose, settings and the image. Findings fixed and re-reviewed by a fresh agent.

### Phase 13: Documents and the stranger test

**Delivers** README (viewer, docs page, Makefile, CI badge, the new architecture, known limits rewritten); architecture and requirements brought in line with the code; `docs/use-cases.md` and `docs/test-cases.md` with actual results; the Postman collection gains the health and schema requests.

**Done when** **QA-4 (independent):** an agent given only the README and the branch's address clones it into an empty folder and follows it literally; every command works and every number matches.

### Phase 14: Final verification and merge (controller)

**Delivers** an evidence table for every new acceptance check; `next` merged into `main` and pushed; the final report.

**Done when** a clone taken from GitHub starts with one command and passes the end-to-end run; CI is green on `main`; one real New York to Los Angeles request through the full stack, and the viewer drawing it; nothing uncommitted.

## Agents

| Phase | Task | Model |
|---|---|---|
| 9 | New test cases from the updated specs | Opus |
| 9 | QA-0a: audit of the delivery side | Opus |
| 9 | QA-0b: review of code changed since the Phase 5 review | Opus |
| 10 | Stand-in routing server and end-to-end Compose file | Sonnet |
| 10 | Makefile, CI, pre-commit, Dependabot | Sonnet |
| 11 | Backend runtime | Opus |
| 11 | OpenAPI schema and Swagger page | Sonnet |
| 11 | QA-1: adversarial review of cache, rate limit, start-up | Opus |
| 12 | The viewer | Opus |
| 12 | nginx, Compose port move, proxy tests | Sonnet |
| 12 | QA-2: frontend review and walkthrough | Opus |
| 12 | QA-3: security review of the whole stack | Opus |
| 13 | Documents | Sonnet |
| 13 | QA-4: the stranger test | Sonnet |
| any | A fresh reviewer for each fix wave | Opus |

Parallel agents never share a file. `config/settings.py`, `pyproject.toml`, `uv.lock` and `docker-compose.yml` each have one owner per phase.

## Makefile

`make help` lists every target. Each is one portable command, so it works under Git Bash, PowerShell and Linux. The README shows the plain command beside each, for anyone without make.

| Target | Does |
|---|---|
| `up`, `down`, `logs`, `ps` | The Compose stack |
| `dev` | Database and Redis in Docker, then the API from source with reload |
| `web-dev` | The viewer's dev server, passing `/api` to the API |
| `test`, `test-slow`, `test-docker`, `coverage` | The suite: from source, the slow exactness test, in a container, with coverage |
| `lint`, `format`, `typecheck`, `check` | Ruff, formatting, types, and all of them plus the tests |
| `e2e` | The end-to-end stack on the stand-in routing server, then Newman and the browser tests |
| `live` | The live-check script against the running stack (uses the public routing server) |
| `load`, `migrate`, `shell` | Station load, migrations, Django shell |
| `clean` | Stop everything and delete the volumes |

## Rules every phase inherits

- Everything in Part 1's rules still holds: PostgreSQL only, no API key, no secret committed, one routing call per new trip, no test reaches beyond this machine.
- A fresh clone starts with one `docker compose up --build` and no `.env`.
- The response of `GET /api/v1/route/` does not change. The independent verifier and the regression pins must pass untouched.
- **Public routing calls: six remain of the hundred, and that is the whole allowance for Part 2.** Everything else runs on the stand-in.
- All documents stay under `docs/`. Commits use the repository's own identity and end with the Claude co-author line, as before.

## Critical files

- Changed: `config/settings.py`, `config/urls.py`, `trips/services/planner.py`, `trips/views.py`, `stations/index.py`, `Dockerfile`, `docker-compose.yml`, `tests/conftest.py`, `pyproject.toml`, `README.md`, the specs.
- New: `config/cache.py`, `gunicorn.conf.py`, `trips/schema.py`, `scripts/fake_osrm.py`, `docker-compose.e2e.yml`, `Makefile`, `.github/workflows/ci.yml`, `.github/dependabot.yml`, `.pre-commit-config.yaml`, `LICENSE`, `web/**`.
- Removed: `docker/entrypoint.sh` (its work moves to the `setup` service and `gunicorn.conf.py`).
- Reused as they are: `tests/verify.py` (the independent verifier), `scripts/live_check.py`, `tests/fixtures/roads/*.json.gz`, `tests/test_regression.py`.

Known traps, from the design review: the catch-all address in `trips/urls.py` swallows any route added after it; `tests/conftest.py` clears the cache in a way that would empty a real Redis, so the suite is pinned to the in-memory cache and Redis tests use their own database; one existing test forbids `DJANGO_ALLOWED_HOSTS` and is reversed on purpose; the API image must not pick up `web/node_modules`.

## Verification

| Level | What it proves | Routing |
|---|---|---|
| Unit and integration, 348 existing plus new | Nothing regressed; new modules do what they say | none |
| Redis tests | Shared cache works; a dead Redis never stalls or fails a request | none |
| Proxy tests | Rate limit cannot be bypassed; errors stay JSON; compression on | none |
| End-to-end stack | The whole thing through nginx: Newman, live-check cases, browser tests | stand-in |
| Viewer in a real browser, by me | The animation actually plays and looks right | stand-in |
| CI | All of the above on a clean machine, on every push | stand-in |
| Fresh clone from GitHub | A stranger can run it from the README | stand-in, then one real call |
| Independent reviews QA-0 to QA-4 | Faults the builders and I did not see | none |

## What approving this covers

- **On GitHub:** pushing the tag `v1.0.0`, pushing the branch `next`, CI running on it, and merging to `main` at passed gates. Dependabot will open pull requests on the repository once its file is merged.
- **On this machine:** installing GNU make for your user with `winget install ezwinports.make`.
- **Packages:** `redis`, `drf-spectacular`, `pytest-cov`, `mypy` and `pip-audit` from PyPI; `react`, `react-dom`, `vite`, `typescript`, `maplibre-gl`, `motion`, `vitest`, Testing Library, Playwright, the axe accessibility scanner and ESLint from npm; the Redis, nginx, Node and Playwright images.
- **Other people's servers, from the visitor's browser:** the viewer loads map tiles from OpenFreeMap and night imagery from NASA, both free and keyless, and the Swagger page loads its script from a pinned CDN address. If the tile servers are unreachable the viewer falls back to its built-in outlines.
- **A licence file:** MIT, in the name Razi Ullah, covering the code only.
- **Changing two written decisions:** host checking is switched on, and the API stops being a single process.

## Not in this plan

Hosting it anywhere; TLS; a trip-planning form in the web app (you chose the viewer only); accounts or saved trips.

## Left for you

- Record the Loom once Phase 14 has passed, or at any point from `v1.0.0` if you would rather not wait.
- Send both links before Friday 8 pm.

---

## The viewer

Researched against primary sources on 18 Nov 2026 (versions checked on npm that day; terms read on each provider's own page). Nothing here needs a key or an account.

### Stack

| Part | Choice | Why |
|---|---|---|
| Renderer | MapLibre GL JS 6 (open source), globe projection | The only keyless option that goes from a globe in space down to readable street maps in one continuous zoom, and can reveal a 5,600-point route without re-sending it each frame. About 455 KB compressed. |
| From space | NASA night-lights imagery (Black Marble, public data) with MapLibre's atmosphere, on a black page | The striking far-out look. Fades out as the camera comes down. |
| Up close | OpenFreeMap's dark vector style (free, no key, no view limits) | Roads and place names once the camera is low. |
| If the tile servers are unreachable | A built-in outline style: land and US state lines from Natural Earth (public domain), bundled in the app | The globe and the route still draw with no map server at all. Also what the browser tests use, so they never depend on someone else's server. |
| Interface animation | Motion (MIT) | One clock drives the camera, the route, the counters and the scrubber together. |
| App | React 19 + TypeScript strict + Vite; no router, no state library, no UI kit | One screen. |

Rejected: CesiumJS (four times the size, and its default imagery needs an account); Mapbox, MapTiler, Google 3D tiles and CARTO (all need a key now); deck.gl's own globe (cannot zoom to street level); a Protomaps self-hosted extract (size unverified, more than a fallback needs).

### What the page does

- A trip comes from the address: `/?start=New York, NY&finish=Los Angeles, CA&stop_cost=10`, the same parameters as the API.
- Opened bare, it shows the slowly turning globe and three example trips to click. There is no form; you chose a viewer.
- A side panel holds the totals, the comparison with the lowest possible fuel bill, any warning, and one card per stop (name, city, price, gallons, cost, mile).
- Every API error has its own state in the panel. An unknown place shows the API's suggestions as links that reopen the page corrected.

### The animation (about 16 seconds, with Skip and Replay)

| Beat | Time | What happens |
|---|---|---|
| 1 | 0–3 s | The night-side globe turns slowly under an atmosphere glow. The trip's title fades in. |
| 2 | 3–8 s | The camera flies from space down to the route, tilting as it arrives. The night lights give way to the road map. The summary cards slide in one after another. |
| 3 | 8–15 s | The route draws itself along the road with a soft glow and a bright moving head. The distance counter runs with it. |
| 4 | during 3 | As the head reaches each fuel stop, its marker pops in, its card appears, and the fuel-cost counter adds that stop's cost. |
| 5 | 15–16.5 s | The camera settles. The finish marker pulses. A scrubber appears: drag it to replay any moment. |
| after | | Click a stop's card and the camera flies to it. Any mouse or wheel input during the intro cancels it and hands over control. |

The route is revealed by moving a colour boundary along the line (one cheap update per frame), not by rebuilding the line. Stop timing uses each stop's position along the drawn line, not its mile marker, because the two differ on a projected map.

### Robustness

- **Reduced motion:** if the visitor's system asks for it, the page opens on the finished state with no fly-in.
- **No WebGL2:** a static drawing of the route with the same panel, and a sentence saying why.
- **Slow graphics:** pixel density capped, terrain off, three small updates per frame.
- **Attribution:** OpenFreeMap, OpenMapTiles, OpenStreetMap and NASA GIBS, always visible.

### How it is proven

| Check | How |
|---|---|
| The animation's maths (progress, stop timing, counters) | Unit tests on pure functions |
| The panel in every state: loading, a plan, each error, suggestions | Component tests with the map replaced by a stand-in |
| It really draws | Headless browser against the end-to-end stack: the route's pixels are sampled on the canvas; the animation is run to its end; screenshots of the finished state compared within a tolerance |
| Accessibility | An automated accessibility scan and a keyboard-only pass |
| Fallbacks | Browser runs with WebGL off and with reduced motion on |
| It looks right | I watch it in a real browser on this machine and say what I saw. Independent reviewer QA-2 does the same. |

### First step of Phase 12: a one-hour trial

Before the full build, a throwaway page proves the three risky things on this machine: the globe with the night imagery and atmosphere, the fly-in, and the route reveal at full size holding a smooth frame rate. Several details could not be confirmed from documentation alone (for example whether the area around the globe is transparent, for a star field). If the trial fails, the cut line applies: a flat map with the same panel and the same route reveal.
