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

No automated test reaches beyond the local machine (NFR-13). A test fixture blocks every connection except those to the same machine: the local database and, for their own tests, the local Redis and the stand-in routing server (PJ-03).

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
| PL-15 | UC-08 | `Honolulu, HI`; `Anchorage, AK`; `Juneau, Alaska`; `San Juan, PR`; `Toronto, ON`; `Vancouver, BC`; `Montreal, Canada`; `Tijuana, Mexico`; `Tijuana Mexico`; `Toronto Canada` | Each raises `OutsideCoverage` with the field passed in and the query as given |
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
| FU-23 | UC-03 | `cheapest_fuel([0, 0.03], [3.50, 3.00], 300)` | (0, 0.003), (1, 29.997); fuel cost 90.0015; one purchase only of 0.005 gallons or more: the tiny one is kept, and in an answer it would show as 0.00 gallons |
| FU-24 | UC-10 | `find_gap`: ([0], 500); ([0], 500.1); ([0, 100], 700); ([0, 503], 990); ([0, 495, 503], 990) | `None`; (0, 500.1); (100, 600); (0, 503); `None`. Each result is the mile where the gap starts and its length |
| FU-25 | UC-10 | `plan_stops` and `cheapest_fuel` on the inputs of FU-12, FU-13, FU-14 and FU-16 | Neither returns a plan |
| FU-26 | UC-03 | `plan_stops([0, 100, 200], [3.00, 3.00, 3.00], 400, 0)`; then with total 600 | (0, 40); then (0, 10), (1, 50). Equal costs are settled the same way every time: fewer stops, then the earlier station |

### 2.7 Exactness: the fuel plan against two exact methods

| ID | UC | Input | Expected |
|---|---|---|---|
| EX-01 | UC-01 | 400 random trips from a fixed seed: 1 to 28 stations, total 50 to 3,000 miles, mile markers to 0.1 mile, prices 2.600 to 4.500 to 3 decimals, and in 30% of trips prices drawn only from {2.90, 3.10, 3.30}. Stop cost 0 | For every feasible trip, the fuel cost of `plan_stops` and of `cheapest_fuel` equals the linear-programming optimum within $0.000001. For every infeasible trip, the solver, `plan_stops` and `find_gap` all report no plan |
| EX-02 | UC-03 | 250 random trips from a fixed seed: 1 to 8 stations, total 100 to 1,800 miles, stop cost drawn from {1, 5, 10, 25, 60}. The same check with 1 to 10 stations (13,506 solver calls, about 30 seconds) runs with `uv run pytest -m slow` | Fuel cost + stop cost × stops of `plan_stops` equals the minimum over every subset of stations, each subset priced by the linear-programming solver, within $0.000001 |
| EX-03 | UC-01 | Every plan produced in EX-01 and EX-02, replayed mile by mile | Tank never below −1e-9 or above 50 + 1e-9 gallons; gallons sum to total ÷ 10 (±1e-9); no stretch between purchases, or to the finish, over 500 miles |
| EX-04 | UC-03 | 100 random trips from a fixed seed, drawn as in EX-01, each planned at stop costs 0, 5, 10, 25 and 60 | As the stop cost rises, the number of stops never rises and the fuel cost never falls |

### 2.8 Answer and rounding: `trips/services/answer.py`

| ID | UC | Input | Expected |
|---|---|---|---|
| AN-01 | UC-01 | Exact gallons [10.004, 20.004, 9.992] at prices [3.00, 3.10, 3.20]; distance 400.0 | Gallons [10.00, 20.01, 9.99] (running totals 10.00, 30.01, 40.00); costs [30.00, 62.03, 31.97]; total_fuel_cost 124.00; summary.gallons 40.00 |
| AN-02 | UC-01 | Exact gallons [10.006, 20.006, 9.988], same prices and distance | Gallons [10.01, 20.00, 9.99] (running totals 10.01, 30.01, 40.00); costs [30.03, 62.00, 31.97]; total_fuel_cost 124.00 |
| AN-03 | UC-01 | 1.00 gallon at 3.005; distance 10.0 | cost 3.01 (half-up in decimal arithmetic; floating point would give 3.00) |
| AN-04 | UC-01 | 2.50 gallons at 3.00733333; distance 25.0 | cost 7.52; the JSON text of price_per_gallon is `3.00733333` |
| AN-05 | UC-05 | First fill-up station 25.0 miles from the start; then 25.1 miles | warnings `[]`; then exactly one warning, containing the start station's name and `25.1` |
| AN-06 | UC-01 | Any plan | Top-level keys in this order: summary, warnings, assumptions, fuel_stops, map. `meta` is not part of the builder's output |
| AN-07 | UC-01 | Stop cost 10, then 0, then 12.5 | assumptions `{"range_miles": 500, "miles_per_gallon": 10, "tank_gallons": 50, "starting_fuel_gallons": 0, "stop_cost": 10.0, "search_radius_miles": 5}`; stop_cost 0.0; stop_cost 12.5 |
| AN-08 | UC-01 | A plan with a start purchase and two station purchases | fuel_stops[0]: order 1, kind `start`, mile_marker 0.0, lat and lng of the start place, the start station's details. fuel_stops[1] and [2]: orders 2 and 3, kind `station`, lat and lng of their road points |
| AN-09 | UC-11 | Stop 2 is `SHEETZ #639` in Youngstown, OH | map.features: [0] a LineString with properties kind `route` and distance_miles; then one Point per stop with kind `stop`, order, title `2. SHEETZ #639, Youngstown OH`, name, mile_marker, price_per_gallon, gallons, cost, marker-color; then a Point with kind `start` and one with kind `finish`, each with title and marker-color. Coordinates are `[lng, lat]` |
| AN-10 | UC-01 | Start lat 40.748380123, a mile marker 100.04, first fill-up 3.149 miles | 40.74838; 100.0; 3.1 |
| AN-11 | UC-03 | QB-13's input: the plan buys (0, 30.000) at 3.50; free-stop purchases (0, 10.001), (1, 0.003), (2, 10.002), (3, 9.994) at [3.50, 3.20, 3.00, 2.00]; distance 300.0 | lowest_possible_stops 3: the 0.003-gallon purchase shows as 0.00 and is no stop; lowest_possible_fuel_cost 85.01: its fuel is in the next running total |

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

The verifier checks rules R1 to R17 (section 4). It reads the real CSV for R5, or in the endpoint tests the stations the test created.

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
- The **Actual** and **Result** columns below hold the run of 18 Nov 2026 against the finished API: 49 cases, 49 passed. Expected figures marked ≈ were measured while the API was designed and are left as they were, so the two columns can be compared.

### 3.1 Positive

| ID | UC | Request | Status | Expected | Actual | Result |
|---|---|---|---|---|---|---|
| P01 | UC-01 | `/api/v1/route/?start=New York, NY&finish=Los Angeles, CA` | 200 | distance_miles ≈ 2,800.7, pass within 2%; stops fewer than 10 (design: 7); total_fuel_cost ≈ 865.93, pass within 2%; lowest_possible_fuel_cost ≈ 854.65, pass within 2%; first_fill_distance_miles ≈ 3.1, pass within 2%; warnings `[]`; labels `New York, NY`, `Los Angeles, CA`; routing_calls 1; cache_hit false | 200; summary.distance_miles 2800.6; summary.stops 7; summary.total_fuel_cost 867.27; summary.lowest_possible_fuel_cost 855.95; summary.first_fill_distance_miles 3.1; warnings []; summary.start.label New York, NY; summary.finish.label Los Angeles, CA; meta.routing_calls 1; meta.cache_hit false; round trip 2023.7 ms | PASS |
| P02 | UC-04 | P01's request again | 200 | summary identical to P01's; routing_calls 0; cache_hit true; round trip under 50 ms | 200; summary identical; meta.routing_calls 0; meta.cache_hit true; round_trip_ms 15.4 | PASS |
| P03 | UC-03 | `/api/v1/route/?start=New York, NY&finish=Los Angeles, CA&stop_cost=0` | 200 | stops more than P01's (design: 17); total_fuel_cost equals P01's lowest_possible_fuel_cost and this response's own; assumptions.stop_cost 0.0; routing_calls 0; cache_hit false | 200; summary.stops 19; summary.total_fuel_cost 855.95; assumptions.stop_cost 0.0; meta.routing_calls 0; meta.cache_hit false; round trip 31.7 ms | PASS |
| P04 | UC-03 | `/api/v1/route/?start=New York, NY&finish=Los Angeles, CA&stop_cost=25` | 200 | stops no more than P01's (design: 6); total_fuel_cost not below P01's, ≈ 884.79, pass within 2%; routing_calls 0 | 200; summary.stops 6; summary.total_fuel_cost 886.15; meta.routing_calls 0; round trip 51.9 ms | PASS |
| P05 | UC-05 | `/api/v1/route/?start=Los Angeles, CA&finish=New York, NY` | 200 | first_fill_distance_miles over 100, ≈ 121, pass within 2%; one warning, naming fuel_stops[0].name and the distance; routing_calls 1 | 200; summary.first_fill_distance_miles 120.6; warnings ["The nearest listed fuel station to the start is Shelee's Travel Center in Coachella, CA, 120.6 miles away. The first fill-up is priced there."]; warnings.0 The nearest listed fuel station to the start is Shelee's Travel Center in Coachella, CA, 120.6 miles away. The first fill-up is priced there.; meta.routing_calls 1; round trip 1104.6 ms | PASS |
| P06 | UC-01 | `/api/v1/route/?start=Seattle, WA&finish=Miami, FL` | 200 | distance_miles ≈ 3,301.2, pass within 2%; stops fewer than 12 | 200; summary.distance_miles 3301.1; summary.stops 8; round trip 940.8 ms | PASS |
| P07 | UC-01 | `/api/v1/route/?start=Chicago, IL&finish=Houston, TX` | 200 | distance_miles ≈ 1,086.9, pass within 2% | 200; summary.distance_miles 1086.9; round trip 1189.6 ms | PASS |
| P08 | UC-02 | `/api/v1/route/?start=Dallas, TX&finish=Houston, TX` | 200 | distance_miles ≈ 238.1, pass within 2%; total_fuel_cost above 0 | 200; summary.distance_miles 239.6; summary.total_fuel_cost 68.62; round trip 246.6 ms | PASS |
| P09 | UC-01 | `/api/v1/route/?start=Boston, MA&finish=Washington, DC` | 200 | distance_miles ≈ 437.1, pass within 2% | 200; summary.distance_miles 437.0; round trip 474.6 ms | PASS |
| P10 | UC-06 | `/api/v1/route/?start=st. louis, mo&finish=Winston-Salem, North Carolina` | 200 | summary.start.label `Saint Louis, MO`; summary.finish.label `Winston Salem, NC` | 200; summary.start.label Saint Louis, MO; summary.finish.label Winston Salem, NC; round trip 680.3 ms | PASS |
| P11 | UC-06 | `/api/v1/route/?start=Dallas TX&finish=Phoenix, Arizona, USA` | 200 | labels `Dallas, TX`, `Phoenix, AZ` | 200; summary.start.label Dallas, TX; summary.finish.label Phoenix, AZ; round trip 480.7 ms | PASS |
| P12 | UC-02 | `/api/v1/route/?start=Fort Worth, TX&finish=Dallas, TX` | 200 | stops 1; fuel_stops[0] kind `start`, mile_marker 0.0, gallons = distance_miles ÷ 10; distance_miles under 50 | 200; summary.stops 1; fuel_stops.0.kind start; fuel_stops.0.mile_marker 0.0; fuel_stops.0.gallons 3.22; summary.distance_miles 32.2; round trip 226.4 ms | PASS |
| P13 | UC-05 | `/api/v1/route/?start=Houston, TX&finish=Dallas, TX` | 200 | first_fill_distance_miles over 25; one warning | 200; summary.first_fill_distance_miles 41.8; warnings ["The nearest listed fuel station to the start is FUEL MAXX #57 in Liberty, TX, 41.8 miles away. The first fill-up is priced there."]; round trip 403.9 ms | PASS |
| P14 | UC-04 | `/api/v1/route/?start=new york city, ny&finish=Los Angeles, California` | 200 | summary identical to P01's, labels `New York, NY` and `Los Angeles, CA`; routing_calls 0; cache_hit true | 200; summary identical; summary.start.label New York, NY; summary.finish.label Los Angeles, CA; meta.routing_calls 0; meta.cache_hit true; round trip 29.9 ms | PASS |
| P15 | UC-03 | `/api/v1/route/?start=New York, NY&finish=Los Angeles, CA&stop_cost=100` | 200 | stops at least 6 and no more than P04's; total_fuel_cost not below P04's; assumptions.stop_cost 100.0; routing_calls 0 | 200; summary.stops 6; summary.total_fuel_cost 886.15; assumptions.stop_cost 100.0; meta.routing_calls 0; round trip 32.2 ms | PASS |
| P16 | UC-04 | `/api/v1/route/?start=Dallas, TX&finish=Houston, TX&units=km` | 200 | summary identical to P08's; routing_calls 0; cache_hit true | 200; summary identical; meta.routing_calls 0; meta.cache_hit true; round trip 5.6 ms | PASS |
| P17 | UC-06 | `/api/v1/route/?start=Washington, D.C.&finish=Boston, MA` | 200 | summary.start.label `Washington, DC` | 200; summary.start.label Washington, DC; round trip 636.7 ms | PASS |
| P18 | UC-06 | `/api/v1/route/?start=Santa Fe, New Mexico&finish=Denver, CO` | 200 | summary.start.label `Santa Fe, NM` | 200; summary.start.label Santa Fe, NM; round trip 607.5 ms | PASS |
| P19 | UC-02, UC-05 | `/api/v1/route/?start=Los Angeles, CA&finish=Las Vegas, NV` | 200 | distance_miles ≈ 276.2, pass within 2%; stops 1; first_fill_distance_miles ≈ 121, pass within 2%; one warning | 200; summary.distance_miles 276.2; summary.stops 1; summary.first_fill_distance_miles 120.6; warnings ["The nearest listed fuel station to the start is Shelee's Travel Center in Coachella, CA, 120.6 miles away. The first fill-up is priced there."]; round trip 413.1 ms | PASS |
| P20 | UC-02 | `/api/v1/route/?start=Los Angeles, CA&finish=San Francisco, CA` | 200 | distance_miles under 500; stops 1; one warning | 200; summary.distance_miles 389.0; summary.stops 1; warnings ["The nearest listed fuel station to the start is Shelee's Travel Center in Coachella, CA, 120.6 miles away. The first fill-up is priced there."]; round trip 622.7 ms | PASS |

### 3.2 Negative

