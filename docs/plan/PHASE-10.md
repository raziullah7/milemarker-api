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
