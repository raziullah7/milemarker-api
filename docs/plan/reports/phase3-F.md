# Phase 3 report: builder F, answer builder

Status: DONE_WITH_CONCERNS. All tests pass. The concerns are judgement calls, listed in sections 4 to 6.

## 1. Files

- `trips/services/answer.py`: implemented `build_answer` plus private helpers. `Stop`, the `build_answer` signature, its docstring, `FAR_FIRST_FILL_MILES` and `SMALLEST_COUNTED_GALLONS` are unchanged. Added module constants `SEARCH_RADIUS_MILES`, `STOP_COLOUR`, `START_COLOUR`, `FINISH_COLOUR` and `CENT`.
- `tests/test_answer.py` (new)

## 2. Test command and output

`uv run pytest tests/test_answer.py -q`

```
..................                                                       [100%]
18 passed in 0.21s
```

Before the implementation, all 18 failed with `NotImplementedError`.

`uv run ruff check trips/services/answer.py tests/test_answer.py`: `All checks passed!`
`uv run ruff format --check trips/services/answer.py tests/test_answer.py`: `2 files already formatted`

Timing: `build_answer` on a 2,800.7-mile road (5,603 points, 7 stops) took 4.4 ms (best of 7). That is about 4% of the 100 ms NFR-1 budget.

## 3. Test-case map

