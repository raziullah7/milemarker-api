# Report 15F2: cache the refusals; 503 when the database is down

Status: done. Nothing committed.

## What changed

- `trips/services/planner.py`: a new frozen dataclass `_Refused(kind, message, miles_abroad=None)`. `_fetch_road` returns one in place of raising for a road under half a mile and for one that leaves the USA. `plan_trip` step 6 turns `NoRoute` into one. The road key holds a `_Road` or a `_Refused`, cached for `TRIP_CACHE_SECONDS`, and a `_Refused` is raised through `_refusal()`. The first answer and every repeat are therefore built by the same code. `RoutingUnavailable` is still raised before anything is cached. I updated two docstrings that my change had made untrue (`health`, `warm_up`).
- `stations/index.py`: `get_index()` catches `DatabaseError` around the station query. It logs one WARNING, `The stations could not be read (OperationalError).`, with no traceback, and raises `StationsNotLoaded("The database could not be reached, ...") from error`. Nothing is remembered.
- `config/settings.py`: `OPTIONS` gets `{"connect_timeout": 5}`, merged under any options from `DATABASE_URL`, so the URL wins. `CACHE_KEY_VERSION` goes from 1 to 2. No test pinned the old number.
- Tests: `test_api.py`, `test_health.py`, `test_index.py`, `test_project.py`. `test_a_road_that_leaves_the_usa_is_not_cached` is replaced by EP-41. `test_planner.py` is unchanged and still passes.

One change from the brief's example shape: `_Refused` also stores `message`. `NoRoute`'s text lives in `trips/services/routing.py`, which I may not edit. Without this field I would have had to copy that sentence into the planner.

## New test IDs

| ID | Test |
|---|---|
| EP-41 | `test_api.py::test_ep41_a_road_that_leaves_the_usa_is_refused_from_the_cache`: one routing call for two requests, the same status and bytes; still cached at 23 h 59 min, routed again after 24 h |
| EP-42 | `test_api.py::test_ep42_no_road_is_refused_from_the_cache` (stand-in transport, one request) |
| EP-43 | `test_api.py::test_ep43_a_road_under_half_a_mile_is_refused_from_the_cache` |
| EP-44 | `test_api.py::test_ep44_a_database_that_cannot_be_reached_is_503_until_it_answers`: 503 with `details` `{}`, no traceback logged, no routing call; then 200 |
| HS-22 | `test_health.py::test_hs22_a_database_that_cannot_be_reached_is_503_until_it_answers` |
| LD-19 | `test_index.py::test_ld19_a_database_that_cannot_be_reached_is_stations_not_loaded`: chained cause, one WARNING naming `OperationalError` with no `exc_info`, then the index loads |
| CF-06 | Extended, same ID: the default carries `connect_timeout` 5; `?connect_timeout=2` in the URL gives 2 |

## Claims

- **Proved**, tests first: the 7 new or changed tests failed on the old code (`assert 2 == 1` calls; `500 == 503`; `OPTIONS` `None`). They pass now.
- **Proved**: the brief's set of tests, with `DATABASE_URL=...milemarker_f2` and `uv run pytest tests/test_api.py tests/test_planner.py tests/test_health.py tests/test_index.py tests/test_project.py tests/test_answer.py tests/test_regression.py tests/test_verify.py tests/test_routing.py -q`, gives `311 passed` (306 before). EP-08 and `test_warm_up_with_no_database_raises_nothing` pass. `ruff check`: `All checks passed!`. `ruff format --check`: `68 files already formatted`. `mypy`: `Success`.
- **Proved**, I2: the proof's own `test_proof_b.py`, unchanged, run on the new code with `uv run pytest -c pyproject.toml --rootdir=. -s -q -k i2 <scratchpad>\f2proof\test_proof_b.py`. It prints `LEAVES routing calls: 1`, `NOROUTE requests at fake: 1`, `SAMEPLACE requests at fake: 1` for 3 requests each.
- **Proved**, M5, live against a closed port: `<scratchpad>\f2proof\m5_f2.py` ran with `DATABASE_URL` on `127.0.0.1:5999` and no `connect_timeout` in it. Output: `OPTIONS: {'connect_timeout': 5}`; health and route each `503 stations_not_loaded`, `(5.0s)`, twice each, so every request tries again; one `stations.index` WARNING per request and no traceback. `warm_up` returned after 5.4 s.
- **Proved**: the tests pickle `_Refused` on every write and read. `LocMemCache` pickles each value (`django/core/cache/backends/locmem.py` lines 28 and 43).
- **Assumed**: the same holds on Redis. I did not run `test_cache.py`, as the brief says.

## Doc lines now out of date

- `docs/backend-architecture.md:333`: "Errors are not cached ... Only a road refused for leaving the USA, and a routing call that failed, are asked for again". Now only a routing failure is asked for again.
- `docs/backend-architecture.md:327`: the Road row's "Holds" column. It now holds the road, or the refusal.
- `docs/backend-architecture.md:458` and `:481`: the 503 row and the health text say only "not run" or "an empty table". Add: or the database cannot be reached.
- `docs/backend-architecture.md:687`: the `DATABASE_URL` row could give the 5-second `connect_timeout` default.
- `docs/use-cases.md:225`, A5: "errors are not cached". Now only routing failures are not cached.
- `docs/test-cases.md:438`: "Errors are not cached | EP-08". Also `:551` CF-06, and the new rows above.
- `docs/requirements.md:149`, D-15: the road cache also holds refusals. This is an addition, not a falsehood.
- `README.md:3`, "a repeat costs none": this is now true.

## Concerns

1. Three places outside my files still describe 503 only as an empty table: `trips/schema.py` lines 452, 458, 739 and 860; `docs/openapi.yaml` lines 493-494, 812 and 841, which are generated from `schema.py` and pinned by HS-16; and the `StationsNotLoaded` docstring at `stations/exceptions.py:50`. Changing them needs someone who owns `schema.py`, then the document regenerated. I did not edit them.
2. While the database is down, each request waits up to 5 s before its 503. This happens only until a worker's index is loaded; after that, requests never touch the database.
3. When the server starts with the database down, it logs two warnings: one from `get_index`, and the existing one from `warm_up`.
4. `get_index` catches any `DatabaseError`, as the brief asks. A missing table (`ProgrammingError`) therefore also says "could not be reached". The log line names the real error type.
