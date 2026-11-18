# Brief 9S: bring the specifications in line with Part 2

The project's rule is that the specifications are written before the code. A second stage of work has been approved. Its decisions are final and are listed in one place. Your job is to write them into the three specification documents so that a builder who reads only those documents builds the right thing.

The repository root is the folder you were given; every path is relative to it.

## Rules

- **Your files only:** `docs/requirements.md`, `docs/backend-architecture.md`, `docs/prd.md`, and your report `docs/plan/reports/phase9-S.md`. Change nothing else. No git command that changes anything. No other agents. Do not run the tests or touch containers.
- **Decide nothing.** Every decision is in the two sources below. Where they leave something open that a builder would have to guess, do not guess: write the gap in your report and leave a clearly marked sentence in the document saying the point is open.
- **Change only what Part 2 changes.** Leave every other sentence as it is. Part 1's text is a record that was verified.
- Match the documents' voice: plain, direct sentences, short paragraphs, tables where rows share a shape, a term explained the first time it appears. No marketing words, no filler.

## Sources

1. `docs/plan/PHASE-9.md`, the section "The spec changes". This is the binding list: requirements changed and added, decisions changed and added, the other edits, and the result of the `drf-spectacular` trial.
2. `docs/plan/PLAN.md`, from the heading "Part 2" to the end: the target architecture, what production level means here, the Makefile targets, and "The viewer" (stack, what the page does, the animation beat by beat, robustness, how it is proven).

Read both in full, and all three documents in full, before writing.

## What to write

- **`docs/requirements.md`:** apply every row of the tables in source 1, the out-of-scope edit and acceptance checks 11 to 20. Requirements that were tier "Nice" and are now built become "Want". The viewer's requirements (FR-21 to FR-26) may sit under their own short heading inside section 4. Update the tier notes in section 3 only if a sentence there has become false.
- **`docs/backend-architecture.md`:** the edits source 1 lists, section by section. For the two new sections at the end:
  - **Running it:** the table of services with what each is, its published port and its role; the start order and what gates it; the configuration table (each variable, its default, what it does); what a stop does; what is logged; the front door (what nginx serves, what it passes through, the forwarded-address rule and why the API has no published port, compression, the JSON answer when the API is down, security headers).
  - **The viewer:** its parts and what each may do (the API client, the pure timeline calculations, the one module that talks to the map library, the panel components); the animation beat by beat; that the route is revealed by moving a colour boundary along the line and why stop timing uses position along the drawn line, not the mile marker; the fallbacks; the map sources with the credit each requires.
  - Leave section 4 (folder layout) and section 14 (speed) untouched: they are updated when the files and the measurements exist.
- **`docs/prd.md`:** scope, non-goals, release criteria and known limits, where Part 2 makes them false.

## Your report: `docs/plan/reports/phase9-S.md`

- A table: each row of "The spec changes", and the document, section and line where it now lives.
- Every gap you found: something a builder would have to guess.
- Any existing sentence you had to change that the sources did not mention, and why.

Reply to the controller with: status, the number of gaps, and one line for each gap.
