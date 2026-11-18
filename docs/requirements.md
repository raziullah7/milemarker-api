# Mile Marker API: Requirements

What the API must do, how well it must do it, and what is deliberately left out.
This file says **what** is required. `backend-architecture.md` says **how** it is built.

**Status:** every decision in section 6 is settled. Each one was tested against the supplied CSV or a real route on 18 Nov 2026, and the measurement is recorded next to it. The document was then read by an independent reviewer and corrected. The second release then changed FR-18, FR-19, NFR-9, NFR-16 to NFR-18, D-2 and D-15, and added FR-20 to FR-26, NFR-19 to NFR-31, D-16 to D-24 and acceptance checks 11 to 20. Those changes come from `docs/plan/PHASE-9.md`, together with the points they left open, settled there under "Gaps found while writing the specs, settled". The measurements and the review above are of the first release, release 1.0, only.

## 1. Purpose

A truck driver or dispatcher gives a start and a finish inside the USA. The API returns the driving route, the best places to buy fuel along it, and what the fuel for the trip will cost.

Prices differ a lot between truck stops (from $2.69 to $6.40 a gallon in the supplied file), and the truck can only travel 500 miles on a tank. The value of the API is in choosing where to stop and how much to buy, so the trip costs as little as possible and the truck never runs dry.

## 2. Given facts and constraints

| Item | Value | From |
|---|---|---|
| Vehicle range | 500 miles on a full tank | Assignment |
| Fuel economy | 10 miles per gallon | Assignment |
| Tank size | 50 gallons (500 ÷ 10) | Derived |
| Coverage | Start and finish both within the USA | Assignment |
| Fuel prices | The supplied CSV of truck stops, taken as the truth | Assignment |
| Routing and map | A free third-party API, found by us | Assignment |
| Framework | Latest stable Django (6.1.3 on 18 Nov 2026) | Assignment |
| Database | PostgreSQL | Ours |
| Deadline | 3 days from receipt: Friday 20 Nov 2026, 8 pm | Assignment |

Facts about the supplied CSV that shape the requirements:

- 8,151 rows, but only 6,738 distinct stations. 678 stations are listed more than once, and 597 of those at more than one price.
- 6,626 of the stations are in the USA, all in the lower 48 states. The other 112 are in nine Canadian provinces.
- There are no coordinates. Each row has a highway-exit address, a city and a state.
- 1,256 rows have city names padded with spaces.
- Coverage is uneven. California has 8 stations, all in the far south-east of the state. The nearest station to Los Angeles is 121 miles away, to San Francisco 167 miles and to Houston 47 miles.
- No station is listed on Interstate 5 through California. Driving from Los Angeles to Seattle, the first one is in Halsey, Oregon, 886 miles in.

## 3. Tiers

Every requirement below has one of three tiers.

- **Need:** the assignment asks for it, or the result would be wrong or impossible to run without it.
- **Want:** not asked for, but it makes the result easier to trust or to review, and it is cheap.
- **Nice:** a nice-to-have. Built only if time is left once the demo could already be recorded.

Order of work: every need first, then wants from the top of each table down, then nice-to-haves.

The second release differs in two ways. The owner asked for its wants, so they are built though not all of them are cheap. Its order of work is the phase order in `docs/plan/PLAN.md`, Part 2.

The **From** column says where a requirement comes from: **Assignment** (stated in it), **Derived** (follows directly from an assignment line) or **Ours** (our own addition).

## 4. Functional requirements

