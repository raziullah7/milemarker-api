# Brief R2: verify Postman, Newman and the map view

You are a research agent. Today is 18 Nov 2026. A Postman collection will be written later to demonstrate a JSON API in a recorded video, and it must also run unattended as a test. I need **verified, current** facts and working samples. Use web search and page fetches against primary sources (Postman Learning Center, the Postman collection schema, the Newman repository, geojson.io docs). Do not rely on memory. Do not spawn other agents.

**Write your full report to `docs/plan/reports\phase1-R2-postman.md`.** Return to me only: a five-line summary and anything you could not confirm.

For every answer give the fact and its URL. Mark anything unconfirmed as `NOT CONFIRMED`.

## The API being demonstrated

`GET {{base_url}}/api/v1/route/?start=New York, NY&finish=Los Angeles, CA&stop_cost=10` returns JSON shaped like:

```json
{
  "summary": {"distance_miles": 2800.7, "gallons": 280.07, "total_fuel_cost": 865.93, "stops": 7,
              "lowest_possible_fuel_cost": 854.65, "first_fill_distance_miles": 3.1},
  "fuel_stops": [{"order": 1, "name": "DELTA", "city": "Jersey City", "state": "NJ", "mile_marker": 0.0,
                  "lat": 40.748, "lng": -73.997, "price_per_gallon": 3.239, "gallons": 39.15, "cost": 126.81}],
  "map": {"type": "FeatureCollection", "features": [
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-73.997, 40.748], [-74.01, 40.75]]}, "properties": {"kind": "route"}},
      {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-73.997, 40.748]}, "properties": {"kind": "stop", "title": "1. DELTA"}}]},
  "meta": {"routing_calls": 1, "cache_hit": false}
}
```

The route line has about 5,600 points; the whole body is about 130 KB. Errors look like `{"error": {"code": "unknown_place", "message": "...", "details": {}}}`.

## Questions

**A. Collection format.** The current collection schema version to target (v2.1.0?) and its `$schema` URL. A minimal valid collection with: one collection variable (`base_url`), two folders, a GET request whose query parameters are separate `query` entries (so spaces and commas in `New York, NY` are encoded correctly), and a test script attached to a request. Does Postman still import this format in the current app?

**B. Test scripts.** Current syntax for: checking the status code; parsing JSON; asserting a field equals, is below, or is above a value; asserting an array's length; asserting response time; saving a value into a collection variable in one request and comparing against it in a later one (I need request 3 to check its total equals request 1's `lowest_possible_fuel_cost`). Is the `event` key `"listen": "test"` still correct, and is it `pm.test` / `pm.expect` / `pm.response.json()`?

**C. Showing a map inside Postman.** I want the response's route and stops drawn as a map in Postman's Visualize tab.
1. Current API: `pm.visualizer.set(template, data)` and how the template reads the data.
2. Can the template load Leaflet's JS and CSS from a CDN and map tiles from OpenStreetMap in the current Postman desktop app? Any content-security or sandbox restriction. Find an official or well-known example that draws a map.
3. Give a complete, copy-pasteable Visualizer test script that draws the `map` FeatureCollection above with Leaflet: the line, a marker per stop with a popup showing its title, and the view fitted to the line.
4. A fallback that needs no external script, in case CDN loading is blocked: an inline SVG that draws the line and numbered stop circles from the same data (simple equirectangular scaling is fine). Give the script.
5. Does the Visualize tab work in Postman's web version as well as the desktop app?

**D. Running the collection unattended.**
1. Is Newman still maintained and usable in Nov 2026? Latest version, the Node versions it supports.
2. The exact command to run a collection file with a delay of 1,200 ms between requests, overriding `base_url`, and failing the process if any test fails. Exit codes.
3. The newer Postman CLI (`postman collection run`): does it need a Postman login or API key to run a **local file**? I need something that works with no account.
4. Whether Visualizer code in a test script causes errors under Newman (it must not break the run).

**E. geojson.io as the fallback viewer.**
1. Ways to load a 130 KB FeatureCollection: paste into the editor, open a file, drag and drop, URL fragment. Any size limit.
2. Which feature properties it styles (`marker-color`, `marker-symbol`, `title`, `stroke`, `stroke-width` from the simplestyle spec) and whether `title` shows in the popup.
3. Any current alternative that opens GeoJSON with no account, in case geojson.io is unavailable.

**F. Large responses in Postman.** Any documented limit or slowdown when the Pretty view renders a 130 KB JSON body, and whether putting small fields first in the JSON helps readability in the recording.

## Verify by running, where you can

You have Node available (`npx`). If Newman is confirmed, write your minimal sample collection to a temporary folder **outside any project** (for example your system temp directory), point it at `https://postman-echo.com/get`, and run it with `npx newman run` to prove the format, the query encoding and the test syntax actually work. Paste the command and its output into the report. Do not send any personal or project information in those requests.
