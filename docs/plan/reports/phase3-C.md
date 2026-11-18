# Phase 3, builder C: the fuel plan

Status: DONE_WITH_CONCERNS. Every test passes. The concerns are three changes the controller needs to make to `docs/test-cases.md` (section 5). There is nothing wrong in the code.

## 1. Files created or changed

- `trips/services/fuel.py`: implemented `find_gap`, `plan_stops` and `cheapest_fuel`. I added private helpers only: `_Entry`, `_Choice`, `_require_plan`, `_reachable_from`, `_buy_then`, `_is_better`, and the constant `SAME_COST_DOLLARS`. No public name, signature or docstring changed.
- `tests/test_fuel.py` (new)
- `tests/exact.py` (new): `lp_cost` and `brute_cost`
- `docs/plan/reports/phase3-C.md` (this file)

## 2. Test command and output

```text
uv run pytest tests/test_fuel.py -q
.............................................                            [100%]
45 passed, 1 deselected in 10.79s
```

The one deselected test is the full-size EX-02, marked `slow`:

```text
uv run pytest tests/test_fuel.py -q -m slow
.                                                                        [100%]
1 passed, 45 deselected in 28.72s
```

`uv run ruff check` and `uv run ruff format --check` on all three files: clean.

## 3. Case IDs to tests

| ID | Test |
|---|---|
| FU-01 | `test_fu01_finish_within_range_of_the_start` |
| FU-02 | `test_fu02_finish_exactly_one_tank_away` |
| FU-03 | `test_fu03_cheaper_station_ahead` |
| FU-04 | `test_fu04_dearer_station_ahead_fill_up_first` |
| FU-05 | `test_fu05_dearer_station_skipped_when_finish_in_range` |
| FU-06 | `test_fu06_equal_prices` |
| FU-07 | `test_fu07_small_saving_taken_when_stops_are_free` |
| FU-08 | `test_fu08_small_saving_still_worth_a_3_dollar_stop` |
| FU-09 | `test_fu09_small_saving_not_worth_a_10_dollar_stop` |
| FU-10 | `test_fu10_two_stations_at_one_mile` |
| FU-11 | `test_fu11_stop_cost_prefers_one_stop_over_two` |
| FU-12 | `test_fu12_finish_one_mile_out_of_range` |
| FU-13 | `test_fu13_gap_after_the_last_station` |
| FU-14 | `test_fu14_first_station_out_of_range` |
| FU-15 | `test_fu15_stretches_of_exactly_500_miles_are_allowed` |
| FU-16 | `test_fu16_a_tenth_of_a_mile_too_far` |
| FU-17 | `test_fu17_stop_that_saves_more_than_it_costs` |
| FU-18 | `test_fu18_stop_that_saves_less_than_it_costs` |
| FU-19 | `test_fu19_very_short_trip` |
| FU-20 | `test_fu20_top_up_to_carry_cheap_fuel_past_a_dearer_station` |
| FU-21 | `test_fu21_fu20_without_the_station_at_mile_105` |
| FU-22 | `test_fu22_cheapest_fuel_matches_the_hand_worked_plans[fu03, fu04, fu07, fu20]` |
| FU-23 | `test_fu23_cheapest_fuel_keeps_a_tiny_purchase` |
| FU-24 | `test_fu24_find_gap` (the five inputs as parameters) |
| FU-25 | `test_fu25_no_plan_from_either_planner[plan_stops, cheapest_fuel × fu12, fu13, fu14, fu16]` |
| EX-01 | `test_ex01_free_stops_match_linear_programming` |
| EX-02 | `test_ex02_stop_cost_matches_brute_force` (default size); `test_ex02_stop_cost_matches_brute_force_full_size` (`slow`, the size in test-cases.md) |
| EX-03 | `test_ex03_every_plan_can_be_driven` |
| EX-04 | `test_ex04_higher_stop_cost_never_means_more_stops_or_less_fuel_money` |
| (no ID) | `test_ties_go_to_fewer_stops_then_the_earlier_station`: the tie rule from the brief (see section 5) |

