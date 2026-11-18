# Phase 9: Preparation, specs, baseline audit

Baseline: `PLAN.md`, Part 2, Phase 9.

## Inputs from Part 1

- `main` is public and is a valid submission. It is tagged `v1.0.0`; all Part 2 work is on the branch `next`.
- 348 tests pass, lint is clean. About 94 of the 100 allowed public routing calls are used; Part 2 may use the remaining six.
- Never independently reviewed: the Docker files, the README, the Postman collection, the verifier and live runner, and the twelve fixes made after the Phase 5 review.

## Tasks

| ID | Task | Who | Owns |
|---|---|---|---|
| 9.1 | Tag `v1.0.0`, push it, create `next`, record Part 2 in `PLAN.md` | Controller | `docs/plan/PLAN.md` |
| 9.2 | Install GNU make; add every new Python dependency | Controller | `pyproject.toml`, `uv.lock` |
| 9.3 | Trial of `drf-spectacular` on Django 6.1 and DRF 3.18 | Controller | nothing in the repository |
| 9.4 | Apply the spec changes below | Opus (9S) | `docs/requirements.md`, `docs/backend-architecture.md`, `docs/prd.md` |
| 9.5 | Use cases and test cases for everything new, before any code | Opus (9T) | `docs/use-cases.md`, `docs/test-cases.md` |
| 9.6 | QA-0a: audit of the delivery side | Opus | `reports/phase9-Q0a-delivery.md` |
| 9.7 | QA-0b: review of the code changed since the Phase 5 review | Opus | `reports/phase9-Q0b-changes.md` |
| 9.8 | Rule on every audit finding | Controller | this file |

Briefs: `briefs/phase9-*.md`.

## Result of the trial (9.3)

`drf-spectacular` 0.30.0 declares support only up to Django 6.0 and DRF 3.17. Tried with throwaway settings on Django 6.1.3 and DRF 3.18.3:

- The schema view answers 200 with an OpenAPI 3.0.3 document. The Swagger page answers 200.
- It needs `drf_spectacular` in the installed apps, a `TEMPLATES` entry with `APP_DIRS`, and `DEFAULT_SCHEMA_CLASS`.
- Its routes must come before the include of `trips.urls`, whose last pattern matches everything.
- The route view is a plain `APIView`, so the tool cannot guess its parameters or its response: they are declared by hand with `extend_schema`. Until then `spectacular --validate --fail-on-warn` reports one error.
- The Swagger page loads its script from a CDN at `@latest`. `SWAGGER_UI_DIST` pins it.

**Ruling:** use `drf-spectacular`. Cost if wrong: a later Django patch breaks it, and the hand-written document replaces it.

## The spec changes (9.4)

This is the binding list. Requirement and decision IDs continue the existing numbering. The response of `GET /api/v1/route/` does not change in any way.

### Requirements changed

| ID | Now reads | Tier |
|---|---|---|
| FR-18 | A web page, the viewer, draws a trip on a map. It is opened as `/?start=…&finish=…&stop_cost=…`, the same parameters as the API. It is a separate web application; the API's response carries no link to it. | Want |
| FR-19 | The API describes itself: an OpenAPI document at `/api/v1/schema/` and an interactive page at `/api/v1/docs/`. The document covers the route's parameters, its 200 body and every error code. | Want |
| NFR-9 | With Docker, one command starts the database, Redis, the API and the viewer from a fresh clone, with no `.env`. | Need |
| NFR-16 | Add: behind the reverse proxy the limit still counts the real client. A client cannot escape it by sending its own `X-Forwarded-For`. | Want |
| NFR-17 | CI on every push and pull request: lint, format, type check, tests with coverage, the deployment check, the migration check, a dependency audit, the image build, the end-to-end run, and the viewer's lint, type check, unit tests and build. | Want |
| NFR-18 | The two caches and the rate-limit counters live in Redis and are shared by every worker. If Redis cannot be reached the API still answers: each process falls back to its own memory, logs one warning, and returns to Redis when it is back. No request fails or is slowed by more than about half a second because of Redis. | Want |

### Requirements added

