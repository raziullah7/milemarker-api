# Mile Marker API: Use Cases

What the API does for the people who use it, step by step, and which tests prove each part.

Requirement IDs (FR, NFR, D) refer to `requirements.md`. Test IDs refer to `test-cases.md`. Field names, error codes and status codes are those of `backend-architecture.md`, section 11. Query strings are shown unencoded. "≈" marks a figure measured on real roads while the API was designed; a test passes within 2% of it.

Every successful response is also checked against the correctness rules R1 to R17 in `test-cases.md`, section 4. The use cases below do not repeat that.

## Actors

| Actor | Who | Uses |
|---|---|---|
| Driver or dispatcher | Plans a truck trip and wants to know where to buy fuel and what it will cost | Any HTTP client: Postman, a browser, curl, an application |
| Operator | Installs and runs the service, and loads the station data | `manage.py`, Docker Compose |
| Reviewer | Checks the project: runs it from a clone, runs the tests, tries the requests | git, Docker, uv, Postman |
| Visitor | Watches a trip drawn on a map | A web browser, at the viewer's address |
| Maintainer | Changes the code and pushes it to the repository | git, GitHub, make |

## Use cases at a glance

| ID | Use case | Actor |
|---|---|---|
| UC-01 | Plan fuel for a long trip | Driver or dispatcher |
| UC-02 | Plan a trip shorter than one tank | Driver or dispatcher |
| UC-03 | Choose between the cheapest bill and fewer stops | Driver or dispatcher |
| UC-04 | Ask for the same trip again | Driver or dispatcher |
| UC-05 | Start where no station is listed nearby | Driver or dispatcher |
| UC-06 | Give places in everyday spellings | Driver or dispatcher |
| UC-07 | Mistype a place and get suggestions | Driver or dispatcher |
| UC-08 | Ask for a place the API does not cover | Driver or dispatcher |
| UC-09 | Ask for a trip whose road leaves the USA | Driver or dispatcher |
| UC-10 | Ask for a trip with no fuel listed along the road | Driver or dispatcher |
| UC-11 | See the route and stops on a map | Driver or dispatcher |
| UC-12 | The routing service fails or finds no road | Driver or dispatcher |
| UC-13 | Load the station data | Operator |
| UC-14 | Run the project from a fresh clone | Reviewer |
| UC-15 | Send an incomplete or malformed request | Driver or dispatcher |
| UC-16 | Ask for a trip from a place to itself | Driver or dispatcher |
| UC-17 | Use the wrong method or address | Driver or dispatcher |
| UC-18 | Send too many requests | Driver or dispatcher |
| UC-19 | Run the automated tests and lint | Reviewer |
| UC-20 | Try the API from the Postman collection | Reviewer |
| UC-21 | Watch a trip in the viewer | Visitor |
| UC-22 | Open the viewer with no trip and choose an example | Visitor |
| UC-23 | The viewer when a place is mistyped | Visitor |
| UC-24 | The viewer when the API refuses the trip | Visitor |
| UC-25 | The viewer when the API cannot be reached | Visitor |
| UC-26 | The viewer with reduced motion | Visitor |
| UC-27 | The viewer without WebGL2 | Visitor |
| UC-28 | The viewer when the map servers cannot be reached | Visitor |
| UC-29 | Read the API's documentation page | Driver or dispatcher |
| UC-30 | Check the service's health | Operator |
| UC-31 | Call the API through the front door | Driver or dispatcher |
| UC-32 | Ask again for a trip that another worker planned | Driver or dispatcher |
| UC-33 | The service when Redis is down | Operator |
| UC-34 | Try to escape the rate limit through the proxy | Driver or dispatcher |
| UC-35 | Follow a request through the logs | Operator |
| UC-36 | Start the whole stack from a fresh clone | Reviewer |
| UC-37 | Run the checks with make | Reviewer |
| UC-38 | A push to the repository runs CI | Maintainer |
| UC-39 | Run the end-to-end stack with no call to the public routing servers | Reviewer |

---

## UC-01 Plan fuel for a long trip

| | |
|---|---|
| Goal | Get the road, where to buy fuel and how much, and the fuel bill, for a trip longer than one tank |
| Actor | Driver or dispatcher |
| Preconditions | The stations are loaded. The routing service is reachable. The same trip has not been asked for in the last 24 hours. |
| Request | `GET /api/v1/route/?start=New York, NY&finish=Los Angeles, CA` |

**Main flow**

1. The client sends the request.
2. The API checks that `start` and `finish` are present, and that `stop_cost`, if sent, is valid.
3. It looks up both places in the offline places table.
4. It finds the station nearest the start place. That station is stop 1, at mile 0: the truck fuels there before leaving.
5. It makes one call to the routing service for the road.
6. It places a point every half mile along the road, each with a mile marker, and checks that the road stays in the USA.
7. It finds the stations within 5 miles of the road and drops each one that a cheaper station within 10 miles makes unnecessary.
8. It chooses where to stop and how much to buy, charging $10 per stop while it chooses. The $10 is never added to the bill.
9. It returns the plan and stores it in the cache.

**What comes back:** 200.

| Field | Value |
|---|---|
| `summary.start.label`, `summary.finish.label` | `New York, NY`, `Los Angeles, CA` |
| `summary.distance_miles` | ≈ 2,800.7 |
| `summary.gallons` | `distance_miles` ÷ 10, exactly |
| `summary.stops` | Fewer than 10 (design: 7) |
| `summary.total_fuel_cost` | ≈ 865.93; the sum of the stops' `cost` |
| `summary.lowest_possible_fuel_cost` | ≈ 854.65; never above the total |
| `summary.first_fill_distance_miles` | ≈ 3.1 |
| `warnings` | `[]` |
| `assumptions` | `range_miles` 500, `miles_per_gallon` 10, `tank_gallons` 50, `starting_fuel_gallons` 0, `stop_cost` 10.0, `search_radius_miles` 5 |
| `fuel_stops[0]` | `kind` `start`, `mile_marker` 0.0 |
| `fuel_stops[1…]` | `kind` `station`; mile markers increasing; no stretch over 500 miles |
| `map` | A FeatureCollection: the route line, one point per stop, the start and the finish |
| `meta` | `routing_calls` 1, `cache_hit` false, `routing_server` `router.project-osrm.org` |

**Alternative flows**

- A1. The station nearest the start is more than 25 miles away: see UC-05.
- A2. A place is unknown or outside coverage: see UC-07 and UC-08.
- A3. The road leaves the USA (UC-09), has no fuel listed (UC-10), or the routing service fails (UC-12).
- A4. The shortened station list has no plan but the full list has one: the plan is made from the full list, and the answer is 200.
- A5. Several stations share the position nearest the start: the cheapest is stop 1; on equal price, the lowest station ID.
- A6. Something unexpected fails: 500 `internal_error` in the standard error body, with no internal detail.

**Requirements:** FR-1, FR-3, FR-5, FR-6, FR-7, FR-8, FR-9, FR-12, FR-13, NFR-1, NFR-2, NFR-3, D-1, D-7, D-8, D-9, D-10, D-11, D-14

**Test cases:** P01, P06, P07, P09, S01, GE-01 to GE-09, CO-01 to CO-17, FU-01 to FU-06, FU-10, FU-15, FU-19, EX-01, EX-03, AN-01 to AN-04, AN-06 to AN-08, AN-10, EP-01, EP-26, EP-33, EP-38

---

## UC-02 Plan a trip shorter than one tank

| | |
|---|---|
| Goal | Get a valid plan with a real cost for a trip under 500 miles |
| Actor | Driver or dispatcher |
| Preconditions | The stations are loaded. The routing service is reachable. |
| Request | `GET /api/v1/route/?start=Dallas, TX&finish=Houston, TX` |

**Main flow**

1. The client sends the request.
2. The API resolves both places and finds the station nearest Dallas, which is stop 1.
3. It makes one routing call: the road is about 238 miles.
4. The truck starts empty (D-1), so the plan buys fuel for the whole trip: all at stop 1, or part of it at a station further on, when buying there saves more than the $10 stop cost.
5. It returns the plan.

**What comes back:** 200.

| Field | Value |
|---|---|
| `summary.distance_miles` | ≈ 238.1 |
| `summary.gallons` | `distance_miles` ÷ 10 |
| `summary.total_fuel_cost` | Above 0 |
| `fuel_stops[0]` | `kind` `start`, `mile_marker` 0.0 |

**Alternative flows**

- A1. No station is listed along the road (Los Angeles to Las Vegas, Los Angeles to San Francisco): one stop, at the start, buys all the fuel. A warning is added when the start station is more than 25 miles away.
- A2. A very short trip (Fort Worth to Dallas): one stop at mile 0, buying `distance_miles` ÷ 10 gallons.

**Requirements:** FR-8, D-1

**Test cases:** P08, P12, P19, P20

---

## UC-03 Choose between the cheapest bill and fewer stops

| | |
|---|---|
| Goal | See the cheapest possible fuel bill, and what a plan with fewer stops costs |
| Actor | Driver or dispatcher |
| Preconditions | As UC-01. Usually the same trip was planned before, so its road is cached. |
| Request | `GET /api/v1/route/?start=New York, NY&finish=Los Angeles, CA&stop_cost=0` |

**Main flow**

1. The client sends the request with `stop_cost`, a number from 0 to 100 with at most 2 decimals.
2. The API resolves both places.
3. It takes the road from the road cache, so it makes no routing call.
4. It chooses the stops, charging the given stop cost while choosing. With 0, it makes as many stops as save money.
5. It returns the plan, with the lowest possible bill (stops free) beside the plan's own bill.