| ID | The API… | Tier | From |
|---|---|---|---|
| FR-1 | Accepts a start and a finish location in one request, each as a place name such as "Dallas, TX" (D-3). | Need | Assignment |
| FR-2 | Rejects a place that is unknown or outside the lower 48 states and DC with a clear error, before any routing call is made. | Need | Assignment |
| FR-3 | Returns the driving route between the two points, with its distance in miles. | Need | Assignment |
| FR-4 | Returns a map of that route as GeoJSON: the route line and every fuel stop as a marked point, ready to draw in any map viewer. | Need | Assignment |
| FR-5 | Returns each fuel stop: station name, address, city, state, position, miles from the start, price per gallon, gallons to buy and cost. | Need | Assignment |
| FR-6 | Chooses where to stop and how much to buy so the fuel bill is as low as possible, without stopping for a saving smaller than the cost of the stop itself (D-9). | Need | Assignment |
| FR-7 | Never plans a stretch longer than 500 miles between fill-ups, and adds as many stops as that takes. | Need | Assignment |
| FR-8 | Returns the total money spent on fuel for the trip at 10 miles per gallon. The total covers every gallon the trip burns (D-1), and every figure can be reproduced from the response with a calculator (D-14). | Need | Assignment |
| FR-9 | Takes every price from the supplied CSV and shows it with nothing rounded away. | Need | Assignment |
| FR-10 | Returns a clear error, not a wrong plan, when no valid plan exists: a stretch of more than 500 miles with no station listed (Los Angeles to Seattle is one), or a road route that leaves the USA (D-4). | Need | Ours |
| FR-11 | Returns a clear error for missing or unrecognised input. The error names the field that failed and suggests the closest place names it does know. Every error, of any kind, has the same shape. | Need | Ours |
| FR-12 | States in the response the assumptions it used: range, fuel economy, starting fuel and stop cost. | Want | Ours |
| FR-13 | Reports in the response how many routing calls were made, whether the answer came from cache, and how long the routing call and our own work took. | Want | Ours |
| FR-14 | Always reports how far the first fill-up station is from the start, and adds a warning when that is more than 25 miles (D-1). | Want | Ours |
| FR-15 | Reports the lowest fuel bill that was possible with unlimited stops, next to the bill of the plan it chose. | Want | Ours |
| FR-16 | Lets the caller change the stop cost. Zero gives the lowest possible fuel bill regardless of how many stops it takes. | Want | Ours |
| FR-17 | Accepts coordinates (latitude and longitude) as well as place names. | Nice | Ours |
| FR-18 | A web page, the viewer, draws a trip on a map. It is opened as `/?start=…&finish=…&stop_cost=…`, the same parameters as the API. It is a separate web application; the API's response carries no link to it. | Want | Ours |
| FR-19 | The API describes itself: an OpenAPI document at `/api/v1/schema/` and an interactive page at `/api/v1/docs/`. The document covers the route's parameters, its 200 body and every error code. | Want | Ours |
| FR-20 | `GET /api/v1/health/` answers 200 with `{"status": "ok", "stations": <count>, "cache": "redis" \| "fallback" \| "memory"}` when the stations are loaded, and 503 `stations_not_loaded` in the standard error shape when they are not. It is not rate limited. | Want | Ours |

### The viewer

FR-18 above makes the viewer a requirement. These rows say what it does.

| ID | Requirement | Tier | From |
|---|---|---|---|
| FR-21 | **Viewer, the trip.** The viewer reads `start`, `finish` and `stop_cost` from its address and asks the API once. Opened with no trip, it shows the turning globe and three example trips to choose from. It has no form. | Want | Ours |
| FR-22 | **Viewer, the animation.** From a globe seen from space the camera flies down to the route; the route draws itself from start to finish; each fuel stop's marker appears as the line reaches it; distance and fuel cost count up in step. Skip jumps to the end, Replay starts again, and a scrubber moves to any moment. A press on the map, a wheel turn, a touch or the Escape key during the intro cancels it. | Want | Ours |
| FR-23 | **Viewer, the panel.** Distance, number of stops, total fuel cost, the lowest possible bill, any warning, the assumptions, and one card per stop with name, city and state, price, gallons, cost and mile. Choosing a card moves the camera to that stop. Every figure shown is the API's, unchanged. | Want | Ours |
| FR-24 | **Viewer, errors.** Each API error code has its own message. An unknown place shows the API's suggestions as links that reopen the viewer corrected. A rate-limited answer says when to retry. An API that cannot be reached is said plainly. | Want | Ours |
| FR-25 | **Viewer, fallbacks.** With reduced motion requested, it opens on the finished state with no camera animation. Without WebGL2 it shows a static drawing of the route and the same panel. If the map servers cannot be reached it draws on built-in outlines of land and state lines. | Want | Ours |
| FR-26 | **Viewer, credit.** The map's sources are credited on screen at all times. | Need | Ours |

## 5. Non-functional requirements

