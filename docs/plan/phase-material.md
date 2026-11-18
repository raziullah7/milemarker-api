## Appendix B: material already worked out, for the phase files

This is not part of `PLAN.md`. It moves into the phase files and into `docs/test-cases.md`, and is kept here so it is not lost.

### Interfaces (Phase 2)

```python
# stations/exceptions.py   plain exceptions: code, message, details. No HTTP status.
MileMarkerError; UnknownPlace(field, query, suggestions); OutsideCoverage(field, query); StationsNotLoaded
# trips/exceptions.py
InvalidRequest; NoRoute; RouteLeavesUSA(miles_abroad); NoFuelPlan(gap_start_mile, gap_miles); RoutingUnavailable(reason)

# stations/sphere.py  (pure)
haversine_miles(lat1, lng1, lat2, lng2); to_xyz(lat, lng) -> ndarray; chord(miles) -> float; arc(chord) -> miles
# stations/types.py   (pure)
StationInfo(opis_id: int, name, address, city, state, price: Decimal)
StationIndex(lat, lng, price: ndarray, xyz: ndarray, info: list[StationInfo])
# stations/places.py
Place(label: str, lat: float, lng: float)
resolve(text: str, field: str) -> Place
locate_city(city: str, state: str) -> tuple[float, float] | None
# stations/index.py
get_index() -> StationIndex;  reset_index() -> None;  nearest_station(index, lat, lng) -> tuple[int, float]

# trips/services/routing.py
Route(coords: ndarray [N, 2] of [lng, lat], distance_miles: float, server: str, calls: int)
fetch_route(start: tuple[float, float], finish: tuple[float, float], *, client: httpx.Client | None = None) -> Route
# trips/services/geo.py  (pure)
RoadPoints(lat, lng, marker: ndarray)                    # marker[0] == 0, marker[-1] == total exactly
resample(coords, total_miles: float, step_miles: float = 0.5) -> RoadPoints
load_borders(path) -> dict[str, ndarray]
longest_run_abroad(points: RoadPoints, borders, sample_every_miles: float = 2.0) -> float
# trips/services/corridor.py  (pure)
Candidate(mile: float, price: float, station: int, off_route_miles: float, point: int)
stations_along(points, index, radius_miles=5.0, thin_miles=10.0, exclude: int | None = None) -> list[Candidate]
# trips/services/fuel.py  (pure)
Purchase(index: int, gallons: float)                    # index 0 is the start
find_gap(miles, total_miles) -> tuple[float, float] | None   # (mile where the first stretch over 500 starts, its length)
plan_stops(miles, prices, total_miles, stop_cost) -> list[Purchase]
cheapest_fuel(miles, prices, total_miles) -> list[Purchase]      # greedy, stops free
# trips/services/answer.py  (pure)       build_answer(...) -> dict
# trips/services/planner.py              plan_trip(start_text, finish_text, stop_cost: Decimal) -> dict
# trips/errors.py                        exception handler: code -> status, one error body
```

### Hand-worked fuel cases (Phase 3), checked against the research algorithm

| miles | prices | total | stop cost | expected purchases | fuel cost |
|---|---|---|---|---|---|
| [0] | [3.00] | 300 | 0 | (0, 30) | 90.00 |
| [0] | [3.00] | 500 | 0 | (0, 50) | 150.00 |
| [0, 100] | [4.00, 3.00] | 400 | 0 | (0, 10), (1, 30) | 130.00 |
| [0, 300] | [3.00, 4.00] | 700 | 0 | (0, 50), (1, 20) | 230.00 |
| [0, 200] | [3.00, 5.00] | 450 | 0 | (0, 45) | 135.00 |
| [0, 250] | [3.00, 3.00] | 600 | 0 | gallons sum to 60 | 180.00 |
| [0, 10] | [3.10, 3.00] | 400 | 0 | (0, 1), (1, 39) | 120.10 |
| [0, 10] | [3.10, 3.00] | 400 | 3 | (0, 1), (1, 39) | 120.10 |
| [0, 10] | [3.10, 3.00] | 400 | 10 | (0, 40) | 124.00 |
| [0, 100, 100] | [4.00, 3.00, 3.50] | 400 | 0 | (0, 10), (1, 30) | 130.00 |
| [0, 495, 503] | [3.20, 3.10, 3.00] | 990 | 10 | (0, 49.5), (1, 49.5) | 311.85 |
| [0] | [3.00] | 501 | 0 | no plan, gap starts at mile 0 | |
| [0, 100] | [3.00, 3.00] | 700 | 0 | no plan, gap starts at mile 100 | |
| [0, 503] | [3.20, 3.00] | 990 | 10 | no plan, gap starts at mile 0 | |

Other fixed values: one degree of longitude on the equator is 69.094 miles; equator to pole is 6,218.47 miles.

### Live cases: input → expected output (Phase 1 doc, Phase 5 run)

Figures marked ≈ are research results; a pass is within 2%.

