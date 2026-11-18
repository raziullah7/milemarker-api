# Brief 5X: fixes from the whole-project review

An independent reviewer read the whole project (`docs/plan/reports/phase5-Q2-review.md`). The controller has ruled on each finding. You make the fixes below, each with a test that fails before it and passes after.

Read `docs/plan/briefs/phase3-common.md` first; its rules apply, except that you are the only builder now, you may edit any file under `config/`, `stations/`, `trips/` and `tests/` that a fix below names, and at the end you run the whole suite. Do not edit anything in `docs/` except your report: the controller updates the documents. No git commands.

Read the review report in full before you start. Finding numbers below are its numbers.

## Fixes

**F1 (finding 1, Important): a shown purchase must never exceed the tank.** In `trips/services/answer.py`, `_bill` rounds each purchase on its own and gives the whole difference to the largest. Replace that with rounding the running total: the shown gallons of purchase k are `round(sum of the first k exact purchases) − round(sum of the first k − 1)`, half-up to 2 decimals, with the last running total taken as the trip's total gallons exactly (distance ÷ 10). The gallons then add up exactly with no separate adjustment. Costs, the total, and the rule that a purchase showing 0.00 gallons is not a stop stay as they are.

- Update AN-01 and AN-02 in `tests/test_answer.py` to whatever the new rule gives for their inputs, and the test for the tie on the largest purchase, which no longer has a meaning: replace it with one that shows the new rule on three purchases.
- Add a test that builds the answer for New York to Los Angeles at stop costs 0, 10 and 100 and for Boston to Seattle at 100 (recorded roads, real stations, through `plan_trip` with the routing call replaced), then walks the **shown** figures: no purchase above 50.00 gallons, and the tank never below 0.00 or above 50.00, with **no** allowance.
- `tests/verify.py` rule R2 allows 0.05 gallons for rounding. Set that allowance to zero and make sure every verifier test still passes.

**F2 (finding 2): `answer.py` must not load Django.** Move the `Place` data class to `stations/types.py`. `stations/places.py` imports it from there and still exposes it, so existing imports of `stations.places.Place` keep working; `trips/services/answer.py` imports it from `stations.types`. Strengthen PJ-02 in `tests/test_project.py`: for each pure module, start a fresh Python interpreter (`subprocess`, `sys.executable`), import the module, and assert that `django` and `rest_framework` are not in `sys.modules`. Keep the existing source check as well.

**F3 (finding 4): the rate limit must not be bypassed with a header.** Add `"NUM_PROXIES": 0` to `REST_FRAMEWORK` in `config/settings.py`, with a one-line comment, and a test beside EP-34 that sends a different `X-Forwarded-For` on each request and is still limited.

**F4 (finding 5): the routing client.**
- Try the next server only after what architecture section 9 names: a timeout, a connection error, a 5xx or 429 status, or a 200 whose body cannot be read as a route. Any other status ends the attempt **and the request**: raise `RoutingUnavailable` with reason `error` at once, with no second call. Correct the comment.
- A route with `distance` 0 is a route: accept `distance >= 0` (still at least two points). The planner already answers a road under half a mile as the same place.
- Add an RT test for each: a 400 `InvalidQuery` from the first server makes one request and raises `RoutingUnavailable(reason="error")`; an `Ok` answer with distance 0 returns a `Route`; and through the endpoint that same answer gives 400 `invalid_request` with one routing call.
- Correct the comment about the deadline: the clock bounds the reading of the body; an attempt whose server is slow both to answer and to send can run to about twice the deadline. Do not change the timeouts themselves: the routing servers take up to about 3 seconds to start answering a coast-to-coast request.

**F5 (finding 6): too many query parameters is a client error.** In `trips/errors.py`, answer `django.core.exceptions.SuspiciousOperation` (which `TooManyFieldsSent` is) as 400 `invalid_request`, with `details.fields` empty, and do not log it as an unexpected failure. Test it with 1,001 parameters.

**F6 (finding 7): a country without a comma.** In `stations/places.py`, when the text has no comma and its last word is `Canada` or `Mexico` and no state matched, raise `OutsideCoverage`. `Santa Fe New Mexico` must still resolve. Add `Tijuana Mexico` and `Toronto Canada` to the PL-15 test and `Santa Fe New Mexico` stays in PL-08.

**F7 (finding 9): one place for each limit.** In `trips/services/corridor.py` define `SEARCH_RADIUS_MILES = 5.0` and `THIN_WINDOW_MILES = 10.0` and use them as the defaults of `stations_along` and `thin`. `planner.py` passes them explicitly. `answer.py` imports `SEARCH_RADIUS_MILES` from `corridor.py` and drops its own copy; the response still shows `"search_radius_miles": 5` as an integer.

**F8 (finding 10): close the start-up connection.** At the end of `warm_up()` in `trips/services/planner.py`, close the database connection it opened (`django.db.connection.close()`), with a comment saying the thread that starts the server never serves a request. The existing warm-up tests must still pass.

**F9 (finding 12): limits on the place text.** Give `start` and `finish` `max_length=100` in `trips/serializers.py`. Test that 101 characters gives 400 `invalid_request` naming the field.

**F10 (finding 12): the allowed-hosts setting does nothing.** With no middleware, nothing ever checks the host. Remove the pretence: set `ALLOWED_HOSTS = ["*"]` in `config/settings.py` with a comment saying why it is safe here (the API never builds an absolute address from the Host header, and has no cookies or sessions to protect), delete the `DJANGO_ALLOWED_HOSTS` handling, and remove the variable from `.env.example`.

## Not to be changed

- Finding 3's timeouts (see F4's last point), finding 8 (documents: the controller), finding 11, the HEAD behaviour in finding 12, and finding 13.

## Done when

- `uv run pytest -q` passes in full, and `uv run pytest -q -m slow` passes.
- `uv run ruff check .` and `uv run ruff format --check .` are clean.
- Every fix has a test that you saw fail before the fix and pass after. Say so, per fix, in your report.

## Your report: `docs/plan/reports/phase5-fix-wave.md`

For each fix: the files changed, the test that covers it, and the before and after of that test. Then the final lines of the three commands above. Then anything you could not do as written, and why.

Reply to the controller with the final test line and any fix you could not complete.

## Added after the live run

The live runner's author (report: `docs/plan/reports/phase5-Q1.md`) found two more things. Both are yours too.

**F11: rule R13 rejects correct short trips.** `tests/verify.py` requires the route line to have `2 × distance_miles + 1` points within 1%. A correct line has one point every half mile plus the end point, so it can differ from that figure by almost a whole point, which is more than 1% on any trip under about 40 miles. Change the check to "within 1% or 1 point, whichever is larger". Add a verifier test with a correct 10.3-mile road (22 points), which must pass, and one with a point removed from a long road, which must still fail.

**F12: the endpoint tests should use the verifier.** `tests/test_api.py` checks its 200 answers with its own `assert_sound`. Keep that, and also run `verify_response` on every 200 it checks, with the prices built from the `FuelStation` rows the test created (station ID to price, name, address, city and state). Put the small helper that builds those prices in `tests/test_api.py`. If the verifier reports a broken rule on any existing endpoint test, do not weaken the verifier: work out which of the two is wrong and say so in your report.
