# Brief 4E: the API

Read `docs/plan/briefs/phase3-common.md` first. Its rules apply in full, with one difference: you are the only builder now, so nobody else is editing files, and at the end you **do** run the whole suite (`uv run pytest -q`), not just your own tests.

## Goal

Join the finished modules into `GET /api/v1/route/`: check the request, plan the trip, cache it, and answer in JSON. Every error, from anywhere, leaves in one shape.

## Your files

- `trips/services/planner.py`
- `trips/views.py`, `trips/serializers.py`, `trips/urls.py`, `trips/errors.py`
- `config/urls.py`: only to name a JSON `handler500`
- `tests/test_planner.py`, `tests/test_api.py`
- Report: `docs/plan/reports/phase4-E.md`

You may add fixtures to your own test files. Do not edit `tests/conftest.py`; if you need something shared there, say so in your report.

## Read

- `docs/backend-architecture.md` sections 2, 3, 5, 8 (the last four subsections), 10 and 11
- `docs/test-cases.md` sections 2.1 and 2.10, the row S04 in section 5, and section 4 (rules R1 to R16, which every 200 must satisfy)
- Every module you call, including its tests, so you use each as its tests do: `stations/places.py`, `stations/index.py`, `stations/types.py`, `trips/services/routing.py`, `geo.py`, `corridor.py`, `fuel.py`, `answer.py`, and both `exceptions.py` files
- `config/settings.py`
- `tests/conftest.py`: `load_road`, `load_road_answer`, `real_index`, `use_real_stations`, `SMALL_CSV`
- `docs/plan/reports/phase1-R1-stack.md` section C: tested facts about Django REST Framework's exception handler, throttling in tests, and how numbers render

## Test cases

EP-01 to EP-40 in `tests/test_api.py`, exactly as `docs/test-cases.md` gives them, and S04. In `tests/test_planner.py`, the checks on real data listed at the end of this brief.

## `plan_trip(start_text, finish_text, stop_cost)`: the steps, in this order

Nothing that can be known before the routing call may be raised after it.

1. `start = resolve(start_text, "start")`, then `finish = resolve(finish_text, "finish")`. Start first, so when both are bad the error names `start`.
2. **Same place.** If both have the same latitude and longitude to 4 decimals: `InvalidRequest("Start and finish are the same place.", fields={"finish": [that sentence]})`.
3. **Answer cache.** Key: both coordinate pairs to 4 decimals plus the stop cost to 2 decimals. On a hit, return the cached body with a fresh `meta`.
4. **Stations.** `index = get_index()` (raises `StationsNotLoaded` if empty), then `nearest_station(index, start.lat, start.lng)` gives the start station and the first-fill distance.
5. **The road.** Key: both coordinate pairs to 4 decimals. On a miss:
   - `route = routing.fetch_route((start.lat, start.lng), (finish.lat, finish.lng))`. Call it through the module (`from trips.services import routing`), so tests have one place to replace it.
   - `distance_miles = round(route.distance_miles, 1)`. If it is under 0.5, raise the same `InvalidRequest` as step 2: the two places are one.
   - `road = resample(route.coords, distance_miles)`.
   - `longest_run_abroad(road, borders)`: if over 25.0, raise `RouteLeavesUSA(message, miles_abroad=...)`. Read the borders file once per process from `settings.BORDERS_FILE`.
   - Only then store (road, distance_miles, server) in the road cache. A road that fails the border check is not cached.
6. **Stations along the road.** `along = stations_along(road, index, exclude=start_station)`. The lists for the fuel routines begin with the start: mile 0.0 at the start station's price, then each candidate's mile and price.
7. **The free-stops plan.** `cheapest_fuel` on every station. It raises `NoFuelPlan` if no plan exists, which is exactly the error to report.
8. **The plan.**
   - Stop cost 0: the plan is the free-stops plan from step 7.
   - Otherwise: `thin(along)`; if `find_gap` finds no gap in the thinned list, `plan_stops` on the thinned list; if it finds one, `plan_stops` on every station.
9. **The answer.** Turn each purchase into a `Stop`: the first is the start station drawn at the start place, mile 0.0; each other is its candidate's station, drawn at the road point `candidate.point`. Pass the free-stops plan as (exact price, gallons) pairs. Use each station's exact price, `index.info[k].price`, never the float copy.
10. Store the body in the answer cache, add `meta`, return.

**`meta`** is built for every response and never cached: `routing_calls` (0, 1 or 2), `cache_hit` (true only when the body came from the answer cache), `routing_server` (the host that supplied the road, remembered with the cached road and answer), and `timings_ms` with `routing`, `own` and `total`, each rounded to 1 decimal. `routing` is the time inside `fetch_route`, 0 when it was not called; `own` is `total − routing`.

