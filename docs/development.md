# Working on it

The README says how to run the API and its tests with Docker alone. This page is for changing the code.

## From source

Needs Python 3.12 and [uv](https://docs.astral.sh/uv/). The database and Redis still run in Docker.

```bash
docker compose up -d db redis
uv sync
uv run python manage.py migrate
uv run python manage.py load_stations
uv run python manage.py runserver 127.0.0.1:8001
```

Then the tests and the checks:

```bash
uv run pytest            # the suite: three to four minutes on Windows, under two in the container
uv run pytest -m slow    # one slow test of the fuel plan against brute force
uv run ruff check .
uv run mypy
```

Use `127.0.0.1`, not `localhost`, for the database and Redis.

## Without the public routing server

A stand-in routing server answers from 21 recorded real roads, so the whole stack runs with no call to the internet. CI uses it on every push.

```bash
docker compose -f docker-compose.yml -f docker-compose.e2e.yml up --build -d
npx newman run docs/postman/milemarker.postman_collection.json --env-var base_url=http://127.0.0.1:8000
docker compose -f docker-compose.yml -f docker-compose.e2e.yml down
```

A trip it has no recording for is answered as "no route".

## With make

`make help` lists nine shortcuts for the commands above: `up`, `down`, `logs`, `test`, `lint`, `dev`, `offline`, `postman` and `clean`.

## Settings

Every setting has a default, so no `.env` is needed. [`.env.example`](../.env.example) lists them, with what each is for. Copy it to `.env` to change one.

## Things to know

- **Reloading the stations.** A running API keeps the stations it read at start. After `load_stations` with changed data, restart it: `docker compose restart api`.
- **Emptying the cache.** Redis keeps nothing on disk: `docker compose restart redis`. Do this after changing `ROUTING_SERVERS`, or the old server's roads are served for up to 24 hours.
- **A change to what is cached.** Raise `CACHE_KEY_VERSION` in `config/settings.py` whenever the shape of a cached value or a planning rule changes.
- **The live cases.** `uv run python scripts/live_check.py` runs 49 cases against a running API. It calls the public routing server, so use it sparingly.
