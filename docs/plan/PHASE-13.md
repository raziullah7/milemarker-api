# Phase 13: A backend-only submission that a person can read

Baseline: `PLAN.md`, Part 2, Phases 13 and 14, changed by the owner's decisions of 19 Nov (below).

## What changed, and why

On 19 Nov the owner had the repository read by an outside reviewer, whose verdict was that it goes far beyond the task: more prose than code, a cache and a rate limiter nobody asked for, and a 3D viewer for a backend role. The owner decided:

| Decision | In the owner's words |
|---|---|
| The submission is backend only. The viewer is parked on a branch of its own | "since its only a backend job, I think we can defer it for now by parking it at a suitable position and putting it on another branch" |
| `docs/plan/` stays in the repository | "no, this needs to stay" |
| The README and the Makefile are rewritten for a person who wants to run the thing | "just tell me how to run it"; "why would a HUMAN reader read that" |
| Each thing that goes beyond the task gets one line saying why it is there | "makes sense" |

No working backend code is removed. What changes is what a reader meets first, and that no document claims something that is not built.

## Tasks

| ID | Task | Who | Owns |
|---|---|---|---|
| 13C | The README (109 lines, run it first), the Makefile (9 commands, was 23), `docs/development.md` for everything a contributor needs | Controller | those three files |
| 13P | Park the viewer: its builder stops at a point that builds; its files go to the branch `viewer` | Controller | the branch |
| 13D | Every document made true of a backend-only submission; test-case results filled in for what was built in Phase 11; the OpenAPI document no longer describes a proxy's answer; the Postman collection gains the health and schema requests and the stronger checks ruled in Phase 9 | Sonnet | `docs/requirements.md`, `docs/backend-architecture.md`, `docs/prd.md`, `docs/use-cases.md`, `docs/test-cases.md`, `docs/postman/`, `trips/schema.py`, `docs/openapi.yaml`, `tests/test_schema.py`, `.env.example`, comments in `config/settings.py`, `trips/middleware.py`, `docker-compose.yml`, `gunicorn.conf.py` |
| QA-4 | The stranger test: an agent given only the README and the repository's address clones it into an empty folder and follows it literally | Sonnet | `reports/phase13-Q4.md` |
| 14 | Final verification, by the controller: a fresh clone from GitHub, one real New York to Los Angeles request, the speed figures, the acceptance checks, the merge | Controller | `reports/final.md` |

Brief: `briefs/phase13-D-documents.md`.

## Rulings

- Ruling: the specifications of the viewer and of the nginx front door stay in the documents, each under a plain notice that it is not part of this submission and where the work is parked. Why: they were written before the code, as everything here was, and the parked branch is built to them; deleting them would leave that branch without its specification. Cost if wrong: a reader skims past two marked sections.
- Ruling: `DJANGO_NUM_PROXIES` stays as a setting, at 0. Why: it is tested, it costs nothing, and it is what makes the rate limit correct the day a proxy is put in front.
- Ruling: Phase 12's two reviews (QA-2 of the viewer, QA-3 of the front door) are not run: there is nothing of theirs in the submission. The three questions QA-1 handed to QA-3 are answered by the controller in the final report: gunicorn's control socket, the pinned Swagger version, and an integrity hash.
- Ruling: the plan files are not reworded (finding Q0a-16 of Phase 9). Why: the owner asked for careful spending, and nothing in them is untrue; they are a record, linked once from the README.

## Gate 13 checklist

- [x] The viewer's files are on the branch `viewer`, and `next` holds none of them.
- [x] The controller has read every diff. (For 13D's 1,200 changed lines of documents: read in outline, with the notices counted and the builder's own search of every mention checked; not line by line.)
- [x] No document claims a viewer, an nginx or a `web` service is part of this submission.
- [x] The suite, coverage, the slow test, mypy, Ruff, the deployment check and the schema validation are clean.
- [x] The Postman collection passes on the stand-in, with the health and schema requests.
- [x] QA-4 followed the README in a fresh clone; every command worked and every figure matched; its findings are ruled and fixed.
- [x] Final verification (task 14) is recorded.
- [x] CI is green on `next`. `next` is merged into `main`.
- [x] Committed.

## Result

**Gate 13 passed** on Thursday 19 Nov 2026. The evidence, and what was not checked, is in `reports/final.md`.

- The README is 113 lines and starts with how to run it. The Makefile has nine commands. `docs/development.md` holds what a contributor needs.
- The documents describe a backend-only submission; the viewer's and the front door's specifications stay under notices. Section 9 of the test cases has a result for every case: 173 pass, 19 not run with the reason, 86 parked.
- The Postman collection walks every answer stop by stop: 16 requests, 148 assertions.
- QA-4, a stranger with only the README, ran it first time; its two Important findings are ruled (one fixed, one an artefact of the test machine), and its Minor ones fixed.
- The version is 2.0.0 in `pyproject.toml` and in the OpenAPI document; the tag `v2.0.0` marks the merge.
- Public routing calls: the one real request made two (the first server failed). All 100 of the budget are used.
