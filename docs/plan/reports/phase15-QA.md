# QA-5: release 2.1.0, `b3d3bef..5cd97c0`

Independent reviewer (Opus), read-only. It worked in two clean exports, the new commit and `v2.0.0`, with its own test database and Redis database 13, which was empty before and after. It made no routing call and used no container. The harness refused its own write of this file, so the controller saved it from its reply, condensed where noted, with the controller's rulings at the end.

## 1. The old proofs, run on the new code

| ID | What the proof shows now | |
|---|---|---|
| I1 | The 50 largest cities with no state: 50 get their own state first, up from 42. The reviewer took its own list straight from the census file (SUMLEV 162, the lower 48 and DC); it matches PL-22's 50. `Dallas` gives TX, GA, IA, NC, OR. `Dalas` gives `Dallas, TX` and `Houstan` gives `Houston, TX`. | proved |
| I2 | Three requests make 1 routing call each for leaves-USA, no road and same place. Through Redis database 13, a second process made 0 calls, and its answers matched the first's in status and bytes. Each first answer is byte-identical to `v2.0.0`'s. | proved |
| M5 | Health and route both answer 503 `stations_not_loaded`. With the 5-second `connect_timeout` default the 503 comes after 5.3 s. A URL's own `connect_timeout` wins, and other URL options are kept. | proved |
| M1 | 61 requests in 0.85 s: 60 answers and one 429. The 8 concurrent requests follow from the unchanged gunicorn configuration (2 workers × 4 threads). | 60 proved, 8 assumed |
| M2 | HEAD gives 200 with no body after one routing call. The GET that follows is a cache hit. Architecture line 467 says so. | proved |
| M3 | The longest leg is 499.8 miles. Chosen stops are at most 4.87 miles from the road. README line 98 says so. | proved |
| M4 | None of the 15 recorded roads triggers the fallback; 1 of 209 random trips does. It took 154 to 338 ms over two runs, so the documented "180 to 350 ms" has the wrong lower bound. | partly proved |
| M6 | PING with no password succeeds, and `requirepass` is empty. `docs/development.md` says so. | proved |
| M7 | Los Angeles to New York: stop 1 is drawn at the start and named after the Coachella station 120.6 miles away. The README says so. | proved |
| M8 | The docs page loads 3 files from the CDN, none with an `integrity` attribute. The architecture says so. | proved |
| M9 | A run of 10 or 22 miles through Canada answers 200; a run of 28 miles answers 422. The README says so. | proved |

## 2. Findings

**Critical:** none.

**Important**

1. **A misspelling with no state can put a bigger, worse match first** (`stations/places.py:228-229`). The close matches are re-sorted by population alone.
   - Examples: `Orlndo` gives `Portland, OR` before `Orlando, FL`. `Minnepolis` puts Indianapolis first. `Lexigton` puts Arlington, TX first. `Tacma` puts Tampa first.
   - Over 621 single-letter slips of large-place names, the intended city came first in 424 (68%).
   - Keeping `difflib`'s own order (closest first), with population ordering only the states that share one name, put it first in 580 (93%). `Dalas` and `Houstan` are unchanged.
   - Proved, and the controller confirmed it on the repository.

**Minor**

2. **The version still says 2.0.0**: `pyproject.toml`, the OpenAPI version in `config/settings.py`, `docs/openapi.yaml` and `uv.lock`. Proved.
3. **N05's Actual records a run that never happened** (`docs/test-cases.md`). The column holds the live run of 18 Nov, but the row was changed to the new order taken from `resolve()`. Proved.
4. **The measured fallback time is 154 to 338 ms**, not "180 to 350 ms" (architecture line 257). Proved.

**Notes**

5. **A latent KeyError.** `places.py:231` raises KeyError on a misspelling once `use_cities_file()` has switched the table. It cannot happen through the API: 35,253 fuzzed inputs on the shipped table raised only the two expected errors, and all 748 keys are in the table.
6. **Failing connects queue behind the index lock while the database is down.** Each queued request waits once more per earlier failure: with a 2 s timeout, waits of 2, 4, 6 and 8 s. This happens only before a worker has loaded its stations. Proved.
7. **`django.db.InterfaceError` is not a `DatabaseError`.** Plausible only.
8. **Start-up with the database down logs two warnings.** Each 503 logs two WARNING lines (`stations.index` and `trips.errors`), but architecture line 179 says "one warning is logged". The `DatabaseError` clause of `warm_up` can no longer be reached in production.
9. **A no-road answer is now kept for 24 hours.** It comes from the first server without asking the second. `docs/development.md` mentions emptying the cache after changing the routing servers, but only for roads.
10. **Documentation nits.**
    - `data/README.md` says the file is "used only" for ranking, but it is also the list misspellings are matched against.
    - Architecture line 165 should say "incorporated places". CDPs and townships are not in the list: `Arlington` ranks VA by state code, and Edison, NJ comes fourth.
    - PL-23 says `Dalas` is timed, but the test times `Houstan`.
    - The coverage figure at the head of `test-cases.md` is from Phase 11.

**Clean:**
- The 9 new test IDs fail on `v2.0.0` and pass now, and no assertion was weakened.
- `CACHE_KEY_VERSION` 2 is needed and complete: `v2.0.0` cannot unpickle a `_Refused`.
- The extract script regenerates the committed file byte for byte. All 12 hand mappings are right, and none of the 51 skipped places has another spelling in its state.
- A no-state lookup takes 2.4 to 5.0 ms (median).
- The OpenAPI document is in sync, the parked sections are untouched, and no false old claim remains.

## 3. Not checked by QA-5

QA-5 could not check the following. The controller ran all of them: the full suite, `test_cache.py`, the live API, Postman, CI, Ruff and mypy. Gunicorn cannot run on Windows, and `connect_timeout` was measured on Windows only.

## Rulings (controller)

| # | Ruling | Why |
|---|---|---|
| 1 | **Fix.** Keep `difflib`'s order, with population ordering only the states that share one name. Add a test for `Orlndo`, `Minnepolis`, `Lexigton` and `Tacma`, and update the documents that say "largest first". | Proved, and it is the I1 symptom again. |
| 2 | **Fix.** Version 2.1.0 in all four places; regenerate the schema; re-lock. | Proved. |
| 3 | **Fix.** Keep the 18 Nov Actual and add the 19 Nov observation. On the rebuilt 2.1.0 API the controller sent `start=Dallas, TX&finish=Springfield, ZZ` (it never routes) and got MO, MA, IL, OR, OH. | Proved; the controller observed it live. |
| 4 | **Fix.** Change the figure to "150 to 350 ms". | Proved. |
| 5 | **No change.** | It cannot happen with the shipped data: the extract script fails unless every key is in the table. The owner's rule is no handling for impossible cases. |
| 6 | **No change.** | Before this release the same wait had no bound at all (no `connect_timeout`). It happens only before a worker's first load. |
| 7 | **No change.** | Plausible only, not reproduced. |
| 8 | **Fix the document only.** Architecture line 179 is corrected. The `warm_up` clause stays: `test_warm_up_with_no_database_raises_nothing` pins it, and it costs nothing. | |
| 9 | **Fix the document.** `docs/development.md` says the cached refusals go too when the cache is emptied. | Real routing servers answer NoRoute the same way each time, so caching it is right. |
| 10 | **Fix all four.** The controller supplies the coverage figure: 98.52%, measured on 5cd97c0. | |
