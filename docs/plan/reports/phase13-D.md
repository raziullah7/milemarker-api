# Report 13D: documents made true of a backend-only submission

Status: done, with the concerns at the end.

## What changed, by task

1. **Notices.** The notice sits at the head of architecture section 19 and "The front door"; requirements "The viewer"; use cases UC-21 to UC-28 and UC-31; test-case sections 9.6, 9.9, 9.10 and 9.11. Parked rows are marked in the Tier column (FR-18, FR-21 to FR-26, NFR-23, NFR-28, NFR-29; a new "Parked" tier is defined in section 3), in the answer of D-18, D-19 and D-24, in acceptance checks 18 and 19, in the use-case and traceability tables, and in the test data for the viewer.
2. **Everything else.**
   - Requirements: NFR-9, NFR-16, NFR-17, NFR-19, NFR-26, D-17 (now: reached directly, `DJANGO_NUM_PROXIES` 0), acceptance checks 11 and 17. PRD: scope, release criteria.
   - Architecture: flow diagram and its note, folder layout (no `docker/entrypoint.sh`; Phase 11's files added), the 503 row and the error notes, the 414 limit, the technology and "Beyond the suite" tables, services, start order, `DJANGO_NUM_PROXIES`, the request ID, images, the commands table (nine commands with plain equivalents), known limits.
   - Use cases: UC-14, UC-29, UC-30, UC-34 to UC-39 and the traceability tables.
   - Test cases: head status, section 8 rows, section 9 conventions and rows (CF-16, 18, 19, 21, 22, 24, 27, 33, CA-20, HS-14).
   - Section 14's figures are untouched.
3. **Test results.** Every section 9 table now has Actual and Result columns, 278 cases: 170 Pass, 19 Not run (reason given), 3 Fail, 86 Parked. A suite case names its test; a stack case names the phase and the run. 28 rows were added for Phase 11 tests (CF-38 to CF-43, CA-25 to CA-38, HS-20, HS-21, HM-11, HM-12), including all of `tests/test_throttling.py`. The head says 597 tests; `pytest --collect-only` agrees.
4. **OpenAPI.** `trips/schema.py` no longer has `api_unavailable` (error list, example, 503 description); `assumptions.stop_cost` takes its default from `settings.DEFAULT_STOP_COST`. `docs/openapi.yaml` regenerated. `tests/test_schema.py`: `PROXY_CODES` and the proxy assertions removed; it now asserts `api_unavailable` is absent.
5. **Comments.** `config/settings.py`, `docker-compose.yml`, `gunicorn.conf.py`, `trips/middleware.py`: nginx replaced by "a reverse proxy, if one is put in front". `.env.example`: `BIND_ADDRESS` removed; `DJANGO_NUM_PROXIES` is 0 unless a proxy that overwrites `X-Forwarded-For` is put in front.
6. **Postman.** See the reply; details below.

## The Postman collection

- A collection-level test script now checks every 200 from the route (Q0a-01): the walk along the stops (no leg or last leg over 500.1 miles, tank between -0.25 and 50.25 gallons, markers rising), each cost within half a cent of gallons times price, one map Point per stop at the stop's place.
- The same script holds the map template once and draws it with coloured circle markers (start and finish larger and underneath), fitted to the line plus the markers with padding 60 (Q0a-14). The template left the four Demo requests.
- P01's distance, total and lowest bill and P04's total are now within 0.5% of the recorded road's pinned values (2800.7, 867.29, 855.97, 886.19). The first-fill figure stays at 2%: I could not confirm its exact value.
- New folder "4. Health and schema": health (200, exactly status, stations 6626 and cache, X-Request-ID) and schema (asks for JSON; OpenAPI 3.0, route and health described, the route's seven statuses, no `api_unavailable`).
- The description no longer says `--delay-request 1200`. The scripts pass `node --check`; the collection is valid JSON; I did not run Newman. It now has 16 requests; 8 route, as before.

## The search

Outside `docs/plan/`, for `nginx`, `web/`, `viewer` (whole word), `BIND_ADDRESS`, `api_unavailable`, `web-dev`: 249 hits. 242 are in the five documents: 176 inside parked sections and 57 in rows marked parked, and 9 more that stay (below). Nothing in `docs/openapi.yaml`, `.env.example`, `Makefile`, `README.md`.

Hits that stay:
- `docs/requirements.md` FR-4 and check 7, `docs/prd.md` goal, `docs/use-cases.md` UC-11 (3 lines): "any GeoJSON viewer" means a third-party tool.
- `docs/test-cases.md` "Error bodies" row: data for the parked viewer cases; CF-29: says the image holds no `web/`, still true; HM-10: "with no nginx", true.
- `.dockerignore` comment on the viewer's packages; `tests/test_hosts.py` (2 comments), `tests/test_logs.py` (a comment and the ID `nginx.ID_42-x`): not my files. `docs/postman/...json`: the assertion that the document has no `api_unavailable`. `tests/test_schema.py`: the same assertion.

## Unsure, and what I decided

- **No network isolation exists.** The documents said the end-to-end API has "no route out". Only the stand-in is configured, so I wrote that; EE-06 is Not run.
- **Make targets.** Rows for removed targets are "Not run: target removed"; targets that survive keep their Phase 10 or 11 result with the phase named. Make is not on this machine's path, so none was run.
- **CI-07**: Phase 11 says CI was green on `next` and it was merged; `main`'s own run is not recorded. I put Pass with that said.
- **Stack cases built differently** (CF-18 to CF-33, CA-20): Pass where the built part was shown, with the difference in Actual.

## Concerns

- `tests/test_project.py` is not mine, but `BIND_ADDRESS` had to leave its list of variables (CF-16); I removed that one line.
- Three cases Fail: MK-19 (the README names no make target; `docs/development.md` does), RP-01 (there is no `LICENSE`, yet NFR-31 promises MIT), RP-02 (the README does not list D-1 to D-24). The controller decides whether to fix the files or the requirements.
- `.github/workflows/ci.yml` comment says the collection has "fourteen requests"; it has sixteen. Not mine.
- `config/settings.py`'s opening docstring says there are no templates; there is one. Not changed.
- Run once at the end: `tests/test_schema.py` and `tests/test_project.py` 63 passed; Ruff check and format clean; `spectacular --validate --fail-on-warn` clean and equal to the committed file.