| ID | Requirement | Tier |
|---|---|---|
| FR-20 | `GET /api/v1/health/` answers 200 with `{"status": "ok", "stations": <count>, "cache": "redis" \| "fallback" \| "memory"}` when the stations are loaded, and 503 `stations_not_loaded` in the standard error shape when they are not. It is not rate limited. | Want |
| FR-21 | **Viewer, the trip.** The viewer reads `start`, `finish` and `stop_cost` from its address and asks the API once. Opened with no trip, it shows the turning globe and three example trips to choose from. It has no form. | Want |
| FR-22 | **Viewer, the animation.** From a globe seen from space the camera flies down to the route; the route draws itself from start to finish; each fuel stop's marker appears as the line reaches it; distance and fuel cost count up in step. Skip jumps to the end, Replay starts again, and a scrubber moves to any moment. Any mouse or wheel input during the intro cancels it. | Want |
| FR-23 | **Viewer, the panel.** Distance, number of stops, total fuel cost, the lowest possible bill, any warning, the assumptions, and one card per stop with name, city and state, price, gallons, cost and mile. Choosing a card moves the camera to that stop. Every figure shown is the API's, unchanged. | Want |
| FR-24 | **Viewer, errors.** Each API error code has its own message. An unknown place shows the API's suggestions as links that reopen the viewer corrected. A rate-limited answer says when to retry. An API that cannot be reached is said plainly. | Want |
| FR-25 | **Viewer, fallbacks.** With reduced motion requested, it opens on the finished state with no camera animation. Without WebGL2 it shows a static drawing of the route and the same panel. If the map servers cannot be reached it draws on built-in outlines of land and state lines. | Want |
| FR-26 | **Viewer, credit.** The map's sources are credited on screen at all times. | Need |
| NFR-19 | **Several processes behind a proxy.** The API runs as two worker processes (set by `WEB_CONCURRENCY`) behind nginx. Only nginx has a published port. The existing address `http://127.0.0.1:8000/api/v1/route/` keeps working. | Want |
| NFR-20 | **Configuration from the environment.** `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_NUM_PROXIES`, `DATABASE_URL`, `REDIS_URL`, `ROUTING_SERVERS`, `WEB_CONCURRENCY`, `LOG_LEVEL`. Every one has a default that makes a fresh clone run. No secret key is written in the code. Host checking is on. | Want |
| NFR-21 | **Deployment check.** `manage.py check --deploy` passes. Each check that is switched off has its reason written beside it. | Want |
| NFR-22 | **Start and stop.** Migrations and the station load run once, before the API starts, not in every worker. Start order follows health checks. A stop lets a request in flight finish, for up to 30 seconds. | Want |
| NFR-23 | **Compression.** JSON responses and the viewer's files are compressed in transit. | Want |
| NFR-24 | **Logs.** Each line has a time, a level and the request's ID. One line is written per planned trip, with its distance, stops, total, routing calls, cache hit and time taken. | Want |
| NFR-25 | **Image.** Built in stages. The running image holds only what runs, and runs as a user that cannot write to the code. | Want |
| NFR-26 | **Tests without the public routing servers.** A stand-in routing server answers with the saved real roads. An end-to-end run drives the API through the proxy, the Postman collection and the viewer in a browser against it, and in that run the API has no route to the internet. | Want |
| NFR-27 | **Quality gates.** Test coverage is measured and may not fall below a set floor. The Django-free modules pass a type check. Dependencies are audited for known faults. The same checks run before a commit through pre-commit. | Want |
| NFR-28 | **Viewer quality.** TypeScript in strict mode, lint, unit tests, browser tests, an automated accessibility scan with no violations, and every control reachable by keyboard. | Want |
| NFR-29 | **Viewer speed.** The work done per animation frame does not grow with the length of the route. Pixel density is capped. | Want |
| NFR-30 | **Makefile.** The everyday commands are `make` targets; `make help` lists them. The README gives the plain command beside each. | Want |
| NFR-31 | **Licence.** The code is under the MIT licence. The data files keep their own terms. | Want |

### Decisions changed and added

