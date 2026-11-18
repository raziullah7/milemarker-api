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

