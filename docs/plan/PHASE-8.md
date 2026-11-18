# Phase 8: Final verification

Baseline: `PLAN.md`, Phase 8. All of this phase is done by the controller.

## Inputs from Phase 7

- Everything is built and committed: the API, 348 tests, the Docker path, the README, the Postman collection.
- The README names `https://github.com/raziullah7/milemarker-api.git`.
- About 91 of the 100 allowed live routing calls are used.

## Steps

| # | Step | Proves |
|---|---|---|
| 1 | Search every tracked file for keys, passwords, machine paths and personal data | FC-04 |
| 2 | Stop the running stack and delete its database volume, so the next start is truly clean | — |
| 3 | Clone the repository into an empty folder and follow the README exactly: `docker compose up --build` | FC-01, CT-01, acceptance check 9 |
| 4 | In the clone: Dallas to Houston, its cached repeat, a misspelt place, an unknown address | FC-01, CT-04 |
| 5 | In the clone: the suite in a container; then `uv sync`, `uv run pytest`, `uv run ruff check .` | FC-02, FC-03 |
| 6 | Write the evidence for the ten acceptance checks | requirements §9 |
| 7 | Create the public repository `raziullah7/milemarker-api` and push `main` | the deliverable |
| 8 | Clone from GitHub into an empty folder, `docker compose up --build`, one request | acceptance check 9, from the public address |

## Gate 8 checklist

- [x] No key, password, machine path or personal data in any tracked file.
- [x] A fresh local clone starts with one command and answers.
- [x] The suite and lint pass in the clone.
- [x] Each of the ten acceptance checks has recorded evidence.
- [x] The public repository exists and holds every commit.
- [x] A clone taken from GitHub starts with one command and answers.
- [x] Nothing is left uncommitted.

## Result

Closed 18 Nov 2026. Every gate item passed. One acceptance check, the Loom and the submission, is the candidate's and is open.

### Gate evidence

All run by the controller.

| Gate item | Evidence |
|---|---|
| No key, password, machine path or personal data | All 145 tracked files searched. The only password is `milemarker`, the local database default. All 24 commits carry the GitHub no-reply address, checked locally and again through the GitHub API after the push |
| A fresh local clone starts with one command | Stack stopped and its volume deleted first. Clone into an empty folder (24 commits, 145 files, no `.env`), `docker compose up --build -d`. Log: the loader's counts ending `Saved: 6626`, then gunicorn listening |
| Requests in the clone | Dallas to Houston: 200, 239.6 miles, 1 stop, $68.62, 1 routing call. Its repeat: 0 routing calls, cache hit, 0.3 ms of own work. `Chicgo, IL`: 400 `unknown_place`, suggestions starting with `Chicago, IL`. An unknown address: 404 `not_found` |
| The suite and lint in the clone | In a container: 348 passed. From source: `uv sync`, `uv run pytest` 348 passed, 1 deselected (the slow test, by its marker); `uv run ruff check .` clean; 52 files already formatted |
| The public repository | `https://github.com/raziullah7/milemarker-api`, public, default branch `main`. The remote head equals the local head |
| A clone from GitHub starts with one command | Clone from the public address into an empty folder, `docker compose up --build -d`: `Saved: 6626`; Dallas to Houston returns 200 with the same figures and a map of 4 features |
| Restart over existing data (CT-02) | `docker compose down`, `up -d`: `Saved: 6626`, 6,626 rows, Dallas to Houston 200 |

### The ten acceptance checks

| Check | Evidence | Result |
|---|---|---|
| 1. New York to Los Angeles, fewer than 10 stops | Live case P01: 200, 2,800.6 miles, 7 stops, $867.27 | PASS |
| 2. No stretch over 500; gallons = distance ÷ 10; total = sum of costs | The independent verifier's rules R1, R3 and R4 on P01's live response, and on every 200 of the live run | PASS |
| 3. One routing call; none on a repeat or with another stop cost | P01 reports 1; P02 and P03 report 0 | PASS |
| 4. A trip under 500 miles costs more than 0 | P08, P12 and P19 in the live run; Dallas to Houston again in this phase, $68.62 | PASS |
| 5. Los Angeles as the start: first fill-up distance and a warning | P05: 120.6 miles to the first station, a warning present | PASS |
| 6. The four refusals | N06 (Honolulu, 422) and N03 (unknown name, 400), with tests EP-15 and EP-18 proving no routing call; N11 (Detroit to Buffalo, 252.0 miles abroad); N12 (Los Angeles to Seattle, a gap of 885.3 miles from mile 0) | PASS |
| 7. The map shows the route with the stops | M01 in geojson.io, with the line reduced to 39 points to paste it; rules R11 and R12 on every live 200 | PASS, with that limit |
| 8. The fuel tests, including the two exact methods | Part of the 348; the slow comparison passed in Phases 3 and 5 | PASS |
| 9. A fresh clone starts with one Compose command, no key | This phase, from the local repository and from GitHub | PASS |
| 10. Loom recorded, both links sent before Friday 20 Nov 2026, 8 pm | Not started. The candidate's | OPEN |

### Not verified

- The map inside Postman's Visualize tab, and importing the collection into the Postman app. The collection was run with Newman only.
- The full-size map pasted into geojson.io. A reduced line was pasted.
- The full live run against the Compose stack (CT-03). It was run in full from source, and as a short list of nine cases against the container.
- A machine with only git and Docker. Both clones were made on the build machine; the API ran only in its containers.

### Deviations

- Three live routing calls, not two: one more for the restart check CT-02, which empties the cache.

### Live routing calls

About 94 of the 100 allowed: 91 before this phase, 3 in it, all Dallas to Houston.

### Left for the candidate

- Record the Loom: the collection's Demo folder in Postman, then a quick walk through the code.
- Send the repository link and the Loom link in the hiring thread before Friday 20 Nov 2026, 8 pm.
