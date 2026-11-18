# Brief 3F: the answer builder

Read `docs/plan/briefs/phase3-common.md` first. It applies in full.

## Goal

Turn a finished plan into the response body. Every figure a caller sees is rounded here, and the rounding must be exact: a reviewer with a calculator must be able to reproduce every number from the response alone.

## Your files

- `trips/services/answer.py`
- `tests/test_answer.py`
- Report: `docs/plan/reports/phase3-F.md`

## Read

- `docs/backend-architecture.md` section 8 ("Money and rounding", "The lowest possible bill") and section 11 ("Response", including Stops, Warnings, Numbers and The map)
- `docs/requirements.md` decisions D-1, D-14 and requirements FR-5, FR-8, FR-9, FR-12, FR-14, FR-15
- `docs/test-cases.md` section 2.8, and section 4 (the correctness rules R1 to R16, which your output must satisfy)
- The data classes you receive: `stations/places.py` (`Place`), `stations/types.py` (`StationInfo`), `trips/services/geo.py` (`RoadPoints`), and `Stop` in your own skeleton

## Test cases

AN-01 to AN-11, exactly as `docs/test-cases.md` gives them. Also write one test that builds a complete answer and checks it against rules R3, R4, R6, R8, R9, R10, R11 and R14 of section 4 by plain assertions.

## Decisions already made

**Rounding, in this order.** Use `decimal.Decimal` throughout; never round money with floats.

1. `distance_miles` arrives already rounded to 0.1. Total gallons = `distance_miles ÷ 10`, which has at most 2 decimals.
2. Round each purchase's gallons half-up to 2 decimals.
3. If the rounded gallons do not add up to the total, add the difference (a few hundredths, either sign) to the largest purchase. On a tie for largest, the earliest.
4. A stop's cost = its rounded gallons × its exact price (`StationInfo.price`), rounded half-up to cents.
5. `total_fuel_cost` = the sum of the stop costs. `summary.gallons` = the sum of the stop gallons.

The free-stops plan (`cheapest`) is rounded by the same steps. Purchases under 0.005 gallons are left out of `lowest_possible_stops` but their fuel still counts towards the gallons and the bill. `lowest_possible_stops` is never less than 1.

**Numbers in the output are plain Python floats and ints**, so they render as JSON numbers: `float(Decimal("3.00733333"))` is `3.00733333`, with nothing rounded away. Miles to 1 decimal, gallons and money to 2, coordinates to 5.

**The order of keys** in the body is `summary`, `warnings`, `assumptions`, `fuel_stops`, `map`. Within each, use the order shown in architecture section 11. `meta` is added later by the caller and is not yours.

**The warning.** When `first_fill_miles` is more than 25.0, `warnings` holds exactly one sentence: `The nearest listed fuel station to the start is <name> in <City>, <ST>, <miles> miles away. The first fill-up is priced there.` with the miles to 1 decimal. Otherwise `warnings` is `[]`.

**Each fuel stop:** `order`, `kind` (`"start"` for the first, `"station"` for the rest), `station_id` (the `opis_id`), `name`, `address`, `city`, `state`, `mile_marker`, `lat`, `lng`, `price_per_gallon`, `gallons`, `cost`.

**The map** is a GeoJSON FeatureCollection in this order:

1. The route: a `LineString` whose coordinates are every point of `road` as `[lng, lat]`. Properties: `kind: "route"`, `distance_miles`.
2. One `Point` per stop, in order. Properties: `kind: "stop"`, `order`, `title` (`"<order>. <name>, <City> <ST>"`, for example `2. SHEETZ #639, Youngstown OH`), `name`, `mile_marker`, `price_per_gallon`, `gallons`, `cost`, `marker-color`.
3. A `Point` for the start (`kind: "start"`, `title: "Start: <label>"`) and one for the finish (`kind: "finish"`, `title: "Finish: <label>"`), each with `marker-color`.

Marker colours: stops `#d9480f`, start `#2b8a3e`, finish `#1864ab`.

A station stop's `lat` and `lng` are exactly the coordinates of one point of `road`, rounded the same way as the line's, so the stop sits on the line (rule R12).

**Assumptions:** `range_miles` 500, `miles_per_gallon` 10, `tank_gallons` 50, `starting_fuel_gallons` 0, `stop_cost` as a float, `search_radius_miles` 5. Take the first three from `trips/services/fuel.py`'s constants.