**What comes back:** 200.

| Field | Value |
|---|---|
| `summary.total_fuel_cost` | With `stop_cost=0`: equal to `lowest_possible_fuel_cost` (≈ 854.65). With 25: not below the default plan's (≈ 884.79) |
| `summary.stops` | With 0: more than the default plan's (design: 17). With 25: no more than the default plan's (design: 6) |
| `summary.lowest_possible_fuel_cost`, `lowest_possible_stops` | The bill and stop count with free stops; the same for every stop cost on this trip |
| `assumptions.stop_cost` | The value sent, for example 0.0 |
| `meta` | `routing_calls` 0, `cache_hit` false |

**Alternative flows**

- A1. The trip was not planned before: one routing call, as in UC-01.
- A2. `stop_cost` is below 0, above 100, has more than 2 decimals, or is not a number: see UC-15.
- A3. The same trip and stop cost were asked for before: see UC-04.

**Requirements:** FR-6, FR-15, FR-16, NFR-1, NFR-2, D-9, D-10

**Test cases:** P03, P04, P15, S03, FU-07, FU-08, FU-09, FU-11, FU-17, FU-18, FU-20, FU-21, FU-22, FU-23, EX-02, EX-04, AN-11, EP-03, EP-12, EP-27

---

## UC-04 Ask for the same trip again

| | |
|---|---|
| Goal | Get a plan already made, at once and without a routing call |
| Actor | Driver or dispatcher |
| Preconditions | The same start, finish and stop cost were planned within the last 24 hours, by the same server process or, when the cache is Redis, by any worker (UC-32). |
| Request | `GET /api/v1/route/?start=New York, NY&finish=Los Angeles, CA` (again) |

**Main flow**

1. The client sends the request.
2. The API resolves both places. The labels come from this lookup.
3. It finds the answer in the cache, by the two positions and the stop cost.
4. It rebuilds `meta` and returns the answer.

**What comes back:** 200.

| Field | Value |
|---|---|
| `summary`, `fuel_stops`, `map` | Identical to the first answer |
| `meta` | `routing_calls` 0, `cache_hit` true, `timings_ms.routing` 0 |
| Time | Under 50 ms |

**Alternative flows**

- A1. The places are spelled differently (`new york city, ny`, `Los Angeles, California`): the same cache entry is used, and the labels are the table's spelling.
- A2. An unknown extra parameter is sent: it is ignored, and the cache entry is used.
- A3. `stop_cost` is sent as `10` or `10.00`: the same entry as the default.
- A4. More than 24 hours have passed, or the trip is reversed: the answer is made again, with one routing call.
- A5. The earlier request failed: errors are not cached, so this one is planned afresh.

**Requirements:** FR-13, NFR-2, NFR-11, D-15

**Test cases:** P02, P14, P16, S02, EP-02, EP-04, EP-05, EP-06, EP-07, EP-08, EP-40

---

## UC-05 Start where no station is listed nearby

| | |
|---|---|
| Goal | Get a plan from a start place with no listed station close by, and be told how far the first fill-up is |
| Actor | Driver or dispatcher |
| Preconditions | As UC-01 |
| Request | `GET /api/v1/route/?start=Los Angeles, CA&finish=New York, NY` |

**Main flow**

1. The client sends the request.
2. The API finds the station nearest Los Angeles. It is about 121 miles away, because the CSV lists no station near the city.
3. That station is stop 1, at mile 0, priced at its CSV price. Its position on the map is the start place.
4. The distance is more than 25 miles, so a warning is added.
5. The plan is made and returned as in UC-01.

**What comes back:** 200.

| Field | Value |
|---|---|
| `summary.first_fill_distance_miles` | ≈ 121, over 100 |
| `warnings` | One sentence, naming the station and the distance |
| `fuel_stops[0]` | `kind` `start`, `mile_marker` 0.0, `lat` and `lng` of Los Angeles, the distant station's name, city, state and price |

**Alternative flows**

- A1. The nearest station is 25 miles away or less: `warnings` is `[]`, and `first_fill_distance_miles` is still reported.

**Requirements:** FR-14, D-1

**Test cases:** P05, P13, P19, LD-18, AN-05, EP-37

---

## UC-06 Give places in everyday spellings

| | |
|---|---|
| Goal | Type a city and state the way people write them, and have it understood |
| Actor | Driver or dispatcher |
| Preconditions | As UC-01 |
| Request | `GET /api/v1/route/?start=st. louis, mo&finish=Winston-Salem, North Carolina` |

**Main flow**

1. The client sends the request.
2. For each place, the API trims it, drops a trailing `USA`, `US` or `United States`, and splits city from state at the last comma (or, with no comma, takes the last word or words as the state when they are a state code or name).
3. It reads the state as letters only, as a code or a name.
4. It matches the city ignoring case, spaces and punctuation, with `St`, `Ste`, `Ft` and `Mt` read as `Saint`, `Sainte`, `Fort` and `Mount`, and with `New York City`, `NYC` and `Manhattan` meaning New York, NY.
5. It plans the trip as in UC-01.

**What comes back:** 200, with `summary.start.label` `Saint Louis, MO` and `summary.finish.label` `Winston Salem, NC`: the places table's own spelling.

**Alternative flows**

- A1. No comma: `Dallas TX` resolves to `Dallas, TX`.
- A2. State name and trailing country: `Phoenix, Arizona, USA` resolves to `Phoenix, AZ`.
- A3. `Washington, D.C.` resolves to `Washington, DC`.
- A4. `Santa Fe, New Mexico` resolves to `Santa Fe, NM`; the word Mexico in a state name does not make it foreign.
- A5. `Manhattan, KS` stays in Kansas; the New York alias applies only in New York.

**Requirements:** FR-1, D-3

**Test cases:** P10, P11, P17, P18, PL-01 to PL-09

---

## UC-07 Mistype a place and get suggestions

| | |
|---|---|
| Goal | Learn which place name was not understood, and what was probably meant |
| Actor | Driver or dispatcher |
| Preconditions | None |
| Request | `GET /api/v1/route/?start=Chicgo, IL&finish=Houston, TX` |

**Main flow**

1. The client sends the request.
2. The API looks up the start first and does not find it.
3. It stops there: no routing call is made.
4. It returns the error, with up to five known names close to the one sent.

**What comes back:** 400.

```json
{"error": {"code": "unknown_place", "message": "…", "details": {"field": "start", "query": "Chicgo, IL", "suggestions": ["Chicago, IL"]}}}
```

`suggestions` holds at most 5 names, as `City, ST`, and includes `Chicago, IL`.

**Alternative flows**

- A1. No state given (`Chicago`): the suggestions are that city name in every state that has it, here `["Chicago, IL"]`.
- A2. Both places are wrong: the error names `start`.
- A3. Only the finish is wrong: the error names `finish`.
- A4. A ZIP code or a street address is sent: `unknown_place`, as neither is accepted.
- A5. The state is not recognised (`Springfield, ZZ`): `unknown_place`, with at most 5 suggestions.

**Requirements:** FR-2, FR-11, NFR-3, D-3

**Test cases:** N03, N04, N05, N16, N26, PL-16 to PL-21, EP-15, EP-16, EP-17

---

## UC-08 Ask for a place the API does not cover

| | |
|---|---|
| Goal | Be told clearly that a place is outside the area served |
| Actor | Driver or dispatcher |
| Preconditions | None |
| Request | `GET /api/v1/route/?start=Honolulu, HI&finish=Los Angeles, CA` |

**Main flow**

1. The client sends the request.
2. The API recognises Hawaii as outside the lower 48 states and DC.
3. It stops there: no routing call is made.
4. It returns the error.

**What comes back:** 422, `outside_coverage`, with `details.field` `start` and `details.query` `Honolulu, HI`.

**Alternative flows**

- A1. Alaska, Puerto Rico, a Canadian province, or a place ending in `Canada` or `Mexico`: the same error.
- A2. The finish is the uncovered place: the error names `finish`.

**Requirements:** FR-2, NFR-3, D-4

**Test cases:** N06, N07, N08, N18, N19, PL-15, EP-18

---

## UC-09 Ask for a trip whose road leaves the USA

| | |
|---|---|
| Goal | Be told that the road runs through another country, instead of getting a plan that buys fuel abroad |
| Actor | Driver or dispatcher |
| Preconditions | As UC-01 |
| Request | `GET /api/v1/route/?start=Detroit, MI&finish=Buffalo, NY` |

**Main flow**

1. The client sends the request.
2. The API resolves both places and makes one routing call.
3. It checks the road against the outlines of Canada and Mexico and finds about 252 miles in a row inside Ontario, more than the 25 allowed.
4. It returns the error without making a fuel plan.

**What comes back:** 422, `route_leaves_usa`, with `details.miles_abroad` ≈ 252.

**Alternative flows**

- A1. The road runs along the border but registers 25 miles or less abroad (Seattle to Blaine, Laredo to Brownsville): a normal plan, as in UC-01.
- A2. The road leaves the USA and also has no fuel listed: `route_leaves_usa`, because the border is checked first.

**Requirements:** FR-10, D-4

**Test cases:** N11, N22, GE-10 to GE-17, EP-21, EP-22, EP-23

---

## UC-10 Ask for a trip with no fuel listed along the road

| | |
|---|---|
| Goal | Be told that no valid plan exists, and where the gap is, instead of getting a plan that runs dry |
| Actor | Driver or dispatcher |
| Preconditions | As UC-01 |
| Request | `GET /api/v1/route/?start=Los Angeles, CA&finish=Seattle, WA` |

