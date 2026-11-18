# Mile Marker API: Requirements

What the API must do, how well it must do it, and what is deliberately left out.
This file says **what** is required. `backend-architecture.md` says **how** it is built.

**Status:** every decision in section 6 is settled. Each one was tested against the supplied CSV or a real route on 18 Nov 2026, and the measurement is recorded next to it. The document was then read by an independent reviewer and corrected.

## 1. Purpose

A truck driver or dispatcher gives a start and a finish inside the USA. The API returns the driving route, the best places to buy fuel along it, and what the fuel for the trip will cost.

Prices differ a lot between truck stops (from $2.69 to $6.40 a gallon in the supplied file), and the truck can only travel 500 miles on a tank. The value of the API is in choosing where to stop and how much to buy, so the trip costs as little as possible and the truck never runs dry.

## 2. Given facts and constraints

| Item | Value | From |
|---|---|---|
| Vehicle range | 500 miles on a full tank | Assignment |
| Fuel economy | 10 miles per gallon | Assignment |
| Tank size | 50 gallons (500 ÷ 10) | Derived |
| Coverage | Start and finish both within the USA | Assignment |
| Fuel prices | The supplied CSV of truck stops, taken as the truth | Assignment |
| Routing and map | A free third-party API, found by us | Assignment |
| Framework | Latest stable Django (6.1.3 on 18 Nov 2026) | Assignment |
| Database | PostgreSQL | Ours |
| Deadline | 3 days from receipt: Friday 20 Nov 2026, 8 pm | Assignment |

Facts about the supplied CSV that shape the requirements:

- 8,151 rows, but only 6,738 distinct stations. 678 stations are listed more than once, and 597 of those at more than one price.
- 6,626 of the stations are in the USA, all in the lower 48 states. The other 112 are in nine Canadian provinces.
- There are no coordinates. Each row has a highway-exit address, a city and a state.
- 1,256 rows have city names padded with spaces.
- Coverage is uneven. California has 8 stations, all in the far south-east of the state. The nearest station to Los Angeles is 121 miles away, to San Francisco 167 miles and to Houston 47 miles.
- No station is listed on Interstate 5 through California. Driving from Los Angeles to Seattle, the first one is in Halsey, Oregon, 886 miles in.

## 3. Tiers

Every requirement below has one of three tiers.

- **Need:** the assignment asks for it, or the result would be wrong or impossible to run without it.
- **Want:** not asked for, but it makes the result easier to trust or to review, and it is cheap.
- **Nice:** a nice-to-have. Built only if time is left once the demo could already be recorded.

Order of work: every need first, then wants from the top of each table down, then nice-to-haves.

The **From** column says where a requirement comes from: **Assignment** (stated in it), **Derived** (follows directly from an assignment line) or **Ours** (our own addition).

## 4. Functional requirements

| ID | The API… | Tier | From |
|---|---|---|---|
| FR-1 | Accepts a start and a finish location in one request, each as a place name such as "Dallas, TX" (D-3). | Need | Assignment |
| FR-2 | Rejects a place that is unknown or outside the lower 48 states and DC with a clear error, before any routing call is made. | Need | Assignment |
| FR-3 | Returns the driving route between the two points, with its distance in miles. | Need | Assignment |
| FR-4 | Returns a map of that route as GeoJSON: the route line and every fuel stop as a marked point, ready to draw in any map viewer. | Need | Assignment |
| FR-5 | Returns each fuel stop: station name, address, city, state, position, miles from the start, price per gallon, gallons to buy and cost. | Need | Assignment |
| FR-6 | Chooses where to stop and how much to buy so the fuel bill is as low as possible, without stopping for a saving smaller than the cost of the stop itself (D-9). | Need | Assignment |
| FR-7 | Never plans a stretch longer than 500 miles between fill-ups, and adds as many stops as that takes. | Need | Assignment |
| FR-8 | Returns the total money spent on fuel for the trip at 10 miles per gallon. The total covers every gallon the trip burns (D-1), and every figure can be reproduced from the response with a calculator (D-14). | Need | Assignment |
| FR-9 | Takes every price from the supplied CSV and shows it with nothing rounded away. | Need | Assignment |
| FR-10 | Returns a clear error, not a wrong plan, when no valid plan exists: a stretch of more than 500 miles with no station listed (Los Angeles to Seattle is one), or a road route that leaves the USA (D-4). | Need | Ours |
| FR-11 | Returns a clear error for missing or unrecognised input. The error names the field that failed and suggests the closest place names it does know. Every error, of any kind, has the same shape. | Need | Ours |
| FR-12 | States in the response the assumptions it used: range, fuel economy, starting fuel and stop cost. | Want | Ours |
| FR-13 | Reports in the response how many routing calls were made, whether the answer came from cache, and how long the routing call and our own work took. | Want | Ours |
| FR-14 | Always reports how far the first fill-up station is from the start, and adds a warning when that is more than 25 miles (D-1). | Want | Ours |
| FR-15 | Reports the lowest fuel bill that was possible with unlimited stops, next to the bill of the plan it chose. | Want | Ours |
| FR-16 | Lets the caller change the stop cost. Zero gives the lowest possible fuel bill regardless of how many stops it takes. | Want | Ours |
| FR-17 | Accepts coordinates (latitude and longitude) as well as place names. | Nice | Ours |
| FR-18 | Serves a page that draws the map, reached by a link in the response. | Nice | Ours |
| FR-19 | Offers interactive API documentation (OpenAPI). | Nice | Ours |

