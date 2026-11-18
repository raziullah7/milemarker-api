# Mile Marker API

Give it a start and a finish in the USA and it returns the driving route, the fuel stops along it, and what the fuel will cost. The stops are chosen for the lowest fuel bill that does not waste stops, and a new trip costs one call to a routing service.

## Run it

You need git and Docker. There is no API key and no account.

```bash
git clone https://github.com/raziullah7/milemarker-api.git
cd milemarker-api
docker compose up --build
```

Wait for the line `Listening at: http://0.0.0.0:8000`. Just above it the log shows the station loader finishing with `Saved: 6626`. Then, from another terminal, send the example below. If port 8000 or 5432 is taken, set `API_PORT` or `POSTGRES_PORT` before starting.

## Example

```bash
curl "http://127.0.0.1:8000/api/v1/route/?start=New%20York,%20NY&finish=Los%20Angeles,%20CA"
```

The response, shortened:

```json
{
  "summary": {
    "start": {"label": "New York, NY", "lat": 40.74838, "lng": -73.99671},
    "finish": {"label": "Los Angeles, CA", "lat": 33.97309, "lng": -118.2479},
    "distance_miles": 2800.6,
    "gallons": 280.06,
    "total_fuel_cost": 867.27,
    "stops": 7,
    "lowest_possible_fuel_cost": 855.95,
    "lowest_possible_stops": 19,
    "first_fill_distance_miles": 3.1
  },
  "warnings": [],
  "assumptions": {
    "range_miles": 500, "miles_per_gallon": 10, "tank_gallons": 50,
    "starting_fuel_gallons": 0, "stop_cost": 10.0, "search_radius_miles": 5
  },
  "fuel_stops": [
    {"order": 1, "kind": "start", "station_id": 72087, "name": "DELTA", "address": "US-9",
     "city": "Jersey City", "state": "NJ", "mile_marker": 0.0, "lat": 40.74838, "lng": -73.99671,
     "price_per_gallon": 3.239, "gallons": 39.21, "cost": 127.0},
    {"order": 2, "kind": "station", "station_id": 72445, "name": "SHEETZ #639",
     "address": "I-80 Exit 223", "city": "Youngstown", "state": "OH", "mile_marker": 392.1,
     "lat": 41.1487, "lng": -80.67643, "price_per_gallon": 3.059, "gallons": 46.17, "cost": 141.23},
    "…"
  ],
  "map": {"type": "FeatureCollection", "features": ["…"]},
  "meta": {"routing_calls": 0, "cache_hit": true, "routing_server": "router.project-osrm.org",
           "timings_ms": {"routing": 0.0, "own": 1.2, "total": 1.2}}
}
```

This meta is from a repeat of the request. On a fresh start, the first request reports `routing_calls` 1 and `cache_hit` false.

- `start` and `finish` are required: a city and state such as `Dallas, TX`. Spellings like `Dallas TX`, `Dallas, Texas` and `st. louis, mo` work. Street addresses and ZIP codes do not.
- `stop_cost` is optional, from 0 to 100, default 10. It is what a stop is worth in dollars when the plan is chosen (see D-9). `stop_cost=0` returns the lowest possible fuel bill, with as many stops as that takes.

To see the trip on a map, copy the response's `map` value into [geojson.io](https://geojson.io).

## How it works

1. `trips/serializers.py` checks that the input has the right shape.
2. `stations/places.py` looks both places up in an offline table. Nothing is geocoded over the network.
3. `trips/services/planner.py` rejects a trip whose two ends are the same place, and returns the cached answer if this trip was planned in the last 24 hours.
4. `stations/index.py` holds all 6,626 stations in memory and finds the one nearest the start.
5. `trips/services/routing.py` gets the road. This is the only network call, and it is cached.
6. `trips/services/geo.py` gives the road a point every half mile, each with a mile marker (its distance from the start), and rejects a road that runs through Canada or Mexico.
7. `trips/services/corridor.py` finds the stations within 5 miles of the road and drops any that a cheaper one nearby makes pointless.
8. `trips/services/fuel.py` chooses the stops and `answer.py` builds the response.

