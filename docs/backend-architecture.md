# Mile Marker API: Backend Architecture

How the API is built, and why each part is the way it is.
`requirements.md` says what is required. IDs such as FR-6 and D-9 refer to it.

Figures marked *measured* come from research runs on 18 Nov 2026 against the supplied CSV and real routes. They were produced by throwaway scripts and will be replaced with figures from the finished API.

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
 │   5. get the road: from the cache, or from the routing service (the ONE network call)
 │   6. lay mile markers along the road, check it stays in the USA
 │   7. find the stations within 5 miles of the road             (memory)
 │   8. choose the stops and how much to buy at each             (pure arithmetic)
 │   9. build the answer, store it in the cache
 ▼
API layer          turn the answer into JSON
```

Everything that can be known before the routing call is checked before it. The database is **not** on this path. It is read once per process, when the stations are loaded into memory (section 6).

## 3. Layers and what each may do

| Layer | Code | Does | Never does |
|---|---|---|---|
| API | `trips/views.py`, `serializers.py`, `urls.py`, `errors.py` | Reads the request, checks its shape, calls one business function, returns JSON, turns errors into status codes | Maths, database queries, network calls |
| Business | `trips/services/planner.py`, `answer.py`, `corridor.py`, `fuel.py`, `geo.py` | All the rules: mile markers, station search, fuel plan, the shape of the answer | Anything to do with HTTP requests or responses |
| Integration | `trips/services/routing.py` | Talks to the routing service. The only module that makes a network call | Any business rule |
| Data | `stations/models.py`, `places.py`, `index.py`, `types.py`, `sphere.py`, `load_stations` command | Stores the stations, loads them into memory, resolves place names | Anything about a particular trip |

Rules that follow from this:

- `fuel.py`, `geo.py`, `corridor.py`, `answer.py`, `stations/types.py` and `stations/sphere.py` import nothing from Django. They are plain functions and data classes, so they can be tested with no database and no server.
- The Django ORM is used in exactly two places: the loader writes the stations, and `index.py` reads them once.
- Business errors are plain Python exceptions carrying a code, a message and details. They know nothing about HTTP. `trips/errors.py` is the one place that maps a code to a status.
- Longitude is called `lng` in every name. Only GeoJSON coordinate pairs are written `[lng, lat]`.

In Django terms the "controller" is the **view**. Patterns used, by their usual names: thin views, a service layer, a gateway around the external API, and an in-memory read model.

## 4. Folder layout

```text
milemarker-api/
├── manage.py, pyproject.toml, uv.lock, .env.example, README.md
├── Dockerfile, docker-compose.yml
├── config/                    settings.py, urls.py, wsgi.py
├── stations/                  the data side
│   ├── exceptions.py          the base error, and the place and station errors
│   ├── sphere.py              distance maths on a sphere
│   ├── types.py               StationInfo, StationIndex
│   ├── models.py              FuelStation
│   ├── places.py              place name → coordinates, from the offline table
│   ├── index.py               all stations as arrays in memory, loaded once
│   └── management/commands/load_stations.py
├── trips/                     the request side
│   ├── exceptions.py          the trip errors
│   ├── urls.py, views.py, serializers.py, errors.py
│   └── services/
│       ├── planner.py         plan_trip(): runs the steps in section 2
│       ├── routing.py         the routing service client
│       ├── geo.py             mile markers, border test
│       ├── corridor.py        stations along the road
│       ├── fuel.py            the fuel plan
│       └── answer.py          builds the response body
├── data/                      fuel CSV, us_cities.csv, borders.json, README.md
├── docs/                      requirements, architecture, PRD, use cases, test cases, Postman collection
├── scripts/                   live_check.py
└── tests/
```

## 5. The request path, step by step

| # | Step | Where | Notes |
|---|---|---|---|
| 1 | Validate input | `serializers.py` | `start` and `finish` are required text. `stop_cost` is an optional decimal with at most 2 decimal places, 0 to 100 inclusive, default 10. Unknown parameters are ignored. |
| 2 | Resolve places | `stations/places.py` | Offline lookup (section 6). Start is resolved first, so if both are bad the error names `start`. |
| 3 | Same place | `planner.py` | If both resolve to the same coordinates (to 4 decimals), the request is invalid. The error is reported against `finish`. |
| 4 | Answer cache | `planner.py` | A hit returns at once (section 10). |
| 5 | Stations | `stations/index.py` | Load on first use. An empty table is an error, raised before any routing call. Find the station nearest the start place. Several stations often share the nearest position; the cheapest of them is used, then the lowest station ID. |
| 6 | Get the road | `routing.py`, `geo.py` | From the road cache, or one routing call (section 9). Then re-space it to one point every half mile, each with its mile marker. |
| 7 | Border check | `geo.py` | Reject if more than 25 miles in a row lie inside Canada or Mexico (D-4). |
| 8 | Station search | `corridor.py` | Stations within 5 miles of the road, each with a mile marker (section 7). The start station is left out. |
| 9 | Fuel plan | `fuel.py` | Chosen stops and gallons (section 8), plus the lowest possible bill for comparison. |
| 10 | Build the answer | `answer.py` | Summary, stops, warnings, GeoJSON map. Stored in the cache. `meta` is added last. |

**Why re-space the road.** The routing service returns points bunched in curves and sparse on straights: 34,931 points for New York to Los Angeles (*measured*). One point every half mile gives 5,594 points. That makes "nearest point on the road" accurate to a quarter mile, gives every point a mile marker, and is also the line returned in the response (127 KB of JSON, down from 861 KB).

**One length, not two.** The routing service's distance, rounded to 0.1 mile, is the trip length `L`. The road is re-spaced on our own distance sums, the markers are then scaled so the last one is `L`, and the last marker is set to `L` exactly. Our own sum differs from the service's figure by at most 0.19% (*measured* on six routes). A road shorter than half a mile is treated as the same place: the request is answered as invalid, after the one routing call that revealed it.

## 6. The offline path: seed data

`python manage.py load_stations` runs once after `migrate`. It is safe to run again: it replaces the table inside one transaction. `--csv` and `--cities` override the default paths under `data/`.

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
- **Alaska, Hawaii, Puerto Rico, a Canadian province, or a final part that is `Canada` or `Mexico`:** outside coverage.
- **Anything else:** unknown place, with up to five suggestions as `City, ST`. With a known state they are the closest names in that state. With no state, or a state that is not recognised, they are that city name in the states that have it (`Chicago` → `Chicago, IL`).

**Positions:**

- A place listed under several counties uses the average of its rows.
- The exception is 22 places whose rows are more than 10 miles apart (*measured*; Orlando's are 48 miles apart). For those a short table in `places.py` names the county whose row is used.
- The five hand-added places live in `places.py` too, so they work as a start or finish as well as a station city.

### Loading into memory

`index.py` reads every `FuelStation` once per process, ordered by station ID, the first time a request needs it. It keeps numpy arrays of latitude, longitude and price, the same points on a unit sphere, and each station's details including its exact price.

- It is not loaded at Django start-up, because start-up also runs for `migrate`, when the table may not exist yet.
- An empty table is never remembered. If the server starts before the stations are loaded, requests get a clear error until `load_stations` has run, and then work without a restart.
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

*Measured* on New York to Los Angeles, 2,801 miles, by the research prototype. At $10 the plan costs 1.3% more fuel than the absolute minimum and makes 10 fewer stops. For comparison, a driver who simply runs the tank down and refuels at whatever station is there pays $972.78. The finished API scales its mile markers slightly differently, so its figures will be close to these, not identical.

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

The plan is computed on the thinned list. If the thinned list has no plan but the full list does, it is computed on the full list. That is slow (about half a second coast to coast, *measured*) and rare, and it is the price of never reporting "no plan" wrongly.

**When the stop cost is zero** the thinned list is not used at all. The plan is the greedy result described next, on every station, so the plan's bill and the lowest possible bill are the same figure (FR-16).

### The lowest possible bill

For comparison (FR-15) the response also carries the lowest fuel bill possible if stops were free. With free stops the answer is the simple greedy rule: buy just enough to reach the next cheaper station, or fill up if there is none within range. It is run on every station along the road, not the thinned list, and takes under 1 ms (*measured*). Purchases smaller than 0.005 gallons are not counted as stops. Its bill is rounded exactly as the plan's is, stop by stop.

The research figure of $854.65 above came from the thinned list. On every station the finished API may report a slightly lower one.

### Why it can be trusted

Both checks are permanent tests (NFR-6):

- **Stop cost zero:** the plan's cost is compared with a linear-programming solver on random trips. In research: 278 trips, largest difference $0.000000.
- **With a stop cost:** the plan is compared with trying every possible subset of stations on random small trips, each subset priced by the same linear-programming solver, so the check shares no code with the routine under test. In research: 161 trips, largest difference $0.000000.

### Money and rounding

Every figure can be reproduced from the response with a calculator (D-14).

1. The trip length `L` is the routing service's distance rounded to 0.1 mile. Total gallons are `L ÷ 10`, which therefore has at most 2 decimals.
2. Each stop's gallons are rounded to 2 decimals. Any difference between their sum and the total, which can only be a few hundredths, is added to the largest purchase.
3. A stop's price is the CSV's own figure with nothing rounded away (for example 3.00733333).
4. A stop's cost is its gallons × its price, rounded half-up to cents. This is done in decimal arithmetic, not floating point.
5. The total is the sum of the stop costs.

Two small rules keep the figures sensible:

- A purchase that rounds to 0.00 gallons is not shown as a stop. Its fuel is not lost, because step 2 has already moved the difference to the largest purchase. The fill-up at the start is always shown.
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
- **When the second server is tried:** after a timeout, a connection error, a 5xx or 429 status, or an answer that cannot be read as a route. Each attempt has a total deadline of 5 seconds, so the worst case is two calls (NFR-2) and about 10 seconds (NFR-12).
- **When it is not:** if the server answers that no road exists between the points, that is the answer. The second server would say the same.
- **If both fail:** one error, `routing_unavailable`. Its reason is `timeout` only when every attempt timed out, and `error` otherwise.
- **One shared HTTP client** (`httpx`) keeps the connection open between requests, so later calls skip the connection set-up.
- **A User-Agent naming the app** is sent, because the second server's rules ask applications to identify themselves. It is a setting.
- **Usage rules:** both servers ask for no more than one request a second and promise no uptime. The caches and the request rate limit (NFR-16) keep us inside that.

**Rejected:**

| Option | Why not |
|---|---|
| openrouteservice | Needs an account and API key, so a reviewer could not run the project straight from a clone. Its address is being changed this month, and it has announced maintenance for 20 Nov, the deadline day. It does offer a truck profile and border avoidance, which is why it is the first thing to add later. |
| Public Valhalla server | Refuses any route over 1,500 km. New York to Los Angeles is about 4,500 km. |

## 10. Caching

Two caches, both in Django's cache framework with the in-memory backend, both for 24 hours. Prices come from a fixed file and roads change slowly.

| Cache | Key | Holds | Effect |
|---|---|---|---|
| Road | Start and finish coordinates, 4 decimals | The re-spaced road, its length, and the server that supplied it | The same trip with a different stop cost makes no routing call |
| Answer | The road key plus the stop cost to 2 decimals | The response body without `meta` | A repeated request skips all the arithmetic too (NFR-11) |

- `meta` is rebuilt for every response. `cache_hit` says whether the answer came from the answer cache. When only the road was cached, `cache_hit` is false and `routing_calls` is 0. `timings_ms.routing` is 0 whenever no routing call was made.
- Place labels come from the current request's lookup. They are always the table's own spelling, so `new york ny` and `New York, NY` produce the same answer.
- Errors are not cached.

The in-memory cache belongs to one process. The API is run as one process with several threads, so every repeat is a hit. Running several processes needs a shared cache (NFR-18).

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
      "order": 1, "kind": "start", "station_id": "…", "name": "DELTA", "address": "…",
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
| 400 | `invalid_request` | A parameter is missing, empty or malformed, or start and finish are the same place | `fields`: the messages per parameter |
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
| 503 | `stations_not_loaded` | `load_stations` has not been run | — |

`trips/errors.py` holds the table from code to status and builds this body. It also turns the framework's own errors (validation, rate limit, wrong method, unexpected failure) into the same shape. An unexpected failure is logged in full and answered with `internal_error` and no detail. A catch-all route answers every unknown address with `not_found`. Neither depends on Django's debug setting.

Only GET is specified. HEAD and OPTIONS are left to the framework's defaults; every other method gets `method_not_allowed`.

`timings_ms.own` is our own work up to the point the answer is handed to the framework. It does not include writing the JSON.

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
| Cache | Django in-memory cache | Nothing to install |
| Server | gunicorn, one process with threads | One process keeps the in-memory cache and station index shared |
| Packaging | uv | One command to install and run |
| Containers | Docker Compose | One command starts PostgreSQL and the API |
| Tests and lint | pytest, pytest-django, Ruff | |

Left out on purpose: pandas (the `csv` module handles 8,151 rows), django-environ (settings are read with `os.environ`), and any API key.

**Settings from the environment:** `DATABASE_URL`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`. Each has a default that works with the Compose file. `.env.example` lists them. The database password in the Compose file is a local development default, not a secret.

