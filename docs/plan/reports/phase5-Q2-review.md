# Review 5Q2: the whole project

Reviewer 5Q2, 18 Nov 2026, against commit 5222f00. Read-only: nothing in the repository was changed apart from this file.

**Method.** I read the four specification documents, every file under `config/`, `stations/`, `trips/` and `tests/`, and the project files. I ran `uv run pytest -q` (294 passed, 1 deselected) and `uv run ruff check .` (clean; `ruff format --check` clean too). To test the findings I wrote throwaway scripts outside the repository. They ran with every outbound socket blocked and the routing call replaced. They used the recorded roads in `tests/fixtures/roads/` and the real CSV, loaded the same way as the `real_index` fixture. One script used a local socket server on 127.0.0.1. No public server was called.

Severity counts: **0 Critical, 1 Important, 8 Minor, 4 Notes.**

## Findings

### 1. Important: a rounded purchase can be more than a full tank, and the shown tank can go below empty

- **Where:** `trips/services/answer.py:167-169` (`_bill`), as specified in `docs/requirements.md:117` (D-14) and `docs/backend-architecture.md:253`.
- **What is wrong:** every purchase is rounded on its own, and the whole rounding difference goes to the largest purchase. The largest purchase is usually a full 50.00-gallon tank, so the difference pushes it above the tank's size. If you follow the figures the response shows, the truck arrives at a stop below empty and then holds more than 50 gallons.
- **Input:** `GET /api/v1/route/?start=New York, NY&finish=Los Angeles, CA&stop_cost=0`. This is P03, a demo request in Postman folder 1. On the recorded road, stop 9 (Henderson Fuel Mart, Henderson NE, mile 1353.6) shows `"gallons": 50.03`. Walking the shown figures, the truck arrives there with −0.01 gallons and leaves with 50.02, and stops 10 to 15 each leave with 50.01 to 50.02. Boston to Seattle with `stop_cost=100` shows a 50.01-gallon purchase. Seattle to Miami with `stop_cost=0` shows 50.02. The money is consistent: each cost is its shown gallons × price, and the total is their sum.
- **Why it is not Critical:** the plan itself is drivable and the bill is right to the cent. The error stays inside rule R2's 0.05-gallon allowance, so the verifier will not flag it. The allowance hides the error instead of proving it cannot happen: an 18-stop plan already uses 0.03 of the 0.05.
- **Confirmed:** yes. I ran `plan_trip` offline on all 15 recorded in-USA roads at stop costs 0, 0.01, 5, 10, 25 and 100.
- **Fix:** round the running total instead of each purchase: `gallons_k = round(sum of the first k) − round(sum of the first k−1)`. I tried this offline on New York–Los Angeles, Seattle–Miami and Boston–Seattle at stop costs 0, 10 and 100. Every shown purchase was at most 50.00, the walked tank stayed within 0.00 to 50.00 with no allowance, and the gallons still summed exactly. The fix changes AN-01 and AN-02's expected figures and the wording of D-14. Add a test that walks the shown figures with zero tolerance.

### 2. Minor: `answer.py`, a module that must be Django-free, imports Django

- **Where:** `trips/services/answer.py:11` imports `Place` from `stations/places.py`, which imports `django.conf.settings` at `stations/places.py:14`. The test is `tests/test_project.py:37-46` (PJ-02).
- **What is wrong:** architecture section 3 says `answer.py` imports nothing from Django. Running `import trips.services.answer` loads `django`. The other five modules on the list do not. PJ-02 only parses each file's own `import` lines, so it passes anyway. In practice `answer.py` can still be tested without a database, but the documented rule is false and its test does not check what its name says.
- **Confirmed:** yes. `'django' in sys.modules` is `True` after importing `answer.py`, and `False` after each of the other five.
- **Fix:** move the `Place` dataclass to `stations/types.py` and import it from there in both modules. Make PJ-02 import each module in a fresh interpreter and check `sys.modules`.

### 3. Minor: the 5-second routing deadline can be overrun to about twice its length

