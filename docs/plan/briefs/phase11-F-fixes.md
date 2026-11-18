# Brief 11F: the fixes from the review of the runtime

A Django API was rebuilt to run on two worker processes with a shared Redis cache. An independent reviewer attacked it and found two Important faults and several smaller ones. Each has a ruling. You are building the fixes, test first.

The repository root is the folder you were given; every path is relative to it.

## Rules

- **Your files:** `trips/throttling.py` (new), `config/cache.py`, `config/settings.py`, `gunicorn.conf.py`, `trips/schema.py`, `docs/openapi.yaml` (regenerated, never edited by hand), `.env.example`, the tests under `tests/`, and your report `docs/plan/reports/phase11-F.md`. Nothing else. `pyproject.toml`, `uv.lock`, the Compose files, the Dockerfile and every document but your report are not yours: if you believe one must change, say so in your reply.
- **The body and status of `GET /api/v1/route/` do not change,** for any request the suite already makes. The independent verifier and the regression pins must pass untouched.
- **No request to a public routing server, ever.** No container started or stopped: the database and Redis are running on `127.0.0.1`, and the suite is all you need.
- **Test first.** Each fix starts with a test that fails for the stated reason; say in your report what each failed with.
- **Simplest thing that meets the ruling.** No option or setting the ruling does not ask for.
- Match the code's style: a description at the top of each module, a docstring on each function, comments that say why, plain names.
- No git command that changes anything. No other agents.

## Read first

- `docs/plan/reports/phase11-Q1.md`: the findings, with how each was shown.
- `docs/plan/PHASE-11.md`, "Rulings on the review (QA-1)": what to do about each. The rulings bind; where a ruling and the reviewer's suggested fix differ, follow the ruling.
- `docs/backend-architecture.md` section 10, "The rate-limit counter" and "When Redis cannot be reached": already corrected to say what you are to build.
- The code you are changing, and `tests/test_cache.py`, `tests/test_api.py` (the rate-limit tests), `tests/test_hosts.py`, `tests/test_project.py`, `tests/test_schema.py`.

## The fixes

1. **Q1-01, the rate limit.** A limiter of our own in `trips/throttling.py`, named in the settings in place of the framework's `AnonRateThrottle`, with the same rate setting and the same way of finding the client (so `DJANGO_NUM_PROXIES` works as now).
   - A window opens with a client's first request and lasts 60 seconds. The 61st request inside it is refused, and the wait reported is the time left in the window, at least 1 second.
   - Counting is one atomic step, the cache's `incr`. `RedisWithFallback` must pass `incr` through to Redis and to its memory, each of which has an atomic one; today it inherits a read followed by a write.
   - Suggested shape, which you may improve on if you show why: one key holds the window's start, written with `add` so that requests arriving together agree on it; the counter's key carries that start, lives longer than the window so it cannot expire under an increment, and is created with `add` only when `incr` finds it missing. Mind the trap in Django's Redis backend: its `incr` checks that the key exists and then increments, and an increment of a key that expired in between creates one with no expiry at all.
   - The health address stays exempt; the schema and docs addresses stay limited, against the same count.
   - Tests: 61 requests in order, as now. A burst: many threads of one client at once against the in-memory cache, and against the live Redis on database 15 with two real worker processes (the helpers in `tests/test_cache.py` do this already): exactly 60 pass, however they interleave. A new window after 60 seconds, by moving the clock. Two clients do not share a count. The wait reported is the time left in the window. During a fallback each process counts alone, as before.
2. **Q1-02, the health check's host.** `127.0.0.1` is always in `ALLOWED_HOSTS`, whatever `DJANGO_ALLOWED_HOSTS` says. Tests: with the variable set to one foreign name, a request under that name and one under `127.0.0.1` are both answered, and a third name is still refused. `.env.example` says so.
3. **Q1-03, other Redis errors.** Every error of the Redis client (`redis.exceptions.RedisError`) falls back as a refused connection does. Test: a Redis that answers a command with an error (a database index that does not exist is the reviewer's case) costs no request and gives one warning. Do not catch errors of reading a cached value back: the ruling leaves those.
4. **Q1-04, the late success.** Only the try made after the 30 seconds can end a fallback: a success from a call sent before the outage began changes nothing. Test: the reviewer's sequence (a slow call that succeeds after another call has fallen back): one warning, no "answers again" line, and the next call does not touch Redis.
5. **Q1-05, the request line.** gunicorn's `limit_request_line` is 8190, its highest. Test: the setting, with the reason beside it. Add a test that a 5,000-byte address reaches the API and gets its JSON answer through Django's test client, if one does not exist.
6. **Q1-06, the canary.** It compares key names, not counts: no key in databases 0 to 14 that was not there before, and the canary still there. Keys that expire during the run are not a failure.
7. **Q1-07, bad values.** `DJANGO_NUM_PROXIES` must be a whole number of 0 or more; `LOG_LEVEL` one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`, in any case; `WEB_CONCURRENCY` a whole number of 1 or more. A bad value stops the start with an error that names the variable and the value, as `ROUTING_SERVERS` does. The two that gunicorn's own file reads are checked there too, with the same wording. Tests in the style of the existing settings cases, one per bad value.
8. **Q1-08, the document's parameters.** In `trips/schema.py` the limits and the default of each parameter are taken from the fields of `RouteQuery` and from the settings, not written again. Test: with a limit of the serializer changed, the document produced changes with it. Then regenerate `docs/openapi.yaml`.
9. **Q1-10, two sentences in the document.** The two place names are trimmed before their length is checked; a request ID is kept only if it is 1 to 64 characters of letters, digits, `.`, `_` and `-`. No `multipleOf`. Regenerate.

## Traps

- `tests/conftest.py` empties the cache around every test, and the suite never sets `REDIS_URL`: a test that needs Redis builds its own cache object on database 15, as `tests/test_cache.py` does.
- Overriding the REST framework's settings in a test: pass a copy of the dictionary. The framework caches the limiter classes and rates; look at how the existing tests cope before writing new ones.
- The suite takes about three minutes. It checks that Redis databases 0 to 14 do not change while it runs, so send no request to the running stack during it.
- Use `127.0.0.1`, never `localhost`. Shell here-documents that contain apostrophes fail on this machine: write a helper script to a file and run the file.

## Prove it

`uv run pytest` in full (none skipped), `uv run pytest --cov` (at or above 98%), `uv run pytest -m slow`, `uv run mypy`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run python manage.py check --deploy --fail-level WARNING`, `uv run python manage.py spectacular --validate --fail-on-warn --file <a scratch file>`: clean. One pytest process at a time, in the foreground. Leave nothing running.

## Your report: `docs/plan/reports/phase11-F.md`

For each fix: the test and what it failed with before, what you changed, and anything you did differently from the suggestion, with the reason. The commands with their output. Anything you are unsure of.

Reply to the controller with: status, the test count, one line for each fix, and any concern.