**Settings in code:** the two routing server templates, the 5-second deadline, the User-Agent, the default stop cost, the cache timeout, the rate limit.

## 13. Testing

No test reaches beyond the local machine. A test fixture blocks every connection except the one to the local database.

| Area | What is tested | Needs the database |
|---|---|---|
| Fuel plan | Hand-worked cases: cheaper station ahead, none ahead, finish within range, equal prices, single station, two stations at one mile, impossible gap. Then the two comparisons in section 8. | no |
| Geometry | Known distances, re-spacing, mile markers, the border test on a real road through Ontario and on roads that stay in the USA | no |
| Station search | A straight synthetic road with stations at known offsets, ties and thinning | no |
| Routing client | Both server addresses, each failure that should retry and the one that should not | no |
| Places | The 58 names from the research run, the everyday spellings in D-3, unknown and out-of-coverage names | no |
| Loader and index | A small CSV with duplicates, padding and a Canadian row. One test on the real CSV asserting the counts in section 6. | yes |
| Endpoint | The routing client replaced with a fake. The response shape, the cache behaviour, and every error code. | yes |
| Verifier | An independent checker, written from this document, applied to every successful response | yes |

## 14. Speed

*Measured* on the New York to Los Angeles road, the largest tested:

| Step | Time |
|---|---|
| Routing call | 600 to 1,700 ms (network, outside our control) |
| Read the routing response | 25 ms |
| Mile markers and station search | 4 ms |
| Border check | 7 ms (40 ms on Boston to Seattle, which follows the border for longest) |
| Fuel plan and the lowest possible bill | 5 ms |
| Build the response | about 10 ms (estimate, not measured) |
| **Our own work** | **about 50 ms**, against a limit of 100 ms (NFR-1) |

