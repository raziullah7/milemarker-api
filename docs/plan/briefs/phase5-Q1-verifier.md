# Brief 5Q1: the independent verifier and the live runner

You are a tester. A small Django API has been built by other people. Your job is to write a checker that knows **only what the documents promise**, and a runner that puts the running API through every documented case. You wrote none of the application, and that is the point: you must not copy its logic or trust its tests.

The repository root is the folder you were given; every path is relative to it.

## Rules

- **Independence.** `tests/verify.py` imports nothing from `config`, `stations` or `trips`, and you do not read `trips/services/planner.py`, `answer.py` or `fuel.py` before you have written it. Build it from `docs/test-cases.md` section 4 and `docs/backend-architecture.md` section 11. Afterwards you may read anything.
- **Your files only:** `tests/verify.py`, `tests/test_verify.py`, `scripts/live_check.py`, and your report `docs/plan/reports/phase5-Q1.md`. Do not fix the application. If you find a fault in it, that is a finding: describe it exactly in your report, with the request that shows it.
- No new dependencies (httpx is available for the runner). No git commands. No other agents.
- `uv run ruff check <your files>` and `uv run ruff format <your files>` must be clean. Tests: `uv run pytest tests/test_verify.py -q`, and at the end the whole suite, `uv run pytest -q`.
- Comment why, not what. Someone must be able to explain this code in an interview.

## Read

- `docs/test-cases.md`: section 4 (rules R1 to R16), section 2.11 (VF-01 to VF-19), section 3 (the live cases), section 5 (speed checks)
- `docs/backend-architecture.md` section 11 (the response and the error table)
- `docs/requirements.md` section 9 (acceptance checks)
- `tests/conftest.py` for the helpers you may import in `tests/test_verify.py`: `load_road`, `use_real_stations`, `real_index`
- `tests/test_api.py` only to see how a test replaces the routing call and creates stations; do not copy its assertions

## Part 1: `tests/verify.py`

`verify_response(body: dict, prices: dict, stop_cost=None) -> list[str]`

- `body` is a parsed 200 response.
- `prices` maps a station ID to what the CSV says about it: its lowest price as a `Decimal`, and the name, address, city and state of the first row at that price, trimmed. Give the module a function that builds this from a CSV path, reading the file with the `csv` module. In tests with invented stations, the test builds the same mapping by hand.
- `stop_cost` is the stop cost the request sent, or `None` if it sent none (rule R9).
- It returns one line per broken rule, each starting with the rule's ID (`R4: ...`), and an empty list when every rule holds. It checks every rule every time; it does not stop at the first.

Read money, gallons and prices as exact decimals: parse the JSON text with `json.loads(text, parse_float=Decimal)` where you have the text, and convert with `Decimal(str(x))` where you only have floats.

## Part 2: `tests/test_verify.py`

VF-01 to VF-19 as the catalogue gives them, with two notes:

- **VF-02 to VF-18** need a correct response to break. Get one by calling the endpoint through Django's test client with the routing call replaced, on a recorded road with the real stations (`use_real_stations`). Then break one thing at a time in a copy.
- **VF-01** as written covers "every 200 produced by the endpoint tests". Do it in your own file: request a spread of trips through the test client (New York to Los Angeles at stop costs 10, 0 and 25; Dallas to Houston; Seattle to Miami; Chicago to Houston; Boston to Washington; each on its recorded road with the real stations) and verify every answer. Say in your report that VF-01 is covered this way.

## Part 3: `scripts/live_check.py`

Runs the documented live cases against a running server and prints what happened.

- `uv run python scripts/live_check.py [--base-url http://127.0.0.1:8000] [--only P01,N03] [--markdown]`
- Cases P01 to P20, N01 to N26 and S01 to S03, exactly as `docs/test-cases.md` sections 3 and 5 give them: the request, the expected status, and each expected field or error code. Keep the cases as data (a list), separate from the code that runs them.
- Order and pacing as section 3 says: at least 1.2 seconds between requests; N15 last, after a 60-second pause.
- Every 200 is also checked with `verify_response`, with prices from `data/fuel-prices-for-be-assessment.csv`.
- One line per case: ID, request, expected, actual (status, code and the figures the case names), PASS or FAIL, and for a FAIL which expectation or rule failed. `--markdown` prints the same as table rows ready to paste into `docs/test-cases.md`.
- Exit code 0 only if every case passed.
- The runner must not import the application either: it talks to the server over HTTP and reads the CSV.

Some expected figures in section 3 were measured during design and are marked "≈, pass within 2%". Keep them as the document has them. If a live result falls outside, report it as a FAIL and say so in your report; do not adjust the expectation.

## Running it live

The public routing servers allow one request a second and the project has a budget of calls, so:

1. Start the server yourself in the background: `uv run python manage.py runserver 127.0.0.1:8000 --noreload`. PostgreSQL is running and the stations are loaded.
2. While developing, use `--only` with one or two cases.
3. Make **one** full run. Do not repeat it.
4. Stop the server when you are done.

## Your report: `docs/plan/reports/phase5-Q1.md`

1. Files created.
2. Test commands and their final output, pasted.
3. The full output of your one full live run.
4. Every FAIL, live or in your tests, with the exact request and what came back. Separate "the API is wrong" from "the document's expectation is wrong or stale", and say why you think so.
5. Anything in the documents you could not turn into a check.

Reply to the controller with: status, the number of live cases passed and failed, and each failure in one line.
