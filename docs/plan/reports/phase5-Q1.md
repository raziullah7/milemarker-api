# Phase 5 report: tester 5Q1, the independent verifier and the live runner

Status: DONE. The verifier, its tests and the live runner are written. The one full live run passed all 49 cases (P01 to P20, N01 to N26, S01 to S03), and every live 200 obeyed R1 to R16. Lint and format are clean, `tests/test_verify.py` passes (27 tests), and the whole suite passes (321). I found no fault in the API. I found two problems in the documents' rules (section 4): R13's point-count tolerance wrongly fails correct answers for short trips, and R10's "exactly one sentence" does not match the API's warning, which is one entry made of two sentences.

## 1. Files created

- `tests/verify.py`: `verify_response(body, prices, stop_cost=None) -> list[str]`, `load_prices(csv_path)` and the `Listing` record. It imports only the standard library. One function per rule, R1 to R16. Every rule runs every time. A rule that cannot read the body (a missing key, a string where a number belongs) is reported as broken, with the reason, and the other rules still run. Money, gallons and prices are compared as `Decimal`; floats are turned back into their shortest text first.
- `tests/test_verify.py`: VF-01 to VF-19. It also has two extra tests: the runner imports nothing from the application, and `load_prices` keeps the cheapest listing, and the first row on a tie (the small CSV of section 2.1).
- `scripts/live_check.py`: the 49 cases are kept as data (`CASES`). Each case holds the document's own Request and Expected text, for the table, and a tuple of checks such as `C("summary.distance_miles", "≈", D("2800.7"))`, for the machine. The code below the data sends the requests, paces them, verifies, compares and prints.
- `docs/plan/reports/phase5-Q1.md`: this report.

No other file was touched. The `scripts/` folder is new.

**Independence.** I wrote `tests/verify.py` from test-cases section 4 and architecture section 11 alone, and its tests passed before I opened `planner.py`, `answer.py` or `fuel.py`. Before that I read only what the brief allows. `tests/test_api.py` showed me how the routing call is replaced. In `trips/services/routing.py` I read only the `Route` signature, because the test fake has to build one. VF-19 checks that the verifier imports nothing outside the standard library, so nothing can reach the application indirectly either.

**VF-01** is covered in my own file, as the brief asks. It requests seven real trips through the test client: New York to Los Angeles at stop costs 10, 0 and 25; Dallas to Houston; Seattle to Miami; Chicago to Houston; and Boston to Washington. Each runs on its recorded road with the real stations, and every answer is verified against the real CSV. No rule fails. The endpoint tests themselves (`tests/test_api.py`) do not call this verifier; they use their own `assert_sound`, which covers R1 to R4, R6 to R8 and R15. Test-cases section 1 ("Inside the endpoint tests") and VF-01 as worded ("every 200 produced by the endpoint tests") therefore describe something that is not literally there.

## 2. Test commands and their final output

```
$ uv run ruff check tests/verify.py tests/test_verify.py scripts/live_check.py
All checks passed!
$ uv run ruff format --check tests/verify.py tests/test_verify.py scripts/live_check.py
3 files already formatted
$ uv run pytest tests/test_verify.py -q
...........................                                              [100%]
27 passed in 3.73s
$ uv run pytest -q
........................................................................ [ 22%]
........................................................................ [ 44%]
........................................................................ [ 67%]
........................................................................ [ 89%]
.................................                                        [100%]
321 passed, 1 deselected in 32.68s
```

The 27 tests are 7 VF-01 trips, VF-02 to VF-18, VF-19, and the two extra tests. The whole suite's 321 tests are the 294 that were already there plus my 27. The one deselected test is the existing `slow` exactness check.

**What each break reports.** VF-02 shows that the unbroken answer reports nothing, so a rule that always fired could not pass VF-03 to VF-18. Each VF test asserts that its own rule is reported. Some other rules fire as well; they are the ones the break necessarily disturbs, because the map repeats each stop and cost depends on gallons × price. Measured on the New York to Los Angeles answer:

| Case | Rules reported |
|---|---|
| VF-03 stop 3 moved to 500.1 miles after stop 2 | R1, R2, R11, R12 |
| VF-04 stop 1 at 55.00 gal, stop 3 lowered to match | R2, R4, R11 |
| VF-05 +0.01 gal on one stop | R3, R4, R11 |
| VF-06 +0.01 on total_fuel_cost | R4 |
| VF-07 last digit of a price changed | R4, R5, R11 |
| VF-08 stops 2 and 3 swapped | R1, R2, R6, R11, R12 |
| VF-09 lowest = total + 0.01 | R7 |
| VF-10 summary.stops + 1 | R8 |
| VF-11 tank_gallons 60 | R9 |
| VF-12 first fill 30.0, no warning | R10 |
| VF-13 a stop Point removed | R11 |
| VF-14 a stop's lat + 0.001 in fuel_stops and the map | R12 |
| VF-15 a middle point removed from the line | R13 |
| VF-16 a cost of 12.345 | R4, R11, R14 |
| VF-17 cache_hit true with routing_calls 1 | R15 |
| VF-18 start label `Toronto, ON` | R16 |

I also tried three breaks the catalogue does not list. The route line written as [lat, lng] was caught by R12 and R13. A price sent as the string `"3.239"` was caught by R4, R5, R11 and R14. A body with no `meta` was caught by R14 and R15, each saying it could not read the body.

## 3. The one full live run

Before the full run I made two short runs against the same server while developing, with `--only P12,N03,N13` and `--only N04,N24 --markdown`. They made one routing call between them, for P12. I then stopped the server and started it again, so that the full run began with empty caches and an empty rate-limit window, as section 3 requires. Then, once:

```
uv run python manage.py runserver 127.0.0.1:8000 --noreload      (in the background)
uv run python scripts/live_check.py --markdown                    (exit code 0)
```

The server's log shows 114 requests: 80 answered 200, 19 answered 400, 1 answered 404, 4 answered 405, 9 answered 422 and 1 answered 429. There was no 5xx and no traceback. The run asked for 18 new trips (P01, P05 to P13, P17 to P20, N11, N12, N22 and N23); every other request was answered from a cache or rejected before routing. The server was stopped afterwards, and port 8000 is free.

The full output, verbatim:

```
| P01 | UC-01 | `/api/v1/route/?start=New York, NY&finish=Los Angeles, CA` | 200 | distance_miles ≈ 2,800.7, pass within 2%; stops fewer than 10 (design: 7); total_fuel_cost ≈ 865.93, pass within 2%; lowest_possible_fuel_cost ≈ 854.65, pass within 2%; first_fill_distance_miles ≈ 3.1, pass within 2%; warnings `[]`; labels `New York, NY`, `Los Angeles, CA`; routing_calls 1; cache_hit false | 200; summary.distance_miles 2800.6; summary.stops 7; summary.total_fuel_cost 867.27; summary.lowest_possible_fuel_cost 855.95; summary.first_fill_distance_miles 3.1; warnings []; summary.start.label New York, NY; summary.finish.label Los Angeles, CA; meta.routing_calls 1; meta.cache_hit false; round trip 1809.2 ms | PASS |
| P02 | UC-04 | P01's request again | 200 | summary identical to P01's; routing_calls 0; cache_hit true; round trip under 50 ms | 200; summary identical; meta.routing_calls 0; meta.cache_hit true; round_trip_ms 23.6 | PASS |
| P03 | UC-03 | `/api/v1/route/?start=New York, NY&finish=Los Angeles, CA&stop_cost=0` | 200 | stops more than P01's (design: 17); total_fuel_cost equals P01's lowest_possible_fuel_cost and this response's own; assumptions.stop_cost 0.0; routing_calls 0; cache_hit false | 200; summary.stops 19; summary.total_fuel_cost 855.95; assumptions.stop_cost 0.0; meta.routing_calls 0; meta.cache_hit false; round trip 34.7 ms | PASS |
| P04 | UC-03 | `/api/v1/route/?start=New York, NY&finish=Los Angeles, CA&stop_cost=25` | 200 | stops no more than P01's (design: 6); total_fuel_cost not below P01's, ≈ 884.79, pass within 2%; routing_calls 0 | 200; summary.stops 6; summary.total_fuel_cost 886.16; meta.routing_calls 0; round trip 40.9 ms | PASS |
| P05 | UC-05 | `/api/v1/route/?start=Los Angeles, CA&finish=New York, NY` | 200 | first_fill_distance_miles over 100, ≈ 121, pass within 2%; one warning, naming fuel_stops[0].name and the distance; routing_calls 1 | 200; summary.first_fill_distance_miles 120.6; warnings ["The nearest listed fuel station to the start is Shelee's Travel Center in Coachella, CA, 120.6 miles away. The first fill-up is priced there."]; warnings.0 The nearest listed fuel station to the start is Shelee's Travel Center in Coachella, CA, 120.6 miles away. The first fill-up is priced there.; meta.routing_calls 1; round trip 1096.8 ms | PASS |
| P06 | UC-01 | `/api/v1/route/?start=Seattle, WA&finish=Miami, FL` | 200 | distance_miles ≈ 3,301.2, pass within 2%; stops fewer than 12 | 200; summary.distance_miles 3301.1; summary.stops 8; round trip 908.6 ms | PASS |
| P07 | UC-01 | `/api/v1/route/?start=Chicago, IL&finish=Houston, TX` | 200 | distance_miles ≈ 1,086.9, pass within 2% | 200; summary.distance_miles 1086.9; round trip 443.7 ms | PASS |
| P08 | UC-02 | `/api/v1/route/?start=Dallas, TX&finish=Houston, TX` | 200 | distance_miles ≈ 238.1, pass within 2%; total_fuel_cost above 0 | 200; summary.distance_miles 239.6; summary.total_fuel_cost 68.62; round trip 402.1 ms | PASS |
| P09 | UC-01 | `/api/v1/route/?start=Boston, MA&finish=Washington, DC` | 200 | distance_miles ≈ 437.1, pass within 2% | 200; summary.distance_miles 437.0; round trip 700.6 ms | PASS |
| P10 | UC-06 | `/api/v1/route/?start=st. louis, mo&finish=Winston-Salem, North Carolina` | 200 | summary.start.label `Saint Louis, MO`; summary.finish.label `Winston Salem, NC` | 200; summary.start.label Saint Louis, MO; summary.finish.label Winston Salem, NC; round trip 1041.0 ms | PASS |
| P11 | UC-06 | `/api/v1/route/?start=Dallas TX&finish=Phoenix, Arizona, USA` | 200 | labels `Dallas, TX`, `Phoenix, AZ` | 200; summary.start.label Dallas, TX; summary.finish.label Phoenix, AZ; round trip 674.9 ms | PASS |
| P12 | UC-02 | `/api/v1/route/?start=Fort Worth, TX&finish=Dallas, TX` | 200 | stops 1; fuel_stops[0] kind `start`, mile_marker 0.0, gallons = distance_miles ÷ 10; distance_miles under 50 | 200; summary.stops 1; fuel_stops.0.kind start; fuel_stops.0.mile_marker 0.0; fuel_stops.0.gallons 3.22; summary.distance_miles 32.2; round trip 224.1 ms | PASS |
| P13 | UC-05 | `/api/v1/route/?start=Houston, TX&finish=Dallas, TX` | 200 | first_fill_distance_miles over 25; one warning | 200; summary.first_fill_distance_miles 41.8; warnings ["The nearest listed fuel station to the start is FUEL MAXX #57 in Liberty, TX, 41.8 miles away. The first fill-up is priced there."]; round trip 410.8 ms | PASS |
| P14 | UC-04 | `/api/v1/route/?start=new york city, ny&finish=Los Angeles, California` | 200 | summary identical to P01's, labels `New York, NY` and `Los Angeles, CA`; routing_calls 0; cache_hit true | 200; summary identical; summary.start.label New York, NY; summary.finish.label Los Angeles, CA; meta.routing_calls 0; meta.cache_hit true; round trip 21.8 ms | PASS |
| P15 | UC-03 | `/api/v1/route/?start=New York, NY&finish=Los Angeles, CA&stop_cost=100` | 200 | stops at least 6 and no more than P04's; total_fuel_cost not below P04's; assumptions.stop_cost 100.0; routing_calls 0 | 200; summary.stops 6; summary.total_fuel_cost 886.16; assumptions.stop_cost 100.0; meta.routing_calls 0; round trip 22.3 ms | PASS |
| P16 | UC-04 | `/api/v1/route/?start=Dallas, TX&finish=Houston, TX&units=km` | 200 | summary identical to P08's; routing_calls 0; cache_hit true | 200; summary identical; meta.routing_calls 0; meta.cache_hit true; round trip 15.0 ms | PASS |
| P17 | UC-06 | `/api/v1/route/?start=Washington, D.C.&finish=Boston, MA` | 200 | summary.start.label `Washington, DC` | 200; summary.start.label Washington, DC; round trip 644.0 ms | PASS |
| P18 | UC-06 | `/api/v1/route/?start=Santa Fe, New Mexico&finish=Denver, CO` | 200 | summary.start.label `Santa Fe, NM` | 200; summary.start.label Santa Fe, NM; round trip 612.0 ms | PASS |
| P19 | UC-02, UC-05 | `/api/v1/route/?start=Los Angeles, CA&finish=Las Vegas, NV` | 200 | distance_miles ≈ 276.2, pass within 2%; stops 1; first_fill_distance_miles ≈ 121, pass within 2%; one warning | 200; summary.distance_miles 276.2; summary.stops 1; summary.first_fill_distance_miles 120.6; warnings ["The nearest listed fuel station to the start is Shelee's Travel Center in Coachella, CA, 120.6 miles away. The first fill-up is priced there."]; round trip 421.4 ms | PASS |
| P20 | UC-02 | `/api/v1/route/?start=Los Angeles, CA&finish=San Francisco, CA` | 200 | distance_miles under 500; stops 1; one warning | 200; summary.distance_miles 389.0; summary.stops 1; warnings ["The nearest listed fuel station to the start is Shelee's Travel Center in Coachella, CA, 120.6 miles away. The first fill-up is priced there."]; round trip 854.1 ms | PASS |
| N01 | UC-15 | `/api/v1/route/?start=New York, NY` | 400 | `invalid_request`; details.fields has `finish` | 400 invalid_request; error.details.fields {finish} | PASS |
| N02 | UC-15 | `/api/v1/route/?start=&finish=Los Angeles, CA` | 400 | `invalid_request`; details.fields has `start` | 400 invalid_request; error.details.fields {start} | PASS |
| N03 | UC-07 | `/api/v1/route/?start=Chicgo, IL&finish=Houston, TX` | 400 | `unknown_place`; field `start`; query `Chicgo, IL`; suggestions include `Chicago, IL`, at most 5 | 400 unknown_place; error.details.field start; error.details.query Chicgo, IL; error.details.suggestions ["Chicago, IL", "Cisco, IL", "West Chicago, IL", "North Chicago, IL", "Cicero, IL"] | PASS |
| N04 | UC-07 | `/api/v1/route/?start=Dallas, TX&finish=Chicago` | 400 | `unknown_place`; field `finish`; suggestions `["Chicago, IL"]` | 400 unknown_place; error.details.field finish; error.details.suggestions ["Chicago, IL"] | PASS |
| N05 | UC-07 | `/api/v1/route/?start=Dallas, TX&finish=Springfield, ZZ` | 400 | `unknown_place`; field `finish`; at most 5 suggestions | 400 unknown_place; error.details.field finish; error.details.suggestions ["Springfield, AR", "Springfield, CO", "Springfield, GA", "Springfield, ID", "Springfield, IL"] | PASS |
| N06 | UC-08 | `/api/v1/route/?start=Honolulu, HI&finish=Los Angeles, CA` | 422 | `outside_coverage`; field `start`; query `Honolulu, HI` | 422 outside_coverage; error.details.field start; error.details.query Honolulu, HI | PASS |
| N07 | UC-08 | `/api/v1/route/?start=Seattle, WA&finish=Anchorage, AK` | 422 | `outside_coverage`; field `finish` | 422 outside_coverage; error.details.field finish | PASS |
| N08 | UC-08 | `/api/v1/route/?start=Toronto, ON&finish=Buffalo, NY` | 422 | `outside_coverage`; field `start` | 422 outside_coverage; error.details.field start | PASS |
| N09 | UC-16 | `/api/v1/route/?start=Dallas, TX&finish=dallas texas` | 400 | `invalid_request`; details.fields has `finish` | 400 invalid_request; error.details.fields {finish} | PASS |
| N10 | UC-15 | `/api/v1/route/?start=New York, NY&finish=Los Angeles, CA&stop_cost=-1`, then with `101`, `abc`, `nan` | 400 each | `invalid_request`; details.fields has `stop_cost` | 400 invalid_request (all 4); error.details.fields {stop_cost} | PASS |
| N11 | UC-09 | `/api/v1/route/?start=Detroit, MI&finish=Buffalo, NY` | 422 | `route_leaves_usa`; miles_abroad ≈ 252, pass within 2% | 422 route_leaves_usa; error.details.miles_abroad 252.0 | PASS |
| N12 | UC-10 | `/api/v1/route/?start=Los Angeles, CA&finish=Seattle, WA` | 422 | `no_fuel_plan`; gap_start_mile 0.0; gap_miles ≈ 886, pass within 2% | 422 no_fuel_plan; error.details.gap_start_mile 0.0; error.details.gap_miles 885.3 | PASS |
| N13 | UC-17 | POST, then PUT, PATCH, DELETE: `/api/v1/route/?start=New York, NY&finish=Los Angeles, CA` | 405 each | `method_not_allowed`; standard error body | 405 method_not_allowed (all 4) | PASS |
| N14 | UC-17 | `/api/v1/routes/?start=New York, NY&finish=Los Angeles, CA` | 404 | `not_found`; standard error body | 404 not_found | PASS |
| N16 | UC-07 | `/api/v1/route/?start=Chicgo, IL&finish=Nowhere, ZZ` | 400 | `unknown_place`; field `start` | 400 unknown_place; error.details.field start | PASS |
| N17 | UC-15 | `/api/v1/route/?start=Nowhere, ZZ` | 400 | `invalid_request` (the missing finish is found before places are looked up); details.fields has `finish` | 400 invalid_request; error.details.fields {finish} | PASS |
| N18 | UC-08 | `/api/v1/route/?start=Tijuana, Mexico&finish=San Diego, CA` | 422 | `outside_coverage`; field `start` | 422 outside_coverage; error.details.field start | PASS |
| N19 | UC-08 | `/api/v1/route/?start=Miami, FL&finish=San Juan, PR` | 422 | `outside_coverage`; field `finish` | 422 outside_coverage; error.details.field finish | PASS |
| N20 | UC-15 | `/api/v1/route/?start=   &finish=Los Angeles, CA` | 400 | `invalid_request`; details.fields has `start` | 400 invalid_request; error.details.fields {start} | PASS |
| N21 | UC-15 | `/api/v1/route/?start=New York, NY&finish=Los Angeles, CA&stop_cost=100.01`, then with `10.555`, then with `stop_cost=` empty | 400 each | `invalid_request`; details.fields has `stop_cost` | 400 invalid_request (all 3); error.details.fields {stop_cost} | PASS |
| N22 | UC-09 | `/api/v1/route/?start=Detroit, MI&finish=Boston, MA` | 422 | `route_leaves_usa`; miles_abroad ≈ 234, pass within 2% | 422 route_leaves_usa; error.details.miles_abroad 234.0 | PASS |
| N23 | UC-10 | `/api/v1/route/?start=San Francisco, CA&finish=Portland, OR` | 422 | `no_fuel_plan`; gap_start_mile 0.0; gap_miles ≈ 554, pass within 2% | 422 no_fuel_plan; error.details.gap_start_mile 0.0; error.details.gap_miles 549.3 | PASS |
| N24 | UC-15 | `/api/v1/route/` | 400 | `invalid_request`; details.fields has `start` and `finish` | 400 invalid_request; error.details.fields {start, finish} | PASS |
| N25 | UC-16 | `/api/v1/route/?start=New York City, NY&finish=Manhattan, NY` | 400 | `invalid_request`; details.fields has `finish` | 400 invalid_request; error.details.fields {finish} | PASS |
| N26 | UC-07 | `/api/v1/route/?start=75201&finish=Dallas, TX` | 400 | `unknown_place`; field `start` | 400 unknown_place; error.details.field start | PASS |
| N15 | UC-18 | P01's request repeated with no pause; run last | 429 | `rate_limited` by the 61st at the latest; details.retry_after_seconds above 0 | 429 rate_limited at request 61; error.details.retry_after_seconds 59 | PASS |
| S01 | UC-01 | NFR-1 | P01 and P06, each a new trip | meta.timings_ms.own 100 or less; round trip minus meta.timings_ms.routing 100 ms or less | P01's meta.timings_ms.own 19.5; P01's round_trip_ms - timings_ms.routing 49.4; P06's meta.timings_ms.own 20.1; P06's round_trip_ms - timings_ms.routing 46.6 | PASS |
| S02 | UC-04 | NFR-11 | P02 | Round trip under 50 ms; meta.timings_ms.total under 50; routing_calls 0 | P02's round_trip_ms 23.6; P02's meta.timings_ms.total 1.3; P02's meta.routing_calls 0 | PASS |
| S03 | UC-03 | NFR-1, NFR-2 | P03 (road cached, new stop cost) | routing_calls 0; round trip 100 ms or less | P03's meta.routing_calls 0; P03's round_trip_ms 34.7 | PASS |

49 cases: 49 passed, 0 failed
```