The speed targets were set from design measurements on a 2,800-mile route. The finished API meets them: the measured figures are in the README and in section 14 of the architecture document.

| ID | Requirement | Tier | From |
|---|---|---|---|
| NFR-1 | **Speed, new request.** Our own work adds no more than 100 ms on top of the routing provider's response time. | Need | Assignment |
| NFR-2 | **Routing calls.** One call to the routing API per new route. One retry is allowed after a timeout or server error, sent to a second server, so never more than two. Asking again for a route that was planned, even with a different stop cost, makes none. | Need | Assignment |
| NFR-3 | **No other external calls.** Start, finish and stations are all looked up locally at request time. | Need | Derived |
| NFR-4 | **Framework.** Built on the latest stable Django. | Need | Assignment |
| NFR-5 | **Free services, no account.** The routing service is free and needs no API key, so a reviewer can run the project without signing up for anything. No secret is committed. | Need | Assignment |
| NFR-6 | **Correct cost.** The fuel algorithm is tested against two independent exact methods, as well as hand-written edge cases. | Need | Ours |
| NFR-7 | **Data preparation.** The station file is cleaned, located and stored in the database once, as seed data. Duplicates, padded names, Canadian rows and missing coordinates are dealt with at that point. Requests read stations from memory, not from the database or the file. | Need | Derived |
| NFR-8 | **Readable.** Logic sits in small, named, commented modules, and the whole design can be walked through in a 5-minute video. | Need | Assignment |
| NFR-9 | **Easy to run.** With Docker, one command starts the database, Redis, the API and the viewer from a fresh clone, with no `.env`. The README covers setup, an example request and the assumptions. | Need | Ours |
| NFR-10 | **Database.** PostgreSQL, run through Docker Compose and configured by one `DATABASE_URL` setting. | Need | Ours |
| NFR-11 | **Speed, repeated request.** An identical request is answered from cache in under 50 ms with no routing call. | Want | Ours |
| NFR-12 | **Provider failure.** If the routing API fails or is slow, the API returns a clear error within about 10 seconds. It does not hang or crash. | Want | Ours |
| NFR-13 | **Wider tests.** Tests for the endpoint (routing faked), the station loader and the search for stations along the route. No test reaches beyond the local machine. | Want | Ours |
| NFR-14 | **Lint.** The code passes Ruff. | Want | Ours |
| NFR-15 | **Postman collection** committed to the repo, each request with its own checks. | Want | Ours |
| NFR-16 | **Rate limit** of 60 requests a minute per client. The free routing servers ask for no more than one request a second. Behind the reverse proxy the limit still counts the real client. A client cannot escape it by sending its own `X-Forwarded-For`. | Want | Ours |
| NFR-17 | **CI** on every push and pull request: lint, format, type check, tests with coverage, the deployment check, the migration check, a dependency audit, the image build, the end-to-end run, and the viewer's lint, type check, unit tests, build and dependency audit. | Want | Ours |
| NFR-18 | **Shared cache.** The two caches and the rate-limit counters live in Redis and are shared by every worker. If Redis cannot be reached the API still answers: each process falls back to its own memory, logs one warning, and returns to Redis when it is back. No request fails or is slowed by more than about half a second because of Redis. | Want | Ours |
| NFR-19 | **Several processes behind a proxy.** The API runs as two worker processes (set by `WEB_CONCURRENCY`) behind nginx. Of the API and nginx, only nginx has a published port. The database and Redis are published on `127.0.0.1` only, for running from source and for the tests. The existing address `http://127.0.0.1:8000/api/v1/route/` keeps working. | Want | Ours |
| NFR-20 | **Configuration from the environment.** `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_NUM_PROXIES`, `DATABASE_URL`, `REDIS_URL`, `ROUTING_SERVERS`, `WEB_CONCURRENCY`, `LOG_LEVEL`. Every one has a default that makes a fresh clone run. No secret key is written in the code. Host checking is on. | Want | Ours |
| NFR-21 | **Deployment check.** `manage.py check --deploy` passes. Each check that is switched off has its reason written beside it. | Want | Ours |
| NFR-22 | **Start and stop.** Migrations and the station load run once, before the API starts, not in every worker. Start order follows health checks. A stop lets a request in flight finish, for up to 30 seconds. | Want | Ours |
| NFR-23 | **Compression.** JSON responses and the viewer's files are compressed in transit. | Want | Ours |
| NFR-24 | **Logs.** Each line has a time, a level and the request's ID. One line is written per planned trip, with its distance, stops, total, routing calls, cache hit and time taken. | Want | Ours |
| NFR-25 | **Image.** Built in stages. The running image holds only what runs, and runs as a user that cannot write to the code. | Want | Ours |
| NFR-26 | **Tests without the public routing servers.** A stand-in routing server answers with the saved real roads. An end-to-end run drives the API through the proxy, the Postman collection and the viewer in a browser against it, and in that run the API has no route to the internet. | Want | Ours |
| NFR-27 | **Quality gates.** Test coverage is measured and may not fall below a set floor. The Django-free modules pass a type check. Dependencies are audited for known faults. The same checks run before a commit through pre-commit. | Want | Ours |
| NFR-28 | **Viewer quality.** TypeScript in strict mode, lint, unit tests, browser tests, an automated accessibility scan with no violations, and every control reachable by keyboard. | Want | Ours |
| NFR-29 | **Viewer speed.** The work done per animation frame does not grow with the length of the route. Pixel density is capped at 2. | Want | Ours |
| NFR-30 | **Makefile.** The everyday commands are `make` targets; `make help` lists them. The README gives the plain command beside each. | Want | Ours |
| NFR-31 | **Licence.** The code is under the MIT licence. The data files keep their own terms. | Want | Ours |

