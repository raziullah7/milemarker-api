# Report 9T: use cases and test cases for Part 2

Status: done, in two rounds. The first round wrote the use cases and test cases. The second wrote in the answers to the 27 points the first round could not settle, decided in `docs/plan/PHASE-9.md`, "Points raised by the test design, settled". Changed: `docs/use-cases.md`, `docs/test-cases.md`. Added: this report. No other file touched, no git command that changes anything, no test, container or request run. Both documents keep LF line endings.

Sources: `docs/requirements.md`, `docs/backend-architecture.md`, `docs/plan/PHASE-9.md` (spec changes, settled gaps, rulings, and the points settled after the first round), the two audit reports, and, for the stand-in routing server and the Makefile, `docs/plan/briefs/phase10-A-harness.md` and `phase10-B-make-ci.md`. The waypoints and distances of the recorded roads were read from `tests/fixtures/roads/`, and the five US places named Mexico from `data/us_cities.csv`.

## Counts

**Use cases added: 19**, UC-21 to UC-39. Two actors added (Visitor, Maintainer). UC-36 supersedes UC-14 for release 2; UC-14 stays as release 1.0's record, with one paragraph saying so.

**Test cases added: 246**, all in the new section 9 of `test-cases.md`, with new prefixes. The second round added 19 of them.

| Section | Prefix | Cases | Added in the second round | Kind |
|---|---|---|---|---|
| 9.2 Configuration and start-up | CF | 36 | CF-34, CF-35, CF-36 | 20 in the suite, 16 against the stack |
| 9.3 Cache | CA | 24 | CA-24 | 20 in the suite (Redis tests), 4 against the stack |
| 9.4 Health, schema and docs addresses | HS | 19 | — | 17 in the suite, 2 against the stack |
| 9.5 Host checking and middleware | HM | 10 | HM-10 | suite |
| 9.6 The front door, through nginx | PX | 18 | — | stack |
| 9.7 The stand-in routing server | SI | 11 | — | suite |
| 9.8 End to end | EE | 8 | — | stack |
| 9.9 The viewer, pure calculations | VT | 15 | VT-13, VT-14, VT-15 | viewer unit tests |
| 9.10 The viewer, the panel and its states | VP | 19 | VP-18, VP-19 | viewer component tests |
| 9.11 The viewer in a browser | VB | 30 | VB-29, VB-30 | stack, Playwright (VB-27 by hand) |
| 9.12 Makefile, CI and the repository | MK, CI, RP | 22, 7, 6 | MK-20, MK-21, MK-22 | stack, CI, by hand |
| 9.13 Fixes from the second audit | QB | 17 | — | suite |
| 9.14 The verifier's options | VR | 4 | VR-01 to VR-04 | suite |

Also added:
- In `test-cases.md`:
  - section 9.1, the test data: the recordings, the Redis stand-ins, viewer answers V1 and V2, the 13 error bodies, test line T, line M, the viewer's test IDs and the figure formats;
  - correctness rule **R17** in section 4;
  - acceptance checks 11 to 20 in section 8.
- In `use-cases.md`:
  - rows in "at a glance";
  - new traceability rows;
  - a table for acceptance checks 11 to 20;
  - a table "Audit rulings with a test".

Suite cases use section 2's columns; stack, browser, CI and by-hand cases use section 7's, with Actual and Result empty.

A script checked both files after each round. Its checks:
- 504 test IDs in all, none defined twice.
- Every test ID named in `use-cases.md` is defined.
- Every new test ID is named in `use-cases.md`.
- Every UC in a test row exists, and all 39 UCs are in "at a glance".
- Every table row has its header's column count.
- No CR characters.

## Coverage

Every new or changed requirement, decision and acceptance check, with the cases that cover it. None is empty.

