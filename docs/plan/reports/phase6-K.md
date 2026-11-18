# Phase 6K: one-command start with Docker

Status: DONE. Files: `Dockerfile`, `.dockerignore`, `docker/entrypoint.sh`, `docker-compose.yml` (db service untouched; `api` and `test` added; header comment rewritten), this report.

## Proof (all run on Docker 29.9.2)

1. `docker compose down -v` then `docker compose up --build -d`. `docker compose logs api`:
```
Applying stations.0001_initial... OK
Rows read: 8151
Stations: 6738
In the lower 48 and DC: 6626
Placed from the places table: 6615
Placed from hand-added places: 11
Saved: 6626
[INFO] Starting gunicorn 27.0.1
[INFO] Listening at: http://0.0.0.0:8000 (1)
[INFO] Using worker: gthread
[INFO] Booting worker with pid: 69
[INFO] Control socket listening at /home/app/.gunicorn/gunicorn.ctl
```
2. Dallas to Houston, twice (200 both times):
```
"meta":{"routing_calls":1,"cache_hit":false,"routing_server":"router.project-osrm.org",...}
"meta":{"routing_calls":0,"cache_hit":true,...}
```
Note for the budget: three Dallas requests were sent in total. The first was against the first build (before the home-directory fix below); the stack was then rebuilt, which empties the in-memory cache, so the proof pair reached the routing server once more. That is two requests that reached it; the cached ones did not.
3. Errors, no routing call:
   - Unknown address `GET /api/v1/nothing`: 404 `{"error": {"code": "not_found", "message": "There is nothing at this address. ...", "details": {}}}`
   - `start=Chicgo, IL`: 400 `{"error":{"code":"unknown_place","message":"Could not find 'Chicgo, IL'. ...","details":{"field":"start","query":"Chicgo, IL","suggestions":["Chicago, IL","Cisco, IL",...]}}}`
   - (A made-up street address as `start` is also 400 `unknown_place`, with no suggestions.)
4. `docker compose --profile test run --rm test`, last line: `====================== 348 passed, 1 deselected in 38.26s ======================`
5. `docker compose down`, `docker compose up -d`: log shows `No migrations to apply.` then `Saved: 6626` then `Listening at`; `select count(*) from stations_fuelstation` gives `6626`.
6. `docker compose config`: `image: postgres:17`; api `DATABASE_URL: postgresql://milemarker:milemarker@db:5432/milemarker`.
7. Image sizes (`docker images`): `milemarker-api-api` 641MB disk usage (150MB content), `milemarker-api-test` 697MB (165MB). Most of it is numpy and scipy.
8. Stack left running: `api` up on 8000, `db` healthy on 5432.

## Changes from R1's Dockerfile
- The `ghcr.io/astral-sh/uv:0.11.19` tag exists (the build pulled it). Only `/uv` is copied, not `/uvx`, which is not used.
- Removed `UV_NO_DEV` and the second `uv sync`: the project has no build system, so installing the project does nothing. Dev tools are chosen by the `WITH_TEST_TOOLS` build argument (`--group dev` or `--no-dev`).
- `PATH` set up front instead of after the code copy.
- Added a non-root `app` user. It is created with a home directory, because gunicorn 27 writes a control socket to `~/.gunicorn` and logged `Permission denied: '/home/app'` without one (found by the first build). I kept the exact gunicorn command rather than adding `--no-control-socket`.
- The `test` service runs `pytest -p no:cacheprovider`, since the app user cannot write to `/app` and pytest otherwise printed a cache warning.
- `CMD ["sh", "docker/entrypoint.sh"]` so the executable bit does not matter. `.gitattributes` (`* text=auto eol=lf`) already keeps the script LF on Windows; no change needed.

## Unsure of
- The `app` user owns nothing, so code is read-only to it; tests that write files inside `/app` would fail (none do: 348 pass).
- A Compose `up --build` on a fresh clone was not tested from a clone, only from this working tree (`.dockerignore` excludes `.git`, `.venv`, `.env`).
