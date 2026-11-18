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

- [ ] The controller has read the diff.
- [ ] `uv run pytest` passes in full, run by the controller; Ruff is clean.
- [ ] Every error code in the architecture's table is produced by a test, in the standard body.
- [ ] A repeat makes no routing call, and neither does the same trip with a different stop cost.
- [ ] On the recorded New York to Los Angeles road with the real stations: fewer than 10 stops, no stretch over 500 miles, our own work 100 ms or less.
- [ ] The controller starts the server and makes the first live call, New York to Los Angeles: fewer than 10 stops, total within 2% of $866.
- [ ] Committed.

## Result

(Filled in when the phase closes.)
