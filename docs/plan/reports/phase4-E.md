# Phase 4 report: builder 4E, the API

Status: DONE_WITH_CONCERNS. Every test passes and lint is clean. The endpoint meets both speed limits, measured best of five. Four concerns need a ruling, listed in section 5. Concern 5a matters most: on a freshly started server, the first request's `own` is about 290 ms, so live check S01 would fail on P01.

## 1. Files

- `trips/services/planner.py`: implemented `plan_trip`. The signature and docstring are unchanged. It runs the brief's ten steps in order, numbered in comments. Private helpers handle the steps that need more than a few lines: `_fetch_road`, `_plan_with_stop_cost`, `_stops`, `_with_meta`, `_fuel_list`, `_borders` and `_spot`. Two small data classes carry data between them: `_Road`, the road-cache value, and `_FuelList`, the list a plan is chosen from.
- `trips/serializers.py`: `RouteQuery`.
- `trips/views.py`: `RouteView`, plus two plain Django views. `not_found` serves the catch-all and `server_error` is `handler500`.
- `trips/urls.py`: `re_path(r"^api/v1/route/?$")`, then the catch-all `re_path(r"^.*$")`.
- `trips/errors.py`: `STATUS_FOR_CODE` (the architecture's table), `error_body()`, `handler()` and `json_error()`. `handler` gained type hints; its name and parameters are unchanged.
- `config/urls.py`: one line, `handler500 = "trips.views.server_error"`.
- `tests/test_api.py` (new) and `tests/test_planner.py` (new).

No other file was touched. `docs/plan/LEDGER.md` was already modified before I started.

## 2. Test commands and output

My own files:

```
uv run pytest tests/test_api.py tests/test_planner.py -q
....................................................................     [100%]
68 passed in 3.79s
```

Before the implementation, all 66 tests written at that point failed, with 404s and `NotImplementedError`. Two more were added afterwards; see section 4.

The whole suite, as this brief requires:

```
uv run pytest -q
........................................................................ [ 25%]
........................................................................ [ 50%]
........................................................................ [ 75%]
........................................................................ [100%]
288 passed, 1 deselected in 38.16s
```

That is the 220 tests from before this phase plus my 68. The one deselected test is the existing `slow` exactness check.

Lint: `uv run ruff check .` gives `All checks passed!`, and `uv run ruff format --check .` gives `47 files already formatted`.

**Checking that the tests can fail.** I replaced `request.query_params.dict()` with the raw `QueryDict`, and `test_ep13_bad_stop_cost[]` failed: the empty `stop_cost=` quietly became the default. I then restored the line.

## 3. Test-case map

| ID | Test |
|---|---|
| EP-01 | test_ep01_plan_on_the_test_road |
| EP-02 | test_ep02_repeat_comes_from_the_answer_cache |
| EP-03 | test_ep03_new_stop_cost_reuses_the_road |
| EP-04 | test_ep04_stop_cost_is_keyed_to_two_decimals |
| EP-05 | test_ep05_other_spellings_of_the_same_trip_hit_the_cache |
| EP-06 | test_ep06_the_reverse_trip_is_another_trip |
| EP-07 | test_ep07_cached_trips_last_24_hours |
| EP-08 | test_ep08_errors_are_not_cached |
| EP-09 | test_ep09_finish_missing |
| EP-10 | test_ep10_start_empty_or_blank (`""` and `"   "`) |
| EP-11 | test_ep11_no_parameters |
| EP-12 | test_ep12_stop_cost_limits_are_allowed (0, 0.01, 99.99, 100) |
| EP-13 | test_ep13_bad_stop_cost (−0.01, 100.01, 10.555, abc, nan, inf, empty) |
| EP-14 | test_ep14_unknown_parameters_are_ignored |
| EP-15 | test_ep15_unknown_start |
| EP-16 | test_ep16_both_unknown_names_the_start |
| EP-17 | test_ep17_unknown_finish |
| EP-18 | test_ep18_outside_coverage (Honolulu as start, Anchorage as finish) |
| EP-19 | test_ep19_same_place |
| EP-20 | test_ep20_a_road_under_half_a_mile_is_the_same_place |
| EP-21 | test_ep21_detroit_to_buffalo_leaves_the_usa |
| EP-22 | test_ep22_border_limit_is_25_miles |
| EP-23 | test_ep23_border_is_checked_before_the_fuel_plan |
| EP-24 | test_ep24_no_road_between_the_points |
| EP-25 | test_ep25_no_station_for_more_than_500_miles |
| EP-26 | test_ep26_full_list_is_used_when_the_thinned_list_has_no_plan |
| EP-27 | test_ep27_stop_cost_zero_keeps_stations_thinning_would_drop |
| EP-28 | test_ep28_both_servers_fail |
| EP-29 | test_ep29_both_servers_time_out |
| EP-30 | test_ep30_second_server_answers |
| EP-31 | test_ep31_stations_not_loaded_then_loaded_without_a_restart |
| EP-32 | test_ep32_places_are_checked_before_stations |
| EP-33 | test_ep33_unexpected_failure (with DEBUG off and on) |
| EP-34 | test_ep34_rate_limit |
| EP-35 | test_ep35_only_get (POST, PUT, PATCH, DELETE) |
| EP-36 | test_ep36_unknown_address (two addresses × DEBUG off and on) |
| EP-37 | test_ep37_first_fill_station_far_from_the_start |
| EP-38 | test_ep38_tied_start_stations |
| EP-39 | `assert_error()`, called by every error test from EP-08 to EP-36 and S04, plus test_ep39_error_table_matches_the_architecture |
| EP-40 | test_ep40_timings |
| S04 | test_s04_both_servers_too_slow (**uses a shortened deadline**; see section 4) |
| Brief: New York to Los Angeles, default stop cost | test_planner.py::test_new_york_to_los_angeles |
| Brief: the same with stop cost 0 | test_planner.py::test_new_york_to_los_angeles_with_free_stops |
| Brief: Dallas to Houston | test_planner.py::test_dallas_to_houston |
| Brief: Detroit to Buffalo | test_planner.py::test_detroit_to_buffalo_leaves_the_usa |
| Brief: Seattle to Miami | test_planner.py::test_seattle_to_miami |
| Brief: a road that fails the border check is not cached | test_a_road_that_leaves_the_usa_is_not_cached |
| Brief: `routing_server` is remembered with the cached road and answer | test_routing_server_is_remembered_with_the_road_and_the_answer |
| Brief: the trailing slash is optional | test_trailing_slash_is_optional |
| Brief: a JSON `handler500` | test_handler500_answers_in_the_standard_body |

**Rules checked on every 200 in `test_api.py`.** The helper `assert_sound()` checks these rules on every successful response:

- R1 range, R2 tank, R3 gallons, R4 money
- R6 stops, R7 lowest bill, R8 stop count, R15 meta
- the key order

It is not the verifier of the next phase, only the rules these cases lean on. Each case then asserts its own expected figures.

**EP-39.** `assert_error()` checks every error response. It checks that:

- the body has exactly one key, `error`;
- `error` has exactly `code`, `message` and `details`, in that order;
- the status is the one the architecture's table gives the code;
- the message is non-empty text;
- `details` is an object holding exactly the keys the code's row lists, and none for codes that list none.

All 12 codes are produced by at least one test.

## 4. Differences from the brief or the documents

- **S04 uses a shortened deadline.** The brief says to do this. The deadline is 0.2 s instead of 5 s, both fake servers drip their body for about a second, and the limit is 1 s instead of 11 s. The test asserts 502 `routing_unavailable`, reason `timeout`, exactly 2 requests, in under 1 second.
- **The view gives the serializer a plain dict** (`request.query_params.dict()`), not the `QueryDict`. When DRF reads a `QueryDict`, it treats an optional parameter sent empty as absent. That would turn `stop_cost=` into the default, against the brief. The `Field.get_value` source confirms it, and the mutation in section 2 proves it. With a repeated parameter, the last value wins.
- **EP-34 uses the configured rate**, 60 a minute, with no override. The brief points at R1 section C for how to set a rate. The case is about the shipped limit, though, and 61 requests take well under a second, so I tested the real setting. The test also checks that the `Retry-After` header equals `retry_after_seconds`.
- **`Retry-After`.** DRF's `Throttled` already rounds `wait` up with `math.ceil`. The handler uses that whole number for both the body and the header, so the two always agree.
- **Fakes reused, not copied.** `test_api.py` imports `Fake`, `slow` and `timeout` from `tests/test_routing.py`. They are not in `conftest.py`, but copying them would break the "import, do not copy" rule.
- **EP-14** clears the cache between the two requests. Otherwise the second request would be an answer-cache hit, and the comparison would prove nothing.
- **EP-22** also clears the cache between its two requests. The road that passed at 25.0 miles is cached, and a cached road skips the border check.
- **EP-33** also runs with DEBUG on, and checks that the failure is logged with its traceback.
- **EP-20, the "same place" error after the routing call,** reports against `finish` with the same sentence as step 2, as the brief says.
- **Messages.** The error messages for validation, rate limit, wrong method, unknown address and internal error are my own sentences. The documents give none. The validation message names the bad parameters.
- **Timings.**
  - The clock starts when `plan_trip` is entered. Checking the parameters, which takes microseconds, is therefore not counted.
  - `routing` and `total` are rounded first, and `own` is `round(total − routing, 1)`. The three always add up, and `own` is never negative.
  - On a cache hit, `routing` is 0.0.
- **Test road.** The test road lies along 35° N, but the request is Dallas to Houston. Stop 1 is therefore drawn at Dallas while the other stops sit on the line further north, as the test data in docs/test-cases.md section 2.1 implies. Rules R6 and R12 still hold.
- **Extra tests.** Four tests cover requirements the brief states but no EP case pins down. They are listed in section 3.

## 5. Unclear, contradictory or needing a ruling

**a. Cold start, and live check S01 (the important one).** S01 measures P01 on a freshly started server. The best-of-five figures in section 7 are well inside the limits. The very first request in a fresh process, however, pays costs measured in the scratch scripts. Two of them fall inside `meta.timings_ms.own`:

- reading the places table: 228 ms
- loading the station index from PostgreSQL: 42 ms
- reading the borders file: 2 ms

So P01's `own` comes out at about 290 ms, over the 100 ms limit.

One more cost falls outside `own` but inside the round trip. Django imports the URL configuration lazily, at the first request, and that pulls in scipy.spatial (606 ms), numpy (190 ms) and DRF: about 1.0 s in all (`python -X importtime`).

Possible fixes, none of them in my files:

- warm the process at start-up: import `trips.urls` and read the places table in an `AppConfig.ready()` or a gunicorn hook. The station index cannot be loaded there, because of `migrate`;
- have `scripts/live_check.py` send one warm-up request first;
- or state in the documents that S01 is measured on a warm server.

**b. `no_fuel_plan` details are not rounded.** EP-25 answers `"gap_miles": 502.9999970484523`. On a real road it will be a similar long float. The brief says the `NoFuelPlan` from `fuel.py` is exactly the error to report, and `fuel.py` is not mine, so I passed it through unchanged. EP-25's ±0.1 tolerance passes. If the error should read cleanly, the fix is to round both figures to 1 decimal in `fuel._require_plan`. The message text already shows them rounded. `miles_abroad` has no such problem: it is always a whole number of 2-mile samples.

**c. A client that will not accept JSON gets a 500.** A request with `Accept: text/html` alone, and no `*/*`, makes DRF raise `NotAcceptable`. The brief's table sends that to "anything else": 500 `internal_error`, logged with a traceback. That reports a client choice as our own failure. Browsers, curl and Postman all send `*/*`, so they are unaffected. I followed the table. If wanted, there are two remedies:

- a content-negotiation class on `RouteView` that always picks JSON (one class attribute and about 5 lines);
- or a new error code, which would mean changing the architecture's table.

`ParseError`, `UnsupportedMediaType` and `PermissionDenied` would also go to 500, but a GET with our settings cannot raise them.

**d. Place labels on a cache hit.** Architecture section 10 says labels "come from the current request's lookup". The answer cache is keyed by coordinates, as the brief says, so a hit returns the labels it was stored with. These differ only if two labels share coordinates to 4 decimals. I checked all 29,323 places: exactly one pair does, `Ackermanville, PA` and `Flicksville, PA` at (40.8648, −75.2073). For that pair, a trip cached under one name would be labelled with the other, and a trip between the two counts as "the same place". I left it as the brief specifies. Adding both labels to the answer key would fix it, if it matters.

## 6. Not sure is right

- **`stop_cost=-0` is accepted.** DRF reads it as `Decimal("-0.00")`, which is ≥ 0, so it is valid. The plan is then the free-stops plan, as it should be. Two small oddities follow:
  - `assumptions.stop_cost` renders as `-0.0`;
  - the answer-cache key is `-0.00` rather than `0.00`, so `stop_cost=-0` misses the cached answer for `stop_cost=0`.

  It is harmless, and I added no handling. Normalising the value in the serializer would be one line.
- **The serializer's default** is `settings.DEFAULT_STOP_COST`, read once when the module is imported. A test that changes the setting at run time would not see the change. No test does.
- **`_borders()` is cached with `functools.cache`**: read once per process, as the brief says. Two threads could both read the file on the very first request. That is harmless.
- **OPTIONS and HEAD** are left to the framework's defaults, as the architecture says. OPTIONS answers 200 with DRF's metadata, which includes the view's docstring as `description`. HEAD answers 200 with no body.
- **New York to Los Angeles on the recorded road.** The answer covers 2,800.7 miles with 7 stops. The total is 867.29, and the lowest possible is 855.97 with 18 stops. The first fill-up is 3.1 miles from the start. The design figures were 865.93, 854.65 and 17 stops. My totals are 0.16% higher, inside the 2% the live case P01 allows.

## 7. Speed

**How measured.** New York to Los Angeles on the recorded road (`nyc_la`), with the real 6,626 stations held in memory. The stations were built exactly as the `real_index` fixture builds them, and a fake `fetch_route` returned the recorded road. Each request went through `django.test.Client` to `/api/v1/route/`. The figure taken is `meta.timings_ms.own`, best of five, on this machine. For a new trip the cache was cleared before each run. The script lived in the scratchpad and is not committed.

| Case | own, best of 5 | The five runs (ms) | Limit |
|---|---|---|---|
| New trip | **16.8 ms** | 17.0, 16.8, 17.0, 18.0, 17.8 | 100 ms |
| Only the stop cost changed (road cached), `stop_cost=0` | **9.1 ms** | 9.1, 9.2, 9.3, 9.1, 9.2 | (S03: 100 ms) |
| The same with `stop_cost=25` | 15.1 ms | 15.3, 66.0, 15.1, 15.1, 15.2 | (S03: 100 ms) |
| Repeated (answer cached) | **1.0 ms** | 1.0, 1.0, 1.1, 1.1, 1.1 | 50 ms |

The best round trips through the test client, JSON writing included, were:

- new trip: 20.8 ms
- stop cost changed: 13.1 ms (18.9 ms at a stop cost of 25)
- answer cached: 4.8 ms

All of these are for a warm process. Section 5a gives the first-request costs.

## Review round 1

The coordinator settled concerns 5a to 5d and the `-0` oddity of section 6 with five fixes. Four are done exactly as asked. Fix 3 is done with one change of wiring, because the instructed wiring is a circular import; see below.

`uv run pytest -q`:

```
294 passed, 1 deselected in 29.74s
```

My two files now hold 74 tests: 66 in `tests/test_api.py` and 8 in `tests/test_planner.py`. `uv run ruff check .` gives `All checks passed!`, and `uv run ruff format --check .` gives `47 files already formatted`.

### Fix 1: cold start (concern 5a)

- **`trips/services/planner.py`** has a new public `warm_up()`. It loads four things in turn:
  - the places table, by one lookup;
  - the border outlines, through `_borders()`;
  - the URL configuration, with `import_module(settings.ROOT_URLCONF)`. Its `include()` imports the views and, through them, scipy;
  - the station index, with `get_index()`.

  If `get_index()` raises `StationsNotLoaded` (an empty table) or Django's `DatabaseError` (no database, or no table before `migrate`), it logs one warning line naming the error class and returns. Nothing is raised.
- **`config/wsgi.py`** calls `warm_up()` right after `application = get_wsgi_application()`. Its comment says why it is there. It also says that only a server goes through this file, and that other `manage.py` commands and the tests do not. The comment names gunicorn **and `manage.py runserver`** as the servers, because `runserver` loads `WSGI_APPLICATION` too. The import sits below the application with `# noqa: E402`, because importing the planner needs Django set up first.
- **Tests** in `tests/test_planner.py`:

  | Test | What it checks |
  |---|---|
  | `test_warm_up_leaves_nothing_for_the_first_request` | Loads the real CSV into the test database, then forgets the places table, the border outlines and the index, as a new process would. Then it runs `warm_up()` and one `plan_trip` on the recorded New York to Los Angeles road. That trip makes **0 database queries** (`django_assert_num_queries(0)`) and reports `own` ≤ 100 ms. |
  | `test_warm_up_with_no_stations_loaded_raises_nothing` | Empty table: nothing raised, one log line naming `StationsNotLoaded`. |
  | `test_warm_up_with_no_database_raises_nothing` | `get_index` replaced by one that raises `OperationalError`: nothing raised, one log line. |

  A mutation check: with the `get_index()` call removed from `warm_up()`, all three fail. The code was then restored, and `cmp` confirmed it matches the backup byte for byte.
- **Measured in fresh processes.** New York to Los Angeles, recorded road, the development database's 6,626 stations (read only). The first request goes through `django.test.Client`.

  | Start-up | Start-up time | First request `own` | First request round trip |
  |---|---|---|---|
  | `import config.wsgi`, with warm-up (3 runs) | 2,351 to 2,987 ms | **18.9, 19.4, 20.9 ms** | 25 to 28 ms |
  | `django.setup()` only, no warm-up (2 runs) | 1,014 to 1,050 ms | 326.5, 326.9 ms | 1,072 to 1,077 ms |

  The warm-up moves about 1.3 s from the first request to start-up. P01 on a freshly started server should now meet S01.
- **Note for the Dockerfile phase.** `warm_up()` opens one database connection in the thread that imports `wsgi.py`. If gunicorn runs with `--preload`, that is the master process, and the forked workers would inherit the open connection. Without `--preload`, each worker warms itself up and nothing is shared. I recommend not using `--preload`. I added no code for it.

### Fix 2: rounded details (concern 5b)

`trips/exceptions.py`:

- `NoFuelPlan` stores `gap_start_mile` and `gap_miles` rounded to 1 decimal.
- `RouteLeavesUSA` stores `miles_abroad` rounded to 1 decimal.

The docstrings say so. `fuel.py` still finds the gap with exact miles; only what the caller reads is rounded. EP-25 now asserts `details == {"gap_start_mile": 0.0, "gap_miles": 503.0}` exactly. `tests/test_fuel.py` passes unchanged: its gaps are already whole tenths, and it compares with `approx`.

### Fix 3: always JSON (concern 5c), with one deviation

- **`trips/views.py`** has a new class, `AlwaysJSON(BaseContentNegotiation)`. It picks the first parser and the first renderer, and settings make JSON the only renderer.
- **Deviation.** It is attached as `RouteView.content_negotiation_class`. It is **not** named in `REST_FRAMEWORK` as `DEFAULT_CONTENT_NEGOTIATION_CLASS`.
  - **The instructed wiring fails.** DRF's `APIView` reads that setting in its class body (`rest_framework/views.py`, line 113), so the setting is read the moment `rest_framework.views` is first imported. The first module to import it is `trips/views.py`. DRF then imports `trips.views` while that module is still half-initialised.
  - **I tried it, and EP-01 failed** with: `AttributeError: partially initialized module 'trips.views' has no attribute 'AlwaysJSON' (most likely due to a circular import)`.
  - **I reverted `config/settings.py`**, which is unchanged from the commit.
  - `RouteView` is the only REST framework view. The catch-all and `handler500` already answer with plain JSON, so the behaviour is the same as the settings route would give.
  - **If the setting is wanted** anyway, the class must live in a module that does not import `rest_framework.views`, for example `trips/errors.py` or a new module.
- **Test**, `test_any_accept_header_gets_json`, sends `Accept: text/html` and checks two answers:
  - the trip answers 200 with `Content-Type: application/json` and a sound body;
  - a request missing `finish` answers the standard 400 `invalid_request` body.

### Fix 4: labels in the answer key (concern 5d)

`plan_trip` now keys the answer cache as:

```
answer:<start lat,lng>;<finish lat,lng>:<start label>;<finish label>:<stop cost>
```

The road key is still the coordinates only. Each label is percent-encoded with `urllib.parse.quote`. Labels hold spaces, and Django's cache warns about spaces in keys (`CacheKeyWarning`, which the in-memory backend checks too). Encoding also keeps two different labels from ever making the same key.

The test is `test_places_sharing_coordinates_keep_their_own_labels`. It replaces `planner.resolve` so that `Alpha, TX` and `Beta, TX` are two `Place` objects at Dallas's coordinates, then plans a trip from each. The Beta trip:

- shows `Beta, TX` in the summary and `Start: Beta, TX` on the map;
- has `cache_hit` false, so it is a different answer;
- has `routing_calls` 0, so it is the same road.

### Fix 5: minus zero (section 6)

`RouteQuery.validate_stop_cost` returns `abs(value)`. `-0` passes the minimum of 0 and becomes 0; every other allowed value is left as it is. The test is `test_stop_cost_minus_zero_is_zero`:

- `stop_cost=-0` shows `assumptions.stop_cost` as `0.0`;
- after a request with `stop_cost=0`, a request with `-0` is an answer-cache hit.

### Files changed in this round

- `trips/services/planner.py`: `warm_up()`, its logger and imports, and the answer key
- `trips/exceptions.py`
- `trips/views.py`
- `trips/serializers.py`
- `config/wsgi.py`
- `tests/test_api.py`
- `tests/test_planner.py`: the `recorded_road` fixture no longer pulls in the real stations. Each real-data test now requests `use_real_stations` itself, because the warm-up test must read the stations from the database instead. An autouse fixture resets the station index around every test in the file.
- this report

`config/settings.py` was edited for Fix 3 and then reverted, so it is unchanged.
