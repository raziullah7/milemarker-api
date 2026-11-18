# Brief 9T: use cases and test cases for Part 2, before any code

The project's rule is that every requirement is traced to a use case and to test cases, each with an exact input and an expected output, written before the code. A second stage of work has been specified. You are extending the two test-design documents to cover it. You are not writing code.

The repository root is the folder you were given; every path is relative to it.

## Rules

- **Your files only:** `docs/use-cases.md`, `docs/test-cases.md`, and your report `docs/plan/reports/phase9-T.md`. Change nothing else. No git command that changes anything. No other agents. Do not run tests, containers or any request.
- **Add; do not rewrite.** Part 1's use cases and test cases are a verified record with actual results filled in. Leave them as they are, except where a Part 2 decision makes a sentence false; list every such change in your report.
- Every test case states its exact input and its expected output, precisely enough that two people would write the same test. "Works correctly" is not an expected output. Leave the Actual and Result columns empty.
- Take every figure, address, name and code from the specifications. Invent nothing. Where the specifications do not say what the expected output is, do not guess: put the case in your report under "cannot be specified", with the question.
- Match the documents' existing format, voice, ID style and column layout exactly.

## Read first, in full

- `docs/requirements.md` and `docs/backend-architecture.md` as they now stand. The new material is: FR-18 to FR-26, NFR-16 to NFR-31, decisions D-15 to D-24, acceptance checks 11 to 20, and architecture sections 2, 3, 10, 11, 13, 16, 18 ("Running it") and 19 ("The viewer").
- `docs/use-cases.md` and `docs/test-cases.md` as they are: their structure is the pattern to follow.
- `docs/plan/PHASE-9.md`: the sections "The spec changes", "Gaps found while writing the specs, settled" and "Rulings on the audits". The rulings name tests that must exist (for example: a foreign `Host` gets 400 in the error shape; two client addresses get separate rate-limit buckets; a stop swapped for a far-away station is caught by a new verifier rule R17; the second routing server is tried after a 302, 403 or 404).

## What to write

### `docs/use-cases.md`

New use cases, continuing the numbering, in the existing template, for at least: watching a trip in the viewer; opening the viewer with no trip and choosing an example; the viewer when a place is mistyped, when the API refuses the trip, and when the API cannot be reached; the viewer with reduced motion and without WebGL2; reading the API's documentation page; checking the service's health; the service when Redis is down; a client trying to escape the rate limit through the proxy; starting the whole stack from a fresh clone (extend or supersede the existing use case, saying which); running the checks with `make`; a push to the repository running CI; running the end-to-end stack with no call to the public routing servers. Update the "at a glance" table and the traceability table so every new requirement ID, decision ID and acceptance check appears.

### `docs/test-cases.md`

New sections after the existing ones, each a table in the existing column layout, with new ID prefixes that do not collide with existing ones. Cover at least:

- **Configuration and start-up:** each environment variable's default and its effect; a bad `ROUTING_SERVERS` value; the deployment check; the start order; the one-off setup; a second start not doubling the stations; shutdown letting a request finish.
- **Cache:** shared between workers; the version in the key; the station fingerprint in the answer's key; the fallback when Redis is unreachable, with its timing limit; the 30-second pause before trying again; recovery; one warning per process; the in-memory cache when `REDIS_URL` is unset.
- **Health, schema and docs addresses:** every documented answer, including health when stations are not loaded, and that health is not rate limited while the others are; the committed OpenAPI document matching the code; what the document must contain.
- **Host checking and middleware:** allowed and foreign hosts; both URL forms still answering with no redirect.
- **The front door (through nginx):** the release 1.0 address still answering; compression on JSON and on the viewer's files; the request ID header; the security headers and where the content security policy applies; the rate limit with forged `X-Forwarded-For`, and separate buckets for separate clients; the JSON answers when the API is down or slow; an unknown address still getting the API's JSON 404; the API having no published port.
- **The stand-in routing server:** a recorded pair, its reverse, a far pair, a malformed request, the request log and its reset, both URL paths.
- **End to end:** the whole Postman collection on the stand-in; the count of routing requests it must make; no route out for the API.
- **The viewer, pure calculations:** progress along the line to position; position along the drawn line for each stop; the road miles at the head; the counters at given moments; the order stops appear in. Give small worked inputs with exact expected numbers wherever the specification makes that possible.
- **The viewer, the panel and its states:** loading; a plan; each API error code by name; suggestions as links; rate limited; API unreachable; a warning present; the first stop's card saying the fuel is priced at the nearest listed station.
- **The viewer in a browser:** the animation run to its end on each example trip; the route drawn; one marker per stop; totals equal to the API's; Skip, Replay, the scrubber, cancelling the intro; choosing a stop's card; reduced motion; no WebGL2; map servers unreachable; the credits visible; keyboard reachability; the accessibility scan; no content-security-policy violation in the console.
- **Makefile and CI:** each target and what it must do; what CI runs and what makes it fail.
- **The fixes from the second audit** (rulings table "QA-0b"): one case per fix, with the exact wrong input and the expected catch.
- **Section 8 (acceptance checks):** add checks 11 to 20, each mapped to the cases that prove it.

## Your report: `docs/plan/reports/phase9-T.md`

- Counts: use cases added, test cases added, by section.
- A coverage table: every new requirement ID, decision ID and acceptance check, and the cases that cover it. None may be empty.
- "Cannot be specified": each case whose expected output the specifications do not determine, with the exact question.
- Every existing sentence you changed, and why.

Reply to the controller with: status, the counts, and one line for each "cannot be specified".
