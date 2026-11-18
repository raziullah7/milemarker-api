# Phase 10C report: fixes from the second independent review

Status: DONE. Every finding in brief 10C is fixed, each after a test that failed for the stated reason. Where a fix only made a test able to fail (N7), the evidence is a scratch mutant, run outside the repository, that the old test let through and the new one catches. One ruling could not be built as written: R12's "own length" estimate fails correct answers, so R12 uses a bracket instead (see "Deviations").

## Findings

| Finding | Tests added or changed | Before the fix | What changed |
|---|---|---|---|
| Q0b-1 | `test_verify.py`: `test_qb01_a_station_far_from_the_road` (QB-01); `test_qb02_every_recorded_road_obeys_every_rule`, 18 roads × stop costs 0, 10, 25 (QB-02) | QB-01: `assert set() == {'R17'}`: the verifier returned `[]` for Utica swapped for Harrold, TX (742 miles away), total 853.21 against the true lowest 855.97. QB-02: 54 passed (a guard, not a failing test) | `tests/verify.py`: new rule R17. Each station stop lies within 15 miles (5 + 10) of a row of its city and state. A city matches by the places table's key rule (architecture section 6, rule 4: capitals, St/Ste/Ft/Mt written out, letters only); any row of the city will do. Default places: `data/us_cities.csv`, read by the verifier, plus its own copy of the five hand-added places. QB-01 now reports R17 and nothing else |
| Q0b-2 | `test_qb03_a_stop_drawn_further_along_than_its_marker` (QB-03) | `assert 'R12' in set()`: stop 4 moved 17 points (8.5 miles), nothing reported | R12 applies the line's own scale and allows 0.1 mile, over a bracket for the last stretch (see "Deviations"). Measured on the New York answer: a shift of 1, 2, 3 or 17 points is now caught on every one of its six station stops |
| Q0b-3 | `test_routing.py`: `test_qb04_…` for 302 (with `Location`), 403, 404 (QB-04); `test_qb05_…` for 204, 301, 307, 408, 410, 451 (QB-05); `test_any_other_refusal_ends_the_request_at_once` kept, now marked QB-06 | All 9 new cases: `RoutingUnavailable: The routing service refused the request.` after one request; server 2 was never asked | `routing.py`: only a 400 that is not `NoRoute`/`NoSegment` ends the request at once. Every other status that is not 200 goes to the next server. The NoRoute rule is unchanged: read whatever the status, below 500. Docstring, and architecture section 9's two bullets, say exactly this |
| Q0b-4 | `test_answer.py`: `test_qb07_lowest_possible_stops_are_counted_from_the_shown_gallons` (QB-07) | `assert 3 == 2`: stops 3, lowest_possible_stops 2, with stop cost 0 and identical purchases | `answer.py`: `lowest_possible_stops = max(1, sum(g > 0 for g in lowest_gallons))`, from the gallons `_bill` shows. `SMALLEST_COUNTED_GALLONS` removed (nothing else used it). Architecture section 8's sentence on 0.005 gallons replaced. The regression pins are unchanged and pass |
| Q0b-5 | `test_qb08_a_stop_that_buys_nothing` (QB-08); `test_qb09_a_stop_that_buys_less_than_nothing` (QB-09); `test_a_stop_buying_less_than_nothing_breaks_no_other_rule` (the review's own stop-cost-0 case, added to QB-09's row) | QB-08: `assert set() == {'R6'}`, nothing reported. QB-09 as catalogued: `assert 'R6' in {'R2', 'R3'}` (its gallons do not add up, so R2 and R3 fire). Stop-cost-0 case: `assert set() == {'R6'}`, nothing reported | R6: every stop after the first buys more than 0 gallons; the first buys 0 or more. QB-08 and the stop-cost-0 case report R6 alone |
| R15 | `test_vr01_a_routing_host_the_caller_names` (VR-01) | Import error: `cannot import name 'places_from'` (the module, with VR-03 and VR-04, did not load before the new options existed) | `verify_response(…, routing_hosts=…)`: hosts R15 accepts besides the two public ones |
| R17 and test data | `test_vr03_the_places_the_caller_gives` (VR-03); `test_vr04_the_hand_added_places_are_in_the_default_places`, all five places (VR-04) | Same import error | `verify_response(…, places=…)`, with `places_from(rows)` to build them. `tests/test_api.py`: `assert_sound` gives the verifier one place per station the test created. Only its verifier call, the import line and the one docstring word "sixteen" (now "seventeen") changed. `tests/test_planner.py` does not call the verifier, so it is untouched |
| N1 | `test_qb10_the_verifier_says_what_it_does_not_check` (QB-10) | `assert 'consistent and possible' in '…'` failed | The verifier's description says it checks that a plan is consistent and possible, not that it is the cheapest, and that EX-01 to EX-04 check that |
| N5 | `test_places.py`: `test_qb12_a_place_called_mexico_in_the_usa_is_not_the_country`; `test_qb12_the_country_without_a_comma_is_still_outside_coverage` for `Mexico` and `Tijuana Mexico` (QB-12) | `OutsideCoverage: 'Mexico, USA' is outside the area covered`. The other two passed before and after | `places.py`: the comma-free country rule applies only when no trailing USA was removed. `Mexico, USA` is `unknown_place` with exactly `Mexico, IN/ME/MO/NY/PA` |
| N7 (a) | AN-11 rewritten to QB-13's input | Passes before the fix, by design. Scratch mutant, the review's own edit (sub-0.005-gallon purchases dropped from the lowest bill): the old AN-11 passed; the new one failed, `Decimal('70.0') == Decimal('70.01')` | AN-11 now has a 0.004-gallon purchase whose hundredth is worth a cent: lowest 70.01, 2 stops |
| N7 (b) | `test_complete_answer_obeys_the_correctness_rules` (QB-14) | Scratch mutant, a route line with every other point dropped: the old test passed (2 of 2) | The test adds `meta` and passes the whole answer to `verify_response`, with the invented stations' prices and places, and requires `[]`. The new test reports R12 and R13 for the mutant. Its hand-written checks, and the helpers only they used (`_cents`, `DECIMALS`, `NUMBERS`, `_leaves`, the `math` import), are removed |
| N7 (c) | `test_regression.py`: `test_pinned_stops_new_york_to_los_angeles` (QB-15), added only | Scratch mutant moving 0.01 gallons from stop 6 to stop 7 (same price, 3.28233333): the summary pin passed (total still 867.29); the stop pin failed, `(71712, 2120.8, 25.91, 85.05) != (71712, 2120.8, 25.92, 85.08)` | Each stop's station ID, mile marker, gallons and cost pinned. The values were recorded from the code as it was before this task's change to `answer.py`, which does not affect them |
| N8 | `test_qb16_two_first_requests_share_one_client` (QB-16) | `assert 2 == 1`: two clients made | `routing.py`: a module lock around creating the shared client |
| Types | none; `uv run mypy` | 9 errors in `sphere.py`, `fuel.py`, `exceptions.py` | `sphere.py`: `ArrayLike` in, `NDArray[np.float64]` out (numpy's own types give that for each expression). `fuel.py`: `filled_ats: list[int \| None]`, `entry: _Entry \| None`, and `assert choice is not None` with the reason the code already relied on. `exceptions.py`: `**details: object`. No `type: ignore`. `mypy`: no issues in 6 files. The fuel and sphere tests (57) and the slow test (1) passed before and after |

## Deviations, and rows corrected

- **R12 is a bracket, not the review's point estimate.** The review proposed own length = `0.5 × (n − 2)` + the straight distance between the last two points. Where the road bends in its last half mile, that straight distance is shorter than the stretch along the road. On Dallas to Phoenix the stretch is 0.416 miles and the straight distance 0.199. With the estimate, 9 of QB-02's 54 correct answers failed, on four roads (`bos_sea`, `nyc_la`, `sea_mia`, `dal_phx`), by up to 0.158 mile. The stretch is at least the straight distance and at most 0.5 mile, so R12 now requires each marker to be within 0.1 mile of `0.5 × i × distance ÷ L` for some own length L in that range. On the 54 real answers the worst marker lies 0.044 mile outside the bracket. Section 4's R12 text says this.
- **QB-02** covered 15 roads in the catalogue. The brief says every recorded road: it now covers the 18 that give a 200. Detroit to Buffalo and to Boston leave the USA, and Los Angeles to Seattle has no fuel plan. Row corrected.
- **QB-09** is built as catalogued. Because stop 4 buys only 0.01 more, its gallons no longer add up, and R2 and R3 fire as well. The review's own case, where R6 is the only rule that can see the fault, is added as a second test and to the row.
- **VR-03 and VR-04**: "places file" became "places", since the endpoint tests build theirs from the stations they create. VR-04 now covers all five hand-added places, each also moved 20 miles to show R17 ran. Rows corrected.
- **AN-11's row** is updated to the input it now has (QB-13's). **R17's text** adds how a city matches, and that any row of it will do.