N15 appears after N26 because section 3 runs it last, after a 60-second pause. The S cases make no request of their own; they read the answers of P01, P02, P03 and P06. The 60 answers before the 429 in N15's burst were each a 200, and each was checked against R1 to R16 once the burst had finished, so that checking did not slow the burst.

## 4. Failures

**Live: none. In my tests at the end: none.**

During development one weakness in my own test showed up and was fixed. VF-17 first relied on the unbroken answer coming from a fresh routing call (routing_calls 1). When it was run in a harness that does not clear the cache between tests, routing_calls was 0, so the break made nothing wrong. VF-17 now sets routing_calls to 1 itself, which is what the catalogue specifies.

### The API is wrong

Nothing found. Every live 200 and every test answer obeyed R1 to R16, and every error had the standard body.

### The document's expectation is wrong or stale

**a) R13's point count is too strict for short trips.** This is a fault in the rule, not in the API. R13 asks for `2 × distance_miles + 1` line points, within 1%. The documents fix the re-spacing: GE-06 gives 140 points for 69.1 miles, and GE-08 gives 278 points for 138.2 miles. That means one point every half mile, plus the end point. A correct line can therefore differ from `2d + 1` by up to 0.8 of a point. For any trip under 39.5 miles, 1% is less than that. I checked this through the test client, with the real stations and a straight 10.3-mile road from Fort Worth (a scratch test, not kept). The API returned 22 points, every one 0.5 miles apart, and the verifier reported `R13: 22 line points, expected 21.6 within 1%`. A 10.0-mile road gave 21 points and passed. No live case hits this, but P12 (32.2 miles: 66 points, against 65.4 ± 0.654) passed by only 0.05 of a point. Suggested rewording: "within 1% or 1 point, whichever is larger".

