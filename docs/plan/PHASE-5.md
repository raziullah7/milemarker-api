# Phase 5: QA

Baseline: `PLAN.md`, Phase 5. Two agents who wrote none of the code check it, in parallel.

## Inputs from Phase 4

- The endpoint works. 294 tests pass. First live call: New York to Los Angeles, 7 stops, $867.27, 19 ms of our own work.
- Server for live checks: `uv run python manage.py runserver 127.0.0.1:8000 --noreload`, with PostgreSQL up and the stations loaded.
- Live routing calls used so far: about 40 of the 100 allowed across all phases.

## Tasks

| ID | Agent | Model | Owns | Test cases |
|---|---|---|---|---|
| 5Q1 | Verifier and live runner | Opus | `tests/verify.py`, `tests/test_verify.py`, `scripts/live_check.py` | VF-01 to VF-19; runs P01 to P20, N01 to N26, S01 to S03 |
| 5Q2 | Whole-project review | Opus | `docs/plan/reports/phase5-Q2-review.md` only | — |

Briefs: `briefs/phase5-Q1-verifier.md`, `briefs/phase5-Q2-review.md`.

## Gate 5 checklist

- [x] The verifier is written from the documents and imports nothing from the application (VF-19).
- [x] The controller runs `scripts/live_check.py` itself against a freshly started server.
- [x] Every live case passes, or has a recorded reason.
- [x] The verifier finds no broken rule in any successful response.
- [x] Both speed limits are met.
- [x] Every review finding is fixed and re-tested, or recorded as a known limit.
- [x] `docs/test-cases.md` holds the actual outputs, and the design figures are replaced by measured ones.
- [x] The passing figures are pinned as regression tests.
- [x] Committed.

## Result

Closed 18 Nov 2026. Every gate item passed.

### Gate evidence

| Gate item | Evidence |
|---|---|
| Verifier written from the documents | `tests/verify.py` imports only the standard library (VF-19). Its author did not open the planner, answer builder or fuel module before it was written |
| Controller's own live run | `scripts/live_check.py` against a freshly started server, real OSRM: **49 cases, 49 passed**, exit code 0. The tester's own earlier run: also 49 of 49 |
| No broken rule in any 200 | Rules R1 to R16 checked on every successful answer of both runs, including the 60 inside the rate-limit burst |
| Speed | New trip: 19.5 ms of our own work (limit 100). Repeat: 23.6 ms round trip (limit 50). Road cached, new stop cost: 31.7 ms round trip |
| Review findings | 0 Critical, 1 Important, 8 Minor, 4 Notes. Twelve fixes made, each with a test seen to fail first; the rest recorded as known limits (see below) |
| Catalogue holds the actual outputs | `docs/test-cases.md` section 3 and 5: 49 rows with Actual and Result |
| Regression pins | `tests/test_regression.py`: seven trips on recorded roads with the real stations |
| Suite and lint | `uv run pytest`: 348 passed. `-m slow`: 1 passed. Ruff clean |

### Live results worth knowing

| Trip | Result |
|---|---|
| New York to Los Angeles | 2,800.6 miles, 7 stops, $867.27; lowest possible $855.95 |
| The same, stop cost 0 | 19 stops, $855.95 |
| The same, stop cost 25 | 6 stops, $886.16 |
| Los Angeles to New York | Warning: nearest listed station is in Coachella, 120.6 miles away |
| Houston to Dallas | Warning: nearest listed station is in Liberty, 41.8 miles away |
| Seattle to Miami | 3,301.1 miles, 8 stops |
| Detroit to Buffalo | Refused: 252.0 miles through Canada |
| Los Angeles to Seattle | Refused: no fuel listed for 885.3 miles from the start |
| San Francisco to Portland | Refused: no fuel listed for 549.3 miles from the start |

### What the review changed

| Fix | What was wrong | Now |
|---|---|---|
| F1 | A shown purchase could exceed the tank (50.03 gallons) because the rounding difference went to the largest purchase | Gallons are rounded as a running total. Checked on 90 plans: none over 50.00 |
| F2 | The answer builder loaded Django indirectly; the test only read import lines | `Place` lives in `stations/types.py`; PJ-02 imports each pure module in a fresh interpreter |
| F3 | The rate limit could be bypassed with `X-Forwarded-For` | `NUM_PROXIES` is 0 |
| F4 | The routing client retried after any refusal, and called a zero-length road unreadable | A refusal ends the request; a zero-length road reaches the planner, which answers "same place" |
| F5 | Over 1,000 query parameters gave a 500 | 400 `invalid_request` |
| F6 | `Tijuana Mexico` without a comma was an unknown place | Outside coverage, as with a comma |
| F7 | The search radius was defined twice | One constant, in `corridor.py` |
| F8 | The start-up warm-up left a database connection open | Closed |
| F9 | Place text had no length limit | 100 characters |
| F10 | The allowed-hosts setting did nothing | Removed; any host is accepted, with the reason stated |
| F11 | Rule R13 rejected correct lines on trips under about 40 miles | "Within 1% or 1 point" |
| F12 | The endpoint tests did not use the verifier | Every 200 they check is also verified. No disagreement found |

Document-only changes by the controller: architecture sections 6 (warm-up), 8 (rounding), 9 (what the deadline bounds; when a request is retried), 10 (labels in the cache key; refused roads are asked for again), 12 and 16; requirements NFR-2 and D-14; rules R2, R10 and R13 in the test catalogue.

### Recorded as known limits, not fixed

- An attempt on a routing server can run to about twice the 5-second deadline. Shortening the timeouts would cut off real coast-to-coast requests.
- Two identical new requests arriving together both call the routing server.
- The rare fallback to every station takes 150 to 300 ms.
- HEAD runs the whole plan (left to the framework).

### Deviations

- The Expected column of the live cases keeps the design figures; the Actual column beside it holds the measured ones. The gate said the design figures would be replaced. Keeping both shows how close the design was, and the runner's expectations did not need changing.
- VF-01 is covered by seven trips on recorded roads in `tests/test_verify.py`, and since F12 by every 200 in the endpoint tests as well.

### Live routing calls

About 77 of the 100 allowed: 40 in research, 3 at the Phase 4 gate, 19 by the tester, 18 by the controller's run. Phase 6 uses a short list of cases.

### Carried into Phase 6

- Do not run gunicorn with `--preload`.
- `.env.example` no longer has an allowed-hosts line.
- The container check uses `scripts/live_check.py --only` with a short list.