**Main flow**

1. The client sends the request.
2. The API resolves both places, makes one routing call and finds the stations along the road.
3. It checks every gap between neighbouring stations, and from the last one to the finish. From the start to the first station, in Halsey, Oregon, is about 886 miles, more than a tank's 500.
4. It returns the error.

**What comes back:** 422, `no_fuel_plan`, with `details.gap_start_mile` 0.0 and `details.gap_miles` ≈ 886.

**Alternative flows**

- A1. The gap is in the middle of the trip: `gap_start_mile` is the mile of the station before it.
- A2. A gap appears only in the shortened station list: the full list is used and a plan is returned (UC-01, A4).

**Requirements:** FR-7, FR-10

**Test cases:** N12, N23, FU-12, FU-13, FU-14, FU-16, FU-24, FU-25, EP-25

---

## UC-11 See the route and stops on a map

| | |
|---|---|
| Goal | Draw the route and the fuel stops in any map viewer |
| Actor | Driver or dispatcher |
| Preconditions | A successful plan, as in UC-01 |
| Request | `GET /api/v1/route/?start=New York, NY&finish=Los Angeles, CA`, then the `map` object pasted into geojson.io |

**Main flow**

1. The client takes `map` from the response.
2. It opens it in a GeoJSON viewer such as geojson.io.
3. The viewer draws the route line, a labelled marker for each stop, and markers for the start and the finish.

**What comes back:** `map` is a GeoJSON FeatureCollection, in this order:

| Feature | Properties |
|---|---|
| The route, a LineString | `kind` `route`, `distance_miles` |
| One Point per stop | `kind` `stop`, `order`, `title` (for example `2. SHEETZ #639, Youngstown OH`), `name`, `mile_marker`, `price_per_gallon`, `gallons`, `cost`, `marker-color` |
| A Point for the start and one for the finish | `kind`, `title`, `marker-color` |

**Alternative flows**

- A1. The viewer (FR-18) draws this same `map` on its own page: see UC-21.

**Requirements:** FR-4, D-2

**Test cases:** M01, AN-09

---

## UC-12 The routing service fails or finds no road

| | |
|---|---|
| Goal | Get either a plan or a clear error within about 10 seconds, never a hang or a crash |
| Actor | Driver or dispatcher |
| Preconditions | The trip is not cached. The first routing server is failing or slow. |
| Request | Any new trip, for example `GET /api/v1/route/?start=Dallas, TX&finish=Houston, TX` |

**Main flow**

1. The client sends the request.
2. The API calls the first routing server, with a deadline of 5 seconds.
3. The call times out, cannot connect, gets a 5xx or 429 status, or gets an answer that is not a route.
4. The API sends the one retry to the second server, also with a 5-second deadline.
5. The second server answers, and the plan is made as in UC-01.

**What comes back:** 200, with `meta.routing_calls` 2 and `meta.routing_server` `routing.openstreetmap.de`.

**Alternative flows**

- A1. Both servers fail: 502 `routing_unavailable`, after no more than two calls. `details.reason` is `timeout` when both attempts timed out, and `error` otherwise.
- A2. The first server answers that no road joins the points: 422 `no_route`, with no retry.

**Requirements:** NFR-2, NFR-12, D-12

**Test cases:** S04, RT-01 to RT-14, EP-24, EP-28, EP-29, EP-30

---

## UC-13 Load the station data

| | |
|---|---|
| Goal | Turn the supplied fuel CSV into located, de-duplicated stations in the database, once |
| Actor | Operator |
| Preconditions | PostgreSQL is running and migrated. `data/` holds the fuel CSV and `us_cities.csv`. |
| Request | `uv run python manage.py load_stations` (in Docker Compose, the start-up runs it) |

**Main flow**

1. The command reads the CSV and trims every field.
2. It keeps one row per `OPIS Truckstop ID`: the cheapest listing, or the first row on a price tie.
3. It drops every station outside the lower 48 states and DC.
4. It places each station at its city's centre from the places table, using the named county's row for the 22 places whose rows are more than 10 miles apart, and the five places added by hand.
5. It replaces the station table inside one transaction.
6. It prints the counts.

**What comes back:** exit code 0 and the counts: 8,151 rows; 6,738 stations; 6,626 in the lower 48 and DC; 6,615 placed from the table; 11 from hand-added places; 6,626 saved.

**Alternative flows**

- A1. A US station's city cannot be placed: the command lists it and exits with an error, and the table keeps what it held.
- A2. The command is run again: the table is replaced, still 6,626 rows.
- A3. A trip is requested before the stations are loaded: 503 `stations_not_loaded`, with no routing call. Once they are loaded, requests work without a restart.
- A4. With the table empty, an unknown place still gets 400 `unknown_place`, because places are checked first.

**Requirements:** FR-9, NFR-7, NFR-10, D-5, D-6, D-13

**Test cases:** PL-10 to PL-14, LD-01 to LD-17, EP-31, EP-32

---

## UC-14 Run the project from a fresh clone

Release 2 supersedes this use case with UC-36: Redis, a one-off setup service and the viewer join the stack, and nginx becomes the only way in. UC-14 stays as release 1.0's, the use case that CT-01 to CT-05, FC-01, FC-04 and M02 were run against.

| | |
|---|---|
| Goal | Start the API from nothing, with one command and no account or key |
| Actor | Reviewer |
| Preconditions | git and Docker are installed. |
| Request | `git clone <repository>`, then `docker compose up`, then `GET /api/v1/route/?start=Dallas, TX&finish=Houston, TX` at the address the README gives |

**Main flow**

1. The reviewer clones the public repository into an empty folder.
2. They run `docker compose up`.
3. Compose starts PostgreSQL 17 and the API. The API's start-up applies migrations and loads the stations.
4. They send the example request from the README.

**What comes back:** 200 with a plan. Nothing asks for an account, a key or a `.env` file.

**Alternative flows**

- A1. Compose is stopped and started again: the loader replaces the table and the API works as before.
- A2. Docker is not installed: not supported, as PostgreSQL runs in Docker.

**Requirements:** NFR-5, NFR-9, NFR-10, D-13

**Test cases:** CT-01, CT-02, CT-03, CT-04, CT-05, FC-01, FC-04, M02

---

## UC-15 Send an incomplete or malformed request

| | |
|---|---|
| Goal | Learn which parameter is wrong and why |
| Actor | Driver or dispatcher |
| Preconditions | None |
| Request | `GET /api/v1/route/?start=New York, NY` |

**Main flow**

1. The client sends the request.
2. The API checks the parameters' shape before anything else and finds `finish` missing.
3. It returns the error. No place is looked up and no routing call is made.

**What comes back:** 400.

```json
{"error": {"code": "invalid_request", "message": "…", "details": {"fields": {"finish": ["…"]}}}}
```

**Alternative flows**

- A1. A parameter is empty or only spaces: the same error, naming it.
- A2. No parameters at all: `fields` names both `start` and `finish`.
- A3. `stop_cost` is below 0, above 100, has more than 2 decimals, is empty, or is not a number (`abc`, `nan`, `inf`): the same error, naming `stop_cost`.
- A4. An unknown extra parameter is sent: it is ignored, and the request succeeds.

**Requirements:** FR-11

**Test cases:** N01, N02, N10, N17, N20, N21, N24, EP-09, EP-10, EP-11, EP-13, EP-14, EP-39

---

## UC-16 Ask for a trip from a place to itself

| | |
|---|---|
| Goal | Be told that the start and the finish are the same place |
| Actor | Driver or dispatcher |
| Preconditions | None |
| Request | `GET /api/v1/route/?start=Dallas, TX&finish=dallas texas` |

**Main flow**

1. The client sends the request.
2. The API resolves both names to the same coordinates, to 4 decimals.
3. It returns the error without a routing call.

**What comes back:** 400, `invalid_request`, with `details.fields` naming `finish`.

**Alternative flows**

- A1. Two aliases of one place (`New York City, NY` and `Manhattan, NY`): the same error.
- A2. Two different places whose road is shorter than half a mile: treated as the same place, the same error, after one routing call.

**Requirements:** FR-11

**Test cases:** N09, N25, EP-19, EP-20

---

## UC-17 Use the wrong method or address

| | |
|---|---|
| Goal | Get the same kind of error body for a client mistake as for any other error |
| Actor | Driver or dispatcher |
| Preconditions | None |
| Request | `POST /api/v1/route/?start=New York, NY&finish=Los Angeles, CA`; `GET /api/v1/routes/` |

**Main flow**

1. The client sends a request with a method other than GET, or to an address that does not exist.
2. The API turns the framework's own error into the standard body.

**What comes back:** 405 `method_not_allowed` for POST, PUT, PATCH or DELETE; 404 `not_found` for an unknown address. Both as `{"error": {"code", "message", "details"}}`.

**Alternative flows:** none.

**Requirements:** FR-11

**Test cases:** N13, N14, EP-35, EP-36

---

## UC-18 Send too many requests

| | |
|---|---|
| Goal | Be told to slow down, and for how long |
| Actor | Driver or dispatcher |
| Preconditions | The client has sent 60 requests in the last minute. |
| Request | `GET /api/v1/route/?start=New York, NY&finish=Los Angeles, CA` (the 61st) |

**Main flow**

1. The client sends one more request.
2. The API refuses it before any other work.

**What comes back:** 429, `rate_limited`, with `details.retry_after_seconds` above 0.

**Alternative flows**

- A1. The client waits for the time given: requests are accepted again.

**Requirements:** NFR-16

**Test cases:** N15, EP-34

---

