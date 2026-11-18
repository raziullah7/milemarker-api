# Brief 10C: fixes from the second independent review

An independent reviewer went through everything changed since the last review and found faults in the response verifier, the routing client's retry rule, one count in the answer builder, one place-name rule, and three tests that check less than their names say. Each has been ruled on. You are making the fixes.

The repository root is the folder you were given; every path is relative to it.

## Rules

- **Your files only:** `tests/verify.py`, `tests/test_verify.py`, `trips/services/routing.py`, `tests/test_routing.py`, `trips/services/answer.py`, `tests/test_answer.py`, `stations/places.py`, `tests/test_places.py`, `tests/test_regression.py`; in `docs/test-cases.md` only the rules table of section 4 and the catalogue rows for the tests you add or change; in `docs/backend-architecture.md` only section 9 and the one sentence of section 8 about purchases under 0.005 gallons, which Q0b-4 makes false; and your report `docs/plan/reports/phase10-C.md`. Other builders are working in this repository on other files at the same time. No git command that changes anything. No other agents.
- **No network.** No request to a routing server or to the running API.
- **Each fix starts with a test that fails for the stated reason.** Run it, see it fail, then fix. Say in your report what each failing test printed.
- `tests/verify.py` must go on importing only the standard library and nothing from the application.
- The response of the API must not change shape. Regression pins in `tests/test_regression.py` must pass unchanged; you may only add to that file.
- Match the code's style: docstrings, comments that say why, plain names.

## Read first

- `docs/plan/reports/phase9-Q0b-changes.md` in full: each finding, how it was shown, and the proposed fix.
- `docs/plan/PHASE-9.md`, the table "QA-0b": the ruling on each finding. Where the ruling and the report's proposal differ, the ruling wins. Also, in "Points raised by the test design, settled", rows 2, 3 and 26.
- `docs/test-cases.md` section 9, the cases QB-01 onward: they are the catalogue rows for these fixes, already written. Build to them; correct a row only if it is wrong, and say so in your report.
- `docs/test-cases.md` section 4 (the rules R1 to R16) and `docs/backend-architecture.md` sections 8 and 9.

## The fixes

| Finding | What to do |
|---|---|
| Q0b-1 | New rule R17 in the verifier: every station stop's position on the map lies within 15 miles of a place with that stop's city and state. The verifier reads `data/us_cities.csv` itself and carries its own copy of the five places added by hand (they are in `stations/places.py`; copy the values, do not import). A new test builds the reviewer's wrong answer (a stop swapped for a station hundreds of miles away, everything else consistent) and must be caught by R17 alone. Every existing valid answer must still pass: run the verifier over every recorded road at stop costs 0, 10 and 25. |
| Q0b-2 | R12 compares each stop's marker with its position on the line using the line's own scale, within 0.1 mile, as the report proposes. A test moves a stop 17 points along the line and must be caught. |
| Q0b-3 | In the routing client, only a 400 whose body is not "no road" ends the request at once. Every other answer that is not a readable route (any other status, including 3xx, 204, 403, 404, 408, 410, 451) goes to the next server. Tests for a 302, a 404 and a 403 from the first server with a good answer from the second. Correct architecture section 9 to say exactly this. |
| Q0b-4 | `lowest_possible_stops` is counted from the shown gallons, as `stops` is. A test with the reviewer's purchases shows equal counts. |
| Q0b-5 | In the verifier: every stop after the first buys more than 0 gallons; the first buys at least 0. A test for a 0.00 stop and for a negative one. |
| R15 | Rule R15 accepts the two public routing hosts, plus any host its caller names (a new optional argument). `scripts/live_check.py` is not yours; say in your report what option it needs to pass that argument, and the controller adds it. |
| R17 and test data | R17 checks against the places data its caller gives; the default is the real places file plus the five hand-added places. The endpoint tests use invented stations in invented places, so they pass their own places file. Change those calls, and only those lines, in `tests/test_api.py` and `tests/test_planner.py` if they call the verifier. |
| N1 | The verifier's description at the top says it checks that a plan is consistent and possible, not that it is the cheapest, and names the tests that check that. |
| N5 | A comma-free country name is treated as a country only when no trailing `USA` was removed. `Mexico, USA` is an unknown place with suggestions again; `Mexico` alone is still outside coverage. Tests for both. |
| N7 | (a) AN-11's second half can fail: give it a purchase worth at least a cent, or assert the gallons. (b) `test_complete_answer_obeys_the_correctness_rules` calls the verifier, or is renamed to what it checks. (c) One trip, New York to Los Angeles at stop cost 10, is pinned stop by stop: each stop's station ID, mile marker, gallons and cost. |
| N8 | A lock around the creation of the shared HTTP client, so two first requests cannot each make one. |
| Types | `uv run mypy` checks the Django-free modules (its settings are in `pyproject.toml`) and reports nine errors today, in `stations/sphere.py`, `trips/services/fuel.py` and `stations/exceptions.py`. Make it pass with type annotations and, where a value can be `None`, an explicit check that states what the code already assumes. These three files are yours for this only. No behaviour may change: the fuel tests and the slow exactness test must pass exactly as before, and you add no `type: ignore` without a reason beside it. |

## Prove it

`uv run pytest` passes in full; `uv run pytest -m slow` passes; `uv run ruff check .` and `uv run ruff format --check .` are clean. Another builder may be running the suite at the same time against the same test database: if you see a database error that is not about your change, wait a minute and run again, and say so in your report.

## Your report: `docs/plan/reports/phase10-C.md`

A row per finding: the test added, what it printed before the fix, what changed. The suite's totals. Anything you are unsure of.

Reply to the controller with: status, test counts, and any concern.
