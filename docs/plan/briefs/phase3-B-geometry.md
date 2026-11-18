# Brief 3B: geometry and station search

Read `docs/plan/briefs/phase3-common.md` first. It applies in full.

## Goal

Given the road the routing service returns, lay evenly spaced mile markers along it, tell whether it leaves the USA, and find the stations along it.

## Your files

- `trips/services/geo.py`
- `trips/services/corridor.py`
- `tests/test_geo.py`, `tests/test_corridor.py`
- Report: `docs/plan/reports/phase3-B.md`

## Read

- `docs/backend-architecture.md` section 5 ("Why re-space the road", "One length, not two"), section 7 (all), section 14 (the border check paragraph)
- `docs/requirements.md` decisions D-4, D-5, D-10, D-11
- `docs/test-cases.md` sections 2.1, 2.4 and 2.5
- The finished helpers you build on: `stations/sphere.py`, `stations/types.py` (`StationIndex`, `build_index`)
- Prototypes: `docs/plan/research/scripts/s4b_stops.py` (re-spacing, search, thinning) and `s8_foreign.py` (border test)

## Test cases

GE-06 to GE-17 and CO-01 to CO-16, exactly as `docs/test-cases.md` gives them. GE-01 to GE-05 are already done in `tests/test_sphere.py`. CO-17 is not yours: it needs the station loader.

## Decisions already made

- Use `scipy.spatial.KDTree` (scipy's own documentation says to prefer it to `cKDTree`). With `distance_upper_bound`, a station with no road point in range comes back with distance `inf`.
- The search builds its tree over the road points and asks, for every station at once, for the nearest road point. Distances in the tree are straight lines on the unit sphere: convert with `chord()` and `arc()`.
- `resample`: measure with `haversine_miles`, re-space by linear interpolation of latitude and longitude along the cumulative distance, then scale the markers and set the last one to `total_miles` exactly.
- `longest_run_abroad`: point-in-outline by ray casting, written with numpy. Sample every `sample_every_miles`; test a sample against `"CAN"` only if it is north of 41.6°, and against `"MEX"` only if it is south of 32.8°.
- Both distance limits are inclusive (architecture section 7).
- `thin()` compares each station with every station it is given, including ones that are themselves dropped (CO-16).
- Recorded roads: `from tests.conftest import load_road`; `load_road("nyc_la")` returns `(coords, distance_miles)`. The names are the keys of `ROADS` in `tests/conftest.py`. The real outlines are at `data/borders.json`.

## Speed

The whole request has 100 ms for our own work. Measure, on this machine, best of five runs, and put the figures in your report:

- `resample` on the New York to Los Angeles road
- `longest_run_abroad` on the Boston to Seattle road (`bos_sea`), which must be **40 ms or less**
- `stations_along` plus `thin` on the New York to Los Angeles road with 6,626 stations spread at random over the lower 48 (seeded)

Add one test for the border check with a generous limit (200 ms) so a gross slowdown is caught without making the suite flaky.
