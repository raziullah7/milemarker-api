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

- [x] The controller has read the diff.
- [x] From a clean start with no volumes, `docker compose up` brings up PostgreSQL and the API; the API's log shows the loader's counts ending in 6,626 saved.
- [x] The controller runs a short list of live cases against the container: P01, P02, P03, P08, N03, N06, N11, N12, N14. All pass.
- [x] P02 against the container reports a cache hit: the API runs as one process (CT-04).
- [x] The whole test suite passes inside a container.
- [x] Stopping and starting again does not duplicate stations (CT-02).
- [x] The local path still works: `uv run pytest` passes on the host.
- [x] Committed.

## Result

Closed 18 Nov 2026. Every gate item passed.

### Gate evidence

Run by the controller unless marked.

| Gate item | Evidence |
|---|---|
| Diff read | `Dockerfile`, `docker/entrypoint.sh`, `.dockerignore` and the Compose file read in full |
| Clean start | Builder: `docker compose down -v`, then `docker compose up --build -d`. The API log shows the six loader lines ending `Saved: 6626`, then gunicorn listening. Controller confirmed the same lines in the running stack's log |
| Short list of live cases against the container | `scripts/live_check.py --only P01,P02,P03,P08,N03,N06,N11,N12,N14`: **9 cases, 9 passed** |
| One process (CT-04) | P02 against the container: answer cache hit, 0 routing calls, 9.1 ms round trip |
| Suite inside a container | `docker compose --profile test run --rm test`: 348 passed |
| No duplicate stations after a restart (CT-02) | Builder: `down`, `up -d`, the log shows `Saved: 6626` again. Controller: `select count(*)` gives 6,626 |
| Local path still works | `uv run pytest` on the host: 348 passed |

### What was built

- **`Dockerfile`**: `python:3.12-slim`, dependencies installed by uv from the lock file in their own layer, the code copied after, a non-root user. One build argument adds the test tools for the test image.
- **`docker/entrypoint.sh`**: migrate, load the stations, then gunicorn with one worker and four threads, without `--preload`.
- **`docker-compose.yml`**: the `api` service beside `db`, started when the database is healthy, and a `test` service in its own profile.
- Image size: 641 MB for the API image, 697 MB with the test tools.

### Found while building

- gunicorn 27 needs a home directory for its control socket, so the non-root user has one.
- The test command passes `-p no:cacheprovider`, because the application user cannot write to the code folder.
- The uv image tag `0.11.19` exists.

### Deviations

- The builder reached the public routing server twice, not once: its first build had the gunicorn error above, and rebuilding emptied the cache.
- The build was proved from the working folder, not from a fresh clone. A fresh clone is Phase 8.

### Live routing calls

About 83 of the 100 allowed: 77 before this phase, 2 by the builder, 4 by the controller's short list.

### Carried into Phase 7

- The stack is running: API on port 8000. The Postman collection can be run against it.
- Commands for the README are in the comment block at the top of `docker-compose.yml`.