## Checks beyond the tests

- Every one of the 6,626 real stations (the `real_index` fixture) has a row of its city in R17's default places, and the farthest is 4.9 miles from its nearest row. So a correct stop, within 5 miles of its station, is under 10 miles from a row; R17 allows 15. On the 54 real answers the farthest station stop is 4.87 miles from a row.
- The regression pins (7) pass unchanged.

## Totals

```
DATABASE_URL=postgresql://milemarker:milemarker@127.0.0.1:5432/milemarker_c uv run pytest -q
449 passed, 1 deselected
uv run pytest -m slow -q                 1 passed, 449 deselected
uv run ruff check .                      All checks passed!
uv run ruff format --check .             54 files already formatted
uv run mypy                              Success: no issues found in 6 source files
```

This task added 82 tests: 67 in `test_verify.py`, 10 in `test_routing.py`, 1 in `test_answer.py`, 3 in `test_places.py` and 1 in `test_regression.py`. The 449 include another builder's `tests/test_fake_osrm.py`, which passed. One run with `--cov` reached 98.40%, above the floor. In that run `test_warm_up_leaves_nothing_for_the_first_request` failed (141.3 ms against 100), with coverage tracing on while the other builders' suites ran. It passed in every run without coverage, and this task changed nothing it times.

## For the controller