Each figure is a single run of a research script on this machine, not an average.

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

## 16. Known limits

- **Station positions are approximate.** They are city centres, a median 2.8 miles from the real station. Mile markers carry that error, and there is no safety reserve on the 500-mile range.
- **Some roads have no fuel listed.** The CSV has no station on Interstate 5 through California, so trips such as Los Angeles to Seattle have no plan. The API says so; it does not invent a stop.
- **Car routing, not truck routing.** The free server has no truck profile, so low bridges and truck bans are ignored.
- **Places are cities.** Street addresses, ZIP codes and coordinates are not understood.
- **The routing servers are free demos** with no uptime promise. The second server covers a failure of the first, not of both.
- **The cache is per process** unless a shared cache is added.
- **Border outlines are coarse.** A road that follows the border can register up to 10 miles as abroad (*measured*), which is why the limit is 25.
- **Docker is needed** to run PostgreSQL.
- **Not yet checked:** that the response's map draws correctly in geojson.io for a coast-to-coast trip. It will be checked as soon as the API returns one.

## 17. Build order

1. Project, PostgreSQL, settings, every module's interface
2. Places, `FuelStation`, `load_stations`, the in-memory index; geometry and station search; the fuel plan; the routing client. Each with its tests.
3. `plan_trip`, the answer builder, the view, errors and caches, with endpoint tests
4. Independent verification, live tests, review
5. Dockerfile and one-command start
6. README and Postman collection
