# Mile Marker API: Product Requirements

## 1. Summary

Mile Marker API takes a start and a finish inside the USA and returns the driving route, the fuel stops along it, and the cost of the fuel. It is for truck drivers and dispatchers, and it runs as a small Django service from a fresh clone.

## 2. Problem

Truck stop prices range from $2.69 to $6.40 a gallon in the supplied file, and a truck can go only 500 miles on a tank. Where a long trip refuels changes the bill. Coverage is uneven: California has 8 stations, none on Interstate 5, so Los Angeles to Seattle has no valid plan.

## 3. Users and what they need

- **Driver or dispatcher:** a route, the stops with price and gallons, and a total they can check by hand. When no plan exists, a clear reason.
- **Operator:** loads the station data once and sees what was kept and dropped.
- **Reviewer:** starts the project with one command and no API key.

## 4. Goals

- Plan the cheapest fuel purchase with no stretch over 500 miles (FR-6, FR-7, NFR-6).
- Report route, stops and total cost so every figure can be reproduced (FR-3, FR-5, FR-8, FR-9).
- Return a map any GeoJSON viewer can draw (FR-4).
- Fail clearly on bad input and impossible trips (FR-2, FR-10, FR-11).
- Stay fast with few outside calls (NFR-1 to NFR-3).
- Run free from a clone (NFR-5, NFR-9, NFR-10).

## 5. Non-goals

Accounts or keys, trips with more than two points, comparing routes, live prices, station data from outside the CSV, street addresses and ZIP codes, places outside the lower 48 states and DC, per-request range or fuel economy, and a frontend.

## 6. Scope

**First release:** every need (FR-1 to FR-11, NFR-1 to NFR-10), then the wants (FR-12 to FR-16, NFR-11 to NFR-16).

**Later:** FR-17 to FR-19, NFR-17, NFR-18.

Settled choices are in the decisions table of `requirements.md`.

## 7. How it behaves

A caller sends `GET /api/v1/route/?start=New York, NY&finish=Los Angeles, CA`. The API looks both places up offline and rejects bad ones before any routing call. It makes one call to a free routing service, finds stations within 5 miles of the road, and chooses where to buy fuel.

The response holds a summary, stops, warnings, assumptions, a GeoJSON map and call details. Stop 1 is the fuel bought before leaving, priced at the listed station nearest the start.

Each stop is charged $10 while the plan is chosen, standing for the time it takes. Without it the cheapest plan makes 17 stops, one for 0.6 gallons. The $10 is never added to the fuel bill, and the caller can change it with `stop_cost`.

## 8. Success measures

- Our own work adds at most 100 ms to the routing response time (NFR-1).
- One routing call per new route, never more than two. Repeats, and the same trip with another stop cost, make none (NFR-2).
- A repeated request answers in under 50 ms (NFR-11).
- Cost matches two independent exact methods in tests (NFR-6). Gallons equal distance divided by 10, and the total equals the sum of stop costs.
- New York to Los Angeles uses fewer than 10 stops.

## 9. Release criteria

Done means the ten acceptance checks in `requirements.md` section 9 pass. They cover a correct, cached New York to Los Angeles plan; short trips; Los Angeles starts; the four rejected trips; the map; the fuel tests; one-command start; and submission before Friday 20 Nov 2026, 8 pm.

## 10. Risks and known limits

| Limit | What is done |
|---|---|
| City-centre station positions, median 2.8 miles off, no range reserve | 5-mile radius; stated in README |
| Some roads have no fuel listed | `no_fuel_plan` error; no invented stop |
| Car routing, not truck routing | Stated; openrouteservice is the first later addition |
| Free routing servers, no uptime promise | Second server; clear error within 10 seconds |
| Cache is per process | One process with threads; shared cache is a nice-to-have |
| Coarse border outlines | 25-mile abroad limit against 10 measured |
| Docker needed for PostgreSQL | One Compose command |
| Map not yet checked in geojson.io | Check on a coast-to-coast trip |

## 11. Related documents

`requirements.md`, `backend-architecture.md`, `use-cases.md`, `test-cases.md`.