## 5. Non-functional requirements

The speed targets come from measurements on a 2,800-mile route. They will be replaced with figures from the finished API.

| ID | Requirement | Tier | From |
|---|---|---|---|
| NFR-1 | **Speed, new request.** Our own work adds no more than 100 ms on top of the routing provider's response time. | Need | Assignment |
| NFR-2 | **Routing calls.** One call to the routing API per new route. One retry is allowed after a timeout or server error, sent to a second server, so never more than two. Asking for the same route again, even with a different stop cost, makes none. | Need | Assignment |
| NFR-3 | **No other external calls.** Start, finish and stations are all looked up locally at request time. | Need | Derived |
| NFR-4 | **Framework.** Built on the latest stable Django. | Need | Assignment |
| NFR-5 | **Free services, no account.** The routing service is free and needs no API key, so a reviewer can run the project without signing up for anything. No secret is committed. | Need | Assignment |
| NFR-6 | **Correct cost.** The fuel algorithm is tested against two independent exact methods, as well as hand-written edge cases. | Need | Ours |
| NFR-7 | **Data preparation.** The station file is cleaned, located and stored in the database once, as seed data. Duplicates, padded names, Canadian rows and missing coordinates are dealt with at that point. Requests read stations from memory, not from the database or the file. | Need | Derived |
| NFR-8 | **Readable.** Logic sits in small, named, commented modules, and the whole design can be walked through in a 5-minute video. | Need | Assignment |
| NFR-9 | **Easy to run.** With Docker, one command starts the database and the API from a fresh clone. The README covers setup, an example request and the assumptions. | Need | Ours |
| NFR-10 | **Database.** PostgreSQL, run through Docker Compose and configured by one `DATABASE_URL` setting. | Need | Ours |
| NFR-11 | **Speed, repeated request.** An identical request is answered from cache in under 50 ms with no routing call. | Want | Ours |
| NFR-12 | **Provider failure.** If the routing API fails or is slow, the API returns a clear error within about 10 seconds. It does not hang or crash. | Want | Ours |
| NFR-13 | **Wider tests.** Tests for the endpoint (routing faked), the station loader and the search for stations along the route. No test reaches beyond the local machine. | Want | Ours |
| NFR-14 | **Lint.** The code passes Ruff. | Want | Ours |
| NFR-15 | **Postman collection** committed to the repo, each request with its own checks. | Want | Ours |
| NFR-16 | **Rate limit** of 60 requests a minute per client. The free routing servers ask for no more than one request a second. | Want | Ours |
| NFR-17 | **CI** that runs lint and tests on every push. | Nice | Ours |
| NFR-18 | **Shared cache** (Redis), needed only when the API runs as several processes. | Nice | Ours |

## 6. Decisions

The assignment is silent on these. Each is stated in the README and, where it affects the numbers, in the response.

