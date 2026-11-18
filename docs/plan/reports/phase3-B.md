# Phase 3 report B: geometry and station search

Status: **DONE_WITH_CONCERNS**. All 44 tests pass and lint is clean. The concerns are small and listed in sections 5 and 6.

## 1. Files

| File | What changed |
|---|---|
| `trips/services/geo.py` | Implemented `resample`, `load_borders`, `longest_run_abroad`. Added a private `_inside` (ray casting) and two latitude constants. No signature, name or docstring changed. |
| `trips/services/corridor.py` | Implemented `stations_along` and `thin`. No signature, name or docstring changed. |
| `tests/test_geo.py` | New: GE-06 to GE-17, plus one speed test for the border check. |
| `tests/test_corridor.py` | New: CO-01 to CO-16. |

## 2. Test run

```
uv run pytest tests/test_geo.py tests/test_corridor.py -q
............................................                             [100%]
44 passed in 1.07s
```

Lint, both clean:

```
uv run ruff check trips/services/geo.py trips/services/corridor.py tests/test_geo.py tests/test_corridor.py
All checks passed!
uv run ruff format --check trips/services/geo.py trips/services/corridor.py tests/test_geo.py tests/test_corridor.py
4 files already formatted
```

Tests were written first and run before the code: 9 failed and 18 errored for geo (the errors came from the module fixture calling `load_borders`), and 17 failed for corridor, all on `NotImplementedError`.

## 3. Case to test

| ID | Test |
|---|---|
| GE-06 | `test_ge06_one_degree_along_the_equator` |
| GE-07 | `test_ge07_a_repeated_point_changes_nothing` |
| GE-08 | `test_ge08_a_corner_keeps_every_point_on_the_road` |
| GE-09 | `test_ge09_new_york_to_los_angeles` |
| GE-10 | `test_ge10_one_stretch_through_a_box` |
| GE-11 | `test_ge11_the_longest_run_not_the_sum` |
| GE-12 | `test_ge12_middle_latitudes_are_not_sampled` |
| GE-13 | `test_ge13_one_stretch_through_mexico` |
| GE-14 | `test_ge14_detroit_to_buffalo_runs_through_ontario` |
| GE-15 | `test_ge15_detroit_to_boston_runs_through_ontario` |
| GE-16 | `test_ge16_roads_that_stay_in_the_usa` (parametrised over the 15 roads) |
| GE-17 | `test_ge17_load_borders` |
| CO-01 | `test_co01_a_station_on_the_road` |
| CO-02 | `test_co02_just_inside_the_limit_to_the_north` |
| CO-03 | `test_co03_just_inside_the_limit_to_the_south` |
| CO-04 | `test_co04_just_outside_the_limit` |
| CO-05 | `test_co05_the_mile_is_the_nearest_road_points` |
| CO-06 | `test_co06_behind_the_start_is_dropped` |
| CO-07 | `test_co07_beyond_the_finish_is_dropped` |
| CO-08 | `test_co08_the_start_station_is_left_out` |
| CO-09 | `test_co09_sorted_by_mile` |
| CO-10 | `test_co10_same_position_the_cheaper_stays` |
| CO-11 | `test_co11_same_position_and_price_the_lower_id_stays` |
| CO-12 | `test_co12_a_cheaper_station_within_ten_miles` |
| CO-13 | `test_co13_the_cheaper_one_may_come_later` |
| CO-14 | `test_co14_equally_cheap_the_earlier_stays_whatever_the_id` |
| CO-15 | `test_co15_ten_miles_is_within` (parametrised: mile 110 and mile 110.5) |
| CO-16 | `test_co16_a_dropped_station_still_drops_others` |
| (speed) | `test_border_check_is_fast_enough`: Boston to Seattle, best of 3, under 200 ms |

The border check gives these figures on the recorded roads (real borders, length rounded to 0.1 mile as the API does):

| Road | Longest run abroad | Expected |
|---|---|---|
| Detroit to Buffalo | 252.0 mi | ≈ 252 |
| Detroit to Boston | 234.0 mi | ≈ 234 |
| International Falls to Baudette | 10.0 mi | at most 25 (design: 10 at most) |
| El Paso to Del Rio, Laredo to Brownsville | 2.0 mi each | at most 25 |
| The other 12 US roads | 0.0 mi | at most 25 |

## 4. Speed

