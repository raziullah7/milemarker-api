# Report 15D: documents true of release 2.1.0

Status: done. Nothing committed. Total set to 656 (the coordinator's figure). Coverage left as it was (98.47%, now stated as measured at the close of Phase 11).

## Changes, by finding

- **I1:** `backend-architecture.md` (165: most populous first, then state code; fuzzy over the 748 large places when no state has the name); `use-cases.md` UC-07 A1. **Proved**: `resolve()` run for `Dallas`, `Dalas`, `Springfield, ZZ`, `Chicago`.
- **I2:** `backend-architecture.md` (road-resolve paragraph, cache table Holds, the "Errors are not cached" bullet); `use-cases.md` A5 and UC-03-style A2; `requirements.md` D-15. README line 3 kept. **Proved** against `planner.py` lines 132-140.
- **M5:** architecture steps table (120), 179, 458, 481, 497, 687 (5 s `connect_timeout`); `requirements.md` FR-20 and D-13; `use-cases.md` A3 and health A1; `trips/schema.py` four 503 descriptions plus the health 503 and the `status` help text; `stations/exceptions.py` docstring. `docs/openapi.yaml` regenerated, not hand-edited. **Proved** against `stations/index.py` 66-73.
- **Cache version:** no document stated the number, so nothing changed.
- **M1:** README table row, NFR-16, architecture 313. **Assumed** the figures 60 and 8 from the brief.
- **M2:** architecture HEAD sentence. OpenAPI needed nothing.
- **M3:** README "Known limits".
- **M4:** architecture 257 (180 to 350 ms, no recorded road triggers it).
- **M6:** `development.md` "Things to know". Compose publishes `127.0.0.1:${REDIS_PORT:-6379}:6379` (**proved**).
- **M7:** README "What it assumes".
- **M8:** architecture 497 (the line that mentions the CDN outside parked sections).
- **M9:** README. **Proved**: `planner.py` refuses on `miles_abroad > MOST_MILES_ABROAD`; the brief gives 25.
- **Tests:** `test-cases.md` rows PL-22, PL-23, LD-19, EP-41 to EP-44 (sections 2.2, 2.3, 2.10; these tables have no Actual column, so the test name and Pass are in Expected), HS-22 (9.4), CF-06 extended, the row "A routing failure is not cached" (EP-08), N05 updated to MO, MA, IL, OR, OH. N03 and N04 checked by running `resolve`: unchanged. Section 9: 279 cases, 171 Pass (a tally of the table gives 279; 174 begin with Pass, i.e. 171 plus the 3 Fail rows, as before). Head: 656 tests. README: 656.
- **`scripts/live_check.py`:** no expectation is false; unchanged.

## Searches (outside `docs/plan/`)

- "Errors are not cached", "CACHE_KEY_VERSION = 1": 0 hits.
- "not cached": 5 left, all true (response `meta` not cached; use-case precondition; test comment; EP-08 row; A5, rewritten).
- "about half a second" / "half a second": hits remain about Redis timeouts (NFR-18, architecture 357/359, UC-33, `config/cache.py`) and a limiter test; all true. The M4 one is gone.
- "is refused." : 1 hit, a test docstring; not the border claim. The README line is rewritten.
- "one request a second": 3 left, all say what the routing servers ask (architecture 313, test-cases 332, a `live_check.py` comment); true.
- "an empty table": 3 left in the architecture, now with "or a database that cannot be read"; LD-15 test row describes an empty table; true.
- "states that have it": 2, in the rewritten I1 text.

## Checks

`pytest tests/test_schema.py tests/test_project.py`: 63 passed (includes HS-16, the OpenAPI sync). `ruff check`, `ruff format --check`: clean. `spectacular --validate --fail-on-warn`: no output, exit clean.

## Unsure, settled

- The health sentence on the 503 and the example summary "The station table is empty" in the 503 example are kept: the example is the empty-table case.
- `ruff format` reformatted one long help_text line in `trips/schema.py`; nothing else.
