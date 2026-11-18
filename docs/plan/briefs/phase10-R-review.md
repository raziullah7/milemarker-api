# Brief 10R: independent review of Phase 10's changes

Three builders have just changed this repository, and the person coordinating them has read their work. You built none of it and have not seen their reports' conclusions accepted or rejected. Review it as an adversary: assume a fault is there and look for it.

The repository root is the folder you were given; every path is relative to it. The changes are not committed yet: `git diff 004cbcc` shows the changed files and `git status --short` the new ones.

## Rules

- **Read-only in the repository.** Write only your report, `docs/plan/reports/phase10-R.md`. To test a suspicion, copy what you need to a scratch folder outside the repository and experiment there. No git command that changes anything. No other agents.
- **No request to a public routing server, and none to the running API.** Do not start, stop or rebuild containers.
- You may run the tests: `uv run pytest`, with the `DATABASE_URL` you were given so your test database is your own.

## Read first

- `docs/plan/PHASE-9.md`: the two tables under "Rulings on the audits", and the three "settled" sections. They say what was to be built and why.
- `docs/plan/reports/phase9-Q0b-changes.md`: the review whose findings the fixes answer.
- `docs/plan/briefs/phase10-A-harness.md`, `phase10-B-make-ci.md`, `phase10-C-fixes.md`: what each builder was asked for. Their own reports are `docs/plan/reports/phase10-A.md`, `-B.md`, `-C.md`; read them last, after you have formed your own view of the code.
- `docs/test-cases.md` section 4 (rules R1 to R17) and, in section 9, the SI, MK, CI, QB and VR cases.

## Scope

1. **The fixes (10C), first and deepest.**
   - `tests/verify.py` and `tests/test_verify.py`: the new rule R17, the changed R6, R12 and R15. R12 does not follow the ruling's formula: the builder found that formula failed nine correct real answers and replaced it with a bracket. Is the bracket sound? What is the largest shift of a stop along the line that it lets through, at the start, middle and end of a long road and on a short road? Can a wrong answer still pass all seventeen rules? Build some: a station in the right city but the wrong one of two cities with the same name in different states; a stop moved one, two and five points; a purchase of exactly 0.00; the stand-in's host name with and without the new option.
   - `trips/services/routing.py`: the new retry rule, and the lock on the shared client. Is there any answer for which the client now makes a second request where it must not, or stops where it must go on? Is a body saying "no road" with a status of 404 or 403 handled as the comments say?
   - `trips/services/answer.py`: the changed count. `stations/places.py`: the `Mexico, USA` rule; try other names it could now get wrong (`Canada, USA`, `New Mexico USA`, `Mexico MO`, `Mexico, MO, USA`).
   - `trips/services/fuel.py`, `stations/sphere.py`, `stations/exceptions.py`: annotations only were allowed. Did any behaviour change? The slow exactness test is the proof; run it.
   - The changed tests: does each new test fail without its fix? Prove it for R17, the retry rule and the count by reverting the fix in a scratch copy.
2. **The stand-in routing server (10A):** `scripts/fake_osrm.py`, `tests/test_fake_osrm.py`, `docker-compose.e2e.yml`, and the `ROUTING_SERVERS` lines of `config/settings.py`. Could it answer with the wrong recording (two recordings share a start city; some pairs are recorded in both directions)? Does it answer as the real server does in every case the client distinguishes? Is the request log safe under concurrent requests? Could a test in the suite pass while the stand-in is wrong?
3. **Makefile and CI (10B):** `Makefile`, `.github/workflows/ci.yml`, `.github/dependabot.yml`, `.pre-commit-config.yaml`. The workflow has never run. Read it as GitHub will: will each job start, find its tools, reach its services, and fail when it should? Is any step able to pass while the thing it checks is broken? Check the action versions and the service-container syntax against the projects' own documentation. Is anything in the Makefile not portable to `cmd.exe`?

## Your report: `docs/plan/reports/phase10-R.md`

- A findings table, most serious first: ID, severity (Critical, Important, Minor, Note), `file:line`, what is wrong, how you showed it, and the smallest fix.
- For scope item 1, a row per fix: sound or not, and whether you saw its test fail without it.
- What you checked and found sound, briefly. What you could not check, and why.

Reply to the controller with the count of findings by severity and one line for each Critical and Important.