Measured on this machine, best of five runs, by a throwaway script kept outside the repository.

| What | Time |
|---|---|
| `resample` on New York to Los Angeles (34,931 points in, 5,594 out) | **1.9 ms** |
| `longest_run_abroad` on Boston to Seattle (limit 40 ms) | **1.7 ms** |
| `stations_along` + `thin` on New York to Los Angeles, 6,626 stations at random over the lower 48 (seeded) | **2.3 ms** (search 2.2, thinning 0.05) |

Stations at random over the whole lower 48 are much sparser near any one road than real ones: only 30 of them fall within 5 miles of this road, against about 363 with the real CSV (CO-17). So `thin` was also timed on 363 candidates: 0.6 ms. The search itself does not depend on how many stations are found. Together that is about 3 ms.

## 5. Differences from the brief, the prototypes and the documents

1. **Border check: only edges a ray could cross are tested.** This is the one real change from `s8_foreign.py`. The prototype tests every sample against all 3,317 edges of the Canada outline. Ported unchanged, that took **52.6 ms** on Boston to Seattle, over the 40 ms limit. `_inside` first keeps only the edges that span the samples' latitudes, reach east of the westmost sample, and are not flat, then does the same ray test. That took 2.1 ms on the same road. I checked that the two versions give the same answer for every sample of all 17 recorded roads. Dropping flat edges also means the division can never be by zero, so no `np.errstate` is needed.
2. **The 5-mile limit is made inclusive explicitly.** scipy's `distance_upper_bound` is strict: I checked that a point exactly at the bound comes back as `inf`. The architecture says the limit is inclusive, so the bound passed is `np.nextafter(chord(radius), inf)`, the next float up. No test case can sit exactly on 5 miles in floating point (CO-02 is 4.9, CO-04 is 5.1), so this is not tested. The 10-mile thinning limit is inclusive through `searchsorted(..., side="right")`, and CO-15 tests that.
3. **Repeated points are removed in `resample`** before interpolating, because `np.interp` expects distances that rise from one point to the next. GE-07 covers this.
4. **Station-ID order by position.** `stations_along` sorts by mile, price, then index position. That equals station-ID order because `StationIndex` is in station-ID order (its docstring says so).
5. **Test borders for GE-10 to GE-13.** Each case gives only one box, but `longest_run_abroad` needs both keys. GE-10 and GE-11 give the GE-13 box as `MEX`; GE-13 gives the GE-10 box as `CAN`. Neither is ever tested in those cases, because the road stays on one side of the middle latitudes. GE-12 gives its box as both, to show neither country is tested between 32.8 and 41.6 degrees N. GE-11's "two boxes" are written as **one C-shaped outline**, because a country in `borders` is one outline. The road along 79.5° W passes through it at 45.0–45.2° N and again at 45.5–45.7° N.

## 6. Unclear in the documents, and things I am not sure of

1. **GE-17 wording against the skeleton.** GE-17 expects each country "with at least one outline". The skeleton's `load_borders` returns `dict[str, np.ndarray]`, one outline per country, and `data/borders.json` holds exactly one per country (the largest, per `data/README.md`). I followed the skeleton. The test checks for two keys, `CAN` and `MEX`, each an array of shape (n, 2) with at least 4 rows. Suggest rewording GE-17 to "each one outline".
2. **`resample` on a road of length zero divides by zero.** If every point is the same, our own length is 0 and the scale `total_miles / own_miles` fails. The architecture says a road under half a mile is answered as invalid, so the caller (`planner.py`) must check the length **before** calling `resample`. I did not add a guard, following "no handling for cases that cannot happen", but the planner's builder should know.
3. **CO-01 "off_route_miles 0.0"** is asserted within 1e-9, not as exactly 0.0. The station and the road point go through `to_xyz` separately, and numpy's vectorised `sin` and `cos` are not promised to give bit-identical results across array lengths, so an exact check could fail on another machine for no real reason. CO-01's mile, price, station and point are checked exactly.
4. **Price ties use floats.** Sorting and thinning compare `index.price` (floats), not the exact decimals. Prices of up to 8 decimals in the 2-to-5-dollar range map to distinct, correctly ordered floats, and equal decimals give equal floats, so the order is the same. Noted in case a reviewer asks.
5. **The speed test's limit** is the brief's 200 ms, about 100 times the measured time. It will only catch a gross slowdown, as intended.
