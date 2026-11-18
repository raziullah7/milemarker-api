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

- [x] The controller has read both.
- [x] The controller runs the collection with Newman against the running API: every check passes (PM-01).
- [x] The collection has the three folders and requests PM-02 lists, each request with at least one check.
- [x] The README's commands work as written (checked in full in Phase 8, from a fresh clone).
- [x] The map of the New York to Los Angeles answer draws in geojson.io (M01), checked by the controller in a browser.
- [x] Committed.

## Result

Closed 18 Nov 2026. Every gate item passed, one with a stated limit.

### Gate evidence

| Gate item | Evidence |
|---|---|
| Both read | The README read in full by the controller; the collection's structure and checks listed by a script |
| Newman (PM-01) | Controller's run against the running container: 14 requests, **111 assertions, 0 failed**, exit code 0. The builder's own run gave the same totals |
| Folders and requests (PM-02) | 1. Demo: 4 requests; 2. More trips: 5; 3. Errors: 5. Each request has between 4 and 13 checks |
| README commands | Taken from `docker-compose.yml`, the entrypoint and `pyproject.toml`. Proved from a fresh clone in Phase 8 |
| Map in geojson.io (M01) | Checked by the controller in a browser: the line from New York to Los Angeles, seven orange stop markers, a green start and a blue finish; clicking a stop shows its `title` and marker colour |

### Limits of what was checked

- **The map was pasted with a reduced line.** The controller's tools could not pass the full 133 KB map, so the line was cut from 5,594 points to 39. The stops, the start, the finish and their properties were the real ones. The full-size paste was not done.
- **The map inside Postman was not seen.** The four Demo requests carry a script that draws it in the Visualize tab. It runs under Newman without error, but nobody has opened it in the Postman app. The README points only to geojson.io.
- **The collection was not imported into the Postman app,** only run with Newman.

### Changes by the controller

- README: the clone address, and three sentences reworded.
- `docs/requirements.md`: the note on speed targets, and the finished API's figures beside D-9's design measurements.
- `docs/backend-architecture.md`: the opening note on which figures are design measurements and which are the finished API's; the finished figures in section 8.

### Deviations

- The collection checks the routing-call counts as relations, so it passes whether or not the trips are already cached. A first request on a fresh server (1 call, no cache hit) is therefore proved by the live run, not by the collection.

### Live routing calls

About 91 of the 100 allowed: 83 before this phase, 6 by the builder's Newman run, 2 by the controller's (the two refused roads, which are never cached).

### Carried into Phase 8

- The README names `https://github.com/raziullah7/milemarker-api.git`. The repository must be created with that name.
- At most a handful of live routing calls remain. The fresh-clone check uses Dallas to Houston only.
