# Mile Marker API: Test Cases

How the API is tested, case by case. Every case states its input and its expected output.

Requirement IDs (FR, NFR, D) refer to `requirements.md`. Use-case IDs (UC) refer to `use-cases.md`. Field names, error codes and status codes are those of `backend-architecture.md`, section 11.

Conventions:

- Query strings are shown unencoded for readability.
- "≈ value, pass within 2%" marks a figure measured on real roads while the API was designed. The finished API places a few cities and mile markers slightly differently, so a result within 2% of the figure passes.
- Prices, gallons and money are compared as exact decimals, not floating point, unless a tolerance is given.
- "Mile 100" is a distance along the road from the start. A station "4.9 mi N" lies 4.9 miles north of the road.

## 1. How the tests are organised

| Level | What it proves | How it is run |
|---|---|---|
| Unit | Each pure module (places, sphere, geo, corridor, fuel, answer) and the routing client does what the architecture says | `uv run pytest`; no database, no network |
| Exactness | The fuel plan is the true optimum, checked against two exact methods that share no code with it | `uv run pytest` (cases EX) |
| Integration | The loader, the in-memory index and the endpoint work with PostgreSQL and a fake routing service: response shape, caches, every error code | `uv run pytest`, with the Compose database running |
| Independent verification | Every successful response obeys the correctness rules of section 4. The verifier is written from the documents and imports nothing from the API | Inside the endpoint tests, and by `scripts/live_check.py` on every live 200 |
| Live | The running API gives the right answers on real roads from the real routing service | `scripts/live_check.py` against a running server (section 3) |
| In the container | The same holds when Docker Compose starts the API and PostgreSQL | `scripts/live_check.py` against the Compose stack (section 7) |
| Postman collection | The committed collection's own checks pass | Newman, from the command line (section 7) |
| Fresh clone | A reviewer can run everything from an empty folder, with no account and no key | By hand, steps FC (section 7) |

No automated test reaches beyond the local machine (NFR-13). A test fixture blocks every connection except the one to the local database (PJ-03).

## 2. Automated test catalogue

### 2.1 Test data

| Name | What it is |
|---|---|
| Places table | The real `data/us_cities.csv`. Coordinates quoted below are its rows. |
| Small CSV | Seven rows in the fuel CSV's format, listed below. |
| Real CSV | The supplied fuel CSV in `data/`. |
| Equator road | `RoadPoints` built directly: 2,001 points along the equator from longitude 0, one every 0.5 miles, with markers exactly 0, 0.5, … 1,000. A point at mile `m` has longitude `m ÷ 69.094094`. A station at "mile `m`, `d` mi N" has latitude `d ÷ 69.094094` and longitude `m ÷ 69.094094`. |
| Test road | A straight road along latitude 35° N, eastward from longitude 110° W, of the length a case names. The fake routing service returns it with `distance` equal to that length. Stations are created on it at the miles a case names. |
| Recorded roads | Real routing responses saved once as test data: New York–Los Angeles, Detroit–Buffalo, Detroit–Boston, and the fifteen roads of GE-16. |
| Fake routing service | An `httpx` fake transport that returns a chosen answer, failure or delay, and counts the calls made. |

Small CSV (Address and Rack ID hold any value):

| Row | OPIS Truckstop ID | Truckstop Name | City | State | Retail Price |
|---|---|---|---|---|---|
| 1 | 1 | ALPHA | `  Dallas  ` | TX | 3.50000000 |
| 2 | 1 | ALPHA TWO | Dallas | TX | 3.40000000 |
| 3 | 2 | BRAVO | Fort Worth | TX | 3.20000000 |
| 4 | 2 | BRAVO TWO | Fort Worth | TX | 3.20000000 |
| 5 | 3 | CHARLIE | Toronto | ON | 3.00000000 |
| 6 | 4 | DELTA | Henrico | VA | 3.00733333 |
| 7 | 5 | ECHO | St. Louis | MO | 3.10000000 |

### 2.2 Places: `stations/places.py`

| ID | UC | Input | Expected |
|---|---|---|---|
| PL-01 | UC-06 | `resolve()` on each of 58 names: New York, NY; Los Angeles, CA; Chicago, IL; Houston, TX; Phoenix, AZ; Philadelphia, PA; San Antonio, TX; San Diego, CA; Dallas, TX; San Jose, CA; Austin, TX; Jacksonville, FL; Fort Worth, TX; Columbus, OH; Charlotte, NC; San Francisco, CA; Indianapolis, IN; Seattle, WA; Denver, CO; Washington, DC; Boston, MA; El Paso, TX; Nashville, TN; Detroit, MI; Oklahoma City, OK; Portland, OR; Las Vegas, NV; Memphis, TN; Louisville, KY; Baltimore, MD; Milwaukee, WI; Albuquerque, NM; Tucson, AZ; Fresno, CA; Sacramento, CA; Kansas City, MO; Atlanta, GA; Miami, FL; Raleigh, NC; Omaha, NE; Minneapolis, MN; New Orleans, LA; Cleveland, OH; Tampa, FL; St. Louis, MO; Pittsburgh, PA; Cincinnati, OH; Salt Lake City, UT; Buffalo, NY; Boise, ID; Winston-Salem, NC; Coeur d'Alene, ID; St. Paul, MN; Ft. Lauderdale, FL; Mt. Pleasant, SC; O'Fallon, MO; Wilkes-Barre, PA; McAllen, TX | Each returns a `Place`; none raises |
| PL-02 | UC-06 | `St. Louis, MO`; `Winston-Salem, NC`; `Coeur d'Alene, ID`; `St. Paul, MN`; `Ft. Lauderdale, FL`; `Mt. Pleasant, SC`; `O'Fallon, MO`; `Wilkes-Barre, PA`; `McAllen, TX` | Labels in the table's spelling, in the same order: `Saint Louis, MO`; `Winston Salem, NC`; `Coeur D Alene, ID`; `Saint Paul, MN`; `Fort Lauderdale, FL`; `Mount Pleasant, SC`; `O Fallon, MO`; `Wilkes Barre, PA`; `Mcallen, TX` |
| PL-03 | UC-06 | `Dallas, TX`; `Dallas TX`; `Dallas, Texas`; `Dallas, TX, USA`; `dallas tx`; `DALLAS,TX`; `  Dallas ,  TX  `; `Dallas TX US`; `Dallas, Texas, United States` | Each: label `Dallas, TX`, lat 32.790439, lng −96.80439 |
| PL-04 | UC-06 | `Washington, D.C.`; `Washington DC`; `washington, district of columbia` | Each: label `Washington, DC`, lat 38.912217, lng −77.017691 |
| PL-05 | UC-06 | `New York City, NY`; `NYC, NY`; `Manhattan, NY`; `new york ny`; `New York, New York` | Each: label `New York, NY`, lat 40.74838, lng −73.996705 |
| PL-06 | UC-06 | `Manhattan, KS` | Label `Manhattan, KS`, lat 39.193757, lng −96.585776 (the New York alias does not apply in Kansas) |
| PL-07 | UC-06 | `Sault Ste. Marie, MI`; `Sault Ste Marie MI` | Each: label `Sault Sainte Marie, MI` |
| PL-08 | UC-06 | `Santa Fe New Mexico`; `Santa Fe, New Mexico`; `santa fe nm` | Each: label `Santa Fe, NM`, lat 35.702472, lng −105.974818; not outside coverage |
| PL-09 | UC-06 | `Ft Worth, TX`; `Ft. Worth TX`; `fort worth, texas` | Each: label `Fort Worth, TX`, lat 32.7469, lng −97.3268 |
| PL-10 | UC-13 | `Saint Louis, MO` (two rows, 7.2 miles apart) | lat 38.638595, lng −90.257751 (mean of the two rows), within 0.000001 |
| PL-11 | UC-13 | `Orlando, FL`; `Saint Paul, MN`; `Houston, TX`; `San Francisco, CA`; `Dallas, TX` | The named county's row, not the mean: (28.539882, −81.372668); (44.969963, −93.083167); (29.7652, −95.3657); (37.775, −122.4183); (32.790439, −96.80439) |
| PL-12 | UC-13 | Every city and state in the places table with more than one row: largest distance between its rows | Exactly 22 exceed 10 miles, and each resolves to its named county's row: Orlando FL (Orange), Austin TX (Travis), Philadelphia PA (Philadelphia), Jacksonville FL (Duval), Greenville SC (Greenville), San Antonio TX (Bexar), Saint Paul MN (Ramsey), Omaha NE (Douglas), North Charleston SC (Charleston), Fort Washington PA (Montgomery), Trenton NJ (Mercer), Dallas TX (Dallas), Cincinnati OH (Hamilton), Charleston SC (Charleston), Houston TX (Harris), Kissimmee FL (Osceola), Denver CO (Denver), Wewahitchka FL (Gulf), Indianapolis IN (Marion), San Francisco CA (San Francisco), Littleton CO (Arapahoe), Tampa FL (Hillsborough) |
| PL-13 | UC-13 | `Port Wentworth, GA`; `Henrico, VA`; `Evergreen, AL`; `Elizabethport, NJ`; `University Park, IL`; then `Henrico, NC` | The five hand-added places resolve with those labels. `Henrico, NC` still resolves to the table's row (36.527409, −77.854625) |
| PL-14 | UC-13 | `locate_city("ST LOUIS", "MO")`; `locate_city("Fort Worth", "TX")`; `locate_city("Henrico", "VA")`; `locate_city("Nowhereville", "TX")` | (38.638595, −90.257751); (32.7469, −97.3268); the hand-added Henrico position; `None` |
| PL-15 | UC-08 | `Honolulu, HI`; `Anchorage, AK`; `Juneau, Alaska`; `San Juan, PR`; `Toronto, ON`; `Vancouver, BC`; `Montreal, Canada`; `Tijuana, Mexico` | Each raises `OutsideCoverage` with the field passed in and the query as given |
| PL-16 | UC-07 | `Chicgo, IL` | `UnknownPlace`; suggestions contain `Chicago, IL`; 1 to 5 suggestions, all ending `, IL` |
| PL-17 | UC-07 | `Chicago` | `UnknownPlace`; suggestions exactly `["Chicago, IL"]` (no other state has a Chicago) |
| PL-18 | UC-07 | `Springfield` | `UnknownPlace`; exactly 5 suggestions, each `Springfield, ST`, five different states |
| PL-19 | UC-07 | `Springfield, ZZ` | `UnknownPlace`; at most 5 suggestions |
| PL-20 | UC-07 | `75201`; `1600 Pennsylvania Ave, Washington, DC` | `UnknownPlace` each: ZIP codes and street addresses are not accepted (D-3) |
| PL-21 | UC-07 | `resolve("Chicgo, IL", field="finish")` | The error's field is `finish` and its query `Chicgo, IL` |

