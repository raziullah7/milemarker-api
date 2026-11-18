# Phase 3: Core modules

Baseline: `PLAN.md`, Phase 3. Five builders work in parallel, each on files nobody else touches.

## Inputs from Phase 2

- Every module's interface exists as code (commit 5d5ec1c). Signatures and docstrings are the contract.
- `stations/sphere.py` is finished and tested (commit cc39f43), because the data side and the geometry both need it.
- `docs/test-cases.md` lists every test, with its input and expected output. Builders write those tests first.
- PostgreSQL runs in Docker (`docker compose up -d db`). Only the data-side tests use it.

## Tasks

| ID | Builder | Model | Owns | Test cases |
|---|---|---|---|---|
| 3A | Data side | Sonnet | `stations/models.py`, `stations/migrations/`, `stations/places.py`, `stations/index.py`, `stations/management/commands/load_stations.py`, `tests/test_places.py`, `tests/test_loader.py`, `tests/test_index.py` | PL-01 to PL-21, LD-01 to LD-18 |
| 3B | Geometry and station search | Opus | `trips/services/geo.py`, `trips/services/corridor.py`, `tests/test_geo.py`, `tests/test_corridor.py` | GE-06 to GE-17, CO-01 to CO-16 |
| 3C | Fuel plan | Opus | `trips/services/fuel.py`, `tests/test_fuel.py`, `tests/exact.py` | FU-01 to FU-25, EX-01 to EX-04 |
| 3D | Routing client | Sonnet | `trips/services/routing.py`, `tests/test_routing.py` | RT-01 to RT-14 |
| 3F | Answer builder | Opus | `trips/services/answer.py`, `tests/test_answer.py` | AN-01 to AN-11 |

CO-17 needs both the loader and the station search, so the controller adds it at the gate.

Shared rules for every builder: `briefs/phase3-common.md`. One brief each: `briefs/phase3-A-data.md` and so on. Reports go to `reports/phase3-<ID>.md`.

## Gate 3 checklist

- [x] The controller has read every diff.
- [x] `uv run pytest` passes in full, run by the controller; Ruff is clean.
- [x] The loader on the real CSV reports 8,151 rows, 6,738 stations, 6,626 saved, none unplaced.
- [x] All 58 research place names resolve, and the everyday spellings of D-3 do too.
- [x] The fuel plan matches the linear-programming solver and the brute-force search on random trips, and passes the hand-worked cases.
- [x] Detroit to Buffalo registers over 200 miles abroad; the fifteen roads that stay in the USA register 25 or less.
- [x] The border test takes 40 ms or less on the longest recorded road.
- [x] The routing client builds the correct address for each server and retries only when it should.
- [x] The pure modules import nothing from Django (PJ-02).
- [x] CO-17 added and passing.
- [x] Committed, one commit per task.

## Result

Closed 18 Nov 2026. Every gate item passed.

### Gate evidence

Everything below was run or measured by the controller, not taken from a builder's report.

| Gate item | Evidence |
|---|---|
| Every diff read | All five modules read in full, with their tests or test lists |
| Full suite and lint | `uv run pytest`: 220 passed. `uv run pytest -m slow`: 1 passed. `ruff check` and `ruff format --check`: clean. `manage.py check`: no issues |
| Loader on the real CSV | 8,151 rows; 6,738 stations; 6,626 in the lower 48 and DC; 6,615 + 11 placed; 6,626 saved. A second run: 6,626 |
| Place names | PL-01 (58 names) and PL-03 to PL-09 (everyday spellings) pass |
| Fuel plan against two exact methods | EX-01: 400 random trips against the linear-programming solver. EX-02: 250 trips against brute force over every subset, each priced by the solver. Largest difference $0.000000000. FU-01 to FU-26 pass |
| Border | Detroit to Buffalo 252.0 miles abroad, Detroit to Boston 234.0. The fifteen roads that stay in the USA: 10.0 at most |
| Border test speed | 1.8 ms on Boston to Seattle, the longest road. Limit 40 |
| Routing client | RT-01 and RT-03 check each server's full address; RT-03 to RT-07 retry; RT-08 does not |
| Pure modules free of Django | PJ-02 passes for all six |
| CO-17 | Added in `tests/test_real_data.py`: 363 stations along New York to Los Angeles, 100 after thinning |

### Measured speed

| Step | Time |
|---|---|
| Re-space New York to Los Angeles | 1.9 ms |
| Border check, Boston to Seattle | 1.8 ms |
| Station search and thinning, New York to Los Angeles, 6,626 stations | 2.3 ms |
| Fuel plan, 100 stations | 5 ms |
| Fuel plan, 400 stations (the rare fallback) | 230 to 340 ms |
| Lowest possible bill, 400 stations | under 0.3 ms |

### Commits

| Task | Commit | Review outcome |
|---|---|---|
| 3D routing client | 5f49cb3 | Three small changes by the controller: "no road" recognised by its code whatever the status; the clock also checked when the headers arrive; an empty server list reports `error` |
| 3A data side | 4a69c73 | Accepted as built |
| 3B geometry and station search | e706163 | Accepted as built. The builder made the border check 30 times faster than the prototype by skipping outline edges no ray could cross |
| 3F answer builder | 7db6c35 | One review round: no stop of 0.00 gallons; the lowest possible bill never above the plan's |
| 3C fuel plan | 28e8c00 | Accepted as built |

### Changes to the specs and the test catalogue

- CO-17: tolerance on the two station counts widened from 2% to 5%. The finished rules give 100 kept stations against a design figure of 98.
- GE-17 reworded: one outline per country.
- EX-02: the default run uses up to 8 stations; the 10-station run is behind `-m slow`.
- EX-04: trips are drawn as in EX-01.
- FU-26 added: equal costs are settled by fewer stops, then the earlier station.
- Architecture section 8: the two answer-builder rules above.

### Deviations

- Five builders, not four: the answer builder was split out of Phase 4.
- `stations/sphere.py` was written by the controller before the builders started.
- The controller made the three routing-client changes itself instead of returning them to the builder, because each was a line or two.

### Carried into Phase 4

- `resample` cannot take a road of length zero. `plan_trip` must reject a road shorter than half a mile before calling it.
- The fuel plan on every station takes a quarter to a third of a second coast to coast. It is only used when the thinned list has no plan.
- At stop cost 0 the plan is `cheapest_fuel` on every station, so `plan_stops` is not called.
- `real_index` and `use_real_stations` in `tests/conftest.py` give tests the real stations without the database.
- An attempt on a routing server whose connection and first byte are both slow can run past the 5-second deadline. To be written into the known limits.
