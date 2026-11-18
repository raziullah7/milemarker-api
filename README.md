# Mile Marker API

Give it a start and a finish in the USA. It returns the driving route, where to stop for fuel, and what the fuel will cost. A new trip costs one call to a free routing service; a repeat costs none.

## Run it

You need git and Docker. There is no API key and no account.

```bash
git clone https://github.com/raziullah7/milemarker-api.git
cd milemarker-api
docker compose up --build -d
```

The first start takes about a minute: it loads 6,626 fuel stations. Then open **http://127.0.0.1:8000/api/v1/docs/** and try a trip from the page, or use curl:

```bash
curl "http://127.0.0.1:8000/api/v1/route/?start=New%20York,%20NY&finish=Los%20Angeles,%20CA"
```

Stop it with `docker compose down`.

## What comes back

```json
{
  "summary": {
    "distance_miles": 2800.6,
    "gallons": 280.06,
    "total_fuel_cost": 867.27,
    "stops": 7
  },
  "fuel_stops": [
    {"order": 1, "name": "DELTA", "city": "Jersey City", "state": "NJ",
     "mile_marker": 0.0, "price_per_gallon": 3.239, "gallons": 39.21, "cost": 127.0},
    "… six more"
  ],
  "map": {"type": "FeatureCollection", "features": ["the route and the stops, as GeoJSON"]},
  "meta": {"routing_calls": 1, "cache_hit": false}
}
```

- `start` and `finish` are a city and state, such as `Dallas, TX`. `Dallas TX` and `Dallas, Texas` work too.
- `stop_cost` is optional (0 to 100, default 10). It is explained below.
- To see the trip on a map, paste the `map` value into [geojson.io](https://geojson.io).
- Every error has one JSON shape with a `code`. The docs page lists them all.

## Run the tests

```bash
docker compose --profile test run --rm test
```

597 tests, about two minutes. None of them reaches the internet.

## How it works

1. Both places are looked up in an offline table. Nothing is geocoded over the network.
2. The road comes from one call to the OSRM public server, and is cached for 24 hours.
3. Every station within 5 miles of the road is found from an index held in memory.
4. The stops are chosen, and the answer is built and cached.

The code for each step is in [`trips/services/`](trips/services/), and [`planner.py`](trips/services/planner.py) runs them in order.

**Choosing the stops.** The vehicle goes 500 miles on a tank at 10 miles per gallon. The cheapest possible fuel bill for New York to Los Angeles takes 19 stops, one of them for about half a gallon, to save $11. Nobody drives like that. So while the plan is chosen, each stop is charged $10; the charge is never added to the bill. That gives 7 stops for $867.27. Send `stop_cost=0` to get the cheapest bill whatever the number of stops. The response shows both figures.

## Beyond the brief

Each of these is more than the task asked for. One line on why it is there:

| What | Why |
|---|---|
| A cost per stop | The cheapest plan on paper is not one a driver would follow (above) |
| Redis, shared by two workers | A repeat is a cache hit whichever worker answers. If Redis is down the API carries on from memory |
| A rate limit of 60 requests a minute | The free routing servers ask for no more than one request a second |
| A docs page | So the API can be tried without reading anything |
| An independent checker, [`tests/verify.py`](tests/verify.py) | It tests every answer against 17 rules and shares no code with the API |
| CI on every push | Lint, types, tests, the image build, and the Postman collection run against recorded roads |
| PostgreSQL | It holds the stations. They are read into memory once, so no request waits on the database |

## What it assumes

The task left some things open. The ones that matter most:

- The tank is empty at the start, so the first fill-up is at the station nearest the start.
- A station is placed at the centre of its city: the supplied file has no coordinates.
- Places are a city and state in the lower 48 states and DC. Street addresses and ZIP codes are not understood.
- A road that runs through Canada or Mexico is refused.

All fifteen decisions, each with the measurement behind it, are in [`docs/requirements.md`](docs/requirements.md).

## Known limits

- Station positions are city centres, a median 2.8 miles from the real station, and there is no reserve on the 500-mile range.
- Some roads have no fuel listed, such as Interstate 5 through California. Los Angeles to Seattle has no plan, and the API says so.
- Routing is for cars, not trucks, and the free routing servers promise no uptime.

## More

| | |
|---|---|
| [`docs/development.md`](docs/development.md) | Running from source, the settings, and the other commands |
| [`docs/backend-architecture.md`](docs/backend-architecture.md) | How it is built and why |
| [`docs/requirements.md`](docs/requirements.md) | What it must do, and every decision |
| [`docs/test-cases.md`](docs/test-cases.md) | Every test case, with results |
| [`docs/postman/`](docs/postman/) | The Postman collection |
| [`docs/plan/`](docs/plan/) | The build plan, phase by phase |

The fuel prices are the file supplied with the task. Sources and licences for the other data are in [`data/README.md`](data/README.md).
