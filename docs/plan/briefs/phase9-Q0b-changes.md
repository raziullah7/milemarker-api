# Brief 9-Q0b: independent review of the code changed after the last review

This repository is a finished take-home assessment: a Django API that plans the cheapest fuel stops for a road trip in the USA. An independent review read the application code at commit `5222f00`. Everything changed after that commit was checked only by the person coordinating the work. You built none of it. Review it as an adversary: assume there is a fault and look for it.

You were given two folders: a frozen copy of release `v1.0.0` to review, and the path for your report. Every path below is relative to the frozen copy. The copy is disposable: you may edit files in it to test a suspicion, as long as you say so in your report. Write nothing outside it except your report.

## Rules

- No other agents. No git command that changes history.
- **No request may reach the public routing servers, and do not call the running API.** The tests never need the network.
- You may run the tests in the frozen copy: `uv sync`, then `uv run pytest` (PostgreSQL is running on `localhost:5432`; the suite makes its own test database). `uv run pytest -m slow` runs the full-size exactness check.
- Do not start, stop or rebuild containers.

## Read first

- `docs/backend-architecture.md` sections 3 and 6 to 11: what the code is meant to do.
- `docs/plan/reports/phase5-Q2-review.md`: the earlier review's findings.
- `docs/plan/briefs/phase5-fix-wave.md` and `docs/plan/reports/phase5-fix-wave.md`: the twelve fixes (F1 to F12) made in answer to it.
- The diff itself: `git diff 5222f00 v1.0.0 -- . ':!docs'`.

## Scope

1. **The twelve fixes.** For each of F1 to F12: is the fault really gone, is the fix the right one, did it break or weaken anything nearby? Does its test fail when the fix is removed? Prove that for at least the money and security fixes (rounding of shown gallons, the rate limit and `X-Forwarded-For`, the routing retry rules, the query-parameter limit) by reverting the fix in your copy and running the test.
2. **The independent verifier:** `tests/verify.py` and `tests/test_verify.py`. It is meant to check any successful response against the rules, sharing no code with the application. Can a wrong plan pass it? Try: build wrong answers (a stretch over 500 miles, gallons that do not sum, a price that is not the file's lowest for that station, a stop out of order, a total off by a cent) and see whether each is caught. Does it import anything from the application?
3. **The live runner and the pinned results:** `scripts/live_check.py`, `tests/test_regression.py`. Could a case pass on a wrong answer? Are the pinned figures compared tightly enough to notice a regression?
4. **The application code as it now stands:** `trips/` and `stations/`, read in full with the changes in mind. In particular, the server runs four threads in one process: look for races in the shared cache, in building the station index (`stations/index.py`), in the start-up warm-up (`config/wsgi.py`, `trips/services/planner.py`), and in the shared HTTP client.
5. **The tests as tests.** Sample twenty across the files. Does each one assert the thing its name claims? Would it fail if the behaviour were wrong? Name any that cannot fail.

## Your report

- A findings table, most serious first: ID, severity (Critical, Important, Minor, Note), `file:line`, what is wrong, how you showed it (the command or the edit, and what happened), and the smallest fix.
- For scope item 1, a row per fix: sound or not, and whether you saw its test fail without it.
- What you checked and found sound, briefly.
- What you could not check, and why.

Reply to the controller with the count of findings by severity and one line for each Critical and Important.
