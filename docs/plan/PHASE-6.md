# Phase 6: One-command start

Baseline: `PLAN.md`, Phase 6. One builder packages the finished API so `docker compose up` starts everything.

## Inputs from Phase 5

- The API is finished and verified: 348 tests pass, and the live run of every documented case passes 49 of 49.
- `docker-compose.yml` already has the PostgreSQL 17 service, healthy check included.
- The server must run as one process with threads, so the in-memory cache and station index are shared, and must not use gunicorn's `--preload` (the start-up warm-up touches the database).
- Live routing calls used: about 77 of 100. This phase uses a short list of live cases, not the full run.

## Task

| ID | Builder | Model | Owns |
|---|---|---|---|
| 6K | Dockerfile and one-command start | Sonnet | `Dockerfile`, `.dockerignore`, `docker/entrypoint.sh`, `docker-compose.yml` |

Brief: `briefs/phase6-K-docker.md`. Report: `reports/phase6-K.md`.

## Gate 6 checklist

- [ ] The controller has read the diff.
- [ ] From a clean start with no volumes, `docker compose up` brings up PostgreSQL and the API; the API's log shows the loader's counts ending in 6,626 saved.
- [ ] The controller runs a short list of live cases against the container: P01, P02, P03, P08, N03, N06, N11, N12, N14. All pass.
- [ ] P02 against the container reports a cache hit: the API runs as one process (CT-04).
- [ ] The whole test suite passes inside a container.
- [ ] Stopping and starting again does not duplicate stations (CT-02).
- [ ] The local path still works: `uv run pytest` passes on the host.
- [ ] Committed.

## Result

(Filled in when the phase closes.)