| ID | Input | Expected |
|---|---|---|
| P01 | `New York, NY` → `Los Angeles, CA` | 200; ≈ 2,801 miles; fewer than 10 stops (research: 7); total ≈ $866; 1 routing call |
| P02 | P01 again | 200; same summary; 0 routing calls; cache hit; 50 ms or less |
| P03 | P01 with `stop_cost=0` | 200; 0 routing calls; more stops than P01; total equals P01's lowest possible bill |
| P04 | P01 with `stop_cost=25` | 200; no more stops than P01; total not below P01's |
| P05 | `Los Angeles, CA` → `New York, NY` | 200; first fill distance over 100 miles (research: 121); a warning present |
| P06 | `Seattle, WA` → `Miami, FL` | 200; ≈ 3,301 miles; fewer than 12 stops |
| P07 | `Chicago, IL` → `Houston, TX` | 200; ≈ 1,087 miles |
| P08 | `Dallas, TX` → `Houston, TX` | 200; ≈ 238 miles; total above $0 |
| P09 | `Boston, MA` → `Washington, DC` | 200; ≈ 437 miles |
| P10 | `st. louis, mo` → `Winston-Salem, North Carolina` | 200; labels in the table's spelling |
| P11 | `Dallas TX` → `Phoenix, Arizona, USA` | 200 |
| P12 | `Fort Worth, TX` → `Dallas, TX` | 200; one stop at mile 0; about 3 gallons |
| N01 | no `finish` | 400 `invalid_request` |
| N02 | `start=` empty | 400 `invalid_request` |
| N03 | `Chicgo, IL` | 400 `unknown_place`; suggestions include `Chicago, IL` |
| N04 | `Chicago` | 400 `unknown_place`; suggestions include `Chicago, IL` |
| N05 | `Springfield, ZZ` | 400 `unknown_place` |
| N06 | `Honolulu, HI` | 422 `outside_coverage` |
| N07 | `Anchorage, AK` | 422 `outside_coverage` |
| N08 | `Toronto, ON` | 422 `outside_coverage` |
| N09 | the same place spelled two ways | 400 `invalid_request` |
| N10 | `stop_cost` of −1, 101, `abc`, `nan` | 400 `invalid_request` each |
| N11 | `Detroit, MI` → `Buffalo, NY` | 422 `route_leaves_usa` |
| N12 | `Los Angeles, CA` → `Seattle, WA` | 422 `no_fuel_plan`, gap starting at mile 0 |
| N13 | POST | 405, standard error body |
| N14 | an unknown path | 404, standard error body |
| N15 | rapid repeats of P01 until refused (run last) | 429 `rate_limited` by the 61st |

With fakes only: both routing servers failing (502), first failing and second answering (200, 2 calls), station table empty (503).

### Correctness rules the verifier checks on every 200 (Phase 5)

1. No stretch between fill-ups, or from the last one to the finish, is over 500 miles.
2. Walking the stops, fuel in the tank is never below 0 or above 50 gallons (0.05 allowed for rounding).
3. The stop gallons sum to `summary.gallons`, which equals distance ÷ 10 exactly.
4. The total equals the sum of the stop costs exactly, and each cost equals its gallons × its price rounded to cents.
5. Every stop's price is, digit for digit, the lowest the CSV lists for that station ID; name, city and state match that row.
6. Mile markers increase, start at 0 and stay below the distance. No station appears twice.
7. The lowest possible bill is not above the total; with `stop_cost=0` they are equal.
8. The map is valid GeoJSON: one line, one point per stop, a start and a finish, each stop point on the line.
9. `summary.stops` equals the number of stops, and `assumptions` carries the spec's constants.

### Use cases (Phase 1 doc)

| ID | Use case | Proven by |
|---|---|---|
| UC-01 | Plan fuel for a long trip | P01, P06 |
| UC-02 | Plan a trip shorter than one tank | P08, P12 |
| UC-03 | Compare the cheapest fuel bill with a plan of fewer stops | P03, P04 |
| UC-04 | Ask for the same trip again | P02 |
| UC-05 | Start where the CSV has no station nearby | P05 |
| UC-06 | Give places in everyday spellings | P10, P11 |
| UC-07 | Mistype a place and get suggestions | N03, N04, N05 |
| UC-08 | Ask for somewhere the API does not cover | N06, N07, N08 |
| UC-09 | Ask for a trip whose road leaves the USA | N11 |
| UC-10 | Ask for a trip with no fuel listed along the road | N12 |
| UC-11 | See the route and stops on a map | Phase 7 map check |
| UC-12 | The routing service fails | fakes |
| UC-13 | An operator loads the station data | loader tests |
| UC-14 | A reviewer runs the project from a fresh clone | Phase 8 |

### Postman collection (Phase 7)

One variable, `base_url`. Every request carries its own checks, so the collection is also an automated test.

| Folder | Requests | What it shows in the Loom |
|---|---|---|
| 1. Demo | P01, P02, P03, P04 | The plan, one routing call, the cache hit, cheapest versus fewer stops |
| 2. More trips | P05, P06, P08, P10, P11 | A far start station, the longest trip, a short trip, everyday spellings |
| 3. Errors | N01, N03, N06, N11, N12 | Clear messages for bad input, uncovered places, a road through Canada, no fuel on the road |

### Research prototypes to port from (never committed)

In `docs/plan/research/scripts/`: `s6_cities.py` (place names), `s4b_stops.py` (mile markers, station search, thinning), `s8_foreign.py` (border test), `s5_optimiser.py` (fuel plan and both exact checks). They are kept with the plan so each measurement in the specs can be re-run.