### 2.3 Loader and index: `load_stations`, `stations/index.py`

These tests need the database.

| ID | UC | Input | Expected |
|---|---|---|---|
| LD-01 | UC-13 | `load_stations --csv <small CSV>` | Exit 0. Prints: 7 rows read, 5 stations, 4 in the lower 48 and DC, 3 placed from the table, 1 from a hand-added place, 4 saved |
| LD-02 | UC-13 | Station 1 after LD-01 (listed at 3.50 and 3.40) | price 3.40000000; name `ALPHA TWO` (the cheapest listing) |
| LD-03 | UC-13 | Station 2 after LD-01 (two listings at 3.20) | name `BRAVO` (the first row on a price tie) |
| LD-04 | UC-13 | Station 1's city (padded in row 1) | `Dallas`, no spaces |
| LD-05 | UC-13 | Station 3 (Toronto, ON) | Not saved |
| LD-06 | UC-13 | Station 4's price | `Decimal("3.00733333")`, every digit kept |
| LD-07 | UC-13 | Positions of stations 1 and 5 | Station 1 at (32.790439, −96.80439); station 5 at (38.638595, −90.257751) |
| LD-08 | UC-13 | Small CSV plus a row for station 6, FOXTROT, in Nowhereville, TX, loaded over the LD-01 table | Command fails with an error; output names station 6 and `Nowhereville, TX`; the table still holds the 4 stations of LD-01 |
| LD-09 | UC-13 | `load_stations --csv <small CSV>` run twice | 4 rows, not 8 |
| LD-10 | UC-13 | `--csv` and `--cities` pointing at copies in a temporary folder | The copies are read, not the files in `data/` |
| LD-11 | UC-13 | `load_stations` on the real CSV | Prints 8,151 rows; 6,738 stations; 6,626 in the lower 48 and DC; 6,615 placed from the table; 11 from hand-added places; 6,626 saved. The 112 dropped stations are in exactly nine Canadian province codes |
| LD-12 | UC-13 | The real CSV, read directly | 678 station IDs listed more than once; 597 of them at more than one price; 1,256 rows whose city has leading or trailing spaces |
| LD-13 | UC-13 | `get_index()` after LD-01 | 4 stations in station-ID order 1, 2, 4, 5; `info[k].price` exact decimals 3.40000000, 3.20000000, 3.00733333, 3.10000000 |
| LD-14 | UC-13 | `get_index()` called twice | The same object both times; the second call makes no database query |
| LD-15 | UC-13 | `get_index()` on an empty table; then LD-01; then `get_index()` | First raises `StationsNotLoaded`. After loading, returns 4 stations without `reset_index()` |
| LD-16 | UC-13 | `nearest_station(index, 32.7469, −97.3268)`; `nearest_station(index, 33.224629, −96.80439)` (30 miles north of Dallas) | Station 2 at 0.0 miles; station 1 at 30.0 miles (±0.05) |
| LD-17 | UC-13 | LD-01 plus station 7 at Dallas, price 3.30; `nearest_station` at the Dallas position. Then station 7 at 3.40, equal to station 1 | First: station 7 (cheaper of two at the same position). Then: station 1 (lower station ID on equal price) |
| LD-18 | UC-05 | Real CSV loaded; `nearest_station` at `Los Angeles, CA` and at `New York, NY` | ≈ 121 miles, pass within 2%; ≈ 3.1 miles, pass within 2% |

### 2.4 Geometry: `stations/sphere.py`, `trips/services/geo.py`

| ID | UC | Input | Expected |
|---|---|---|---|
| GE-01 | UC-01 | `haversine_miles(0, 0, 0, 1)` | 69.094 (±0.001): one degree of longitude on the equator |
| GE-02 | UC-01 | `haversine_miles(0, 0, 90, 0)` | 6,218.47 (±0.01): equator to pole |
| GE-03 | UC-01 | `haversine_miles` from a point to itself | 0.0 |
| GE-04 | UC-01 | `to_xyz` of (0, 0), (90, 0), (40.74838, −73.996705), (33.973093, −118.247896) | Each vector has length 1 (±1e-12). The straight-line distance between the New York and Los Angeles vectors equals `chord(haversine_miles(NY, LA))` (±1e-12) |
| GE-05 | UC-01 | `arc(chord(m))` for m = 0, 0.5, 5, 500, 3,000; `chord(12,436.94)` | Returns m (±1e-9 miles); 2.0 (±1e-6) |
| GE-06 | UC-01 | `resample([[0, 0], [1, 0]], 69.1)` (coordinates `[lng, lat]`) | 140 points; first (lat 0, lng 0), last (lat 0, lng 1); `marker[0]` = 0; `marker[-1]` = 69.1 exactly; markers strictly increasing |
| GE-07 | UC-01 | `resample([[0, 0], [0.5, 0], [0.5, 0], [1, 0]], 69.1)` (a repeated point) | Same points and markers as GE-06 (±1e-9); no error |
| GE-08 | UC-01 | `resample([[0, 0], [1, 0], [1, 1]], 138.2)` | 278 points; `marker[-1]` = 138.2 exactly; every point lies on one of the two segments (±1e-9 degrees) |
| GE-09 | UC-01 | Recorded New York–Los Angeles road, total 2,800.7 | 5,594 points (±1); `marker[-1]` = 2,800.7 exactly; our own length within 0.2% of 2,800.7 |
| GE-10 | UC-09 | Border box "Canada" 45–46° N, 80–79° W; road due north along 79.5° W from 44° N to 47° N | `longest_run_abroad` 69.1 miles, pass within 4 miles (two samples) |
| GE-11 | UC-09 | Two boxes on that road, 45.0–45.2° N and 45.5–45.7° N | 13.8 miles, pass within 4: the longest single run, not the sum of 27.6 |
| GE-12 | UC-09 | Box 35–36° N, 80–79° W; road along 79.5° W from 34° N to 37° N | 0.0: latitudes between 32.8° N and 41.6° N are not sampled |
| GE-13 | UC-09 | Border box "Mexico" 30–31° N, 106–105° W; road along 105.5° W from 29° N to 32° N | 69.1 miles, pass within 4 |
| GE-14 | UC-09 | Recorded Detroit–Buffalo road, real borders | ≈ 252 miles, pass within 2% |
| GE-15 | UC-09 | Recorded Detroit–Boston road, real borders | ≈ 234 miles, pass within 2% |
| GE-16 | UC-09 | Recorded roads that stay in the USA: Boston–Washington, Boston–Seattle, Chicago–Houston, Dallas–Houston, Detroit–Port Huron, El Paso–Del Rio, Houlton–Madawaska, International Falls–Baudette, Key West–Miami, Laredo–Brownsville, Montauk–New York, New York–Los Angeles, San Diego–Calexico, Seattle–Miami, Seattle–Blaine | Each 25 miles or less, so none is rejected (measured in design: 10 at most) |
| GE-17 | UC-09 | `load_borders("data/borders.json")` | Two entries, `CAN` and `MEX`, each one outline of `[lng, lat]` points |