## UC-19 Run the automated tests and lint

| | |
|---|---|
| Goal | Confirm that the code does what the documents say, and passes lint |
| Actor | Reviewer |
| Preconditions | A clone, `uv sync` done, and the Compose database running |
| Request | `uv run pytest`, then `uv run ruff check .` |

**Main flow**

1. The reviewer runs `uv run pytest`.
2. The tests run with no network: a fixture blocks every connection except those to the same machine: the local database and, for their own tests, the local Redis and the stand-in routing server.
3. The fuel plan is compared with two exact methods, the endpoint is tested with a fake routing service, and every successful endpoint response is checked by the independent verifier.
4. The reviewer runs `uv run ruff check .`.

**What comes back:** every test passes; Ruff reports no findings.

**Alternative flows**

- A1. CI is built (NFR-17): it runs both on every push.

**Requirements:** NFR-4, NFR-6, NFR-8, NFR-13, NFR-14, NFR-17

**Test cases:** VF-01 to VF-19, PJ-01 to PJ-05, FC-02, FC-03, FC-05, M04

---

## UC-20 Try the API from the Postman collection

| | |
|---|---|
| Goal | Send the demonstration requests and see each one checked |
| Actor | Reviewer |
| Preconditions | The API is running with an empty cache: freshly started, together with Redis when the cache is Redis. |
| Request | Import the collection from `docs/`, set `base_url` to the API's address, run it; or `npx newman run <collection> --env-var base_url=<API address> --delay-request 1200` |

**Main flow**

1. The reviewer opens or runs the collection.
2. The requests run in three folders: the demo trip and its cache and stop-cost variants, more trips, and errors.
3. Each request's own checks run on its response.

**What comes back:** every check passes; Newman exits with code 0.

**Alternative flows**

- A1. The cache was not empty: the first request may report a cache hit, and its routing-call check fails. Restart the API, and Redis too when the cache is Redis (it keeps nothing on disk), and run again.

**Requirements:** NFR-15

**Test cases:** PM-01, PM-02

---

## UC-21 Watch a trip in the viewer

| | |
|---|---|
| Goal | See a trip drawn on a map, with its fuel stops and its figures, as it plays from a globe in space down to the road |
| Actor | Visitor |
| Preconditions | The stack is running and the stations are loaded. The browser has WebGL2 and does not ask for reduced motion. The map servers can be reached. |
| Request | `http://127.0.0.1:8000/?start=New York, NY&finish=Los Angeles, CA&stop_cost=10`, opened in a browser |

**Main flow**

1. The visitor opens the address.
2. The viewer reads `start`, `finish` and `stop_cost` from it and sends one `GET /api/v1/route/` with those parameters, on its own origin. While it waits, the panel shows that the trip is loading.
3. 0–3 s: the night-side globe turns slowly under an atmosphere glow, and the trip's title fades in.
4. 3–8 s: the camera flies down to the route, tilting as it arrives. The night lights give way to the road map, and the summary cards slide in.
5. 8–15 s: the route draws itself along the road, its head moving at a constant speed along the line as drawn. The distance counter shows the road miles at the head of the line.
6. As the head reaches each fuel stop, its marker pops in, its card appears, and the fuel-cost counter adds that stop's cost; stop 1, at the start, appears at 8 s. Each stop is timed by its position along the line as drawn in Web Mercator, not by its mile marker.
7. 15–16.5 s: the camera settles, the finish marker pulses, and a scrubber appears.
8. The visitor chooses a stop's card, and the camera flies to that stop.

**What comes back:** the API's 200 answer, drawn.

| Part | Shows |
|---|---|
| Map | The route line of `map`, unchanged (D-2); one marker per stop; the start and the finish |
| Panel | `summary.distance_miles`, `summary.stops`, `summary.total_fuel_cost`, `summary.lowest_possible_fuel_cost`, any warning, the assumptions, and one card per stop with its name, city and state, price, gallons, cost and mile marker. Every figure is the API's, unchanged, shown as `2,800.6 mi`, `$867.27`, `39.15` gallons and `$3.239 / gal` |
| Counters at the end | Distance: `summary.distance_miles`. Fuel cost: `summary.total_fuel_cost` |
| Stop 1's card | That its fuel is priced at the station named, the listed station nearest the start, and that the stop is drawn at the start |
| Credits | The sources in use, on screen at all times: NASA GIBS, OpenFreeMap, OpenMapTiles and OpenStreetMap, and Natural Earth for the built-in outlines beneath |

**Alternative flows**

- A1. Skip, during the animation: it jumps to the end.
- A2. Replay, at the end: it starts again from the globe, without asking the API again.
- A3. The visitor drags the scrubber: the map, the markers and the counters show that moment.
- A4. During the intro, a press on the map, a wheel turn, a touch or the Escape key cancels it: the trip is shown finished, as after Skip, and the camera stays where the visitor's gesture leaves it.
- A5. The start station is more than 25 miles away: the API's warning is shown in the panel (UC-05).
- A6. The visitor uses only the keyboard: every control, the stop cards, Skip, Replay and the scrubber included, is reached and worked from it.
- A7. A place is unknown (UC-23), the API refuses the trip (UC-24), or the API cannot be reached (UC-25).
- A8. Reduced motion (UC-26), no WebGL2 (UC-27), or the map servers cannot be reached (UC-28).

**Requirements:** FR-18, FR-21, FR-22, FR-23, FR-26, NFR-28, NFR-29, D-2, D-17, D-18, D-19

**Test cases:** VT-01 to VT-15, VP-01 to VP-05, VP-12, VP-15, VP-16, VP-17, VP-19, VB-01, VB-04 to VB-12, VB-17, VB-18, VB-20, VB-21, VB-22, VB-26, PX-18, EE-08

---

## UC-22 Open the viewer with no trip and choose an example

| | |
|---|---|
| Goal | See what the viewer does, without knowing an address to give it |
| Actor | Visitor |
| Preconditions | As UC-21 |
| Request | `http://127.0.0.1:8000/` |

**Main flow**

1. The visitor opens the address with neither `start` nor `finish`.
2. The viewer shows the slowly turning globe and three example trips. It sends no request to the API.
3. The visitor chooses one.
4. The viewer opens at that trip's address and plays it as in UC-21.

**What comes back:** three examples, each a link to the viewer's address for that trip.

| Example | `start` | `finish` |
|---|---|---|
| 1 | New York, NY | Los Angeles, CA |
| 2 | Seattle, WA | Miami, FL |
| 3 | Dallas, TX | Houston, TX |

There is no form and no text field: a trip is named only by its address (D-19).

**Alternative flows**

- A1. The visitor uses only the keyboard: the three links are reached with Tab and opened with Enter.
- A2. The visitor's system asks for reduced motion: the globe does not turn.
- A3. The address has `start` but no `finish`, or the reverse: it is not a bare page. The viewer asks the API, which answers 400 `invalid_request` (UC-24).

**Requirements:** FR-21, FR-25, FR-26, NFR-28, D-19

**Test cases:** VP-13, VP-14, VP-18, VB-02, VB-03, VB-17, VB-18, VB-25, VB-26, VB-29

---

## UC-23 The viewer when a place is mistyped

| | |
|---|---|
| Goal | Learn which place was not understood, and reopen the viewer with one of the names the API suggests |
| Actor | Visitor |
| Preconditions | As UC-21 |
| Request | `http://127.0.0.1:8000/?start=Chicgo, IL&finish=Houston, TX&stop_cost=10` |

**Main flow**

1. The visitor opens the address.
2. The viewer asks the API once. The API answers 400 `unknown_place`, naming `start` and suggesting up to five names (UC-07).
3. The panel shows the message for `unknown_place`, and each suggestion as a link.
4. The visitor chooses `Chicago, IL`.
5. The viewer opens at `/?start=Chicago, IL&finish=Houston, TX&stop_cost=10` and plays that trip as in UC-21.

**What comes back:** one link per suggestion, in the API's order. Each link is the same address with the field the API named replaced by that suggestion; the other parameters are kept as they were. No route and no stop is drawn.

**Alternative flows**

- A1. The finish is the mistyped place: the links replace `finish`.
- A2. The API sends no suggestion: the message alone, with no link.

**Requirements:** FR-24, FR-11, D-19

**Test cases:** VP-06, VP-07, VP-08, VP-09, VB-23, VB-24

---

## UC-24 The viewer when the API refuses the trip

| | |
|---|---|
| Goal | Be told plainly why there is no plan |
| Actor | Visitor |
| Preconditions | As UC-21 |
| Request | `http://127.0.0.1:8000/?start=Detroit, MI&finish=Buffalo, NY` |

**Main flow**

1. The visitor opens the address.
2. The viewer asks the API once. The API answers 422 `route_leaves_usa` (UC-09).
3. The panel shows a short heading for that code and, under it, the API's own `message`. No route and no stop is drawn.

**What comes back:** the heading and the API's message. Each code of the error table has its own heading, different from every other: `invalid_request`, `unknown_place` (UC-23), `not_found`, `method_not_allowed`, `outside_coverage`, `route_leaves_usa`, `no_route`, `no_fuel_plan`, `rate_limited`, `internal_error`, `routing_unavailable`, `stations_not_loaded` and `api_unavailable` (UC-25).

**Alternative flows**

- A1. The API answers 429 `rate_limited`: the panel also shows when to try again, from `details.retry_after_seconds`.
- A2. `Honolulu, HI` as the start: the heading for `outside_coverage`.
- A3. `Los Angeles, CA` to `Seattle, WA`: the heading for `no_fuel_plan`.
- A4. Only `start`, or only `finish`, in the address: the viewer asks the API all the same, and shows the `invalid_request` it answers with.

