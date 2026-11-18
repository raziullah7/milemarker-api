# Ledger: Mile Marker API build

Recovery map. After a context reset, trust this file and `git log` over memory.
Plan: `docs/plan/PLAN.md`. Phase files: `PHASE-N.md`. Raw material for later phases: `phase-material.md`.
Repo: this repository (commit identity must be `Razi Ullah <50240668+raziullah7@users.noreply.github.com>`).

## Rulings

- Ruling: per-task review is done by the controller reading the diff and running the tests; the independent Opus review runs once in Phase 5. Why: the approved plan says so. Cost if wrong: a fault survives until Phase 5.
- Ruling: Phase 3 runs four builders in parallel on disjoint files. Why: approved plan; file ownership is exclusive. Cost if wrong: a merge conflict, fixed by the controller.
- Ruling: agents never commit; the controller commits after each gate. Why: approved plan.

## Progress

- 2026-11-18 Phase 1 started. Project folder created, git initialised on `main`, docs moved in, research prototypes and cache copied to `plan/research/`.
- Phase 1 task 1.3 done: both specs rewritten with Appendix A (21 items) and PostgreSQL. NFR IDs renumbered (NFR-10 database, NFR-16 rate limit, NFR-18 shared cache).
- Phase 1 tasks 1.4, 1.5 done: `reports/phase1-cities-and-no-fuel.md` (22 cities with a named county; LA to Seattle confirmed no plan, gap 886 mi from mile 0).
- Phase 1 task 1.2 done (R2): `reports/phase1-R2-postman.md`. Newman 6.2.3 verified by a real run. Map inside Postman NOT verified; check geojson.io in the browser in Phase 7.
- Phase 1 task 1.7 done (R4): `docs/prd.md` reviewed by controller, accepted. Three wording fixes applied to requirements (check 1, check 5, D-5).
- Ruling: started Docker Desktop with `docker desktop start` instead of asking — the plan needs it, the user was told, and the CLI is the documented way. Engine 29.9.2 is up.
- Phase 1 task 1.1 done (R1): `reports/phase1-R1-stack.md`. Key facts: use `KDTree` not `cKDTree`; httpx `timeout=` is per phase, so a total deadline needs a streamed read against a clock; pytest-socket does not see psycopg; gunicorn runs only in Docker; PostgreSQL 18 images moved the data directory.
- 2026-11-18 The user ruled that ALL documents, the plan included, live in `docs/` inside the repository. The plan folder was moved from beside the project to `docs/plan/`. Machine paths and one personal name were removed from the plan files. Cached research data is git-ignored.
- Ruling reversed by the user: I began Phase 2 tasks 2.1 (uv project, dependencies) while R3 was still writing. The user said to take the time and put quality first. The one command already running is allowed to finish; nothing else in Phase 2 starts until Gate 1 has passed and Phase 1 is committed.
- Waiting on: R3 (use cases, test cases). Nothing committed yet.