- **Where:** `trips/services/routing.py:108-121`. The promise is in `docs/backend-architecture.md:281`: "worst case is two calls and about 10 seconds" (NFR-12).
- **What is wrong:** `httpx.Timeout(5)` limits each phase of a request (connecting, waiting for the headers, each read), not the whole attempt. The clock is only checked after the headers arrive and after each chunk. A server that pauses just under 5 seconds before the headers and again before the first chunk keeps one attempt going for about 10 seconds, so two attempts take about 20. The comment at lines 109-110 says the clock check "bounds the whole attempt", which overstates it.
- **Confirmed:** yes, against a local socket server. With the deadline set to 0.5 s, the server paused 0.45 s before the headers and between chunks. The two attempts took 1.84 s against the promised 1.0 s. RT-11 does not catch this because `MockTransport` applies no phase timeouts.
- **Fix:** state the real bound (about twice the deadline per attempt) in section 9, or give each phase half the deadline so the overrun is smaller. Keep a local-socket test like the one above.

### 4. Minor: any client can bypass the rate limit with an `X-Forwarded-For` header

- **Where:** `config/settings.py:91-93`.
- **What is wrong:** DRF's `AnonRateThrottle` identifies a client by `X-Forwarded-For` whenever the header is present, because `NUM_PROXIES` is unset. A client that sends a different value on each request is never limited, so NFR-16 does not hold. The comment above the setting suggests it keeps the API within the routing servers' one-request-a-second rule. It cannot do that either, because the limit is per client, not overall.
- **Confirmed:** yes, with the Django test client. 70 requests with varying `X-Forwarded-For` values got zero 429s. 70 requests from one client got ten.
- **Fix:** set `"NUM_PROXIES": 0` in `REST_FRAMEWORK` (or 1 once the API runs behind one proxy), and add an EP-34 variant that varies the header.

### 5. Minor: the routing client retries when it should not, and turns a zero-length road into a 502

- **Where:** `trips/services/routing.py:132-135` and `:155`. The rules are in `docs/backend-architecture.md:281-282`.
- **What is wrong:**
  - **Any other non-200 status is retried.** Section 9 lists only timeouts, connection errors, 5xx, 429 and unreadable answers. The code also sends the retry after any other non-200 status, for example a 400 `InvalidQuery`. Its own comment says the second server "would reject too", but the code asks it anyway.
  - **A zero-length road is called unreadable.** `_read_route` rejects `distance` 0 as unreadable. So if both points snap to the same spot on the road, both servers are called and the user gets 502 `routing_unavailable` ("could not be reached"). The EP-20 rule says that case should be 400 `invalid_request`, the same place.
- **Confirmed:** with the fake transport from `tests/test_routing.py`. A 400 `InvalidQuery` from server 1 led to a second call (`calls == 2`). An `Ok` answer with `distance: 0` led to two requests and `RoutingUnavailable(reason="error")`. I could not check that the public server returns distance 0 for such a pair, because the network was off limits.
- **Fix:**
  - Retry only on the statuses section 9 names, and correct the comment.
  - Accept `distance >= 0`, so the planner's half-mile check answers with 400.
  - Add an RT case for each.

### 6. Minor: more than 1,000 query parameters give a 500

- **Where:** `trips/views.py:42`, which reads `request.query_params`, and `trips/errors.py:73-74`.
- **What is wrong:** Django raises `TooManyFieldsSent` when the query string is parsed. The exception handler does not recognise it, so the request is answered as `internal_error` 500 and logged as an unexpected failure with a traceback. It is a client error.
- **Input:** `GET /api/v1/route/?start=Dallas,TX&finish=Houston,TX&x0=1&x1=1&…&x1000=1`.
- **Confirmed:** yes, with the Django test client: 500 `internal_error`, in the standard body.
- **Fix:** map `django.core.exceptions.SuspiciousOperation` to `invalid_request` 400 in `handler`.

### 7. Minor: "Tijuana Mexico" without a comma is an unknown place, not outside coverage

