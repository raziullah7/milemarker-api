# Phase 5 report: builder 5X, the fix wave

Status: DONE. All twelve fixes are made, each with a test I saw fail before the fix and pass after (F12 is the exception by its nature; see its entry). The whole suite passes (341), the slow check passes, and Ruff is clean. Nothing in `docs/` was changed apart from this file. No git command was run.

## The fixes

### F1: a shown purchase never exceeds the tank (finding 1)

**Files:** `trips/services/answer.py`, `tests/verify.py`, `tests/test_answer.py`, `tests/test_planner.py`, `tests/test_verify.py`, `tests/test_api.py`.

`_bill` now rounds the running total. It adds up the exact purchases in decimal, sets the last running total to the trip's total gallons, rounds each running total half-up to cents, and shows each purchase as the difference between consecutive rounded totals. The largest-purchase adjustment is gone. Costs, the total, and the rule that a 0.00-gallon purchase is not a stop are unchanged. The docstrings and the comment on 0.00-gallon purchases now describe the new rule. In `tests/verify.py`, R2's 0.05-gallon allowance (`TANK_SLACK`) is removed and the walk compares with 0 and 50 exactly.

| Test | Before | After |
|---|---|---|
| `test_planner.py::test_the_shown_gallons_fit_the_tank_exactly` (New York to Los Angeles at stop costs 0, 10 and 100, Boston to Seattle at 100; recorded roads, real stations, through `plan_trip`) | 2 of 4 failed: `[nyc_la-0]` "stop 9 buys 50.03 gallons"; `[bos_sea-100]` "tank at -0.01 on reaching stop 3". At 10 and 100 New York to Los Angeles already walked cleanly. | 4 passed |
| `test_answer.py::test_rounding_difference_falls_where_the_running_total_crosses_a_cent` (replaces the tie test): [20.004, 10.004, 10.002], distance 400.1 → [20.00, 10.01, 10.00] | failed: `Decimal('20.01') != Decimal('20.00')` at index 0 | passed |
| `test_verify.py::test_r2_allows_nothing_for_rounding`: stop 1 raised to 50.01 gallons and stop 2 lowered to match, so the only fault is 0.01 over | failed: only R4 and R11 reported, not R2 | passed |
| AN-01, AN-02 (renamed `test_an01_gallons_are_rounded_as_a_running_total`, `test_an02_a_running_total_can_round_up_first`) | passed | passed |

**AN-01 and AN-02 keep their figures.** The new rule gives the same numbers for their inputs: running totals 10.00, 30.01, 40.00 and 10.01, 30.01, 40.00, the figures `docs/test-cases.md` now lists. The review expected them to change, but they do not. I renamed both tests, because their old names described the largest-purchase rule, and added an assertion on the running totals.

**Other checks on the new rule.**
- **Scratch walk.** A script in my scratchpad, not in the repository, walked the shown figures with no allowance on all 15 recorded in-USA roads, at stop costs 0, 0.01, 5, 10, 25 and 100. It found **90 plans with no problem**: no purchase over 50.00, the tank never below 0.00 or above 50.00, and exactly 0 at the finish.
- **VF-01 and the existing answer tests.** All seven VF-01 trips pass with the zero allowance. `test_lowest_bill_is_never_shown_above_the_plans_bill`, `test_purchase_rounding_to_zero_gallons_is_not_a_stop` and AN-11 give the same figures as before.

### F2: `answer.py` does not load Django (finding 2)

**Files:** `stations/types.py`, `stations/places.py`, `trips/services/answer.py`, `tests/test_project.py`.

`Place` now lives in `stations/types.py`. `stations/places.py` imports it from there, so `stations.places.Place` still works for `planner.py`, `tests/test_api.py` and `tests/test_places.py`. `answer.py` imports it from `stations.types`. PJ-02 keeps its source check. For each pure module it also runs `sys.executable -c "import sys, <module>; ..."` in a fresh interpreter, from the repository root, and asserts that neither `django` nor `rest_framework` is in `sys.modules`.

| Test | Before | After |
|---|---|---|
| `test_project.py::test_pj02_pure_modules_do_not_import_django` (6 modules) | `[trips/services/answer.py]` failed: `"['django']" == '[]'`; the other 5 passed | 6 passed |

### F3: the rate limit ignores `X-Forwarded-For` (finding 4)

**Files:** `config/settings.py`, `tests/test_api.py`.

