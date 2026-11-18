# Phase 15: the review's proven findings (release 2.1.0)

Baseline: `v2.0.0` (b3d3bef).

## Why

An independent review of the whole codebase at `v2.0.0` made 11 findings. Four proof agents then reproduced all of them, each in its own copy of the code, and the controller re-ran every proof. Measured against the proof, 9 findings are Minor and 2 are not an issue; nothing is Critical or Important. The owner asked for the user-visible bugs to be fixed and every document to be true. A first plan, which fixed all 11 in code, was judged over-engineered for 3 of them. The owner chose the balanced plan below.

| ID | Finding, as proved | Action |
|---|---|---|
| I1 | A city given with no state is offered the same name in other states, in alphabetical order of state, cut at five. "Dallas" is offered GA, IA, NC, OR and PA. 8 of the 50 largest cities miss their own state. A misspelling with no state gets nothing. | Code: rank by US Census population; a no-state misspelling is matched against large places |
| I2 | Every repeat of a refused trip calls the routing server again (leaves the USA, no road, a road under half a mile): 3 requests make 3 calls. README line 3 says a repeat costs none. | Code: cache the refusal under the road key |
| M5 | With the database unreachable, `/route/` and `/health/` answer 500 `internal_error`. On Windows the driver hangs, because no connect timeout is set. | Code: 503 `stations_not_loaded`, and a connect timeout |
| M1 | The README gives "one request a second" as the reason for the rate limit, but one client can send 60 in a second, and up to 8 routing calls run at once. | Documents |
| M2 | HEAD runs the plan, which includes a routing call. | Documents only. RFC 9110 section 9.1 requires HEAD wherever GET is supported, and the result is cached. |
| M3 | Legs go up to 499.8 miles, and the detour from the road to a station uses no fuel (D-8). The README does not say so. | Documents |
| M4 | The full-list fallback takes 180 to 350 ms. No recorded road triggers it, and 1 of 209 random long trips did. | Documents: the measured figure |
| M6 | Redis is published on 127.0.0.1 with no password. Its values are pickled. | Documents |
| M7 | Stop 1 is drawn at the start but named after the nearest station. | Documents |
| M8 | The CDN files on the docs page carry no integrity hash. | Documents |
| M9 | The README says any road through Canada or Mexico is refused. The rule is a run of more than 25 miles. | Documents |

## Tasks

| ID | Task | Model | Owns |
|---|---|---|---|
| 15F1 | I1 | Sonnet | `stations/places.py`, `data/large_places.csv`, `data/README.md`, `scripts/extract_large_places.py`, `tests/test_places.py` |
| 15F2 | I2, M5, the cache version | Opus | `trips/services/planner.py`, `stations/index.py`, `config/settings.py`, `tests/test_api.py`, `tests/test_planner.py`, `tests/test_health.py`, `tests/test_index.py`, `tests/test_project.py` |
| 15D | Every document made true | Sonnet | the documents |
| QA-5 | Re-run the proofs on the new code; adversarial review of the diff | Opus | `reports/phase15-QA.md` |

Briefs: `briefs/phase15-F1-places.md`, `briefs/phase15-F2-backend.md`, then the documents and QA briefs.

## Rulings

- **M4, M6 and M8 change no code.** Why: M4's path is not triggered by any recorded road, and the slowness is already documented; fixing it would change a planning rule. M6 can be reached only from this machine, as Postgres with its published password can. M8 is a page with no cookies and no secrets. Cost if wrong: one of them is raised again after submission. Each gets one true sentence in the documents.
- **M5 reuses `stations_not_loaded`.** Why: when the database cannot be reached, the stations are in fact not loaded. A new code would change the contract, the schema and about 12 pins, and a client would gain nothing. Cost if wrong: the code name is slightly less precise; the message says what happened.
- **I1 ranks with census population.** Why: the places table has no size column. Ranking by county rows, or by station counts from the fuel file, was measured and ranks badly. The station index is not loaded when places are resolved (EP-32). Fuzzy matching over all 18,209 names took 29 ms and returned noise. Cost if wrong: one committed data file of about 800 rows from a public-domain source.
- **`CACHE_KEY_VERSION` goes to 2.** Why: the project's own rule. I2 adds a new shape of value under the road key. Cost: every trip is routed once more after the upgrade.

## Gate 15

- [ ] Ruff, format, mypy, the deployment check, the migration check, schema validation, and the OpenAPI document in sync
- [ ] The full suite in the container, with coverage of at least 98%, and the slow test
- [ ] Live, with requests that never route: `Dallas` suggests `Dallas, TX` first; `Dalas` suggests `Dallas, TX`; health is 200
- [ ] The database-down proof gives 503 on both addresses
- [ ] Postman on the stand-in: every assertion passes, 8 routing calls
- [ ] QA-5's findings ruled; Critical and Important fixed and re-reviewed
- [ ] CI green on `next`; merged into `main`; tagged `v2.1.0`