The fuel plan rests on two moves. At a stop, if the next stop is no dearer, buy just enough to reach it. If the next stop is dearer, fill the tank. That leaves one question: which stops to make. Dynamic programming answers it. Fuel alone would favour 19 stops on this trip, the first for about half a gallon, so each stop is charged $10 while the plan is chosen. The $10 is never added to the fuel bill. The result is checked against two exact methods: a linear-programming solver and brute force over every subset of stations. See [`docs/backend-architecture.md`](docs/backend-architecture.md) for the rest.

## What it assumes

The task left these open. Each is decided in [`docs/requirements.md`](docs/requirements.md), section 6, with the measurement behind it.

| ID | Question | Decision |
|---|---|---|
| D-1 | Fuel in the tank at the start? | None. The first fill-up is priced at the listed station nearest the start, as stop 1 at mile 0. |
| D-2 | What is a map? | The route and stops as GeoJSON in the response. No page is served. |
| D-3 | What is a location? | City and state, from an offline table of 29,880 US places. No street addresses or ZIP codes. |
| D-4 | What is within the USA? | The lower 48 states and DC. A road running over 25 miles in a row through Canada or Mexico is rejected. |
| D-5 | Where is a station? | At the centre of its city. On the route if within 5 miles of the road. |
| D-6 | Several prices for one station? | The cheapest listing. |
| D-7 | Fuel left at the finish? | None. |
| D-8 | Does a detour use fuel? | No. Stations count as on the route. |
| D-9 | How many stops are too many? | Each stop is charged $10 when the plan is chosen, never added to the bill. |
| D-10 | Which stations are worth considering? | One is skipped if another within 10 miles along the route is cheaper, or as cheap and earlier. Nothing is skipped at `stop_cost=0`. |
| D-11 | How wide is the search? | 5 miles either side of the road. |
| D-12 | Which routing service? | The OSRM public server, with a second server for one retry. No key. |
| D-13 | Which database? | PostgreSQL, holding only the seed data. Requests do not read it. |
| D-14 | Rounding? | Miles to 0.1. Gallons as a running total to 2 decimals. Each cost to cents. The total is the sum of the costs. |
| D-15 | What is cached? | The road, and the finished answer, each for 24 hours. |

## Errors

Every error has the body `{"error": {"code", "message", "details"}}`.

| Status | Code | When |
|---|---|---|
| 400 | `invalid_request` | A parameter is missing, empty or malformed, or both ends are the same place |
| 400 | `unknown_place` | A place is not in the table (up to 5 suggestions) |
| 404 | `not_found` | No such address |
| 405 | `method_not_allowed` | Anything but GET |
| 422 | `outside_coverage` | A place in Alaska, Hawaii, Puerto Rico, Canada or Mexico |
| 422 | `route_leaves_usa` | The road runs through Canada or Mexico |
| 422 | `no_route` | The routing service finds no road |
| 422 | `no_fuel_plan` | A stretch of more than 500 miles with no station listed |
| 429 | `rate_limited` | More than 60 requests a minute from one client |
| 500 | `internal_error` | Anything unexpected |
| 502 | `routing_unavailable` | Both routing servers failed or timed out |
| 503 | `stations_not_loaded` | The loader has not run |

## Speed

Measured on the finished API for New York to Los Angeles, the largest trip tried, with the API run from source and the real routing server (18 Nov 2026). "Our own work" excludes the routing call. The limit is 100 ms.

| Request | Our own work |
|---|---|
| A new trip | 19.5 ms |
| The same trip again | 1.1 ms (23.6 ms round trip; limit 50) |
| The same trip, another `stop_cost` | 11.0 ms (31.7 ms round trip) |

The routing call took 2,646 ms on the first live request.

## Tests