**Requirements:** FR-24, FR-11, NFR-16

**Test cases:** VP-06, VP-10, VP-18, VB-19, VB-23, VB-24

---

## UC-25 The viewer when the API cannot be reached

| | |
|---|---|
| Goal | Be told plainly that the API cannot be reached, not shown a broken page |
| Actor | Visitor |
| Preconditions | The `web` service is running; the `api` service is stopped. |
| Request | `http://127.0.0.1:8000/?start=Dallas, TX&finish=Houston, TX` |

**Main flow**

1. The visitor opens the address. nginx serves the viewer's page, which needs no API.
2. The viewer asks the API. nginx cannot reach it and answers 503 `api_unavailable` in the API's error shape (D-24).
3. The panel says plainly that the API cannot be reached.

**What comes back:** that message. No route and no stop is drawn.

**Alternative flows**

- A1. Nothing answers at all, and the request fails in the browser: the same plain statement.
- A2. The API is running but does not answer within 30 seconds: nginx answers `api_unavailable`, and the viewer says the same. Until then the panel shows that the trip is loading.

**Requirements:** FR-24, D-24

**Test cases:** VP-01, VP-11, VB-24, PX-09, PX-10

---

## UC-26 The viewer with reduced motion

| | |
|---|---|
| Goal | See the trip without the camera flying |
| Actor | Visitor |
| Preconditions | The visitor's system asks for reduced motion. Otherwise as UC-21. |
| Request | As UC-21 |

**Main flow**

1. The visitor opens the address.
2. The viewer asks the API once.
3. It opens on the finished state: the route drawn, every stop's marker and card, the counters at their totals, and the scrubber. The camera does not fly.

**What comes back:** the same map and panel as at the end of UC-21.

**Alternative flows:** none.

**Requirements:** FR-25, NFR-28

**Test cases:** VB-13, VB-19

---

## UC-27 The viewer without WebGL2

| | |
|---|---|
| Goal | Still see the trip, and know why the map is missing, in a browser that cannot draw it |
| Actor | Visitor |
| Preconditions | The browser has no WebGL2. Otherwise as UC-21. |
| Request | As UC-21 |

**Main flow**

1. The visitor opens the address.
2. The viewer asks the API once.
3. It shows a static drawing of the route, the same panel as in UC-21, and a sentence saying why the map cannot be shown.

**What comes back:** the drawing, the panel with the API's figures, and the sentence. The credits name the sources in use: the drawing uses only the API's data and the built-in outlines, so they credit Natural Earth.

**Alternative flows:** none.

**Requirements:** FR-25, FR-23, FR-26

**Test cases:** VB-14, VB-17, VB-19

---

## UC-28 The viewer when the map servers cannot be reached

| | |
|---|---|
| Goal | See the trip even when the servers the map's pictures come from cannot be reached |
| Actor | Visitor |
| Preconditions | As UC-21, but OpenFreeMap's and NASA's servers cannot be reached from the browser. |
| Request | As UC-21 |

**Main flow**

1. The visitor opens the address.
2. The viewer draws its built-in outlines of land and US state lines, from Natural Earth. They are always the bottom layer, beneath the remote map.
3. It gives the remote map's description 4 seconds to arrive. It does not arrive, so the viewer goes on with the outlines alone.
4. The globe, the route, the markers and the panel play as in UC-21.

**What comes back:** the trip drawn on the outlines, with the credits still on screen, naming the sources in use.

**Alternative flows**

- A1. The description arrives, but a tile fails later: that tile is not drawn, and the outlines show through.
- A2. The description arrives after its 4 seconds: it is ignored for that page view, and the outlines stay alone.

**Requirements:** FR-25, FR-26, D-18

**Test cases:** VB-15, VB-16, VB-17, VB-27, VB-28, VB-30

---

## UC-29 Read the API's documentation page

| | |
|---|---|
| Goal | See what the API accepts and returns, in a browser |
| Actor | Driver or dispatcher |
| Preconditions | The stack is running. The browser can reach the CDN the page loads its script from. |
| Request | `http://127.0.0.1:8000/api/v1/docs/` in a browser; `GET /api/v1/schema/` |

**Main flow**

1. The client opens the Swagger page.
2. The page loads its script from a CDN, at a version pinned in the code, and the OpenAPI document from `/api/v1/schema/`.
3. It shows `GET /api/v1/route/`: its three parameters, its 200 body, and its 400, 422, 429, 500, 502 and 503 answers in the standard error shape, with every code each can carry, including the `api_unavailable` the proxy sends. The document's opening text describes `not_found` and `method_not_allowed`, which the route itself never answers.

**What comes back:** the page. The document behind it is OpenAPI 3.0.3, produced from the code by `drf-spectacular`, and equal to the committed `docs/openapi.yaml` (D-20).

**Alternative flows**

- A1. The client asks for `GET /api/v1/schema/` directly: the document.
- A2. The client has sent 60 requests in the last minute: both addresses answer 429 `rate_limited`, like the route.
- A3. The CDN cannot be reached: the page cannot draw itself (architecture section 16).

**Requirements:** FR-19, NFR-16, D-20

**Test cases:** HS-09, HS-11 to HS-18

---

## UC-30 Check the service's health

| | |
|---|---|
| Goal | Know whether the API is up, how many stations it holds, and which cache it is using |
| Actor | Operator |
| Preconditions | The API is running. |
| Request | `GET /api/v1/health/` |

**Main flow**

1. The operator, or Compose's health check, sends the request.
2. The API counts the stations in its in-memory index, loading the index first if it is not loaded yet.
3. It makes one cheap cache read, so that the state it reports is current.
4. It answers.

**What comes back:** 200.

```json
{"status": "ok", "stations": 6626, "cache": "redis"}
```

| `cache` | Meaning |
|---|---|
| `memory` | `REDIS_URL` is not set: the cache is the process's own memory |
| `redis` | `REDIS_URL` is set and the answering process is using Redis |
| `fallback` | `REDIS_URL` is set and the answering process is in its 30-second fallback (UC-33) |

**Alternative flows**

- A1. The stations are not loaded: 503 `stations_not_loaded` in the standard error shape. Once they are loaded, 200, with no restart.
- A2. The client has been rate limited on other addresses: health still answers. It is never limited.
- A3. In Compose, `api` counts as healthy once this answers within 5 seconds, and `web` waits for that.

**Requirements:** FR-20, NFR-16, NFR-18, NFR-22, D-15, D-16

**Test cases:** HS-01 to HS-08, HS-10, HS-19, CF-21, CF-25, CF-28

---

## UC-31 Call the API through the front door

| | |
|---|---|
| Goal | Use the API at the address release 1.0 used, now behind nginx |
| Actor | Driver or dispatcher |
| Preconditions | The stack is running. |
| Request | `GET http://127.0.0.1:8000/api/v1/route/?start=Dallas, TX&finish=Houston, TX`, with `Accept-Encoding: gzip` |

**Main flow**

1. The client sends the request to nginx, the only way in.
2. nginx makes a request ID, overwrites `X-Forwarded-For` with the address it saw, and passes the request on to the API with the client's own `Host`.
3. The API checks the host against `DJANGO_ALLOWED_HOSTS`, then plans the trip as in UC-02.
4. The API's answer carries its security headers, set by Django. nginx compresses it on its way out and adds no security header to it.