| ID | Test |
|---|---|
| AN-01 | test_an01_rounding_shortfall_goes_to_the_largest_purchase |
| AN-02 | test_an02_rounding_excess_is_taken_from_the_largest_purchase |
| AN-03 | test_an03_cost_rounds_half_up_in_decimal_arithmetic |
| AN-04 | test_an04_price_keeps_every_digit_of_the_csv |
| AN-05 | test_an05_warning_only_when_first_fill_is_over_25_miles (25.0, 25.1, and 25.04; see 4a) |
| AN-06 | test_an06_keys_are_in_the_documented_order (also checks the key order inside summary, start, assumptions, a fuel stop and map) |
| AN-07 | test_an07_assumptions (stop cost 10, 0 and 12.5; compares the JSON text, so 500 must be an int and 10.0 a float) |
| AN-08 | test_an08_start_stop_then_station_stops_on_the_road (also checks each station stop's `[lng, lat]` equals its road point in the line, R12) |
| AN-09 | test_an09_map_holds_the_route_then_the_stops_then_start_and_finish |
| AN-10 | test_an10_miles_and_coordinates_are_rounded |
| AN-11 | test_an11_tiny_free_stop_purchase_is_not_counted_but_its_fuel_is |
| Rules R3, R4, R6, R8, R9, R10, R11, R14 | test_complete_answer_obeys_the_correctness_rules (first fill 3.149 and 47.26, so both branches of R10 run) |
| Brief: a tie for largest goes to the earliest | test_rounding_tie_for_largest_purchase_goes_to_the_earliest |

Every test reads the answer back through `json.dumps` and then `json.loads(..., parse_float=Decimal)`. Numbers are therefore compared as exact decimals, as section 4 reads them. This also shows that the body is plain JSON.

## 4. Differences from the brief or the documents

a. **The warning goes by the rounded distance, not the raw one.** The brief says to warn when `first_fill_miles` is more than 25.0. Rule R10 says to warn when the `first_fill_distance_miles` shown in the response is over 25. These two disagree for any input from 25.0 to under 25.05. For example, 25.04 is shown as 25.0, so R10 forbids a warning, but the brief's wording asks for one that would say "25.0 miles away". I compare the rounded figure, so the warning always matches the number shown. The AN-05 test includes 25.04 to pin this down.

b. **Miles and coordinates use Python's `round()`, not `Decimal`.** The brief says "Use `decimal.Decimal` throughout; never round money with floats." I read "throughout" as covering the money and gallons steps, and those all use `Decimal` with half-up rounding:
- each purchase's gallons
- each cost
- the totals
- the lowest possible bill

Miles go to 1 decimal and coordinates to 5, both with `round(float(x), n)`. Reasons:
- These are measurements. No figure a reader recomputes depends on which way a half rounds. The trip length arrives already rounded, and total gallons are computed from the shown distance.
- The route line has over 11,000 numbers coast to coast. I measured 12.5 ms with `Decimal` against 3.9 ms with `round()`.
- Every coordinate goes through one helper, `_coordinate`, so a station stop has exactly the `[lng, lat]` of its road point in the line (R12).

The visible effect: `round()` sends an exact binary tie to the even digit. A mile marker of exactly 100.25 shows as 100.2, not 100.3. Ties like this are vanishingly rare in real data, because markers are scaled and distances come from haversine. If the controller wants half-up for miles, it is a one-line change in `_miles`.

c. **How a float becomes a `Decimal`.** Exact gallons and the distance are read as the decimal the float prints as (`Decimal(str(x))`), not as its binary value (`Decimal(x)`). That way 10.005 gallons rounds up to 10.01, as a person would round it. The documents do not say which to use. AN-01 and AN-02 pass either way.

d. **"Largest purchase" means largest after rounding to 2 decimals.** This follows the order of the steps in the brief. A tie goes to the earliest.

e. **Key order inside each GeoJSON feature is `type`, `properties`, `geometry`.** No document fixes it. I put `properties` first so the route's long coordinate list comes last, in the spirit of "small parts first, the map last". RFC 7946 allows either order.

f. **Total gallons come from the rounded distance.** `distance_miles` is passed through `_miles` once, and that value is used both for the response and for total gallons = distance ÷ 10. If the caller sends an unrounded distance, R3 (`summary.gallons` = `summary.distance_miles` ÷ 10 exactly) still holds.

## 5. Unclear, contradictory or untestable

- **R10 against the brief's warning rule:** see 4a.
- **Tiny purchases in the chosen plan.** When the stop cost is 0, the plan is the greedy result (architecture section 8). It may then hold a purchase under 0.005 gallons. That purchase would appear in `fuel_stops` with `gallons` 0.00 and `cost` 0.00, and `summary.stops` would count it, while `lowest_possible_stops` would not. The documents leave out under-0.005 purchases only for the lowest-possible figures, so I left the plan's stops exactly as given. On real roads this should not happen: station markers are road-point markers about 0.5 miles apart, so any purchase that is not zero is at least about 0.05 gallons. It is the planner's or the fuel plan's business either way.
- **Search radius.** `search_radius_miles` 5 is a new constant in `answer.py`. It repeats the default `radius_miles=5.0` of `corridor.stations_along`, which has no module constant I could import. If someone changes one, they must change the other.

## 6. Not sure is right

- **The lowest bill could show a cent or two above the plan's bill.** R7 says `lowest_possible_fuel_cost` is not above `total_fuel_cost`. With a stop cost above 0, the two plans are rounded stop by stop, separately. If their exact bills were within a cent or two of each other, rounding could in theory put the lowest bill above the plan's bill. With stop cost 0 the two are the same purchases, so they always match (FR-16). I did not add a guard, because none is asked for and clamping would break "reproducible with a calculator". The endpoint tests' verifier would catch it if it ever happened.
- **`lowest_possible_stops` is `max(1, ...)`, as the brief says.** I believe a count of 0 cannot happen on a real trip, for the same 0.5-mile reason as in section 5.

## Review round 1

The coordinator accepted concerns 1 and 2 and asked for two fixes. Both are made, in `trips/services/answer.py` only.

- **Fix 1: no stop of 0.00 gallons.** After rounding, and after the difference has gone to the largest purchase, any stop whose rounded gallons are 0.00 is left out of `fuel_stops` and out of the map. Stop 1, the start, always stays. `order` runs 1, 2, 3 over the stops that remain, and `summary.stops` counts them. `summary.gallons` and `total_fuel_cost` are summed over the remaining stops. A dropped stop holds 0.00 gallons and costs 0.00, so neither figure changes: gallons still equal distance ÷ 10, and the total is still the sum of the shown costs.
- **Fix 2: the lowest bill is never shown above the plan's bill.** If the rounded free-stops bill comes out above `total_fuel_cost`, the response shows the plan's own bill and stop count as `lowest_possible_fuel_cost` and `lowest_possible_stops`. A comment in the code says why: the plan's bill can actually be bought, so the lowest cannot be more.

New tests:

| Test | What it covers |
|---|---|
| test_purchase_rounding_to_zero_gallons_is_not_a_stop | A middle purchase of 0.003 gallons: no such stop in `fuel_stops` or the map. Orders are 1, 2. Gallons sum to distance ÷ 10. The total equals the sum of the costs. |
| test_lowest_bill_is_never_shown_above_the_plans_bill | Both exact bills are 119.99. The free-stops plan, (4.50, 9.995) and (2.50, 30.005), rounds to 120.00 (checked: without Fix 2 it would show 120.00). The plan is 40 gallons at 2.99975, which rounds to 119.99. Both figures show 119.99 and 1 stop. |
| test_free_stops_plan_equal_to_the_plan_gives_equal_figures | Stop cost 0: `cheapest` is the plan's own purchases, including a middle 0.003. The two bills are equal, and so are the two stop counts (2). |

`uv run pytest tests/test_answer.py -q`

```
.....................                                                    [100%]
21 passed in 0.23s
```

`uv run ruff check` and `uv run ruff format --check` on both files: clean.

One edge is left, and I believe it cannot happen. If the start purchase itself were under 0.005 gallons, the two counts would differ by one, even with stop cost 0:
- Stop 1 is never left out, so `summary.stops` counts it.
- AN-11 requires that `lowest_possible_stops` does not count it.

R7 is unaffected, because it only compares the two costs. For this to happen, a cheaper station would have to sit within 0.05 miles of mile 0. The corridor leaves out stations at marker 0, and the next road point is about 0.5 miles away, so it cannot happen on a real trip.