### Exactness results

The largest difference from the exact method was $0.000000000 in every run. The test tolerance is $0.000001.

| Case | Trips | With a plan | Without | Solver calls | Time |
|---|---|---|---|---|---|
| EX-01: 1–28 stations, 50–3,000 mi, seed 1 | 400 | 287 | 113 | 400 | 0.6–0.9 s |
| EX-02 default: **1–8 stations**, 100–1,800 mi, seed 2 | 250 | 140 | 110 | 3,956 | 7.5 s (about 5 s when the CPU is cool) |
| EX-02 full size (`slow`): 1–10 stations | 250 | 143 | 107 | 13,506 | 16.0–16.5 s cool, 26–28 s throttled |
| EX-03: re-plans every EX-01 trip and the EX-02 trips at both sizes | — | — | — | 0 | 0.1 s |
| EX-04: 100 trips with a plan, seed 4, at 0, 5, 10, 25 and 60 | 100 | 100 | — | 0 | 0.1 s |

In the default run the exactness tests take about 8.6 seconds in all.

**Why EX-02 is smaller by default.** At full size it took 16 seconds in five early runs, which is within the 20-second limit. Later the same test took 26 to 28 seconds without any code change. This laptop throttles under sustained load: one `linprog` call takes 1.2 ms in the first second and 1.9 to 2.0 ms after that (I measured this over 8,000 calls). Because the full size can run over 20 seconds on this machine, I followed the brief's fallback. The default run keeps all 250 trips but caps each at 8 stations instead of 10. The full size runs with `uv run pytest -m slow tests/test_fuel.py`.

**Do the checks catch a wrong plan?** I loaded `fuel.py` with one deliberate fault at a time, in a scratch script; the repo file was not touched. The unchanged code had 0 failures.

| Fault | EX-01 failures (of 287) | EX-02 failures (first 100 full-size trips) |
|---|---|---|
| Move 1 only to strictly cheaper stations | 61 | 0 |
| No move 2 (never fill up) | 159 | 17 |
| Move 2 to the wrong dearer station | 132 | 12 |
| Stop cost not charged on moves 1 and 2 | 0 | 29 |
| Ties go to more stops | 0 | 0 (the tie test catches it) |
| Ties go to the later station | 0 | 0 (the tie test catches it) |

## 4. Where I differ from the brief, the documents or the prototype