### 2.5 Station search: `trips/services/corridor.py`

All cases use the equator road (1,000 miles), radius 5 and thinning 10 unless stated. Expected lists give the stations kept, in order.

| ID | UC | Input: stations as (mile, offset, price, ID) | Expected |
|---|---|---|---|
| CO-01 | UC-01 | (100, on the road, 3.00, 1) | One candidate: mile 100.0, price 3.00, station 1, off_route_miles 0.0, point 200 |
| CO-02 | UC-01 | (100, 4.9 mi N, 3.00, 1) | Kept; off_route_miles 4.9 (±0.001) |
| CO-03 | UC-01 | (100, 4.9 mi S, 3.00, 1) | Kept; off_route_miles 4.9 (±0.001) |
| CO-04 | UC-01 | (100, 5.1 mi N, 3.00, 1) | `[]` |
| CO-05 | UC-01 | (100.2, 3.0 mi N, 3.00, 1) | mile 100.0 (the nearest road point); off_route_miles 3.007 (±0.001) |
| CO-06 | UC-01 | (−3, on the line extended behind the start, 3.00, 1) | `[]`: its mile marker is 0 |
| CO-07 | UC-01 | (1,003, beyond the finish, 3.00, 1) | `[]`: its mile marker is the finish |
| CO-08 | UC-01 | (50, on, 3.00, 1), (300, on, 3.00, 2); `exclude` = station 1 | `[2]` |
| CO-09 | UC-01 | (300, on, 3.00, 1), (100, on, 3.00, 2), (200, on, 3.00, 3) | `[2, 3, 1]`: sorted by mile |
| CO-10 | UC-01 | (100, on, 3.20, 3), (100, on, 3.10, 8): same position | `[8]` |
| CO-11 | UC-01 | (100, on, 3.00, 7), (100, on, 3.00, 4): same position and price | `[4]` |
| CO-12 | UC-01 | (100, on, 3.00, 1), (105, on, 3.10, 2) | `[1]`: a cheaper station within 10 miles |
| CO-13 | UC-01 | (100, on, 3.10, 1), (105, on, 3.00, 2) | `[2]`: the cheaper one may come later |
| CO-14 | UC-01 | (100, on, 3.00, 9), (105, on, 3.00, 1) | `[9]`: equally cheap and earlier, whatever the ID |
| CO-15 | UC-01 | (100, on, 3.00, 1), (110, on, 3.10, 2); then the second at mile 110.5 | `[1]` (exactly 10 miles counts as within); then `[1, 2]` |
| CO-16 | UC-01 | (100, on, 3.00, 1), (108, on, 3.05, 2), (116, on, 3.08, 3) | `[1]`: station 3 is dropped because station 2 is within 10 miles and cheaper, even though station 2 is dropped too |
| CO-17 | UC-01 | Recorded New York–Los Angeles road, real CSV loaded, start station excluded | ≈ 363 candidates before thinning and ≈ 98 after, each pass within 5%: these are small counts, and the finished rules for city positions and marker scaling move a station or two across a limit |

### 2.6 Fuel plan: `trips/services/fuel.py`

`miles[0]` is 0 and is the start; `total` is the trip length. Purchases are `(index, gallons)`. "Fuel cost" is the sum of gallons × price, with the stop cost never added. Gallons and costs match within 1e-9 unless stated.

| ID | UC | miles | prices | total | stop cost | Expected purchases | Fuel cost |
|---|---|---|---|---|---|---|---|
| FU-01 | UC-01 | [0] | [3.00] | 300 | 0 | (0, 30) | 90.00 |
| FU-02 | UC-01 | [0] | [3.00] | 500 | 0 | (0, 50) | 150.00 |
| FU-03 | UC-01 | [0, 100] | [4.00, 3.00] | 400 | 0 | (0, 10), (1, 30) | 130.00 |
| FU-04 | UC-01 | [0, 300] | [3.00, 4.00] | 700 | 0 | (0, 50), (1, 20) | 230.00 |
| FU-05 | UC-01 | [0, 200] | [3.00, 5.00] | 450 | 0 | (0, 45) | 135.00 |
| FU-06 | UC-01 | [0, 250] | [3.00, 3.00] | 600 | 0 | Gallons sum to 60 | 180.00 |
| FU-07 | UC-03 | [0, 10] | [3.10, 3.00] | 400 | 0 | (0, 1), (1, 39) | 120.10 |
| FU-08 | UC-03 | [0, 10] | [3.10, 3.00] | 400 | 3 | (0, 1), (1, 39) | 120.10 |
| FU-09 | UC-03 | [0, 10] | [3.10, 3.00] | 400 | 10 | (0, 40) | 124.00 |
| FU-10 | UC-01 | [0, 100, 100] | [4.00, 3.00, 3.50] | 400 | 0 | (0, 10), (1, 30) | 130.00 |
| FU-11 | UC-03 | [0, 495, 503] | [3.20, 3.10, 3.00] | 990 | 10 | (0, 49.5), (1, 49.5) | 311.85 |
| FU-12 | UC-10 | [0] | [3.00] | 501 | 0 | No plan; gap starts at mile 0, 501 miles long | — |
| FU-13 | UC-10 | [0, 100] | [3.00, 3.00] | 700 | 0 | No plan; gap starts at mile 100, 600 miles long | — |
| FU-14 | UC-10 | [0, 503] | [3.20, 3.00] | 990 | 10 | No plan; gap starts at mile 0, 503 miles long | — |
| FU-15 | UC-01 | [0, 500] | [3.00, 4.00] | 1,000 | 0 | (0, 50), (1, 50): stretches of exactly 500 are allowed | 350.00 |
| FU-16 | UC-10 | [0] | [3.00] | 500.1 | 0 | No plan; gap starts at mile 0, 500.1 miles long | — |
| FU-17 | UC-03 | [0, 10] | [3.10, 3.00] | 400 | 3.89 | (0, 1), (1, 39): the stop saves more than it costs | 120.10 |
| FU-18 | UC-03 | [0, 10] | [3.10, 3.00] | 400 | 3.91 | (0, 40): the stop saves less than it costs | 124.00 |
| FU-19 | UC-01 | [0] | [3.00] | 0.5 | 10 | (0, 0.05) | 0.15 |
| FU-20 | UC-03 | [0, 100, 105, 400, 650] | [4.00, 3.00, 3.01, 3.50, 2.50] | 900 | 0 | (0, 10), (1, 50), (2, 0.5), (3, 4.5), (4, 25) | 269.755 |
| FU-21 | UC-03 | [0, 100, 400, 650] | [4.00, 3.00, 3.50, 2.50] | 900 | 0 | (0, 10), (1, 50), (2, 5), (3, 25): FU-20 without the station at mile 105 | 270.00 |

