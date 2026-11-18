# Brief 10A: a stand-in routing server and an end-to-end stack

The API plans a trip from one call to a public routing server (OSRM). That server is free and must not be leaned on, so today nothing but hand-run checks ever exercises the whole stack. You are building a local stand-in that answers like the real server from recorded answers, so the full stack, the Postman collection and later a browser can run with no call to the internet.

The repository root is the folder you were given; every path is relative to it.

## Rules

- **Your files only:** `scripts/fake_osrm.py`, `tests/test_fake_osrm.py`, `docker-compose.e2e.yml`, your report `docs/plan/reports/phase10-A.md`, and in `config/settings.py` only the lines that define `ROUTING_SERVERS` and their comment. Change nothing else: not `docker-compose.yml`, not `Dockerfile`, not `pyproject.toml`. No git command that changes anything. No other agents.
- **No request to the public routing servers, ever.** Do not run `scripts/live_check.py` or Newman against a stack that still points at them.
- Standard library only for the stand-in. It must run with plain `python scripts/fake_osrm.py` inside the existing API image.
- Write each test first and see it fail.
- Match the code's style: a short description at the top of each module, a docstring on each function, comments that say why.

## Read first

- `trips/services/routing.py` in full: exactly what the client sends and what it accepts. `tests/test_routing.py` for how answers are faked today.
- `docs/backend-architecture.md` section 9.
- `tests/conftest.py`: `ROADS`, `load_road_answer`. `tests/fixtures/roads/*.json.gz` are whole recorded answers, each with `routes[0].geometry.coordinates`, `routes[0].distance` and two `waypoints` whose `location` is `[lng, lat]`.
- `config/settings.py`, `docker-compose.yml`, `Dockerfile`, `docker/entrypoint.sh`.

## Build

### 1. `ROUTING_SERVERS` from the environment

In `config/settings.py`: when the environment variable `ROUTING_SERVERS` is set, it is a comma-separated list of URL templates, each containing `{coords}`, tried in order; when it is not set, the two public servers stay exactly as they are now. Reject at start-up, with a clear message, a template without `{coords}`. One existing test reads this setting (`tests/test_project.py`): it must still pass unchanged.

### 2. `scripts/fake_osrm.py`

A small threaded HTTP server.

- `GET /route/v1/driving/{lng,lat;lng,lat}` and `GET /routed-car/route/v1/driving/{...}` (the two public servers' paths), with any query string: find the recorded road whose first waypoint is nearest the requested start and whose second is nearest the requested finish. If both are within 30 miles, answer 200 with that recording's JSON, byte for byte as recorded. Otherwise answer as the real server does when no road exists: status 400, body `{"code": "NoRoute", "message": "..."}`. Check that against how `routing.py` recognises "no road".
- A malformed path or coordinate list: status 400 with `{"code": "InvalidUrl", ...}`.
- `GET /_requests`: JSON with the number of route requests served since start or since the last reset, and for each its coordinates, the recording it matched (or none) and the status. `POST /_reset` empties it. `GET /_health`: 200.
- Options: `--port` (default 5000), `--host` (default `0.0.0.0`), `--roads` (default `tests/fixtures/roads`).
- Recordings are read once at start. The folder may gain files later; do not hard-code their names.

### 3. `tests/test_fake_osrm.py`

Start the server on a free local port in a fixture and talk to it over HTTP (the suite allows connections to 127.0.0.1). Cover: a recorded pair returns its recording; the reverse of a recorded pair does not match unless that direction was recorded too; a pair far from every recording returns the "no road" answer; a malformed request; the request log and reset; both URL paths. Then one test that points the real client, `trips.services.routing.fetch_route`, at the stand-in through the setting and gets back a `Route` whose distance equals the recording's, with `calls == 1`.

### 4. `docker-compose.e2e.yml`

A second Compose file, used on top of the first: `docker compose -f docker-compose.yml -f docker-compose.e2e.yml up --build -d`.

- Adds a service `fake-osrm`: the API image, running the stand-in, with the recordings inside it. Its port is published on `127.0.0.1:${FAKE_OSRM_PORT:-5000}` so the request log can be read from the host.
- Sets the `api` service's `ROUTING_SERVERS` to the stand-in alone, and makes `api` wait for it.
- A comment block at the top with the commands to start it, read the log, and stop it.

Do not add an internal-only network: that comes with the reverse proxy in a later phase.

## Prove it

1. `uv run pytest` passes in full and `uv run ruff check .` and `uv run ruff format --check .` are clean.
2. Start the end-to-end stack. Then, against `http://127.0.0.1:8000`:
   - `npx newman run docs/postman/milemarker.postman_collection.json --folder "1. Demo"` passes.
   - `GET /_requests` on the stand-in shows exactly one route request for that folder (its four requests are one trip: one routed, three answered from the cache).
3. Stop the end-to-end stack with `down` (not `down -v`), then start the ordinary stack again with `docker compose up -d`, so it is left as you found it.

## Your report: `docs/plan/reports/phase10-A.md`

What you built, the commands you ran with their output, the stand-in's request log after the Demo folder, and anything you are unsure of.

Reply to the controller with: status, test counts, and any concern.