- **Where:** `stations/places.py:221-228`.
- **What is wrong:** the country is only checked after a comma. UC-08 A1 says a place "ending in `Canada` or `Mexico`" gets `outside_coverage`. `Tijuana Mexico` and `Toronto Canada` get 400 `unknown_place` with no suggestions. `Tijuana, Mexico` gets 422 as specified. PL-15 only tests the comma forms.
- **Confirmed:** yes, through the endpoint with the test client.
- **Fix:** when there is no comma and no state matched, treat a final word `Canada` or `Mexico` as outside coverage. `Santa Fe New Mexico` is unaffected, because the two-word state matches first. Add the comma-free forms to PL-15.

### 8. Minor: the documents disagree with the code in three places

- **Index loading:** `docs/backend-architecture.md:150-152` says the station index is read "the first time a request needs it" and "is not loaded at Django start-up". `config/wsgi.py:23-25` calls `warm_up()`, which loads it when the server starts. Section 6 should describe `warm_up()` and its rule against gunicorn `--preload`.
- **Answer-cache key:** `docs/backend-architecture.md:302` says the key is "the road key plus the stop cost". `trips/services/planner.py:89-91` also includes both labels, for a good reason that the document should give.
- **Repeated refused roads:** NFR-2 (`docs/requirements.md:80`) says asking for the same route again makes no routing call. A road that is refused is never cached (`planner.py:105-107` caches only after `_fetch_road` passes), so every repeat of Detroit to Buffalo calls the routing server again. `tests/test_api.py:713-719` asserts exactly that. Either cache the refusal under the road key, or reword NFR-2 and section 10.
- **Confirmed:** read, and checked with grep. The third behaviour is pinned by the existing test.

### 9. Minor: the search radius is set in two places

- **Where:** `trips/services/answer.py:23` (`SEARCH_RADIUS_MILES = 5`, which is reported in `assumptions`) and `trips/services/corridor.py:37` (`radius_miles: float = 5.0`, which is the radius actually used). `planner.py:111` relies on the default.
- **What is wrong:** if one value changes, the response states one radius and searches with another, and no test would notice.
- **Confirmed:** read only.
- **Fix:** define one constant in `corridor.py`, pass it explicitly from the planner, and import it in `answer.py`.

### 10. Note: concurrency and process state

- **What I found:**
  - **Duplicate routing calls.** Nothing stops two identical new requests that arrive together from both missing the road cache (`planner.py:102-107`). Both call the routing server and both report `routing_calls: 1`, so NFR-2 holds only for repeats that come one after another.
  - **An idle database connection.** `warm_up()` opens a database connection in the thread that imports `wsgi.py`. Under gunicorn that thread never serves requests, so the connection stays idle for the life of the worker. Closing it after `get_index()` costs one line.
  - **Everything else is safe.** The index, the places table, the border outlines and the shared `httpx` client are each written once and are idempotent, so a race only repeats work. `LocMemCache` pickles every value, so no request can change another's cached body. A coast-to-coast road plus its answer is 261 KB pickled (measured).
- **Confirmed:** read, apart from the measured size.
- **Action:** none needed. At most, mention the first two points in Known limits.

### 11. Note: falling back to the full station list breaks the 100 ms budget, but thinning itself is sound

- **Where:** `planner.py:228-231`.
- **What I found:** `plan_stops` on the full list took 281 ms on New York to Los Angeles (364 stations), 300 ms on Boston to Seattle and 154 ms on Seattle to Miami. The thinned lists took 6 to 7 ms. A trip that needs the fallback misses NFR-1. Architecture section 8 already says this ("about half a second", "rare").
- **D-10 holds.** On five recorded roads at stop costs 1, 5, 10 and 25, the thinned plan's cost (fuel plus stop costs) equalled the full list's in 18 of 20 cases. The worst was +0.065% (Boston to Washington at $1).
- **Confirmed:** yes, measured.
- **Action:** none needed. Optionally put the measured figure in Known limits.

### 12. Note: three framework defaults that behave differently from what they suggest