| ID | UC | Input | Expected |
|---|---|---|---|
| FU-22 | UC-03 | `cheapest_fuel` on the inputs of FU-03, FU-04, FU-07 and FU-20 | The same purchases and fuel costs as those rows |
| FU-23 | UC-03 | `cheapest_fuel([0, 0.03], [3.50, 3.00], 300)` | (0, 0.003), (1, 29.997); fuel cost 90.0015; 1 counted stop, because a purchase under 0.005 gallons is not counted |
| FU-24 | UC-10 | `find_gap`: ([0], 500); ([0], 500.1); ([0, 100], 700); ([0, 503], 990); ([0, 495, 503], 990) | `None`; (0, 500.1); (100, 600); (0, 503); `None`. Each result is the mile where the gap starts and its length |
| FU-25 | UC-10 | `plan_stops` and `cheapest_fuel` on the inputs of FU-12, FU-13, FU-14 and FU-16 | Neither returns a plan |

### 2.7 Exactness: the fuel plan against two exact methods

| ID | UC | Input | Expected |
|---|---|---|---|
| EX-01 | UC-01 | 400 random trips from a fixed seed: 1 to 28 stations, total 50 to 3,000 miles, mile markers to 0.1 mile, prices 2.600 to 4.500 to 3 decimals, and in 30% of trips prices drawn only from {2.90, 3.10, 3.30}. Stop cost 0 | For every feasible trip, the fuel cost of `plan_stops` and of `cheapest_fuel` equals the linear-programming optimum within $0.000001. For every infeasible trip, the solver, `plan_stops` and `find_gap` all report no plan |
| EX-02 | UC-03 | 250 random trips from a fixed seed: 1 to 10 stations, total 100 to 1,800 miles, stop cost drawn from {1, 5, 10, 25, 60} | Fuel cost + stop cost × stops of `plan_stops` equals the minimum over every subset of stations, each subset priced by the linear-programming solver, within $0.000001 |
| EX-03 | UC-01 | Every plan produced in EX-01 and EX-02, replayed mile by mile | Tank never below −1e-9 or above 50 + 1e-9 gallons; gallons sum to total ÷ 10 (±1e-9); no stretch between purchases, or to the finish, over 500 miles |
| EX-04 | UC-03 | 100 random trips from a fixed seed, each planned at stop costs 0, 5, 10, 25 and 60 | As the stop cost rises, the number of stops never rises and the fuel cost never falls |

### 2.8 Answer and rounding: `trips/services/answer.py`

| ID | UC | Input | Expected |
|---|---|---|---|
| AN-01 | UC-01 | Exact gallons [10.004, 20.004, 9.992] at prices [3.00, 3.10, 3.20]; distance 400.0 | Gallons [10.00, 20.01, 9.99] (the 0.01 short goes to the largest purchase); costs [30.00, 62.03, 31.97]; total_fuel_cost 124.00; summary.gallons 40.00 |
| AN-02 | UC-01 | Exact gallons [10.006, 20.006, 9.988], same prices and distance | Gallons [10.01, 20.00, 9.99] (the 0.01 over is taken from the largest purchase); costs [30.03, 62.00, 31.97]; total_fuel_cost 124.00 |
| AN-03 | UC-01 | 1.00 gallon at 3.005; distance 10.0 | cost 3.01 (half-up in decimal arithmetic; floating point would give 3.00) |
| AN-04 | UC-01 | 2.50 gallons at 3.00733333; distance 25.0 | cost 7.52; the JSON text of price_per_gallon is `3.00733333` |
| AN-05 | UC-05 | First fill-up station 25.0 miles from the start; then 25.1 miles | warnings `[]`; then exactly one warning, containing the start station's name and `25.1` |
| AN-06 | UC-01 | Any plan | Top-level keys in this order: summary, warnings, assumptions, fuel_stops, map. `meta` is not part of the builder's output |
| AN-07 | UC-01 | Stop cost 10, then 0, then 12.5 | assumptions `{"range_miles": 500, "miles_per_gallon": 10, "tank_gallons": 50, "starting_fuel_gallons": 0, "stop_cost": 10.0, "search_radius_miles": 5}`; stop_cost 0.0; stop_cost 12.5 |
| AN-08 | UC-01 | A plan with a start purchase and two station purchases | fuel_stops[0]: order 1, kind `start`, mile_marker 0.0, lat and lng of the start place, the start station's details. fuel_stops[1] and [2]: orders 2 and 3, kind `station`, lat and lng of their road points |
| AN-09 | UC-11 | Stop 2 is `SHEETZ #639` in Youngstown, OH | map.features: [0] a LineString with properties kind `route` and distance_miles; then one Point per stop with kind `stop`, order, title `2. SHEETZ #639, Youngstown OH`, name, mile_marker, price_per_gallon, gallons, cost, marker-color; then a Point with kind `start` and one with kind `finish`, each with title and marker-color. Coordinates are `[lng, lat]` |
| AN-10 | UC-01 | Start lat 40.748380123, a mile marker 100.04, first fill-up 3.149 miles | 40.74838; 100.0; 3.1 |
| AN-11 | UC-03 | Free-stop purchases (0, 0.003), (1, 29.997) at [3.50, 3.00]; distance 300.0 | lowest_possible_stops 1; lowest_possible_fuel_cost 90.00 |

### 2.9 Routing client: `trips/services/routing.py`

Start (32.790439, −96.80439) and finish (29.7652, −95.3657) unless stated. "OK answer" is `{"code": "Ok", "routes": [{"distance": 1609344.0, "geometry": {"type": "LineString", "coordinates": [[-96.80439, 32.790439], [-95.3657, 29.7652]]}}]}`.

| ID | UC | Input | Expected |
|---|---|---|---|
| RT-01 | UC-12 | Server 1 gives the OK answer | One GET to `https://router.project-osrm.org/route/v1/driving/` with path coordinates `-96.80439,32.790439;-95.3657,29.7652` (longitude first) and query `overview=full&geometries=geojson` |
| RT-02 | UC-12 | Server 1 gives the OK answer | `Route`: distance_miles 1,000.0; coords `[[-96.80439, 32.790439], [-95.3657, 29.7652]]`; server `router.project-osrm.org`; calls 1 |
| RT-03 | UC-12 | Server 1 answers 503; server 2 the OK answer | Second GET to `https://routing.openstreetmap.de/routed-car/route/v1/driving/` with the same coordinates and query; server `routing.openstreetmap.de`; calls 2 |
| RT-04 | UC-12 | Server 1 answers 429; server 2 OK | Retried; calls 2 |
| RT-05 | UC-12 | Server 1 times out; server 2 OK | Retried; calls 2 |
| RT-06 | UC-12 | Server 1 refuses the connection; server 2 OK | Retried; calls 2 |
| RT-07 | UC-12 | Server 1 answers 200 with a body that is not JSON; separately, 200 JSON with no `routes` | Retried in each case; calls 2 |
| RT-08 | UC-12 | Server 1 answers status 400, `{"code": "NoRoute", "message": "No route found between points"}` | Raises `NoRoute`; calls 1; server 2 never called |
| RT-09 | UC-12 | Both servers answer 500 | Raises `RoutingUnavailable`, reason `error`; exactly 2 requests |
| RT-10 | UC-12 | Both servers time out | Raises `RoutingUnavailable`, reason `timeout`; exactly 2 requests |
| RT-11 | UC-12 | Deadline setting 0.2 s; both servers answer only after 1 s | `RoutingUnavailable`, reason `timeout`, raised in under 0.6 s |
| RT-12 | UC-12 | Any request, to either server | The User-Agent header equals the configured application name |
| RT-13 | UC-12 | Server 1 template setting changed to another host | The request goes to that host |
| RT-14 | UC-12 | Server 1 times out and server 2 answers 500; then the reverse | `RoutingUnavailable`, reason `error` both times: the reason is `timeout` only when every attempt timed out |