## 6. Decisions

The assignment is silent on these. Each is stated in the README and, where it affects the numbers, in the response.

| ID | Question | Decision | What we measured |
|---|---|---|---|
| D-1 | How much fuel is in the tank at the start? | None. The truck fuels up before leaving, and that fuel is priced at the listed station nearest the start place. Where several stations share that nearest position, the cheapest is used. That station is stop 1, at mile 0, and is not counted again along the road. The total therefore covers every gallon the trip burns. Rejected: starting full, which gives a $0 total for any trip under 500 miles. | For most cities the nearest station is in the city itself. For Los Angeles it is 121 miles away and for Houston 47, which is why FR-14 reports the distance. |
| D-2 | What counts as "a map"? | Unchanged for the API: the route and the fuel stops as GeoJSON in the response, which any map viewer can draw. The viewer (FR-18) draws that same GeoJSON. | — |
| D-3 | What can be given as a location? | A city and state, looked up in an offline table of 29,880 US places. Everyday spellings are accepted: `Dallas, TX`, `Dallas TX`, `Dallas, Texas`, `Dallas, TX, USA`, `st. louis, mo`, `Washington, D.C.`, `New York City, NY`, `Sault Ste. Marie, MI`. Matching ignores case, spaces and punctuation. Street addresses and ZIP codes are not accepted, because recognising them needs a geocoding API and would add calls to every request. | All 58 test names resolved, including Winston-Salem, Coeur d'Alene, St. Louis and O'Fallon. |
| D-4 | What is "within the USA"? | The lower 48 states and DC. Alaska, Hawaii, Puerto Rico, Canadian provinces and Mexico are rejected as outside coverage. A route that runs more than 25 miles in a row through Canada or Mexico is rejected too. | The fastest road from Detroit to Buffalo runs 252 miles through Ontario, and Detroit to Boston 234. Fifteen trips that stay in the USA, including ones along the border and across islands, registered a run of 10 miles at most. |
| D-5 | Where is a station, when the file has no coordinates? | At the centre of the city the CSV gives for it. A station counts as on the route if that point is within 5 miles of the road. Where the places table lists a city under several counties, the average of its rows is used, unless they are more than 10 miles apart; then one named county's row is used. | All 6,626 US stations were placed: 6,615 from the places table and 11 from five places added by hand. Checked against the real position of 36 stations, the city centre was a median 2.8 miles away, and within 5 miles for 86% of them. 22 cities have rows over 10 miles apart; Orlando's are 48 miles apart. |
| D-6 | Which price applies when a station is listed several times? | Every row in the CSV is true, so the truck buys at the cheapest listing. Where two listings tie, the first in the file gives the station its name. | The 597 stations with more than one price differ by a median of 9 cents. Taking the lowest and not the average moves the average station price by half a cent. |
| D-7 | How much fuel must be left at the finish? | None. The plan buys only enough to arrive. | — |
| D-8 | Does the detour to a station use fuel? | No. Stations are treated as being on the route. | With D-5 the detour is at most 5 miles each way. |
| D-9 | How many stops are too many? | Each stop is charged $10 when the plan is chosen, to stand for the time it takes. The $10 is never added to the fuel bill. Without it, the cheapest plan stops for less than a gallon to save a few cents. | New York to Los Angeles, lowest possible fuel bill: $854.65 with 17 stops, the smallest for 0.6 gallons. At $10 a stop: $865.93 with 7 stops, the smallest for 25.8 gallons. That is 1.3% more fuel money for 10 fewer stops. These are the design measurements; the finished API gives $855.95 with 19 stops, and $867.27 with 7. |
| D-10 | Which stations along the route are worth considering? | A station is skipped if another within 10 miles along the route is cheaper, or equally cheap and earlier. This never hides a valid plan: whether a plan exists is decided on every station, and the full list is used if the shorter one has none. When the stop cost is zero no station is skipped, so the bill is the true lowest. | This removes about three quarters of the candidates (363 to 98 on New York to Los Angeles) and raises the fuel bill by 0.2% at most. |
| D-11 | How wide is the search for stations? | 5 miles either side of the road (see D-5). | Widening to 10 miles lowers the bill by less than 1% and admits stations twice as far from the road. |
| D-12 | Which free routing API? | The OSRM public server, which needs no API key, with a second server running the same software for the one retry. Rejected: openrouteservice, which needs an account and key and has maintenance announced for the deadline day. | New York to Los Angeles returned in 1.6 seconds. The second server gave the identical route. |
| D-13 | Which database? | PostgreSQL, the database a Django service runs on in production, started with the API by one Docker Compose command. The database is only used to hold the seed data; no request reads it. | — |
| D-14 | How are the figures rounded? | The trip length is rounded to 0.1 mile. The gallons are rounded as a running total, to 2 decimals, so the stops add up to the distance ÷ 10 exactly and no stop shows more than a full tank. A stop's cost is its gallons × its CSV price, rounded to cents. The total is the sum of the stop costs. The lowest possible bill (FR-15) is rounded the same way. | — |
| D-15 | What is cached, and where? | The road, by its two end points, and the finished answer, by those plus the stop cost, for 24 hours, in Redis. Every key carries a version number, and the answer's key also carries a fingerprint of the station data, so an answer computed from other code or other prices is never served. With `REDIS_URL` unset the cache is the process's own memory, as in release 1.0. | — |
| D-16 | What happens when Redis is down? | The API answers from each process's own memory. Rejected: failing the request (a cache must not take the service down); treating every error as a miss (that also switches the rate limit off). Cost: during an outage a repeat may land on the other worker and be planned again, and the limit is per process. | — |
| D-17 | How do clients reach the API? | Through nginx on the published port, on the same origin as the viewer, so no cross-origin rules are needed. nginx overwrites `X-Forwarded-For` with the address it saw, and the API trusts exactly one proxy (`DJANGO_NUM_PROXIES=1`, set in the Compose file; the default stays 0). The API has no published port, which is what keeps the forged-header bypass closed. | — |
| D-18 | How is the viewer's map drawn? | MapLibre GL JS with its globe projection. From space: NASA's night-lights imagery. Up close: OpenFreeMap's dark vector map. Built in: outlines from Natural Earth. All free, none needs a key. Rejected: CesiumJS (four times the size; its default imagery needs an account); Mapbox, MapTiler, Google 3D tiles and CARTO (each needs a key); deck.gl's own globe (cannot zoom to street level). | Versions checked on npm and terms read on each provider's own page, 18 Nov 2026. MapLibre GL JS is about 455 KB compressed. |
| D-19 | Why does the viewer have no form? | It is a viewer of one trip, named by its address. The owner chose this over a trip-planning form. | — |
| D-20 | How is the OpenAPI document produced? | By `drf-spectacular` from the code, with the route's parameters, body and errors declared by hand. A test fails if the committed document and the code disagree. The Swagger page's script is loaded from a CDN at a pinned version. | `drf-spectacular` 0.30.0 declares support only up to Django 6.0 and DRF 3.17. On Django 6.1.3 and DRF 3.18.3 its schema view answered 200 with an OpenAPI 3.0.3 document, and its Swagger page answered 200. |
| D-21 | Host checking and the secret key | Reverses release 1.0. `DJANGO_ALLOWED_HOSTS` defaults to `localhost,127.0.0.1,[::1]`. With no `DJANGO_SECRET_KEY` a random key is made at start-up; nothing is signed, so workers need not share it. | — |
| D-22 | Two identical new requests at the same moment | Both are routed. A lock would let waiting threads tie up the server to save one free routing call. Kept as a known limit. | — |
| D-23 | Is it deployed? | No. It is ready to run behind a TLS terminator. TLS, HSTS and redirect settings belong to whatever is put in front and are not set here. | — |
| D-24 | What does a client see when the API process is down? | nginx answers 503 in the API's own error shape, with the code `api_unavailable`, never an HTML error page. | — |