- **HEAD runs the whole plan.** It answers 200 with an empty body, makes a routing call for a new trip, and counts against the rate limit. Section 11 deliberately leaves HEAD to the framework.
- **`DJANGO_ALLOWED_HOSTS` is never enforced.** With no middleware nothing calls `get_host()`. A request with `Host: evil.example` is answered normally. This is harmless, because no absolute URL is ever built, but the variable and `.env.example` suggest it matters.
- **Place text has no length limit.** `start` and `finish` have no maximum length, and `_TRAILING_COUNTRY` (`places.py:86-88`) takes time that grows with the square of the length of a run of spaces. 4,000 spaces cost 73 ms and 8,000 cost 285 ms. Adding `max_length=100` to the serializer fields would end it.
- **Confirmed:** yes, all three were run.

### 13. Note: what a hiring reviewer will see on publishing

- **Missing deliverables.** These planned files do not exist yet: `README.md`, the `Dockerfile`, the API service in `docker-compose.yml`, the Postman collection and `scripts/live_check.py` (Phases 6 and 7). A fresh clone today can start only the database, and has no instructions. NFR-9 and acceptance check 9 are open until then.
- **The build record will be public.** `docs/plan/` holds about 45 files: agent briefs, agent reports and a ledger naming the models used and the commit-identity rule. Every commit carries a `Co-Authored-By: Claude` trailer. The ledger records the user's ruling that all documents live in `docs/`. I raise it only so that publishing it is a deliberate choice.
- **No secrets.** I found no secrets, keys, machine paths or personal email addresses in tracked files. The only password is the documented local database default.

## Checked and found sound

- **Fuel plan (`fuel.py`).**
  - **Same test at every 500-mile limit.** `find_gap`, `_reachable_from` and the "the tank already reaches it" tests in `plan_stops` all use the same subtraction against 500, so a stretch of exactly 500 miles is never lost in floating point.
  - **No crash on empty input.** No code path in the DP or the greedy plan crashes on an empty or one-station list after `find_gap` has passed.
  - **The first purchase is always the start.** Candidates at mile 0 are excluded.
  - **Exact against two methods.** EX-01 to EX-04 pass, and they compare the plan with linear programming and with brute force.
- **The whole request path on real data.** I ran `plan_trip` on all 15 recorded in-USA roads at six stop costs.
  - Every plan's gallons summed to distance ÷ 10, and every total equalled the sum of its stop costs.
  - The lowest possible bill was never above the plan's, and there were never fewer than ⌈L/500⌉ stops.
  - Our own work took 2 to 23 ms, with one 55 ms outlier.
  - Detroit to Buffalo is refused with 252 miles abroad.
- **Limits and ties.**
  - The 500-mile limit is inclusive.
  - The 5-mile limit is inclusive, through `nextafter`.
  - The 10-mile thinning limit is inclusive (CO-15).
  - The 25-mile warning is decided on the figure shown.
  - The border check needs more than 25 miles abroad.
  - Stations at mile 0 and at the finish are dropped.
  - Sorting is by mile, then price, then ID, and ties in thinning and in `nearest_station` compare exact decimals.
- **Caches.**
  - The answer key holds both coordinate pairs, both labels and the stop cost to 2 decimals, so `10`, `10.00` and `-0` behave as specified.
  - The road cache is keyed by coordinates only.
  - Errors are not cached, and `meta` is rebuilt on every response.
  - No cached value is shared mutable state.
- **Errors.**
  - One table maps codes to statuses (`errors.py`).
  - The catch-all 404 does not depend on `DEBUG`, and 405 keeps the `Allow` header.
  - `AlwaysJSON` stops an `Accept: text/html` request from becoming a 406, which would otherwise reach the handler as a 500.
  - A validation error names the field.
  - Start is resolved before finish, and both before the stations and the routing call.
- **Loader.** No station ID in the CSV appears with two different cities or states (checked), so keeping the cheapest listing before dropping Canadian rows loses nothing. The loader writes inside one transaction, and the price keeps all 8 decimals.
- **Layers.**
  - **Thin view.** The view does nothing but validate and call `plan_trip`.
  - **One network module.** Only `routing.py` makes a network call.
  - **ORM in two places.** The ORM is used only in `index.py` and the loader.
  - **Plain exceptions.** Business errors carry no HTTP.
  - **Pure modules.** Apart from finding 2, the pure modules import no Django.
- **Tests and lint.** 294 tests pass with sockets blocked, Ruff is clean, and there are no secrets in the repository.
