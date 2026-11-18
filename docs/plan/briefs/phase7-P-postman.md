# Brief 7P: the Postman collection

A finished API needs a Postman collection that does two jobs: its author will demonstrate the API from it in a five-minute recorded video, and it must run unattended as a test.

The repository root is the folder you were given; every path is relative to it.

## Rules

- **Your file only:** `docs/postman/milemarker.postman_collection.json`, and your report `docs/plan/reports/phase7-P.md`. Change nothing else. No git commands that change anything. No other agents.
- The API is running at `http://127.0.0.1:8000` (Docker). Do not restart it: its cache holds trips you can use for free.

## Read

- `docs/test-cases.md`: section 3 (the live cases, with the actual results of the last run) and section 7 rows PM-01 and PM-02
- `docs/backend-architecture.md` section 11 (the response and the error table)
- `docs/plan/reports/phase1-R2-postman.md`: the researched collection format, test-script syntax, a sample collection proved under Newman, and two scripts for drawing a map in Postman's Visualize tab (neither was verified in the Postman app)

## The collection

- Format v2.1.0. One collection variable, `base_url`, default `http://127.0.0.1:8000`.
- Query parameters as separate `query` entries, so `New York, NY` is encoded correctly.
- Three folders, in this order, with these requests in this order. Name each request by what it shows, not by its case ID, and put the case ID and one sentence on what to look at in the request's description.

| Folder | Requests (case IDs in `docs/test-cases.md`) |
|---|---|
| 1. Demo | P01, P02, P03, P04 |
| 2. More trips | P05, P06, P08, P10, P11 |
| 3. Errors | N01, N03, N06, N11, N12 |

- **Checks on every request**, as `pm.test` scripts: the status; for a 200, the fields the case names in section 3 and the invariants any plan must obey (fewer than the case's stop limit, `total_fuel_cost` equal to the sum of the stops' `cost` to the cent, `summary.gallons` equal to `distance_miles / 10`, `fuel_stops[0].kind` is `start`); for an error, `error.code` and the detail fields the case names.
- **Checks that link requests** use collection variables: P01 saves its total, its stop count and its `lowest_possible_fuel_cost`; P02 checks the same total with `routing_calls` 0 and `cache_hit` true; P03 checks its total equals P01's lowest possible bill and it has more stops; P04 checks it has no more stops than P01 and its total is not below P01's.
- Do **not** check response time: it depends on the machine and would make the demo fail for no reason.
- Figures that depend on today's roads (totals, distances) are checked as ranges or relations, never as exact numbers, so the collection still passes after the map data changes. Use the "pass within 2%" figures of section 3 where it gives them.
- **The map.** On the four Demo requests, add the Leaflet visualizer script from the research report, so the Visualize tab draws the route and stops. It must not break the run under Newman: guard it, and prove it with the run below. Say plainly in your report that it was not seen in the Postman app.
- The collection's own description says, in three or four lines, what the API does, that `base_url` is the one variable, and that the requests are meant to be run in order.

## Prove it

Requests that reach the public routing server are limited, so:

1. While writing, run only what is free: `npx newman run <file> --folder "1. Demo"` (those trips are cached) and the three errors that make no routing call (N01, N03, N06) if you split them out temporarily.
2. Then **one** full run: `npx newman run docs/postman/milemarker.postman_collection.json --delay-request 1200`. It must exit 0 with every check passing. Paste its summary table into your report.
3. Do not make a second full run. If the one run shows a failing check, fix it, re-run only the folder that failed, and say so.

## Your report: `docs/plan/reports/phase7-P.md`

The requests and the checks on each, the Newman output, and anything you are unsure of.

Reply to the controller with: status, Newman's totals (requests, assertions, failures), and any concern.
