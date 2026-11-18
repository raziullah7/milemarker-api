# Rules for every Phase 3 builder

You are one of five builders working **at the same time in the same folder**, each on different files. The repository root is the folder you were given; every path below is relative to it.

## What you build from

- **Your brief** names your files, your test cases and what to read.
- **Your module's skeleton** already exists. Its signatures, data classes and docstrings are the contract other builders are coding against right now. Do not change a name, a signature or what a docstring promises. If you believe one is wrong, stop and say so in your report; do not work around it silently.
- **`docs/test-cases.md`** gives every test's input and expected output. **`docs/backend-architecture.md`** gives the rules. Where your brief and those documents disagree, say so in your report.

## How you work

1. **Tests first.** Write the tests for your cases, with the case ID in each test's name (for example `test_fu03_cheaper_station_ahead`). Run them and see them fail. Then implement until they pass.
2. **Only your files.** Create and edit only the files your brief lists. Never edit `tests/conftest.py`, `pyproject.toml`, `config/`, another builder's module, or anything in `docs/` except your report. Import shared helpers, do not copy them: `from tests.conftest import load_road, SMALL_CSV`.
3. **Only your tests.** Run just your own test files, for example `uv run pytest tests/test_fuel.py -q`. Other builders' tests will be failing while they work; that is not your concern. Do not run the whole suite.
4. **Lint your files:** `uv run ruff check <your files>` and `uv run ruff format <your files>` must both be clean.
5. **No new dependencies.** Available: Django 6.1, Django REST Framework, httpx, numpy, scipy, dj-database-url, psycopg; for tests pytest, pytest-django, pytest-socket.
6. **No network.** Tests are blocked from reaching beyond this machine.
7. **No git.** Do not commit, stash, reset or check out anything. The controller commits.
8. **No other agents.** Do the work yourself.

## What good looks like

- Someone must be able to explain this code line by line in an interview. Prefer clear names and plain steps to clever ones.
- Comment **why**, not what. Keep the module docstring; give each function a short docstring.
- Type hints on every function.
- Nothing the documents do not ask for: no extra options, no speculative generality, no handling for cases that cannot happen.
- Research prototypes in `docs/plan/research/scripts/` show working maths you may port. They are throwaway scripts: take the logic, not the style.

## Your report

Write it to the file your brief names, then reply to the controller with a five-line summary.

The report holds:

1. Files created or changed.
2. The exact test command you ran and its final output, pasted.
3. A table: each test-case ID → the name of the test that covers it. Every ID in your brief must appear.
4. Anything you did differently from the brief or the documents, and why.
5. Anything in the documents you found unclear, contradictory or untestable.
6. Anything you are not sure is right.
