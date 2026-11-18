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

- [ ] No key, password, machine path or personal data in any tracked file.
- [ ] A fresh local clone starts with one command and answers.
- [ ] The suite and lint pass in the clone.
- [ ] Each of the ten acceptance checks has recorded evidence.
- [ ] The public repository exists and holds every commit.
- [ ] A clone taken from GitHub starts with one command and answers.
- [ ] Nothing is left uncommitted.

## Result

(Filled in when the phase closes.)
