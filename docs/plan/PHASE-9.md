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

## Gaps found while writing the specs, settled

9S reported 27 points the binding list left open (`reports/phase9-S.md`). Each is settled here and written into the specs.

| # | Open point | Decision |
|---|---|---|
| 1 | Redis memory | Capped at 256 MB. When full it evicts the least recently used key. No persistence. |
| 2 | The cache key's version | One integer, `CACHE_KEY_VERSION`, in `config/settings.py`, used as the cache's `VERSION`. It is raised by hand whenever the shape of a cached value or a planning rule changes; the comment beside it says so. |
| 3 | Trying Redis again after falling back | A process that has fallen back does not touch Redis for 30 seconds, then tries again. A dead Redis therefore costs one short timeout every 30 seconds, not one per request. |
| 4 | "One warning" | One per process each time it falls back, and one line when it returns. Acceptance check 13 reads "each worker logs one warning". |
| 5 | The health endpoint's `cache` value | `memory` when `REDIS_URL` is not set. Otherwise the answering process's own state: `redis`, or `fallback` while it is in its 30-second fallback. Health makes one cheap cache read so that state is current. |
| 6 | Rate limit on the schema and docs addresses | Limited like every other address. Only health is exempt. |
| 7 | The committed OpenAPI document | `docs/openapi.yaml`. |
| 8 | `api_unavailable` in the OpenAPI document | Listed on the route as a 503, described as sent by the proxy when the API cannot be reached. |
| 9 | The coverage floor | The figure measured in Phase 10, rounded down to a whole per cent, recorded in `pyproject.toml`. |
| 10 | Auditing the viewer's packages | `npm audit --omit=dev --audit-level=high` in CI. |
| 11 | "Only nginx has a published port" | Reworded: of the API and nginx, only nginx is published. The database and Redis are published on `127.0.0.1` only, for running from source and for the tests. |
| 12 | `API_PORT` and `POSTGRES_PORT` | Both stay. `API_PORT` now moves nginx's port. `REDIS_PORT` is added. |
| 13 | Start order and health checks | `setup` waits for a healthy database. `api` waits for `setup` to finish successfully and for Redis to have started (not to be healthy: the API must start without it). `web` waits for a healthy `api`. Checks: the database with `pg_isready` on its network address; Redis with a ping; the API with a request to its health endpoint, timeout 5 s, 6 retries; nginx with a request for the viewer's page. |
| 14 | `ROUTING_SERVERS` | Comma-separated URL templates, each containing `{coords}`, tried in order. |
| 15 | `LOG_LEVEL` | Defaults to `INFO`. |
| 16 | The request ID | Made by nginx and passed to the API as `X-Request-ID`. The API makes one if none arrives. It is on every log line and returned in the response header `X-Request-ID`. |
| 17 | nginx's own errors | The API is given 30 seconds to answer (its worst case is about 20). If it cannot be reached or does not answer in time: 503 `api_unavailable`. A request nginx itself refuses as malformed or too long: 400 `invalid_request`. Both in the API's error shape. The API's own error answers pass through untouched. |
| 18 | Security headers | On every answer: `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, and a ban on framing. On the viewer's page only, a content security policy that allows the page's own files, the two map servers, and the workers and inline styles the map library needs. The Swagger page has none, because it loads its script from the CDN. The browser tests fail on any policy violation. |
| 19 | The `Host` the API sees | The client's, passed on by nginx. |
| 20 | A host that is not allowed | 400 `invalid_request` in the error shape (from audit finding Q0a-03). |
| 21 | Redis when running from source | Redis is published on `127.0.0.1:${REDIS_PORT:-6379}`. Running from source uses the in-memory cache unless `REDIS_URL` is set. The Redis tests use database 15 of that Redis and nothing else. |
| 22 | The viewer's three example trips | New York, NY to Los Angeles, CA; Seattle, WA to Miami, FL; Dallas, TX to Houston, TX. |
| 23 | What cancels the intro | A press on the map, a wheel turn, a touch, or the Escape key. |
| 24 | The distance counter | The road miles at the head of the line, so it reads a stop's mile marker as the head reaches that stop. Not the fraction of the line drawn. |
| 25 | When the map servers cannot be reached | The built-in outlines are always the bottom layer. The remote map's description is given 4 seconds; if it has not arrived the viewer goes on with the outlines alone. A tile that fails later simply does not draw. |
| 26 | The pixel-density cap | 2. |
| 27 | The credit lines | The map's credit control stays open and shows what each source asks for. The exact wording and links are taken from each provider's own page in Phase 12 and recorded with their addresses. |
| — | Unknown addresses behind nginx | nginx serves the viewer at `/` and its files under `/assets/`. Every other address goes to the API, so an unknown address still gets the API's JSON 404, as in release 1.0. |

Settled after 9S's second pass:

- nginx's port is published on `127.0.0.1` by default, like the other two. A Compose variable, `BIND_ADDRESS`, changes that for a deployment. The database and Redis stay on `127.0.0.1` always.
- "The response does not change" means the body and the status. Headers are added: the request ID, the security headers, compression.
- The two new `invalid_request` answers (a host that is not allowed; a request nginx refuses) have empty `details`.
- A failed try at Redis during one outage logs nothing new: one warning per worker per outage.
- The database's health check is `pg_isready -h 127.0.0.1`.

9S's own readings are confirmed: NFR-9 keeps its README sentence; D-2 and D-15 merge old and new text; new rows are "From: Ours"; `WEB_CONCURRENCY` defaults to 2; health counts stations from the in-memory index; the cache class sits in the integration layer.

## Rulings on the audits (9.8)

### QA-0a, the delivery side

Report: `reports/phase9-Q0a-delivery.md`. No Critical, 4 Important, 15 Minor, 8 Notes. Every finding is accepted as true unless the ruling says otherwise.

| Finding | Ruling | Where it is fixed |
|---|---|---|
| Q0a-01 Postman checks would pass a wrong plan | Fix. Add the walk along the stops (no leg over 500 miles, tank between 0 and 50, markers increasing, each cost = gallons × price to the cent, one map point per stop), and tighten the reference figures | Phase 13, with the other collection changes |
| Q0a-02 Database and API published on every network interface | Fix first: bind both ports to `127.0.0.1`. It is in the public release, so it goes to `main` at the next gate | Phase 10, controller |
| Q0a-03 `ALLOWED_HOSTS` would enforce nothing; a refused host would get HTML | Fix. `CommonMiddleware` with the slash redirect off, JSON `handler400` and `handler403`, a test that a foreign `Host` gets 400 in the error shape, the comment corrected | Phase 11 |
| Q0a-04 Behind nginx every client would share one rate-limit bucket | Already decided (D-17). Added from this finding: a test that two client addresses get separate buckets | Phase 11 (setting), Phase 12 (through the proxy) |
| Q0a-05 False claim that the limits keep us inside the routing server's one request a second | Correct the sentence. No limiter is built: the per-client limit cannot cap all callers together, and a deployment with real traffic must run its own routing server, as the public server's own rules require. Written as a known limit | Phase 13 |
| Q0a-06 `.env.example` promises variables that never reach the container | Fix. Compose passes each variable through, the file says which process reads which, `API_PORT` added | Phase 11 |
| Q0a-07 README says anything but GET is refused; HEAD and OPTIONS are not | Correct the README row | Phase 13 |
| Q0a-08 Architecture says a road with no fuel plan is asked for again; it is cached | Correct the sentence; the code is right | Phase 13 |
| Q0a-09, Q0a-10 Speed figures from no traceable run; three sets of figures for one trip | Fix. Figures are measured again on the finished stack in Phase 14 and the README names the run; one sentence explains live road against recorded road | Phases 13 and 14 |
| Q0a-11 Health check could pass before PostgreSQL listens on the network; no restart policy | Fix: `pg_isready -h 127.0.0.1`, and `restart: unless-stopped` on the long-running services | Phase 10, controller |
| Q0a-12 Only `.env` is ignored | Fix: ignore `.env*`, keep `.env.example`, in both ignore files | Phase 10, controller |
| Q0a-13 Cache keys carry no version | Already decided (D-15). Added: the README says how to empty the cache, and its "fresh start" sentences are corrected | Phases 11 and 13 |
| Q0a-14 Postman map: identical pins, clipped ends, template pasted four times | Fix: coloured circle markers, bounds from the line and the markers, the template kept once | Phase 13 |
| Q0a-15 Stop 1 carries a station's name but is drawn at the start | Stands (D-1): the response does not change in Part 2. The README's D-1 row and the viewer's first card say plainly that the fuel is priced at that station and drawn at the start | Phases 12 and 13 |
| Q0a-16 The build record reads as a conversation | Fix the wording of the plan files to a neutral voice and link the record once from the README. The history is not rewritten: it is public | Phase 13 |
| Q0a-17 No access log, no time or level on log lines | Already decided (NFR-24) | Phase 11 |
| Q0a-18 README: nothing on using the Postman collection, the versions, or the response fields | Fix | Phase 13 |
| Q0a-19 PM-01 and M01 marked PASS with their condition unmet | Fix now: both marked PARTIAL. Both are run again as written in Phase 14 | Phase 9, controller; Phase 14 |
| Q0a-20 Version `0.1.0` under a `v1.0.0` tag | Fix: the version is set with the release | Phase 14 |
| Q0a-21 Base images on floating tags | Fix: pinned by digest in the new image and Compose files; Dependabot keeps them current | Phase 11 |
| Q0a-22 Dockerfile comment overstates what the user cannot do | Fix the comment | Phase 11 |
| Q0a-23 `psycopg[binary]` in the running image | Stands. The compiled package needs a C toolchain, and the project must install on Windows without one. The database is read once at start-up, never during a request | — |
| Q0a-24 Two JSON spacings | Fix: one compact form | Phase 11 |
| Q0a-25 A hung routing server could starve the health check | Fix: eight request slots, and the health check's timeout and retries set above the routing worst case | Phase 11 |
| Q0a-26 Two figures for one fallback; data README omits the hand-added places | Fix | Phase 13 |
| Q0a-27 Items already scheduled | Noted | Phases 10 to 12 |

### QA-0b, the code changed since the Phase 5 review

Report: `reports/phase9-Q0b-changes.md`. No Critical, 1 Important, 4 Minor, 9 Notes. The reviewer reverted each of the twelve fixes in turn and saw its test fail; eleven are sound, and F4's retry rule is finding Q0b-3. The suite, the slow test and lint were clean in the reviewer's copy.

| Finding | Ruling | Where it is fixed |
|---|---|---|
| Q0b-1 The verifier never checks that a stop's station is near the road: a station 742 miles away, drawn on the line, passed all 16 rules | Fix. New rule R17: each station stop lies within 15 miles of a place of its city and state in the places data, read by the verifier itself. A test swaps a stop's station and must fail | Phase 10, task 10C |
| Q0b-2 R12's tolerance hides up to 8.5 miles | Fix as proposed: apply the line's own scale and compare within 0.1 mile | 10C |
| Q0b-3 The second routing server is not tried after a 3xx, 204, 403, 404, 408, 410 or 451 | Fix. Only a 400 that is not "no road" ends the request at once, because then the request itself is wrong. Every other answer that is not a readable route goes to the second server. Architecture section 9 is corrected to say so | 10C |
| Q0b-4 `stops` and `lowest_possible_stops` are counted by different rules | Fix as proposed: both counted from the shown gallons | 10C |
| Q0b-5 A stop buying 0.00 or a negative amount passes the verifier | Fix: every stop after the first buys more than 0; the first at least 0 | 10C |
| N1 The verifier does not check that the plan is the cheapest | Stands by design: the exactness tests do that. The verifier's description says so | 10C |
| N2 The rate limit can be exceeded by one client on several threads | Stands. The framework reads and writes the count without a lock and says itself it is not a security measure. Written as a known limit | Phase 13 |
| N3 Behind Docker's published port, clients share one bucket | Removed by the proxy design (D-17) | Phase 12 |
| N4 Stale comment on the routing deadline | Fix | Phase 11 |
| N5 `Mexico, USA` is refused as outside coverage | Fix as proposed | 10C |
| N6 An exact half could show the tank 0.01 out | Stands. Not seen on 90 real plans, and already recorded | — |
| N7 Three tests check less than their names say | Fix all three: AN-11 given a purchase worth a cent; the answer test calls the verifier; one trip pinned stop by stop | 10C |
| N8 Two first requests can each build an index or an HTTP client | Fix: a lock around each creation | 10C (client), Phase 11 (index) |
| N9 One client varying the stop cost can push other trips out of the cache | Stands. The cache is bounded; the cost to another caller is one repeated routing call. Written as a known limit | Phase 13 |

## Gate 9 checklist

- [ ] `v1.0.0` is on GitHub; work is on `next`.
- [ ] The trial's result is recorded.
- [ ] Every row of "The spec changes" has a matching line in a spec, checked by the controller.
- [ ] Every new requirement ID appears in a use case or a test case; every new test case states its input and expected output.
- [ ] Both audits are in, and every finding has a ruling.
- [ ] Committed.

## Result

(Filled in when the phase closes.)