**What comes back:** 200, with the body and status of release 1.0. Headers are added, each once: `Content-Encoding: gzip`, `X-Request-ID`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin` and `X-Frame-Options: DENY`. There is no `Access-Control-` header, as the viewer shares the origin, and no redirect to HTTPS or `Strict-Transport-Security`, as the stack is not deployed (D-23).

**Alternative flows**

- A1. The `Host` is not allowed: 400 `invalid_request`, with empty `details`.
- A2. `/api/v1/route` without the slash: the same answer, with no redirect.
- A3. An unknown address: the API's 404 `not_found`, as in release 1.0.
- A4. The API is down, or does not answer within 30 seconds: nginx answers 503 `api_unavailable`, with empty `details`, never an HTML page (D-24).
- A5. nginx refuses the request itself, as malformed or too long: 400 `invalid_request`, with empty `details`.
- A6. An error the API sends itself passes through nginx untouched.
- A7. A file missing under `/assets/`: nginx answers 404 `not_found` in the API's error shape.
- A8. The viewer's files, and the answers nginx writes itself, get the same security headers from nginx.

**Requirements:** NFR-19, NFR-23, D-17, D-21, D-23, D-24

**Test cases:** HM-01, HM-02, HM-03, HM-06, HM-09, HM-10, PX-01 to PX-03, PX-05, PX-06, PX-09 to PX-12, PX-14 to PX-17, CF-18, CF-32

---

## UC-32 Ask again for a trip that another worker planned

| | |
|---|---|
| Goal | Have either worker answer a repeat from the shared cache |
| Actor | Driver or dispatcher |
| Preconditions | The stack is running with Redis. The same trip and stop cost were planned within the last 24 hours, by either worker. |
| Request | `GET /api/v1/route/?start=Dallas, TX&finish=Houston, TX` (again) |

**Main flow**

1. The client sends the request. It reaches one of the two workers.
2. That worker looks for the answer in Redis, under a key that carries the cache's version number, a fingerprint of the station data, both places and the stop cost.
3. It finds it, rebuilds `meta` and answers.

**What comes back:** 200, with `meta.routing_calls` 0 and `meta.cache_hit` true, whichever worker answers.

**Alternative flows**

- A1. Another stop cost: the road is found in Redis, so `routing_calls` is 0 and `cache_hit` false.
- A2. The cache's version number has been raised in the code since: nothing cached under the old number is used, and the trip is routed again.
- A3. The station data has changed since: the answer is made again, from the cached road, with the new prices.
- A4. The API has restarted since: the answer is still found, as Redis outlives the API's processes.
- A5. Two identical new requests arrive at the same moment: both are routed (D-22).
- A6. Redis cannot be reached: UC-33.

**Requirements:** NFR-11, NFR-18, D-15, D-22

**Test cases:** CA-01 to CA-05, CA-18, CA-19, CA-20

---

## UC-33 The service when Redis is down

| | |
|---|---|
| Goal | Keep answering when Redis cannot be reached, and go back to it when it returns |
| Actor | Operator |
| Preconditions | The stack is running. Redis has been stopped. |
| Request | `docker compose stop redis`, then any request, for example `GET /api/v1/route/?start=Dallas, TX&finish=Houston, TX` |

**Main flow**

1. A worker tries Redis for the request and cannot reach it.
2. It falls back to its own memory, for both caches and the rate-limit counters, and logs one warning.
3. It answers. No request fails, or is slowed by more than about half a second, because of Redis: a connection to Redis times out after 0.1 s and a command after 0.25 s, with no retry.
4. For 30 seconds it does not touch Redis. Then it tries again; if that fails, another 30 seconds of fallback start, and nothing new is logged.
5. Redis is started again. At its next try the worker goes back to Redis and logs one line.

**What comes back:** 200 answers, as with Redis. `GET /api/v1/health/` reports `cache` `fallback` from a worker in its fallback, and `redis` once it is back. Each worker logs one warning per outage.

**Alternative flows**

- A1. During the outage a repeat lands on the other worker: it is planned again, with a routing call.
- A2. During the outage each worker counts the rate limit on its own. The limit still holds in each.
- A3. `REDIS_URL` is not set, as when running from source: the cache is the process's own memory, as in release 1.0. Nothing is logged, and health reports `memory`.
- A4. Redis is down when the API starts: the API starts all the same.

**Requirements:** NFR-18, FR-20, D-15, D-16

**Test cases:** CA-06 to CA-13, CA-15, CA-21 to CA-24, CF-07, CF-25, HS-03, HS-04, HS-05

---

## UC-34 Try to escape the rate limit through the proxy

| | |
|---|---|
| Goal | Send more than 60 requests in a minute by giving each a different `X-Forwarded-For`, and be refused all the same |
| Actor | Driver or dispatcher |
| Preconditions | The stack is running. The client has sent 60 requests through nginx in the last minute, each with a different `X-Forwarded-For`. |
| Request | The 61st: `GET http://127.0.0.1:8000/api/v1/route/?start=Dallas, TX` with `X-Forwarded-For: 198.51.100.61` |

**Main flow**

1. The client sends the request.
2. nginx overwrites `X-Forwarded-For` with the address it saw. It does not add to what the client sent.
3. The API trusts exactly one proxy, so it counts the address nginx saw: the same for all 61 requests.
4. It refuses the request before any other work.

**What comes back:** 429 `rate_limited`, with `details.retry_after_seconds` above 0.

**Alternative flows**

- A1. Another client, at another address: it has its own count of 60.
- A2. The client tries to reach the API past nginx: it cannot, as the API has no published port.
- A3. Health requests are never limited (UC-30).
- A4. Both workers share the counts through Redis. While Redis is down each counts on its own (UC-33).

**Requirements:** NFR-16, NFR-19, D-17

**Test cases:** PX-07, PX-08, PX-13, HM-07, HM-08, CA-14, CA-15, CF-05

---

## UC-35 Follow a request through the logs

| | |
|---|---|
| Goal | Find every log line about one request, and the summary of each planned trip |
| Actor | Operator |
| Preconditions | The stack is running. |
| Request | Any request through nginx, then `docker compose logs api` |

**Main flow**

1. nginx makes a request ID and passes it to the API as `X-Request-ID`.
2. The API writes each line about the request with a time, a level and that ID.
3. For every 200, cache hits included, it writes one line at INFO from the logger `trips`, for example `trip start="New York, NY" finish="Los Angeles, CA" stop_cost=10 miles=2800.6 stops=7 total=867.27 routing_calls=1 cache_hit=false own_ms=19.5`.
4. The client receives the ID in the response header `X-Request-ID`.
5. The operator searches the log for it.

**What comes back:** the request's lines, each with its time, level and ID.

**Alternative flows**

- A1. No request ID arrives, as when the API runs from source: the API makes one.
- A2. The client sends its own `X-Request-ID`: nginx replaces it with its own.
- A3. The answer is an error: one line at WARNING with its code and no trip figures.
- A4. `LOG_LEVEL` sets the lowest level written. The default is `INFO`.
- A5. A worker falls back from Redis: one warning. It goes back: one line (UC-33).

**Requirements:** NFR-24, NFR-20

**Test cases:** CF-11, CF-13, CF-14, CF-15, CF-36, PX-04

---

## UC-36 Start the whole stack from a fresh clone

This use case supersedes UC-14 for release 2.

| | |
|---|---|
| Goal | Start the database, Redis, the API and the viewer from nothing, with one command and no account, key or `.env` |
| Actor | Reviewer |
| Preconditions | git and Docker are installed. |
| Request | `git clone <repository>`, then `docker compose up --build`, then `http://127.0.0.1:8000/` and `http://127.0.0.1:8000/api/v1/health/` |

**Main flow**

1. The reviewer clones the public repository into an empty folder.
2. They run `docker compose up --build`.
3. Compose starts `db` and `redis`. `db` counts as healthy once PostgreSQL accepts network connections.
4. `setup` runs once: `migrate`, then `load_stations`, which prints its counts. It exits with code 0.
5. `api` starts: gunicorn, with two workers of four threads. Each worker loads the places, the borders and the stations into memory. `api` counts as healthy once `/api/v1/health/` answers.
6. `web`, nginx with the viewer built in, starts once `api` is healthy.
7. The reviewer opens the viewer and the health address.

**What comes back:** health 200, `{"status": "ok", "stations": 6626, "cache": "redis"}`; the viewer's page at `/`; the API at `http://127.0.0.1:8000/api/v1/route/`, through nginx. Every setting has a default that works, so nothing asks for an account, a key or a `.env`.

**Alternative flows**

- A1. The stack is stopped and started again: `setup` runs again and replaces the table, still 6,626 stations.
- A2. A port is taken: `API_PORT` moves nginx's, `POSTGRES_PORT` the database's and `REDIS_PORT` Redis's. `BIND_ADDRESS` sets the address nginx is published on; the database and Redis stay on 127.0.0.1.
- A3. `setup` fails: `api` and `web` do not start.
- A4. Redis is not running: `api` starts all the same (UC-33).
- A5. The stack is stopped while a request is in flight: the request finishes, for up to 30 seconds.
- A6. Docker is not installed: not supported, as PostgreSQL, Redis and nginx run in Docker.

**Requirements:** NFR-5, NFR-9, NFR-10, NFR-19, NFR-20, NFR-21, NFR-22, NFR-25, D-13, D-21, D-23

**Test cases:** CF-01 to CF-04, CF-06, CF-10, CF-12, CF-16, CF-17, CF-19 to CF-24, CF-26, CF-27, CF-29, CF-30, CF-31, CF-33, HS-19, RP-02

---

## UC-37 Run the checks with make

| | |
|---|---|
| Goal | Run the everyday commands by name, from any of the usual shells |
| Actor | Reviewer |
| Preconditions | A clone, `uv sync` done, GNU make installed, Docker running. |
| Request | `make help`, `make lint`, `make test`, `make up` |

**Main flow**

1. `make help` lists every target with what it does.
2. `make lint` runs Ruff.
3. `make test` runs the suite from source.
4. `make up` starts the stack, as in UC-36.

**What comes back:** each exits with code 0, and the stack answers through nginx.

**Alternative flows**

- A1. Make is not installed: the README gives the plain command beside each target.
- A2. Git Bash, PowerShell or Linux: the same targets work in each.
- A3. `make check` runs lint, the type check and the tests together; `make audit` audits the Python dependencies; `make dev` runs the API from source on port 8001; `make e2e-up`, `make e2e` and `make e2e-down` run UC-39; `make clean` stops everything and deletes the volumes.

**Requirements:** NFR-30, NFR-14, NFR-27

**Test cases:** MK-01 to MK-15, MK-17, MK-18, MK-19, MK-22

---

## UC-38 A push to the repository runs CI

| | |
|---|---|
| Goal | Have every check run on a clean machine for each change, and see at once if one fails |
| Actor | Maintainer |
| Preconditions | The repository is on GitHub, with its workflow. |
| Request | `git push` of a branch, or a pull request |

**Main flow**

1. The maintainer pushes.
2. GitHub Actions runs Ruff's check and format check, the type check, the tests with coverage against its floor, `manage.py check --deploy`, the migration check, the dependency audit, the image build, the end-to-end run, and the viewer's lint, type check, unit tests, build and dependency audit.
3. Every check passes, and the run is green.

**What comes back:** a green run.

**Alternative flows**

- A1. A check fails: the run fails, at that check's step.
- A2. Before a commit, pre-commit runs the lint and format checks: Ruff's checks, Ruff's formatter and the file hygiene hooks.
- A3. Dependabot proposes dependency updates as pull requests, which run CI in turn.

**Requirements:** NFR-17, NFR-21, NFR-26, NFR-27, NFR-28, NFR-31

