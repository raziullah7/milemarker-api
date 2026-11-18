# Report 7P: the Postman collection

Status: done. File: `docs/postman/milemarker.postman_collection.json` (format v2.1.0, one variable `base_url` = `http://127.0.0.1:8000`, query parameters as separate `query` entries, collection description of four lines).

## Requests and checks

Every request: its description holds the case ID and one sentence on what to look at. Every 200 also runs these checks: status 200; `fuel_stops.length` below the case's stop limit and equal to `summary.stops`; `total_fuel_cost` equals the sum of the stops' `cost` in cents; `summary.gallons` within 0.006 of `distance_miles / 10`; `fuel_stops[0].kind` is `start`; `lowest_possible_fuel_cost` not above `total_fuel_cost`; `meta.routing_calls` 0 to 2, and `cache_hit` true implies 0 calls. Every error also checks the exact body shape (`error` with `code`, `message`, `details` only, message non-empty), the status and `error.code`. No response-time check anywhere.

**1. Demo**

| Request (case) | Case-specific checks |
|---|---|
| New York to Los Angeles: the full plan (P01) | distance, total, lowest possible bill, first fill-up each within 2% of 2800.7, 865.93, 854.65, 3.1; stops below 10; warnings `[]`; labels; saves `p01_total`, `p01_stops`, `p01_lowest` |
| Same trip again: answered from the cache (P02) | total and stops equal P01's; `routing_calls` 0; `cache_hit` true |
| Same trip, stops free (P03, `stop_cost=0`) | total equals `p01_lowest` to the cent and its own `lowest_possible_fuel_cost`; more stops than P01; `assumptions.stop_cost` 0; `routing_calls` 0 |
| Same trip, each stop costs $25 (P04, `stop_cost=25`) | stops no more than P01's; total not below P01's and within 2% of 884.79; `stop_cost` 25; `routing_calls` 0 |

**2. More trips**

| Request (case) | Case-specific checks |
|---|---|
| Los Angeles to New York (P05) | first fill-up above 100 and within 2% of 121; exactly one warning containing the first stop's name and the distance |
| Seattle to Miami (P06) | distance within 2% of 3301.2; stops below 12 |
| Dallas to Houston (P08) | distance within 2% of 238.1; total above 0 |
| st. louis, mo to Winston-Salem, North Carolina (P10) | labels `Saint Louis, MO`, `Winston Salem, NC` |
| Dallas TX to Phoenix, Arizona, USA (P11) | labels `Dallas, TX`, `Phoenix, AZ` |

**3. Errors**

| Request (case) | Case-specific checks |
|---|---|
| Missing finish (N01) | 400 `invalid_request`; `details.fields` has `finish` |
| Misspelt city (N03) | 400 `unknown_place`; field `start`, query `Chicgo, IL`; suggestions include `Chicago, IL`, at most 5 |
| Honolulu (N06) | 422 `outside_coverage`; field `start`, query `Honolulu, HI` |
| Detroit to Buffalo (N11) | 422 `route_leaves_usa`; `miles_abroad` within 2% of 252 |
| Los Angeles to Seattle (N12) | 422 `no_fuel_plan`; `gap_start_mile` 0; `gap_miles` within 2% of 886 |

## Design choices

- The checks on routing calls are relations, not the case table's literals. The brief says this API's cache already held these trips, and the collection must also pass on a second run within 24 hours. So P01 does not demand `routing_calls` 1 / `cache_hit` false (a warm cache gives 0 / true); it demands consistency. P03 and P04 demand `routing_calls` 0 only: P03's `cache_hit` false would turn true on a repeat run. P02 is strict (0 and true), as the brief says. A freshly started API still shows 1 / false on P01 in the demo; the collection just does not fail if it does not.
- Linked values are passed through `Number(...)`, since collection variables come back as strings.
- Map: the Leaflet script from the research report (Appendix 1) is on the four Demo requests, inside `try/catch` and guarded by `pm.visualizer` and `body.map` being present.

## Newman output

Free runs while writing: `--folder "1. Demo"` (4 requests, 46 assertions, 0 failed) and the three no-routing errors N01, N03, N06 selected by request name (3 requests, 13 assertions, 0 failed).

The one full run: `npx newman run docs/postman/milemarker.postman_collection.json --delay-request 1200`. Exit code 0. No second full run and no re-run was needed.

```
┌─────────────────────────┬────────────────────┬────────────────────┐
│                         │           executed │             failed │
├─────────────────────────┼────────────────────┼────────────────────┤
│              iterations │                  1 │                  0 │
├─────────────────────────┼────────────────────┼────────────────────┤
│                requests │                 14 │                  0 │
├─────────────────────────┼────────────────────┼────────────────────┤
│            test-scripts │                 14 │                  0 │
├─────────────────────────┼────────────────────┼────────────────────┤
│      prerequest-scripts │                  0 │                  0 │
├─────────────────────────┼────────────────────┼────────────────────┤
│              assertions │                111 │                  0 │
├─────────────────────────┴────────────────────┴────────────────────┤
│ total run duration: 22.3s                                         │
├───────────────────────────────────────────────────────────────────┤
│ total data received: 863.23kB (approx)                            │
├───────────────────────────────────────────────────────────────────┤
│ average response time: 295ms [min: 4ms, max: 1337ms, s.d.: 423ms] │
└───────────────────────────────────────────────────────────────────┘
```

The full run reached the public routing server for the uncached trips (P05, P06, P10, P11, N11, roughly 5 calls; P08 was cached).

## Not verified

- **The map was NOT seen in the Postman app.** Under Newman, the `pm.visualizer.set` call ran without error and did not break the run; whether Leaflet and the OpenStreetMap tiles load in the Postman Visualize tab (CSP, external script, 124 kB map payload) is unproven, as in the research report. The SVG fallback (report Appendix 2) is not included.
- The collection was not imported into the Postman app, so v2.1 import in the current app is unconfirmed (research report section A). The `$schema` URL and structure are what Newman 6.2.3 accepts.
- PM-01 says "against a freshly started API"; I ran against the already-warm API as instructed, so P01's first-call path (`routing_calls` 1, `cache_hit` false) was not exercised by this run.
