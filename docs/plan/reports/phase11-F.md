# Report 11F: the fixes from the review of the runtime

Status: done, with the concerns at the end.

The suite has 597 tests, all passing, none skipped: 567 before, and 30 new. Each fix started with a test, run against the unchanged code; what each failed with is below. The body and status of `GET /api/v1/route/` are unchanged for every request the suite already made: the verifier, the regression pins and every earlier test pass untouched, apart from CF-04, whose expectation the ruling on Q1-02 changes.

## Files

| File | Change |
|---|---|
| `trips/throttling.py` (new) | `FixedWindowThrottle`, the limiter of Q1-01 |
| `config/settings.py` | The limiter named in place of `AnonRateThrottle`; `127.0.0.1` always allowed; `DJANGO_NUM_PROXIES` and `LOG_LEVEL` checked; the request ID sentence of the opening text |
| `config/cache.py` | `incr` passed through; every `RedisError` falls back; only the try ends a fallback |
| `gunicorn.conf.py` | `limit_request_line = 8190`; `WEB_CONCURRENCY` and `LOG_LEVEL` checked |
| `trips/schema.py` | The parameters' limits and default read from `RouteQuery`; the trimming and request ID sentences |
| `docs/openapi.yaml` | Regenerated |
| `.env.example` | One sentence: `127.0.0.1` is always allowed |
| `tests/test_throttling.py` (new) | 6 tests |
| `tests/cache_worker.py` | A `burst` command: several threads of one worker send requests at once |
| `tests/test_cache.py`, `test_hosts.py`, `test_project.py`, `test_schema.py`, `test_api.py` | The other 24 tests; CF-04's expectation; the canary |

## The fixes

### 1. Q1-01, the rate limit

**Tests, and what each failed with before.**

