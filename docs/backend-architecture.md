# Mile Marker API: Backend Architecture

How the API is built, and why each part is the way it is.
`requirements.md` says what is required. IDs such as FR-6 and D-9 refer to it.

Figures marked *measured* were taken on 18 Nov 2026 against the supplied CSV and real routes. Those in sections 5 to 9 come from the research scripts in `docs/plan/research/`, run before the API was built, and are the reasons for the decisions. Section 14 and the README hold the figures of the finished API.

## 1. The idea

Everything that never changes is prepared once, ahead of time: the station file is cleaned, each station is given a position, and the result is stored in PostgreSQL as seed data.

At request time the API makes **one** call to a routing service to get the road. Everything else is arithmetic on data already in memory: find the stations along the road, give each one a **mile marker** (its distance from the start), and choose where to buy fuel.

## 2. Request flow

```text
GET /api/v1/route/?start=New York, NY&finish=Los Angeles, CA
 │
 ▼
API layer          check the input has the right shape
 │
 ▼
Business layer     plan_trip()
 │   1. look up both places in the offline places table         (memory)
 │   2. reject a trip whose start and finish are the same place
 │   3. return the cached answer if this exact trip was planned  (0 routing calls)
 │   4. make sure the stations are in memory; find the one nearest the start
 │   5. get the road: from the cache, or from the routing service (the ONE outside call)
 │   6. lay mile markers along the road, check it stays in the USA
 │   7. find the stations within 5 miles of the road             (memory)
 │   8. choose the stops and how much to buy at each             (pure arithmetic)
 │   9. build the answer, store it in the cache
 ▼
API layer          turn the answer into JSON
```

Everything that can be known before the routing call is checked before it. The database is **not** on this path. It is read once per process, when the stations are loaded into memory (section 6).

The API is reached directly, on the port it publishes on `127.0.0.1` (section 18). With `REDIS_URL` set, the cache in steps 3, 5 and 9 is Redis, a service on the stack's own network, shared by every worker; if Redis cannot be reached, each process uses its own memory (section 10).

## 3. Layers and what each may do

| Layer | Code | Does | Never does |
|---|---|---|---|
| API | `trips/views.py`, `serializers.py`, `urls.py`, `errors.py`, `schema.py` | Reads the request, checks its shape, calls one business function, returns JSON, turns errors into status codes. Answers the health check. `schema.py` declares the route's parameters, its 200 body and its errors for the OpenAPI document (section 11) | Maths, database queries, network calls |
| Business | `trips/services/planner.py`, `answer.py`, `corridor.py`, `fuel.py`, `geo.py` | All the rules: mile markers, station search, fuel plan, the shape of the answer | Anything to do with HTTP requests or responses |
| Integration | `trips/services/routing.py` | Talks to the routing service. The only module that calls a service outside the stack | Any business rule |
| Integration | `config/cache.py` | The cache class: holds the two caches and the rate-limit counters in Redis, or in the process's own memory when Redis cannot be reached (section 10) | Any business rule |
| Data | `stations/models.py`, `places.py`, `index.py`, `types.py`, `sphere.py`, `load_stations` command | Stores the stations, loads them into memory, resolves place names | Anything about a particular trip |

Rules that follow from this:

- `fuel.py`, `geo.py`, `corridor.py`, `answer.py`, `stations/types.py` and `stations/sphere.py` import nothing from Django. They are plain functions and data classes, so they can be tested with no database and no server.
- The Django ORM is used in exactly two places: the loader writes the stations, and `index.py` reads them once.
- Business errors are plain Python exceptions carrying a code, a message and details. They know nothing about HTTP. `trips/errors.py` is the one place that maps a code to a status.
- Longitude is called `lng` in every name. Only GeoJSON coordinate pairs are written `[lng, lat]`.

In Django terms the "controller" is the **view**. The design patterns used, by their usual names:

| Pattern | Where | What it rules out |
|---|---|---|
| Thin view over a service layer | `trips/views.py`, `trips/services/planner.py` | Business rules in a view; a rule that needs HTTP to be tested |
| Gateway to the external API | `trips/services/routing.py` | A second module that calls out; a call with no deadline |
| Cache-aside with versioned keys | `plan_trip` steps 4 and 6; `CACHE_KEY_VERSION` | A cached answer served after the prices or the code changed (section 10) |
| Graceful degradation | `config/cache.py`, `RedisWithFallback` | A failed request because Redis is down |
| In-memory read model, loaded once | `stations/index.py`, behind a double-checked lock | A request that waits on the database; two threads reading the table at once |
| Spatial index | `trips/services/corridor.py`, a KD-tree | A scan of every station for every point of the road |
| Dynamic programming | `trips/services/fuel.py`, `plan_stops` | A plan that is not the cheapest once each stop has a cost; checked by linear programming and brute force (section 13) |
| One error envelope | `stations/exceptions.py`, `trips/exceptions.py`, `trips/errors.py` | An error that knows its HTTP status; a second error shape |
| Test doubles and an oracle | `scripts/fake_osrm.py`, `tests/fixtures/roads/`, `tests/verify.py` | A test that reaches the network; a test that checks the code against itself |

## 4. Folder layout

```text
milemarker-api/
├── manage.py, pyproject.toml, uv.lock, .python-version, .env.example, README.md
├── Dockerfile, docker-compose.yml, docker-compose.e2e.yml, .dockerignore
├── Makefile, gunicorn.conf.py, .pre-commit-config.yaml
├── .github/workflows/ci.yml   CI
├── config/                    settings.py, urls.py, wsgi.py, cache.py (Redis and its fallback),
│                              logs.py (log lines and request IDs)
├── stations/                  the data side
│   ├── exceptions.py          the base error, and the place and station errors
│   ├── sphere.py              distance maths on a sphere
│   ├── types.py               Place, StationInfo, StationIndex
│   ├── models.py              FuelStation
│   ├── places.py              place name → coordinates, from the offline table
│   ├── index.py               all stations as arrays in memory, loaded once
│   ├── migrations/            the FuelStation table
│   └── management/commands/load_stations.py
├── trips/                     the request side
│   ├── exceptions.py          the trip errors
│   ├── urls.py, views.py, serializers.py, errors.py
│   ├── middleware.py          the request ID
│   ├── throttling.py          the rate limiter
│   ├── schema.py              the OpenAPI document's declarations
│   └── services/
│       ├── planner.py         plan_trip(): runs the steps in section 2
│       ├── routing.py         the routing service client
│       ├── geo.py             mile markers, border test
│       ├── corridor.py        stations along the road
│       ├── fuel.py            the fuel plan
│       └── answer.py          builds the response body
├── data/                      fuel CSV, us_cities.csv and its licence, borders.json, README.md
├── scripts/
│   ├── live_check.py          runs the live cases of the test catalogue against a running server
│   └── fake_osrm.py           the stand-in routing server, answering with recorded roads
├── tests/
│   ├── conftest.py            shared fixtures, including the network block
│   ├── exact.py               the linear-programming and brute-force checks
│   ├── verify.py              the independent verifier
│   ├── cache_worker.py        a worker process for the cache tests
│   ├── test_*.py              one file per area: places, loader, index, sphere, geo, corridor,
│   │                          fuel, answer, routing, planner, api, project, real_data,
│   │                          regression, verify, cache, health, hosts, logs, throttling,
│   │                          schema, fake_osrm
│   └── fixtures/              a small CSV, and recorded roads under roads/
└── docs/
    ├── requirements.md, prd.md, backend-architecture.md, use-cases.md, test-cases.md
    ├── development.md, openapi.yaml
    ├── postman/               the Postman collection
    └── plan/                  the build plan, phase by phase, with briefs and reports
```

## 5. The request path, step by step

| # | Step | Where | Notes |
|---|---|---|---|
| 1 | Validate input | `serializers.py` | `start` and `finish` are required text. `stop_cost` is an optional decimal with at most 2 decimal places, 0 to 100 inclusive, default 10. Unknown parameters are ignored. |
| 2 | Resolve places | `stations/places.py` | Offline lookup (section 6). Start is resolved first, so if both are bad the error names `start`. |
| 3 | Same place | `planner.py` | If both resolve to the same coordinates (to 4 decimals), the request is invalid. The error is reported against `finish`. |
| 4 | Stations loaded | `stations/index.py` | Load on first use. An empty table, or a database that cannot be read, is an error (`stations_not_loaded`), raised here, before the cache is read and before any routing call. The answer's cache key carries a fingerprint of the stations (section 10), so they come first. |
| 5 | Answer cache, then the start's station | `planner.py`, `stations/index.py` | A hit returns at once (section 10). Otherwise find the station nearest the start place. Several stations often share the nearest position; the cheapest of them is used, then the lowest station ID. |
| 6 | Get the road | `routing.py`, `geo.py` | From the road cache, or one routing call (section 9). Then re-space it to one point every half mile, each with its mile marker. |
| 7 | Border check | `geo.py` | Reject if more than 25 miles in a row lie inside Canada or Mexico (D-4). |
| 8 | Station search | `corridor.py` | Stations within 5 miles of the road, each with a mile marker (section 7). The start station is left out. |
| 9 | Fuel plan | `fuel.py` | Chosen stops and gallons (section 8), plus the lowest possible bill for comparison. |
| 10 | Build the answer | `answer.py` | Summary, stops, warnings, GeoJSON map. Stored in the cache. `meta` is added last. |