**Test cases:** CI-01 to CI-07, RP-01, RP-03 to RP-06

---

## UC-39 Run the end-to-end stack with no call to the public routing servers

| | |
|---|---|
| Goal | Drive the whole stack through nginx, as a client and a browser would, without spending a call to the public routing servers |
| Actor | Reviewer |
| Preconditions | Docker is running, and the ordinary stack is stopped. |
| Request | `make e2e-up`, then `make e2e` and the browser tests, then `make e2e-down`; or the same with `docker compose -f docker-compose.yml -f docker-compose.e2e.yml` and Newman |

**Main flow**

1. The second Compose file puts the stand-in routing server, the service `fake-osrm`, in place of the public servers, and the API on a network with no route out. The stand-in runs from the test image, which holds the recordings.
2. The stand-in answers each route request with the recorded road whose ends match it, and keeps a log of the requests.
3. Newman runs the whole Postman collection through nginx; every trip in it has a recording. The live-check cases that have recorded roads run with `--routing-host fake-osrm`, so the verifier accepts the stand-in as the routing server. The viewer's browser tests run.
4. The stand-in's log is compared with the routing calls expected.

**What comes back:** every check passes. The log holds exactly the expected route requests, each matched to a recording. The API reached nothing outside the stack.

**Alternative flows**

- A1. A request whose ends match no recording: the stand-in answers as the real server does when no road exists, the API answers 422 `no_route`, and the run fails at the log check.
- A2. The stand-in is stopped: a new trip gets 502 `routing_unavailable`.

**Requirements:** NFR-26, NFR-13, NFR-15, NFR-17, D-12

**Test cases:** SI-01 to SI-11, EE-01 to EE-07, CF-08, CF-09, CF-34, CF-35, MK-16, MK-20, MK-21, VR-01, VR-02

---

## Traceability

Every requirement and decision in `requirements.md`, with the use cases and tests that cover it. R1 to R17 are the correctness rules in `test-cases.md`, section 4.

### Functional requirements

| ID | Requirement | Use cases | Test cases |
|---|---|---|---|
| FR-1 | Start and finish as place names | UC-01, UC-06 | P01, P10, P11, PL-01 to PL-09, EP-01 |
| FR-2 | Reject unknown or uncovered places before routing | UC-07, UC-08 | N03 to N08, N16, N18, N19, N26, PL-15 to PL-21, EP-15 to EP-18 |
| FR-3 | Driving route with its distance | UC-01 | P01, P06, P07, P09, RT-02, GE-09 |
| FR-4 | GeoJSON map of route and stops | UC-11 | M01, AN-09, EP-01, R11, R12, R13 |
| FR-5 | Each stop's details | UC-01 | P01, AN-08, R5, R6 |
| FR-6 | Lowest bill, with the stop cost | UC-01, UC-03 | P01, P04, FU-01 to FU-21, EX-01, EX-02 |
| FR-7 | No stretch over 500 miles | UC-01, UC-10 | FU-02, FU-12 to FU-16, FU-24, EX-03, EP-25, EP-26, R1, R2, R8 |
| FR-8 | Total cost covers every gallon; reproducible | UC-01, UC-02 | P08, P12, AN-01 to AN-04, R3, R4 |
| FR-9 | Prices exactly as the CSV has them | UC-01, UC-13 | LD-02, LD-06, AN-04, R5 |
| FR-10 | Clear error when no valid plan exists | UC-09, UC-10 | N11, N12, N22, N23, GE-10 to GE-16, FU-12 to FU-14, FU-16, EP-21 to EP-23, EP-25 |
| FR-11 | Errors name the field, suggest names, share one shape | UC-07, UC-15, UC-16, UC-17 | N01 to N05, N09, N10, N13, N14, N17, N20, N21, N24, N25, EP-09 to EP-19, EP-35, EP-36, EP-39 |
| FR-12 | Assumptions in the response | UC-01 | AN-07, R9 |
| FR-13 | Routing calls, cache and timings in the response | UC-01, UC-04 | P01, P02, EP-01, EP-02, EP-40, R15 |
| FR-14 | First fill-up distance, and a warning over 25 miles | UC-05 | P05, P13, P19, LD-18, AN-05, EP-37, R10 |
| FR-15 | Lowest possible bill beside the plan's | UC-03 | P03, FU-22, FU-23, AN-11, R7 |
| FR-16 | Caller sets the stop cost; 0 gives the lowest bill | UC-03 | P03, P04, P15, EP-03, EP-12, EP-27, EX-04, R7 |
| FR-17 | Coordinates as input (Nice) | — | None. Optional, and the architecture gives it no contract. Proven instead by the README listing it as not built; if it is built, its use case and tests are added with it. |
| FR-18 | The viewer: a separate web page at `/?start=…&finish=…&stop_cost=…`; no link in the response | UC-21, UC-22 | VP-12, VP-13, VB-01 to VB-03, VB-25, PX-18, EE-08 |
| FR-19 | OpenAPI document at `/api/v1/schema/` and Swagger page at `/api/v1/docs/` | UC-29 | HS-11 to HS-18 |
| FR-20 | Health endpoint: 200 with stations and cache state, or 503; not rate limited | UC-30 | HS-01 to HS-08, HS-10, HS-19 |
| FR-21 | Viewer: the trip from its address, asked for once; examples with no trip; no form | UC-21, UC-22 | VP-12, VP-13, VP-14, VP-18, VB-25, VB-26 |
| FR-22 | Viewer: the animation, Skip, Replay, the scrubber, cancelling the intro | UC-21 | VT-01 to VT-15, VB-01 to VB-11 |
| FR-23 | Viewer: the panel, each card moving the camera, every figure the API's | UC-21, UC-27 | VP-02 to VP-05, VP-15, VP-16, VP-19, VB-06, VB-12 |
| FR-24 | Viewer: a message per error code, suggestions as links, retry time, API unreachable | UC-23, UC-24, UC-25 | VP-06 to VP-11, VP-18, VB-23, VB-24 |
| FR-25 | Viewer: reduced motion, no WebGL2, built-in outlines | UC-22, UC-26, UC-27, UC-28 | VB-13 to VB-16, VB-29, VB-30 |
| FR-26 | Viewer: the map's sources credited at all times | UC-21, UC-27, UC-28 | VB-14, VB-17, VB-27 |

### Non-functional requirements

| ID | Requirement | Use cases | Test cases |
|---|---|---|---|
| NFR-1 | Our own work adds 100 ms at most | UC-01, UC-03 | S01, S03 |
| NFR-2 | One routing call per new road; at most two; none on repeat | UC-01, UC-03, UC-04, UC-12 | P01 to P04, P14, RT-03 to RT-10, RT-14, EP-02, EP-03, EP-28 to EP-30 |
| NFR-3 | No other external calls | UC-01, UC-07, UC-08 | PJ-03, LD-14, EP-15, EP-18 |
| NFR-4 | Latest stable Django | UC-19 | PJ-01 |
| NFR-5 | Free routing, no key, no secret committed | UC-14 | FC-01, FC-04, RT-01 |
| NFR-6 | Fuel algorithm tested against two exact methods and hand cases | UC-19 | FU-01 to FU-25, EX-01, EX-02 |
| NFR-7 | Stations prepared once; requests read memory | UC-13 | LD-01 to LD-15 |
| NFR-8 | Readable, small modules; 5-minute walkthrough | UC-19 | PJ-02, M03, M04 |
| NFR-9 | One Docker command from a fresh clone, now with Redis and the viewer; README | UC-14, UC-36 | FC-01, CT-01, M02, CF-33, MK-10 |
| NFR-10 | PostgreSQL in Compose, one `DATABASE_URL` | UC-13, UC-14 | PJ-05, CT-01, CT-02, CT-05 |
| NFR-11 | Repeat answered from cache in under 50 ms | UC-04 | P02, S02 |
| NFR-12 | Clear error within about 10 s when routing fails | UC-12 | RT-09, RT-10, RT-11, EP-28, EP-29, S04 |
| NFR-13 | Endpoint, loader and search tests; nothing beyond the local machine | UC-19 | PJ-03, LD-01 to LD-17, CO-01 to CO-17, EP-01 to EP-40 |
| NFR-14 | Ruff passes | UC-19 | FC-03 |
| NFR-15 | Postman collection with checks | UC-20 | PM-01, PM-02 |
| NFR-16 | 60 requests a minute per client, counted by the real client behind the proxy | UC-18, UC-34 | N15, EP-34, PX-07, PX-08, HM-07, HM-08, HS-08, HS-09, CA-14, CA-15 |
| NFR-17 | CI on every push and pull request | UC-38 | CI-01 to CI-07 |
| NFR-18 | Caches and rate-limit counters shared in Redis; each process's memory when Redis is down | UC-32, UC-33 | CA-01 to CA-24, HS-03 to HS-05 |
| NFR-19 | Two workers behind nginx; only nginx published of the two; release 1.0's address still works | UC-31, UC-36 | CF-10, CF-18, CF-32, PX-01, PX-13 |
| NFR-20 | Configuration from the environment, each with a working default; no key in the code; host checking on | UC-35, UC-36 | CF-01 to CF-11, CF-16, CF-20, CF-34, CF-35 |
| NFR-21 | `manage.py check --deploy` passes; each check switched off says why | UC-36, UC-38 | CF-12, CI-03 |
| NFR-22 | Setup once before the API; start order by health checks; a stop lets a request finish | UC-36 | CF-21 to CF-28 |
| NFR-23 | JSON and the viewer's files compressed | UC-31 | PX-02, PX-03 |
| NFR-24 | Log lines with time, level and request ID; one line per planned trip | UC-35 | CF-11, CF-13, CF-14, CF-15, CF-36, PX-04 |
| NFR-25 | Image in stages, holding only what runs, run by a user that cannot write the code | UC-36 | CF-29, CF-30, CF-31, CI-04 |
| NFR-26 | Stand-in routing server; end-to-end run with no route out | UC-39 | SI-01 to SI-11, EE-01 to EE-07, VR-01, VR-02, MK-16, MK-20, MK-21 |
| NFR-27 | Coverage floor, type check, dependency audit; lint and format checks through pre-commit | UC-37, UC-38 | MK-04, MK-08, MK-22, CI-03, RP-04, RP-05 |
| NFR-28 | Viewer: strict TypeScript, lint, unit and browser tests, accessibility scan, keyboard | UC-21, UC-38 | RP-06, CI-06, VB-18, VB-19 |
| NFR-29 | Viewer: work per frame independent of route length; pixel density capped at 2 | UC-21 | VT-12, VB-21, VB-22 |
| NFR-30 | Makefile; `make help`; plain commands in the README | UC-37 | MK-01 to MK-22 |
| NFR-31 | MIT licence for the code; data files keep their terms | UC-38 | RP-01 |