| ID | Question | Decision |
|---|---|---|
| D-2 | What counts as "a map"? | Unchanged for the API: GeoJSON in the response. The viewer (FR-18) draws that same GeoJSON. |
| D-15 | What is cached, and where? | The road and the finished answer, for 24 hours, in Redis. Every key carries a version number, and the answer's key also carries a fingerprint of the station data, so an answer computed from other code or other prices is never served. With `REDIS_URL` unset the cache is the process's own memory, as in release 1.0. |
| D-16 | What happens when Redis is down? | The API answers from each process's own memory. Rejected: failing the request (a cache must not take the service down); treating every error as a miss (that also switches the rate limit off). Cost: during an outage a repeat may land on the other worker and be planned again, and the limit is per process. |
| D-17 | How do clients reach the API? | Through nginx on the published port, on the same origin as the viewer, so no cross-origin rules are needed. nginx overwrites `X-Forwarded-For` with the address it saw, and the API trusts exactly one proxy (`DJANGO_NUM_PROXIES=1`, set in the Compose file; the default stays 0). The API has no published port, which is what keeps the forged-header bypass closed. |
| D-18 | How is the viewer's map drawn? | MapLibre GL JS with its globe projection. From space: NASA's night-lights imagery. Up close: OpenFreeMap's dark vector map. Built in: outlines from Natural Earth. All free, none needs a key. Rejected: CesiumJS (four times the size; its default imagery needs an account); Mapbox, MapTiler, Google 3D tiles and CARTO (each needs a key); deck.gl's own globe (cannot zoom to street level). |
| D-19 | Why does the viewer have no form? | It is a viewer of one trip, named by its address. The owner chose this over a trip-planning form. |
| D-20 | How is the OpenAPI document produced? | By `drf-spectacular` from the code, with the route's parameters, body and errors declared by hand. A test fails if the committed document and the code disagree. The Swagger page's script is loaded from a CDN at a pinned version. |
| D-21 | Host checking and the secret key | Reverses release 1.0. `DJANGO_ALLOWED_HOSTS` defaults to `localhost,127.0.0.1,[::1]`. With no `DJANGO_SECRET_KEY` a random key is made at start-up; nothing is signed, so workers need not share it. |
| D-22 | Two identical new requests at the same moment | Both are routed. A lock would let waiting threads tie up the server to save one free routing call. Kept as a known limit. |
| D-23 | Is it deployed? | No. It is ready to run behind a TLS terminator. TLS, HSTS and redirect settings belong to whatever is put in front and are not set here. |
| D-24 | What does a client see when the API process is down? | nginx answers 503 in the API's own error shape, with the code `api_unavailable`, never an HTML error page. |

### Other edits

- **Requirements section 7 (out of scope):** replace the line about a frontend application with: a trip-planning form, accounts, saved trips, and hosting.
- **Requirements section 9 (acceptance checks):** checks 1 to 10 stay. Add:

  11. From a fresh clone with no `.env`, one Compose command starts the database, Redis, the one-off setup, the API and the viewer. The API answers through the proxy at the address release 1.0 used, and has no published port of its own.
  12. Twenty repeats of one trip are all cache hits with no routing call, whichever worker answers.
  13. With Redis stopped, requests still return 200, one warning is logged, and the health endpoint reports `fallback`. When Redis is started again the shared cache returns.
  14. The 61st request in a minute from one client is refused with 429, whatever `X-Forwarded-For` it sends.
  15. The health endpoint answers 200. The OpenAPI document is valid and describes the parameters, the 200 body and every error code. The Swagger page renders.
  16. `manage.py check --deploy` passes, and CI is green on `main`.
  17. The end-to-end run passes the Postman collection and the viewer's browser tests while the API has no route to the internet.
  18. The viewer, opened on New York to Los Angeles, plays to its end: the route is drawn, there is one marker per stop, and the panel's totals equal the API's.
  19. The viewer's fallbacks work: reduced motion, no WebGL2, and each API error; the accessibility scan reports no violation.
  20. `make help`, `make test`, `make lint` and `make up` work.

- **Architecture document:** section 2 (the proxy in the request flow); section 3 (the cache class and the schema declarations placed in their layers); section 10 rewritten for D-15 and D-16; section 11 gains the health, schema and docs addresses and the `api_unavailable` code; sections 12, 13, 15 and 16 brought in line; two new sections at the end, "Running it" (services, ports, start order, configuration table, shutdown, logging, the front door) and "The viewer" (its parts, the animation beat by beat, the fallbacks, the map sources and their credit lines). Section 4 (folder layout) and section 14 (speed) are left for Phase 13, when the files and measurements exist.
- **PRD:** scope, non-goals and release criteria brought in line.

## Gate 9 checklist

- [ ] `v1.0.0` is on GitHub; work is on `next`.
- [ ] The trial's result is recorded.
- [ ] Every row of "The spec changes" has a matching line in a spec, checked by the controller.
- [ ] Every new requirement ID appears in a use case or a test case; every new test case states its input and expected output.
- [ ] Both audits are in, and every finding has a ruling.
- [ ] Committed.

## Result

(Filled in when the phase closes.)
