# Phase 1: Research, corrected specs, test design

Baseline: `PLAN.md`, Phase 1. No code is written in this phase.

## Inputs

- The two specs in `docs/`.
- `PLAN.md` Appendix A: 21 decisions from the independent read, plus the PostgreSQL decision.
- `phase-material.md`: live cases, correctness rules, use-case list (drafts for the docs).
- Research prototypes and cached data in `docs/plan/research/`.

## Tasks

| ID | Task | Owner | Writes | Order |
|---|---|---|---|---|
| 1.1 | Verify the stack against primary docs | R1, Sonnet | `docs/plan/reports/phase1-R1-stack.md` | starts at once |
| 1.2 | Verify Postman, Newman, map view | R2, Sonnet | `docs/plan/reports/phase1-R2-postman.md` | starts at once |
| 1.3 | Apply Appendix A and the PostgreSQL decision to both specs | controller | `docs/requirements.md`, `docs/backend-architecture.md` | starts at once |
| 1.4 | Cities whose table rows are over 10 miles apart: list them, choose the row | controller | architecture §6, `docs/plan/reports/phase1-cities.md` | with 1.3 |
| 1.5 | Confirm Los Angeles to Seattle has no fuel plan, on a real route | controller | `docs/plan/reports/phase1-no-fuel.md` | with 1.3 |
| 1.6 | Write `docs/use-cases.md` and `docs/test-cases.md` | R3, Opus | those two files | after 1.3 to 1.5 |
| 1.7 | Write `docs/prd.md` | R4, Sonnet | that file | after 1.3 |

Briefs are in `docs/plan/briefs/`. Agents write their full report to the file named above and return a short summary.

## Gate 1 checklist

- [x] Every line of Appendix A has a matching line in a spec (controller lists the matches in the Result).
- [x] Every requirement ID appears in at least one use case or test case.
- [x] Every test case states its exact input and its expected output.
- [x] Los Angeles to Seattle confirmed on a real route.
- [x] R1 and R2 reports cite a primary source for each fact.
- [x] The five docs are committed.

## Result

Closed 18 Nov 2026. Every gate item passed.

### Gate evidence

| Gate item | Evidence |
|---|---|
| Every line of Appendix A is in a spec | See the table below |
| Every requirement ID is covered | A script found all 52 IDs (19 FR, 18 NFR, 15 D) in the traceability table of `use-cases.md` |
| Every test case has an input and an expected output | The same script checked all 257 rows of `test-cases.md`; IDs are unique and every cross-reference between the two documents resolves |
| Los Angeles to Seattle confirmed | `reports/phase1-cities-and-no-fuel.md`: first station at mile 886, in Halsey, Oregon |
| Research reports cite sources | `reports/phase1-R1-stack.md` and `reports/phase1-R2-postman.md` |

### Where each Appendix A decision landed

| # | Decision | In the specs |
|---|---|---|
| 1 | Retry server's path | Architecture §9 |
| 2 | Border test sampling | Architecture §14 |
| 3 | First fill-up | Requirements D-1; architecture §5, §7, §8, §11 |
| 4 | "Far" | Requirements FR-14; architecture §11 |
| 5 | Two caches | Requirements D-15, NFR-2; architecture §10 |
| 6 | Rounding | Requirements D-14; architecture §8 |
| 7 | Lowest possible bill | Architecture §8 |
| 8 | Thinning never hides a plan | Requirements D-10; architecture §8 |
| 9 | Ties | Requirements D-6, D-10; architecture §6, §7 |
| 10 | Order of checks | Architecture §2, §5 |
| 11 | Place spellings | Requirements D-3; architecture §6 |
| 12 | Cities under several counties | Requirements D-5; architecture §6 |
| 13 | Hand-added places | Architecture §6 |
| 14 | Error details | Requirements FR-11; architecture §11 |
| 15 | Routing failures | Architecture §9 |
| 16 | In-memory index | Architecture §6 |
| 17 | Layering | Architecture §3, §4 |
| 18 | Fuel routine | Architecture §8 |
| 19 | No fuel on the road | Requirements §2, FR-10, check 6; architecture §8, §16 |
| 20 | Coordinates as input | Requirements FR-17 (nice-to-have); architecture §16 |
| 21 | Test independence; easy to run | Architecture §8; requirements NFR-9 |

### Decisions taken on what the test designer flagged

R3 reported sixteen places where the specs were silent or disagreed. Each is now settled in the specs.

| # | Gap | Decision |
|---|---|---|
| 1 | With stop cost 0 the plan used the thinned list, so it could cost more than the "lowest possible" bill | At stop cost 0 the plan is the greedy result on every station, so the two are the same figure |
| 2 | Rounding of the lowest possible bill | Rounded exactly as the plan's |
| 3 | Start-station ties | Cheapest, then lowest station ID |
| 4 | Which field a same-place error names | `finish` |
| 5 | A road under half a mile | Invalid request, after the one call that revealed it |
| 6 | `cache_hit` when only the road was cached | False; `routing_calls` is 0 |
| 7 | "Within 5 / 10 miles" | Both inclusive; thinning compares against the whole list |
| 8 | Place parsing edge cases | A country counts only as a whole final part; the Manhattan alias applies only with NY; a bare state name is unknown |
| 9 | HEAD and OPTIONS | Left to the framework's defaults |
| 10 | Mixed routing failures | `timeout` only when every attempt timed out |
| 11 | What `timings_ms.own` covers | Our work up to handing the answer to the framework |
| 12 | 404 and 500 bodies depended on the debug setting | A catch-all route and the error handler make them JSON in every mode |
| 13 | FR-17 to FR-19 and NFR-18 have no contract | Correct: they are nice-to-haves and are not built |
| 14 | `find_gap` returned only the start | It returns the start and the length |
| 15 | "Digit for digit" prices | Compared as exact decimal values |
| 16 | Some design figures were measured before the named-county rule | Those cases assert ranges, and are re-measured in Phase 5 |

Changes the controller made to R3's documents: RT-14 and its row in section 6 (decision 10), FU-24 (decision 14), EP-36 and the live-run preconditions (decision 12), and UC-12 A1 (decision 10).

### Deviations

- The plan folder was first created beside the project. The user ruled that every document lives in `docs/`, so it was moved to `docs/plan/`.
- The dependency install for Phase 2 was started early and allowed to finish. Nothing else in Phase 2 was done before this gate.
- Postman's own map view could not be verified by R2. The map will be checked in geojson.io in Phase 7.

### Carried into Phase 2

- More recorded roads are needed as test data than first prepared: the fifteen of GE-16 and Detroit to Boston.
- `KDTree`, the streamed deadline for the routing client, `pytest-socket`, no `CommonMiddleware`, and a route that accepts the address with or without a trailing slash.