| ID | UC | Request | Status | Expected | Actual | Result |
|---|---|---|---|---|---|---|
| N01 | UC-15 | `/api/v1/route/?start=New York, NY` | 400 | `invalid_request`; details.fields has `finish` | 400 invalid_request; error.details.fields {finish} | PASS |
| N02 | UC-15 | `/api/v1/route/?start=&finish=Los Angeles, CA` | 400 | `invalid_request`; details.fields has `start` | 400 invalid_request; error.details.fields {start} | PASS |
| N03 | UC-07 | `/api/v1/route/?start=Chicgo, IL&finish=Houston, TX` | 400 | `unknown_place`; field `start`; query `Chicgo, IL`; suggestions include `Chicago, IL`, at most 5 | 400 unknown_place; error.details.field start; error.details.query Chicgo, IL; error.details.suggestions ["Chicago, IL", "Cisco, IL", "West Chicago, IL", "North Chicago, IL", "Cicero, IL"] | PASS |
| N04 | UC-07 | `/api/v1/route/?start=Dallas, TX&finish=Chicago` | 400 | `unknown_place`; field `finish`; suggestions `["Chicago, IL"]` | 400 unknown_place; error.details.field finish; error.details.suggestions ["Chicago, IL"] | PASS |
| N05 | UC-07 | `/api/v1/route/?start=Dallas, TX&finish=Springfield, ZZ` | 400 | `unknown_place`; field `finish`; at most 5 suggestions | 400 unknown_place; error.details.field finish; error.details.suggestions ["Springfield, AR", "Springfield, CO", "Springfield, GA", "Springfield, ID", "Springfield, IL"] | PASS |
| N06 | UC-08 | `/api/v1/route/?start=Honolulu, HI&finish=Los Angeles, CA` | 422 | `outside_coverage`; field `start`; query `Honolulu, HI` | 422 outside_coverage; error.details.field start; error.details.query Honolulu, HI | PASS |
| N07 | UC-08 | `/api/v1/route/?start=Seattle, WA&finish=Anchorage, AK` | 422 | `outside_coverage`; field `finish` | 422 outside_coverage; error.details.field finish | PASS |
| N08 | UC-08 | `/api/v1/route/?start=Toronto, ON&finish=Buffalo, NY` | 422 | `outside_coverage`; field `start` | 422 outside_coverage; error.details.field start | PASS |
| N09 | UC-16 | `/api/v1/route/?start=Dallas, TX&finish=dallas texas` | 400 | `invalid_request`; details.fields has `finish` | 400 invalid_request; error.details.fields {finish} | PASS |
| N10 | UC-15 | `/api/v1/route/?start=New York, NY&finish=Los Angeles, CA&stop_cost=-1`, then with `101`, `abc`, `nan` | 400 each | `invalid_request`; details.fields has `stop_cost` | 400 invalid_request (all 4); error.details.fields {stop_cost} | PASS |
| N11 | UC-09 | `/api/v1/route/?start=Detroit, MI&finish=Buffalo, NY` | 422 | `route_leaves_usa`; miles_abroad ≈ 252, pass within 2% | 422 route_leaves_usa; error.details.miles_abroad 252.0 | PASS |
| N12 | UC-10 | `/api/v1/route/?start=Los Angeles, CA&finish=Seattle, WA` | 422 | `no_fuel_plan`; gap_start_mile 0.0; gap_miles ≈ 886, pass within 2% | 422 no_fuel_plan; error.details.gap_start_mile 0.0; error.details.gap_miles 885.3 | PASS |
| N13 | UC-17 | POST, then PUT, PATCH, DELETE: `/api/v1/route/?start=New York, NY&finish=Los Angeles, CA` | 405 each | `method_not_allowed`; standard error body | 405 method_not_allowed (all 4) | PASS |
| N14 | UC-17 | `/api/v1/routes/?start=New York, NY&finish=Los Angeles, CA` | 404 | `not_found`; standard error body | 404 not_found | PASS |
| N15 | UC-18 | P01's request repeated with no pause; run last | 429 | `rate_limited` by the 61st at the latest; details.retry_after_seconds above 0 | 429 rate_limited at request 61; error.details.retry_after_seconds 59 | PASS |
| N16 | UC-07 | `/api/v1/route/?start=Chicgo, IL&finish=Nowhere, ZZ` | 400 | `unknown_place`; field `start` | 400 unknown_place; error.details.field start | PASS |
| N17 | UC-15 | `/api/v1/route/?start=Nowhere, ZZ` | 400 | `invalid_request` (the missing finish is found before places are looked up); details.fields has `finish` | 400 invalid_request; error.details.fields {finish} | PASS |
| N18 | UC-08 | `/api/v1/route/?start=Tijuana, Mexico&finish=San Diego, CA` | 422 | `outside_coverage`; field `start` | 422 outside_coverage; error.details.field start | PASS |
| N19 | UC-08 | `/api/v1/route/?start=Miami, FL&finish=San Juan, PR` | 422 | `outside_coverage`; field `finish` | 422 outside_coverage; error.details.field finish | PASS |
| N20 | UC-15 | `/api/v1/route/?start=   &finish=Los Angeles, CA` | 400 | `invalid_request`; details.fields has `start` | 400 invalid_request; error.details.fields {start} | PASS |
| N21 | UC-15 | `/api/v1/route/?start=New York, NY&finish=Los Angeles, CA&stop_cost=100.01`, then with `10.555`, then with `stop_cost=` empty | 400 each | `invalid_request`; details.fields has `stop_cost` | 400 invalid_request (all 3); error.details.fields {stop_cost} | PASS |
| N22 | UC-09 | `/api/v1/route/?start=Detroit, MI&finish=Boston, MA` | 422 | `route_leaves_usa`; miles_abroad ≈ 234, pass within 2% | 422 route_leaves_usa; error.details.miles_abroad 234.0 | PASS |
| N23 | UC-10 | `/api/v1/route/?start=San Francisco, CA&finish=Portland, OR` | 422 | `no_fuel_plan`; gap_start_mile 0.0; gap_miles ≈ 554, pass within 2% | 422 no_fuel_plan; error.details.gap_start_mile 0.0; error.details.gap_miles 549.3 | PASS |
| N24 | UC-15 | `/api/v1/route/` | 400 | `invalid_request`; details.fields has `start` and `finish` | 400 invalid_request; error.details.fields {start, finish} | PASS |
| N25 | UC-16 | `/api/v1/route/?start=New York City, NY&finish=Manhattan, NY` | 400 | `invalid_request`; details.fields has `finish` | 400 invalid_request; error.details.fields {finish} | PASS |
| N26 | UC-07 | `/api/v1/route/?start=75201&finish=Dallas, TX` | 400 | `unknown_place`; field `start` | 400 unknown_place; error.details.field start | PASS |

## 4. Correctness rules

Checked on every successful response: by the verifier in the endpoint tests (VF-01) and by `scripts/live_check.py` on every live 200. Money, gallons and prices are read from the JSON as exact decimals.

