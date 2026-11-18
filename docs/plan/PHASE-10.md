# Phase 10: Test harness, Makefile, CI

Baseline: `PLAN.md`, Part 2, Phase 10. Written before Gate 9 closed; nothing here starts until it has.

## Inputs from Phase 9

- Work is on `next`. `v1.0.0` is the fallback.
- Dependencies are in: `redis`, `drf-spectacular`; dev: `pytest-cov`, `mypy`, `pip-audit`. No agent changes `pyproject.toml` or `uv.lock`.
- GNU make 4.4.1 is installed on the build machine.
- `tests/fixtures/roads/` holds 17 recorded answers of the public routing server, each the server's whole JSON answer.
- The Postman collection needs four roads that are not among them: Los Angeles to New York, St. Louis to Winston-Salem, Dallas to Phoenix, and Los Angeles to Seattle. The last was recorded during the Phase 1 research.

## Tasks

| ID | Task | Who | Owns |
|---|---|---|---|
| 10.1 | Record the three missing roads (three public routing calls) and add the research recording of Los Angeles to Seattle; list them in `tests/conftest.py` | Controller | `tests/fixtures/roads/`, `tests/conftest.py` |
| 10.2 | Coverage and type-check settings | Controller | `pyproject.toml` |
| 10A | The stand-in routing server, `ROUTING_SERVERS` from the environment, the end-to-end Compose file | Sonnet | `scripts/fake_osrm.py`, `tests/test_fake_osrm.py`, `docker-compose.e2e.yml`, and in `config/settings.py` the `ROUTING_SERVERS` lines only |
| 10B | Makefile, CI, pre-commit, Dependabot | Sonnet | `Makefile`, `.github/**`, `.pre-commit-config.yaml` |
| 10C | The fixes ruled out of the second audit (QA-0b) | Opus | the verifier, the routing client, the answer builder, the place lookup and their tests; architecture section 9 |
| 10.3 | From the first audit: both published ports bound to `127.0.0.1`; the database health check on the network address; a restart policy; `.env*` ignored | Controller | `docker-compose.yml`, `.gitignore`, `.dockerignore` |
| 10R | A fresh reviewer for 10C's fixes, not the controller | Opus | `reports/phase10-R.md` |

10A, 10B and 10C share no file and run in parallel. Briefs: `briefs/phase10-A-harness.md`, `briefs/phase10-B-make-ci.md`, `briefs/phase10-C-fixes.md`.

## Rulings

- Ruling: the "API with no route to the internet" part of the end-to-end run moves to Phase 12. Why: a container on an internal-only network cannot publish a port, and until nginx exists the API is what the host talks to. In this phase the proof is that `ROUTING_SERVERS` names only the stand-in and the stand-in's request count matches. Cost if wrong: none; Phase 12 adds the network.
- Ruling: three of the six remaining public routing calls are spent recording roads. Why: with them the whole Postman collection runs on the stand-in, in CI, for ever. Three calls remain for the final check.
- Ruling: `make dev` serves on port 8001, so it never collides with the Compose stack on 8000.

## Rulings on the review (10R)

Report: `reports/phase10-R.md`. No Critical, 1 Important, 5 Minor, 11 Notes. The reviewer reverted each of 10C's fixes in a copy and saw its test fail, and found R12's bracket sound. Every finding is accepted as true.

| Finding | Ruling | Fixed by |
|---|---|---|
| R10-01 R17 allows a stop 15 miles from any row of its city, so it cannot catch a search radius that is too wide | Fix as proposed: a stop lies within 5.01 miles of the mean of its city's rows, or of one row, which is how a station is placed. Tests: a stop 9.5 to 12 miles off the road is caught; every real answer still passes | 10C, second pass |
| R10-02 Padding the line with repeated end points hides miles from R12 | Fix as proposed: R13 rejects repeated points and allows the point count to be 0.25% or 2 points off | 10C |
| R10-03 `ROUTING_SERVERS` accepts three entries, which breaks "never more than two calls" | Fix: more than two entries is refused at start-up, like the other bad values | 10C |
| R10-04 CI installs from a stale lock file without complaint | Fix: `uv sync --locked` | Controller |
| R10-05 Dependabot does not watch the Compose files' images | Fix: add the `docker-compose` ecosystem | Controller |
| R10-06 Nothing tests that the stand-in logs the path without its query string | Fix: a test | 10C |
| R10-07 At stop cost 0 the two stop counts can still differ when the start purchase shows 0.00 | Fix: the start is always counted, in both | 10C |
| R10-08 Architecture section 6 still says a final `Mexico` or `Canada` is always outside coverage | Fix the sentence: unless the text ended in USA. The behaviour for comma-free texts such as `Tijuana Mexico USA` (unknown place, no suggestions) stands: the caller said USA | 10C |
| R10-09 "No road, whatever the status short of a server error" is tested only at 400 and 200 | Fix: tests for a 404 and a 503 carrying a "no road" body | 10C |
| R10-10 Any 400 ends the request, even one that is not the routing server's own | Stands, as ruled in Phase 9. One sentence in section 9 says so | 10C |
| R10-11 The stand-in answers 404 for an unknown path; the real server answers 400 | Fix: 400 `InvalidUrl`, as the real server | 10C |
| R10-12 A bare string as `routing_hosts` is read as a set of letters | Fix: a string raises `TypeError` | 10C |
| R10-13 The verifier's copy of the hand-added places is held only loosely to the application's | Fix: the test compares the two tables directly | 10C |
| R10-14 No job has a time limit; Newman has no request timeout; the count of routing requests is not enforced | Fix: 20 minutes per job, a 60-second request timeout, and the end-to-end check requires exactly 8 routing requests | Controller |
| R10-15 `check --deploy` exits 0 on warnings | Carried: Phase 11 adds the step with `--fail-level WARNING` | Phase 11 |
| R10-16 A test comment and a catalogue row still describe the removed 0.005-gallon rule | Fix both | 10C |
| R10-17 10B's report gives a delay the Makefile does not have | Correct the report's row | Controller |

The second pass is re-read by the reviewer, not by the controller alone.

## Gate 10 checklist

- [ ] The controller has read both diffs.
- [ ] The suite passes with the new tests; lint is clean.
- [ ] The end-to-end stack starts with one command and the whole Postman collection passes against it under Newman.
- [ ] The stand-in's request count equals the routing calls the collection's trips need, and no request left the machine for a routing server.
- [ ] `make help`, `make test`, `make lint` and `make up` work on the build machine, under Git Bash and PowerShell.
- [ ] Every finding ruled into this phase is fixed, and 10C's fixes have been read by a reviewer who did not write them.
- [ ] `next` is pushed and CI is green on it.
- [ ] `next` is merged into `main`, so the port binding reaches the public release.
- [ ] Committed.

## Result

(Filled in when the phase closes.)
