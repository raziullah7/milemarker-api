# Phase 7: Demo and docs

Baseline: `PLAN.md`, Phase 7. Two builders in parallel, on files that do not overlap.

## Inputs from Phase 6

- `docker compose up --build` starts PostgreSQL and the API. The stack is running, API on port 8000.
- Measured on the finished API: a new coast-to-coast trip takes about 19 ms of our own work on top of the routing call; a repeat about 1 ms; the same trip with another stop cost about 11 ms.
- `scripts/live_check.py` runs every documented live case. `docs/test-cases.md` holds the results.
- From the Phase 1 research (`reports/phase1-R2-postman.md`): collection format v2.1 runs under Newman 6.2.3, proved by a real run. Drawing a map inside Postman was not verified.
- Live routing calls used: about 83 of 100. The trips already in the running API's cache cost nothing: New York to Los Angeles (any stop cost) and Dallas to Houston.

## Tasks

| ID | Builder | Model | Owns |
|---|---|---|---|
| 7P | Postman collection | Sonnet | `docs/postman/milemarker.postman_collection.json` |
| 7R | README and document updates | Sonnet | `README.md`; `docs/backend-architecture.md` sections 4 and 14 only |

Briefs: `briefs/phase7-P-postman.md`, `briefs/phase7-R-readme.md`.

## Gate 7 checklist

- [ ] The controller has read both.
- [ ] The controller runs the collection with Newman against the running API: every check passes (PM-01).
- [ ] The collection has the three folders and requests PM-02 lists, each request with at least one check.
- [ ] The README's commands work as written (checked in full in Phase 8, from a fresh clone).
- [ ] The map of the New York to Los Angeles answer draws in geojson.io (M01), checked by the controller in a browser.
- [ ] Committed.

## Result

(Filled in when the phase closes.)