1. **R1 Range.** No stretch between consecutive stops' mile markers, or from the last stop to `distance_miles`, is over 500 miles.
2. **R2 Tank.** Walking the stops from mile 0 with an empty tank, adding each stop's gallons and burning 1 gallon per 10 miles, the tank is never below 0 or above 50 gallons, and no purchase is more than 50 gallons.
3. **R3 Gallons.** The stops' gallons add up exactly to `summary.gallons`, which equals `summary.distance_miles` ÷ 10 exactly.
4. **R4 Money.** Each stop's `cost` equals its `gallons` × `price_per_gallon`, rounded half-up to cents. `summary.total_fuel_cost` equals the sum of the costs exactly.
5. **R5 Prices and names.** Each stop's `price_per_gallon` equals, as an exact decimal, the lowest `Retail Price` the CSV lists for its `station_id`. Its `name`, `address`, `city` and `state` equal that row's, with spaces trimmed; on a price tie, the first such row.
6. **R6 Stops.** `fuel_stops[0]` has `kind` `start`, `mile_marker` 0.0, and `lat` and `lng` equal to `summary.start`. Every other stop has `kind` `station`. `order` runs 1, 2, 3… Mile markers strictly increase and stay below `distance_miles`. No `station_id` appears twice. Every stop after the first buys more than 0 gallons; the first buys 0 or more.
7. **R7 Lowest bill.** `lowest_possible_fuel_cost` is not above `total_fuel_cost`, and `lowest_possible_stops` is at least 1. When `assumptions.stop_cost` is 0, the two costs are equal (FR-16).
8. **R8 Stop count.** `summary.stops` equals the number of `fuel_stops`, and is at least `distance_miles` ÷ 500 rounded up.
9. **R9 Assumptions.** `assumptions` is `range_miles` 500, `miles_per_gallon` 10, `tank_gallons` 50, `starting_fuel_gallons` 0, `search_radius_miles` 5, and `stop_cost` equal to the request's, or 10.0 when none was sent.
10. **R10 First fill-up.** `first_fill_distance_miles` is 0 or more. If it is over 25, `warnings` holds exactly one entry, containing `fuel_stops[0].name` and the distance; otherwise `warnings` is `[]`.
11. **R11 Map.** `map` is a GeoJSON FeatureCollection. Feature 0 is a LineString with `kind` `route` and `distance_miles` equal to the summary's. Then one Point per stop, in order, with `kind` `stop` and `order`, `name`, `mile_marker`, `price_per_gallon`, `gallons` and `cost` equal to the stop's, and `title` `order. NAME, City ST`. Then a Point with `kind` `start` at `summary.start` and one with `kind` `finish` at `summary.finish`. Every Point has `title` and `marker-color`. Coordinates are `[lng, lat]`.
12. **R12 Stops on the line.** Each `station` stop's `[lng, lat]` is one of the route line's coordinates. Their positions in the line increase with `order`. The line has a point every half mile of its own length plus its end point, and its markers are scaled to `distance_miles`. So with `n` points its own length is `0.5 × (n − 2)` plus its last stretch along the road, which is at least the straight distance between its last two points and at most 0.5 mile. For a stop at line position `i`, counted from 0, `mile_marker` is within 0.1 mile of `0.5 × i × distance_miles ÷` some such length. (The straight distance alone is not enough: where the road bends in its last half mile it is shorter than the stretch, by 0.22 mile on the recorded Dallas to Phoenix road, and 9 of QB-02's 54 correct answers, on four recorded roads, failed with it.)
13. **R13 Line spacing.** Consecutive route-line points are at most 0.51 miles apart, and no point repeats the one before it, except that the end point may repeat the point before it: the end can fall within a metre of the last half-mile point and be cut to the same 5 decimals, as on every test road of a whole number of miles. The line has `2 × distance_miles + 1` points, within 0.25% or 2 points, whichever is larger. A point every half mile plus the end point can differ from that figure by almost a whole point, and the road's own length differs from the routing service's figure, by up to 0.18% on the recorded roads. R12 takes the line's scale from its number of points, so repeated or extra points would let stops be drawn past their markers (review 10R, R10-02).
14. **R14 Precision.** Every number is a JSON number. Miles have at most 1 decimal, gallons and money at most 2, coordinates at most 5.
15. **R15 Meta.** `routing_calls` is 0, 1 or 2. `cache_hit` true implies `routing_calls` 0. `timings_ms.routing`, `own` and `total` are 0 or more, and `routing` is 0 when `routing_calls` is 0. `routing_server` is `router.project-osrm.org` or `routing.openstreetmap.de`, or a host the verifier's caller names: the end-to-end run names the stand-in, `fake-osrm`.
16. **R16 Labels.** `summary.start.label` and `summary.finish.label` have the form `City, ST`, with ST one of the lower 48 states or DC.
17. **R17 Stations near the road.** Each `station` stop's `[lng, lat]` lies within 5.01 miles of where a station of the stop's `city` and `state` stands: the mean of that city's rows in the places data, or one of its rows. A station stands at the mean of its city's rows, or, for the few cities whose rows are far apart, at one of them (architecture section 6); a stop is drawn at the road point nearest its station, within the 5-mile search radius (D-11); the 0.01 is room for coordinates cut to 5 decimals. The places data is what the verifier's caller gives. By default it is the rows of `data/us_cities.csv`, which the verifier reads itself, and the five places added by hand (architecture section 6), of which it keeps its own copy and which count, as in the application, only where the file has no such city. The endpoint tests give their own places, one where each station they create stands. A city matches as the places table matches it (architecture section 6, rule 4). (Until review 10R, R10-01, R17 allowed 15 miles from any row: a station 9.5 to 12 miles from the road, or a search radius in the wrong units, passed it.)

## 5. Speed checks

Round trip is measured by `scripts/live_check.py` on the same machine as the server, from sending the request to receiving the whole body.

| ID | UC | Requirement | Input | Expected | Actual | Result |
|---|---|---|---|---|---|---|
| S01 | UC-01 | NFR-1 | P01 and P06, each a new trip | meta.timings_ms.own 100 or less; round trip minus meta.timings_ms.routing 100 ms or less | P01's meta.timings_ms.own 28.3; P01's round_trip_ms - timings_ms.routing 42.9; P06's meta.timings_ms.own 36.4; P06's round_trip_ms - timings_ms.routing 47.3 | PASS |
| S02 | UC-04 | NFR-11 | P02 | Round trip under 50 ms; meta.timings_ms.total under 50; routing_calls 0 | P02's round_trip_ms 15.4; P02's meta.timings_ms.total 2.2; P02's meta.routing_calls 0 | PASS |
| S03 | UC-03 | NFR-1, NFR-2 | P03 (road cached, new stop cost) | routing_calls 0; round trip 100 ms or less | P03's meta.routing_calls 0; P03's round_trip_ms 31.7 | PASS |
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
| CT-01 | UC-14 | `docker compose up` in a fresh clone | The database and the API start. The API's log shows the loader's counts, ending with 6,626 stations saved. `GET /api/v1/route/?start=Dallas, TX&finish=Houston, TX` returns 200 | Phase 8, twice: a clone of the local repository and a clone from GitHub, each in an empty folder. Both containers start; the log shows the loader's counts ending `Saved: 6626`, then gunicorn listening. Dallas to Houston returns 200: 239.6 miles, 1 stop, $68.62, routing_calls 1 | PASS |
| CT-02 | UC-14 | `docker compose down`, then `docker compose up` | Starts again; the loader replaces the table without error; still 6,626 stations; P08 returns 200 | Phase 8: `docker compose down`, `docker compose up -d` over the existing data. The log shows `Saved: 6626` with no error; `select count(*)` gives 6,626; Dallas to Houston returns 200 | PASS |
| CT-03 | UC-14 | `scripts/live_check.py` against the Compose stack | Every P and N case passes; S01 to S03 are met | Not run in full against the Compose stack, to stay inside the limit of 100 live routing calls. The full run (49 of 49) was made in Phase 5 against the same code served from source. Against the Compose stack, Phase 6 ran P01, P02, P03, P08, N03, N06, N11, N12 and N14: 9 of 9 passed | PARTIAL |
| CT-04 | UC-14 | P01, then P02, against the Compose stack | P02 reports routing_calls 0 and cache_hit true: the API runs as one process | Phase 6: P02 against the container reports routing_calls 0 and cache_hit true. Phase 8, fresh clone: the repeat of Dallas to Houston reports the same | PASS |
| CT-05 | UC-14 | `docker compose config` | A PostgreSQL 17 image; the API receives `DATABASE_URL` | Image `postgres:17`; the API receives `DATABASE_URL: postgresql://milemarker:milemarker@db:5432/milemarker` | PASS |
| PM-01 | UC-20 | `npx newman run <collection in docs/> --env-var base_url=<API address> --delay-request 1200`, against a freshly started API | Exit code 0; every check passes | Phase 7: 14 requests, 111 assertions, 0 failed, exit code 0. The API was running, not freshly started, so some trips were already cached; the collection's checks do not depend on that | PARTIAL: the API was not freshly started. Run again as written in Phase 14 |
| PM-02 | UC-20 | The collection file | One variable, `base_url`. Folders: 1. Demo (P01, P02, P03, P04); 2. More trips (P05, P06, P08, P10, P11); 3. Errors (N01, N03, N06, N11, N12). Every request has at least one check | One variable, `base_url`. 1. Demo: 4 requests; 2. More trips: 5; 3. Errors: 5; in the order listed. Each request has between 4 and 13 checks | PASS |
| FC-01 | UC-14 | Clone the public repository into an empty folder on a machine with only git and Docker; no `.env`; `docker compose up` | P08 returns 200. Nothing asks for an account or a key | Phase 8: `git clone https://github.com/raziullah7/milemarker-api.git` into an empty folder (24 commits, 145 files, no `.env`), then `docker compose up --build -d`. Dallas to Houston returns 200. Nothing asked for an account or a key. Done on the build machine, which has more than git and Docker installed; the API ran only in its containers | PASS |
| FC-02 | UC-19 | `uv sync`, the Compose database running, `uv run pytest` | Every test passes; none is skipped for want of a network | Phase 8, in the fresh clone: `uv sync`, then `uv run pytest`: 348 passed, 1 deselected (the slow exactness test, by its marker). In a container: 348 passed | PASS |
| FC-03 | UC-19 | `uv run ruff check .` | Exit code 0; no findings | Phase 8, in the fresh clone: `All checks passed!`; `ruff format --check` reports 52 files already formatted | PASS |
| FC-04 | UC-14 | Search the repository for keys and secrets; read `.env.example` | No API key or token. The only password is the local database default in the Compose file. `.env.example` lists `DATABASE_URL`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` | Phase 8: all 145 tracked files searched. No key or token. The only password is `milemarker`, the local database default. `.env.example` lists the three settings and `POSTGRES_PORT` | PASS |
| FC-05 | UC-19 | Only if CI is built (NFR-17): a push to the repository | The workflow runs lint and tests, and the run passes | CI was not built | N/A |
| M01 | UC-11 | P01's `map` pasted into geojson.io | A line from New York to Los Angeles; one marker per stop, labelled with its title, for example `2. NAME, City ST`; a start and a finish marker | Phase 7, in a browser: the line from New York to Los Angeles, seven stop markers with their titles, a start and a finish marker. The line was cut from 5,594 points to 39 to paste it; the stops, start and finish were the real ones | PARTIAL: the full-size map was not pasted. Run again as written in Phase 14 |
| M02 | UC-14 | The README | Covers setup with one command, an example request, and the decisions D-1 to D-15 | One-command setup, an example request with its response, and a table of D-1 to D-15 (all fifteen found by a script) | PASS |
| M03 | — | The Loom video and the hiring-thread message | Video 5 minutes or less: the API in Postman, then the code. Both links sent before Friday 20 Nov 2026, 8 pm, as the message time shows | Left for the candidate | OPEN |
| M04 | UC-19 | Read the code against `backend-architecture.md` sections 3 and 4 | Each module sits in its layer and does only that layer's work; each has a short description at the top | Phase 5: the independent review read every module against both specifications; its one layering finding (the answer builder loading Django) was fixed. A test asserts that the pure modules import nothing from Django | PASS |

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
| 11. Fresh clone, no `.env`: one Compose command starts the database, Redis, the setup, the API and the viewer; the API answers through the proxy at release 1.0's address and has no published port | CF-33, CF-18, CF-21, CF-22, CF-23, PX-01, PX-13 |
| 12. Twenty repeats of one trip are all cache hits, whichever worker answers | CA-20, CA-01 |
| 13. Redis stopped: requests still 200, each worker logs one warning, health reports `fallback`; Redis back: the shared cache returns | CA-21, CA-22, CA-06, CA-10, CA-11, CA-12, HS-04, HS-05 |
| 14. The 61st request in a minute from one client is refused with 429, whatever `X-Forwarded-For` it sends | PX-07, PX-08, HM-07, HM-08 |
| 15. Health answers 200; the OpenAPI document is valid and describes the parameters, the 200 body and every error code; the Swagger page renders | HS-01, HS-19, HS-11 to HS-16, HS-18 |
| 16. `manage.py check --deploy` passes; CI is green on `main` | CF-12, CI-02, CI-07 |
| 17. The end-to-end run passes the Postman collection and the viewer's browser tests while the API has no route to the internet | EE-03, EE-05, EE-06 |
| 18. The viewer plays New York to Los Angeles to its end: the route drawn, one marker per stop, the panel's totals equal to the API's | VB-01, VB-04, VB-05, VB-06 |
| 19. The fallbacks work: reduced motion, no WebGL2 and each API error; the accessibility scan finds no violation | VB-13, VB-14, VB-23, VB-24, VP-06, VB-19 |
| 20. `make help`, `make test`, `make lint` and `make up` work | MK-01, MK-05, MK-02, MK-10 |

## 9. Release 2: test catalogue

The cases below were written before the second release's code, from `requirements.md` (FR-18 to FR-26, NFR-16 to NFR-31, D-15 to D-24, acceptance checks 11 to 20), architecture sections 2, 3, 10, 11, 13, 16, 18 and 19, and the rulings on the two audits of release 1.0 in `docs/plan/PHASE-9.md`. The architecture names the stand-in routing server's file and roads only; its interface is taken from `docs/plan/briefs/phase10-A-harness.md`. The points this catalogue first left open are settled in `docs/plan/PHASE-9.md`, "Points raised by the test design, settled"; a case that cites "row n" follows that table's row. Sections 1 to 8 still hold.

Conventions, in addition to those at the top:

- Cases run by a test suite (`uv run pytest`, or the viewer's unit and component tests) have the columns of section 2. Cases run against a running stack, in a browser, by CI or by hand have the columns of section 7; their **Actual** and **Result** are filled in when they are run.
- "The stack" is the Compose stack of architecture section 18. "The end-to-end stack" is the same with `docker-compose.e2e.yml` on top: the stand-in routing server in place of the public servers, and the API with no route out. A stack case runs on the end-to-end stack unless it says otherwise, so it makes no call to the public routing servers.
- "Through nginx" means at `http://127.0.0.1:8000`, the address release 1.0 used.
- "In the standard shape" means the body `{"error": {"code": …, "message": …, "details": …}}` of EP-39: a non-empty message, and `details` an object.
- P, N and EP numbers name the requests of sections 2.10 and 3.

### 9.1 Test data

| Name | What it is |
|---|---|
| Recordings | The recorded roads in `tests/fixtures/roads/`. The 17 of release 1.0: `bos_dc`, `bos_sea`, `chi_hou`, `dal_hou`, `det_bos`, `det_buf`, `det_porthuron`, `elpaso_delrio`, `houlton_madawaska`, `intlfalls_baudette`, `keywest_miami`, `laredo_brownsville`, `montauk_nyc`, `nyc_la`, `sandiego_calexico`, `sea_blaine`, `sea_mia`. Four more are added in Phase 10 (row 1): Los Angeles to New York, St. Louis to Winston-Salem and Dallas to Phoenix, recorded then, and Los Angeles to Seattle, from the Phase 1 research recordings. Each holds one direction only: `nyc_la` is New York to Los Angeles, and Houston to Dallas is not recorded. |
| `dal_hou` | The recorded Dallas to Houston road: 238.1 miles; first waypoint `[-96.797185, 32.777588]`, second `[-95.36593, 29.765262]`. Asked for from the places table's Dallas (32.790439, −96.80439) and Houston (29.7652, −95.3657), its path coordinates are `-96.80439,32.790439;-95.3657,29.7652`. |
| Live Redis | The stack's Redis, published on 127.0.0.1:6379. The Redis tests use `redis://127.0.0.1:6379/15` and no other database. |
| Refusing Redis | `redis://127.0.0.1:1/15`. Nothing listens there, so every connection is refused at once. |
| Silent Redis | A listener started by the test on 127.0.0.1 that accepts connections, never answers, and counts the connections it receives. It stands for a Redis that hangs. |
| Switchable Redis | A forwarder started by the test on 127.0.0.1, in front of the live Redis. Switched off, it closes each connection at once and counts it; switched on, it passes connections through. |
| Two processes | Two separate Python processes, A and B, standing for two workers. Each has its own fake routing service. |
| Routing-free request | `GET /api/v1/route/?start=Dallas, TX`. It is answered 400 `invalid_request` before any place lookup or routing call, so it serves wherever only the number of requests matters. |
| Viewer answer V1 | A 200 body for the viewer's unit and component tests. Start `New York, NY` (40.7484, −73.9967), finish `Chicago, IL` (41.8781, −87.6244). distance_miles 853.2; gallons 85.32; stops 2; total_fuel_cost 268.04; lowest_possible_fuel_cost 268.04; lowest_possible_stops 2; first_fill_distance_miles 3.1; warnings `[]`; assumptions as AN-07 with stop_cost 10.0. Stop 1: order 1, kind `start`, `DELTA`, Jersey City, NJ, mile_marker 0.0, at the start, price_per_gallon 3.239, gallons 39.15, cost 126.81. Stop 2: order 2, kind `station`, `SHEETZ #639`, Youngstown, OH, mile_marker 391.5, at (41.0998, −80.6495), price_per_gallon 3.059, gallons 46.17, cost 141.23. The route line's coordinates are `[[-73.9967, 40.7484], [-80.6495, 41.0998], [-87.6244, 41.8781]]`. Its figures obey R1 to R4 and R6 to R10. |
| Viewer answer V2 | V1 with first_fill_distance_miles 30.0 and one warning, in the API's words: `The nearest listed fuel station to the start is DELTA in Jersey City, NJ, 30.0 miles away. The first fill-up is priced there.` |
| Error bodies | For each code of the error table in architecture section 11, the API's body with its status: `invalid_request` 400, details.fields `{"finish": ["…"]}`; `unknown_place` 400, as N03's actual result; `not_found` 404; `method_not_allowed` 405; `outside_coverage` 422, field `start`, query `Honolulu, HI`; `route_leaves_usa` 422, miles_abroad 252.0; `no_route` 422; `no_fuel_plan` 422, gap_start_mile 0.0, gap_miles 885.3; `rate_limited` 429, retry_after_seconds 37; `internal_error` 500; `routing_unavailable` 502, reason `timeout`; `stations_not_loaded` 503; `api_unavailable` 503. Each body's `message` is `Message for ` followed by its code and a full stop, for example `Message for no_route.`. A code whose row lists no details has `details` `{}`. |
| Test line T | For the viewer's timeline: a route line of three points, A, B and C, given by its two running totals (row 6). Drawn length, in Web Mercator units scaled up for reading: 0 at A, 3 at B, 7 at C, so the head's positions are A (0, 0), B (3, 0) and C (3, 4). Road miles: 0.0 at A, 100.0 at B, 200.0 at C. The two pieces are equally long on the ground but not as drawn, as when the projection stretches one more than the other. Stop 1 is at A (mile_marker 0.0, cost 126.81), stop 2 at B (mile_marker 100.0, cost 141.23). distance_miles 200.0; total_fuel_cost 268.04. |
| Line M | For the running totals of row 6: a route line of three `[lng, lat]` points, `[[0, 0], [0, 60], [10, 60]]`, with distance_miles 4,000.0: north along the Greenwich meridian to 60° N, then 10° east along 60° N. Web Mercator here is `x = (180 + lng) ÷ 360`, `y = (180 − (180 ÷ π) × ln(tan(π ÷ 4 + lat × π ÷ 360))) ÷ 360`, the map library's own. |

Viewer test IDs. The viewer's tests find elements by role and by these `data-testid` values (row 9). The visible wording of headings and of the fixed sentences is written when the viewer is built and recorded in Phase 12; the tests compare figures and test IDs, not prose.

| Test ID | Element |
|---|---|
| `loading` | The loading state |
| `trip-distance`, `trip-stops`, `trip-total`, `trip-lowest` | The panel's distance, number of stops, total fuel cost and lowest possible bill |
| `trip-warning` | Each warning, in the API's words |
| `assumptions` | The assumptions |
| `stop-card` | Each stop's card, in order. In it: `stop-name`, `stop-place` (city and state), `stop-price`, `stop-gallons`, `stop-cost`, `stop-mile` |
| `stop-start-note` | On stop 1's card only: the sentence that its fuel is priced at the listed station nearest the start and that the stop is drawn at the start |
| `counter-distance`, `counter-cost` | The distance and fuel-cost counters |
| `error` | The error state. In it: an element of role `heading`, one for each code, and `error-message`, the API's own `message` |
| `error-retry` | In a `rate_limited` error: the seconds to wait, from `details.retry_after_seconds` |
| `suggestion` | Each suggestion, of role `link` |
| `example` | Each example trip, of role `link` |
| `skip`, `replay` | Of role `button`, named Skip and Replay |
| `scrubber` | Of role `slider` |
| `static-route`, `no-webgl` | Without WebGL2: the static drawing, and the sentence saying why |
| `credits` | The map's credits |

Figures are shown as row 9 sets: miles with a thousands separator and one decimal, as `2,800.6 mi`; money as `$867.27`; gallons to two decimals, as `39.15`; a price exactly as the API gives it, as `$3.239 / gal`.

### 9.2 Configuration and start-up

Architecture section 18 ("Configuration"), section 12, NFR-20, NFR-21 and NFR-24. Each setting is read in a separate process with only the variables the case names, so the test runner's own additions (it adds `testserver` to the allowed hosts) do not enter.

| ID | UC | Input | Expected |
|---|---|---|---|
| CF-01 | UC-36 | `DJANGO_SECRET_KEY` unset; the settings loaded in two separate processes | Each has a non-empty `SECRET_KEY`, and the two differ: a random key is made at start-up. `config/settings.py` gives no key text as a default (D-21) |
| CF-02 | UC-36 | `DJANGO_SECRET_KEY=cf-02-0123456789-abcdefghijklmnopqrstuvwxyz-0123456789` | `SECRET_KEY` is that text |
| CF-03 | UC-36 | `DJANGO_DEBUG` unset; then `DJANGO_DEBUG=1` | `DEBUG` false; then true. Error answers are JSON either way (EP-36, HM-02) |
| CF-04 | UC-36 | `DJANGO_ALLOWED_HOSTS` unset; then `DJANGO_ALLOWED_HOSTS=api.example,api2.example` | `ALLOWED_HOSTS` is `["localhost", "127.0.0.1", "[::1]"]`; then `["api.example", "api2.example"]`. `"*"` is in neither. The release 1.0 test that forbade the variable is reversed on purpose (architecture section 13) |
| CF-05 | UC-34 | `DJANGO_NUM_PROXIES` unset; then `DJANGO_NUM_PROXIES=1` | `REST_FRAMEWORK["NUM_PROXIES"]` is 0; then 1. Its effect: HM-07, HM-08 |
| CF-06 | UC-36 | `DATABASE_URL` unset | `DATABASES["default"]`: PostgreSQL engine, host `127.0.0.1`, port 5432, name `milemarker`, user `milemarker` |
| CF-07 | UC-33 | `REDIS_URL` unset; then `REDIS_URL=redis://127.0.0.1:6379/15` | Unset: the two caches and the rate-limit counters are the process's own memory, and health reports `memory` (HS-01). Set: they are in that Redis, and health reports `redis` (HS-03) |
| CF-08 | UC-39 | `ROUTING_SERVERS` unset; then `http://127.0.0.1:5000/route/v1/driving/{coords}?overview=full&geometries=geojson`; then that template, a comma, and `http://127.0.0.1:5001/routed-car/route/v1/driving/{coords}?overview=full&geometries=geojson` | The two public templates of PJ-04; then that one template alone; then both, in that order |
| CF-09 | UC-39 | `ROUTING_SERVERS=http://127.0.0.1:5000/route/v1/driving/?overview=full` (no `{coords}`); then a valid template, a comma, and that one | Each time the settings refuse to load with Django's `ImproperlyConfigured`, so the API does not start. Its message contains `ROUTING_SERVERS` and the entry `http://127.0.0.1:5000/route/v1/driving/?overview=full` (row 21) |
| CF-10 | UC-36 | `gunicorn.conf.py` read with `WEB_CONCURRENCY` unset; then with `WEB_CONCURRENCY=3` | 2 worker processes of 4 threads each, eight request slots in all (Q0a-25); then 3 worker processes |
| CF-11 | UC-35 | `LOG_LEVEL` unset; then `LOG_LEVEL=WARNING`. Each time, one message logged at INFO and one at WARNING | Unset: both are written. `WARNING`: only the WARNING message |
| CF-12 | UC-36 | `uv run python manage.py check --deploy`, no variable set | Output "System check identified no issues", with any number silenced; exit code 0. Each entry of `SILENCED_SYSTEM_CHECKS` has a comment beside it giving its reason. `SECURE_HSTS_SECONDS` is 0 and `SECURE_SSL_REDIRECT` is off: they belong to the TLS terminator (D-23) |
| CF-13 | UC-35 | EP-01's request with the header `X-Request-ID: cf-13`; the log lines written while it is answered | Every line about the request carries a time, a level and `cf-13`. The response header `X-Request-ID` is `cf-13` |
| CF-14 | UC-35 | EP-01's request with no `X-Request-ID`; then the same again | Each response carries a non-empty `X-Request-ID`, made by the API; the two differ; each request's log lines carry its own |
| CF-15 | UC-35 | EP-01's request, a new trip, with `X-Request-ID: cf-15` | Exactly one line at INFO from the logger `trips`, carrying a time, the level and `cf-15`, whose message has the form of row 15: `trip start="Dallas, TX" finish="Houston, TX" stop_cost=10 miles=… stops=… total=… routing_calls=1 cache_hit=false own_ms=…`. As numbers, `miles` equals the response's `summary.distance_miles` (990.0), `stops` its `summary.stops` (3), `total` its `summary.total_fuel_cost`, and `own_ms` its `meta.timings_ms.own` |
| CF-16 | UC-36 | `.env.example` | Names `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_NUM_PROXIES`, `DATABASE_URL`, `REDIS_URL`, `ROUTING_SERVERS`, `WEB_CONCURRENCY`, `LOG_LEVEL`, `API_PORT`, `POSTGRES_PORT`, `REDIS_PORT` and `BIND_ADDRESS`, and says for each whether Compose or the API reads it (Q0a-06). It holds no key or token |
| CF-17 | UC-36 | `.gitignore` and `.dockerignore`, asked about `.env`, `.env.local`, `.env.production` and `.env.example` | The first three are ignored by both files; `.env.example` by neither (Q0a-12) |
| CF-34 | UC-39 | `ROUTING_SERVERS=" http://127.0.0.1:5000/route/v1/driving/{coords}?overview=full&geometries=geojson , ,http://127.0.0.1:5001/routed-car/route/v1/driving/{coords}?overview=full&geometries=geojson "` (spaces round the entries, and an empty entry between them) | Exactly the two templates, without the spaces, in that order: entries are trimmed and empty ones dropped (row 21) |
| CF-35 | UC-39 | `ROUTING_SERVERS` set to the empty text; then to `"   "` (spaces only); then to `" , "` | Empty, and spaces only: the two public servers, as when it is not set. `" , "`: the settings refuse to load with `ImproperlyConfigured`, its message containing `ROUTING_SERVERS`, because a value was given and no entry is left (row 21) |
| CF-36 | UC-35 | EP-01's request twice; then EP-15's request (an unknown place) | The repeat logs one INFO line from `trips` as in CF-15, with `routing_calls=0` and `cache_hit=true`: every 200 is logged, cache hits included. EP-15's logs one line at WARNING containing `unknown_place` and none of `miles=`, `stops=` or `total=` (row 15). EP-33's `internal_error` is logged once, in full, at ERROR, with no WARNING line (architecture section 18) |
| CF-37 | UC-39 | `ROUTING_SERVERS` set to three valid templates (ports 5000, 5001 and 5002) | The settings refuse to load with `ImproperlyConfigured`, its message containing `ROUTING_SERVERS` and the count 3: the client tries each server once, and a route may take two calls at most (NFR-2; review 10R, R10-03) |

Against the stack: architecture section 18 ("Services", "Start order", "Stopping", "Images"), NFR-19, NFR-22 and NFR-25, and rulings Q0a-02, Q0a-06, Q0a-11, Q0a-21 and Q0a-25. CF-27, CF-28 and CF-33 use the ordinary stack, CF-27 and CF-28 with a Compose override of `ROUTING_SERVERS`.

| ID | UC | Input | Expected | Actual | Result |
|---|---|---|---|---|---|
| CF-18 | UC-31 | `docker compose config`, no variable set | Published: `web` 8000 on 127.0.0.1; `db` 5432 on 127.0.0.1; `redis` 6379 on 127.0.0.1. `api` and `setup`: none. `api` receives `DATABASE_URL` naming host `db`, `REDIS_URL` naming host `redis`, and `DJANGO_NUM_PROXIES` 1. `db`, `redis`, `api` and `web` have `restart: unless-stopped` (Q0a-11). `api`'s stop grace period is 30 s or more | | |
| CF-19 | UC-36 | `docker compose config` with `API_PORT=8080`, `POSTGRES_PORT=5433`, `REDIS_PORT=6380` and `BIND_ADDRESS=0.0.0.0` | `web` 8080 on 0.0.0.0; `db` 5433 and `redis` 6380, both still on 127.0.0.1 | | |
| CF-20 | UC-36 | A `.env` holding `DJANGO_DEBUG=1`, `LOG_LEVEL=DEBUG`, `WEB_CONCURRENCY=3` and `DJANGO_ALLOWED_HOSTS=api.example`; `docker compose config` | `api`'s environment holds those four values: Compose passes each variable through (Q0a-06) | | |
| CF-21 | UC-36 | `docker compose config`: dependencies and health checks | `setup` waits for `db` healthy; `api` for `setup` completed successfully and for `redis` started, not healthy; `web` for `api` healthy. Health checks: `db` `pg_isready -h 127.0.0.1`; `redis` a ping; `api` a request to `/api/v1/health/` with a 5 s timeout and 6 retries; `web` a request for the viewer's page | | |
| CF-22 | UC-36 | From `docker compose down -v`: `docker compose up --build -d`, with `docker compose events` recorded | `db` is healthy before `setup` starts; `setup` exits 0 before `api` starts; `api` is healthy before `web` starts | | |
| CF-23 | UC-36 | The logs of CF-22 | `setup`: the migrations, then the loader's counts ending with 6,626 saved, then exit code 0. `api`: no migration and no loader count, in either worker | | |
| CF-24 | UC-36 | A Compose override giving `setup` a `DATABASE_URL` that names a database that does not exist; `docker compose up -d` | `setup` exits with a code other than 0; `api` and `web` are not started | | |
| CF-25 | UC-33 | The stack running; `docker compose stop redis`; `docker compose restart api` | `api` starts and becomes healthy without Redis; `GET /api/v1/health/` reports `cache` `fallback` | | |
| CF-26 | UC-36 | `docker compose down`, then `docker compose up -d` | `setup` runs again and replaces the table: 6,626 stations, not 13,252; health reports `stations` 6626 | | |
| CF-27 | UC-36 | `ROUTING_SERVERS` pointed at a server that answers with the `dal_hou` recording after 4 s; P08's request through nginx; `docker compose stop api` 1 s after it is sent | The request ends with 200 and its plan (distance_miles 238.1), not a cut connection. The `api` container exits after that answer, and within 30 s of the stop | | |
| CF-28 | UC-30 | `ROUTING_SERVERS` pointed at two servers that accept the connection and never answer; the requests of P01, P06, P07, P08, P09, P10, P11 and P13, none cached, sent at once, so that they hold every request slot | `api` is never reported unhealthy while they run: the health check's 5 s timeout and 6 retries outlast them (Q0a-25). Each trip ends with 502 `routing_unavailable`, reason `timeout`; health then answers 200 | | |
| CF-29 | UC-36 | The `api` image: its Dockerfile; inside a running container, the files under `/app`, the user, and an attempt to create `/app/x` | Built in stages: the Dockerfile has more than one `FROM`. No `uv` binary, and no `web/`, `docs/` or `tests/` directory: neither the tests nor the recordings, which the test image holds (row 23). The process runs as a user other than root, and creating `/app/x` fails with permission denied (NFR-25) | | |
| CF-30 | UC-36 | `web/node_modules` present in the clone; the `api` image built | The image holds no `node_modules` directory | | |
| CF-31 | UC-36 | Every `FROM` line of the Dockerfiles and every `image:` of the Compose files | Each names its image by digest, `@sha256:…` (Q0a-21) | | |
| CF-32 | UC-31 | The processes inside the running `api` container | One gunicorn master and two worker processes (NFR-19) | | |
| CF-33 | UC-36 | The repository cloned into an empty folder; no `.env`; `docker compose up --build -d`; then through nginx `GET /api/v1/health/`, `GET /` and `GET /api/v1/route/?start=Chicgo, IL&finish=Houston, TX` | `db`, `redis`, `api` and `web` running; `setup` exited 0. Health: 200 `{"status": "ok", "stations": 6626, "cache": "redis"}`. `/`: 200, the viewer's page. The route: 400 `unknown_place` in the standard shape, from the API through nginx. `api` has no published port. Nothing asks for an account, a key or a `.env` (acceptance check 11) | | |

### 9.3 Cache

Architecture section 10, D-15, D-16, D-22 and NFR-18. The Redis tests run against the live Redis's database 15, and against the refusing, silent and switchable Redis of 9.1. The request is EP-01's unless stated. "At T + 30 s" means with the clock moved, not waited for.

| ID | UC | Input | Expected |
|---|---|---|---|
| CA-01 | UC-32 | Two processes on the live Redis. A sends the request; then B sends it | A: routing_calls 1, cache_hit false. B: routing_calls 0, cache_hit true, its fake not called; body without meta identical to A's |
| CA-02 | UC-32 | As CA-01, but B sends the request with `stop_cost=0` | B: routing_calls 0, cache_hit false: the road is shared |
| CA-03 | UC-32 | A caches the answer with `CACHE_KEY_VERSION` n; B, the same code with n + 1, sends the request | B: routing_calls 1, cache_hit false. Nothing cached under version n is used |
| CA-04 | UC-32 | The answer cached. The mile-700 station re-priced from 3.20 to 3.15 in the table, the index rebuilt, and the request sent again. Then the index rebuilt with no change, and the request sent again | After the price change: routing_calls 0 (the road's key holds no fingerprint), cache_hit false, and the mile-700 stop's price_per_gallon 3.15. After the rebuild with no change: cache_hit true: the same data gives the same fingerprint |
| CA-05 | UC-32 | A caches the answer and ends; a new process C, with the same code and data, sends the request | C: cache_hit true, routing_calls 0: the answer outlives the process |
| CA-06 | UC-33 | One process on the refusing Redis; the request twice | Both 200. First: routing_calls 1, body without meta identical to the same request on the in-memory cache. Second: cache_hit true, from the process's own memory |
| CA-07 | UC-33 | One process on the silent Redis, the fake answering at once; the request, timed. The same request timed in a process on the live Redis, up | 200. Its round trip is no more than 0.5 s longer than the one with Redis up (NFR-18, row 14) |
| CA-08 | UC-33 | The silent Redis; 20 requests within 30 s, new trips and repeats | All 200. Requests 2 to 20 make no connection to it and add no time |
| CA-09 | UC-33 | The silent Redis; the process falls back at time T. Requests at T + 1 s, T + 29 s, T + 30 s, T + 59 s and T + 60 s | No connection at T + 1 s or T + 29 s; one at T + 30 s, which fails; none at T + 59 s; one at T + 60 s |
| CA-10 | UC-33 | Process A on the switchable Redis, switched off: A falls back at T. Switched on; B caches the answer in the Redis; A sends the request at T + 30 s | A: cache_hit true, from Redis. A logs one line saying it is back on Redis; health from A reports `redis` |
| CA-11 | UC-33 | The switchable Redis switched off; 10 requests within 30 s; one at T + 30 s, whose try fails; switched on, one request at T + 60 s; switched off again, one request | One WARNING when the process falls back; nothing for the 10 requests or the failed try; one line when it returns; one new WARNING for the second outage |
| CA-12 | UC-33 | Two processes on the switchable Redis; switched off; each answers 5 requests | Two WARNING lines in all, one from each process: each worker logs one warning (acceptance check 13) |
| CA-13 | UC-33 | `REDIS_URL` unset; the request twice | Second: cache_hit true. The live Redis receives no connection; no warning is logged; health reports `memory` |
| CA-14 | UC-34 | Two processes on the live Redis; one client address; 30 routing-free requests to A, 30 to B, then 1 to A | The last is 429 `rate_limited`: the counters are shared |
| CA-15 | UC-34 | Two processes on the refusing Redis; one client address; 61 routing-free requests to A; then 1 to B | A's 61st is 429: the limit still holds during the outage. B's is not 429: during the outage each process counts on its own (D-16) |
| CA-16 | UC-19 | A key `canary` placed in database 0 of the live Redis; then the Redis tests | `canary` is still in database 0. No database other than 15 holds a key the tests wrote |
| CA-17 | UC-19 | `REDIS_URL` set to the live Redis in the environment; `uv run pytest` | Every test outside the Redis tests uses the in-memory cache: database 0's `canary` survives the fixture that clears the cache between tests |
| CA-18 | UC-32 | Live Redis; the request | The road's and the answer's keys each have a time to live of at most 86,400 s and more than 86,000 s |
| CA-19 | UC-32 | Two identical new requests released together; the fake routing service holds each answer 0.5 s | Both 200; the fake counted 2 calls: both are routed (D-22) |
| CA-24 | UC-33 | The cache's Redis client settings; then one cache read against the silent Redis, timed, and its connections counted | Connections time out after 0.1 s, commands after 0.25 s, with no retry (row 14). The read gives up no sooner than 0.25 s, the command timeout, and no later than 0.5 s, row 14's limit, then falls back; the silent Redis received one connection: the read was not retried |

Against the stack:

| ID | UC | Input | Expected | Actual | Result |
|---|---|---|---|---|---|
| CA-20 | UC-32 | The end-to-end stack, Redis just started, the stand-in's log reset; P08's request through nginx, then 20 times more | Each of the 20: cache_hit true, routing_calls 0. The stand-in's log: 1 route request, matched to `dal_hou` (acceptance check 12) | | |
| CA-21 | UC-33 | The end-to-end stack; P08's request; `docker compose stop redis`; 10 requests, P08's and P06's in turn; `GET /api/v1/health/` 4 times; `docker compose logs api` | Every answer 200. Health 200 with `cache` `fallback`. Each worker that answered since the stop has logged exactly one fallback warning; none has logged two | | |
| CA-22 | UC-33 | Continuing CA-21: `docker compose start redis`; 31 s later, health 4 times; then P06's request and 20 repeats | Health reports `redis`. The 20 repeats: cache_hit true, routing_calls 0: the shared cache is back (acceptance check 13) | | |
| CA-23 | UC-33 | `docker compose exec redis redis-cli CONFIG GET` for `maxmemory`, `maxmemory-policy`, `save` and `appendonly` | `268435456` (256 MB), `allkeys-lru`, empty, `no`: memory capped, the least recently used key evicted, nothing kept on disk | | |

### 9.4 Health, schema and docs addresses

Architecture section 11 ("Other addresses"), FR-19, FR-20 and D-20. Unless stated, the small CSV is loaded and `REDIS_URL` is unset.

| ID | UC | Input | Expected |
|---|---|---|---|
| HS-01 | UC-30 | `GET /api/v1/health/` | 200, body exactly `{"status": "ok", "stations": 4, "cache": "memory"}` |
| HS-02 | UC-30 | The real CSV loaded; health | 200; `stations` 6626 |
| HS-03 | UC-30 | `REDIS_URL` set to the live Redis; health | 200; `cache` `redis` |
| HS-04 | UC-30 | `REDIS_URL` set to the refusing Redis; health | 200; `cache` `fallback`; one fallback warning logged |
| HS-05 | UC-30 | One process on the switchable Redis: health; switched off at T; health; switched on; health at T + 10 s and at T + 30 s, the clock moved | `redis`; then `fallback` at once, as health's own cache read finds Redis gone; `fallback` at T + 10 s; `redis` at T + 30 s |
| HS-06 | UC-30 | Empty station table; health; then `load_stations --csv <small CSV>`; health | 503, body `{"error": {"code": "stations_not_loaded", "message": "…", "details": {}}}`. Then 200 with `stations` 4, with no restart |
| HS-07 | UC-30 | The index not yet loaded, the small CSV in the table; health twice | Both 200 with `stations` 4. The first reads the database once, loading the index; the second makes no database query |
| HS-08 | UC-30 | 100 health requests from one client within a minute; then 61 routing-free requests; then health | All 100 health answers 200. Routing-free requests 1 to 60 are not 429 and the 61st is: health was not counted. The last health answer 200: health is never limited |
| HS-09 | UC-29 | 60 routing-free requests from one client within a minute; then `GET /api/v1/schema/`; then `GET /api/v1/docs/` | Both 429 `rate_limited` in the standard shape: only health is exempt |
| HS-10 | UC-30 | POST to `/api/v1/health/`, to `/api/v1/schema/` and to `/api/v1/docs/` | 405 `method_not_allowed` each, in the standard shape |
| HS-11 | UC-29 | `GET /api/v1/schema/` | 200, an OpenAPI document whose `openapi` is `3.0.3`; not the catch-all's 404 |
| HS-12 | UC-29 | HS-11's document: the GET operation on `/api/v1/route/` | Parameters: `start` and `finish` in the query, required, text; `stop_cost` in the query, optional, a number from 0 to 100, default 10 |
| HS-13 | UC-29 | Same operation: its 200 response | A schema naming `summary`, `warnings`, `assumptions`, `fuel_stops`, `map` and `meta`; EP-01's 200 body validates against it |
| HS-14 | UC-29 | Same operation: its error responses; and the document's opening text (`info.description`) | Error responses for exactly 400, 422, 429, 500, 502 and 503, each with the standard shape, naming every code it can carry: 400 `invalid_request`, `unknown_place`; 422 `outside_coverage`, `route_leaves_usa`, `no_route`, `no_fuel_plan`; 429 `rate_limited`; 500 `internal_error`; 502 `routing_unavailable`; 503 `stations_not_loaded`, `api_unavailable`, the last described as sent by the proxy when the API cannot be reached. No 404 and no 405 on the route: the opening text describes `not_found` and `method_not_allowed` instead (row 18). EP-15's 400 body validates against the 400 schema |
| HS-15 | UC-29 | `uv run python manage.py spectacular --validate --fail-on-warn` | Exit code 0; no error, no warning |
| HS-16 | UC-29 | The committed `docs/openapi.yaml` against the document generated from the code; then with one parameter's description changed in `trips/schema.py` alone | Equal; then the test fails |
| HS-17 | UC-29 | `GET /api/v1/docs/` | 200, an HTML page whose script is loaded from a CDN at one exact version: its address names a version number, not `latest` |

Against the stack:

| ID | UC | Input | Expected | Actual | Result |
|---|---|---|---|---|---|
| HS-18 | UC-29 | `http://127.0.0.1:8000/api/v1/docs/` in a browser that can reach the CDN | The page renders: `GET /api/v1/route/` is listed with its three parameters (acceptance check 15) | | |
| HS-19 | UC-30 | The ordinary stack: `GET http://127.0.0.1:8000/api/v1/health/` | 200, `{"status": "ok", "stations": 6626, "cache": "redis"}` (acceptance check 15) | | |

### 9.5 Host checking and middleware

Architecture sections 11 and 12, D-21, and rulings Q0a-03, Q0a-04 and Q0a-24. The Django test client with the `Host` the case names; the default settings unless stated.

| ID | UC | Input | Expected |
|---|---|---|---|
| HM-01 | UC-31 | `GET /api/v1/health/` with `Host` `localhost`, `127.0.0.1`, `[::1]` and `127.0.0.1:8000` | 200 each |
| HM-02 | UC-31 | `Host: evil.example` on `/api/v1/route/?start=Dallas, TX&finish=Houston, TX`, on `/api/v1/health/` and on `/nowhere`, with `DJANGO_DEBUG` off and on | 400 each, `Content-Type: application/json`, body `{"error": {"code": "invalid_request", "message": "…", "details": {}}}`, never an HTML page. Fake not called |
| HM-03 | UC-31 | `DJANGO_ALLOWED_HOSTS=api.example`; health with `Host: api.example`; then with `Host: localhost` | 200; then 400 `invalid_request` with empty details |
| HM-04 | UC-17 | `GET /api/v1/route/?start=Dallas, TX&finish=Houston, TX`; then `GET /api/v1/route?start=Dallas, TX&finish=Houston, TX` | 200 each, no redirect; bodies without meta identical. The slash redirect stays off with `CommonMiddleware` in place |
| HM-05 | UC-17 | `GET /api/v1/routes` and `GET /api/v1/routes/` | 404 `not_found` each, not a redirect |
| HM-06 | UC-31 | `MIDDLEWARE`, `APPEND_SLASH`, and the error handlers of `config/urls.py` | `MIDDLEWARE` holds `django.middleware.security.SecurityMiddleware` and `django.middleware.common.CommonMiddleware`; `APPEND_SLASH` is false. `handler400` is set to a view answering in the error shape; `handler403` is not set, as nothing in the API can answer 403 (row 27) |
| HM-07 | UC-34 | `DJANGO_NUM_PROXIES=1`; 60 routing-free requests with `X-Forwarded-For: 203.0.113.1`; then one with `203.0.113.2`; then one more with `203.0.113.1` | The `203.0.113.2` request is not 429: another client, another bucket (Q0a-04). The last `203.0.113.1` request is 429 |
| HM-08 | UC-34 | `DJANGO_NUM_PROXIES` unset; 61 routing-free requests, each with a different `X-Forwarded-For` | Request 61 is 429: with no proxy trusted the header is ignored, as in EP-34 |
| HM-09 | UC-31 | The body text of a 404 `not_found` and of a 400 `invalid_request` | Both in one compact form: no space after any `:` or `,` outside strings (Q0a-24) |
| HM-10 | UC-31 | The API alone, with no nginx: EP-01's 200, `/nowhere`'s 404, EP-15's 400 and `/api/v1/health/` | Each answer carries, from Django, exactly one `X-Content-Type-Options: nosniff`, one `Referrer-Policy: strict-origin-when-cross-origin` and one `X-Frame-Options: DENY` (row 19) |

### 9.6 The front door, through nginx

Architecture section 18 ("The front door"), NFR-16, NFR-19, NFR-23, D-17, D-23 and D-24. Every request is sent through nginx, on the end-to-end stack.

| ID | UC | Input | Expected | Actual | Result |
|---|---|---|---|---|---|
| PX-01 | UC-31 | `GET http://127.0.0.1:8000/api/v1/route/?start=Dallas, TX&finish=Houston, TX` (P08) | 200 with the plan: labels `Dallas, TX` and `Houston, TX`, distance_miles 238.1 (`dal_hou`), routing_calls 1 | | |
| PX-02 | UC-31 | P01's request with `Accept-Encoding: gzip`; then without it | With it: `Content-Encoding: gzip`, and the body unpacks to the full JSON answer and is smaller than it. Without it: no `Content-Encoding` | | |
| PX-03 | UC-31 | `GET /`, and each JavaScript and CSS file under `/assets/` that the page loads, with `Accept-Encoding: gzip` | `Content-Encoding: gzip` on each (NFR-23) | | |
| PX-04 | UC-35 | P08's request with no `X-Request-ID`, twice; then once with `X-Request-ID: client-1`; `docker compose logs api` | Each response carries a non-empty `X-Request-ID`, made by nginx; the first two differ. The third's is not `client-1`: nginx replaces a client's own (row 16). The API's log lines for each request carry that request's value, and none carries `client-1` | | |
| PX-05 | UC-31 | `/`; one file under `/assets/`; P08's request; `/api/v1/health/`; `/api/v1/schema/`; `/api/v1/docs/`; `/nowhere`; N03's request; a 429 after 60 routing-free requests; `/assets/missing.js`; and, with `api` stopped, P08's request | Every answer, error answers included, carries `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin` and `X-Frame-Options: DENY`, each exactly once. The API's answers carry them from Django (HM-10); the viewer's files and nginx's own answers from nginx, which adds none to an answer it passes through (row 19) | | |
| PX-06 | UC-31 | `/`, `/?start=New York, NY&finish=Los Angeles, CA` and `/api/v1/docs/` | `/` and `/?start=…` carry `Content-Security-Policy`, and its text names `tiles.openfreemap.org` and `gibs.earthdata.nasa.gov`. `/api/v1/docs/` carries none. The policy's full text is recorded in Phase 12 (row 20) | | |
| PX-07 | UC-34 | 61 routing-free requests from one client within a minute, the n-th with `X-Forwarded-For: 198.51.100.n` | Requests 1 to 60: 400 `invalid_request`. Request 61: 429 `rate_limited` in the standard shape, details.retry_after_seconds above 0 (acceptance check 14) | | |
| PX-08 | UC-34 | Client A, as in PX-07, reaches 429; then client B, at another address, sends 61 routing-free requests with `Host: 127.0.0.1:8000` | B's requests 1 to 60: 400, none 429: another client, another bucket (Q0a-04). B's 61st: 429 | | |
| PX-09 | UC-25 | `docker compose stop api`; then P08's request, `/api/v1/health/`, `/api/v1/schema/` and `/nowhere`; then `/` | Each of the first four: 503, `Content-Type: application/json`, body `{"error": {"code": "api_unavailable", "message": "…", "details": {}}}`, never an HTML page (D-24). `/`: 200, the viewer's page | | |
| PX-10 | UC-25 | `docker compose pause api`; P08's request, timed; then `docker compose unpause api` | 503 `api_unavailable` in the standard shape with empty details, answered no sooner than 30 s after the request | | |
| PX-11 | UC-31 | N03's request; then the stand-in's service stopped and P09's request, not yet cached. Each also sent from inside the stack's network straight to `api` | N03: 400 `unknown_place`, the body byte for byte as the API sent it. P09's: 502 `routing_unavailable`, reason `error`, as the API sent it, not replaced by `api_unavailable` | | |
| PX-12 | UC-31 | `/nowhere` and `/api/v2/route/`; then `/assets/missing.js`, a file the viewer does not have | The first two: 404 `not_found` in the standard shape, from the API, as in release 1.0. The third: 404, `Content-Type: application/json`, body `{"error": {"code": "not_found", "message": "…", "details": {}}}`, written by nginx (row 17) | | |
| PX-13 | UC-34 | `docker compose ps` and `docker compose port api 8000` | `api` has no published port; the only published ports are those of CF-18 | | |
| PX-14 | UC-31 | A request whose address is `/api/v1/route/?start=` followed by 100,000 `a` | 400, body `{"error": {"code": "invalid_request", "message": "…", "details": {}}}`, written by nginx | | |
| PX-15 | UC-31 | P08's request with `Host: evil.example`; then with `Host: localhost:8000` | 400 `invalid_request` with empty details, from the API: nginx passed the client's `Host` on. Then 200 | | |
| PX-16 | UC-31 | P08's and N03's requests, each with `Origin: http://other.example` | No `Access-Control-` header on either: the viewer is on the same origin (D-17) | | |
| PX-17 | UC-31 | `http://127.0.0.1:8000/` and P08's request | 200 each, not a redirect to HTTPS; no `Strict-Transport-Security` header (D-23) | | |
| PX-18 | UC-21 | `GET /` and `GET /?start=New York, NY&finish=Los Angeles, CA&stop_cost=10` | 200 each, `text/html`, the same viewer page | | |

### 9.7 The stand-in routing server

`scripts/fake_osrm.py` and `tests/test_fake_osrm.py`. The stand-in is started on a free local port with the recordings of 9.1 unless stated; `<base>` is its address. Path coordinates are `lng,lat;lng,lat`, and every route request carries the query `?overview=full&geometries=geojson`.

| ID | UC | Input | Expected |
|---|---|---|---|
| SI-01 | UC-39 | `GET <base>/route/v1/driving/-96.80439,32.790439;-95.3657,29.7652` | 200; the body is `dal_hou.json.gz` unpacked, byte for byte |
| SI-02 | UC-39 | `GET <base>/routed-car/route/v1/driving/-96.80439,32.790439;-95.3657,29.7652` | The same 200 and body as SI-01: both public paths are served |
| SI-03 | UC-39 | The reverse: `GET <base>/route/v1/driving/-95.3657,29.7652;-96.80439,32.790439` | 400, body with `code` `NoRoute`: Houston to Dallas was not recorded. The routing client reads it as no road, as in RT-08 |
| SI-04 | UC-39 | A pair far from every recording: `GET <base>/route/v1/driving/0,0;1,1` | 400 with `code` `NoRoute` |
| SI-05 | UC-39 | Finish at `dal_hou`'s second waypoint; start 29 miles due north of its first waypoint, `-96.797185,33.197306`; then 31 miles north, `-96.797185,33.226252` | 200 with `dal_hou`; then 400 `NoRoute`: both ends must lie within 30 miles of a recording's |
| SI-06 | UC-39 | `GET <base>/route/v1/driving/abc`; `GET <base>/route/v1/driving/-96.80439,32.790439` (one point); `GET <base>/route/v1/driving/-96.80439,32.790439;north,south` | 400 with `code` `InvalidUrl`, each |
| SI-07 | UC-39 | `POST <base>/_reset`; SI-01's request; SI-03's request, each with the query `?overview=full&geometries=geojson`; `GET <base>/_requests`; `POST <base>/_reset`; `GET <base>/_requests` | First log, as JSON (row 22): `{"count": 2, "requests": [{"path": …, "start": [-96.80439, 32.790439], "finish": [-95.3657, 29.7652], "matched": "dal_hou", "status": 200}, {"path": …, "start": [-95.3657, 29.7652], "finish": [-96.80439, 32.790439], "matched": null, "status": 400}]}`, where the first `path` is exactly `/route/v1/driving/-96.80439,32.790439;-95.3657,29.7652` and the second exactly `/route/v1/driving/-95.3657,29.7652;-96.80439,32.790439`, without the query (review 10R, R10-06). After the reset: `{"count": 0, "requests": []}` |
| SI-08 | UC-39 | `GET <base>/_health` | 200 |
| SI-09 | UC-39 | `ROUTING_SERVERS` set to `<base>/route/v1/driving/{coords}?overview=full&geometries=geojson`; `fetch_route` from Dallas (32.790439, −96.80439) to Houston (29.7652, −95.3657) | A `Route` with distance_miles 238.1, the recording's distance; calls 1 |
| SI-10 | UC-39 | A folder holding only a copy of `dal_hou.json.gz` named `x.json.gz`; the stand-in started with `--roads` naming it; SI-01's request; then New York to Los Angeles, `-73.996705,40.74838;-118.247896,33.973093` | 200 with that recording; then 400 `NoRoute`. Recordings are found in the folder, not named in the code |
| SI-11 | UC-39 | The stand-in started with no option | It listens on port 5000 on every interface (`0.0.0.0`) and reads `tests/fixtures/roads`: SI-01's request on port 5000 answers 200 |
| SI-12 | UC-39 | `GET <base>/nothing`, a path the stand-in does not serve | 400 with `code` `InvalidUrl`, as the real server answers (review 10R, R10-11). The routing client ends a request on it, where a 404 would send it to a second server |

### 9.8 End to end

Architecture section 13 ("Beyond the suite") and NFR-26. The end-to-end stack is started with `docker compose -f docker-compose.yml -f docker-compose.e2e.yml up --build -d`. Before each case Redis is freshly started and the stand-in's log reset, unless stated.

| ID | UC | Input | Expected | Actual | Result |
|---|---|---|---|---|---|
| EE-01 | UC-39 | The end-to-end stack started; its `config` for `api` and `fake-osrm`; health through nginx | Every service running, `setup` exited 0. `api`'s `ROUTING_SERVERS` is the stand-in alone, at the service `fake-osrm`, with no public server in it. `fake-osrm` runs from the test image, which holds the recordings (row 23). Health 200 | | |
| EE-02 | UC-39 | `npx newman run docs/postman/milemarker.postman_collection.json --folder "1. Demo" --env-var base_url=http://127.0.0.1:8000` | Exit code 0, every check passing. The stand-in's log: exactly 1 route request, matched to `nyc_la`: the folder's four requests are one trip, routed once and then answered from the cache | | |
| EE-03 | UC-39 | The whole collection: `npx newman run docs/postman/milemarker.postman_collection.json --env-var base_url=http://127.0.0.1:8000` | Exit code 0, every check passing. The stand-in's log: `count` 8, from P01, P05, P06, P08, P10, P11, N11 and N12, with `matched` `nyc_la`, `sea_mia`, `dal_hou` and `det_buf` for P01, P06, P08 and N11, and for P05, P10, P11 and N12 the recording added for each in Phase 10 (row 1); no `matched` is null. The other 6 requests make none (acceptance check 17) | | |
| EE-04 | UC-39 | `scripts/live_check.py --routing-host fake-osrm` against `http://127.0.0.1:8000`, limited to the cases whose roads are recorded or need none: P01 to P11, P14 to P16, N01 to N22, N24 to N26 | Each meets its expected result in section 3, and every 200 obeys R1 to R17, R15 accepting `fake-osrm` (row 2). The stand-in's log: `count` 11, from P01, P05, P06, P07, P08, P09, P10, P11, N11, N12 and N22; no `matched` is null | | |
| EE-05 | UC-39 | The viewer's browser tests (section 9.11) against `http://127.0.0.1:8000` | Every test passes (acceptance check 17) | | |
| EE-06 | UC-39 | Inside the `api` container: a TCP connection to `router.project-osrm.org` port 443, opened without sending anything; then one to the stand-in's port | The first fails within 5 s: the name does not resolve, or there is no route. The second opens. The API has no route to the internet (acceptance check 17) | | |
| EE-07 | UC-39 | The collection's checks on a 200; then P01's request answered by a stub at `base_url` with P01's answer altered so that stop 1 buys every gallon and the other stops buy none (Q0a-01) | Each 200's checks walk the stops: no leg, nor the last stop to the finish, over 500 miles; the tank between 0 and 50 gallons; mile markers increasing; each cost equal to gallons × price to the cent; one map Point per stop. The altered answer fails P01's checks | | |
| EE-08 | UC-21 | The ordinary stack, with the public routing servers: P01's request through nginx; then the viewer on `/?start=New York, NY&finish=Los Angeles, CA` | One routing call. P01's expected result in section 3; meta.routing_server `router.project-osrm.org` or `routing.openstreetmap.de`; R1 to R17 hold. The viewer plays it to the end with VB-04 to VB-06 holding. It spends one of the remaining public routing calls | | |

### 9.9 The viewer: pure calculations

The timeline of architecture section 19 ("Its parts"): pure functions, with no React, no map library and no network, run by the viewer's unit tests. The inputs are test line T, line M and viewer answer V1. `p` is the head's progress: the fraction of the line's drawn length, in Web Mercator, behind the boundary, from 0 to 1. It is 0 until 8 s, `(t − 8) ÷ 7` from 8 s to 15 s, and 1 after (row 4). Between two line points, drawn length and road miles are both interpolated linearly (row 6). A stop is "shown" when its marker, its card and its cost in the fuel counter are; stop 1 is shown from 8 s (row 5). Numbers compare within 1e-9 unless stated; money compares exactly, to the cent.

| ID | UC | Input | Expected |
|---|---|---|---|
| VT-01 | UC-21 | Line T; the head's position for p = 0, 0.25, 3/7, 0.5 and 1 | (0, 0); (1.75, 0); (3, 0); (3, 0.5); (3, 4) |
| VT-02 | UC-21 | Line T; the drawn position of stop 1 at A, of stop 2 at B, and of the finish at C | 0; 3/7 (0.428571…); 1. Stop 2's is not 0.5, the fraction its mile marker gives (100.0 of 200.0) |
| VT-03 | UC-21 | Line T; p = 0.42, 3/7 and 0.45 | Stop 2 not shown at 0.42; shown at 3/7 and at 0.45: it appears as the head reaches it on the drawn line, before p = 0.5 |
| VT-04 | UC-21 | A line of five points, (0, 0), (1, 0), (2, 0), (3, 0) and (4, 0); stop 1 at the first, stops 2, 3 and 4 at the second, third and fourth; p rising from 0 to 1 in steps of 0.01 | Stops 2, 3 and 4 appear in that order, at p = 0.25, 0.5 and 0.75, each once; none disappears as p rises |
| VT-05 | UC-21 | Line T; road miles at the head for p = 0, 0.25, 3/7, 0.5 and 1 | 0.0; 58.33 (±0.01); 100.0, stop 2's mile_marker exactly; 112.5; 200.0, distance_miles exactly |
| VT-06 | UC-21 | Line T; p from 0 to 1 in steps of 0.001 | Neither the road miles nor the fuel counter ever falls as p rises |
| VT-07 | UC-21 | Line T; the fuel counter at t = 7.9 s, 8 s (p = 0), 9.4 s (p = 0.2), 11 s (p = 3/7) and 15 s (p = 1) | 0.00; 126.81, as stop 1 appears at 8 s; 126.81; 268.04; 268.04, equal to total_fuel_cost. Exactly 268.04, not the 268.03999999999996 that adding the two costs as binary fractions gives |
| VT-08 | UC-21 | Time to progress, for t = 0, 8, 9.4, 11.5, 15 and 16.5 s | p = 0, 0, 0.2, 0.5, 1 and 1: linear between 8 s and 15 s (row 4) |
| VT-09 | UC-21 | V1 at t = 16.5 s, the end, where Skip leads | Distance counter 853.2 and fuel counter 268.04, the API's figures; both stops shown |
| VT-10 | UC-21 | V1 at t = 0, where Replay leads; and at t = 7.9 s | Each: distance counter 0.0 and fuel counter 0.00; no part of the route drawn (p = 0); no stop shown, stop 1 included (row 5) |
| VT-11 | UC-21 | V1's state at t = 12 s computed directly, and reached by scrubbing from t = 16.5 s back to 12 s | The two states are equal |
| VT-12 | UC-21 | A frame at t = 10 s for a line of 10 points, and for one of 5,600 points, with the map module replaced by a stand-in that records what it is asked | The stand-in receives the same three small updates per frame for both lines, and the line's coordinates once per trip, not per frame (NFR-29) |
| VT-13 | UC-21 | Line T at the moments t = 10 s, 11 s, 12.75 s and 15 s | t = 10 s (p = 2/7): head at (2, 0), road miles 66.67 (±0.01), fuel counter 126.81, stop 2 not shown. t = 11 s (p = 3/7): head at (3, 0), 100.0, 268.04, stop 2 shown. t = 12.75 s (p = 4.75/7): head at (3, 1.75), 143.75, 268.04. t = 15 s: head at (3, 4), 200.0, 268.04 |
| VT-14 | UC-21 | Line M: the two running totals at its three points; the drawn position of a stop at `[0, 60]`; the road miles at p = 0.5 and p = 0.95 | Road miles, by the great-circle formula and scaled so the last is distance_miles: 0.0, 3,692.578211, 4,000.0 (±1e-6). Drawn length in Web Mercator: 0, 0.209600359, 0.237378137 (±1e-9). The stop's drawn position is 0.882981 (±1e-6), though its mile fraction is 0.923145, so it appears at t = 14.180866 s (±1e-6). Road miles at p = 0.5: 2,090.972887; at p = 0.95: 3,868.644619 (±1e-6) (row 6) |
| VT-15 | UC-21 | V1, the intro cancelled at t = 1 s | The state is the finished state of VT-09: counters 853.2 and 268.04, both stops shown (row 7) |

### 9.10 The viewer: the panel and its states

Component tests (architecture section 13): the panel's React components, with the map module replaced by a stand-in that records what it is asked, and the API's answer supplied by the test. Elements are found by role and by the test IDs of 9.1, and figures are compared in the formats row 9 sets. A heading's or a fixed sentence's wording is recorded in Phase 12 and not compared here.

| ID | UC | Input | Expected |
|---|---|---|---|
| VP-01 | UC-21 | The API's answer not yet arrived | `loading` shown; no `trip-` element, no `stop-card` and no `error` |
| VP-02 | UC-21 | V1 | `trip-distance` `853.2 mi`; `trip-stops` `2`; `trip-total` `$268.04`; `trip-lowest` `$268.04`; no `trip-warning`; `assumptions` showing V1's six values (500, 10, 50, 0, 10.0, 5), compared as numbers. Two `stop-card`s, in order. First: `stop-name` `DELTA`; `stop-place` holding `Jersey City` and `NJ`; `stop-price` `$3.239 / gal`; `stop-gallons` `39.15`; `stop-cost` `$126.81`; `stop-mile` `0.0 mi`. Second: `SHEETZ #639`; `Youngstown` and `OH`; `$3.059 / gal`; `46.17`; `$141.23`; `391.5 mi` |
| VP-03 | UC-21 | V1 | `stop-start-note` on the first `stop-card` and on no other (Q0a-15). Its wording, that the fuel is priced at the listed station nearest the start and the stop is drawn at the start, is recorded in Phase 12 |
| VP-04 | UC-21 | V2 | One `trip-warning`, its text exactly V2's warning |
| VP-05 | UC-21 | V1 with stop 2's price_per_gallon 3.00733333, gallons 2.50 and cost 7.52; and with total_fuel_cost set to 999.99 | Stop 2's `stop-price` `$3.00733333 / gal`, every digit as sent; `stop-gallons` `2.50`; `stop-cost` `$7.52`. `trip-total` `$999.99`: the panel shows the API's figure and does not add the costs itself |
| VP-06 | UC-24 | Each of the 13 error bodies of 9.1 | Each: `error` shown, holding an element of role `heading` and `error-message` whose text is the body's `message`, as `Message for no_route.`. The 13 headings differ from one another; their wording is recorded in Phase 12 (row 9). No `trip-` element, no `stop-card`, no route given to the map stand-in |
| VP-07 | UC-23 | Address `/?start=Chicgo, IL&finish=Houston, TX&stop_cost=10`; the unknown_place body of N03's actual result: field `start`, suggestions `Chicago, IL`, `Cisco, IL`, `West Chicago, IL`, `North Chicago, IL`, `Cicero, IL` | Five `suggestion` links (role `link`), in that order. Each link's parameters, decoded: `start` the suggestion, `finish` `Houston, TX`, `stop_cost` `10` |
| VP-08 | UC-23 | Address `/?start=Dallas, TX&finish=Houstn, TX`; unknown_place with field `finish` and suggestions `["Houston, TX"]` | One `suggestion` link, with `start` `Dallas, TX`, `finish` `Houston, TX`, and no `stop_cost`, as the address had none |
| VP-09 | UC-23 | unknown_place with suggestions `[]` | `error` with its heading and `error-message`, and no `suggestion` |
| VP-10 | UC-24 | rate_limited with details.retry_after_seconds 37 | `error` with its heading and `error-message`, and `error-retry` showing `37` |
| VP-11 | UC-25 | The api_unavailable body (503); then a request that fails with no answer at all | First: `error` with the `api_unavailable` heading and `error-message` `Message for api_unavailable.`. Then: `error` with a heading saying the API cannot be reached, and no `error-message`, as no answer came. Neither shows a `trip-` element |
| VP-12 | UC-21 | Address `/?start=Dallas, TX&finish=Houston, TX&stop_cost=5` | Exactly one request: `GET /api/v1/route/` on the page's own origin, with `start` `Dallas, TX`, `finish` `Houston, TX` and `stop_cost` `5`. Skip and Replay send no further request |
| VP-13 | UC-22 | Address `/` | No request to the API. The globe, and three `example` links whose parameters, decoded, are `start` `New York, NY` and `finish` `Los Angeles, CA`; `Seattle, WA` and `Miami, FL`; `Dallas, TX` and `Houston, TX` |
| VP-14 | UC-22 | Each state: bare, loading, V1, an error, suggestions | No `form` element, no text field and no `textarea` in any (D-19) |
| VP-15 | UC-21 | V1; stop 2's card chosen with a click, then with the keyboard (focus and Enter) | Each time the map stand-in is asked once to fly to (41.0998, −80.6495), stop 2's position |
| VP-16 | UC-21 | V1 | The map stand-in is given the coordinates of `map.features[0]` unchanged, once, and a marker for each stop at its `lat` and `lng` (D-2) |
| VP-17 | UC-21 | V1, during the animation; then at its end | During: `skip`, a button named Skip. At the end: `replay`, a button named Replay, and `scrubber`, of role `slider` |
| VP-18 | UC-24 | Address `/?start=Dallas, TX`, the API answering 400 `invalid_request` with details.fields `{"finish": ["…"]}` and message `Message for invalid_request.`; then `/?finish=Houston, TX`, answered likewise for `start`; then `/?stop_cost=5` | The first two: one request each, carrying only the parameter the address has; `error` with the `invalid_request` heading and the API's message; no `example`. The third, with neither `start` nor `finish`: no request; the globe and the three `example` links (row 8) |
| VP-19 | UC-21 | V1 with distance_miles 2800.6 and stop 2's mile_marker 1353.6, at the end of the animation | `trip-distance` `2,800.6 mi`; stop 2's `stop-mile` `1,353.6 mi`; `counter-distance` `2,800.6 mi` and `counter-cost` `$268.04`: a thousands separator in miles (row 9) |

### 9.11 The viewer in a browser

Playwright, headless, through nginx on the end-to-end stack (architecture section 13). The map draws on the built-in outlines: the test answers every request to the map servers itself, as each case says, and none reaches them. A case run "to the end" waits for the animation's finished state, about 16.5 s.

| ID | UC | Input | Expected | Actual | Result |
|---|---|---|---|---|---|
| VB-01 | UC-21 | `/?start=New York, NY&finish=Los Angeles, CA&stop_cost=10`, run to the end; map server requests refused | VB-04, VB-05 and VB-06 hold; the scrubber is shown; the finish marker is shown (acceptance check 18) | | |
| VB-02 | UC-22 | `/?start=Seattle, WA&finish=Miami, FL`, run to the end; map server requests refused | As VB-01 | | |
| VB-03 | UC-22 | `/?start=Dallas, TX&finish=Houston, TX`, run to the end; map server requests refused | As VB-01 | | |
| VB-04 | UC-21 | The finished state of VB-01 to VB-03: ten route points spread along the line, projected to the screen, and the canvas pixel at each | Each pixel has the drawn route's colour, within a tolerance for smoothing: the route is drawn. The colour and the tolerance are recorded in Phase 12 (row 10) | | |
| VB-05 | UC-21 | Same | One stop marker for each entry of `fuel_stops`, each at its stop's `lat` and `lng` | | |
| VB-06 | UC-21 | Same; the API's answer read from the page's own request | `trip-distance`, `trip-stops`, `trip-total` and `trip-lowest`, read as numbers, equal the answer's `summary.distance_miles`, `stops`, `total_fuel_cost` and `lowest_possible_fuel_cost`; each `stop-card`'s figures equal its stop's | | |
| VB-07 | UC-21 | VB-01's finished state, as a screenshot | Matches the stored screenshot within a tolerance. The screenshot and the tolerance are recorded in Phase 12 (row 10) | | |
| VB-08 | UC-21 | VB-01's address; Skip at t = 2 s | The finished state at once: VB-05 and VB-06 hold, and the scrubber is shown | | |
| VB-09 | UC-21 | VB-01's finished state; Replay | Back to the start: no stop marker at all, `counter-distance` `0.0 mi`, `counter-cost` `$0.00`. Stop 1 appears at 8 s (row 5). It plays to the end again, and no new request reaches the API | | |
| VB-10 | UC-21 | VB-01's finished state; the scrubber dragged to its start, to its end, and to the moment the head reaches stop 3 | Start: no stop marker at all, `counter-distance` `0.0 mi`. End: the finished state. Stop 3's moment: the markers of stops 1 to 3 shown and no later one; `counter-distance` at stop 3's mile_marker | | |
| VB-11 | UC-21 | VB-01's address; at t = 1 s, in four separate loads: a press on the map; a wheel turn over it; a touch, with touch emulated; the Escape key | Each time the trip is shown finished at once, as after Skip: VB-05 and VB-06 hold and the scrubber is shown. The camera stays where the gesture leaves it: its centre and zoom 2 s after the gesture ends are those at its end (row 7). A drag on the map then pans it | | |
| VB-12 | UC-21 | VB-01's finished state; stop 3's card chosen | After the flight the map's centre is stop 3's position, to 3 decimals | | |
| VB-13 | UC-26 | VB-01's address with reduced motion requested (`prefers-reduced-motion: reduce`) | Within 1 s of the answer arriving: the finished state, with VB-05, VB-06 and the scrubber. Two screenshots taken 1 s apart are identical: the camera does not move | | |
| VB-14 | UC-27 | VB-01's address in a browser with WebGL turned off | `static-route`, the static drawing; the panel with VB-06's figures; `no-webgl`, the sentence saying why, its wording recorded in Phase 12. No `error`. `credits` names Natural Earth, and neither NASA GIBS nor OpenFreeMap (row 13) | | |
| VB-15 | UC-28 | VB-01's address with every request to OpenFreeMap and NASA GIBS held without an answer | After 4 s the viewer goes on with the built-in outlines alone: land and state outlines are drawn; the route is drawn (VB-04); it plays to the end | | |
| VB-16 | UC-28 | VB-01's address with the remote map's description answered by the test from a copy, and every tile request answered 500 | The failed tiles are not drawn and the outlines show beneath; it plays to the end; the panel shows no error | | |
| VB-17 | UC-21 | Each state: bare; loading; VB-01's finished state; an error (N03's address); outlines only (VB-15); no WebGL2 (VB-14) | `credits` is on screen and expanded in each, and names the sources in use (row 13). The built-in outlines are always the bottom layer, so Natural Earth is named in every state. With the outlines alone, as in every case of this section but VB-16 and VB-27, and without WebGL2, it is the only source named. With the remote map in use (VB-27), NASA GIBS, OpenFreeMap, OpenMapTiles and OpenStreetMap are named as well. The exact wording and links are recorded in Phase 12 (FR-26) | | |
| VB-18 | UC-21 | Keyboard only, from page load, in Playwright and by hand, in each state: bare; VB-01 during play and finished; N03's address | Tab reaches every control: the three example links, Skip, Replay, the scrubber, each stop card, each suggestion link and the credit links. Enter or Space works each; the arrow keys move the scrubber (NFR-28) | | |
| VB-19 | UC-24 | The axe accessibility scan in each state: bare; loading; VB-01 finished; each error state of VB-23; suggestions; reduced motion; no WebGL2 | No violation in any (acceptance check 19) | | |
| VB-20 | UC-21 | The console during every case of this section | No content security policy violation is reported; the viewer's page was served with the policy (PX-06) | | |
| VB-21 | UC-21 | VB-01's address with a device pixel ratio of 3 | The map canvas's drawing buffer is twice its displayed width and height: pixel density capped at 2 (NFR-29) | | |
| VB-22 | UC-21 | While the route draws: the map library's update calls per frame for VB-01 (about 5,600 points) and for VB-03 | The same number of updates per frame for both, and the route's coordinates given to the map once per trip (NFR-29) | | |
| VB-23 | UC-24 | VB-01's address, the API request answered by the test with each of the 13 error bodies of 9.1 | Each: `error` with its code's heading and `error-message` the body's `message`, as in VP-06; no route and no stop marker drawn (acceptance check 19) | | |
| VB-24 | UC-23 | `/?start=Chicgo, IL&finish=Houston, TX`, then its `Chicago, IL` link; `/?start=Houston, TX&finish=Dallas, TX` (not recorded); `/?start=Honolulu, HI&finish=Los Angeles, CA`; `/?start=Detroit, MI&finish=Buffalo, NY`; P08's address with `api` stopped; `/?start=Boston, MA&finish=Washington, DC`, not yet cached, with the stand-in stopped | `unknown_place` with five suggestion links; the link opens `/?start=Chicago, IL&finish=Houston, TX`, which plays to the end (`chi_hou`). Then `no_route`; `outside_coverage`; `route_leaves_usa`; `api_unavailable`, said plainly; `routing_unavailable`. Each as `error` with its code's heading and the API's own `message` in `error-message` (acceptance check 19) | | |
| VB-25 | UC-22 | `/` | The globe turning and the three examples of VP-13; no request to `/api/v1/route/`. Choosing Seattle, WA to Miami, FL opens its address and plays it to the end | | |
| VB-26 | UC-21 | The requests the page sends: on VB-01's address, run to the end, with Replay and a card chosen; on `/` | One request to `/api/v1/route/` for the trip; none for `/` | | |
| VB-27 | UC-28 | By hand, in a browser that can reach the map servers: the ordinary stack through nginx, VB-01's address, after EE-08 so that the trip comes from the cache | The night imagery on the globe, then the vector road map as the camera comes down; the credits shown; no content security policy violation in the console | | |
| VB-28 | UC-28 | The requests the browser makes during every case of this section but VB-27 | None reaches `tiles.openfreemap.org` or `gibs.earthdata.nasa.gov`: the tests depend on no map server | | |
| VB-29 | UC-22 | `/` with reduced motion requested | The three `example` links; two screenshots taken 1 s apart are identical: the globe does not turn (row 11) | | |
| VB-30 | UC-28 | VB-01's address, the remote map's description held and then answered by the test from a copy 6 s after it was asked for | At 4 s the viewer goes on with the built-in outlines alone. The late description is ignored for that page view: no tile is asked for after it arrives, and the trip plays to the end on the outlines (row 12) | | |

### 9.12 Makefile, CI and the repository

Architecture section 18 ("Commands") and section 13 (CI), NFR-17, NFR-27, NFR-28, NFR-30 and NFR-31. The targets are those of brief 10B, which row 25 makes binding over the architecture's table; `web-dev` comes with the viewer, in Phase 12. A target is run in the clone's root. "Under each shell" means once under Git Bash, once under PowerShell and once on Linux. `make live` calls the public routing servers, so it is checked with `make -n`, which prints its command without running it.

| ID | UC | Input | Expected | Actual | Result |
|---|---|---|---|---|---|
| MK-01 | UC-37 | `make help`, under each shell | Exit code 0. One line for each target with what it does: `help`, `up`, `down`, `logs`, `ps`, `dev`, `web-dev`, `migrate`, `load`, `shell`, `test`, `test-slow`, `test-docker`, `coverage`, `lint`, `format`, `typecheck`, `audit`, `check`, `e2e-up`, `e2e-down`, `e2e`, `live`, `clean`. The list is written as plain lines, so it needs no `grep`, `awk` or `sed` (acceptance check 20) | | |
| MK-02 | UC-37 | `make lint` under each shell on the clean tree; then with an unused import added to `trips/views.py` | Exit code 0; then not 0, with Ruff's finding naming the file (acceptance check 20) | | |
| MK-03 | UC-37 | A file with a formatting fault; `make format`; then `make lint` | The file is reformatted; `make lint` exits 0 | | |
| MK-04 | UC-37 | `make typecheck` | Exit code 0; the Django-free modules of architecture section 3 are checked | | |
| MK-05 | UC-37 | `make test` under each shell, with the database running | Exit code 0; every test passes (acceptance check 20) | | |
| MK-06 | UC-37 | `make test-slow` | Exit code 0: the slow exactness test passes | | |
| MK-07 | UC-37 | `make test-docker` | The suite runs in a container; exit code 0 | | |
| MK-08 | UC-37 | `make coverage` | A coverage report with a total; exit code 0 when the total is at or above the floor in `pyproject.toml`, not 0 below it | | |
| MK-09 | UC-37 | `make check`; then with one failing test added | Runs `lint`, `typecheck` and `test`, in that order; exit code 0; then not 0 | | |
| MK-10 | UC-37 | From `docker compose down -v`: `make up` | The stack is built and started in the background, as in CF-22; `GET http://127.0.0.1:8000/api/v1/health/` answers 200 (acceptance check 20) | | |
| MK-11 | UC-37 | `make ps`; `make logs` | The services and their states; then the API's log, followed as it grows | | |
| MK-12 | UC-37 | `make down` | Every service stopped; the database volume kept | | |
| MK-13 | UC-37 | `make clean` | Every service stopped; the volumes deleted | | |
| MK-14 | UC-37 | `make dev`, the database volume already holding the stations | The `db` container up; the API from source with reload on port 8001, so `GET http://127.0.0.1:8001/api/v1/health/` answers 200 with `cache` `memory`, as `REDIS_URL` is unset; a saved change to a Python file restarts it (row 25) | | |
| MK-15 | UC-37 | `make web-dev`, with the API running from source | The viewer's dev server answers its page; `GET /api/v1/health/` sent to the dev server is answered by the API | | |
| MK-16 | UC-39 | `make e2e-up` | The end-to-end stack is started, as in EE-01 (row 25) | | |
| MK-20 | UC-39 | `make e2e`, with the end-to-end stack running | Newman runs the whole Postman collection against it, as in EE-03, and, from Phase 12, the viewer's browser tests, as in EE-05; exit code 0; no request to the public routing servers | | |
| MK-21 | UC-39 | `make e2e-down` | The end-to-end stack is stopped | | |
| MK-22 | UC-37 | `make audit` | Runs `pip-audit` on the locked Python dependencies; exit code 0 when none has a known fault | | |
| MK-17 | UC-37 | `make -n live` | Prints the command that runs `scripts/live_check.py` against the stack's address. Its line in `make help` says it uses the public routing server | | |
| MK-18 | UC-37 | `make migrate`, `make load` and `make shell`, from source with the database running | Migrations applied, exit code 0; the loader's counts ending with 6,626 saved; a Django shell opens | | |
| MK-19 | UC-37 | The README | Each target of `make help` appears with the plain command beside it, for anyone without make (NFR-30) | | |
| CI-01 | UC-38 | `.github/workflows/ci.yml` | It runs on every push and every pull request (NFR-17) | | |
| CI-02 | UC-38 | A push to `next` | The run holds: Ruff's check; Ruff's format check; the type check; the suite with coverage against its floor; `manage.py check --deploy`; the migration check; `pip-audit`; the image build; the end-to-end run (EE-02 to EE-06); and the viewer's lint, type check, unit tests, build and `npm audit --omit=dev --audit-level=high`. Every step passes; the run is green | | |
| CI-03 | UC-38 | On a throwaway branch, one change at a time, each pushed: a Ruff finding; an unformatted file; a type error in `trips/services/fuel.py`; a failing test; a test removed so that coverage falls below the floor; a model field added with no migration; a check removed from `SILENCED_SYSTEM_CHECKS`; a Python package pinned at a version with a known fault | Each run fails at the step for that check: lint; format; type check; tests; coverage; migration check; deploy check; audit | | |
| CI-04 | UC-38 | A Dockerfile that does not build | The run fails at the image build | | |
| CI-05 | UC-38 | A Postman check broken; separately, a collection request whose trip has no recording | The run fails at the end-to-end run: the first at Newman, the second at the check that every request in the stand-in's log was matched | | |
| CI-06 | UC-38 | In `web/`, one at a time: an ESLint finding; a TypeScript error; a failing unit test; a build error; a dependency with a high-severity advisory | Each run fails at the viewer's lint; type check; unit tests; build; audit | | |
| CI-07 | UC-38 | `main`, after `next` is merged into it | Its latest CI run is green (acceptance check 16) | | |
| RP-01 | UC-38 | `LICENSE` and `data/README.md` | `LICENSE` is the MIT licence, for the code. `data/README.md` states each data file's own terms (NFR-31) | | |
| RP-02 | UC-36 | The README | States every decision, D-1 to D-24 | | |
| RP-03 | UC-38 | `.github/dependabot.yml` | Proposes updates for the Python packages, the images, the GitHub actions and the viewer's packages | | |
| RP-04 | UC-38 | `.pre-commit-config.yaml`; `pre-commit run --all-files` on the clean tree; then a commit of a file with a Ruff finding | The hooks are Ruff's checks, Ruff's formatter and the file hygiene hooks (row 24), and leave `data/` and `*.gz` files alone. The run exits 0. The commit is refused, naming the finding | | |
| RP-05 | UC-38 | `pyproject.toml` | Holds a coverage floor: a whole per cent, the coverage measured in Phase 10 rounded down | | |
| RP-06 | UC-38 | `web/tsconfig.json`; in `web/`, `npx tsc --noEmit` and `npx eslint .` | `strict` is true; both exit 0 (NFR-28) | | |

### 9.13 Fixes from the second audit

One case for each fix ruled in the table "QA-0b" of `docs/plan/PHASE-9.md`, with the wrong input the fix must catch. "The New York answer" is the answer for the recorded New York to Los Angeles road at stop cost 10, built as in the regression tests and checked against the real CSV. R6, R12 and R17 are as written in section 4. The routing cases use the start, finish and "OK answer" of section 2.9.

| ID | UC | Input | Expected |
|---|---|---|---|
| QB-01 | UC-19 | Q0b-1. The New York answer with stop 3 (Utica, IL, 2.969) given the station 66341 (Harrold, TX, 2.68733333), 742 miles away: its `station_id`, name, address, city, state and price changed; its point on the line, mile marker and gallons kept; its cost, `total_fuel_cost`, `lowest_possible_fuel_cost` (lowered to the new total) and its map Point made to agree | R17 is reported, and no other rule |
| QB-02 | UC-19 | Q0b-1 and Q0b-2. The verifier over the answer for each of the 18 recorded roads that stay in the USA and have a fuel plan, at stop costs 0, 10 and 25: the 15 of GE-16, and Los Angeles to New York, St. Louis to Winston-Salem and Dallas to Phoenix of Phase 10 (Los Angeles to Seattle has no fuel plan) | No rule fails, R17 and the new R6 and R12 included |
| QB-03 | UC-19 | Q0b-2. The New York answer with stop 4's `lat` and `lng`, and its map Point, moved 17 points further along the route line, about 8.5 miles; its `mile_marker` kept | R12 is reported |
| QB-04 | UC-12 | Q0b-3. Server 1 answers 302, with a `Location` header; separately, 403; separately, 404. Server 2 gives the OK answer each time | A `Route` from server 2 each time: server `routing.openstreetmap.de`, calls 2 |
| QB-05 | UC-12 | Q0b-3. Server 1 answers 204, 301, 307, 408, 410 and 451, each in its own test; server 2 the OK answer | Retried each time; calls 2 |
| QB-06 | UC-12 | Q0b-3. Server 1 answers 400 with `{"code": "InvalidQuery", "message": "…"}` | `RoutingUnavailable`, reason `error`; calls 1; server 2 never called: a 400 that is not "no road" means the request itself is wrong. RT-08 still holds for a 400 with `NoRoute` |
| QB-07 | UC-03 | Q0b-4. `build_answer` with the plan's and the free-stops purchases both (0, 10.004), (1, 0.004), (2, 9.992), at prices [3.00, 3.00, 3.00]; distance 200.0; stop cost 0 | Shown gallons [10.00, 0.01, 9.99]; costs [30.00, 0.03, 29.97]; total_fuel_cost and lowest_possible_fuel_cost 60.00; stops 3 and lowest_possible_stops 3, both counted from the shown gallons |
| QB-08 | UC-19 | Q0b-5. The New York answer with one more stop between stops 2 and 3: a station along the road that the plan does not use, at its own road point, buying 0.00 gallons at cost 0.00; orders renumbered, `summary.stops` one higher, a map Point added | R6 is reported, and no other rule |
| QB-09 | UC-19 | Q0b-5. The New York answer with stop 3 buying −0.01 gallons at cost −0.03, stop 4 buying 0.01 gallons more, and costs and total made to agree. Then the review's own case: the New York to Los Angeles answer at stop cost 0, stop 15 (1.75 gallons) buying −0.01 instead and stop 16 buying 1.76 more, costs, total and lowest bill made to agree | R6 is among the rules reported; then R6 is reported, and no other rule |
| QB-10 | UC-19 | N1. The description at the top of `tests/verify.py` | Says that the verifier checks that a plan is consistent and possible, not that it is the cheapest, and names the exactness tests (EX-01 to EX-04) as what checks that |
| QB-11 | UC-12 | N4. The comment beside `ROUTING_DEADLINE_SECONDS` in `config/settings.py` | Says what architecture section 9 says: an attempt can run to about twice the deadline. It no longer says the deadline runs "to reading the last byte" |
| QB-12 | UC-08 | N5. `resolve()` on `Mexico, USA`; on `Mexico`; on `Tijuana Mexico` | `UnknownPlace`, with exactly the suggestions `Mexico, IN`, `Mexico, ME`, `Mexico, MO`, `Mexico, NY` and `Mexico, PA`, in any order; `OutsideCoverage`; `OutsideCoverage` |
| QB-13 | UC-03 | N7 (a). `build_answer`: the plan buys (0, 30.000) at 3.50; the free-stops purchases are (0, 10.001), (1, 0.003), (2, 10.002), (3, 9.994) at [3.50, 3.20, 3.00, 2.00]; distance 300.0. The tiny purchase comes after the start, because the start is always counted (QB-22) | lowest_possible_fuel_cost 85.01 (shown gallons 10.00, 0.00, 10.01, 9.99; costs 35.00, 0.00, 30.03, 19.98); lowest_possible_stops 3. A builder that dropped the 0.003-gallon purchase would give 85.00 (gallons 10.00, 10.00, 10.00), and one that counted it would give 4 stops, so both halves of AN-11 can fail |
| QB-14 | UC-19 | N7 (b). The answer test named for the correctness rules, on its own input | It passes the whole answer to `verify_response` and requires `[]`, so every rule is checked, not the nine it checked before |
| QB-15 | UC-19 | N7 (c). The regression pins, for the New York answer | Pinned stop by stop: each stop's `station_id`, `mile_marker`, `gallons` and `cost`, as exact values, beside the summary pins. The values are those the release produces, recorded when the test is written (row 26). Any change fails it: moving 0.01 gallons from one stop to the next is one such change |
| QB-16 | UC-12 | N8. Two threads ask for the shared HTTP client at once, on first use, with its creation slowed so that both are inside it together | Both get the same client; one client is created |
| QB-17 | UC-13 | N8. Two threads call `get_index()` at once, on first use, with the read slowed in the same way | Both get the same index; the database is read once |
| QB-18 | UC-19 | Review 10R, R10-01. The New York answer with stop 2, 3, 4 or 5, each in its own test, given the nearest station the plan does not use that is 9.5 to 12 miles from the stop's point on the line (Lowellville OH, Tonica IL, York NE, Hudson CO); its point, marker and gallons kept, every other figure made to agree. Separately, QB-02's answers | R17 is reported, and no other rule; QB-02 still passes |
| QB-19 | UC-19 | R10-02. The New York answer with 30 copies of the line's last point added, and each station stop moved to the farthest line point that R12 (section 4) still accepts for its marker | R13 is reported (29 repeated points, and 5,624 points against 5,602.4) |
| QB-20 | UC-19 | R10-02. The New York answer with its middle line point repeated; separately, 19 and then 30 distinct points added between the line's last two | R13 reports a repeated point; R13 does not report the point count (5,613 points, 0.19% over); R13 reports it (5,624, 0.39% over, beyond 0.25%) |
| QB-21 | UC-39 | R10-12. `verify_response(…, routing_hosts="fake-osrm")`, a bare string | `TypeError` |
| QB-22 | UC-03 | R10-07. `build_answer` with the plan's and the free-stops purchases both (0, 0.004), (1, 10.003), (2, 19.993) at [3.50, 3.00, 2.00]; distance 300.0; stop cost 0 | Shown gallons 0.00, 10.01, 19.99; both bills 70.01; stops 3 and lowest_possible_stops 3: the fill-up at the start is counted in both, even at 0.00 gallons |
| QB-23 | UC-12 | R10-09. Server 1 answers 404 with `{"code": "NoRoute"}`; separately, server 1 answers 503 with that body and server 2 the OK answer | `NoRoute`, calls 1, server 2 never asked; a `Route` from server 2, calls 2: a 5xx is the server's own trouble, whatever its body says |

### 9.14 The verifier's options

Rows 2 and 3 of the settled points: the verifier accepts any routing host its caller names, as well as the two public ones (R15), and checks R17 against the places its caller gives. "The New York answer" is as in 9.13.

| ID | UC | Input | Expected |
|---|---|---|---|
| VR-01 | UC-39 | The New York answer with `meta.routing_server` `fake-osrm`: checked with no host named; then with the caller naming `fake-osrm`. Then the unchanged answer, `router.project-osrm.org`, with the caller naming `fake-osrm` | R15 is reported, and no other rule; then no rule fails; then no rule fails, as the public hosts are always accepted (row 2) |
| VR-02 | UC-39 | `scripts/live_check.py`'s check of one 200 body, the answer of VR-01 with `fake-osrm`: run with `--routing-host fake-osrm`; then without the option | Passes; then fails, naming R15 (row 2) |
| VR-03 | UC-19 | EP-01's answer, whose stations are in `Testville, TX`: checked with the endpoint tests' own places, which put `Testville, TX` at each of the test's station positions; then with the default places | No rule fails; then R17 is reported for each station stop, as `data/us_cities.csv` has no `Testville, TX` (row 3) |
| VR-04 | UC-19 | With the default places: an answer whose one station stop is in `Henrico, VA`, at the position `stations/places.py` gives that hand-added place; the same for each of the other four hand-added places; then each stop moved 20 miles north. Separately, the verifier's own copy of the five places beside `stations/places.py`'s | R17 is not reported: the five hand-added places are part of the default places (row 3); then R17 is reported, so it did run. The two tables are equal, value for value (review 10R, R10-13) |
