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

- [ ] The verifier is written from the documents and imports nothing from the application (VF-19).
- [ ] The controller runs `scripts/live_check.py` itself against a freshly started server.
- [ ] Every live case passes, or has a recorded reason.
- [ ] The verifier finds no broken rule in any successful response.
- [ ] Both speed limits are met.
- [ ] Every review finding is fixed and re-tested, or recorded as a known limit.
- [ ] `docs/test-cases.md` holds the actual outputs, and the design figures are replaced by measured ones.
- [ ] The passing figures are pinned as regression tests.
- [ ] Committed.

## Result

(Filled in when the phase closes.)