463 tests, plus one slow test that runs with `-m slow`. No test reaches beyond this machine. The kinds:

- **Unit:** places, distance, geometry, station search, fuel plan, answer builder, routing client.
- **Exactness:** the fuel plan against a linear-programming solver (400 random trips) and against brute force over every subset of stations (250 trips).
- **Integration:** the loader, the station index and the endpoint, with PostgreSQL and a fake routing service.
- **Independent verifier:** `tests/verify.py` checks 17 rules on every successful response. It imports nothing from the API.
- **End to end:** `scripts/fake_osrm.py` stands in for the routing server, answering from recorded real roads, so the whole stack and the Postman collection run with no call to the internet. CI does this on every push.
- **Live:** `scripts/live_check.py` runs 49 cases against a running server. Last run, 18 Nov 2026: 49 passed.

```bash
docker compose --profile test run --rm test        # in a container
docker compose up -d db && uv sync && uv run pytest   # from source
uv run python scripts/live_check.py                # live cases, against a server on port 8000
npx newman run docs/postman/milemarker.postman_collection.json --env-var base_url=http://127.0.0.1:8000 --delay-request 1200
```

The live cases call the public routing server, so run them against a freshly started API. The last command runs the Postman collection under Newman; you can also import it into Postman.

To run the collection without the public routing server, start the stack with the stand-in:

```bash
docker compose -f docker-compose.yml -f docker-compose.e2e.yml up --build -d
npx newman run docs/postman/milemarker.postman_collection.json --env-var base_url=http://127.0.0.1:8000
docker compose -f docker-compose.yml -f docker-compose.e2e.yml down
```

With GNU make, `make help` lists these and the other everyday commands as targets: `make up`, `make test`, `make lint`, `make e2e-up`, `make e2e`, and so on. Each target runs one of the plain commands shown in this file.

## Run from source

Needs Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
docker compose up -d db
uv sync
uv run python manage.py migrate
uv run python manage.py load_stations
uv run python manage.py runserver 127.0.0.1:8000 --noreload
```

Restart the server after reloading the stations. `.env.example` lists the settings, all optional.

## Project layout

| Folder | What is in it |
|---|---|
| `config/` | Django settings, URLs, WSGI entry |
| `stations/` | Station model, places table lookup, in-memory index, the `load_stations` command |
| `trips/` | The endpoint, and `services/` with the planner, routing client, geometry, station search, fuel plan and answer builder |
| `data/` | The fuel CSV, the places table, border outlines |
| `docker/` | The container's start-up script |
| `scripts/` | `live_check.py` |
| `tests/` | The test suite and recorded roads |
| `docs/` | The documents below |

## Known limits

- Station positions are city centres, a median 2.8 miles from the real station, and there is no reserve on the 500-mile range.
- Some roads have no fuel listed, such as Interstate 5 through California. Los Angeles to Seattle has no plan, and the API says so.
- Routing is for cars, not trucks, and the free routing servers promise no uptime.
- An attempt on a slow routing server can run to about twice its 5-second deadline.
- Two identical new requests arriving together both call the routing server.
- The cache is per process, so the API runs as one process.
- Border outlines are coarse: a road along the border can register up to 10 miles abroad.

## Documents

| File | What is in it |
|---|---|
| `docs/requirements.md` | What the API must do, and the decisions D-1 to D-15 |
| `docs/prd.md` | The product in one page |
| `docs/backend-architecture.md` | How it is built and why |
| `docs/use-cases.md` | Who uses it and how |
| `docs/test-cases.md` | Every test case, with the results of the live run |
| `docs/postman/` | The Postman collection |
| `docs/plan/` | The build plan, phase by phase, with the result of each phase |

## Data and licences

The fuel prices are the file supplied with the task. Places come from the MIT-licensed `kelvins/US-Cities-Database`, and border outlines from Natural Earth, which is public domain. Test roads are from OpenStreetMap contributors. Sources and licences are in [`data/README.md`](data/README.md).