- **`scripts/live_check.py` needs `--routing-host`.** For example `parser.add_argument("--routing-host", action="append", default=[])`, repeatable. Pass it as `routing_hosts=args.routing_host` to both `verify_response` calls (lines 860 and 918 today). Its description (line 12) still says R1 to R16.
- **R17's default places** are read from `data/us_cities.csv`, found from `tests/verify.py`'s own location. Any image that runs the verifier or `live_check.py` must hold `data/` as well as `tests/`.
- **Stale wording outside my files:** the comment at `tests/test_fuel.py:178` and FU-23's row still describe the 0.005-gallon rule. For FU-23's input the count is the same under the new rule (0.003 shows as 0.00).
- **The stand-in and Q0b-3.** The stand-in answers 404 for an unknown path. A real client now passes a 404 to the next server; in the end-to-end stack there is only one server, so the result is still `routing_unavailable`.
- **`.coverage` is tracked.** It was committed in `004cbcc`, so any run with `--cov` changes a tracked file. My one such run did; I wrote the committed version back (`git show HEAD:.coverage`), and the file is clean again. It probably belongs in `.gitignore`.
- **Database address.** With `localhost` in `DATABASE_URL`, each connection on this machine took minutes (IPv6 tried first). My first full run made no progress and I stopped it. Every run above used `127.0.0.1`, as builder 10A also found.

## Unsure

