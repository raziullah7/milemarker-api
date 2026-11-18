# Review 9-Q0b: the code changed after commit 5222f00

Reviewer 9-Q0b, 18 Nov 2026, against release `v1.0.0` (commit `8f9609a`), in a disposable copy of it. Scope: `git diff 5222f00 v1.0.0 -- . ':!docs'`, the twelve fixes F1 to F12, the verifier, the live runner, the pinned figures, and `trips/` and `stations/` read in full.

**Method.** I read architecture sections 3 and 6 to 11, review 5Q2, the fix-wave brief and report, the diff, every file under `trips/`, `stations/` and `config/`, `tests/verify.py`, `tests/test_verify.py`, `tests/test_regression.py`, `scripts/live_check.py`, the Docker files, and most of the test files. I ran `uv run pytest` (348 passed, 1 deselected), `uv run pytest -m slow` (1 passed), `uv run ruff check .` and `ruff format --check .` (both clean).

To test suspicions I did two kinds of work:
- **Edits in the copy.** I reverted each fix in the copy, ran its tests and restored the file with `git checkout`. I also made three throwaway edits, listed under "Edits made in the copy". The copy was clean (`git status` empty) after each one.
- **Scratch tests outside the repository.** These were run with `uv run pytest -p tests.conftest --rootdir=. -c pyproject.toml <file>`, so they used the project's fixtures, the real stations and the recorded roads.

No request left the machine, the running API was not called, and no container was touched.

Severity counts: **0 Critical, 1 Important, 4 Minor, 9 Notes.**

## Findings