### 2.10 Endpoint: `GET /api/v1/route/`

The Django test client against the real URL, with PostgreSQL, the fake routing service and stations created for each case. Unless a case says otherwise: the request is `?start=Dallas, TX&finish=Houston, TX`; a start station priced 3.20 sits at the Dallas position (32.790439, −96.80439); the road and stations are EP-01's. "Fake not called" means the fake routing service counted 0 calls. Every 200 is checked by the verifier (VF-01).

| ID | UC | Input | Expected |
|---|---|---|---|
| EP-01 | UC-01 | Test road 990 miles; stations at mile 200 (3.10), 450 (3.00), 700 (3.20) | 200. Stops: start, mile-450 station, mile-700 station, buying ≈ 45, 50 and 4 gallons. total_fuel_cost 306.80, pass within $0.20. distance_miles 990.0; gallons 99.00; first_fill_distance_miles 0.0; warnings `[]`. meta: routing_calls 1, cache_hit false, routing_server `router.project-osrm.org`. Keys in order summary, warnings, assumptions, fuel_stops, map, meta |
| EP-02 | UC-04 | EP-01's request twice | Second: routing_calls 0, cache_hit true; body without meta identical to the first; fake called once in all |
| EP-03 | UC-03 | EP-01, then the same with `stop_cost=0` | Second: routing_calls 0, cache_hit false; assumptions.stop_cost 0.0; 4 stops; total_fuel_cost 304.30 (pass within $0.20) and equal to lowest_possible_fuel_cost |
| EP-04 | UC-04 | In order: no stop_cost; `stop_cost=10`; `stop_cost=10.00`; `stop_cost=10.5`; `stop_cost=10.50` | cache_hit false, true, true, false, true; routing_calls 1, 0, 0, 0, 0 |
| EP-05 | UC-04 | `?start=Dallas, TX&finish=Houston, TX`, then `?start=dallas tx&finish=houston, texas` | Second: cache_hit true; labels `Dallas, TX` and `Houston, TX` |
| EP-06 | UC-04 | Dallas to Houston, then Houston to Dallas | Second: routing_calls 1, cache_hit false |
| EP-07 | UC-04 | A 200; clock moved 23 h 59 min; then moved to 24 h 1 s | First repeat: cache_hit true. Second repeat: routing_calls 1, cache_hit false |
| EP-08 | UC-04 | Fake fails on both servers; then answers; same request both times | 502, then 200 with routing_calls 1 and cache_hit false |
| EP-09 | UC-15 | `?start=Dallas, TX` | 400 `invalid_request`; details.fields has `finish`; fake not called |
| EP-10 | UC-15 | `?start=&finish=Houston, TX`; `?start=   &finish=Houston, TX` | 400 `invalid_request` each; details.fields has `start`; fake not called |
| EP-11 | UC-15 | No parameters | 400 `invalid_request`; details.fields has `start` and `finish` |
| EP-12 | UC-03 | `stop_cost` = 0; 0.01; 99.99; 100 | 200 each; assumptions.stop_cost 0.0; 0.01; 99.99; 100.0 |
| EP-13 | UC-15 | `stop_cost` = −0.01; 100.01; 10.555; `abc`; `nan`; `inf`; empty | 400 `invalid_request` each; details.fields has `stop_cost`; fake not called |
| EP-14 | UC-15 | EP-01's request plus `&units=km` | 200; body without meta identical to EP-01's |
| EP-15 | UC-07 | `?start=Chicgo, IL&finish=Houston, TX` | 400 `unknown_place`; details.field `start`, query `Chicgo, IL`, suggestions include `Chicago, IL`; fake not called |
| EP-16 | UC-07 | `?start=Chicgo, IL&finish=Nowhere, ZZ` | 400 `unknown_place`; details.field `start`; fake not called |
| EP-17 | UC-07 | `?start=Dallas, TX&finish=Houstn, TX` | 400 `unknown_place`; details.field `finish`; suggestions include `Houston, TX`; fake not called |
| EP-18 | UC-08 | `?start=Honolulu, HI&finish=Houston, TX`; `?start=Dallas, TX&finish=Anchorage, AK` | 422 `outside_coverage`; details.field `start`, then `finish`, with the query as sent; fake not called |
| EP-19 | UC-16 | `?start=Dallas, TX&finish=dallas texas` | 400 `invalid_request`; details.fields has `finish`; fake not called |
| EP-20 | UC-16 | `?start=Dallas, TX&finish=Fort Worth, TX`; the fake returns a road of 0.4 miles | 400 `invalid_request` (treated as the same place); fake called once |
| EP-21 | UC-09 | `?start=Detroit, MI&finish=Buffalo, NY`; the fake returns the recorded Detroit–Buffalo road | 422 `route_leaves_usa`; details.miles_abroad ≈ 252, pass within 2% |
| EP-22 | UC-09 | `longest_run_abroad` replaced to return 25.0; then 25.1 | 200; then 422 `route_leaves_usa` with details.miles_abroad 25.1 |
| EP-23 | UC-09 | `?start=Detroit, MI&finish=Boston, MA`; recorded Detroit–Boston road (706.5 miles); no station along it | 422 `route_leaves_usa`, not `no_fuel_plan`: the border is checked first |
| EP-24 | UC-12 | The fake answers `{"code": "NoRoute"}` | 422 `no_route`; fake called once |
| EP-25 | UC-10 | Test road 990 miles; one station, at mile 503 | 422 `no_fuel_plan`; details.gap_start_mile 0.0; details.gap_miles 503.0 (±0.1) |
| EP-26 | UC-01 | Test road 990 miles; stations at mile 495 (3.10) and 503 (3.00); default stop cost | 200. The thinned list has no plan, so the full list is used: stops are the start and the mile-495 station; total_fuel_cost 311.85, pass within $0.20 |
| EP-27 | UC-03 | Start station 4.00; test road 900 miles; stations at mile 100 (3.00), 105 (3.01), 400 (3.50), 650 (2.50); `stop_cost=0` | 200; total_fuel_cost equals lowest_possible_fuel_cost (≈ 269.76). A plan that skips the mile-105 station would cost ≈ 270.00 and fails |
| EP-28 | UC-12 | Both servers answer 500 | 502 `routing_unavailable`; details.reason `error`; fake called twice |
| EP-29 | UC-12 | Both servers time out | 502 `routing_unavailable`; details.reason `timeout`; fake called twice |
| EP-30 | UC-12 | Server 1 answers 503; server 2 answers with EP-01's road | 200; meta.routing_calls 2; meta.routing_server `routing.openstreetmap.de` |
| EP-31 | UC-13 | Empty station table; then `load_stations --csv <small CSV>`; then the same request on a 238-mile test road | 503 `stations_not_loaded`, fake not called; then 200 with no restart, one stop at the start (station 1, 3.40) |
| EP-32 | UC-13 | Empty station table; `?start=Chicgo, IL&finish=Houston, TX` | 400 `unknown_place`: places are checked before stations |
| EP-33 | UC-01 | The fake raises `RuntimeError("boom")` | 500 `internal_error` in the standard body; the body contains neither `boom` nor `Traceback` |
| EP-34 | UC-18 | 61 requests from one client within a minute | Requests 1 to 60 are not 429; request 61 is 429 `rate_limited` with details.retry_after_seconds above 0 |
| EP-35 | UC-17 | POST, PUT, PATCH and DELETE to `/api/v1/route/?start=Dallas, TX&finish=Houston, TX` | 405 `method_not_allowed` each, in the standard body |
| EP-36 | UC-17 | GET `/api/v1/routes/` and `/api/v2/route/`, with debug on and with debug off | 404 `not_found` each, in the standard body, whatever the debug setting |
| EP-37 | UC-05 | No station at the Dallas position; the nearest is 30 miles north of it | first_fill_distance_miles 30.0; one warning, containing that station's name and `30.0` |
| EP-38 | UC-01 | Instead of the default start station, two at the Dallas position: 3.30 (ID 20) and 3.25 (ID 30); then both at 3.25 | fuel_stops[0].station_id 30, price_per_gallon 3.25; then station 20 |
| EP-39 | UC-15 | Every error response in EP-08 to EP-36 | Body is exactly `{"error": {"code", "message", "details"}}`; the code matches its status in the architecture's error table; message is non-empty text; details is an object, empty for codes whose row lists no details |
| EP-40 | UC-04 | EP-01's request, then again | First: timings_ms routing, own and total present and 0 or more. Second: routing_calls 0, cache_hit true, timings_ms.routing 0 |