**b) R10 says `warnings` holds "exactly one sentence".** The API's single warning is two sentences: "The nearest listed fuel station to the start is Shelee's Travel Center in Coachella, CA, 120.6 miles away. The first fill-up is priced there." I read "one sentence" as "one entry in the list", which agrees with AN-05 ("exactly one warning") and with architecture section 11 ("a list of plain sentences. One is added when…"). On that reading every live case passes. Read literally, R10 would fail P05, P13, P19 and P20. The document should say "exactly one warning".

**c) Design figures are stale but inside their 2%.** Every "≈" case passed. These are the live figures next to the design ones:

| Case | Figure | Design | Live | Difference |
|---|---|---|---|---|
| P01 | distance_miles | 2,800.7 | 2,800.6 | −0.004% |
| P01 | total_fuel_cost | 865.93 | 867.27 | +0.15% |
| P01 | lowest_possible_fuel_cost | 854.65 | 855.95 | +0.15% |
| P03 | stops (design note) | 17 | 19 | not a pass condition |
| P04 | total_fuel_cost | 884.79 | 886.16 | +0.15% |
| P05, P19 | first_fill_distance_miles | 121 | 120.6 | −0.33% |
| P06 | distance_miles | 3,301.2 | 3,301.1 | −0.003% |
| P08 | distance_miles | 238.1 | 239.6 | +0.63% |
| P09 | distance_miles | 437.1 | 437.0 | −0.02% |
| N12 | gap_miles | 886 | 885.3 | −0.08% |
| N23 | gap_miles | 554 | 549.3 | −0.85% |

