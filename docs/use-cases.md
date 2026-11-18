# Mile Marker API: Use Cases

What the API does for the people who use it, step by step, and which tests prove each part.

Requirement IDs (FR, NFR, D) refer to `requirements.md`. Test IDs refer to `test-cases.md`. Field names, error codes and status codes are those of `backend-architecture.md`, section 11. Query strings are shown unencoded. "≈" marks a figure measured on real roads while the API was designed; a test passes within 2% of it.

Every successful response is also checked against the correctness rules R1 to R16 in `test-cases.md`, section 4. The use cases below do not repeat that.

## Actors

| Actor | Who | Uses |
|---|---|---|
| Driver or dispatcher | Plans a truck trip and wants to know where to buy fuel and what it will cost | Any HTTP client: Postman, a browser, curl, an application |
| Operator | Installs and runs the service, and loads the station data | `manage.py`, Docker Compose |
| Reviewer | Checks the project: runs it from a clone, runs the tests, tries the requests | git, Docker, uv, Postman |

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
| Preconditions | The same start, finish and stop cost were planned within the last 24 hours by the same server process. |
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

- A1. A map page served by the API (FR-18) is optional and not specified; it is tested only if built.

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
2. The tests run with no network: a fixture blocks every connection except the local database.
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
| Preconditions | The API is running and freshly started. |
| Request | Import the collection from `docs/`, set `base_url` to the API's address, run it; or `npx newman run <collection> --env-var base_url=<API address> --delay-request 1200` |

**Main flow**

1. The reviewer opens or runs the collection.
2. The requests run in three folders: the demo trip and its cache and stop-cost variants, more trips, and errors.
3. Each request's own checks run on its response.

**What comes back:** every check passes; Newman exits with code 0.

**Alternative flows**

- A1. The API was not freshly started: the first request may report a cache hit, and its routing-call check fails. Restart the API and run again.

**Requirements:** NFR-15

**Test cases:** PM-01, PM-02

---

## Traceability

Every requirement and decision in `requirements.md`, with the use cases and tests that cover it. R1 to R16 are the correctness rules in `test-cases.md`, section 4.

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
| FR-18 | Map page (Nice) | — | None, for the same reason as FR-17. |
| FR-19 | OpenAPI documentation (Nice) | — | None, for the same reason as FR-17. |

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
| NFR-9 | One Docker command from a fresh clone; README | UC-14 | FC-01, CT-01, M02 |
| NFR-10 | PostgreSQL in Compose, one `DATABASE_URL` | UC-13, UC-14 | PJ-05, CT-01, CT-02, CT-05 |
| NFR-11 | Repeat answered from cache in under 50 ms | UC-04 | P02, S02 |
| NFR-12 | Clear error within about 10 s when routing fails | UC-12 | RT-09, RT-10, RT-11, EP-28, EP-29, S04 |
| NFR-13 | Endpoint, loader and search tests; nothing beyond the local machine | UC-19 | PJ-03, LD-01 to LD-17, CO-01 to CO-17, EP-01 to EP-40 |
| NFR-14 | Ruff passes | UC-19 | FC-03 |
| NFR-15 | Postman collection with checks | UC-20 | PM-01, PM-02 |
| NFR-16 | 60 requests a minute per client | UC-18 | N15, EP-34 |
| NFR-17 | CI (Nice) | UC-19 | FC-05, only if built. If not built, the README says so. |
| NFR-18 | Shared cache (Nice) | — | None: needed only with several processes. CT-04 shows the API runs as one process, so every repeat is a cache hit. |

### Decisions

| ID | Decision | Use cases | Test cases |
|---|---|---|---|
| D-1 | Start empty; buy first at the station nearest the start | UC-01, UC-02, UC-05 | P05, P12, P19, LD-16, LD-17, LD-18, AN-08, EP-38, R6 |
| D-2 | The map is GeoJSON in the response | UC-11 | M01, AN-09, R11 |
| D-3 | City and state, everyday spellings, offline | UC-06, UC-07 | P10, P11, P17, P18, N26, PL-01 to PL-09, PL-20 |
| D-4 | Lower 48 and DC; under 25 miles abroad in a row | UC-08, UC-09 | N06, N07, N08, N11, N18, N19, N22, PL-15, GE-10 to GE-16, EP-21 to EP-23 |
| D-5 | Station at its city centre; 5-mile search; named county for spread places | UC-13 | PL-10 to PL-14, LD-07, CO-02 to CO-05 |
| D-6 | Cheapest listing per station; first row on a tie | UC-13 | LD-02, LD-03, R5 |
| D-7 | Arrive empty | UC-01 | FU-01, FU-05, R3 |
| D-8 | No fuel for detours | UC-01 | AN-01, R3 |
| D-9 | $10 per stop while choosing, never billed | UC-01, UC-03 | P01, P03, P04, P15, FU-07, FU-08, FU-09, FU-11, FU-17, FU-18, EX-02, EX-04 |
| D-10 | Skip a station with a cheaper one within 10 miles; never hide a plan | UC-01, UC-03 | CO-12 to CO-17, EP-26, EP-27 |
| D-11 | Search 5 miles either side | UC-01 | CO-02 to CO-05, AN-07 |
| D-12 | OSRM public server, second server for the retry | UC-12 | RT-01 to RT-14, PJ-04 |
| D-13 | PostgreSQL, holding only the seed data | UC-13, UC-14 | PJ-05, CT-01, CT-05 |
| D-14 | Rounding: miles 0.1, gallons adjusted to sum, cost half-up to cents | UC-01 | AN-01 to AN-04, AN-10, R3, R4, R14 |
| D-15 | Road and answer cached for 24 hours | UC-04 | P02, P03, P14, P16, EP-02 to EP-08 |

The deadline (Friday 20 Nov 2026, 8 pm) is not an FR, NFR or D item. It is proven by M03: the time of the message that sends both links.
