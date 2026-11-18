# Brief R3: write the use cases and the test cases

You are a test designer. A small Django API has been fully specified but **not built yet**. Your job is to write down, before any code exists, what it must do for its users and exactly how that will be proven. Builders and testers will work from your two documents, so they must be precise.

Do not write code. Do not spawn other agents. Edit only the two files named below.

## Read first

1. `docs/requirements.md` (what is required: FR, NFR and D items, acceptance checks)
2. `docs/backend-architecture.md` (how it works: request flow, rules, response shape, error table, testing section)
3. `docs/plan/phase-material.md` (a draft list of live cases, correctness rules, hand-worked fuel cases and use cases; every item in it must appear in your documents, and you should add what the specs imply that it misses)
4. `docs/plan/reports\phase1-cities-and-no-fuel.md` (measured facts you can use as expected results)

Where the draft material and the specs disagree, the specs win. Say so in your reply.

## Write

### `docs/use-cases.md`

- A short introduction and the actors (driver or dispatcher using a client, an operator who loads data, a reviewer running the project).
- One section per use case, with a stable ID (`UC-01` …). Each has: goal, actor, preconditions, the exact request, the main flow as numbered steps, what comes back (the fields that matter and their values or ranges), alternative flows, the requirement IDs it covers, and the test-case IDs that prove it.
- Cover at least the use cases in the draft list. Add any the specs imply.
- End with a **traceability table**: one row for every FR, NFR and D item in `requirements.md`, giving the use cases and test cases that cover it. No requirement ID may be missing. If something genuinely cannot be tested by a use case or test case (for example the deadline), say what proves it instead.

### `docs/test-cases.md`

- **How the tests are organised:** the levels (unit, exactness, integration, independent verification, live, in the container, Postman collection, fresh clone), one line each on what the level proves and how it is run. The live cases are run by `scripts/live_check.py` against a running server; automated tests by `uv run pytest`.
- **Automated test catalogue**, grouped by area (places, loader and index, geometry, station search, fuel plan, routing client, endpoint, verifier). Each case has an ID, the input and the expected output with exact values. Use the hand-worked fuel cases and fixed values from the draft material exactly as given: they have been checked. For other areas derive the cases from the specs. Include positive, negative and boundary cases for every area.
- **Live cases**, positive (`P01` …) and negative (`N01` …). Each row: ID, the exact request as a URL path and query string, the expected status, the expected fields or error code, then two empty columns, **Actual** and **Result**, to be filled in when the cases are run. Figures taken from research are approximate: write them as "≈ value, pass within 2%".
- **Correctness rules** checked on every successful response, numbered.
- **Speed checks.**
- **Cases that can only be tested with a fake routing service**, and why.

## Rules for both documents

- Every test case states its **input** and its **expected output**. "Works correctly" is not an expected output.
- Every ID is unique and stable. Use-case and test-case IDs must cross-reference correctly in both directions.
- Use the exact field names, error codes and status codes from the architecture document.
- The base path is `/api/v1/route/`. Show query strings unencoded for readability, for example `?start=New York, NY&finish=Los Angeles, CA`.
- These files go into a public repository. Write plain, direct sentences. No filler, no marketing. Do not mention agents, plans or how the documents were produced.
- Use tables where rows share a shape, and keep table cells short.

## Reply to me with

- The number of use cases and of test cases by section.
- Anything in the specs you found unclear, contradictory or untestable, with the section it is in. This matters as much as the documents: do not guess silently.
- Any item from the draft material you changed or dropped, and why.
