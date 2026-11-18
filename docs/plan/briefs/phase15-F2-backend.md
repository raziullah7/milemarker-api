# Brief 15F2: cache the refusals; 503 when the database is down

The Mile Marker API (Django) answers `GET /api/v1/route/` by resolving two places, loading the station index, making one routing call per new road, and planning fuel stops. Roads and answers are cached for 24 hours, in Redis or in memory.

The repository root is `F:\Spotter-AI\milemarker-api`. Every path below is relative to it.

## Bug 1, I2 (proved)

`trips/services/planner.py` caches the road (`cache.set(road_key, ...)`, around lines 114-119) only after `_fetch_road` (around 206-227) returns. It raises before that point in three cases, so each repeat of those trips makes a fresh routing call:

- The road runs abroad for more than `MOST_MILES_ABROAD` miles in a row. This raises `RouteLeavesUSA`, with `miles_abroad`.
- The routing server says there is no road. `trips/services/routing.py` raises `NoRoute` on `NoRoute`/`NoSegment` answers below 500.
- The road is shorter than `SHORTEST_TRIP_MILES`. This raises `InvalidRequest(SAME_PLACE, ...)`.

Proved: Detroit to Buffalo sent 3 times makes 3 calls, and so do the other two cases. See `C:\Users\Bakemono\AppData\Local\Temp\claude\a83fc35170f12650\2174297b-dd78-49b7-8d5b-a766fb1b748a\scratchpad\proof\b\repo\tests\test_proof_b.py`. `README.md` line 3 says "a repeat costs none".

**The fix (decided):**
- Cache the refusal under the same road key, for the same `settings.TRIP_CACHE_SECONDS`, as plain data, never as a pickled exception (exceptions with keyword-only constructors do not unpickle reliably).
- Shape: a module-level frozen dataclass, for example `_Refused(kind: str, miles_abroad: float | None)`. Store the unrounded `miles_abroad`, because the message formats it with `.0f` and the detail rounds it to 0.1.
- A cache hit on a refusal raises the same error. Its status and body must be byte-for-byte what the first request got.
- One key holds either a `_Road` or a `_Refused`, so there is no second cache read. Keep the code flat and short.

**Must not change:**
- A routing failure (`RoutingUnavailable`, a timeout or 5xx) is never cached. EP-08 (`test_ep08_errors_are_not_cached`) pins this.
- `NoFuelPlan` behaviour.
- Every successful response.

**Tests:**
- `test_a_road_that_leaves_the_usa_is_not_cached` (`tests/test_api.py`, about line 778) becomes a test that the refusal is cached: one routing call for two requests, and identical bodies.
- Add the same test for no road and for a road under half a mile, and use the stand-in fixtures for all three.
- Keep EP-08 and its ID.
- Name each new test with an ID that continues its section, and list the IDs in your report. The documents agent adds them to `docs/test-cases.md`.

## Bug 2, M5 (proved)

With the database unreachable, `/api/v1/route/` and `/api/v1/health/` answer 500 `internal_error` and log a traceback. The cause: `stations/index.py` `get_index()` lets `DatabaseError` escape to the catch-all in `trips/errors.py`. On Windows, running from source, psycopg also hangs on a refused port, because no `connect_timeout` is set. See `...\scratchpad\proof\b\m5_dbdown.py` (same folder as above).

**The fix (decided; the ruling is in `docs/plan/PHASE-15.md`):**
- `get_index()` turns a `DatabaseError` into the existing `StationsNotLoaded`, which is 503 `stations_not_loaded` with `details` `{}`. Use a message that says the database could not be reached, chained with `from`.
- Nothing is remembered, so the next request tries again.
- Log one warning line naming the error type, not a traceback.
- `config/settings.py`: give the default database a `connect_timeout` of 5 seconds through `OPTIONS`. A `?connect_timeout=` in `DATABASE_URL` must still win.
- `warm_up()` already catches both errors. Keep `test_warm_up_with_no_database_raises_nothing` passing.

**Tests:**
- Both addresses answer 503 `stations_not_loaded` when the station query raises `OperationalError` (patch it, as the existing tests do).
- A later request succeeds once the database answers.
- The settings default carries `connect_timeout` 5, and a URL parameter overrides it (extend CF-06 in `tests/test_project.py`, or add a test beside it).

## Also: the cache version

In `config/settings.py`, set `CACHE_KEY_VERSION` from 1 to 2. The project's rule (`docs/development.md`) is to raise it when the shape of a cached value changes, which bug 1 does. Fix any test that pins the number.

## Rules

- **You own only:** `trips/services/planner.py`, `stations/index.py`, `config/settings.py`, `tests/test_api.py`, `tests/test_planner.py`, `tests/test_health.py`, `tests/test_index.py`, `tests/test_project.py`.
- If you believe another file must change, for example `trips/services/routing.py` or `trips/schema.py`, stop and say so in your reply rather than editing it.
- **Do not edit any document.** A later agent does that. In your report, list the doc lines that state the old behaviour.
- **Another agent edits `stations/places.py` and `tests/test_places.py` at the same time. Do not touch them.**
- **Database:** use `DATABASE_URL=postgresql://milemarker:milemarker@127.0.0.1:5432/milemarker_f2` for pytest.
- **Tests to run:** your test files, plus `tests/test_answer.py`, `tests/test_regression.py`, `tests/test_verify.py` and `tests/test_routing.py`.
- **Never run `tests/test_cache.py` or the full suite.** Both use the shared Redis database 15, so the controller runs them.
- **Static checks:** `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`.
- **Forbidden:** any request to a routing server; starting or stopping a container; any git command that changes anything; subagents.
- **Style:** write plainly, in full sentences with common words. Match the existing code style, including the numbered-step comments in `plan_trip`.

## Report: `docs/plan/reports/phase15-F2.md`

Keep it under a page:
- What changed, file by file.
- The new test IDs.
- Each claim marked **proved** (with the command and the decisive output) or **assumed**.
- The doc lines that are now out of date.

Reply with: status, the files changed, the test counts, and any concern.