### 2.11 Verifier

The verifier checks rules R1 to R16 (section 4). It reads the real CSV for R5, or in the endpoint tests the stations the test created.

| ID | UC | Input | Expected |
|---|---|---|---|
| VF-01 | UC-19 | Every 200 produced by the endpoint tests | No rule fails |
| VF-02 | UC-19 | EP-01's response, unchanged | No rule fails |
| VF-03 | UC-19 | EP-01's response with stop 3's mile_marker moved so it is 500.1 miles after stop 2 | R1 reported |
| VF-04 | UC-19 | Stop 1's gallons raised to 55.00 and stop 3's lowered by the same amount | R2 reported |
| VF-05 | UC-19 | 0.01 added to one stop's gallons | R3 reported |
| VF-06 | UC-19 | 0.01 added to total_fuel_cost | R4 reported |
| VF-07 | UC-19 | The last digit of one price changed | R5 reported |
| VF-08 | UC-19 | fuel_stops[1] and fuel_stops[2] swapped | R6 reported |
| VF-09 | UC-19 | lowest_possible_fuel_cost set to total_fuel_cost + 0.01 | R7 reported |
| VF-10 | UC-19 | 1 added to summary.stops | R8 reported |
| VF-11 | UC-19 | assumptions.tank_gallons set to 60 | R9 reported |
| VF-12 | UC-19 | first_fill_distance_miles set to 30.0, warnings left `[]` | R10 reported |
| VF-13 | UC-19 | One stop Point removed from the map | R11 reported |
| VF-14 | UC-19 | One station stop's lat changed by 0.001 in fuel_stops and in the map | R12 reported |
| VF-15 | UC-19 | One point removed from the middle of the route line | R13 reported |
| VF-16 | UC-19 | One cost written as 12.345 | R14 reported |
| VF-17 | UC-19 | meta.cache_hit true with routing_calls 1 | R15 reported |
| VF-18 | UC-19 | summary.start.label set to `Toronto, ON` | R16 reported |
| VF-19 | UC-19 | The verifier's source | Imports nothing from `config`, `stations` or `trips` |

### 2.12 Project

| ID | UC | Input | Expected |
|---|---|---|---|
| PJ-01 | UC-19 | `django.get_version()` | 6.1.3 or a later 6.1 release |
| PJ-02 | UC-19 | Source of `fuel.py`, `geo.py`, `corridor.py`, `answer.py`, `stations/types.py`, `stations/sphere.py` | None imports `django` |
| PJ-03 | UC-19 | A test opens a connection to a public address, then queries the database | The connection fails with the blocking fixture's error; the database query works |
| PJ-04 | UC-19 | Settings | Routing templates for `router.project-osrm.org` and `routing.openstreetmap.de/routed-car`, both with `overview=full&geometries=geojson`; deadline 5 s; a non-empty User-Agent; default stop cost 10; cache timeout 86,400 s; rate limit 60 a minute |
| PJ-05 | UC-19 | `DATABASE_URL=postgres://u:p@db:5432/x` | `DATABASES["default"]`: PostgreSQL engine, host `db`, port 5432, name `x` |

## 3. Live cases

Run by `scripts/live_check.py` against a running server that uses the real routing service.

- The server is freshly started, with the stations loaded and empty caches.
- Order: P01 to P20, then N01 to N26 except N15, then a 60-second pause, then N15 last.
- At least 1.2 seconds pass between requests: the routing servers ask for no more than one request a second, and the API allows 60 a minute.
- Every 200 is also checked against rules R1 to R16 (section 4).
- **Actual** records what came back: status, code and the figures named. **Result** is pass or fail.

### 3.1 Positive

| ID | UC | Request | Status | Expected | Actual | Result |
|---|---|---|---|---|---|---|
| P01 | UC-01 | `/api/v1/route/?start=New York, NY&finish=Los Angeles, CA` | 200 | distance_miles ≈ 2,800.7, pass within 2%; stops fewer than 10 (design: 7); total_fuel_cost ≈ 865.93, pass within 2%; lowest_possible_fuel_cost ≈ 854.65, pass within 2%; first_fill_distance_miles ≈ 3.1, pass within 2%; warnings `[]`; labels `New York, NY`, `Los Angeles, CA`; routing_calls 1; cache_hit false | | |
| P02 | UC-04 | P01's request again | 200 | summary identical to P01's; routing_calls 0; cache_hit true; round trip under 50 ms | | |
| P03 | UC-03 | `/api/v1/route/?start=New York, NY&finish=Los Angeles, CA&stop_cost=0` | 200 | stops more than P01's (design: 17); total_fuel_cost equals P01's lowest_possible_fuel_cost and this response's own; assumptions.stop_cost 0.0; routing_calls 0; cache_hit false | | |
| P04 | UC-03 | `/api/v1/route/?start=New York, NY&finish=Los Angeles, CA&stop_cost=25` | 200 | stops no more than P01's (design: 6); total_fuel_cost not below P01's, ≈ 884.79, pass within 2%; routing_calls 0 | | |
| P05 | UC-05 | `/api/v1/route/?start=Los Angeles, CA&finish=New York, NY` | 200 | first_fill_distance_miles over 100, ≈ 121, pass within 2%; one warning, naming fuel_stops[0].name and the distance; routing_calls 1 | | |
| P06 | UC-01 | `/api/v1/route/?start=Seattle, WA&finish=Miami, FL` | 200 | distance_miles ≈ 3,301.2, pass within 2%; stops fewer than 12 | | |
| P07 | UC-01 | `/api/v1/route/?start=Chicago, IL&finish=Houston, TX` | 200 | distance_miles ≈ 1,086.9, pass within 2% | | |
| P08 | UC-02 | `/api/v1/route/?start=Dallas, TX&finish=Houston, TX` | 200 | distance_miles ≈ 238.1, pass within 2%; total_fuel_cost above 0 | | |
| P09 | UC-01 | `/api/v1/route/?start=Boston, MA&finish=Washington, DC` | 200 | distance_miles ≈ 437.1, pass within 2% | | |
| P10 | UC-06 | `/api/v1/route/?start=st. louis, mo&finish=Winston-Salem, North Carolina` | 200 | summary.start.label `Saint Louis, MO`; summary.finish.label `Winston Salem, NC` | | |
| P11 | UC-06 | `/api/v1/route/?start=Dallas TX&finish=Phoenix, Arizona, USA` | 200 | labels `Dallas, TX`, `Phoenix, AZ` | | |
| P12 | UC-02 | `/api/v1/route/?start=Fort Worth, TX&finish=Dallas, TX` | 200 | stops 1; fuel_stops[0] kind `start`, mile_marker 0.0, gallons = distance_miles ÷ 10; distance_miles under 50 | | |
| P13 | UC-05 | `/api/v1/route/?start=Houston, TX&finish=Dallas, TX` | 200 | first_fill_distance_miles over 25; one warning | | |
| P14 | UC-04 | `/api/v1/route/?start=new york city, ny&finish=Los Angeles, California` | 200 | summary identical to P01's, labels `New York, NY` and `Los Angeles, CA`; routing_calls 0; cache_hit true | | |
| P15 | UC-03 | `/api/v1/route/?start=New York, NY&finish=Los Angeles, CA&stop_cost=100` | 200 | stops at least 6 and no more than P04's; total_fuel_cost not below P04's; assumptions.stop_cost 100.0; routing_calls 0 | | |
| P16 | UC-04 | `/api/v1/route/?start=Dallas, TX&finish=Houston, TX&units=km` | 200 | summary identical to P08's; routing_calls 0; cache_hit true | | |
| P17 | UC-06 | `/api/v1/route/?start=Washington, D.C.&finish=Boston, MA` | 200 | summary.start.label `Washington, DC` | | |
| P18 | UC-06 | `/api/v1/route/?start=Santa Fe, New Mexico&finish=Denver, CO` | 200 | summary.start.label `Santa Fe, NM` | | |
| P19 | UC-02, UC-05 | `/api/v1/route/?start=Los Angeles, CA&finish=Las Vegas, NV` | 200 | distance_miles ≈ 276.2, pass within 2%; stops 1; first_fill_distance_miles ≈ 121, pass within 2%; one warning | | |
| P20 | UC-02 | `/api/v1/route/?start=Los Angeles, CA&finish=San Francisco, CA` | 200 | distance_miles under 500; stops 1; one warning | | |