**Why re-space the road.** The routing service returns points bunched in curves and sparse on straights: 34,931 points for New York to Los Angeles (*measured*). One point every half mile gives 5,594 points. That makes "nearest point on the road" accurate to a quarter mile, gives every point a mile marker, and is also the line returned in the response (127 KB of JSON, down from 861 KB).

**One length, not two.** The routing service's distance, rounded to 0.1 mile, is the trip length `L`. The road is re-spaced on our own distance sums, the markers are then scaled so the last one is `L`, and the last marker is set to `L` exactly. Our own sum differs from the service's figure by at most 0.19% (*measured* on six routes). A road shorter than half a mile is treated as the same place: the request is answered as invalid, after the one routing call that revealed it. The refusal is cached in the road's place (section 10).

## 6. The offline path: seed data

`python manage.py load_stations` runs once after `migrate`. It is safe to run again: it replaces the table inside one transaction. A running API keeps the stations it read at start, so after loading changed data restart it (`docker compose restart api`): until then every worker answers from the old data, and a worker that restarted alone would answer from the new. `--csv` and `--cities` override the default paths under `data/`.

| Step | What happens | Count (*measured*) |
|---|---|---|
| Read the CSV | Standard `csv` module. Whitespace stripped from every field. | 8,151 rows |
| One row per station | Group by `OPIS Truckstop ID`, keep the cheapest listing (D-6). On a price tie, the first row in the file. | 6,738 stations |
| Keep the lower 48 and DC | Drop every row whose state is anything else. In this file those are nine Canadian provinces. | 6,626 stations |
| Give each a position | Look up its city and state in the places table (D-5). | 6,615 found |
| Five places added by hand | Port Wentworth GA, Henrico VA, Evergreen AL, Elizabethport NJ, University Park IL are missing from the table. | 11 more, 6,626 in total |
| Save | `FuelStation` rows: station ID, name, address, city, state, rack ID, price, latitude, longitude. | 6,626 rows |

The command prints these counts. If any US station cannot be placed it lists them and exits with an error. A test asserts the counts against the real CSV.

The price is stored exactly as the CSV has it (up to 8 decimal places).

### The places table

`data/us_cities.csv` holds 29,880 US places with coordinates (MIT licence, from the `kelvins/US-Cities-Database` repository). `places.py` reads it into memory the first time it is needed. The same lookup serves the loader (station cities) and the API (start and finish), so both follow one set of rules.

**Reading a place name:**

1. Trim it, and drop a trailing `USA`, `US` or `United States`. A country is only recognised as a whole final part, so `Santa Fe, New Mexico` is not mistaken for Mexico.
2. Split city from state at the last comma. With no comma, the last word or words are the state if they are a state code or name, longest match first (`Dallas TX`, `Santa Fe New Mexico`). A state name on its own, with no city, is an unknown place.
3. The state is read as letters only, so `D.C.` is `DC`. It may be a code (`TX`) or a name (`Texas`).
4. The city key is the name in capitals with `St`, `Ste`, `Ft` and `Mt` (with or without a dot) expanded to `Saint`, `Sainte`, `Fort` and `Mount`, then everything but letters removed. `Winston-Salem`, `Winston Salem` and `winston salem` are one key.
5. A few aliases are known: with the state NY, `New York City`, `NYC` and `Manhattan` all mean New York. `Manhattan, KS` is still Manhattan, Kansas.

**What comes back:**

- **Found:** the coordinates and a label in the table's own spelling, `City, ST`. The table's spelling is plain: `Saint Louis, MO`, `Winston Salem, NC`, `Mcallen, TX`.
- **Alaska, Hawaii, Puerto Rico, a Canadian province, or a final part that is `Canada` or `Mexico`:** outside coverage. With no comma, a last word `Canada` or `Mexico` counts only if the text did not end in USA: the caller said the place is in the United States. So `Mexico, USA` is an unknown place, with the US places called Mexico as suggestions, and `Tijuana Mexico USA` an unknown place with none; `Tijuana, Mexico, USA` is still outside coverage.
- **Anything else:** unknown place, with up to five suggestions as `City, ST`. With a known state they are the closest names in that state. With no state, or a state that is not recognised, they are that city name in the states that have it, the most populous first by US Census population (`data/large_places.csv`, the 748 incorporated places of 50,000 or more), then by state code (`Dallas` → `Dallas, TX` first). If no state has that name, they are the close names among those large places only, the closest name first (`Dalas` → `Dallas, TX`); only the states that share one name are ordered by population.

**Positions:**

