# Brief QA-5: prove the fixes, review the change adversarially

You are an independent reviewer. You did not write any of this code, and the people who did will not see your work before the controller does. Your job: decide with proof whether release 2.1.0 fixes what it claims, breaks nothing, and whether its documents are true. Weigh proof against assumption. A claim you ran and saw is **proved**. A claim you reasoned from reading is **assumed**: say so, and say what would prove it.

The repository is `F:\Spotter-AI\milemarker-api`. The change under review is `b3d3bef..HEAD` on branch `next`; list it with `git log --oneline b3d3bef..HEAD`. `docs/plan/PHASE-15.md` says what was found and what was decided, and why. The builders' reports are in `docs/plan/reports/phase15-F1.md`, `phase15-F2.md` and `phase15-D.md`. Read those after you have formed your own view of the diff, not before.

## 1. Reproduce the old proofs on the new code

Earlier, four proof agents reproduced 11 findings on `v2.0.0`. Their scripts are in the session scratchpad: `C:\Users\Bakemono\AppData\Local\Temp\claude\a83fc35170f12650\2174297b-dd78-49b7-8d5b-a766fb1b748a\scratchpad\proof\`. Folders `a` to `d` each hold a `repo` with proof tests under `repo/tests/test_proof_*.py`, plus `report.md` files. Folder `b` also has `m5_dbdown.py`, and `c` has `m1/`, `m6/` and `m8/`.

1. Export the new commit to a clean folder of your own: `git -C F:\Spotter-AI\milemarker-api archive HEAD | tar -x -C <your folder>\repo`, under `...\scratchpad\qa5\`. Then run `uv sync` there.
2. Copy in the proof tests and scripts, and run them against the new code.
3. For each finding, state what the proof now shows:
   - **I1, I2 and M5** must now behave correctly. Expected: Dallas → Dallas, TX first; a refused trip repeated → 1 routing call; database down → 503 `stations_not_loaded` on both addresses.
   - **For the other eight**, behaviour is unchanged by decision. Show that the documents now state what the code does, quoting the document line and the code line that makes it true.

Some proof scripts print results rather than assert them. Read their output.

## 2. Adversarial review of the diff

Read every changed line (`git diff b3d3bef..HEAD`). Look hardest at these:

- **I2 (`trips/services/planner.py`).**
  - Is a cached refusal byte-for-byte the same answer as the first one, including the `RouteLeavesUSA` message, which formats the unrounded miles, and its rounded detail?
  - Can anything transient end up cached as a refusal?
  - Is the value safe to pickle and unpickle through Redis? Prove this against a real Redis: database 13 only, delete your keys afterwards, and never touch databases 0, 1, 14 or 15.
  - Does `meta`/`routing_calls` stay right?
  - Is `CACHE_KEY_VERSION` 2 correct, and complete?
- **M5 (`stations/index.py`, `config/settings.py`).**
  - Is every `DatabaseError` path covered?
  - Does the lock still behave?
  - Is anything remembered that should not be?
  - Does the `connect_timeout` default merge correctly with a URL that has its own, and with one that has other options?
  - Is the start-up `warm_up` still right?
- **I1 (`stations/places.py`, `data/large_places.csv`, `scripts/extract_large_places.py`).**
  - Check the 50-city claim yourself, from the census file at `...\scratchpad\census\sub-est2023.csv`, not from `large_places.csv` alone.
  - Do the 12 hand mappings point to the right places?
  - Are the 51 skipped places truly absent from `data/us_cities.csv`? Check a sample.
  - Is the cutoff of 0.7 sensible on your own list of 20 typos?
  - Measure the time of a no-state lookup yourself.
  - Can any input now raise something other than `UnknownPlace`/`OutsideCoverage` (a KeyError, for example)?
- **Tests.** Does each new test fail on `v2.0.0` and pass now? Prove at least I1, I2 and M5 by running the new tests against your old export (`git archive b3d3bef`). Are any tests weakened? Diff every changed assertion.
- **Documents.**
  - Is every changed sentence true of the code?
  - Is any old claim left anywhere outside `docs/plan/`?
  - Is `docs/openapi.yaml` in sync? Check with `uv run pytest tests/test_schema.py`.
  - Are the parked sections untouched?
  - Did the documents grow beyond what truth needs?

## Rules

- **Read-only** on `F:\Spotter-AI\milemarker-api`: no edits, and no git command that changes anything. Work in your own folder under `...\scratchpad\qa5\`.
- **Database for pytest:** `DATABASE_URL=postgresql://milemarker:milemarker@127.0.0.1:5432/milemarker_qa`.
- **Redis:** database 13 only, and only for the pickling proof. Never run `tests/test_cache.py` (it flushes database 15 and scans 0-14). Never run the full suite. The controller runs both.
- **No routing calls:** never make a request that can reach a public routing server. Use the recorded roads and the test fixtures, or `scripts/fake_osrm.py` on a port between 18200 and 18299.
- **The running API** on 127.0.0.1:8000 runs the OLD code until the controller rebuilds it, so do not use it.
- **No containers:** do not start, stop or remove any.
- **No subagents.**

## Report: `...\scratchpad\qa5\report.md`

The controller will copy it into `docs/plan/reports/phase15-QA.md`. Keep it under two pages.

- **Section 1:** one row per finding (I1, I2, M1-M9): what the proof shows now, and **proved** or **assumed**.
- **Section 2:** your findings, ranked Critical, Important, Minor or Note. Each one gives:
  - file:line
  - what is wrong
  - a concrete failure scenario
  - **proved** (with the command and output) or **plausible**
  - the fix you suggest
- **Section 3:** what you could not check, and why.

Reply with only: the count per severity, the one-line title of each Critical or Important finding, and whether every proof in section 1 holds.