1. **EX-02's default size** is 250 trips of up to 8 stations. The full size from test-cases.md is behind `@pytest.mark.slow`; the reason and the timings are above.
2. **EX-03 re-plans the trips; it does not store the plans.** The planners are deterministic, so planning again gives the same plans. EX-03 then runs without the slow exact methods, so it covers the full-size EX-02 trips on every run. Its checks: the tank stays within −1e-9 and 50 + 1e-9 gallons; the gallons add up to total ÷ 10 within ±1e-9; no stretch is over 500 miles. I also check that every purchase is for more than 0 gallons, that the first one is at index 0, and that the indices rise.
3. **EX-01 also checks `cheapest_fuel`** on the infeasible trips. The case lists only the solver, `plan_stops` and `find_gap`.
4. **EX-04 does not say how its trips are drawn.** I used the EX-01 recipe with seed 4 and kept the first 100 trips that have a plan. The fuel-cost check allows $1e-9 for floating-point noise.
5. **FU-23's "1 counted stop"** is checked by counting purchases of 0.005 gallons or more inside the test. The real counting rule is in `answer.py` (`SMALLEST_COUNTED_GALLONS`). I did not import it, so this test does not depend on builder F's module.
6. **Changes from the prototype's `dp`**, beyond the two the brief requires (a loop instead of recursion, and LP pricing in the brute force):
   - **No fixed tolerances (the prototype's 1e-9 EPS).** The miles still to buy are worked out as `(mile − where the tank was filled) − range`. That is the same subtraction `find_gap` and the range test use, so "the tank already reaches v" and "v is out of range" can never both be false. This is why no plan is lost on a stretch of exactly 500 miles, and why a move that would buy 0 gallons is never taken.
   - **The best fill-up move is found once per station, not once per table entry.** After a fill-up at u the tank is full, so the best next stop does not depend on how the truck reached u. The results are identical, and the speed went from 7.0 to 5.1 ms on 100 stations.
   - **The tie rule.** Costs within `SAME_COST_DOLLARS` ($1e-9) count as the same cost, because the same total reached by two different sums can differ in the last binary digit. On the same cost, the plan with fewer stops wins. If the stops are also equal, the earlier next stop wins, because options are offered in order of their next stop and only a strictly better one replaces the choice.
   - `cheapest_fuel` tracks the tank as the mile where its fuel runs out, not as gallons. Rounding then cannot build up from stop to stop, and "already enough" is an exact comparison.
7. **The error message** is: "No fuel station is listed for 503.0 miles from mile 0.0, more than the truck's range of 500 miles." The details carry the unrounded floats.

## 5. Unclear, contradictory or untestable in the documents

1. **test-cases.md EX-02** must change to match. Default run: 250 trips of 1–8 stations. Full size (1–10 stations): `uv run pytest -m slow`.
2. **The brief's tie rule has no case in test-cases.md.** I wrote `test_ties_go_to_fewer_stops_then_the_earlier_station` for it. I suggest adding it as FU-26:
   - `plan_stops([0, 100, 200], [3.00, 3.00, 3.00], 400, 0)` gives (0, 40): fewer stops at the same cost.
   - With a total of 600 it gives (0, 10), (1, 50): two stops either way, so the earlier station wins.
   - Nothing else catches a broken tie rule. FU-06 checks only the gallon sum, and the EX cases check only the cost.
3. **EX-04 does not say how its trips are drawn** (section 4, item 4). The document could name the EX-01 recipe.

## 6. What I am not sure is right

- **Other stations at mile 0.** `plan_stops` always buys first at index 0, as its docstring promises. If another station sat at mile 0 and was cheaper than the start, the plan would not be the cheapest possible. In that case `cheapest_fuel` would also make its first purchase at that other station, not at index 0. This cannot happen through the API, because `corridor.py` drops stations at mile 0 and at the trip length. I added no handling for it.
- **Stretches that are exactly 500 miles in decimal.** In binary such a stretch can come out as 500.00000000000006 miles. Then `find_gap` calls it a gap, and `plan_stops` may make an extra stop for about 1e-14 gallons. Every function measures distance the same way, so no plan is lost or invented. With real mile markers this needs two markers exactly 500 miles apart, so I left it alone.
- **The $1e-9 threshold for "the same cost"** is my choice; the brief does not define it.
- **Speed.** The brief asks for "a few milliseconds" at 100 stations, and section 14 of the architecture document gives 5 ms for the plan and the lowest bill together. I get about 5 ms; the prototype was 3.5 ms on the same input. My loop fills every table entry, while the recursion visited only the entries it reached. The figures:

  These are best of five, on random mile markers over 2,800 miles with prices from 2.900 to 4.500 and a fixed seed. Other builders were running at the same time, and the CPU was throttling.

  | Call | Time | Prototype `dp`, same input |
  |---|---|---|
  | `plan_stops`, 100 stations, stop cost $10 | 5.0–5.2 ms | 3.5–3.6 ms |
  | `plan_stops`, 400 stations (fallback) | 230–340 ms | 175–300 ms |
  | `cheapest_fuel`, 400 stations | 0.11–0.27 ms (0.04 ms on 100) | — |

  The plans and the prototype's agree to within $1.2e-13 on these inputs.