| ID | Severity | Where | What is wrong | How I showed it | Smallest fix |
|---|---|---|---|---|---|
| Q0b-1 | Important | `tests/verify.py:213-228` (R5) and `:394-420` (R12); no rule anywhere | **The verifier never checks that a stop's station is anywhere near the road.** R5 checks that the station exists and that its price and name match the CSV. R12 checks that the stop's `lat`/`lng` is a point of the line. Nothing ties the station to that point. A plan that buys at a station hundreds of miles away, drawn on the line, passes all 16 rules. Its bill can even be below the real lowest possible bill. So a corridor-search regression, for example a radius in the wrong units, would go through VF-01, the endpoint tests and every live 200. | Scratch test on the New York to Los Angeles answer at the default stop cost. Stop 3, Utica IL at $2.969, was replaced by the CSV's cheapest station, 66341 in Harrold TX at $2.68733333, which is 742 miles away. The stop kept Utica's place on the line, and costs, map and totals were made consistent. `verify_response` returned `[]`. The total fell from 867.29 to 853.21, below the true lowest possible bill of 855.97. | Add a rule, R17. Each station stop's `[lng, lat]` must lie within 15 miles of some row of `data/us_cities.csv` for its city and state. The 15 miles are the 5-mile radius plus at most 10 miles of county averaging. The verifier reads the file itself, and needs the five hand-added places listed in it too. Add a VF case that swaps a stop's station as above. |
| Q0b-2 | Minor | `tests/verify.py:415-416` (R12) | **R12's tolerance hides miles.** R12 compares a stop's `mile_marker` with `0.5 × line position`, allowing 0.5% + 0.05 miles. That is about 7 miles at mile 1,350 and 12.5 at mile 2,500. The allowance exists because markers are scaled by `distance / own length` (up to 0.19% off), but the verifier does not apply that scale. A stop drawn several miles further along than its marker passes. The stretch before it can then be over 500 miles while R1 and R2, which read the markers, see 499.8. | Scratch test, same answer. Stop 4 (marker 1353.6) was moved 17 line points, about 8.5 miles, along the line, with its marker kept. No rule fired. The stretch from stop 3 is really about 508 miles but is shown as 499.8. Later stops could be moved 22 to 33 points. | Estimate the line's own length as `0.5 × (n − 2) + the last gap`, and expect `0.5 × i × distance / own`, within 0.1 mile. Change R12 in `docs/test-cases.md` to match. |
| Q0b-3 | Minor | `trips/services/routing.py:138-143` (F4) | **F4 gives up on the second server too often.** It ends the request at once, with no second call, on every status that is not 200, 5xx or 429. That includes 204, 301, 302, 307, 403, 404, 408, 410 and 451. Architecture section 9 calls only a 4xx a refusal. A 3xx or a 204 is "an answer that cannot be read as a route", which section 9 says goes to the second server. Beyond the documents: 403 (one operator blocking a client), 404 or 410 (a path moved; the two servers' paths differ) and 408 (a server-side timeout) concern one server, not the request. The second server is there for exactly those. | Scratch test with the `Fake` transport from `tests/test_routing.py`, server 1 answering each of those nine statuses. Every one gave `RoutingUnavailable(reason="error")` after one request, and server 2 was never asked. | Raise the early `RoutingUnavailable` only for status 400, or only when the body's OSRM `code` is one of `InvalidUrl`, `InvalidService`, `InvalidVersion`, `InvalidOptions`, `InvalidQuery` or `InvalidValue`. Send every other non-200 to the next server. Add RT cases for a 3xx and a 404. |
| Q0b-4 | Minor | `trips/services/answer.py:81-91` (F1) | **The plan and the lowest possible bill now count stops by different rules.** F1 made "shown as a stop" mean "its running-total difference is above 0.00". `lowest_possible_stops` still counts exact purchases of 0.005 gallons or more. These now disagree. A 0.004-gallon purchase can show as a 0.01-gallon stop (before F1 it rounded to 0.00 and was hidden), and a 0.006-gallon one can show 0.00 and vanish. At stop cost 0 the plan *is* the free-stops plan (FR-16), yet the two counts can differ. `test_free_stops_plan_equal_to_the_plan_gives_equal_figures` uses an input where they happen to agree. | Scratch test calling `build_answer` with purchases [10.004, 0.004, 9.992] and stop cost 0. Both bills were 58.00, `stops` was 3 and `lowest_possible_stops` was 2. I did not see it on real data: 15 recorded roads at stop costs 0, 0.01, 5, 10, 25 and 100 had no purchase under 0.05 gallons. | Count `lowest_possible_stops` from the shown gallons, as `stops` is: `max(1, sum(g > 0 for g in lowest_gallons))`, where `lowest_gallons` is the first value `_bill(cheapest, …)` returns. AN-11 still passes (it shows 0.00 and 30.00, so the count is 1). Add the case above as a test. |
| Q0b-5 | Minor | `tests/verify.py:166-183` (R2), `:231-263` (R6) | **A stop that buys nothing, or less than nothing, passes.** No rule requires a station stop to buy more than 0 gallons. Architecture section 8 says a purchase that rounds to 0.00 is not shown as a stop. | Scratch tests. (a) An extra stop buying 0.00 gallons, at a real unused station placed on the line between stops 2 and 3, gave `[]`. (b) At stop cost 0, stop 15 changed to buy −0.01 gallons at −$0.03, with stop 16 buying 1.76 more, also gave `[]`. | Add to R6: every stop after the first has `gallons > 0`, and stop 1 has `gallons ≥ 0`. Add a VF case. |
| N1 | Note | `tests/verify.py:266-277` (R7) | `lowest_possible_fuel_cost` has no lower bound, and the plan's optimality is not checked. A lowest bill of 1.00 with 99 stops passes. A plan that moves 2 gallons from stop 4 to the dearer stop 5 (+$0.50) passes. Optimality is the job of the exactness tests (EX-01 to EX-04), so this is by design, but the verifier's docstring and README do not say it. | Scratch tests: both returned `[]`. | Say in `verify.py`'s docstring that it checks consistency and feasibility, not optimality. |
| N2 | Note | `config/settings.py:91-92`; DRF `SimpleRateThrottle.allow_request` | **Concurrent requests can slip past the per-client limit.** The throttle reads its history from the cache and writes it back without a lock, and the server runs four threads. Two requests from one client can read the same history and both pass, so the client can exceed 60 a minute under concurrency. | Scratch script calling the view directly, `plan_trip` stubbed: 100 requests from one address over 4 threads. Unchanged, 60 were answered and 40 limited. With a 2 ms pause between the throttle's read and write (standing in for a thread switch), all 100 were answered. | None needed here. Note in section 16 that the limit is approximate under concurrency. |
| N3 | Note | `config/settings.py:93-94` (F3), `docker-compose.yml` | **Behind Docker, many clients can share one limit.** With `NUM_PROXIES: 0` a client is `REMOTE_ADDR`. Behind Compose's published port, Docker Desktop shows every client as the Docker gateway, and so does Linux for localhost connections. All such clients then share one 60-a-minute allowance, and one busy caller can lock out the rest. The fix itself is right: trusting `X-Forwarded-For` was worse. | Read. No container was started. | Say so in the README. Use `NUM_PROXIES: 1` only behind a trusted proxy that sets the header. |
| N4 | Note | `config/settings.py:107` | **A stale comment on the deadline.** The comment on `ROUTING_DEADLINE_SECONDS` still says "from sending the request to reading the last byte". F4 corrected this in `routing.py` and section 9: an attempt can run to about twice the deadline. | Read. | Reword the comment to match `routing.py:112-116`. |
| N5 | Note | `stations/places.py:221-226` (F6) | **`Mexico, USA` is now outside coverage.** The trailing `USA` is stripped before the country test, so the text is called the country even though the caller wrote USA, and the table has US places named Mexico. Before F6 it was `unknown_place` with suggestions `Mexico, IN`, `ME`, `MO`, `NY`, `PA`. Also, `Mexico.` (with a full stop) is `unknown_place` while `Mexico` is `outside_coverage`. | Scratch script calling `resolve`. | Apply the comma-free country rule only when `_TRAILING_COUNTRY` removed nothing. |
| N6 | Note | `trips/services/answer.py:166-169` against `:236-243` | **An exact half could still put the shown tank 0.01 out.** Gallons round half-up on decimal text, while miles round with `round()`, ties to even, on binary floats. At an exact half the walk could show ±0.01. The fix-wave report already says so. | Walked 90 real plans (15 roads × 6 stop costs) with no allowance: all clean. | Round mile markers half-up in `Decimal` too, if it is ever seen. |
| N7 | Note | `tests/test_answer.py:341-347`, `:431-527`; `tests/test_regression.py:18-26` | **Three tests check less than their names promise.** (a) AN-11's second half ("…but its fuel is") cannot fail. Dropping every sub-0.005-gallon purchase from the lowest bill altogether still passes all 21 answer tests, because 0.003 gallons are worth under a cent and the last running total is forced to the trip total. (b) `test_complete_answer_obeys_the_correctness_rules` checks R3, R4, R6, R8 to R11 and R14, but not R1, R2, R5, R7, R12 or R13. (c) The pins are exact, but cover only five summary figures. With F1 reverted, only 2 of the 7 pins failed (`sea_mia` and `chi_hou` at stop cost 10). New York to Los Angeles at stop cost 0, the trip where 50.03 gallons appeared, still passed, and all 71 endpoint tests passed. F1's walk test and VF-01 are what catch it. | (a) An edit in the copy, then `pytest tests/test_answer.py`: 21 passed. (c) F1 reverted, then `pytest tests/test_regression.py tests/test_api.py`: 2 failed, 76 passed. | (a) Give AN-11 a tiny purchase worth at least a cent, or assert the gallons. (b) Rename the test, or call `verify_response`. (c) Pin each stop's ID and gallons for one trip. |
| N8 | Note | `trips/services/routing.py:95-100`, `stations/index.py:27-49` | **Two harmless check-then-set races.** Two first requests at once can each build a station index or an HTTP client. The duplicate index is harmless; the losing client is never closed. | Read. | Optional: a module lock around each creation. |
| N9 | Note | `config/settings.py:71-77` | **One client can push every other trip out of the cache.** Roads, answers and throttle records share one 500-entry in-memory cache. Each distinct `stop_cost` (10,001 allowed values) makes a new answer entry; a coast-to-coast road and its answer together are about 260 KB. One client at 60 a minute can evict every other trip's cached answer within about 8 minutes. Memory stays bounded. | Read; the size is 5Q2's measurement. | None needed for this project. |

## Scope item 1: the twelve fixes

"Fails without it": I reverted only that fix in the copy, ran the named test, saw it fail, and restored the file.

| Fix | Sound? | Fails without it? | Notes |
|---|---|---|---|
| F1 running-total gallons | **Sound.** The shown tank stays within 0 and 50 on every real plan I walked, and the sums are exact. | **Yes.** `test_the_shown_gallons_fit_the_tank_exactly`: 2 of 4 failed ("stop 9 buys 50.03 gallons", "tank at -0.01 on reaching stop 3"). The three-purchase test failed. VF-01 `nyc_la-0` reported R2. Verifier half: with the 0.05 allowance put back, `test_r2_allows_nothing_for_rounding` failed. | Introduced Q0b-4. See N6 and N7(c). |
| F2 `Place` in `types.py` | Sound | **Yes.** PJ-02 `[answer.py]` failed. | The fresh-interpreter check is a real check. |
| F3 `NUM_PROXIES: 0` | **Sound** | **Yes.** `test_ep34_rate_limit_ignores_x_forwarded_for`: `200 == 429` failed. | See N2 and N3. |
| F4 routing rules | **Partly.** The zero-length road is sound. The retry rule is broader than section 9 (Q0b-3). | **Yes, both halves.** Retry rule reverted: `test_any_other_refusal_ends_the_request_at_once` failed. `metres > 0` restored: the RT zero-length test and EP-20 zero-length (502 instead of 400) failed. | Comment fixed in `routing.py`, not in `settings.py` (N4). |
| F5 `SuspiciousOperation` → 400 | **Sound.** `TooManyFieldsSent` is raised only when the view reads `query_params`, so it reaches the handler. | **Yes.** 500 `internal_error`, logged with a traceback. | |
| F6 country without a comma | Sound | **Yes.** PL-15 `[Tijuana Mexico]` and `[Toronto Canada]` failed. | Quirks in N5. `Mexico Missouri` and `Mexico NY` still resolve. |
| F7 one constant per limit | Sound | **Yes.** `KeyError: 'radius_miles'`. | The test would also catch a radius changed only in `corridor.py`, since it compares `assumptions` with the constant. |
| F8 close the start-up connection | **Sound.** Under gunicorn 27.0.1, `init_process` calls `load_wsgi()` (and so `warm_up()`) in the main thread before `run()`, so the closed connection belongs to a thread that never serves. | **Yes.** `test_warm_up_closes_its_database_connection` failed. | The test covers only the empty-table path. |
| F9 `max_length=100` | **Sound.** The worst lookup at 100 characters took about 4 ms. | **Yes.** Both parameters failed (`unknown_place`). | |
| F10 `ALLOWED_HOSTS = ["*"]` | **Sound.** No middleware reads the host. | **Yes.** | The test is a text check, but it can fail. |
| F11 R13 allowance | Sound | **Yes.** "R13: 22 line points, expected 21.6 within 1%". | |
| F12 verifier in endpoint tests | Sound | **Yes, by planting.** An always-failing rule `R99` made 26 of 71 endpoint tests fail: every one that checks a 200. That matches the fix-wave report. | |

## Scope item 2: the verifier against wrong answers

`tests/verify.py` imports only the standard library. VF-19 checks this through the AST, and I confirmed it by reading the file.

Each wrong answer below was built from a correct one, with costs, map and totals made consistent where the edit allowed it.

| Wrong answer | Result |
|---|---|
| Stretch over 500 miles, by moving a marker (VF-03) | Caught: R1 |
| Stretch over 500 miles, by moving the stop along the line with its marker kept | **Passes** (Q0b-2) |
| Gallons that do not sum (VF-05) | Caught: R3 |
| A real CSV price for the stop's station that is not its lowest (station 70744: 2.969, 2.999, 3.159) | Caught: R5 |
| Stops 2 and 3 swapped and renumbered | Caught: R1, R2, R6, R12 |
| One stop's cost and the total both a cent up | Caught: R4 |
| A station 742 miles from the road | **Passes** (Q0b-1) |
| A 0.00-gallon or −0.01-gallon stop | **Passes** (Q0b-5) |
| `lowest_possible_fuel_cost` 1.00 | **Passes** (N1) |
| 2 gallons moved to a dearer stop | **Passes** (N1, by design) |

## Scope item 3: the live runner and the pinned figures

- **`scripts/live_check.py`** imports no application code. It verifies every 200, including each 200 of the N15 burst, and checks every error body. A wrong status fails the case. Missing figures and type errors count as failures, not passes.
  - Its money checks (P01, P04, P05) allow ±2%, because live data drifts: ±$17 on P01. The exact guards are the relational checks: P03 equals P01's lowest, and P04 and P15 are not below the earlier totals.
  - A wrong plan that keeps the arithmetic consistent passes there exactly as it passes the verifier (Q0b-1, Q0b-2, Q0b-5).
- **`tests/test_regression.py`** compares five summary figures exactly, as floats from the same rounding, which is tight to the cent. Coverage is narrow: see N7(c).

## Scope item 4: the application code and concurrency

**Shared cache.** `LocMemCache` instances share one store and one lock across threads, and values are pickled, so no request can change another's body. `_with_meta` builds a new dict.

**Station index.** The race is benign (N8). After `warm_up()` no request touches the database. If the table was empty at start-up, request threads read it once and Django closes their connections at request end.

**Warm-up.** It runs before the thread pool serves anything (see F8 above). Under `runserver` it runs in the server's own start-up thread.

**HTTP client.**
- The creation race is benign (N8).
- The client is created inside the worker, because there is no `--preload`.
- An attempt that fails inside `client.stream` closes its response on leaving the `with` block.

**Throttle.** See N2 and N3.

**Other changed code, found sound:**
- `_bill`'s `running[-1] = total_gallons` only absorbs float noise. `plan_stops` and `cheapest_fuel` always arrive empty, so the exact sum is the trip total.
- Dropped 0.00 stops carry their fuel into the next running total, so the walk stays exact.
- The early `RoutingUnavailable` escapes the retry loop as intended.
- The Docker files do what their comments say: non-root user, one worker, no `--preload`, and `load_stations` replaces the table in one transaction.

## Scope item 5: twenty tests sampled

**Sound: they assert what their names say, and I saw most of them fail when their fix was reverted.**
- `test_ep34_rate_limit_ignores_x_forwarded_for`
- `test_too_many_parameters_is_a_client_error`
- `test_place_text_over_100_characters`
- `test_ep20_a_road_of_length_zero_is_the_same_place`
- `test_any_other_refusal_ends_the_request_at_once` (it covers only 400; see Q0b-3)
- `test_a_road_of_length_zero_is_a_route`
- `test_the_shown_gallons_fit_the_tank_exactly`
- `test_the_radius_shown_is_the_radius_searched`
- `test_warm_up_closes_its_database_connection`
- PJ-02
- `test_allowed_hosts_does_not_pretend_to_check_the_host`
- `test_rounding_difference_falls_where_the_running_total_crosses_a_cent`
- `test_r2_allows_nothing_for_rounding`
- `test_r13_a_correct_short_road_passes`
- VF-03 (it covers only the naive form; see Q0b-2)
- VF-14
- LD-14
- EP-26
- `test_lowest_bill_is_never_shown_above_the_plans_bill`

**Weaker than their names:**
- AN-11's second half cannot fail (N7a).
- `test_complete_answer_obeys_the_correctness_rules` checks only 9 of the 16 rules (N7b).
- `test_free_stops_plan_equal_to_the_plan_gives_equal_figures` holds only for the input it chose (Q0b-4).
- In EP-27 and `test_new_york_to_los_angeles_with_free_stops`, the assertion "total equals lowest at stop cost 0" is true by construction, because both bills come from the same purchases. Each test has other assertions that can fail.

Apart from AN-11's second half, I found no test that cannot fail at all.

## Checked and found sound

- **Suite and lint.** The whole suite passes with sockets blocked. The slow exactness test passes. Ruff is clean.
- **Shown figures on real data.** All 15 recorded in-USA roads at stop costs 0, 0.01, 5, 10, 25 and 100 walk cleanly with no allowance.
- **What the verifier catches.** It catches every wrong answer the brief names in its direct form, and it imports nothing from the application.
- **F5's reach.** The handler sees `TooManyFieldsSent` because the throttle and content negotiation never read the query string.
- **F6's edge cases.** `New Mexico` alone, `Santa Fe New Mexico`, `Mexico Missouri`, `Mexico NY`, `Canada, KY` and `Toronto Ontario Canada` all behave as intended.

## Edits made in the copy (each restored at once with `git checkout`)

- The twelve fix reverts above, each a small string replacement in one or two files.
- `tests/verify.py`: R2's 0.05 allowance put back. Then, separately, an always-failing rule `R99` added to `RULES`.
- `trips/services/answer.py`: sub-0.005-gallon purchases filtered out of the lowest bill, for N7(a).

## What I could not check

- **The public routing servers.** I could not see which statuses they really send when they refuse or block a client (Q0b-3). Every routing behaviour was tested with the fake transport.
- **Containers.** The client address behind Docker's published port (N3) is reasoned from how Docker forwards ports, not observed.
- **The live runner.** I did not run `scripts/live_check.py`, because the running API was off limits. I judged it by reading.
- **`httpx.Client` under heavy concurrent load.** Its thread safety is taken from the library's design; I did not stress-test it.
- **Q0b-4 on real data.** It is shown on a constructed plan only. No recorded road produced a purchase small enough.