### 3.2 Negative

| ID | UC | Request | Status | Expected | Actual | Result |
|---|---|---|---|---|---|---|
| N01 | UC-15 | `/api/v1/route/?start=New York, NY` | 400 | `invalid_request`; details.fields has `finish` | | |
| N02 | UC-15 | `/api/v1/route/?start=&finish=Los Angeles, CA` | 400 | `invalid_request`; details.fields has `start` | | |
| N03 | UC-07 | `/api/v1/route/?start=Chicgo, IL&finish=Houston, TX` | 400 | `unknown_place`; field `start`; query `Chicgo, IL`; suggestions include `Chicago, IL`, at most 5 | | |
| N04 | UC-07 | `/api/v1/route/?start=Dallas, TX&finish=Chicago` | 400 | `unknown_place`; field `finish`; suggestions `["Chicago, IL"]` | | |
| N05 | UC-07 | `/api/v1/route/?start=Dallas, TX&finish=Springfield, ZZ` | 400 | `unknown_place`; field `finish`; at most 5 suggestions | | |
| N06 | UC-08 | `/api/v1/route/?start=Honolulu, HI&finish=Los Angeles, CA` | 422 | `outside_coverage`; field `start`; query `Honolulu, HI` | | |
| N07 | UC-08 | `/api/v1/route/?start=Seattle, WA&finish=Anchorage, AK` | 422 | `outside_coverage`; field `finish` | | |
| N08 | UC-08 | `/api/v1/route/?start=Toronto, ON&finish=Buffalo, NY` | 422 | `outside_coverage`; field `start` | | |
| N09 | UC-16 | `/api/v1/route/?start=Dallas, TX&finish=dallas texas` | 400 | `invalid_request`; details.fields has `finish` | | |
| N10 | UC-15 | `/api/v1/route/?start=New York, NY&finish=Los Angeles, CA&stop_cost=-1`, then with `101`, `abc`, `nan` | 400 each | `invalid_request`; details.fields has `stop_cost` | | |
| N11 | UC-09 | `/api/v1/route/?start=Detroit, MI&finish=Buffalo, NY` | 422 | `route_leaves_usa`; miles_abroad ≈ 252, pass within 2% | | |
| N12 | UC-10 | `/api/v1/route/?start=Los Angeles, CA&finish=Seattle, WA` | 422 | `no_fuel_plan`; gap_start_mile 0.0; gap_miles ≈ 886, pass within 2% | | |
| N13 | UC-17 | POST, then PUT, PATCH, DELETE: `/api/v1/route/?start=New York, NY&finish=Los Angeles, CA` | 405 each | `method_not_allowed`; standard error body | | |
| N14 | UC-17 | `/api/v1/routes/?start=New York, NY&finish=Los Angeles, CA` | 404 | `not_found`; standard error body | | |
| N15 | UC-18 | P01's request repeated with no pause; run last | 429 | `rate_limited` by the 61st request at the latest; details.retry_after_seconds above 0 | | |
| N16 | UC-07 | `/api/v1/route/?start=Chicgo, IL&finish=Nowhere, ZZ` | 400 | `unknown_place`; field `start` | | |
| N17 | UC-15 | `/api/v1/route/?start=Nowhere, ZZ` | 400 | `invalid_request` (the missing finish is found before places are looked up); details.fields has `finish` | | |
| N18 | UC-08 | `/api/v1/route/?start=Tijuana, Mexico&finish=San Diego, CA` | 422 | `outside_coverage`; field `start` | | |
| N19 | UC-08 | `/api/v1/route/?start=Miami, FL&finish=San Juan, PR` | 422 | `outside_coverage`; field `finish` | | |
| N20 | UC-15 | `/api/v1/route/?start=   &finish=Los Angeles, CA` | 400 | `invalid_request`; details.fields has `start` | | |
| N21 | UC-15 | `/api/v1/route/?start=New York, NY&finish=Los Angeles, CA&stop_cost=100.01`, then with `10.555`, then with `stop_cost=` empty | 400 each | `invalid_request`; details.fields has `stop_cost` | | |
| N22 | UC-09 | `/api/v1/route/?start=Detroit, MI&finish=Boston, MA` | 422 | `route_leaves_usa`; miles_abroad ≈ 234, pass within 2% | | |
| N23 | UC-10 | `/api/v1/route/?start=San Francisco, CA&finish=Portland, OR` | 422 | `no_fuel_plan`; gap_start_mile 0.0; gap_miles ≈ 554, pass within 2% | | |
| N24 | UC-15 | `/api/v1/route/` | 400 | `invalid_request`; details.fields has `start` and `finish` | | |
| N25 | UC-16 | `/api/v1/route/?start=New York City, NY&finish=Manhattan, NY` | 400 | `invalid_request`; details.fields has `finish` | | |
| N26 | UC-07 | `/api/v1/route/?start=75201&finish=Dallas, TX` | 400 | `unknown_place`; field `start` | | |

## 4. Correctness rules

Checked on every successful response: by the verifier in the endpoint tests (VF-01) and by `scripts/live_check.py` on every live 200. Money, gallons and prices are read from the JSON as exact decimals.

1. **R1 Range.** No stretch between consecutive stops' mile markers, or from the last stop to `distance_miles`, is over 500 miles.
2. **R2 Tank.** Walking the stops from mile 0 with an empty tank, adding each stop's gallons and burning 1 gallon per 10 miles, the tank is never below 0 or above 50 gallons, with 0.05 allowed for rounding.
3. **R3 Gallons.** The stops' gallons add up exactly to `summary.gallons`, which equals `summary.distance_miles` ÷ 10 exactly.
4. **R4 Money.** Each stop's `cost` equals its `gallons` × `price_per_gallon`, rounded half-up to cents. `summary.total_fuel_cost` equals the sum of the costs exactly.
5. **R5 Prices and names.** Each stop's `price_per_gallon` equals, as an exact decimal, the lowest `Retail Price` the CSV lists for its `station_id`. Its `name`, `address`, `city` and `state` equal that row's, with spaces trimmed; on a price tie, the first such row.
6. **R6 Stops.** `fuel_stops[0]` has `kind` `start`, `mile_marker` 0.0, and `lat` and `lng` equal to `summary.start`. Every other stop has `kind` `station`. `order` runs 1, 2, 3… Mile markers strictly increase and stay below `distance_miles`. No `station_id` appears twice.
7. **R7 Lowest bill.** `lowest_possible_fuel_cost` is not above `total_fuel_cost`, and `lowest_possible_stops` is at least 1. When `assumptions.stop_cost` is 0, the two costs are equal (FR-16).
8. **R8 Stop count.** `summary.stops` equals the number of `fuel_stops`, and is at least `distance_miles` ÷ 500 rounded up.
9. **R9 Assumptions.** `assumptions` is `range_miles` 500, `miles_per_gallon` 10, `tank_gallons` 50, `starting_fuel_gallons` 0, `search_radius_miles` 5, and `stop_cost` equal to the request's, or 10.0 when none was sent.
10. **R10 First fill-up.** `first_fill_distance_miles` is 0 or more. If it is over 25, `warnings` holds exactly one sentence, containing `fuel_stops[0].name` and the distance; otherwise `warnings` is `[]`.
11. **R11 Map.** `map` is a GeoJSON FeatureCollection. Feature 0 is a LineString with `kind` `route` and `distance_miles` equal to the summary's. Then one Point per stop, in order, with `kind` `stop` and `order`, `name`, `mile_marker`, `price_per_gallon`, `gallons` and `cost` equal to the stop's, and `title` `order. NAME, City ST`. Then a Point with `kind` `start` at `summary.start` and one with `kind` `finish` at `summary.finish`. Every Point has `title` and `marker-color`. Coordinates are `[lng, lat]`.
12. **R12 Stops on the line.** Each `station` stop's `[lng, lat]` is one of the route line's coordinates. Their positions in the line increase with `order`. For a stop at line position `i`, `mile_marker` is within 0.5% + 0.05 miles of `0.5 × i`.
13. **R13 Line spacing.** Consecutive route-line points are at most 0.51 miles apart, and the line has `2 × distance_miles + 1` points, within 1%.
14. **R14 Precision.** Every number is a JSON number. Miles have at most 1 decimal, gallons and money at most 2, coordinates at most 5.
15. **R15 Meta.** `routing_calls` is 0, 1 or 2. `cache_hit` true implies `routing_calls` 0. `timings_ms.routing`, `own` and `total` are 0 or more, and `routing` is 0 when `routing_calls` is 0. `routing_server` is `router.project-osrm.org` or `routing.openstreetmap.de`.
16. **R16 Labels.** `summary.start.label` and `summary.finish.label` have the form `City, ST`, with ST one of the lower 48 states or DC.

