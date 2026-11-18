# Report 7R: README and architecture sections 4 and 14

Status: done. README word count 895 outside tables and code blocks (counted after removing fenced blocks and table rows).

## Where each figure comes from

| README / section 14 figure | Source |
|---|---|
| Wait for `Listening at: http://0.0.0.0:8000`, `Saved: 6626` | `docker compose logs api` of the running stack; `load_stations.py` lines 28-64 |
| `API_PORT`, `POSTGRES_PORT`, test profile command, `docker compose up -d db` | `docker-compose.yml` lines 1-9, 20, 29 |
| Run-from-source commands | `docker-compose.yml` header; `docker/entrypoint.sh` (migrate, load_stations); `docs/plan/PHASE-4.md` Result, "Carried into Phase 5" (runserver 127.0.0.1:8000 --noreload) |
| Example response: summary, warnings, assumptions, first two stops, meta | Real API, request 1 of 2 (default NY to LA). Cache was warm, so meta is a repeat (cache_hit true); README says so |
| 1 routing call and cache_hit false on a fresh start | `docs/plan/PHASE-4.md` Result, first live calls table |
| 19 stops at stop cost 0 | Real API, request 2 of 2 (`stop_cost=0`: stops 19, $855.95); also `docs/test-cases.md` P03 |
| 6,626 stations; 29,880 places | `docs/requirements.md` D-3, D-5; `data/README.md` |
| D-1 to D-15 table | `docs/requirements.md` lines 104-118 |
| Errors table | `docs/backend-architecture.md` section 11 (lines 383-396); 60 a minute from NFR-16 |
| Speed: new trip 19.5 ms own work | `docs/plan/PHASE-5.md` Result, Speed row |
| Repeat 1.1 ms own work | `docs/plan/PHASE-4.md` Result, first live calls table; real API just now: 1.2 ms |
| Repeat 23.6 ms round trip (limit 50) | `docs/plan/PHASE-5.md` Result, Speed row |
| Other stop cost 11.0 ms own work | `docs/plan/PHASE-4.md` Result, first live calls table |
| Other stop cost 31.7 ms round trip | `docs/plan/PHASE-5.md` Result, Speed row; `docs/test-cases.md` P03 |
| Routing call 2,646 ms | `docs/plan/PHASE-4.md` Result, first live calls table |
| Step timings in section 14 (1.9, 2.3, 1.8, 5, under 0.3, 230 to 340 ms) | `docs/plan/PHASE-3.md` Result, "Measured speed" |
| Limits 100 ms and 50 ms | NFR-1, NFR-11 |
| 348 tests, 1 slow | `uv run pytest --collect-only -q` (348/349, 1 deselected); `PHASE-5.md` and `PHASE-6.md` Results |
| 400 trips (LP), 250 trips (brute force) | `docs/test-cases.md` EX-01, EX-02 |
| 16 rules in verifier | `docs/test-cases.md` section 4 |
| Live run: 49 cases, 49 passed, 18 Nov 2026 | `docs/test-cases.md` section 3 header; `PHASE-5.md` Result |
| `docker compose --profile test run --rm test` | `docker-compose.yml` header |
| Newman command | `docs/test-cases.md` PM-01 |
| `live_check.py` usage | `scripts/live_check.py` docstring and argparse (`--base-url`, `--only`, `--markdown`) |
| Known limits | `docs/backend-architecture.md` section 16 |
| Median 2.8 miles; up to 10 miles abroad | section 16 |

## Not found or not done

- **Routing call time on a clean run:** only one live figure exists in the Result sections (2,646 ms, Phase 4). The earlier research range (600 to 1,700 ms) was dropped as the brief required. The catalogue's P01 round trip (2,023.7 ms) is a different run; not quoted.
- **Which machine:** no Result section names the hardware. The README and section 14 say "the development machine" and "run from source with runserver" (Phases 4 and 5 used runserver). Phase 3 step timings are build-time timings, not stated to be from the same server.
- **Own work for a new trip:** Phase 4 reported 19.4 ms, Phase 5 reported 19.5 ms. I used 19.5 (Phase 5, the controller's gate run).
- **Postman collection:** `docs/postman/milemarker.postman_collection.json` did not exist when I finished (writer 7P owns it). The README and section 4 name that path from brief 7P. I did not run Newman. No claim is made about Postman's Visualize tab.
- **Docker from a fresh clone:** not run by me (Phase 8). The commands are those in `docker-compose.yml`. The curl uses `%20` for spaces; I did not send it (only the two allowed requests were sent, both with `--data-urlencode`).
- **Clone URL:** `<this repository>` is a placeholder; the repository address is not in any file.

## Requests sent to the API

Two, both cached, 200: `New York, NY` to `Los Angeles, CA`, with and without `stop_cost=0`. No routing calls.

## Things outside my sections that are now out of date

- `docs/backend-architecture.md` line 6 still says figures come from research runs "and will be replaced"; sections 5 to 10, 16 still carry research figures (for example 17 stops and $854.65 in section 8). `docs/requirements.md` section 5 intro also says speed targets "will be replaced". Not touched, as they are not mine.
- Section 14 no longer holds the research figures "Read the routing response 25 ms" and "Build the response about 10 ms"; the finished API's whole-request own-work figures replace them.

## Edits made

- `README.md`: new, 13 sections in the brief's order.
- `docs/backend-architecture.md`: section 4 tree rewritten (added `docker/`, `.dockerignore`, `.python-version`, `stations/migrations/`, `types.py` now lists `Place`, `scripts/`, the `tests/` files and fixtures, `docs/` contents); section 14 table and measuring note replaced; border-check paragraph kept unchanged.
