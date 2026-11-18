# Brief 13D: documents that are true of a backend-only submission

A Django API plans fuel stops for a road trip. It is a take-home submission for a backend role. Its documents were written before its code, and they also specify two things that will not be part of this submission: a map viewer (a React application) and an nginx front door. Both were parked. Your job is to make every document true of what is built, fill in the test results for what was built, and make three small related changes to code. You add no new feature and no new prose beyond what truth needs.

The repository root is the folder you were given; every path is relative to it.

## Rules

- **Your files:** `docs/requirements.md`, `docs/backend-architecture.md`, `docs/prd.md`, `docs/use-cases.md`, `docs/test-cases.md`, `docs/postman/milemarker.postman_collection.json`, `trips/schema.py`, `docs/openapi.yaml` (regenerated, never edited by hand), `tests/test_schema.py`, `.env.example`, and comments only in `config/settings.py`, `trips/middleware.py`, `docker-compose.yml` and `gunicorn.conf.py`. Your report: `docs/plan/reports/phase13-D.md`.
- **Not yours:** `README.md`, `Makefile`, `docs/development.md` (just rewritten; read them, they are the model for tone and length), everything under `docs/plan/` but your report, and all other code. If you believe one of those must change, say so in your reply.
- **The body and status of every answer the API gives do not change.** Only the OpenAPI document's description of one answer does (task 4).
- **Shorter, not longer.** Where a sentence is untrue, correct or cut it. Do not add explanations, history or new sections, with the one exception of the notices in task 1.
- Write plainly: full sentences, common words, no figures of speech. Follow the style of the documents as they are.
- No request to a public routing server. No container started or stopped: the database and Redis are running on `127.0.0.1`. No git command that changes anything. No other agents.

## Read first

- `docs/plan/PHASE-13.md`: what was decided and why, and the rulings.
- `README.md`, `Makefile`, `docs/development.md`: what a reader is now told. The Makefile has nine commands: `up`, `down`, `logs`, `test`, `lint`, `dev`, `offline`, `postman`, `clean`.
- `docs/plan/PHASE-11.md`, "Result" and the rulings sections: what was built, measured and ruled; and `docs/plan/reports/phase11-K.md`, `phase11-S.md`, `phase11-F.md` for which test cases were built and their results.
- The code as it is: `docker-compose.yml`, `docker-compose.e2e.yml`, `config/settings.py`, `gunicorn.conf.py`, `trips/`, `stations/`, `tests/`.

## What is built, and what is not

Built: the API on two gunicorn workers with Redis and a fallback; a one-off `setup` service; the `api` service published on `127.0.0.1:${API_PORT:-8000}`; `DJANGO_NUM_PROXIES` 0; the health, schema and docs addresses; host checking; request IDs made by the API (a client's is kept only if well formed); a rate limiter of our own; CI; the stand-in routing server; the Makefile's nine commands.

Not built, parked on the branch `viewer`: the viewer (`web/`), nginx, the `web` service and image, `BIND_ADDRESS`, compression, the content security policy, the `api_unavailable` answer, `make web-dev`, the browser tests, the web jobs in CI.

## Tasks

1. **Notices.** Where a document specifies the viewer or the front door, keep the specification and put one notice at the head of that section, in these words: "**Not part of this submission.** This section specifies work that is parked on the branch `viewer`. It is kept as that branch's specification." That means: architecture section 19 and "The front door" in section 18; the requirements, decisions and acceptance checks that are about the viewer or nginx (mark each such row, in whatever way fits the table, as parked); the use cases about the viewer; test-case sections 9.6, 9.9, 9.10 and 9.11, and single cases elsewhere that need nginx or the viewer (their Result is "Parked").
2. **Everything else made true.** Every sentence outside those sections that speaks as if nginx, the viewer, the `web` service or `BIND_ADDRESS` exists is corrected to what is built: the services table, the start order, the configuration table (`DJANGO_NUM_PROXIES` is 0 in the Compose file; the request ID is made by the API), the images, the commands table (the nine commands, with their plain equivalents), the folder layout of section 4 (no `docker/entrypoint.sh`; add what Phase 11 created), the diagrams, the tests table, "what production level means", the known limits (the cache is no longer per process; add the request line over 8,190 bytes answered by gunicorn in HTML), the one-page product description. Section 14's speed figures stay as measured, each named by its run; do not invent a figure.
3. **Test results.** In `docs/test-cases.md` section 9, fill in Actual and Result for every case that was built or run in Phases 10 and 11, from the reports and from the tests themselves (name the test). A case that was not run is "Not run", with the reason in a few words; never "Pass" without evidence. Add rows for the tests Phase 11's fix wave added (`tests/test_throttling.py` and the others its report lists), with IDs that continue their sections. Bring the counts and the summary at the head of the document up to date: 597 tests.
4. **The OpenAPI document.** It lists 503 `api_unavailable`, "sent by the proxy". There is no proxy in this submission: remove that code from the document (`trips/schema.py`), regenerate `docs/openapi.yaml` with `uv run python manage.py spectacular --file docs/openapi.yaml`, and bring `tests/test_schema.py` in line. 503 `stations_not_loaded` stays. Also the description of the response field `assumptions.stop_cost`, which spells out the default: take it from the settings, as the parameters do.
5. **Comments.** Where a comment in the four code files speaks of nginx as if it were there, say "a reverse proxy, if one is put in front" or cut it. `.env.example`: remove `BIND_ADDRESS`; say of `DJANGO_NUM_PROXIES` that it is 0 unless a proxy that overwrites `X-Forwarded-For` is put in front.
6. **The Postman collection.** Add a request for the health address and one for the schema address, each with assertions. Then the two findings ruled into this phase in `docs/plan/PHASE-9.md` ("Rulings on the audits", Q0a-01 and Q0a-14): read each ruling and do what it says, no more. Every request must still pass on the stand-in routing server; you cannot run it (no containers), so say in your report exactly what you changed, and the controller will run it.

## Prove it

`uv run pytest tests/test_schema.py tests/test_project.py` with `DATABASE_URL=postgresql://milemarker:milemarker@127.0.0.1:5432/milemarker_d`, then `uv run ruff check .`, `uv run ruff format --check .`, `uv run python manage.py spectacular --validate --fail-on-warn --file <a scratch file>`: clean. The collection is valid JSON. A search of the whole repository outside `docs/plan/` for `nginx`, `web/`, `viewer`, `BIND_ADDRESS`, `api_unavailable`, `web-dev` finds them only inside the sections marked as parked; list every other hit and why it stays. Run the test files once, at the end.

## Your report: `docs/plan/reports/phase13-D.md`

For each task: what you changed, file by file, in a few lines. The search's result. Every place where you were unsure whether something is built, and what you decided. Under a page and a half.

Reply to the controller with: status, the counts of the search, what you changed in the Postman collection, and any concern.