- **R12's bracket is wider than 0.1 mile.** Near the end of a long road whose last two points are close together, it can be up to about 0.5 mile wide. A stop moved by one point could then pass near the finish, though a move of 2 or more points cannot. The review's 17 points, and a one-point move on every New York stop, are caught.
- **The rule for "no road" is unchanged.** A `NoRoute` body is still `NoRoute` with any status below 500, for example a 404 carrying it. The ruling names only "a 400 whose body is not no road", so I left that rule as it was.

## Second pass

Status: DONE. This pass fixes the twelve findings of review 10R ruled to 10C in `docs/plan/PHASE-10.md` ("Rulings on the review (10R)"), working on top of `838d1cb`. Each fix began with a test that failed for the stated reason. Where the test could not fail against the current code, a scratch mutant run outside the repository shows that it can. No regression pin changed. Every test run used `DATABASE_URL=…@127.0.0.1:5432/milemarker_c`, one pytest process at a time.

| Finding | Tests added or changed | Before the fix | What changed |
|---|---|---|---|
| R10-01 | `test_verify.py`: QB-18 (four cases, stops 2 to 5). QB-02's 54 answers and VF-01's 7 run again | Each QB-18 case: `assert set() == {'R17'}`, so all 17 rules passed. The stations chosen are the nearest unused ones 9.5 to 12 miles from the stop's point: Lowellville OH (9.77 mi), Tonica IL (10.34), York NE (11.46), Hudson CO (9.54) | `tests/verify.py`, R17: a station stop lies within 5.01 miles of the mean of its city's rows, or of one of them. Those are the only points where the application places a station. The five hand-added places count only where the file has no such city, as in the application. **After:** each QB-18 case reports R17 alone. QB-02 (all 18 recorded roads with a plan, at stop costs 0, 10 and 25) and VF-01 pass. Across QB-02's answers, the farthest of 163 station stops is 4.87 miles from such a point. All 6,626 real stations stand exactly on one (largest distance 0.0) |
| R10-02 | QB-19 (the review's padded line); QB-20 (a repeated middle point; 19 and 30 distinct points added at the end) | QB-19: `assert 'R13' in set()`: 30 copies of the end point, each stop moved to the farthest point R12 accepts, and all 17 rules passed. Repeated point: `assert 'R13' in {'R12'}`. 30 extra points: no count problem under the old 1% | R13 refuses a point that repeats the one before it, and allows the count to be 0.25% or 2 points off. **After:** QB-19 reports R13 (29 repeated points; 5,624 points against 5,602.4) and R17 (four stops moved over 5 miles). 19 extra points pass (0.19%); 30 are refused (0.39%) |
| R10-03 | `test_fake_osrm.py`: CF-37 | `DID NOT RAISE ImproperlyConfigured` | `config/settings.py`: more than two `ROUTING_SERVERS` entries are refused, with a message giving the count. The comment above now says "one or two templates" |
| R10-06 | SI-07 now sends `?overview=full&geometries=geojson` and requires each logged `path` to equal the bare path | It passes against the stand-in, which already drops the query. Against a scratch copy that logs `self.path`: `'…29.7652?overview=full&geometries=geojson' != '…29.7652'` | Test only |
| R10-07 | `test_answer.py`: QB-22. AN-11 (QB-13) given a new input | QB-22: `assert 3 == 2`: at stop cost 0, with identical purchases and a start purchase shown as 0.00, `stops` was 3 and `lowest_possible_stops` 2 | `answer.py`: `lowest_possible_stops = 1 + sum(g > 0 for g in lowest_gallons[1:])`, so the start is always counted, as in the plan. Section 8's sentence says so. AN-11 had its tiny purchase at the start, where it is now counted, which would make its name ("not counted") false. Its tiny purchase now comes after the start: (10.001, 0.003, 10.002, 9.994) at (3.50, 3.20, 3.00, 2.00); lowest 85.01, 3 stops. Scratch mutants: the tiny purchase dropped gives `85.0 != 85.01`; every purchase counted gives `4 != 3`. Rows AN-11 and QB-13 follow. The regression pins (8) pass unchanged |
| R10-08 | none: a document fix | `resolve()` today: `Mexico` and `Tijuana Mexico` are outside coverage. `Mexico, USA` is unknown, with IN, ME, MO, NY and PA suggested. `Tijuana Mexico USA` and `Toronto Canada US` are unknown, with none. `Tijuana, Mexico, USA` is outside coverage | Architecture section 6: with no comma, a last word `Canada` or `Mexico` counts only if the text did not end in USA. The sentence gives the three examples. The behaviour stands, as ruled |
| R10-09 | `test_routing.py`: QB-23 (404 carrying `NoRoute`; 503 carrying it, then server 2) | Both pass against the current code. Scratch mutants of `_attempt`: with the `status < 500` guard removed, the 503 case failed (`NoRoute` raised); with the guard narrowed to `status == 400`, the 404 case failed (server 2 called) | Tests only |
| R10-10 | none | | Architecture section 9: one sentence saying any 400 ends the request, even one that is not the routing server's own, and that this is accepted |
| R10-11 | `test_fake_osrm.py`: the old 404 test is now SI-12 | `assert 404 == 400` | `scripts/fake_osrm.py`: a GET to a path it does not serve answers 400 `InvalidUrl`, as the real server does. Its docstrings say so. A POST to an unknown path still answers 404: the real server answers only GET, and the stand-in's only POST is its own `/_reset` |
| R10-12 | QB-21 | `DID NOT RAISE TypeError` | `verify_response` raises `TypeError` when `routing_hosts` is a string. Its docstring says it takes a list |
| R10-13 | `test_vr04_the_verifiers_copy_of_the_hand_added_places_is_the_applications` | Scratch mutant, the verifier's Henrico 0.1° of longitude off: the old VR-04 passed. The new test failed: `{('VA', 'Henrico'): (37.5131, -77.24650000000001)} != {('VA', 'Henrico'): (37.5131, -77.3465)}` | The test compares the two tables value for value. VR-04's row says so |
| R10-16 | none | | The comment at `tests/test_fuel.py:178` (comment only) and FU-23's row now describe what the test asserts: one purchase only is 0.005 gallons or more. They no longer state a counting rule |

### Deviation

**R13 allows one repeat: the end point may repeat the point before it.** The ruling says R13 rejects repeated points. Without this exception, VR-03 failed with `R13: repeated points: 1, the first after point 1980`, and every endpoint test would fail the same way. The test roads are whole numbers of miles long, so the planner's re-spaced line ends 0.000006 miles past the last half-mile point (1,982 points on EP-01's road), and both are cut to the same 5 decimals. A real road ends so only when its last stretch is under about a metre, which is rare (under 1 trip in 1,000, judging by the length of that stretch). Allowing only that one repeat keeps the padding attack closed: QB-19's 29 further repeats are refused. One extra end point can move a stop at most half a mile near the finish, which R12's bracket already allowed. R13's text in section 4 says this.

### Rows corrected or added

Section 4: R13 and R17. Rows changed: AN-11, QB-13, FU-23, SI-07, VR-04. Rows added: SI-12, CF-37, QB-18 to QB-23.

### Totals

```
DATABASE_URL=postgresql://milemarker:milemarker@127.0.0.1:5432/milemarker_c uv run pytest -q
463 passed, 1 deselected
uv run pytest -m slow -q                 1 passed, 463 deselected
uv run mypy                              Success: no issues found in 6 source files
uv run ruff check .                      All checks passed!
uv run ruff format --check .             54 files already formatted
```

This pass added 14 tests: 10 in `test_verify.py`, 1 in `test_answer.py`, 2 in `test_routing.py`, and 1 in `test_fake_osrm.py` (SI-12 replaces the old 404 test).

### Concerns

- **R12's text is unchanged.** The review proposed saying there that the line itself is trusted. This pass may change only R13 and R17 in section 4, so R13's text says instead that R12 takes its scale from the number of points.
- **R17 now depends on exactly where the application places a station.** If `stations/places.py` changed its rule, for example to average a chosen county's several rows, R17 would have to follow. Today every station stands exactly on one of R17's points.
