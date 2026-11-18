# Final report: release 2

Thursday 19 Nov 2026. What is on `main`, what was checked, and what was not.

## What it is

The route-planning API of release 1, made fit to run as a service, and nothing else: the map viewer and the nginx front door planned for this release were parked on the branch `viewer` by the owner's decision (`PHASE-13.md`).

| Added in release 2 | Phase |
|---|---|
| CI on every push; a stand-in routing server with 21 recorded roads; a Makefile | 10 |
| Two workers on a shared Redis cache with a fallback; a one-off setup step; settings from the environment; host checking; a health address; request IDs and logs; a staged image | 11 |
| An OpenAPI document and a Swagger page | 11 |
| A rate limiter that counts atomically | 11 |
| A README of one page; a stronger Postman collection; a licence | 13 |

## What was checked, and by whom

| Check | Result | By |
|---|---|---|
| The suite | 597 passed, none skipped; coverage 98.47% (floor 98%) | Controller, and CI |
| Lint, format, types, deployment check, schema validation, the slow test | Clean | Controller, and CI |
| A fresh clone from GitHub, following the README only | Worked first time; every figure in the README matched the real answer | QA-4 |
| One real New York to Los Angeles request | 2,800.6 mi, $867.27, 7 stops; a repeat was a cache hit in 12 ms | QA-4 |
| The suite in a container, from that clone | 597 passed in 95.7 s | QA-4 |
| The Postman collection on recorded roads, from a cold cache | 16 requests, 148 assertions, none failed; 8 routing requests | Controller, and CI |
| Redis stopped under load | Every request 200; the first on each worker 0.46 to 0.50 s; back on Redis within 31 s | Controller; QA-1 with about 5,600 requests |
| A burst of 300 requests at once from one client | Exactly 60 answered | Controller |
| Independent reviews | QA-0a, QA-0b (the first release), QA-1 (the runtime, adversarial), 10R and 11R (re-reads of fixes), QA-4 (the README). No Critical finding in any; every Important one fixed and re-read | Agents that built none of what they reviewed |

Acceptance checks 11 to 16 and 20 of the requirements are met by the rows above; 17 to 19 are the viewer's and are parked.

## What was not checked, or is left as it is

- **The first public routing server failed on the one real request,** and the second answered. The API did what it is built to do, but the first new trip took 7.3 seconds. Nothing shows whether that server was down or slow at that moment.
- **Public routing calls: all 100 of the budget are used.** Every other check ran on recorded roads.
- **PM-01** (the Postman collection against a freshly started API on the public servers) and **M01** (the whole map pasted into geojson.io) stay partial, as recorded in the test cases. The collection passes from a cold cache on recorded roads; the full map was never pasted by hand.
- **A request line over 8,190 bytes** is answered by gunicorn in HTML, not in the API's JSON shape.
- **gunicorn 27 opens a control socket** in the app user's home inside the container. It cannot be reached from outside; it was not disabled.
- **Swagger UI is pinned at 5.17.14** and loaded from a CDN with no integrity hash. Whether a later release fixes a known fault was not checked.
- **CF-24, CF-27, CF-28 and EE-06** were not run: they need a deliberately broken database or a network with no route out.
- **The viewer's frame rate on real graphics** was never measured; the viewer is parked.

## Where things are

- `main`: this release. `v1.0.0`: the first release. `viewer` (local, not pushed): the parked viewer.
- `docs/plan/LEDGER.md`: every step, in order. `docs/plan/PHASE-9.md` to `PHASE-13.md`: each phase's rulings and result.