| ID | Use cases | Test cases |
|---|---|---|
| FR-18 | UC-21, UC-22 | VP-12, VP-13, VB-01 to VB-03, VB-25, PX-18, EE-08 |
| FR-19 | UC-29 | HS-11 to HS-18 |
| FR-20 | UC-30 | HS-01 to HS-08, HS-10, HS-19 |
| FR-21 | UC-21, UC-22 | VP-12, VP-13, VP-14, VP-18, VB-25, VB-26 |
| FR-22 | UC-21 | VT-01 to VT-15, VB-01 to VB-11 |
| FR-23 | UC-21, UC-27 | VP-02 to VP-05, VP-15, VP-16, VP-19, VB-06, VB-12 |
| FR-24 | UC-23, UC-24, UC-25 | VP-06 to VP-11, VP-18, VB-23, VB-24 |
| FR-25 | UC-22, UC-26, UC-27, UC-28 | VB-13 to VB-16, VB-29, VB-30 |
| FR-26 | UC-21, UC-27, UC-28 | VB-14, VB-17, VB-27 |
| NFR-9 | UC-14, UC-36 | CF-33, MK-10 (and release 1.0's FC-01, CT-01, M02) |
| NFR-16 | UC-18, UC-34 | PX-07, PX-08, HM-07, HM-08, HS-08, HS-09, CA-14, CA-15 (and N15, EP-34) |
| NFR-17 | UC-38 | CI-01 to CI-07 |
| NFR-18 | UC-32, UC-33 | CA-01 to CA-24, HS-03 to HS-05 |
| NFR-19 | UC-31, UC-36 | CF-10, CF-18, CF-32, PX-01, PX-13 |
| NFR-20 | UC-35, UC-36 | CF-01 to CF-11, CF-16, CF-20, CF-34, CF-35 |
| NFR-21 | UC-36, UC-38 | CF-12, CI-03 |
| NFR-22 | UC-36 | CF-21 to CF-28 |
| NFR-23 | UC-31 | PX-02, PX-03 |
| NFR-24 | UC-35 | CF-11, CF-13, CF-14, CF-15, CF-36, PX-04 |
| NFR-25 | UC-36 | CF-29, CF-30, CF-31, CI-04 |
| NFR-26 | UC-39 | SI-01 to SI-11, EE-01 to EE-07, VR-01, VR-02, MK-16, MK-20, MK-21 |
| NFR-27 | UC-37, UC-38 | MK-04, MK-08, MK-22, CI-03, RP-04, RP-05 |
| NFR-28 | UC-21, UC-38 | RP-06, CI-06, VB-18, VB-19 |
| NFR-29 | UC-21 | VT-12, VB-21, VB-22 |
| NFR-30 | UC-37 | MK-01 to MK-22 |
| NFR-31 | UC-38 | RP-01 |
| D-2 | UC-11, UC-21 | VP-16 (and M01, AN-09, R11) |
| D-15 | UC-04, UC-32 | CA-01 to CA-05, CA-18, CA-20 (and EP-02 to EP-08) |
| D-16 | UC-33 | CA-06 to CA-13, CA-15, CA-21, CA-22, CF-25 |
| D-17 | UC-31, UC-34 | PX-07, PX-08, PX-13, PX-16, HM-07, CF-05, CF-18 |
| D-18 | UC-21, UC-28 | VB-15, VB-16, VB-17, VB-27, VB-28, VB-30 |
| D-19 | UC-21, UC-22 | VP-14 |
| D-20 | UC-29 | HS-15, HS-16, HS-17 |
| D-21 | UC-31, UC-36 | CF-01, CF-02, CF-04, HM-01 to HM-03, PX-15 |
| D-22 | UC-32 | CA-19 |
| D-23 | UC-31, UC-36 | CF-12, PX-17 |
| D-24 | UC-25, UC-31 | PX-09, PX-10, VP-11, VB-24 |
| Check 11 | UC-36 | CF-33, CF-18, CF-21, CF-22, CF-23, PX-01, PX-13 |
| Check 12 | UC-32 | CA-20, CA-01 |
| Check 13 | UC-33 | CA-21, CA-22, CA-06, CA-10, CA-11, CA-12, HS-04, HS-05 |
| Check 14 | UC-34 | PX-07, PX-08, HM-07, HM-08 |
| Check 15 | UC-29, UC-30 | HS-01, HS-19, HS-11 to HS-16, HS-18 |
| Check 16 | UC-36, UC-38 | CF-12, CI-02, CI-07 |
| Check 17 | UC-39 | EE-03, EE-05, EE-06 |
| Check 18 | UC-21 | VB-01, VB-04, VB-05, VB-06 |
| Check 19 | UC-24, UC-26, UC-27 | VB-13, VB-14, VB-23, VB-24, VP-06, VB-19 |
| Check 20 | UC-37 | MK-01, MK-05, MK-02, MK-10 |

The tests the rulings name are in place:
- A foreign `Host` gets 400 in the error shape: HM-02, PX-15.
- Two client addresses get separate buckets: HM-07, PX-08.
- A stop swapped for a far-away station is caught by R17: QB-01.
- The second routing server is tried after a 302, 403 or 404: QB-04.

The "Audit rulings with a test" table in `use-cases.md` lists each.

## The 27 settled points, and the cases that now carry them

Each row of "Points raised by the test design, settled". A case that follows a row cites it as "row n". Where a row puts a value off to Phase 12, the case states what is checked now and marks that one value "recorded in Phase 12".

| # | Settled point | Cases |
|---|---|---|
| 1 | Four collection trips recorded in Phase 10 | 9.1 "Recordings"; EE-03 (8 route requests, none unmatched); EE-04 (now P01 to P11, N01 to N22, N24 to N26; 11 route requests) |
| 2 | The verifier accepts a host its caller names; `live_check.py --routing-host fake-osrm` | R15 in section 4; VR-01, VR-02; EE-04 |
| 3 | R17 checks against the places its caller gives | R17 in section 4; VR-03 (the endpoint tests' own places file), VR-04 (the hand-added places by default); QB-01, QB-02 |
| 4 | Progress linear from 8 s to 15 s | Section 9.9's introduction; VT-08, VT-13; the time in VT-14 |
| 5 | Stop 1 appears at 8 s | VT-07, VT-10, VB-09, VB-10 |
| 6 | Two running totals: scaled great-circle miles and Web Mercator length, linear between points | 9.1 "Test line T" and "Line M"; VT-05, VT-13, VT-14 (worked figures to 1e-6) |
| 7 | Cancelling the intro shows the trip finished; the camera stays | VT-15, VB-11 |
| 8 | Only `start` or only `finish`: the API is asked | VP-18; UC-22 A3, UC-24 A4 |
| 9 | Number formats; a heading per code over the API's message | 9.1 "Viewer test IDs" and formats; VP-01 to VP-11, VP-17, VP-19; VB-06, VB-14, VB-23, VB-24. Headings and fixed sentences: recorded in Phase 12 |
| 10 | Route colour and image tolerances | VB-04, VB-07: recorded in Phase 12 |
| 11 | No turning globe under reduced motion | VB-29; UC-22 A2 |
| 12 | A late description is ignored | VB-30; UC-28 A2 |
| 13 | Credits name the sources in use; Natural Earth without WebGL2 | VB-14, VB-17; UC-27 |
| 14 | Redis timeouts 0.1 s and 0.25 s, no retry; 0.5 s limit against Redis up | CA-07, CA-24; UC-33 step 3 |
| 15 | One INFO line per 200 from `trips`; WARNING per error | CF-15, CF-36; UC-35 |
| 16 | nginx replaces a client's `X-Request-ID` | PX-04; UC-35 A2 |
| 17 | A missing `/assets/` file: nginx's 404 `not_found` | PX-12, PX-05; UC-31 A7 |
| 18 | The route lists 400, 422, 429, 500, 502, 503; `not_found` and `method_not_allowed` in the opening text | HS-14; UC-29 step 3 |
| 19 | One `Referrer-Policy`; Django for API answers, nginx for its own | HM-10, PX-05; UC-31 |
| 20 | The policy's text in Phase 12; hosts named; on `/`, not on `/api/v1/docs/` | PX-06 (text recorded in Phase 12); VB-20, VB-27, VB-28 |
| 21 | `ROUTING_SERVERS` trimmed, empties dropped; `ImproperlyConfigured` naming variable and entry | CF-09, CF-34, CF-35 |
| 22 | The stand-in's log JSON | SI-07 |
| 23 | The stand-in runs from the test image | CF-29, EE-01; UC-39 step 1 |
| 24 | pre-commit: Ruff checks, formatter, hygiene hooks | RP-04; UC-38 A2 |
| 25 | Brief 10B's targets are binding | MK-01, MK-09 to MK-11, MK-14, MK-16, MK-20, MK-21, MK-22; section 9.12's introduction; UC-37, UC-39 |
| 26 | Pin values recorded when the test is written | QB-15 |
| 27 | `handler403` not built | HM-06 (asserts `handler400` set, `handler403` not). No case ever expected a 403 answer |

## Still not specifiable

What the decisions leave open, with the question. Values put off to Phase 12 by rows 9, 10, 20 and gap 27 are not repeated here: headings and fixed sentences, the route's colour, the image tolerances, the policy's text and the credit wording.

1. **Money of $1,000 or more.** Row 9 gives a thousands separator for miles only, and its money example, $867.27, is under $1,000. Seattle to Miami (VB-02) may cost more. Is it `$1,034.56` or `$1034.56`? No case depends on it: VB-06 compares figures as numbers, and the VP cases use money under $1,000.
2. **The assumptions' format.** Under row 9 the range would read `500.0 mi` and the stop cost `$10.00`. Is that meant? VP-02 compares the six values as numbers.
3. **No answer at all.** The heading shown when no answer arrives (VP-11, second half): is it the `api_unavailable` heading, or its own? VP-11 does not assert which.
4. **The stand-in's `path`.** Does it include the query string? SI-07 checks only that it begins with the route path.
5. **The four added recordings' file names (row 1).** EE-03 says "the recording added for each". The names are chosen in Phase 10.

The specifications were brought in line with the 27 decisions while this round was written, and the cases follow their wording. Three points came from those edits:
- Architecture section 19 now credits Natural Earth, whose outlines are always the bottom layer. So VB-17 names it in every state, alone when only the outlines are drawn.
- Section 18 logs an `internal_error` once at ERROR, with no WARNING line (CF-36).
- From Phase 12, `make e2e` also runs the browser tests (MK-20).

I also named the viewer's test IDs in 9.1. That is test design, not a decision from the specs, and the builder must use those `data-testid` values or the controller must amend the table.

## Existing sentences changed, and why

Both rounds. Part 1 text first.

`docs/test-cases.md`:

| Where | Change | Why |
|---|---|---|
| Section 1, last paragraph | The fixture sentence first gained the local Redis, then read: "except those to the same machine: the local database and, for their own tests, the local Redis and the stand-in routing server" | D-15 and NFR-18 (Redis tests); the settled correction of architecture section 13 (the stand-in's tests connect to 127.0.0.1) |
| Section 2.11, first sentence | "R1 to R16" becomes "R1 to R17" | R17 added (ruling Q0b-1) |
| Section 4, R6 | Sentence added: every stop after the first buys more than 0 gallons; the first buys 0 or more | Ruling Q0b-5 |
| Section 4, R12 | The tolerance sentence replaced by the line's own scale, within 0.1 mile | Ruling Q0b-2 |
| Section 4, R15 | "…or a host the verifier's caller names: the end-to-end run names the stand-in, `fake-osrm`" added | Row 2 |
| Section 4, R17 | Added in the first round; in the second, the places come from the verifier's caller, by default the real file and the five hand-added places | Ruling Q0b-1; row 3 |
| Section 8 | Rows for checks 11 to 20 added | Brief |

`docs/use-cases.md`:

| Where | Change | Why |
|---|---|---|
| Introduction | "R1 to R16" becomes "R1 to R17" | R17 added |
| UC-04, preconditions | "by the same server process" becomes "by the same server process or, when the cache is Redis, by any worker (UC-32)" | False with a shared cache (D-15, NFR-18) |
| UC-11, A1 | The optional, unspecified map page becomes "The viewer (FR-18) draws this same `map` on its own page: see UC-21" | FR-18 is a specified Want now (D-2) |
| UC-14 | One paragraph added: UC-36 supersedes it; its steps are kept as release 1.0's record | Its start-up is false for release 2 (NFR-22), but CT-01 to CT-05, FC-01, FC-04 and M02 were run against it |
| UC-19, step 2 | The fixture sentence, as in test-cases section 1 | As above |
| UC-20, preconditions and A1 | "freshly started" becomes "with an empty cache…"; "Restart the API" gains "and Redis too when the cache is Redis" | Redis outlives the API process (D-15; Q0a-13) |
| Traceability, introduction | "R1 to R16" becomes "R1 to R17" | R17 added |
| Traceability rows FR-18, FR-19, NFR-17, NFR-18 | Replaced | They said "Nice" and "none", or "only if built" |
| Traceability rows NFR-9, NFR-16, D-2, D-12, D-15 | Text brought in line, and cases appended | Changed in Part 2, or by ruling Q0b-3 (D-12) |

In the second round I also changed my own first-round text wherever a decision contradicted it:
- UC-21, UC-22, UC-24, UC-27 to UC-29, UC-31, UC-33, UC-35, UC-37, UC-38 and UC-39, as listed in the table above;
- in section 9: CF-09, CF-15, CF-29, CA-07, HS-14, HM-06, PX-04, PX-05, PX-06, PX-12, SI-07, EE-01, EE-03, EE-04;
- VT-05, VT-07, VT-08, VT-10;
- VP-01 to VP-11 and VP-17;
- VB-04, VB-06, VB-07, VB-09, VB-10, VB-11, VB-14, VB-17, VB-23, VB-24, VB-28;
- MK-01, MK-09, MK-10, MK-11, MK-14, MK-16, RP-04 and QB-15.

Left as they are, though now dated:
- test-cases section 3's "Every 200 is also checked against rules R1 to R16", the record of the 18 Nov live run;
- FC-04, FC-05, CT-04 and M02, records of release 1.0;
- UC-12 step 3, whose list of retry triggers is incomplete under Q0b-3 but not false;
- FU-23, which describes `fuel.py`'s own count.

The QB and VR cases name Part 1 use cases (UC-03, UC-08, UC-12, UC-13, UC-19). Those use cases' test lists were not extended; the rulings table traces them instead.

## For the controller

- **Ownership overlap with brief 10C.** R6, R12, R15 and R17 are written in section 4 from the rulings and rows 2 and 3, and QB-01 to QB-17 and VR-01 to VR-04 are the catalogue rows for 10C's fixes. 10C should check them rather than add duplicates.
- **A trap between row 21 and ruling Q0a-06.** If Compose passes `ROUTING_SERVERS` through as `${ROUTING_SERVERS}` with nothing set in the shell, the API receives it set but empty and, by row 21, refuses to start. A fresh clone would then not run; CF-33 would catch it.
- **Spec text.** NFR-27, architecture sections 13, 18 and 19 now match the decisions. Still to come, by 10C as ruled: architecture section 8 on purchases under 0.005 gallons, and section 9 on which answers end a routing attempt.
- **Readings I made**, none a new decision:
  - "A ban on framing" is `X-Frame-Options: DENY`.
  - `check --deploy` "passes" means no issue reported, silenced checks allowed.
  - "Evicts the least recently used key" is Redis's `allkeys-lru`.
  - A stop is reached when the head's progress equals its drawn position.
  - A suggestion link keeps the address's other parameters as they were.
  - Rate-limit cases through nginx use a request that makes no routing call.
  - The keyboard pass is both automated and by hand.
- **Routing budget.** Only EE-08 spends a public routing call (one, in Phase 14), and VB-27 reuses its cached trip. Every other stack case runs on the stand-in, or makes no routing call. The four recordings of row 1 cost three more calls in Phase 10.