The sample response in architecture section 11 and the stop-cost table in section 8 still carry the research figures (865.93, 854.65, 17 stops).

## 5. What I could not turn into a check, or checked only in part

- **R10 "one sentence"**: this is checked as exactly one entry that is a non-empty string and contains the stop's name and the distance as the response writes it (`120.6`). Sentences are not counted; see 4b.
- **R11 "Coordinates are [lng, lat]"**: every Point is checked against the stop or place it stands for. The route line's order is checked only indirectly. R12 requires each station stop to be a line point in [lng, lat] order. R13 catches a swapped line too, because the spacing changes: I tried it, and it reported 4,235 gaps.
- **R14 "Every number is a JSON number"**: checked for every figure the contract documents as a number: summary, assumptions, each stop, map coordinates and properties, and meta. `station_id` is not required to be a number, because section 11 shows it as `"…"`. Prices have no limit on decimals ("every digit the CSV has"); R5 checks their exact value instead.
- **R2's 0.05-gallon allowance** holds today, but it is narrower than the rounding rule allows. On the recorded New York to Los Angeles road at stop cost 0, one stop buys 50.03 gallons, because the largest purchase absorbs the rounding difference (architecture section 8, step 2). That is within 0.05. The rule itself allows up to 0.005 gallons per purchase, so a correct plan with many purchases that all round the same way could exceed 0.05 and be reported under R2. I have not seen it happen.
- **"The server is freshly started, with empty caches"** is a precondition of section 3, not something the runner can check. I met it by restarting the server before the full run.
- **Standard error body**: the document asks for it only in N13 and N14. The runner checks it, as EP-39 defines it, on every error response, because architecture section 11 says every error has the same body. This is my addition. Every error passed it.
- **Round trip** is measured by the runner on the same machine, from sending the request to receiving the whole body, as section 5 defines it. It does not include the runner's own JSON parsing.
- **S04** is an endpoint test with a fake routing service, not a live case, so it is not in the runner.
- **A road that passes the same point twice**: R12 places each stop at the first such pass after the previous stop. The documents do not say what to do in this case.
