# Brief 6K: one-command start with Docker

A Django API is finished and tested. A reviewer with only git and Docker must be able to clone the repository, run **one command**, and call the API. Your job is the packaging that makes that true.

The repository root is the folder you were given; every path is relative to it.

## Rules

- **Your files only:** `Dockerfile`, `.dockerignore`, `docker/entrypoint.sh`, `docker-compose.yml`, and your report `docs/plan/reports/phase6-K.md`. Do not change application code, tests, settings, `pyproject.toml` or `uv.lock`. If something in them blocks you, stop and say so in your report.
- No git commands that change anything. No other agents.
- Comment why, not what. Someone must be able to explain every line of these files in an interview. Nothing that is not needed.

## Read

- `docs/backend-architecture.md` sections 6 ("Loading into memory"), 10 and 12
- `docs/test-cases.md` section 7, rows CT-01 to CT-05 and FC-01
- `docker-compose.yml`, `config/settings.py`, `config/wsgi.py`, `pyproject.toml`, `.env.example`, `.gitattributes`
- `docs/plan/reports/phase1-R1-stack.md` sections H and I: researched facts about uv in Docker, the PostgreSQL image and gunicorn. The Dockerfile there was never built: treat it as a starting point and prove each line by building.

## What to build

**`Dockerfile`**
- Base `python:3.12-slim`. Install dependencies with uv from `uv.lock`, frozen, so the image has exactly the locked versions. Pin the uv image you copy the binary from to a version tag that exists (check by building; do not use `latest`).
- Dependencies in one layer, the project's code in a later one, so a code change does not reinstall everything.
- One build argument decides whether the test tools are installed: off for the API image, on for the test image. Nothing else differs between the two.
- Run as a non-root user.

**`docker/entrypoint.sh`**, in this order: apply migrations; load the stations (`python manage.py load_stations`, which replaces the table and is safe to repeat); then `exec` the server:

```text
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1 --threads 4
```

- One worker on purpose: the cache and the station index live in the process's memory. Say so in a comment.
- **Never `--preload`:** the server reads the stations from the database as it starts, and that must happen inside the worker.
- Stop on the first failing step (`set -e`), so a failed migration or load does not start a server with no stations.
- The file must work when the repository is cloned on Windows: start it as `sh docker/entrypoint.sh`, so it does not depend on the executable bit, and confirm `.gitattributes` keeps it with LF line endings.

**`docker-compose.yml`**: keep the existing `db` service as it is and add:
- `api`: built from the Dockerfile, `DATABASE_URL` pointing at the `db` service, port `${API_PORT:-8000}:8000`, started only when `db` is healthy.
- `test`: the same image built with the test tools, with the same `DATABASE_URL`, whose command runs the test suite. Put it in a Compose profile named `test`, so `docker compose up` does not start it and `docker compose --profile test run --rm test` does.
- Update the comment block at the top of the file to show the commands a reviewer needs.

**`.dockerignore`**: keep the image small and free of local state: `.git`, `.venv`, caches, `.env`, and `docs/plan/research/cache` and `out`. The `data/` and `tests/` folders must be in the image.

## Prove it

Docker Desktop is running, and the `db` container of this project may already be up with data. Run these yourself and paste the output into your report.

1. `docker compose down -v`, then `docker compose up --build -d`. Wait for the API. `docker compose logs api` must show the loader's six count lines ending in `Saved: 6626`, then gunicorn listening.
2. `curl -s -G http://127.0.0.1:8000/api/v1/route/ --data-urlencode "start=Dallas, TX" --data-urlencode "finish=Houston, TX"` returns 200 with `"routing_calls": 1`. Run it once more: `"routing_calls": 0` and `"cache_hit": true`. **These two requests are the only ones you may send that reach the public routing server** (the first does; the second is cached). Do not request any other trip.
3. `curl` an unknown address and a bad place (`start=Chicgo, IL`): the standard JSON error body, 404 and 400. These make no routing call.
4. `docker compose --profile test run --rm test`: the whole suite passes inside the container. Paste its last line.
5. `docker compose down` (without `-v`), then `docker compose up -d`: it starts again, the log shows `Saved: 6626` again, and `docker compose exec db psql -U milemarker -d milemarker -c "select count(*) from stations_fuelstation"` shows 6626, not double.
6. `docker compose config` shows the PostgreSQL 17 image and `DATABASE_URL` on the API.
7. The image size, from `docker images`.
8. Leave the stack **running** when you finish, so the controller can check it.

## Your report: `docs/plan/reports/phase6-K.md`

The files, each proof step with its command and pasted output, the image size, anything you changed from R1's researched Dockerfile and why, and anything you are unsure of.

Reply to the controller with: status, the last line of the in-container test run, and any concern.