### Decisions

| ID | Decision | Use cases | Test cases |
|---|---|---|---|
| D-1 | Start empty; buy first at the station nearest the start | UC-01, UC-02, UC-05 | P05, P12, P19, LD-16, LD-17, LD-18, AN-08, EP-38, R6 |
| D-2 | The map is GeoJSON in the response; the viewer draws that same GeoJSON | UC-11, UC-21 | M01, AN-09, R11, VP-16 |
| D-3 | City and state, everyday spellings, offline | UC-06, UC-07 | P10, P11, P17, P18, N26, PL-01 to PL-09, PL-20 |
| D-4 | Lower 48 and DC; under 25 miles abroad in a row | UC-08, UC-09 | N06, N07, N08, N11, N18, N19, N22, PL-15, GE-10 to GE-16, EP-21 to EP-23 |
| D-5 | Station at its city centre; 5-mile search; named county for spread places | UC-13 | PL-10 to PL-14, LD-07, CO-02 to CO-05 |
| D-6 | Cheapest listing per station; first row on a tie | UC-13 | LD-02, LD-03, R5 |
| D-7 | Arrive empty | UC-01 | FU-01, FU-05, R3 |
| D-8 | No fuel for detours | UC-01 | AN-01, R3 |
| D-9 | $10 per stop while choosing, never billed | UC-01, UC-03 | P01, P03, P04, P15, FU-07, FU-08, FU-09, FU-11, FU-17, FU-18, EX-02, EX-04 |
| D-10 | Skip a station with a cheaper one within 10 miles; never hide a plan | UC-01, UC-03 | CO-12 to CO-17, EP-26, EP-27 |
| D-11 | Search 5 miles either side | UC-01 | CO-02 to CO-05, AN-07 |
| D-12 | OSRM public server, second server for the retry | UC-12 | RT-01 to RT-14, PJ-04, QB-04, QB-05, QB-06 |
| D-13 | PostgreSQL, holding only the seed data | UC-13, UC-14 | PJ-05, CT-01, CT-05 |
| D-14 | Rounding: miles 0.1, gallons adjusted to sum, cost half-up to cents | UC-01 | AN-01 to AN-04, AN-10, R3, R4, R14 |
| D-15 | Road and answer cached for 24 hours, in Redis, keys with a version and the answer's with a station fingerprint | UC-04, UC-32 | P02, P03, P14, P16, EP-02 to EP-08, CA-01 to CA-05, CA-18, CA-20 |
| D-16 | Redis down: each process answers from its own memory | UC-33 | CA-06 to CA-13, CA-15, CA-21, CA-22, CF-25 |
| D-17 | Through nginx on one origin; `X-Forwarded-For` overwritten; one proxy trusted; no API port | UC-31, UC-34 | PX-07, PX-08, PX-13, PX-16, HM-07, CF-05, CF-18 |
| D-18 | MapLibre globe; NASA night lights, OpenFreeMap, Natural Earth outlines; no key | UC-21, UC-28 | VB-15, VB-16, VB-17, VB-27, VB-28, VB-30 |
| D-19 | The viewer has no form | UC-21, UC-22 | VP-14 |
| D-20 | OpenAPI document from `drf-spectacular`; committed copy checked; Swagger script pinned | UC-29 | HS-15, HS-16, HS-17 |
| D-21 | Host checking on, default hosts; a random secret key when none is set | UC-31, UC-36 | CF-01, CF-02, CF-04, HM-01 to HM-03, PX-15 |
| D-22 | Two identical new requests at once are both routed | UC-32 | CA-19 |
| D-23 | Not deployed: no TLS, HSTS or HTTPS redirect here | UC-31, UC-36 | CF-12, PX-17 |
| D-24 | nginx answers 503 `api_unavailable` when the API is down | UC-25, UC-31 | PX-09, PX-10, VP-11, VB-24 |

### Acceptance checks 11 to 20

Checks 1 to 10 are mapped to their tests in `test-cases.md`, section 8, with these.

| Check | Use cases | Test cases |
|---|---|---|
| 11. Fresh clone: one Compose command starts everything; the API through the proxy, with no port of its own | UC-36 | CF-33, CF-18, CF-21, CF-22, CF-23, PX-01, PX-13 |
| 12. Twenty repeats are all cache hits, whichever worker answers | UC-32 | CA-20, CA-01 |
| 13. Redis stopped: still 200, one warning per worker, health `fallback`; the shared cache returns | UC-33 | CA-21, CA-22, CA-06, CA-10, CA-11, CA-12, HS-04, HS-05 |
| 14. The 61st request in a minute refused, whatever `X-Forwarded-For` says | UC-34 | PX-07, PX-08, HM-07, HM-08 |
| 15. Health 200; the OpenAPI document valid and complete; the Swagger page renders | UC-29, UC-30 | HS-01, HS-19, HS-11 to HS-16, HS-18 |
| 16. `check --deploy` passes; CI green on `main` | UC-36, UC-38 | CF-12, CI-02, CI-07 |
| 17. End-to-end run passes Postman and the browser tests with no route out | UC-39 | EE-03, EE-05, EE-06 |
| 18. The viewer plays New York to Los Angeles to its end, with the API's totals | UC-21 | VB-01, VB-04, VB-05, VB-06 |
| 19. Reduced motion, no WebGL2 and each API error work; no accessibility violation | UC-24, UC-26, UC-27 | VB-13, VB-14, VB-23, VB-24, VP-06, VB-19 |
| 20. `make help`, `make test`, `make lint` and `make up` work | UC-37 | MK-01, MK-05, MK-02, MK-10 |

### Audit rulings with a test

The rulings on the two audits of release 1.0, in `docs/plan/PHASE-9.md`, that call for a test, and the cases that hold it.

| Finding | Ruling | Use cases | Test cases |
|---|---|---|---|
| Q0a-01 | The Postman checks walk the stops | UC-39 | EE-07 |
| Q0a-02 | Published ports on 127.0.0.1 | UC-36 | CF-18, CF-19 |
| Q0a-03 | A foreign `Host` gets 400 in the error shape; `CommonMiddleware` in place with the slash redirect off | UC-17, UC-31 | HM-02, HM-04, HM-05, HM-06 |
| Q0a-04 | Two client addresses get separate rate-limit buckets | UC-34 | HM-07, PX-08 |
| Q0a-06 | Compose passes each variable through; `.env.example` says which process reads which; `API_PORT` added | UC-36 | CF-16, CF-20 |
| Q0a-11 | `pg_isready -h 127.0.0.1`; `restart: unless-stopped` | UC-36 | CF-18, CF-21 |
| Q0a-12 | `.env*` ignored, `.env.example` kept | UC-36 | CF-17 |
| Q0a-15 | The viewer's first card says where its fuel is priced | UC-21 | VP-03 |
| Q0a-21 | Base images pinned by digest | UC-36 | CF-31 |
| Q0a-24 | One compact JSON form | UC-31 | HM-09 |
| Q0a-25 | Eight request slots; the health check outlasts the routing worst case | UC-30, UC-36 | CF-10, CF-28 |
| Q0b-1 | Verifier rule R17: a station stop lies near a place of its city and state, in the places its caller gives | UC-19 | QB-01, QB-02, VR-03, VR-04 |
| Q0b-2 | R12 on the line's own scale, within 0.1 mile | UC-19 | QB-02, QB-03 |
| Q0b-3 | Only a 400 that is not "no road" ends the request; every other answer that is not a readable route goes to the next server | UC-12 | QB-04, QB-05, QB-06 |
| Q0b-4 | Both stop counts taken from the shown gallons | UC-03 | QB-07 |
| Q0b-5 | Every stop after the first buys more than 0 gallons | UC-19 | QB-08, QB-09 |
| N1 | The verifier's description says it does not check that a plan is the cheapest | UC-19 | QB-10 |
| N4 | The deadline's comment corrected | UC-12 | QB-11 |
| N5 | `Mexico, USA` is an unknown place again | UC-08 | QB-12 |
| N7 | Three tests made to check what their names say | UC-03, UC-19 | QB-13, QB-14, QB-15 |
| N8 | A lock around the creation of the HTTP client and of the index | UC-12, UC-13 | QB-16, QB-17 |

The deadline (Friday 20 Nov 2026, 8 pm) is not an FR, NFR or D item. It is proven by M03: the time of the message that sends both links.