The fix adds `"NUM_PROXIES": 0` to `REST_FRAMEWORK`, with the one-line comment "No proxy in front: a client is its connection's address, never X-Forwarded-For."

| Test | Before | After |
|---|---|---|
| `test_api.py::test_ep34_rate_limit_ignores_x_forwarded_for`: 61 requests, each with a different `X-Forwarded-For`; the first 60 are not 429, and the 61st is | failed: `assert 200 == 429` | passed (EP-34 too) |

### F4: the routing client (finding 5)

**Files:** `trips/services/routing.py`, `tests/test_routing.py`, `tests/test_api.py`.

- **Which statuses lead to the second server.** After the `NoRoute` check, a 5xx or 429 status still leads to the next server. Any other non-200 status now raises `RoutingUnavailable("The routing service refused the request.", reason="error")` at once, with no second call. The comment says so. A 200 that cannot be read still leads to the next server, as before.
- **A zero-length road.** `_read_route` now accepts `distance >= 0`. It still needs at least two points, and it rejects a NaN or negative distance.
- **The deadline comment.** It now says the clock bounds the reading of the body, that an attempt can run to about twice the deadline, and why the timeouts are not cut. The `fetch_route` docstring describes the same timing and the new early `RoutingUnavailable`. The timeouts themselves are unchanged.