## 7. Out of scope

- User accounts, login, or keys for callers
- Trips with more than two points
- Comparing alternative routes against each other
- Live or updated fuel prices
- Outside sources of station data. The CSV is the only source of stations and prices.
- Street addresses and ZIP codes as input (D-3)
- Alaska, Hawaii and anywhere outside the USA (D-4)
- Changing the range or fuel economy per request
- A trip-planning form, accounts, saved trips, and hosting

## 8. Deliverables

- A public GitHub repository
- A Loom video of 5 minutes or less: the API demonstrated in Postman, then a quick code overview
- Both links sent in the hiring thread before the deadline

## 9. Acceptance checks

The work is done when all of these hold.

1. `New York, NY` to `Los Angeles, CA` returns the route, the stops and a total cost, with fewer than 10 stops, counting the fill-up at the start.
2. In that plan, no stretch between fill-ups is longer than 500 miles, the gallons bought equal the distance ÷ 10, and the total equals the sum of the stop costs.
3. The response reports one routing call. Sending the same request again reports none, and so does the same trip with a different stop cost.
4. A trip shorter than 500 miles returns a valid plan with a cost above zero.
5. `Los Angeles, CA` as the start returns a plan and reports the first fill-up distance (about 121 miles). Because that is over the 25-mile limit in FR-14, the response carries a warning.
6. `Honolulu, HI` and an unrecognised place name are each rejected without a routing call. `Detroit, MI` to `Buffalo, NY` is rejected because the road leaves the USA. `Los Angeles, CA` to `Seattle, WA` is rejected because no fuel is listed along the road.
7. The map in the response, opened in a GeoJSON viewer, shows the route with the stops marked.
8. The fuel algorithm's tests pass, including the comparison with the two exact methods.
9. A fresh clone starts with one Docker Compose command, with no API key.
10. The Loom is recorded and both links are submitted before Friday 20 Nov 2026, 8 pm.
11. From a fresh clone with no `.env`, one Compose command starts the database, Redis, the one-off setup, the API and the viewer. The API answers through the proxy at the address release 1.0 used, and has no published port of its own.
12. Twenty repeats of one trip are all cache hits with no routing call, whichever worker answers.
13. With Redis stopped, requests still return 200, each worker logs one warning, and the health endpoint reports `fallback`. When Redis is started again the shared cache returns.
14. The 61st request in a minute from one client is refused with 429, whatever `X-Forwarded-For` it sends.
15. The health endpoint answers 200. The OpenAPI document is valid and describes the parameters, the 200 body and every error code. The Swagger page renders.
16. `manage.py check --deploy` passes, and CI is green on `main`.
17. The end-to-end run passes the Postman collection and the viewer's browser tests while the API has no route to the internet.
18. The viewer, opened on New York to Los Angeles, plays to its end: the route is drawn, there is one marker per stop, and the panel's totals equal the API's.
19. The viewer's fallbacks work: reduced motion, no WebGL2, and each API error; the accessibility scan reports no violation.
20. `make help`, `make test`, `make lint` and `make up` work.
