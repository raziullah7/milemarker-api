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

- [ ] The controller has read every diff.
- [ ] `uv run pytest` passes in full, run by the controller; Ruff is clean.
- [ ] The loader on the real CSV reports 8,151 rows, 6,738 stations, 6,626 saved, none unplaced.
- [ ] All 58 research place names resolve, and the everyday spellings of D-3 do too.
- [ ] The fuel plan matches the linear-programming solver and the brute-force search on random trips, and passes the hand-worked cases.
- [ ] Detroit to Buffalo registers over 200 miles abroad; the fifteen roads that stay in the USA register 25 or less.
- [ ] The border test takes 40 ms or less on the longest recorded road.
- [ ] The routing client builds the correct address for each server and retries only when it should.
- [ ] The pure modules import nothing from Django (PJ-02).
- [ ] CO-17 added and passing.
- [ ] Committed, one commit per task.

## Result

(Filled in when the phase closes.)