## 5. Speed checks

Round trip is measured by `scripts/live_check.py` on the same machine as the server, from sending the request to receiving the whole body.

| ID | UC | Requirement | Input | Expected | Actual | Result |
|---|---|---|---|---|---|---|
| S01 | UC-01 | NFR-1 | P01 and P06, each a new trip | meta.timings_ms.own 100 or less; round trip minus meta.timings_ms.routing 100 ms or less | | |
| S02 | UC-04 | NFR-11 | P02 | Round trip under 50 ms; meta.timings_ms.total under 50; routing_calls 0 | | |
| S03 | UC-03 | NFR-1, NFR-2 | P03 (road cached, new stop cost) | routing_calls 0; round trip 100 ms or less | | |
| S04 | UC-12 | NFR-12 | Endpoint test with the default 5 s deadline; both fake servers accept the request and never answer | 502 `routing_unavailable`, reason `timeout`, within 11 s of the request | | |

## 6. Cases that need a fake routing service or fixed test data

| Case | Proven by | Why it cannot be a live case |
|---|---|---|
| First server fails, second answers | RT-03 to RT-07, EP-30 | The public servers cannot be made to fail on demand |
| Both servers fail | RT-09, EP-28 | Same |
| Both time out, and the answer comes within the deadline | RT-10, RT-11, EP-29, S04 | Same, and the delay must be controlled |
| Never more than two routing calls | RT-09, RT-10 | Counting attempts needs control of the transport |
| A timeout mixed with another failure reports `error` | RT-14 | Same |
| The server finds no road | RT-08, EP-24 | No pair of covered places is known for which the routing service finds no road |
| No routing call for errors found before routing | EP-09 to EP-11, EP-13, EP-15 to EP-19, EP-31, EP-32 | Error bodies carry no `meta`, so only a fake can count the calls |
| A road shorter than half a mile | EP-20 | No pair of distinct places is known whose road is that short |
| A border run of exactly 25.0 and 25.1 miles | EP-22 | A real road cannot be picked to run an exact distance abroad |
| The thinned list has no plan but the full list does | EP-26 | Needs stations at chosen miles |
| Stop cost 0 when thinning drops a useful station | EP-27 | Same |
| Start stations tied on distance | EP-38 | Needs stations at a chosen position |
| Station table empty | EP-31, EP-32 | Would mean emptying the table of the running server |
| Unexpected failure | EP-33 | Needs an injected fault |
| Cache expiry after 24 hours | EP-07 | Needs a moved clock |
| Errors are not cached | EP-08 | Needs a routing failure followed by a success |

## 7. Container, Postman, fresh clone and manual checks

| ID | UC | Input | Expected | Actual | Result |
|---|---|---|---|---|---|
| CT-01 | UC-14 | `docker compose up` in a fresh clone | The database and the API start. The API's log shows the loader's counts, ending with 6,626 stations saved. `GET /api/v1/route/?start=Dallas, TX&finish=Houston, TX` returns 200 | | |
| CT-02 | UC-14 | `docker compose down`, then `docker compose up` | Starts again; the loader replaces the table without error; still 6,626 stations; P08 returns 200 | | |
| CT-03 | UC-14 | `scripts/live_check.py` against the Compose stack | Every P and N case passes; S01 to S03 are met | | |
| CT-04 | UC-14 | P01, then P02, against the Compose stack | P02 reports routing_calls 0 and cache_hit true: the API runs as one process | | |
| CT-05 | UC-14 | `docker compose config` | A PostgreSQL 17 image; the API receives `DATABASE_URL` | | |
| PM-01 | UC-20 | `npx newman run <collection in docs/> --env-var base_url=<API address> --delay-request 1200`, against a freshly started API | Exit code 0; every check passes | | |
| PM-02 | UC-20 | The collection file | One variable, `base_url`. Folders: 1. Demo (P01, P02, P03, P04); 2. More trips (P05, P06, P08, P10, P11); 3. Errors (N01, N03, N06, N11, N12). Every request has at least one check | | |
| FC-01 | UC-14 | Clone the public repository into an empty folder on a machine with only git and Docker; no `.env`; `docker compose up` | P08 returns 200. Nothing asks for an account or a key | | |
| FC-02 | UC-19 | `uv sync`, the Compose database running, `uv run pytest` | Every test passes; none is skipped for want of a network | | |
| FC-03 | UC-19 | `uv run ruff check .` | Exit code 0; no findings | | |
| FC-04 | UC-14 | Search the repository for keys and secrets; read `.env.example` | No API key or token. The only password is the local database default in the Compose file. `.env.example` lists `DATABASE_URL`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS` | | |
| FC-05 | UC-19 | Only if CI is built (NFR-17): a push to the repository | The workflow runs lint and tests, and the run passes | | |
| M01 | UC-11 | P01's `map` pasted into geojson.io | A line from New York to Los Angeles; one marker per stop, labelled with its title, for example `2. NAME, City ST`; a start and a finish marker | | |
| M02 | UC-14 | The README | Covers setup with one command, an example request, and the decisions D-1 to D-15 | | |
| M03 | — | The Loom video and the hiring-thread message | Video 5 minutes or less: the API in Postman, then the code. Both links sent before Friday 20 Nov 2026, 8 pm, as the message time shows | | |
| M04 | UC-19 | Read the code against `backend-architecture.md` sections 3 and 4 | Each module sits in its layer and does only that layer's work; each has a short description at the top | | |

## 8. Acceptance checks

How each acceptance check in `requirements.md` section 9 is proven.

| Check | Proven by |
|---|---|
| 1. New York to Los Angeles: route, stops, total, fewer than 10 stops | P01 |
| 2. No stretch over 500; gallons = distance ÷ 10; total = sum of costs | P01 with R1, R3, R4 |
| 3. One routing call; none on repeat or with another stop cost | P01, P02, P03 |
| 4. A trip under 500 miles has a plan costing more than 0 | P08, P12, P19 |
| 5. Los Angeles start: first fill-up over 100 miles, with a warning | P05 |
| 6. Honolulu and an unknown name rejected without a routing call; Detroit–Buffalo leaves the USA; Los Angeles–Seattle has no fuel | N06, N03, EP-15, EP-18, N11, N12 |
| 7. The map shows the route with the stops marked | M01, R11, R12 |
| 8. The fuel tests pass, including the two exact methods | FU-01 to FU-25, EX-01, EX-02 |
| 9. A fresh clone starts with one Compose command, with no key | FC-01, CT-01 |
| 10. Loom recorded, links sent before the deadline | M03 |