Both caches use Django's cache (`django.core.cache.cache`) with `settings.TRIP_CACHE_SECONDS`. A `RoadPoints` holds numpy arrays; the in-memory cache pickles values, which works.

Keep `plan_trip` readable as a list of steps. Put each step that needs more than a few lines in a small private function with a name that says what it does.

## The view

- `RouteView(APIView)` with `get()`. Read `request.query_params` through a serializer: `start` and `finish` are required, trimmed, and may not be blank; `stop_cost` is an optional `DecimalField(max_digits=5, decimal_places=2, min_value=Decimal("0"), max_value=Decimal("100"))`, default `settings.DEFAULT_STOP_COST`. Unknown parameters are ignored. An empty `stop_cost=` is an error, not the default.
- The view calls `plan_trip` and returns `Response(body)`. Nothing else.
- Addresses: `re_path(r"^api/v1/route/?$", ...)`, so the trailing slash is optional, then a catch-all `re_path(r"^.*$", ...)` to a plain Django view that answers 404 `not_found` in the standard body. Neither may depend on `DEBUG`.

## Errors: `trips/errors.py`

One function builds the body `{"error": {"code": ..., "message": ..., "details": {...}}}`. One table maps each code to its status, exactly as architecture section 11 lists them. `handler(exc, context)` handles, in this order:

| Raised | Status and code | Details |
|---|---|---|
| A `MileMarkerError` | from the table, by `exc.code` | `exc.details` |
| DRF `ValidationError` | 400 `invalid_request` | `{"fields": {parameter: [messages]}}` |
| DRF `Throttled` | 429 `rate_limited` | `{"retry_after_seconds": whole seconds, rounded up}`. Keep the `Retry-After` header |
| DRF `MethodNotAllowed` | 405 `method_not_allowed` | `{}` |
| DRF `NotFound`, Django `Http404` | 404 `not_found` | `{}` |
| Anything else | 500 `internal_error` | `{}`. Log the exception with its traceback (`logger.exception`). The message says only that something went wrong |

The handler must return a response for **every** exception, so an unexpected failure is JSON whatever `DEBUG` is. Also give `config/urls.py` a JSON `handler500`, for failures outside the REST framework.

## Notes for the tests

- **Replace the routing call** with `monkeypatch.setattr(routing, "fetch_route", fake)`, where `fake` returns a `Route` and counts its calls. For the cases about the two servers failing (EP-28 to EP-30) and S04, drive the real `fetch_route` through a client on `httpx.MockTransport` instead, by replacing `routing._shared_client`, so the retry really runs.
- **The test road** of section 2.1: build its coordinates directly (latitude 35° N, eastward from 110° W, the length the case names) and return it in a `Route` with that `distance_miles`. A station "at mile m" sits on that line m miles along. Create stations as `FuelStation` rows and call `reset_index()` before and after, so the index is read fresh.
- **Throttling** (EP-34): see R1 section C for how to set the rate in a test. Other tests must not be throttled: the shared `_empty_cache` fixture clears the counters before each test.
- **EP-07** needs the clock moved. The in-memory cache reads `time.time()`; patch it where that backend reads it.
- **EP-36** runs with `settings.DEBUG` both true and false.
- **S04:** set the deadline to 0.2 seconds and give both fake servers a slow-drip body, as `tests/test_routing.py` does for RT-11, and check the endpoint answers 502 `routing_unavailable` with reason `timeout` in under 1 second. Say in your report that the test uses a shortened deadline.
- Every 200 must satisfy rules R1 to R16. A separate, independent verifier is written in the next phase; you do not write it. Do assert the rules that matter to each case.

## Checks on real data: `tests/test_planner.py`

Use `use_real_stations` and a fake `fetch_route` that returns a recorded road from `load_road`.

- New York to Los Angeles (`nyc_la`), default stop cost: fewer than 10 stops; no stretch between stops or to the finish over 500 miles; gallons equal distance ÷ 10; the total equals the sum of the stop costs; `lowest_possible_fuel_cost` is not above the total; the first stop is the start; no station appears twice.
- The same with stop cost 0: `total_fuel_cost` equals `lowest_possible_fuel_cost`, and there are more stops than at the default.
- Dallas to Houston (`dal_hou`): a valid plan with a cost above zero.
- Detroit to Buffalo (`det_buf`): `RouteLeavesUSA` with `miles_abroad` within 2% of 252.
- Seattle to Miami (`sea_mia`): a valid plan with fewer than 12 stops.

## Speed

Put in your report, best of five on this machine, `meta.timings_ms.own` for New York to Los Angeles on the recorded road with the real stations: once as a new trip, once with only the stop cost changed (road cached), once repeated (answer cached). The first must be 100 ms or less and the last 50 ms or less. If the first is not, say where the time goes; do not change the other modules.