- A place listed under several counties uses the average of its rows.
- The exception is 22 places whose rows are more than 10 miles apart (*measured*; Orlando's are 48 miles apart). For those a short table in `places.py` names the county whose row is used.
- The five hand-added places live in `places.py` too, so they work as a start or finish as well as a station city.

### Loading into memory

`index.py` reads every `FuelStation` once per process, ordered by station ID, the first time it is asked for. It keeps numpy arrays of latitude, longitude and price, the same points on a unit sphere, and each station's details including its exact price.

- The server asks for it as it starts. `config/wsgi.py`, which only a server goes through, calls `warm_up()`: it loads the places table, the border outlines, the views and the station index, so the first request is as fast as any other (about 20 ms of our own work, against about 290 without it; *measured*). Start-up takes 2 to 3 seconds. `migrate`, `load_stations` and the tests do not go through that file.
- Because `warm_up()` touches the database, the server must not be run with gunicorn's `--preload` option, which would open the connection before the worker process exists.
- An empty table, or a database that cannot be read, is never remembered. If the server starts before the stations are loaded, or while the database is down, requests get a clear error (besides the line every error answer gets, one warning names the database error) until the stations can be read, and then work without a restart.
- After reloading the stations, the server must be restarted to pick up the change.

## 7. Finding stations along the route

1. Put every half-mile road point into a KD-tree (a structure that answers "what is the nearest point?" without checking them all).
2. Ask it, for all 6,626 stations in one call, for the nearest road point and its distance.
3. Keep the stations within 5 miles. A station's mile marker is the marker of its nearest road point. Dropped: the start station (it is already stop 1), and any station at mile 0 or at the finish, as the truck cannot use them.
4. Sort by mile marker, then price, then station ID, so the order never depends on chance.
5. Thin the list (D-10): drop a station if another within 10 miles along the road is cheaper, or equally cheap and earlier in the list. Each station is compared with every station found in step 4, including ones that are themselves dropped.

Both limits are inclusive: a station exactly 5 miles from the road is kept, and one exactly 10 miles from a cheaper station is dropped.

*Measured* on New York to Los Angeles: 368 stations within 5 miles, 363 of them between the start and the finish, 98 left after step 5, 4 ms for the whole search. The same search without the tree took 818 ms, which is why `scipy` is a dependency.

Equal mile markers are normal, not rare: stations in the same city share one position, and 4,209 of the 6,626 share theirs with at least one other (*measured*).

Points are converted to x, y, z on a unit sphere before going into the tree, so straight-line distance in the tree corresponds exactly to distance over the ground.

**Why 5 miles.** A station sits at its city centre, not at its exit. Checked against the real position of 36 stations, the city centre was a median 2.8 miles away and within 5 miles for 86% (*measured*). Widening to 10 miles lowered the fuel bill by under 1% on every route tested and admitted stations twice as far from the road.

## 8. The fuel plan

### The model

The trip is a straight line from mile 0 to mile L. Stations sit on it at their mile markers, each with a price. The tank holds 50 gallons, and a gallon moves the truck 10 miles. The truck starts empty (D-1) and may arrive empty (D-7).

The start counts as a station at mile 0, priced at the listed station nearest the start place.

### Is there a plan at all?

A plan exists exactly when no gap between neighbouring stations, or from the last one to the finish, is longer than 500 miles. This is checked first, on every station along the road, by one pass over the mile markers. If it fails, the error says where the first such gap starts and how long it is (FR-10). Los Angeles to Seattle fails at mile 0 with a gap of 886 miles (*measured*).

### Two moves

For any fixed list of stops, the cheapest way to buy is known. At each stop:

- **If the next stop is no dearer:** buy just enough to reach it.
- **If the next stop is dearer:** fill the tank, to carry cheap fuel past it.

This is a published result (Khuller, Malekian and Mestre, "To Fill or Not to Fill: The Gas Station Problem"). It means the only real question is **which stops to make**.

### The stop cost

With fuel as the only cost, the best plan makes many tiny purchases. New York to Los Angeles comes out at 17 stops, one of them for 0.6 gallons, to save a few cents each time (*measured*). Nobody drives like that.

So each stop is charged a fixed $10 while the plan is being chosen (D-9). It stands for the time a stop takes. It is **never added to the fuel bill** in the response. The caller can change it (FR-16), and zero gives the pure lowest fuel bill.

| Stop cost | Stops | Fuel bill | Smallest purchase |
|---|---|---|---|
| $0 | 17 | $854.65 | 0.6 gal |
| $5 | 8 | $860.54 | 0.6 gal |
| **$10** | **7** | **$865.93** | **25.8 gal** |
| $15 | 7 | $865.93 | 25.8 gal |
| $25 | 6 | $884.79 | 39.1 gal |

*Measured* on New York to Los Angeles, 2,801 miles, by the research prototype. At $10 the plan costs 1.3% more fuel than the absolute minimum and makes 10 fewer stops. For comparison, a driver who simply runs the tank down and refuels at whatever station is there pays $972.78. The finished API scales its mile markers slightly differently and computes the lowest possible bill on every station, so its figures are close to these, not identical: 7 stops and $867.27 at $10, and 19 stops and $855.95 at $0 (live, 18 Nov 2026).

### How the best list of stops is found

```text
best(station u, fuel on arrival g):
    options = []
    if the finish is within 500 miles and g is not already enough to reach it:
        options += stop_cost + (fuel to finish − g) × price[u]
    for each station v ahead of u, within 500 miles:
        if price[v] <= price[u]:                       # move 1: just enough
            if g is not already enough to reach v:
                options += stop_cost + (fuel to v − g) × price[u] + best(v, 0)
        else:                                          # move 2: fill up
            options += stop_cost + (50 − g) × price[u] + best(v, 50 − fuel to v)
    return the cheapest option

answer = best(start, 0)
```

The fuel on arrival is only ever 0, or "a full tank minus the drive from the station where it was filled". So there is one case per (station, station where the tank was last filled), and each is worked out once. This is dynamic programming. It is written as a loop from the last station back to the first, not as a function that calls itself, so it never depends on the interpreter's recursion limit. With 98 candidate stations it takes 4 ms (*measured*).

The plan is computed on the thinned list. If the thinned list has no plan but the full list does, it is computed on the full list. That is slow (150 to 350 ms on coast-to-coast roads, *measured*) and rare: none of the recorded roads triggers it, and it is the price of never reporting "no plan" wrongly.

**When the stop cost is zero** the thinned list is not used at all. The plan is the greedy result described next, on every station, so the plan's bill and the lowest possible bill are the same figure (FR-16).

### The lowest possible bill

For comparison (FR-15) the response also carries the lowest fuel bill possible if stops were free. With free stops the answer is the simple greedy rule: buy just enough to reach the next cheaper station, or fill up if there is none within range. It is run on every station along the road, not the thinned list, and takes under 1 ms (*measured*). Its stops are counted as the plan's are: the fill-up at the start always, and after it no purchase shown as 0.00 gallons, though its fuel is in the bill. Its bill is rounded exactly as the plan's is, stop by stop.

The research figure of $854.65 above came from the thinned list. On every station the finished API may report a slightly lower one.

### Why it can be trusted

Both checks are permanent tests (NFR-6):

- **Stop cost zero:** the plan's cost is compared with a linear-programming solver on random trips. In research: 278 trips, largest difference $0.000000.
- **With a stop cost:** the plan is compared with trying every possible subset of stations on random small trips, each subset priced by the same linear-programming solver, so the check shares no code with the routine under test. In research: 161 trips, largest difference $0.000000.

### Money and rounding

Every figure can be reproduced from the response with a calculator (D-14).

1. The trip length `L` is the routing service's distance rounded to 0.1 mile. Total gallons are `L ÷ 10`, which therefore has at most 2 decimals.
2. The gallons are rounded as a running total: the gallons shown for a stop are the rounded total bought up to and including it, less the rounded total before it. The shown gallons therefore add up to the total exactly, and no shown purchase is more than the tank holds.
3. A stop's price is the CSV's own figure with nothing rounded away (for example 3.00733333).
4. A stop's cost is its gallons × its price, rounded half-up to cents. This is done in decimal arithmetic, not floating point.
5. The total is the sum of the stop costs.

Two small rules keep the figures sensible:

- A purchase that rounds to 0.00 gallons is not shown as a stop. Its fuel is not lost, because the running total of step 2 carries it into the next stop. The fill-up at the start is always shown.
- The lowest possible bill is never shown above the plan's bill. Each bill is rounded stop by stop, so two plans within a cent of each other can swap order after rounding. The plan's bill can be bought, so it is the lowest in that case.

## 9. The routing service

**Chosen:** the OSRM public server. Free, no API key, no account. A second server run by FOSSGIS serves the same software and data and takes the one retry. Their paths differ:

```text
1. https://router.project-osrm.org/route/v1/driving/{lng},{lat};{lng},{lat}?overview=full&geometries=geojson
2. https://routing.openstreetmap.de/routed-car/route/v1/driving/{lng},{lat};{lng},{lat}?overview=full&geometries=geojson
```

Both templates are settings, and each has its own test.

| | *Measured* |
|---|---|
| New York to Los Angeles, full road | 1.6 s, 34,931 points, 273 KB compressed |
| Seattle to Miami, full road | 1.4 s, 35,546 points |
| Dallas to Houston, full road | 0.8 s, 2,435 points; the second server returned the identical route |

- **`overview=full` is required.** The default "simplified" road has 55 points for New York to Los Angeles and comes out 154 miles short, which would put every mile marker in the wrong place.
- **When the second server is tried:** after a timeout, a connection error, or any answer that is not a readable route, except the two below. So a 5xx or 429, a redirect, a 204, 403, 404, 408, 410 or 451, and a 200 that cannot be read as a route all go to the second server: they concern the server that answered, not the request. The deadline is 5 seconds per attempt, so a server that does not answer costs two calls (NFR-2) and about 10 seconds (NFR-12).
- **What the deadline bounds.** The HTTP library times connecting and waiting for the answer separately, and our own clock is checked as the answer is read. An attempt whose server is slow both to answer and to send can therefore run to about twice the deadline. The timeouts are not made shorter, because a coast-to-coast request takes up to about 3 seconds to start answering.
- **When it is not:** if the server answers that no road exists between the points (OSRM's `NoRoute` or `NoSegment`), that is the answer. Any other answer with status 400 means the request itself is wrong, and ends it with `routing_unavailable`. In both cases the second server would say the same. This holds for any 400, even one that is not the routing server's own, such as a page from a proxy in front of one server: that case is accepted, so the rule stays simple (review 10R, R10-10).
- **If both fail:** one error, `routing_unavailable`. Its reason is `timeout` only when every attempt timed out, and `error` otherwise.
- **One shared HTTP client** (`httpx`) keeps the connection open between requests, so later calls skip the connection set-up.
- **A User-Agent naming the app** is sent, because the second server's rules ask applications to identify themselves. It is a setting.
- **Usage rules:** both servers ask for no more than one request a second and promise no uptime. The caches keep the calls few. The rate limit (NFR-16) keeps one client from leaning on the free servers through us; it does not hold routing calls to one a second, since one client can send 60 requests in a second and up to 8 routing calls run at once.

**Rejected:**

| Option | Why not |
|---|---|
| openrouteservice | Needs an account and API key, so a reviewer could not run the project straight from a clone. Its address is being changed this month, and it has announced maintenance for 20 Nov, the deadline day. It does offer a truck profile and border avoidance, which is why it is the first thing to add later. |
| Public Valhalla server | Refuses any route over 1,500 km. New York to Los Angeles is about 4,500 km. |

## 10. Caching

Two caches, both in Django's cache framework, both for 24 hours. Prices come from a fixed file and roads change slowly.

| Cache | Key | Holds | Effect |
|---|---|---|---|
| Road | A version number, and the start and finish coordinates, 4 decimals | The re-spaced road, its length, and the server that supplied it; or the refusal, for a road that leaves the USA, has no route, or is under half a mile | The same trip with a different stop cost makes no routing call |
| Answer | The road key, a fingerprint of the station data, both place labels, and the stop cost to 2 decimals | The response body without `meta` | A repeated request skips all the arithmetic too (NFR-11) |

- `meta` is rebuilt for every response. `cache_hit` says whether the answer came from the answer cache. When only the road was cached, `cache_hit` is false and `routing_calls` is 0. `timings_ms.routing` is 0 whenever no routing call was made.
- Place labels are part of the answer key, because two places can share coordinates (Ackermanville and Flicksville, PA do). They are always the table's own spelling, so `new york ny` and `New York, NY` share one cached answer.
- A refusal after routing (the road leaves the USA, there is no road, or the road is under half a mile) is cached in the road's place, so a repeat makes no routing call and gets the identical answer. The road is also cached before the fuel plan is tried, so a trip with no fuel plan makes no routing call when it is asked for again. Only a routing failure is never cached: it is asked for again each time (EP-08).

### Where the caches live (D-15)

With `REDIS_URL` set, both caches and the rate-limit counters are in Redis, and every worker shares them: a repeat is a hit whichever worker answers it (NFR-18). The Compose file sets `REDIS_URL`. With it unset, they are in the process's own memory, as in release 1.0. That is how the API runs from source, unless `REDIS_URL` is set there too. The cache class in `config/cache.py` handles both.

Redis keeps nothing on disk. Its memory is capped at 256 MB; when it is full, it evicts the least recently used key.

### Why the keys carry a version and a fingerprint

The cache now outlives the process: a cached answer survives a restart of the API, a new version of the code, and a reload of the stations. So every key carries a version number, and the answer's key also carries a fingerprint of the station data. An answer computed from other code or other prices is then never served, because its key no longer matches.

The version number is one integer, `CACHE_KEY_VERSION`, in `config/settings.py`, used as the cache's `VERSION`. It is raised by hand whenever the shape of a cached value or a planning rule changes; the comment beside it says so.

### The rate-limit counter

The limit is 60 requests in a minute for each client (NFR-16). It is counted in the cache, so every worker shares the count.

- **A window opens with a client's first request and lasts 60 seconds.** The 61st request inside it is answered 429, with the seconds left in the window as `retry_after_seconds` and in the `Retry-After` header. The next request after the window ends opens a new one. A client that times it can therefore send 60 at the end of one window and 60 at the start of the next; the limit is on each window, not on every 60 seconds that can be drawn.
- **Each request is counted with one atomic step,** the cache's own increment (Redis `INCR`). The framework's built-in limiter reads a client's history, adds to it and writes it back; with two workers of four threads on one Redis, requests sent at once overwrote each other's entries, and 164 of 300 passed (*measured*, review QA-1). The limiter in `trips/throttling.py` replaces it.
- **Which addresses.** The route, the schema and the Swagger page count against the one limit. The health address does not. Neither does an answer given before any view runs: the 404 for an unknown address and the 400 for a host that is not allowed.

### When Redis cannot be reached (D-16)

The API still answers. Each process falls back to its own memory for both caches and the rate-limit counters, and returns to Redis when it is back. No request fails, or is slowed by more than about half a second, because of Redis (NFR-18).

- **Timeouts.** A connection to Redis times out after 0.1 seconds and a command after 0.25 seconds, with no retries. "About half a second" in NFR-18 is tested as 0.5 seconds: a request with Redis unreachable takes no more than 0.5 seconds longer than the same request with Redis up.
- **A deadline on every call.** The two timeouts cover a Redis that refuses or hangs. They do not cover looking up its name: when the Redis container is stopped its name leaves Docker's DNS, and the lookup alone took 4 seconds to fail (*measured*, in a container on the Compose network; 1 second with the resolver told to try once for one second). So the cache class runs each Redis call on a small pool of threads and waits for it at most 0.4 seconds, more than the two timeouts together. A call that misses the deadline falls back like one that could not connect, and is left to finish by itself.
- **Trying again.** A process that has fallen back does not touch Redis for 30 seconds, then tries again. A dead Redis therefore costs one short timeout every 30 seconds, not one per request. A try that fails starts another 30 seconds of fallback.
- **What counts as unreachable.** Any error of the Redis client: a refused connection, a timeout, a missed deadline, and also an error Redis answers with, such as a database that does not exist or a server that is read-only. Each falls back in the same way. An answer that arrives late, from a call sent before the outage began, does not end the fallback: only the one try made after the 30 seconds can.
- **What is logged.** Each process logs one warning when it falls back, and one line when it returns to Redis. A failed try during the same outage logs nothing new, so a worker logs one warning per outage (acceptance check 13).

During the outage:

- a repeat may land on the other worker and be planned again;
- each process counts the rate limit on its own.

Rejected: failing the request, because a cache must not take the service down; treating every Redis error as a cache miss, because that also switches the rate limit off.

## 11. API contract

### Request

```text
GET /api/v1/route/?start=New York, NY&finish=Los Angeles, CA
GET /api/v1/route/?start=New York, NY&finish=Los Angeles, CA&stop_cost=0
```

GET, because planning a trip reads data and changes nothing. It can be repeated safely and tried from a browser's address bar.

### Response (200)

Small parts first, the map last, so the result is readable in Postman without scrolling past coordinates. The numbers below are from the research run; "…" marks values left out.

```json
{
  "summary": {
    "start": {"label": "New York, NY", "lat": 40.748, "lng": -73.997},
    "finish": {"label": "Los Angeles, CA", "lat": 33.973, "lng": -118.248},
    "distance_miles": 2800.7,
    "gallons": 280.07,
    "total_fuel_cost": 865.93,
    "stops": 7,
    "lowest_possible_fuel_cost": 854.65,
    "lowest_possible_stops": 17,
    "first_fill_distance_miles": 3.1
  },
  "warnings": [],
  "assumptions": {
    "range_miles": 500, "miles_per_gallon": 10, "tank_gallons": 50,
    "starting_fuel_gallons": 0, "stop_cost": 10.0, "search_radius_miles": 5
  },
  "fuel_stops": [
    {
      "order": 1, "kind": "start", "station_id": 73127, "name": "DELTA", "address": "…",
      "city": "Jersey City", "state": "NJ", "mile_marker": 0.0,
      "lat": 40.748, "lng": -73.997,
      "price_per_gallon": 3.239, "gallons": 39.15, "cost": 126.81
    }
  ],
  "map": {"type": "FeatureCollection", "features": ["…"]},
  "meta": {
    "routing_calls": 1, "cache_hit": false, "routing_server": "router.project-osrm.org",
    "timings_ms": {"routing": 1620, "own": 55, "total": 1675}
  }
}
```

**Unchanged since release 1.0.** The body and the status code of this answer are as release 1.0 gave them. Only headers are added: the request ID and the security headers.

**Stops.** Stop 1 always has `kind: "start"`: it is the fuel bought before leaving, priced at the listed station nearest the start, and its `lat` and `lng` are the start place. Every other stop has `kind: "station"`, and its `lat` and `lng` are the point where the road passes the station's city, so it sits on the route line. The CSV has no coordinates of its own.

**Warnings.** A list of plain sentences. One is added when the first fill-up station is more than 25 miles from the start, naming the station and the distance.

**Numbers.** Everything is a JSON number. Miles have 1 decimal, gallons and money 2, coordinates 5, and prices every digit the CSV has.

**The map.** A GeoJSON FeatureCollection, in this order:

1. The route as a `LineString`. Properties: `kind: "route"`, `distance_miles`.
2. One `Point` per stop. Properties: `kind: "stop"`, `order`, `title` (for example `2. SHEETZ #639, Youngstown OH`), `name`, `mile_marker`, `price_per_gallon`, `gallons`, `cost`, `marker-color`.
3. A `Point` each for the start and the finish. Properties: `kind`, `title`, `marker-color`.

`title` and `marker-color` follow the convention geojson.io reads, so the stops are labelled when the map is pasted there.

### Errors

Every error has the same body, whatever raised it:

```json
{"error": {"code": "unknown_place", "message": "…", "details": {"field": "start", "query": "Chicgo, IL", "suggestions": ["Chicago, IL"]}}}
```

| Status | Code | When | Details |
|---|---|---|---|
| 400 | `invalid_request` | A parameter is missing, empty or malformed, or start and finish are the same place. Also a host that is not allowed, and a request line longer than 8,190 bytes (below) | `fields`: the messages per parameter. `fields` is there but empty for a request Django would not read, such as one with more than 1,000 parameters. `details` itself is empty for a host that is not allowed |
| 400 | `unknown_place` | A place is not in the table | `field`, `query`, `suggestions` (up to 5) |
| 404 | `not_found` | No such address | — |
| 405 | `method_not_allowed` | Anything but GET | — |
| 422 | `outside_coverage` | A place in Alaska, Hawaii, Puerto Rico, Canada or Mexico | `field`, `query` |
| 422 | `route_leaves_usa` | The road runs through Canada or Mexico | `miles_abroad` |
| 422 | `no_route` | The routing service finds no road between the points | — |
| 422 | `no_fuel_plan` | A stretch of more than 500 miles with no station listed | `gap_start_mile`, `gap_miles` |
| 429 | `rate_limited` | Too many requests from one client | `retry_after_seconds` |
| 500 | `internal_error` | Anything unexpected | — |
| 502 | `routing_unavailable` | Both routing servers failed or timed out | `reason`: `timeout` or `error` |
| 503 | `stations_not_loaded` | `load_stations` has not been run, or the database cannot be read | — |

`trips/errors.py` holds the table from code to status and builds this body. It also turns the framework's own errors (validation, rate limit, wrong method, unexpected failure) into the same shape. An unexpected failure is logged in full and answered with `internal_error` and no detail. A catch-all route answers every unknown address with `not_found`. Neither depends on Django's debug setting.

Two answers come from outside the route's view. The first is in the same shape:

- **A host that is not allowed.** A request whose `Host` is not in `DJANGO_ALLOWED_HOSTS` gets 400 `invalid_request`, with empty `details` (D-21). Django's own 400 page is replaced by a handler (`handler400`) that answers in this shape. No 403 handler is set: nothing in the API can answer 403.
- **A request line over 8,190 bytes.** gunicorn answers it itself with an HTML 414 that cannot be changed (`gunicorn.conf.py`). It is not in the API's shape (section 16).

Only GET is specified. OPTIONS is left to the framework's default. HEAD is answered as GET without the body (RFC 9110, section 9.1), so a HEAD for a new trip makes its routing call, and the result is cached. Every other method gets `method_not_allowed`.

`timings_ms.own` is our own work up to the point the answer is handed to the framework. It does not include writing the JSON.

### Other addresses

| Address | Answers | Rate limited |
|---|---|---|
| `GET /api/v1/health/` | 200 with `{"status": "ok", "stations": 6626, "cache": "redis"}` when the stations are loaded; 503 `stations_not_loaded`, in the standard error shape, when they are not (FR-20) | No |
| `GET /api/v1/schema/` | The OpenAPI 3.0.3 document, produced from the code by `drf-spectacular` (FR-19, D-20) | Yes |
| `GET /api/v1/docs/` | The Swagger page: an interactive view of that document | Yes |

The schema and the Swagger page are limited like the route, against the same count. The health address is exempt. An unknown address (404) and a host that is not allowed (400) are answered before any view runs, and are not counted either (section 10).

**The health answer.** `stations` is the number of stations in the in-memory index. Asking for it loads the index if it is not loaded yet, as a route request does, so the Django ORM is still used in only the two places of section 3, and an empty table, or a database that cannot be read, gives `stations_not_loaded`. `cache` describes the worker process that answered:

| `cache` | Meaning |
|---|---|
| `memory` | `REDIS_URL` is not set, so the cache is the process's own memory, as in release 1.0 (D-15) |
| `redis` | `REDIS_URL` is set and this process is using Redis |
| `fallback` | `REDIS_URL` is set, and this process is in its 30-second fallback because Redis could not be reached (section 10, D-16) |

The health check makes one cheap cache read before it answers, so the state it reports is current.

**The OpenAPI document (D-20).** The trial of `drf-spectacular` 0.30.0 on Django 6.1.3 and DRF 3.18.3 set what it needs:

- `drf_spectacular` in the installed apps, a `TEMPLATES` entry with `APP_DIRS`, and `DEFAULT_SCHEMA_CLASS` in the REST framework settings.
- Its routes placed before the include of `trips.urls`, whose last pattern is the catch-all and matches everything.
- The route view is a plain `APIView`, so the tool cannot guess its parameters or its response. They are declared by hand with `extend_schema`, in `trips/schema.py`: the three parameters, the 200 body, and the error answers in the standard error shape. Until they are declared, `spectacular --validate --fail-on-warn` reports one error.
- The route lists 400, 422, 429, 500, 502 and 503, each with every code it can carry. Its 503 is `stations_not_loaded` only: the table is empty, or the database cannot be read. `not_found` is not listed on the route, because the route's address exists. `not_found` and `method_not_allowed` are described in the document's opening text.
- The Swagger page loads its script from a CDN at `@latest` by default. `SWAGGER_UI_DIST` pins it to one version. Its three files carry no integrity hash.

The document is committed as `docs/openapi.yaml`. A test fails if it and the code disagree.

## 12. Technology

| Piece | Choice | Why |
|---|---|---|
| Python | 3.12 | Django 6.1 needs 3.12 or newer |
| Framework | Django 6.1.x | Required. 6.1.3 is the latest on PyPI. |
| API | Django REST Framework 3.18 | The standard for Django APIs. Its release notes add Django 6.1 support. |
| Database | PostgreSQL 17 | The database a Django service runs on in production |
| Database driver and URL | psycopg 3, dj-database-url | One `DATABASE_URL` setting configures the connection |
| HTTP client | httpx | Timeouts, connection reuse, and a built-in fake transport for tests |
| Numbers | numpy, scipy | Vector maths and the KD-tree |
| Cache | Redis, through Django's cache framework, with the `redis` client; the process's own memory when `REDIS_URL` is unset or Redis cannot be reached | Shared by every worker (D-15, D-16) |
| Server | gunicorn, 2 worker processes × 4 threads, set in `gunicorn.conf.py` | Several processes (NFR-19). Each worker holds its own station index; the caches are shared through Redis |
| API description | drf-spectacular | The OpenAPI document and the Swagger page, from the code (D-20) |
| Packaging | uv | One command to install and run |
| Containers | Docker Compose | One command starts PostgreSQL, Redis, the setup and the API |
| Tests and lint | pytest, pytest-django, pytest-cov, Ruff, mypy, pip-audit, pre-commit | |

Left out on purpose: pandas (the `csv` module handles 8,151 rows), django-environ (settings are read with `os.environ`), and any API key.

**Settings from the environment:** the nine variables in the table of section 18 (NFR-20). Every one has a default that makes a fresh clone run. No secret key is written in the code: with no `DJANGO_SECRET_KEY` a random key is made at start-up, and since nothing is signed the workers need not share it. Host checking is on: `DJANGO_ALLOWED_HOSTS` defaults to `localhost,127.0.0.1,[::1]` (D-21). `.env.example` lists them. The database password in the Compose file is a local development default, not a secret.

**Settings in code:** the two default routing server templates (`ROUTING_SERVERS` replaces them), the 5-second deadline, the User-Agent, the default stop cost, the cache timeout, the cache key version `CACHE_KEY_VERSION` (section 10), the rate limit.

**Deployment check:** Django's security middleware is on, and `manage.py check --deploy` passes (NFR-21). Each check that is switched off has its reason written beside it. TLS, HSTS and redirect settings are not set here: they belong to whatever is put in front (D-23).

## 13. Testing

No test reaches beyond the local machine. A test fixture blocks every connection except those to `127.0.0.1`. That covers the local database, the stand-in routing server in its own tests, and, for the Redis tests, the Redis on the same machine.

| Area | What is tested | Needs the database |
|---|---|---|
| Fuel plan | Hand-worked cases: cheaper station ahead, none ahead, finish within range, equal prices, single station, two stations at one mile, impossible gap. Then the two comparisons in section 8. | no |
| Geometry | Known distances, re-spacing, mile markers, the border test on a real road through Ontario and on roads that stay in the USA | no |
| Station search | A straight synthetic road with stations at known offsets, ties and thinning | no |
| Routing client | Both server addresses, each failure that should retry and the one that should not | no |
| Places | The 58 names from the research run, the everyday spellings in D-3, unknown and out-of-coverage names | no |
| Loader and index | A small CSV with duplicates, padding and a Canadian row. One test on the real CSV asserting the counts in section 6. | yes |
| Endpoint | The routing client replaced with a fake. The response shape, the cache behaviour, and every error code. | yes |
| Verifier | An independent checker, written from this document, applied to every successful response. Its rule on `meta` (R15) accepts the two public routing hosts, plus any host its caller names: `scripts/live_check.py --routing-host` names the stand-in's service, `fake-osrm`, in the end-to-end run. Its rule that each station stop lies near a place of its city and state (R17) checks against the places data its caller gives: by default the real places file and the five places added by hand (section 6); the endpoint tests give their own small places file | yes |
| Cache | Against a real Redis, in its database 15 and nothing else, and against a dead address: the shared cache, the fallback with its one warning, the 30-second wait before Redis is tried again, the line logged on return, and, timed, that a dead Redis never stalls a request | no |
| Health and schema | The health answer in each state. The committed OpenAPI document matches the code, and `spectacular --validate --fail-on-warn` passes | yes |
| Settings | Host checking is on: the release 1.0 test that forbade `DJANGO_ALLOWED_HOSTS` is reversed on purpose | no |

The suite itself is pinned to the in-memory cache, because the fixture that clears the cache between tests would empty a real Redis. Only the Redis tests use Redis, and only its database 15.

### Beyond the suite

| Check | What it proves | Routing |
|---|---|---|
| End-to-end run | The whole stack: the Postman collection (Newman) run against the API. The stand-in's request count matches the routing calls expected: eight, each matched to a recording | stand-in |

**The stand-in routing server.** `scripts/fake_osrm.py` answers like the routing server, with the saved real roads in `tests/fixtures/roads/`. It runs from the test image (section 18). A second Compose file, `docker-compose.e2e.yml`, gives the API the stand-in as its only routing server, so a run sends nothing to a public one (NFR-26).

**CI** runs on every push and pull request (NFR-17): lint, format, type check, tests with coverage, `manage.py check --deploy`, the migration check, a dependency audit, the image build and the end-to-end run. Dependabot proposes dependency updates.

- **Type check:** the Django-free modules of section 3 (NFR-27).
- **Coverage floor:** the coverage measured when the gate is set up in Phase 10, rounded down to a whole per cent and recorded in `pyproject.toml`. Coverage may not fall below it.
- **Dependency audit:** `pip-audit` for the Python packages.
- **Before a commit:** pre-commit runs Ruff's checks, Ruff's formatter and the file hygiene hooks (NFR-27).

## 14. Speed

*Measured* on the finished API for the New York to Los Angeles road, the largest tested. The API was run from source with `manage.py runserver` on the development machine, against the real routing server, on 18 Nov 2026. The steps were timed during build (Phase 3), and the whole request by the live run (Phases 4 and 5).

| Step | Time |
|---|---|
| Routing call | 2,646 ms on the first live request (network, outside our control) |
| Re-space the road | 1.9 ms |
| Station search and thinning, 6,626 stations | 2.3 ms |
| Border check | 1.8 ms on Boston to Seattle, the longest road tested |
| Fuel plan, 100 stations | 5 ms |
| Lowest possible bill, 400 stations | under 0.3 ms |
| Fuel plan on every station (the rare fallback, 400 stations) | 230 to 340 ms |

| Whole request | Our own work | Round trip |
|---|---|---|
| A new trip | 19.5 ms, against a limit of 100 ms (NFR-1) | |
| The same trip again, answer cached | 1.1 ms | 23.6 ms, against a limit of 50 ms (NFR-11) |
| The same trip, another stop cost (road cached) | 11.0 ms | 31.7 ms |

"Our own work" is `meta.timings_ms.own`: everything except the routing call and the writing of the JSON. Each figure is one run of the live check, not an average. The first request after the server starts is as fast as the rest, because `warm_up()` (section 6) loads the places, borders and stations as the server starts.

**The border check must use its own, coarser sampling.** It tests one road point every 2 miles, and only points north of 41.6° or south of 32.8°, the only latitudes where Canada or Mexico can be. Run on every half-mile point it took 115 to 149 ms by itself (*measured*), which would break NFR-1.

## 15. Decisions and what was rejected

| Decision | Rejected alternative | Reason |
|---|---|---|
| Keyless routing server | A service with an API key | A reviewer can clone and run with no sign-up |
| GET with query parameters | POST with a JSON body | Nothing is created or changed |
| PostgreSQL | SQLite | It is what the service would run on in production, and one Compose command starts it |
| Stations in memory at request time | A database query per request | 6,626 rows fit in memory, and the search takes 4 ms |
| Database holds only stations | Saving every plan | Nothing reads a saved plan now that the map is GeoJSON (D-2) |
| City-centre positions | An outside dataset of truck stops | The CSV is the only source of stations (requirements, section 7) |
| Stop cost in the plan | Pure lowest fuel bill | 17 stops with sub-gallon purchases is not a usable plan |
| Dynamic programming | The simple greedy rule | Greedy is exact only when stops are free. It is used for the comparison figure, where stops are free. |
| Half-mile road points in the response | The service's full 34,931 points | Same picture at trip scale, one seventh of the size |
| Test against Canada and Mexico outlines | Test against the US outline | The US outline wrongly flagged Manhattan, Long Island and Key West |
| Two caches, road and answer | One cache of whole answers | Changing only the stop cost should not cost a routing call |
| One error code for routing failure | Separate codes for failure and timeout | The caller does the same thing in both cases; the details say which |
| One settings file | Separate dev, test and production settings | A handful of environment variables do not need four files |
| Fall back to each process's memory when Redis is down | Failing the request; treating every Redis error as a cache miss | A cache must not take the service down; treating errors as misses also switches the rate limit off (D-16) |
| Both of two identical new requests are routed | A lock that makes the second wait | Waiting threads would tie up the server to save one free routing call (D-22) |
| One health endpoint | Separate liveness and readiness endpoints | Nothing acts on the difference |
| Ready to run behind a TLS terminator | TLS, HSTS, a secrets manager | There is no deployment (D-23) |
| Plain log lines with a time, a level and a request ID | JSON logs, metrics, tracing, error tracking | There is no operator to read them |
| Type check on the Django-free modules | Strict typing of the Django layer | The stubs do not yet declare support for Django 6.1 |
| **Parked.** MapLibre GL JS with its globe projection | CesiumJS; Mapbox, MapTiler, Google 3D tiles and CARTO; deck.gl's own globe; a self-hosted Protomaps extract | CesiumJS is four times the size and its default imagery needs an account; the next four each need a key; deck.gl's globe cannot zoom to street level; the Protomaps extract's size is unverified and more than a fallback needs (D-18) |
| **Parked.** A viewer of one trip, named by its address | A trip-planning form | The owner chose a viewer (D-19) |

## 16. Known limits

- **Station positions are approximate.** They are city centres, a median 2.8 miles from the real station. Mile markers carry that error, and there is no safety reserve on the 500-mile range.
- **Some roads have no fuel listed.** The CSV has no station on Interstate 5 through California, so trips such as Los Angeles to Seattle have no plan. The API says so; it does not invent a stop.
- **Car routing, not truck routing.** The free server has no truck profile, so low bridges and truck bans are ignored.
- **Places are cities.** Street addresses, ZIP codes and coordinates are not understood.
- **The routing servers are free demos** with no uptime promise. The second server covers a failure of the first, not of both.
- **The routing deadline is not strict.** An attempt can run to about twice its 5 seconds if the server is slow both to answer and to send (section 9).
- **Two identical new requests arriving together both call the routing server.** Nothing makes the second wait for the first, so "none on repeat" in NFR-2 holds for requests that come one after another. A lock was rejected (D-22).
- **The rare fallback is slow.** When the shortened station list has no plan, the plan is chosen from every station, which takes 150 to 300 ms coast to coast (*measured*) and so exceeds NFR-1 for that request.
- **While Redis is down, the cache and the rate limit are per process** (D-16). A repeat may land on the other worker and be planned again, and each worker counts the limit on its own.
- **Border outlines are coarse.** A road that follows the border can register up to 10 miles as abroad (*measured*), which is why the limit is 25.
- **A request line over 8,190 bytes is answered by gunicorn, in HTML.** It is not in the API's error shape, and gunicorn gives no way to change that. A shorter long address reaches the API and gets its JSON 400.
- **Docker is needed** to run PostgreSQL.
- **Not deployed.** There is no TLS, HSTS or redirect to HTTPS, and no reverse proxy; they belong to whatever is put in front (D-23).
- **Parked, with the viewer: its map comes from other people's servers.** The visitor's browser loads tiles from OpenFreeMap and imagery from NASA. If they cannot be reached the viewer draws on its built-in outlines (FR-25). The Swagger page loads its script from a CDN.
- **`drf-spectacular` does not declare support for Django 6.1 or DRF 3.18.** It passed a trial on both (D-20). If a later Django patch breaks it, a hand-written document replaces it.
- **Only the Django-free modules are type checked.** The type stubs do not yet declare support for Django 6.1.

## 17. Build order

1. Project, PostgreSQL, settings, every module's interface
2. Places, `FuelStation`, `load_stations`, the in-memory index; geometry and station search; the fuel plan; the routing client. Each with its tests.
3. `plan_trip`, the answer builder, the view, errors and caches, with endpoint tests
4. Independent verification, live tests, review
5. Dockerfile and one-command start
6. README and Postman collection

## 18. Running it

From a fresh clone with no `.env`, one command, `docker compose up --build`, starts the whole stack (NFR-9).

### Services

| Service | What it is | Published port | Role |
|---|---|---|---|
| `db` | `postgres:17` | 5432, on `127.0.0.1` only | The seed data |
| `redis` | Redis, with no persistence, memory capped at 256 MB, least recently used key evicted when full | 6379, on `127.0.0.1` only | The two caches and the rate-limit counters, shared by every worker (section 10) |
| `setup` | The API image, run once | none | `migrate`, then `load_stations`, then exits |
| `api` | gunicorn, 2 workers × 4 threads | `127.0.0.1:${API_PORT:-8000}` | `/api/v1/...`; starts after `setup` succeeds |
| `test` | The test image | none | The suite in a container, as in release 1.0; started only with `--profile test` |

The API, the database and Redis are published on `127.0.0.1` only (NFR-19), the last two for running from source and for the tests.

Three Compose variables move the published ports: `API_PORT` (default 8000) the API's, `POSTGRES_PORT` (default 5432) the database's, and `REDIS_PORT` (default 6379) Redis's. They are read by Compose, not by the API.

The address release 1.0 used, `http://127.0.0.1:8000/api/v1/route/`, works (NFR-19).

For the end-to-end run, a second Compose file, `docker-compose.e2e.yml`, gives the API the stand-in routing server as its only routing server (section 13).

### Start order

The start order follows health checks (NFR-22).

| Service | Starts when | Its health check |
|---|---|---|
| `db` | At once | `pg_isready -h 127.0.0.1`: over the network, not the local socket, so it passes only once PostgreSQL accepts network connections |
| `redis` | At once | A ping |
| `setup` | `db` is healthy | None: it runs `migrate`, then `load_stations`, and exits |
| `api` | `setup` has exited successfully, and `redis` has started | A request to `/api/v1/health/`, with a 5-second timeout and 6 retries |

- `api` waits for Redis to have started, not to be healthy: the API must be able to start without it (D-16).
- Migrations and the station load run once, in `setup`, before the API starts, not in every worker (NFR-22).
- Each API worker loads the places, the borders and the stations into memory as it starts (section 6).

### Configuration

All of it comes from the environment (NFR-20). Every default makes a fresh clone run.

| Variable | Default | What it does |
|---|---|---|
| `DJANGO_SECRET_KEY` | None: a random key is made at start-up | Django's secret key. Nothing is signed, so the workers need not share it (D-21) |
| `DJANGO_DEBUG` | Off | Django's debug mode |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]` | The host names the API answers to. Any other gets 400 `invalid_request` (D-21). `127.0.0.1` is always allowed, whatever the variable says: the container's health check asks under that name |
| `DJANGO_NUM_PROXIES` | `0`; the Compose file also sets `0` | How many proxies in front of the API to trust when finding a client's address for the rate limit (D-17) |
| `DATABASE_URL` | `postgresql://milemarker:milemarker@127.0.0.1:5432/milemarker`; the Compose file points it at `db`. The address is `127.0.0.1`, not `localhost`: the database is published on `127.0.0.1` only, and a machine that tries IPv6 first for `localhost` waits seconds on every connection | The PostgreSQL connection (NFR-10). Unless the URL sets one, the connection gives up after 5 seconds (`connect_timeout`) |
| `REDIS_URL` | Unset: each process uses its own memory | The Redis that holds the caches and the rate-limit counters (D-15). The Compose file points it at `redis` |
| `ROUTING_SERVERS` | The two public servers of section 9 | The routing servers: URL templates separated by commas, each containing `{coords}`, tried in order. The end-to-end run points it at the stand-in |
| `WEB_CONCURRENCY` | 2 | The number of gunicorn worker processes (NFR-19). A whole number of 1 or more |
| `LOG_LEVEL` | `INFO` | The lowest level of message written to the log: `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL` |

**`ROUTING_SERVERS` is checked at start-up.** Each entry is trimmed, and empty entries are dropped. At most two entries are allowed, because a request never makes more than two routing calls (NFR-2); a third is refused like any other bad value. A value that is empty or only spaces counts as not set, and the two public servers are used: Compose passes the variable through, so on a fresh clone it arrives empty. If the value is anything else and no entry is left, or an entry has no `{coords}`, the API refuses to start: Django raises `ImproperlyConfigured`, naming the variable and the entry.

### Stopping

A stop lets a request in flight finish, for up to 30 seconds (NFR-22). gunicorn stops taking new requests and gives the running ones that long. Compose must wait at least as long before it kills the container; its own default is 10 seconds. A request is therefore not cut off in the middle of a routing call, which takes about 20 seconds at worst (section 9).

### Logs

Each line has a time, a level and the request's ID (NFR-24). The lines are plain text, not JSON (section 15).

**One line per trip.** Every 200 from the route, cache hits included, logs one line at INFO from the logger `trips`. Its message has this form:

```text
trip start="New York, NY" finish="Los Angeles, CA" stop_cost=10 miles=2800.6 stops=7 total=867.27 routing_calls=1 cache_hit=false own_ms=19.5
```

An error answer logs one line at WARNING with its code, and no trip figures. The one exception is an unexpected failure (`internal_error`): it is logged once, in full, at ERROR, and has no second line.

Each process also logs one warning when it falls back from Redis, and one line when it returns (section 10).

**The request ID** is made by the API. A client's `X-Request-ID` is kept only if it is 1 to 64 characters of letters, digits, `.`, `_` and `-`, because the ID is written into the log; with none, or any other, the API makes one. It is on every log line about the request, and is returned to the client in the response header `X-Request-ID`.

### The front door

**Not part of this submission.** This section specifies work that is parked on the branch `viewer`. It is kept as that branch's specification.

nginx, in the `web` service, is the only way in.

- **What it serves.** The viewer at `/` and its built files under `/assets/`. A missing file under `/assets/` gets 404 `not_found` in the API's error shape, written by nginx. Every other address is passed to `api`: the route, the health check, the schema and the Swagger page, and any unknown address, which still gets the API's JSON 404 `not_found`, as in release 1.0.
- **The `Host` header.** nginx passes on the client's own `Host`, so host checking (D-21) sees the name the client used. A name not in `DJANGO_ALLOWED_HOSTS` gets 400 `invalid_request`.
- **The request ID.** nginx makes one for each request, replacing any the client sent, and passes it to the API as `X-Request-ID` (see "Logs").
- **The client's address.** nginx overwrites `X-Forwarded-For` with the address it saw; it does not add to what the client sent. The API trusts exactly one proxy (`DJANGO_NUM_PROXIES=1`), so the rate limit counts the address nginx saw (D-17, NFR-16).
- **Why the API has no published port.** A client that could reach gunicorn directly could send its own `X-Forwarded-For`, and the API, trusting one proxy, would count that forged address. With no published port, every request passes through nginx, which overwrites the header. This is what keeps the forged-header bypass, found while release 1.0 was built, closed.
- **One origin.** The viewer and the API share one origin, so no cross-origin rules are needed (D-17).
- **Compression.** JSON responses and the viewer's files are compressed in transit (NFR-23). The map in a coast-to-coast answer is about 133 KB of JSON.
- **Waiting for the API.** nginx gives the API 30 seconds to answer. Its slowest proper answer takes about 20 (section 9).
- **When the API is down or too slow.** If the API cannot be reached, or does not answer within the 30 seconds, nginx answers 503 in the API's own error shape, with the code `api_unavailable`, never an HTML error page (D-24): `{"error": {"code": "api_unavailable", "message": "…", "details": {}}}`.
- **Requests nginx refuses.** A request nginx refuses itself, as malformed or too long, gets 400 `invalid_request` in the same shape.
- **The API's own errors** pass through untouched.
- **Security headers.** On every answer: `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, and a ban on framing. `Referrer-Policy` has that one value everywhere. Each answer gets its headers from one place, so none is sent twice:

  | Answer | Security headers set by |
  |---|---|
  | The API's answers, passed through nginx | Django (its security middleware, section 12). nginx adds none to them |
  | The viewer's page and files | nginx |
  | The answers nginx writes itself: `api_unavailable`, a request it refuses, a missing file under `/assets/` | nginx |

  On the viewer's page only, there is also a content security policy. It allows the page's own files, the two map servers (`tiles.openfreemap.org` and `gibs.earthdata.nasa.gov`, section 19), and the workers and inline styles the map library needs. Its exact text is written when the viewer is built, in Phase 12, and recorded then. The Swagger page has no content security policy, because it loads its script from a CDN.
- **TLS.** None here. The stack is ready to run behind a TLS terminator; TLS, HSTS and redirects belong to it (D-23).

### Images

The API image is built in stages. The running image holds only what runs, and runs as a user that cannot write to the code (NFR-25). 
The stand-in routing server runs from the test image, which holds the tests and the recorded roads. The running image holds neither.

### Commands

The everyday commands are nine `make` targets (NFR-30). Each recipe line is one plain command, so the targets work on Linux, on macOS, and on Windows under Git Bash or PowerShell. The README shows the plain command beside each, for anyone without make.

| Target | Does | Plain command |
|---|---|---|
| `up` | The Compose stack, built, in the background | `docker compose up --build -d` |
| `down` | Stops it | `docker compose -f docker-compose.yml -f docker-compose.e2e.yml down --remove-orphans` |
| `logs` | Follows the API's log | `docker compose logs -f api` |
| `test` | The tests, in a container | `docker compose --profile test run --rm test` |
| `lint` | Ruff's checks, its format check and the type check | `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` |
| `dev` | The database and Redis containers, then the API from source with auto-reload on port 8001 | `docker compose up -d db redis`, then `uv run python manage.py runserver 127.0.0.1:8001` |
| `offline` | The stack on recorded roads, with no call to a public routing server; empties the stand-in's Redis database | the Compose command with both files, then `redis-cli -n 1 FLUSHDB` in the `redis` service |
| `postman` | The Postman collection, against the running API | `npx newman run docs/postman/milemarker.postman_collection.json --env-var base_url=http://127.0.0.1:8000` |
| `clean` | Stops everything and deletes the volumes | the `down` command with `-v` |

`make help` lists them (NFR-30).

`make dev` starts the database and Redis. The API it runs from source uses the in-memory cache unless `REDIS_URL` is set. Redis is published on `127.0.0.1:${REDIS_PORT:-6379}` for that case and for the Redis tests.

## 19. The viewer

**Not part of this submission.** This section specifies work that is parked on the branch `viewer`. It is kept as that branch's specification.

A separate web application, in `web/`, that draws one trip on a map (FR-18). It is opened as `/?start=…&finish=…&stop_cost=…`, the same parameters as the API, for example `/?start=New York, NY&finish=Los Angeles, CA&stop_cost=10`. It reads them, asks the API once (FR-21), and draws the GeoJSON the API returns (D-2). The API's response does not change for it and carries no link to it.

It has no form: it is a viewer of one trip, named by its address (D-19). Opened with no trip, it shows the slowly turning globe and three example trips to choose from: New York, NY to Los Angeles, CA; Seattle, WA to Miami, FL; and Dallas, TX to Houston, TX.

"No trip" means neither `start` nor `finish` is in the address. With only one of them, the viewer asks the API like any other address, and shows the `invalid_request` the API answers with.

### Stack

| Part | Choice | Why |
|---|---|---|
| App | React 19, TypeScript in strict mode, Vite. No router, no state library, no UI kit | One screen |
| Map | MapLibre GL JS 6, globe projection (D-18) | The only keyless option that goes from a globe in space down to readable street maps in one continuous zoom, and can reveal a 5,600-point route without re-sending it each frame. About 455 KB compressed |
| Animation | Motion | One clock drives the camera, the route, the counters and the scrubber together |

It is built into the `web` image and served by nginx (section 18). `make web-dev` runs it from source, passing `/api` to the API.

### Its parts

| Part | Does |
|---|---|
| API client | The only code that calls the API: one `GET /api/v1/route/` with the address's parameters, on the same origin. Hands back the answer, or the error's code and details |
| Timeline | Pure calculations, with no React, no map library and no network: where the route's head is at each moment, when each stop appears, and what each counter shows. Unit tested on their own |
| Map module | The one module that talks to MapLibre: the globe, the camera, the route line and its colour boundary, the markers, the remote map, and the built-in outlines beneath it |
| Panel components | React components that show the answer: the totals, the warning, the assumptions, the stop cards, the error states, Skip, Replay and the scrubber. They never call MapLibre themselves; choosing a stop's card asks the map module to fly there |

**The panel** (FR-23) shows the distance, the number of stops, the total fuel cost, the lowest possible bill, any warning, the assumptions, and one card per stop with its name, city and state, price, gallons, cost and mile. Every figure shown is the API's, unchanged; the counters count up to those figures. Only the format is the viewer's:

| Figure | Shown as |
|---|---|
| Miles | A thousands separator and one decimal: `2,800.6 mi` |
| Money | `$867.27` |
| Gallons | Two decimals |
| A price per gallon | Exactly as the API gives it: `$3.239 / gal` |

**Errors** (FR-24). Each API error code has its own message in the panel: a short heading for the code and, under it, the API's own `message`. An unknown place shows the API's suggestions as links that reopen the viewer with that place corrected. A rate-limited answer says when to retry, from `retry_after_seconds`. An API that cannot be reached, whether nginx answers `api_unavailable` or nothing answers at all, is said plainly.

The error headings and the other fixed sentences (the loading state, the first card's sentence, the no-WebGL2 sentence) are written when the viewer is built, in Phase 12, and recorded in the test cases then. The tests find elements by their role and test ID, and compare figures, not prose.

Every control, including the stop cards, Skip, Replay and the scrubber, is reachable by keyboard (NFR-28).

### The animation

About 16 seconds, with Skip and Replay (FR-22).

| Beat | Time | What happens |
|---|---|---|
| 1 | 0–3 s | The night-side globe turns slowly under an atmosphere glow. The trip's title fades in. |
| 2 | 3–8 s | The camera flies from space down to the route, tilting as it arrives. The night lights give way to the road map. The summary cards slide in one after another. |
| 3 | 8–15 s | The route draws itself along the road with a soft glow and a bright moving head. The distance counter runs with it. |
| 4 | during 3 | As the head reaches each fuel stop, its marker pops in, its card appears, and the fuel-cost counter adds that stop's cost. |
| 5 | 15–16.5 s | The camera settles. The finish marker pulses. A scrubber appears: drag it to replay any moment. |
| after | | Choosing a stop's card flies the camera to it. |

- **Stop 1** (the fill-up at the start) appears at 8 s, as the line starts: its marker, its card and its cost.
- **Skip** jumps to the end. **Replay** starts again.
- **Cancelling the intro.** During the intro, a press on the map, a wheel turn, a touch or the Escape key cancels it and hands over control. The trip is then shown finished, as after Skip, and the camera stays where the visitor's own gesture leaves it.

### Revealing the route

The whole route line is given to the map once. It is revealed by moving a colour boundary along it: behind the boundary the line is drawn, ahead of it the line is not shown. Each frame moves the boundary, one cheap update, instead of rebuilding the line, so the work per frame does not grow with the route's length (NFR-29). New York to Los Angeles has about 5,600 points.

**The head moves at a constant speed along the drawn line.** Its progress, the fraction of the drawn length behind it, rises linearly from 0 at 8 s to 1 at 15 s.

**Two running totals per point.** For each point of the route line the viewer keeps:

- the ground distance from the start, by the great-circle formula, scaled so the last point's total equals the API's `distance_miles`;
- the drawn length from the start in Web Mercator, which is what the map library's line progress measures.

Between two points, both are interpolated linearly. The drawn length places the boundary and times the stops; the ground distance gives the road miles at the head.

**Stop timing uses position along the drawn line, not the mile marker.** The boundary's place is a fraction of the line's length as drawn, measured in Web Mercator. A mile marker is a fraction of the length on the ground. The projection stretches distance by different amounts at different latitudes, so the two fractions differ, and a stop timed by its mile marker would pop in before or after the head reaches it. Each stop is therefore timed by its own position along the drawn line. A stop's `lat` and `lng` lie on the route line (section 11), so that position can be found.

**The distance counter** shows the road miles at the head of the line, not the fraction of the line drawn. It therefore reads a stop's mile marker as the head reaches that stop.

### Fallbacks

| Situation | What the viewer does |
|---|---|
| The visitor's system asks for reduced motion | Opens on the finished state, with no camera animation (FR-25). On the page with no trip, the globe does not turn |
| No WebGL2 | A static drawing of the route, the same panel, and a sentence saying why |
| The map servers cannot be reached | Draws on built-in outlines, bundled in the app: land and country lines from Natural Earth, US state lines from the US Census Bureau. The globe and the route still draw |
| Slow graphics | Pixel density capped at 2, terrain off, three small updates per frame (NFR-29) |

**How the outlines take over.** The built-in outlines are always the bottom layer, under the remote map. The remote map's description (its style) is given 4 seconds to arrive; if it has not, the viewer goes on with the outlines alone, and a description that arrives later is ignored for that page view. A tile that fails later simply does not draw, and the outlines show through.

The browser tests use the built-in outlines, so they never depend on someone else's server.

### Map sources and credit

| Source | Server | Used for | Terms | Credit on screen |
|---|---|---|---|---|
| NASA night-lights imagery (Black Marble), from NASA GIBS | `gibs.earthdata.nasa.gov` | The globe from space, with MapLibre's atmosphere, on a black page. It fades out as the camera comes down | Public data; no key | NASA GIBS |
| OpenFreeMap's dark vector style | `tiles.openfreemap.org` | Roads and place names once the camera is low | Free; no key, no account, no view limits | OpenFreeMap, OpenMapTiles, OpenStreetMap |
| Built-in outlines: land and country lines from Natural Earth (the `world-atlas` package), US state lines from the US Census Bureau's cartographic boundaries (the `us-atlas` package) | None: bundled in the app | The bottom layer, the fallback, and the browser tests | Public domain; no credit required | Natural Earth, US Census Bureau |

The credits are on screen at all times (FR-26), and they name the sources in use. Without WebGL2 the static drawing uses only the API's data and the built-in outlines, so it credits Natural Earth. The map's credit control stays expanded and shows what each source asks for. The exact wording and links are copied from each provider's own page when the viewer is built, in Phase 12, and recorded together with those pages' addresses.