| Test | Before |
|---|---|
| `test_throttling.py::test_a_burst_from_one_client_passes_exactly_60`: 100 requests of one client from 20 threads at once, on the in-memory cache, each cache step slowed by 2 ms so the threads interleave between any two steps | `assert (100, 0) == (60, 40)`: all 100 passed, none refused |
| `test_cache.py::test_a_burst_across_two_workers_passes_exactly_60`: two real worker processes on the live Redis (database 15), 8 threads each, 8 requests per thread, all at once | `assert (128, 0) == (60, 68)`: all 128 passed |
| `test_cache.py::test_incr_is_one_atomic_step_on_redis_and_on_the_fallback[redis]`: 8 threads, 50 increments each, through `RedisWithFallback` | `assert 84 == 400`: 316 increments lost |
| `[own memory]`, the same on the fallback | Passed before (memory's steps are too quick to interleave); kept as the fallback's case |
| `test_cache.py::test_the_rate_limit_keys_expire_in_redis`: the window's start lives at most 60 s, the count more than 60 and at most 120 | `ValueError: not enough values to unpack`: the keys did not exist |
| `test_throttling.py::test_the_settings_name_this_limiter_at_the_same_rate` | `ModuleNotFoundError: No module named 'trips.throttling'` |
| `test_the_window_opens_with_the_first_request_and_lasts_60_seconds`: 1 request at T, 59 at T+30, the 61st refused; at T+60 a whole new 60 | `assert 429 not in [429, 429, ...]` at T+60. (The framework's limiter keeps its own reference to the clock, so it did not see the clock move either; a sliding window would also have let only one through at T+60.) |
| `test_the_wait_is_the_time_left_in_the_window`: first request at T, the 61st at T+20.5 | `{'retry_after_seconds': 60} == {'retry_after_seconds': 40}` |
| `test_the_wait_is_at_least_a_second`: the limiter's clock half a second past the window's end while the cache still holds it | `ImportError` on `trips.throttling` |
| `test_two_clients_do_not_share_a_count` | Passed before; a pin of the ruling |

Kept and passing: EP-34 and its `X-Forwarded-For` case (61 in order), HM-07 and HM-08 (`DJANGO_NUM_PROXIES`), HS-08 (health exempt), HS-09 (schema and docs on the same count), CA-14 (counted across workers in order) and CA-15 (during a fallback each process counts alone).

**What changed.** `trips/throttling.py` holds `FixedWindowThrottle`, a `SimpleRateThrottle` with scope `anon`: the same rate setting (`DEFAULT_THROTTLE_RATES["anon"]`, `60/min`) and the framework's own `get_ident`, so `DJANGO_NUM_PROXIES` works as before. For each request:

1. The window's start: `cache.get_or_set("throttle_anon_start_<client>", now, 60)`. Django's `get_or_set` reads, writes with `add` if nothing is there, and reads back what is stored, so requests that find no window at once all take the one start stored first.
2. The count: `cache.incr("throttle_anon_count_<client>_<start>")`. If that raises `ValueError` (no such key), `cache.add(key, 1, 120)`; the one request whose `add` wins counts 1, the others find the key and `incr` it.
3. Refused when the count passes 60. The wait is `max(1, start + 60 - now)`, which the framework rounds up to whole seconds.

The count key carries the start, so each window counts from nothing, and lives 120 s, twice the window, so it cannot expire under an increment: Django's Redis `incr` runs `EXISTS` then `INCRBY`, and an `INCRBY` of a key that expired in between would make one with no expiry.

`RedisWithFallback.incr` now passes `incr` through `_call` to Redis's `INCRBY` or to memory's own locked increment, each atomic. `decr` and `get_or_set` come from Django's base class, built on these.

**Different from the suggestion, and why.**

- `get_or_set` rather than `add` then `get`. It is the same agreement (the write is an `add`), and a window that already exists, the usual case, costs one read instead of a refused `add` and a read.
- Key names. The start and count keys have different words after `throttle_anon_` (`start_`, `count_`), so no client name, which a forged `X-Forwarded-For` can choose when a proxy is trusted (Q1-13), can make one client's start key equal another's count key. Both differ from the framework's `throttle_anon_<client>`, so a history list left in Redis by the old code when this one is deployed is never read as a start; it expires within 60 s.
- The in-memory burst slows each step of the cache by 2 ms. Without it the threads rarely interleave between a read and a write, and the framework's limiter could pass by luck.

### 2. Q1-02, the health check's host

**Test.** `test_hosts.py::test_127_0_0_1_is_answered_whatever_the_variable_says`: `ALLOWED_HOSTS` as a new process makes it from `DJANGO_ALLOWED_HOSTS=api.example` (the existing `settings_with` helper); health under `api.example` and `127.0.0.1` answers 200, under `other.example` the refusal. Before: `assert 400 == 200` for `127.0.0.1`.

CF-04's expectation changed with the ruling: `api.example,api2.example` now gives `["api.example", "api2.example", "127.0.0.1"]`, and a value that already holds `127.0.0.1` does not get it twice. Before the fix it failed with the old list. The default stays `["localhost", "127.0.0.1", "[::1]"]`.

**What changed.** `config/settings.py` appends `127.0.0.1` when it is missing, with the ruling's reason beside it. `.env.example` says so.

### 3. Q1-03, other Redis errors

**Test.** `test_cache.py::test_a_redis_that_answers_with_an_error_costs_no_request`: this process on database 99 of the live Redis, which answers `DB index is out of range` (`ResponseError`). Two route requests answer 200 (the second a hit from memory), health says `fallback`, one warning. Before: `assert (500, 500) == (200, 200)`.

**What changed.** `_call` catches `redis.exceptions.RedisError`, the base of every error of the Redis client, where it caught `ConnectionError` and `TimeoutError`. The two narrower imports went.

As ruled, an error of reading a value back is not caught. `test_a_cached_value_that_cannot_be_read_back_is_not_caught` pins that edge: a value in Redis that is not a pickle raises `UnpicklingError` and does not fall back. It passed before and after; it is there so that a later widening of the catch is noticed.

### 4. Q1-04, the late success

**Test.** `test_cache.py::test_a_late_answer_to_a_call_sent_before_the_outage_does_not_end_it`, the review's sequence with a stand-in for Django's Redis cache (no real Redis): call `a` is sent and held; call `b` is refused and the process falls back; then `a` answers. Before: `assert False` on `cache.falling_back` after `a`'s answer: the late success had ended the fallback. After: still falling back, `c` is served from memory without touching the stand-in, and the log is one `WARNING`.

**What changed.** `_may_use_redis()`, which returned a yes or no, is now `_where()`, which returns `"memory"`, `"try"` (the one call made when the 30 seconds are over) or `"redis"`. `_call` calls `_redis_answered()` only for `"try"`. That made the two guards inside `_redis_answered` unreachable (it ran on every success before; now it runs only for the try, and there is one try at a time, made only while falling back), so I removed them, and coverage no longer reports them.

CA-09 (a try every 30 s), CA-10, CA-11 (warning, info, warning across two outages) and HS-05 still pass: the try still ends a fallback.

### 5. Q1-05, the request line

**Test.** `test_project.py::test_gunicorn_takes_request_lines_up_to_its_highest_limit`: `limit_request_line` read from `gunicorn.conf.py` in a new process is 8190, and the comment above it gives the reason (it must say "highest" and "JSON"). Before: `assert None == 8190`.

`GUNICORN_SCRIPT` now reads the names with `c.get(name)`, so a missing setting reads `None` instead of stopping the script with `KeyError`. Without that, the Q1-07 cases below would have failed on the `KeyError`, not for their own reasons.

`test_api.py::test_a_5000_byte_address_gets_the_apis_json_answer` did not exist, so I added it: a 5,000-byte address through Django's test client gets the JSON 400 `invalid_request` for `start`. It passed before, as expected: Django's test client has no line limit. It pins the API's side.

**What changed.** `limit_request_line = 8190` in `gunicorn.conf.py`, with the reason beside it, including that nginx's own limit must stay below it from Phase 12. `limit_request_field_size` is not changed: the ruling covers the request line only.

### 6. Q1-06, the canary

**Test.** `test_cache.py::test_ca16_a_key_that_expires_while_the_tests_run_is_no_change`: a key in database 14 that expires between two looks is no change; a key that was not there before is a change. I first moved the fixture's comparison, unchanged, into two helpers (`redis_keys()`, still `dbsize` per database, and `unchanged()`, equality) and wrote the test against them. Before: `assert False` at the first `unchanged`.

My first try at the test used a key that lived 100 ms. It passed against the count comparison: one look at the 15 databases takes 0.2 to 0.4 s here (a new connection each), so the key had expired before database 14 was looked at. The test now uses a key that lives 1 s and waits until `EXISTS` says it is gone. `EXISTS` also removes an expired key, so the count would see it go too.

**What changed.** `redis_keys()` returns each database's key names, and `unchanged()` holds when every database's names after are among its names before. The fixture still checks that the canary is there.

### 7. Q1-07, bad values

**Tests**, in the style of the settings cases (a new process with only the named variable set):

| Test | Before |
|---|---|
| `test_a_bad_value_stops_the_api_naming_the_variable_and_the_value[DJANGO_NUM_PROXIES--1]` | Started: `assert 0 != 0` on the return code, with `NUM_PROXIES: -1` in the output |
| `[DJANGO_NUM_PROXIES-abc]`, `[DJANGO_NUM_PROXIES-1.5]` | `ValueError: invalid literal for int() with base 10: 'abc'`, with no variable named |
| `[LOG_LEVEL-verbose]` | Started |
| `test_a_bad_value_stops_gunicorn_naming_the_variable_and_the_value[WEB_CONCURRENCY-0]`, `[-2]` | Started, with `workers` 0 and -2 |
| `[WEB_CONCURRENCY-abc]` | `ValueError: invalid literal for int() ...`, with no variable named |
| `[LOG_LEVEL-verbose]` | Started, with `loglevel: verbose` |
| `test_gunicorn_and_the_api_refuse_a_log_level_in_the_same_words` | The API started |
| `test_the_log_level_is_read_in_any_case` (`warning`, `Warning`) | Passed before; a pin that the check takes any case |

**What changed.** `config/settings.py` has `_num_proxies()` (a whole number of 0 or more) and `_log_level()` (the five names, any case), each raising `ImproperlyConfigured` naming the variable and the value, as `ROUTING_SERVERS` does: for example `DJANGO_NUM_PROXIES must be a whole number of 0 or more, not '-1'.` `gunicorn.conf.py` has `_workers()` (1 or more) and `_log_level()`, in the same words.

**Different, and why.**

- I read "the two that gunicorn's own file reads are checked there too" as: each file checks the variables it reads. Settings checks `DJANGO_NUM_PROXIES` and `LOG_LEVEL`; gunicorn's file checks `WEB_CONCURRENCY` and `LOG_LEVEL`. Settings does not read `WEB_CONCURRENCY`, so it does not check it.
- gunicorn's file raises `ValueError`, not Django's `ImproperlyConfigured`. It is gunicorn's file, which imports nothing of Django, and gunicorn's own setting checks raise `ValueError`. gunicorn prints `Failed to read config file`, then the traceback ending in the message, and exits 1. The words are the same, and a test holds them the same for `LOG_LEVEL`.
- "A whole number" is checked with `str.isdecimal()`, so `+1`, `1.0` and `1_000` are refused as well as `-1` and `abc`.

### 8. Q1-08, the document's parameters

**Test.** `test_schema.py::test_hs12_the_parameters_follow_the_serializer`: a new process replaces `RouteQuery`'s `start` field (`max_length` 120) and `stop_cost` field (1 to 200, 3 decimals, default 7.5) before the URLs load, and writes the document with `manage.py spectacular --format openapi-json`. The document must follow: `maxLength` 120 for `start` and still 100 for `finish`, `minimum` 1, `maximum` 200, `default` 7.5, and the description says "1 to 200, at most 3 decimals, 7.5 when left out". Before: `assert 100 == 120`.

**What changed.** `trips/schema.py` reads `RouteQuery().fields`. `maxLength` is the field's `max_length`; `minLength` is 1 because the field does not allow blank; `minimum`, `maximum` and `default` are its `min_value`, `max_value` and `default` (which is `settings.DEFAULT_STOP_COST`), written as whole numbers when they are whole. The stop cost's description takes the same figures and the field's `decimal_places`, so its prose cannot fall behind either. The regenerated document is unchanged in these places: the values are the same.

HS-12's own literals (100, 0, 100, 10) stay. They pin today's values, as `test_api.py` does.

### 9. Q1-10, two sentences

**Tests.** `test_the_place_names_are_trimmed_before_their_length_is_checked`: `RouteQuery` accepts 5 spaces and 100 letters, and `start`'s description says the spaces are "removed before its length is checked". It also asserts that `stop_cost` has no `multipleOf`, with the ruling's reason beside it. `test_the_document_says_which_request_ids_are_kept`: the opening text, and the `X-Request-ID` header of every answer of both addresses, say "1 to 64 characters of letters, digits, `.`, `_` and `-`", and `trips.middleware.GOOD_REQUEST_ID` is that pattern. Before: both failed on the sentence, which was not there.

**What changed.** `start`'s description (`finish` is "written as `start` is"); the opening text in `SPECTACULAR_SETTINGS`, which now also says any other ID is replaced; and the `X-Request-ID` header's description in `trips/schema.py`, which said "a well-formed ID" too. No `multipleOf`. `docs/openapi.yaml` regenerated: 21 lines in, 11 out, all in those sentences.

## Commands

Every pytest run used `DATABASE_URL=postgresql://milemarker:milemarker@127.0.0.1:5432/milemarker_f`, one at a time, in the foreground.

```text
$ uv run pytest
================ 597 passed, 1 deselected in 133.36s (0:02:13) ================

$ uv run pytest --cov
Name                        Stmts   Miss Branch BrPart  Cover   Missing
-----------------------------------------------------------------------
config\settings.py             67      3     18      3    93%   53, 156, 285
config\wsgi.py                  6      6      0      0     0%   10-25
stations\models.py             13      1      0      0    92%   21
stations\places.py            108      0     40      1    99%   156->154
trips\errors.py                41      1     14      1    96%   74
trips\services\fuel.py        113      1     54      1    99%   229
trips\services\routing.py      83      2     20      2    96%   128, 172
trips\views.py                 45      1      0      0    98%   29
-----------------------------------------------------------------------
TOTAL                        1279     15    220      8    98%

26 files skipped due to complete coverage.
Required test coverage of 98.0% reached. Total coverage: 98.47%
================ 597 passed, 1 deselected in 212.06s (0:03:32) ================

$ uv run pytest -m slow
===================== 1 passed, 597 deselected in 19.31s ======================

$ uv run mypy
Success: no issues found in 6 source files

$ uv run ruff check .
All checks passed!

$ uv run ruff format --check .
67 files already formatted

$ uv run python manage.py check --deploy --fail-level WARNING
System check identified no issues (3 silenced).

$ uv run python manage.py spectacular --validate --fail-on-warn --file <scratch file>
(no output, exit 0; the file is identical to docs/openapi.yaml)
```

`config/cache.py` and `trips/throttling.py` are fully covered. The three new lines of `config/settings.py` reported missing (53, the added `127.0.0.1`; 156 and 285, the two refusals) run only in the new processes of CF-04 and the Q1-07 cases, which coverage does not follow; those tests check them.

The concurrency tests (both bursts, the atomic increment, the late answer, the canary's own test and the throttling file) were also run six times in a row: 11 passed each time, in 5.9 to 6.9 s.

The baseline before any change: 567 passed, 1 deselected, in 93 s. The suite now takes longer: 105 and 133 s in my two final plain runs, 212 s with coverage. The new cases start 19 more Python processes (17 for the settings, gunicorn and host cases and the document with a changed serializer, and two workers), and the time varied from run to run on this machine.

## Concerns, and what I am unsure of

1. **`WEB_CONCURRENCY=abc` still stops gunicorn before our file is read.** gunicorn 27.0.1 reads the variable itself as it imports its own settings (`gunicorn/config.py`, line 762: `default = int(os.environ.get("WEB_CONCURRENCY", 1))`). A value that is not a number fails there with `invalid literal for int() with base 10: 'abc'`, which names the value but not the variable, before `gunicorn.conf.py` runs. Our check covers what gunicorn accepts at import (0, -2), and names the variable for a non-number only when the file is run on its own, as the test does. I could not run gunicorn here to see it (it cannot be imported on Windows: `grp`); this is from reading its source. Closing it fully would mean checking the variable before gunicorn starts, in the Dockerfile's `CMD` or the Compose file, neither of which is mine. The Compose file already passes `WEB_CONCURRENCY: ${WEB_CONCURRENCY:-2}` for the same reason (gunicorn fails on an empty value).
2. **A try that is an increment of a key Redis does not hold.** The one try after the 30 seconds is whichever cache call comes first. If it is the limiter's `incr` of a count kept in memory, Redis answers "no such key" and Django raises `ValueError`. That is an answer, but `_call` does not count it as one, so the process stays on its memory for another 30 seconds, with no new log line. The limiter then counts in memory, correctly. It needs a request whose read of the window's start fell just before the end of the 30 seconds and whose increment fell just after. I left it rather than add a case for it.
3. **The documents.** Architecture section 10 already says what was built. `docs/test-cases.md` has no IDs for the 30 new tests; it is not mine, so they are named for what they check and for the finding.
4. **One help text still writes the default again.** The assumptions' `stop_cost` in the 200 body says "the request's stop_cost, or 10". It is a field of the answer, not a parameter, so I left it as written.
5. **`.env.example`.** Only the sentence Q1-02 asks for. It does not list the five level names or the lowest worker count; the architecture's table does.

Nothing is left running. No container was started or stopped, no request went to the running stack or to a public routing server, and no git command that changes anything was run. Scratch files are outside the repository.