| Test | Before | After |
|---|---|---|
| `test_routing.py::test_any_other_refusal_ends_the_request_at_once`: 400 `InvalidQuery` from server 1; server 2 must not be called | failed: "routing.openstreetmap.de should not have been called" | passed: one request, `reason == "error"` |
| `test_routing.py::test_a_road_of_length_zero_is_a_route`: `Ok`, distance 0, two identical points | failed: same message (server 2 was asked) | passed: a `Route` of 0.0 miles, `calls == 1` |
| `test_api.py::test_ep20_a_road_of_length_zero_is_the_same_place`: both servers give that answer | failed: 502 `routing_unavailable` (the review's observation) | passed: 400 `invalid_request` naming `finish`, one request |

The zero-length answer is one constant, `ZERO_LENGTH_ANSWER` in `tests/test_routing.py`. `tests/test_api.py` imports it, so the RT test and the endpoint test use the same answer.

### F5: too many query parameters is a client error (finding 6)

**Files:** `trips/errors.py`, `tests/test_api.py`.

`handler` now answers `django.core.exceptions.SuspiciousOperation` with 400 `invalid_request`, `details` `{"fields": {}}`, and the message "The request could not be read: it is too large or malformed." It logs nothing. The check comes after the 404 branch and before the catch-all.

| Test | Before | After |
|---|---|---|
| `test_api.py::test_too_many_parameters_is_a_client_error`: `start`, `finish` and 999 more, 1,001 in all; no record from the `trips.errors` logger; no routing call | failed: 500 `internal_error`, logged "Unexpected failure while answering a request" | passed |

### F6: a country without a comma (finding 7)

**Files:** `stations/places.py`, `tests/test_places.py`.

In the no-comma branch of `resolve`, `OutsideCoverage` is raised when three things hold:
- the last word is `canada` or `mexico`, compared case-insensitively;
- `_split_trailing_state` matched no state;
- the whole text is not itself a state name.

The third condition is mine; see "Done differently" below.

| Test | Before | After |
|---|---|---|
| PL-15 `[Tijuana Mexico]`, `[Toronto Canada]` (added) | both failed: `UnknownPlace` | passed |
| PL-08 `[Santa Fe New Mexico]` | passed | passed |
| `test_a_state_name_on_its_own_is_unknown[New Mexico]` (added beside `Texas`) | passed | passed |

I also tried these spellings by hand after the fix:
- `tijuana mexico`, `MEXICO` and `Canada` are outside coverage.
- `Mexico NY` and `Mexico, NY` resolve to Mexico, NY.
- `, USA` stays an unknown place, not a crash, because the text left after "USA" is removed is empty.

### F7: one place for each limit (finding 9)

**Files:** `trips/services/corridor.py`, `trips/services/planner.py`, `trips/services/answer.py`, `tests/test_planner.py`.

- **The constants.** `corridor.py` defines `SEARCH_RADIUS_MILES = 5.0` and `THIN_WINDOW_MILES = 10.0`, and both are the defaults of `stations_along` and `thin`.
- **The planner.** `planner.py` passes them by keyword.
- **The answer.** `answer.py` imports `SEARCH_RADIUS_MILES` from `corridor.py` and drops its own copy. It writes `int(SEARCH_RADIUS_MILES)`, so the response still shows `5` (AN-07 checks the exact JSON).
- **`answer.py` now imports `corridor.py`, and with it scipy.** It is still Django-free: PJ-02 passes.

| Test | Before | After |
|---|---|---|
| `test_planner.py::test_the_radius_shown_is_the_radius_searched`: spies on the planner's `stations_along` and `thin`; the radius and window passed must be the corridor constants, and `assumptions.search_radius_miles` must equal the radius | failed: `KeyError: 'radius_miles'` (the planner relied on the default) | passed |

### F8: close the start-up connection (finding 10)

**Files:** `trips/services/planner.py`, `tests/test_planner.py`.

`warm_up()` ends with `connection.close()`, after the `try`/`except`, so the connection is closed whether the index loaded or not. The comment says the thread that starts the server never serves a request.

| Test | Before | After |
|---|---|---|
| `test_planner.py::test_warm_up_closes_its_database_connection` (`django_db(transaction=True)`; asserts `connection.connection is None`) | failed: `<psycopg.Connection [IDLE] ...> is None` | passed |
| The three existing warm-up tests | passed | passed |

The new test runs outside a test transaction because inside one, Django's `close()` closes the socket but keeps the connection object (it sets `closed_in_transaction`). The existing warm-up tests run inside a transaction and still pass, including the one that counts zero queries afterwards.

### F9: limits on the place text (finding 12)

**Files:** `trips/serializers.py`, `tests/test_api.py`.

`start` and `finish` are now `CharField(max_length=100)`. The docstring says so, and a comment gives the reason.

| Test | Before | After |
|---|---|---|
| `test_api.py::test_place_text_over_100_characters[start]`, `[finish]`: 101 characters, no routing call | both failed: `'unknown_place' == 'invalid_request'` | passed, each naming its field |

### F10: the allowed-hosts setting (finding 12)

**Files:** `config/settings.py`, `.env.example`, `tests/test_project.py`.

- **The setting.** `ALLOWED_HOSTS = ["*"]`, with a comment: nothing checks the Host header with no middleware, the API never builds an absolute address from it, and there are no cookies or sessions.
- **The variable.** The `DJANGO_ALLOWED_HOSTS` handling is deleted, and the variable is removed from `.env.example`.
- **The module docstring.** It said "four environment variables"; it now says three (`DATABASE_URL`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`).

| Test | Before | After |
|---|---|---|
| `test_project.py::test_allowed_hosts_does_not_pretend_to_check_the_host`: `"*"` in `ALLOWED_HOSTS` (the test runner appends `testserver`), and neither `.env.example` nor `config/settings.py` mentions `DJANGO_ALLOWED_HOSTS` | failed: `assert '*' in ['localhost', '127.0.0.1', '[::1]', 'testserver']` | passed |

### F11: R13 and correct short trips

**Files:** `tests/verify.py`, `tests/test_verify.py`.

The point-count check is now `abs(len(line) - expected) > max(expected / 100, 1)`. The message reads "within 1% or 1 point, whichever is larger", and a comment gives the reason.

| Test | Before | After |
|---|---|---|
| `test_verify.py::test_r13_a_correct_short_road_passes`: a straight 10.3-mile road due north from Fort Worth, through the endpoint with the real stations; asserts 22 line points and no broken rule | failed: `['R13: 22 line points, expected 21.6 within 1%']`, which is exactly what 5Q1 saw | passed |
| `test_verify.py::test_r13_a_long_road_missing_a_point_still_fails`: one point removed a third of the way along New York to Los Angeles; R13 reported, through its gap check | passed | passed |
| VF-15 | passed | passed |

The long-road test can only fail through the gap check. One point fewer out of about 5,600 is well inside 1%, so the count cannot see it. The test asserts that the R13 line reports one gap and no count problem. It is close to VF-15, which removes the middle point; I kept it because the brief asks for it, and it shows which part of R13 does the work.

### F12: the endpoint tests use the verifier

**Files:** `tests/test_api.py`, `tests/test_verify.py` (docstring only).

- **The prices.** `listed_prices()` in `tests/test_api.py` builds the verifier's price list from the `FuelStation` rows the test created: station ID to `Listing(price, name, address, city, state)`.
- **Where the verifier runs.** `assert_sound(body, stop_cost=None)` keeps all its own checks, and then asserts `verify_response(body, listed_prices(), stop_cost) == []`. Every 200 the file checks goes through `assert_sound`. `plan()` passes `params.get("stop_cost")`, and EP-12 passes its stop cost, so R9 compares with what was sent.
- **`assert_sound`'s R2.** It lost its 0.05 allowance too, since its comment cited R2's, which no longer exists.
- **The docstring.** The `tests/test_verify.py` module docstring no longer says the endpoint tests skip the verifier.

**Before and after.** The fix is the test change itself, so no test fails before it in the usual sense. After it, all endpoint tests pass with the verifier on every 200: the endpoint tests and the verifier agree, so there was nothing to judge between them. To show the verifier is really reached, I briefly set every listing's city to `"MUTATED"`. 26 tests then failed with R5 ("stop 1: city 'Testville', the CSV has 'MUTATED'"), one for each test that checks a 200. I restored the line afterwards and confirmed that no `MUTATED` is left in `tests/`.

## Final output of the commands

```
$ uv run pytest -q
341 passed, 1 deselected in 40.37s
$ uv run pytest -q -m slow
1 passed, 341 deselected in 20.15s
$ uv run ruff check .
All checks passed!
$ uv run ruff format --check .
50 files already formatted
```

The suite grew from 321 tests to 341. The tie test was removed; 21 test cases were added (6 for F1, 1 for F3, 3 for F4, 1 for F5, 3 for F6, 1 each for F7, F8 and F10, 2 each for F9 and F11).

## Fixes I could not complete as written

None. Every fix is made as the brief describes. The judgment calls are listed below.

## Done differently from the brief, and why

1. **F1's walking test is in `tests/test_planner.py`, not `tests/test_answer.py`.** It runs `plan_trip` on recorded roads with the real stations, which is what that file does, and it reuses that file's `recorded_road` fixture and `trip()` helper instead of copying them.
2. **F1 also removed `TANK_SLACK` from `assert_sound` in `tests/test_api.py`.** Its comment said "Rule R2 allows 0.05 gallons for rounding", which is no longer true.
3. **F6 has one extra condition: the whole text must not itself be a state.** Without it, "New Mexico" on its own ends in "Mexico", matches no state through `_split_trailing_state` (a state on its own is never split), and would be called outside coverage. With it, "New Mexico" stays `unknown_place`, as "Texas" does. A test covers it.
4. **F4's early error has its own message,** "The routing service refused the request.", because "could not be reached" would be false for a server that answered.
5. **F5 logs nothing,** not even a warning. The brief says not to log it as an unexpected failure. Django's own `django.request` logger still records the 400, as it does for every 4xx.
6. **The new tests have descriptive names and no case IDs,** because `docs/test-cases.md` has none for them yet. If the controller wants IDs, the natural ones are:
   - RT-15 `test_any_other_refusal_ends_the_request_at_once` and RT-16 `test_a_road_of_length_zero_is_a_route`;
   - EP variants for the X-Forwarded-For, zero-length-road, 1,001-parameter and 101-character tests;
   - a PJ case for allowed hosts;
   - VF cases for the two R13 tests and the R2 test.

## Unclear in the documents

- **R2 in `docs/test-cases.md` adds "no purchase is more than 50 gallons".** The verifier does not check it on its own, because the walk already implies it. Walking from an empty tank with no allowance, a purchase above 50 leaves the tank above 50 unless the arrival was already reported below 0.
- **The rate-limit comment overstates.** The comment above it in `config/settings.py` ("The free routing servers ask for no more than one request a second.") is what finding 4 says the per-client limit cannot deliver. The brief asked only for `NUM_PROXIES`, so I left it.

## Not sure is right

- **The running-total guarantee is shown on real data, not proven for every input.** The shown tank stays within 0 and 50 when the exact plan does, provided the mile markers and the gallons round the same way. They do, except at exact halves: miles go through Python's `round()`, which takes the nearest binary float and sends ties to even; gallons go through `Decimal` rounding, which sends halves up. 90 real plans, and the four the new test walks, showed no case. An unlucky tie could in principle still show 0.01 either way.
- **F8 inside test transactions.** The existing warm-up tests still pass with `close()` inside their transaction, because Django marks the connection `closed_in_transaction` and clears it when the transaction ends. That relies on Django's own handling of this case. It works on Django 6.1 as installed.
