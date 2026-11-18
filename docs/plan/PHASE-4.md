# Phase 4: The API

Baseline: `PLAN.md`, Phase 4. One builder joins the finished modules into the endpoint.

## Inputs from Phase 3

Every module below is finished, tested and committed. Phase 4 calls them and changes none of them.

| Module | Gives |
|---|---|
| `stations/places.py` | `resolve(text, field) -> Place` |
| `stations/index.py` | `get_index()`, `nearest_station(index, lat, lng)` |
| `trips/services/routing.py` | `fetch_route(start, finish) -> Route` |
| `trips/services/geo.py` | `resample()`, `load_borders()`, `longest_run_abroad()` |
| `trips/services/corridor.py` | `stations_along()`, `thin()` |
| `trips/services/fuel.py` | `find_gap()`, `plan_stops()`, `cheapest_fuel()` |
| `trips/services/answer.py` | `Stop`, `build_answer()` |

Measured in Phase 3: re-spacing 1.9 ms, border check 1.8 ms, station search 2.3 ms, fuel plan 5 ms. The limit for all our own work is 100 ms.

## Task

| ID | Builder | Model | Owns | Test cases |
|---|---|---|---|---|
| 4E | The API | Opus | `trips/services/planner.py`, `trips/views.py`, `trips/serializers.py`, `trips/urls.py`, `trips/errors.py`, one line in `config/urls.py`, `tests/test_planner.py`, `tests/test_api.py` | EP-01 to EP-40, S04 |

Brief: `briefs/phase4-E-api.md`. Report: `reports/phase4-E.md`.

## Gate 4 checklist

- [x] The controller has read the diff.
- [x] `uv run pytest` passes in full, run by the controller; Ruff is clean.
- [x] Every error code in the architecture's table is produced by a test, in the standard body.
- [x] A repeat makes no routing call, and neither does the same trip with a different stop cost.
- [x] On the recorded New York to Los Angeles road with the real stations: fewer than 10 stops, no stretch over 500 miles, our own work 100 ms or less.
- [x] The controller starts the server and makes the first live call, New York to Los Angeles: fewer than 10 stops, total within 2% of $866.
- [x] Committed.

## Result

Closed 18 Nov 2026. Every gate item passed.

### Gate evidence

Run or measured by the controller.

| Gate item | Evidence |
|---|---|
| Diff read | `planner.py`, `views.py`, `serializers.py`, `urls.py`, `errors.py`, `config/wsgi.py` and the changed exceptions read in full |
| Full suite and lint | `uv run pytest`: 294 passed. `ruff check` and `ruff format --check`: clean. `manage.py check`: no issues |
| Every error code in the standard body | EP-08 to EP-39 |
| No routing call on a repeat or a new stop cost | EP-02 to EP-04, and live: see below |
| Recorded New York to Los Angeles road, real stations | 7 stops; own work 16.8 ms as a new trip, 9.1 ms with the road cached, 1.0 ms with the answer cached (builder's figures, best of five) |
| First live call | See below |

### The first live calls

Server started with `manage.py runserver`, stations loaded, real OSRM server, 18 Nov 2026.

| Request | Result |
|---|---|
| New York, NY to Los Angeles, CA | 200. 2,800.6 miles, **7 stops, $867.27**. Lowest possible $855.95 with 19 stops. First fill-up 3.1 miles away. 1 routing call. Routing 2,646 ms, our own work **19.4 ms**. Body 120 KB |
| The same again | 200. Answer cache hit, 0 routing calls, own work 1.1 ms, round trip 39 ms |
| The same with `stop_cost=0` | 200. 19 stops, $855.95, equal to the lowest possible. 0 routing calls (the road was cached), own work 11.0 ms |

The stops of the first call: Jersey City NJ (start, 39.21 gal), Youngstown OH, Utica IL, Henderson NE, Keenesburg CO, Green River UT, North Las Vegas NV. The first stop checks by hand: 39.21 gallons at $3.239 is $127.00.

The design figure was $865.93. The finished API scales its mile markers to the routing service's distance, which accounts for the difference of 0.15%.

### Review

One round. The builder raised all five points itself.

| Point | Decision |
|---|---|
| The first request on a fresh server spent about 290 ms of our own time loading the places table and the stations | `warm_up()` loads them, the border outlines and the views when the server starts. First request after start-up: 19 to 21 ms. Start-up takes 2.4 to 3.0 seconds |
| `no_fuel_plan` showed `502.9999970484523` miles | Miles in error details are rounded to 1 decimal, in the exception classes |
| A client accepting only HTML got a 500 | `RouteView` always answers in JSON. The class is set on the view, not in settings: naming it in settings is a circular import |
| Two places share coordinates, so a cached answer could carry the other's label | Both labels are in the answer cache key |
| `stop_cost=-0` | Treated as 0 |

### Deviations

- S04 runs with the deadline shortened to 0.2 seconds, so the suite does not wait 10 seconds. The full deadline is exercised live.
- The lowest possible bill is now computed on every station, so the live figure is 19 stops and $855.95, not the design's 17 stops and $854.65 from the thinned list.

### Carried into Phase 5

- `warm_up()` opens a database connection at start-up. In Phase 6, gunicorn must not be run with `--preload`.
- The catalogue's design figures for New York to Los Angeles ($865.93, $854.65, 17 stops) should be replaced by the measured ones once the verifier has passed them.
- The server for live checks is `uv run python manage.py runserver 127.0.0.1:8000 --noreload`.