| ID | Question | Decision | What we measured |
|---|---|---|---|
| D-1 | How much fuel is in the tank at the start? | None. The truck fuels up before leaving, and that fuel is priced at the listed station nearest the start place. Where several stations share that nearest position, the cheapest is used. That station is stop 1, at mile 0, and is not counted again along the road. The total therefore covers every gallon the trip burns. Rejected: starting full, which gives a $0 total for any trip under 500 miles. | For most cities the nearest station is in the city itself. For Los Angeles it is 121 miles away and for Houston 47, which is why FR-14 reports the distance. |
| D-2 | What counts as "a map"? | The route and the fuel stops as GeoJSON in the response, which any map viewer can draw. The API serves no page of its own unless FR-18 is built. | — |
| D-3 | What can be given as a location? | A city and state, looked up in an offline table of 29,880 US places. Everyday spellings are accepted: `Dallas, TX`, `Dallas TX`, `Dallas, Texas`, `Dallas, TX, USA`, `st. louis, mo`, `Washington, D.C.`, `New York City, NY`, `Sault Ste. Marie, MI`. Matching ignores case, spaces and punctuation. Street addresses and ZIP codes are not accepted, because recognising them needs a geocoding API and would add calls to every request. | All 58 test names resolved, including Winston-Salem, Coeur d'Alene, St. Louis and O'Fallon. |
| D-4 | What is "within the USA"? | The lower 48 states and DC. Alaska, Hawaii, Puerto Rico, Canadian provinces and Mexico are rejected as outside coverage. A route that runs more than 25 miles in a row through Canada or Mexico is rejected too. | The fastest road from Detroit to Buffalo runs 252 miles through Ontario, and Detroit to Boston 234. Fifteen trips that stay in the USA, including ones along the border and across islands, registered a run of 10 miles at most. |
| D-5 | Where is a station, when the file has no coordinates? | At the centre of the city the CSV gives for it. A station counts as on the route if that point is within 5 miles of the road. Where the places table lists a city under several counties, the average of its rows is used, unless they are more than 10 miles apart; then one named county's row is used. | All 6,626 US stations were placed: 6,615 from the places table and 11 from five places added by hand. Checked against the real position of 36 stations, the city centre was a median 2.8 miles away, and within 5 miles for 86% of them. 22 cities have rows over 10 miles apart; Orlando's are 48 miles apart. |
| D-6 | Which price applies when a station is listed several times? | Every row in the CSV is true, so the truck buys at the cheapest listing. Where two listings tie, the first in the file gives the station its name. | The 597 stations with more than one price differ by a median of 9 cents. Taking the lowest and not the average moves the average station price by half a cent. |
| D-7 | How much fuel must be left at the finish? | None. The plan buys only enough to arrive. | — |
| D-8 | Does the detour to a station use fuel? | No. Stations are treated as being on the route. | With D-5 the detour is at most 5 miles each way. |
| D-9 | How many stops are too many? | Each stop is charged $10 when the plan is chosen, to stand for the time it takes. The $10 is never added to the fuel bill. Without it, the cheapest plan stops for less than a gallon to save a few cents. | New York to Los Angeles, lowest possible fuel bill: $854.65 with 17 stops, the smallest for 0.6 gallons. At $10 a stop: $865.93 with 7 stops, the smallest for 25.8 gallons. That is 1.3% more fuel money for 10 fewer stops. |
| D-10 | Which stations along the route are worth considering? | A station is skipped if another within 10 miles along the route is cheaper, or equally cheap and earlier. This never hides a valid plan: whether a plan exists is decided on every station, and the full list is used if the shorter one has none. When the stop cost is zero no station is skipped, so the bill is the true lowest. | This removes about three quarters of the candidates (363 to 98 on New York to Los Angeles) and raises the fuel bill by 0.2% at most. |
| D-11 | How wide is the search for stations? | 5 miles either side of the road (see D-5). | Widening to 10 miles lowers the bill by less than 1% and admits stations twice as far from the road. |
| D-12 | Which free routing API? | The OSRM public server, which needs no API key, with a second server running the same software for the one retry. Rejected: openrouteservice, which needs an account and key and has maintenance announced for the deadline day. | New York to Los Angeles returned in 1.6 seconds. The second server gave the identical route. |
| D-13 | Which database? | PostgreSQL, the database a Django service runs on in production, started with the API by one Docker Compose command. The database is only used to hold the seed data; no request reads it. | — |
| D-14 | How are the figures rounded? | The trip length is rounded to 0.1 mile. Each stop's gallons are rounded to 2 decimals and adjusted so they add up to the distance ÷ 10 exactly. A stop's cost is its gallons × its CSV price, rounded to cents. The total is the sum of the stop costs. The lowest possible bill (FR-15) is rounded the same way. | — |
| D-15 | What is cached? | The road, by its two end points, and the finished answer, by those plus the stop cost. Both for 24 hours. | — |

## 7. Out of scope

- User accounts, login, or keys for callers
- Trips with more than two points
- Comparing alternative routes against each other
- Live or updated fuel prices
- Outside sources of station data. The CSV is the only source of stations and prices.
- Street addresses and ZIP codes as input (D-3)
- Alaska, Hawaii and anywhere outside the USA (D-4)
- Changing the range or fuel economy per request
- A frontend application. The only page considered is the optional map page (FR-18).

## 8. Deliverables

- A public GitHub repository
- A Loom video of 5 minutes or less: the API demonstrated in Postman, then a quick code overview
- Both links sent in the hiring thread before the deadline

## 9. Acceptance checks

The work is done when all of these hold.

1. `New York, NY` to `Los Angeles, CA` returns the route, the stops and a total cost, with fewer than 10 stops, counting the fill-up at the start.
2. In that plan, no stretch between fill-ups is longer than 500 miles, the gallons bought equal the distance ÷ 10, and the total equals the sum of the stop costs.
3. The response reports one routing call. Sending the same request again reports none, and so does the same trip with a different stop cost.
4. A trip shorter than 500 miles returns a valid plan with a cost above zero.
5. `Los Angeles, CA` as the start returns a plan and reports the first fill-up distance (about 121 miles). Because that is over the 25-mile limit in FR-14, the response carries a warning.
6. `Honolulu, HI` and an unrecognised place name are each rejected without a routing call. `Detroit, MI` to `Buffalo, NY` is rejected because the road leaves the USA. `Los Angeles, CA` to `Seattle, WA` is rejected because no fuel is listed along the road.
7. The map in the response, opened in a GeoJSON viewer, shows the route with the stops marked.
8. The fuel algorithm's tests pass, including the comparison with the two exact methods.
9. A fresh clone starts with one Docker Compose command, with no API key.
10. The Loom is recorded and both links are submitted before Friday 20 Nov 2026, 8 pm.
