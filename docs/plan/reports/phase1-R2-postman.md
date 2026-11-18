# R2 report: Postman, Newman, Visualizer map, geojson.io (checked 18 Nov 2026)

Legend: VERIFIED-RUN = I ran it. DOC = read in a primary source (URL given). THIRD-PARTY = non-official source. NOT CONFIRMED = could not establish.

## A. Collection format

- The official schema site lists two versions: v2.1.0 and v3.0.0 (draft-07 JSON Schema files). https://schema.postman.com/ (DOC)
- Target v2.1.0. `$schema` value: `https://schema.getpostman.com/json/collection/v2.1.0/collection.json`. The schema file's own `$id` is `https://schema.getpostman.com/json/draft-07/collection/v2.1.0/` (fetched from https://schema.postman.com/collection/json/v2.1.0/draft-07/collection.json, DOC). My probe of the `$schema` URL returned HTTP 301 (redirect), and Newman accepted it (VERIFIED-RUN).
- Newman 6.2.3 runs a v2.1.0 collection with that `$schema` (VERIFIED-RUN, see Sample).
- Does the current Postman app still import v2.1 JSON? NOT CONFIRMED. No primary page states it. The Postman CLI page only says v2.1 JSON can be converted with `postman collection migrate`, and its examples use the v3 directory/YAML format. https://learning.postman.com/docs/postman-cli/postman-cli-collections/ (DOC)
- Query params as separate `query` entries: the sample does this, and the echo server received `start` = `New York, NY` exactly (VERIFIED-RUN). Newman's console prints the raw URL unencoded; the server's `args` show correct decoding.

## B. Test scripts

- `"listen": "test"` under `event` is correct (VERIFIED-RUN).
- Syntax from https://learning.postman.com/docs/tests-and-scripts/write-scripts/test-examples/ (DOC), all run under Newman 6.2.3 (VERIFIED-RUN):
  - `pm.test("name", () => {...})`, `pm.expect(...)`, `pm.response.json()`, `pm.response.to.have.status(200)`, `pm.response.responseTime`.
  - equals: `.to.eql(v)`; below/above: `.to.be.below(n)` / `.to.be.above(n)`; array length: `pm.expect(arr).to.have.lengthOf(n)` (the docs page has no dedicated array example; my run used `Object.keys(...)` with `lengthOf`).
  - Cross-request value: `pm.collectionVariables.set('lowest', ...)` in request 1, `pm.collectionVariables.get('lowest')` in request 3. The docs test-examples page does not cover collection variables; the run proved it works (request 2 compared against the saved value and passed). For the real collection:
    - request 1: `pm.collectionVariables.set('lowest', pm.response.json().summary.lowest_possible_fuel_cost)`
    - request 3: `pm.expect(pm.response.json().summary.total_fuel_cost).to.eql(Number(pm.collectionVariables.get('lowest')))`
  - Caveat: in my run the saved value came back as a string (compared string to string). Wrapping in `Number(...)` for numbers is my recommendation; I did not run the numeric case.
- Under Newman, request 3 depends on request 1 having run earlier in the same run.

## C. Visualizer (map inside Postman)

1. API: `pm.visualizer.set(layout, data, options)`. `layout` is a Handlebars HTML template string, `data` is bound to it, `options` goes to `Handlebars.compile()`. Inside a `<script>` in the layout, `pm.getData(function(error, data){...})` returns the same `data`. `pm.visualizer.clear()` also exists. https://learning.postman.com/docs/tests-and-scripts/write-scripts/postman-sandbox-reference/pm-visualizer.md and https://learning.postman.com/docs/sending-requests/response-data/visualizer/ (DOC). The tab is called "Visualization" in current docs.
2. External Leaflet and OSM tiles:
   - The visualizer docs say an external JS library can be added by URL in a `<script>` tag (D3 example), and also say "Visualizer doesn't support interactions that download resources" (ambiguous). https://learning.postman.com/docs/sending-requests/response-data/visualizer/ (DOC)
   - A public working example loads Leaflet 1.7.1 from unpkg and OSM tiles `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`, calls `pm.visualizer.set(template, {response: pm.response.json()})` and reads data with `pm.getData`. https://github.com/OrdnanceSurvey/postmanGeoJSON (README read; I did not run it; its age is not stated).
   - A developer reports the visualizer CSP is fixed and quotes `script-src http: https: 'unsafe-inline'`, with `unsafe-eval` blocked and JavaScript inside HTML attributes blocked. https://dev.to/marcusatlocalhost/jsonpath-with-alpinejs-csp-build-in-postman-visualizer-17ob (THIRD-PARTY). Practical rule: use `<script>` blocks only, no `onclick=` style attributes, no eval. Leaflet needs none of those.
   - That tile images load under the current app's CSP: NOT CONFIRMED (cannot drive Postman here). The OS example implies it works.
   - Visualizer developer tools (Inspect visualization) are desktop-only. https://learning.postman.com/docs/sending-requests/response-data/visualizer/ (DOC)
3. Leaflet script: Appendix 1. I ran it against a mock `pm` in Node: it produces a template with no `{{` (Handlebars will not touch it), and the inner script parses. NOT run in real Postman. The Leaflet 1.9.4 unpkg URL was not independently fetched (the documented example uses 1.7.1; swap if 1.9.4 misbehaves).
4. Inline SVG fallback: Appendix 2. No external script, template has no `<script>`, uses `{{{svg}}}` (unescaped). Ran against a mock `pm` under Node. NOT rendered in real Postman.
5. Web version: the Postman docs I read do not say either way. NOT CONFIRMED.

## D. Unattended runs

1. Newman: npm `latest` = 6.2.3, `engines.node` >= 16, registry last modified 2026-10-09 (VERIFIED by `npm view newman`; also https://raw.githubusercontent.com/postmanlabs/newman/develop/package.json). README compatibility table: v6.x for Node >= 16. https://github.com/postmanlabs/newman (DOC). Active repo; README promotes the Postman CLI but does not say Newman is deprecated. Ran on Node v24.22.1 (VERIFIED-RUN). Install prints deprecation warnings for transitive dependencies; harmless.
2. Command (VERIFIED-RUN, exit 0):

   `npx newman run coll.json --delay-request 1200 --env-var "base_url=https://postman-echo.com" --bail failure`

   Options per https://github.com/postmanlabs/newman (DOC): `--delay-request <ms>`, `--env-var key=value` (repeatable), `--global-var`, `--bail [folder|failure]`, `-x/--suppress-exit-code`.
   - Observed exit codes (VERIFIED-RUN): 0 when all pass; 1 with a failing assertion; 1 on connection error (`--env-var base_url=http://127.0.0.1:1`); 1 for a missing collection file.
   - The docs say default exit 0 on a clean run, and `--bail` stops and exits 1 on a test failure. https://learning.postman.com/docs/collections/using-newman-cli/newman-options.md (DOC). I observed exit 1 on a failing assertion even without `--bail`, so `--bail` is optional for failing the process; it only stops early.
   - `--env-var base_url=...` overriding a collection variable: my sample passed the same value as the collection default, so override precedence is NOT PROVEN. The bad-host run did fail, which suggests the override applied, but it was not a clean A/B test.
3. Postman CLI (`postman collection run <collection>`): docs say local runs need no login or API key when given a file path; results only go to Postman with login, `POSTMAN_API_KEY` or `--postman-api-key`. It has `--delay-request`, `--env-var`, `--bail`, `--report-events=false`. https://learning.postman.com/docs/postman-cli/postman-cli-run-collection/ and https://learning.postman.com/docs/postman-cli/postman-cli-collections/ (DOC). Running a v2.1 JSON file directly: NOT CONFIRMED (docs show v3 formats and suggest `postman collection migrate`). I tried to run it; the sandbox denied the install, so it was not run. Use Newman for the no-account unattended run.
4. Visualizer under Newman: a test script calling `pm.visualizer.set('<div>{{x}}</div>', {x: 1})` ran with no error, run passed (VERIFIED-RUN, Newman 6.2.3). Not tested with the html reporter.

## E. geojson.io

1. Loading:
   - URL hash params: `#data=data:application/json,<encodeURIComponent(JSON)>`, `#data=data:text/x-url,<encoded URL>` (public, CORS-enabled URL), `#id=gist:login/gistid`, `#id=github:login/repo/blob/branch/path`, `#map=zoom/lat/lon`. https://raw.githubusercontent.com/mapbox/geojson.io/main/API.md (DOC). No size limit is stated there.
   - Imports GeoJSON, KML, CSV, Shapefile. https://github.com/mapbox/geojson.io (DOC).
   - Open > File: only a third-party mention. https://docs.live-eo.com/tradeaware/using-the-tradeaware-web-app/plot-upload-and-analysis-trouble-shooting (THIRD-PARTY). Paste into the editor and drag and drop: NOT CONFIRMED from a primary source.
   - Size limit: NOT CONFIRMED (none documented). A 130 KB body in a URL hash would be 200 KB or more, so prefer file open or paste. GitHub login and so gist/repo loading was removed in an earlier update, so `id=gist:` may not work. https://www.mapbox.com/blog/updating-geojson-io (DOC). Current status NOT CONFIRMED.
   - The repo says there was an early-2026 overhaul on a fork of Placemark Play. https://github.com/mapbox/geojson.io (DOC). The older docs may not match the current UI; a manual check in a browser is needed.
2. Styling: geojson.io supports simplestyle-spec ("mostly back in place" after a regression). https://www.mapbox.com/blog/updating-geojson-io (DOC, older post). Spec properties: `title`, `description`, `marker-size`, `marker-symbol`, `marker-color`, `stroke`, `stroke-opacity`, `stroke-width`, `fill`, `fill-opacity`. https://github.com/mapbox/simplestyle-spec/blob/master/1.1.0/README.md (DOC). Whether the current geojson.io shows `title` in a popup: NOT CONFIRMED. Suggestion: add `marker-color`, `marker-symbol`, `stroke`, `stroke-width` to feature properties; harmless extras.
3. Alternatives with no account: mapshaper.org opens GeoJSON in the browser (warns that very large files may need its CLI). https://mapshaper.org/docs/formats/geojson.html (DOC; drag and drop and account-free use not stated on that page). Others not researched.

## F. Large responses in Postman

- Setting "Max response size" is the largest download in MB; 0 means any size; "Rendering large responses may affect Postman's performance." https://learning.postman.com/latest-v-12/docs/getting-started/installation/settings/general-settings (DOC). A 50 MB default is claimed by https://apidog.com/blog/postman-maximum-response-size-reached (THIRD-PARTY). 130 KB is far below any such limit.
- A documented slowdown for 130 KB in Pretty view: NOT CONFIRMED (not measured; I cannot drive Postman). My estimate: the 5,600-point coordinates array pretty-prints to about 11,000 lines, so it scrolls long.
- Small fields first: sensible for recording because Pretty shows the body from the top, so summary and fuel_stops appear without scrolling and `map` sits last. This is my judgement; that Pretty preserves key order and that fold arrows collapse blocks are NOT CONFIRMED in the docs I read.

## Sample (run here, outside the project)

Folder: `a temporary folder outside the project` (coll.json, fail.json, leaflet.js, svg.js, chk.js). Requests went only to https://postman-echo.com/get with the fake values `New York, NY`, `Los Angeles, CA`, `10`.

Command: `npx -y newman run coll.json --delay-request 1200 --env-var "base_url=https://postman-echo.com" --bail failure`

Output (trimmed):
```
□ Folder A
└ 1 echo query
  GET https://postman-echo.com/get?start=New York, NY&finish=Los Angeles, CA&stop_cost=10 [200 OK, 1.42kB, 404ms]
  √  status 200
  √  start encoded round trip
  √  stop_cost equals 10
  √  stop_cost below 11
  √  stop_cost above 9
  √  args has 3 keys
  √  response time under 5000ms
□ Folder B
└ 2 compare to saved
  GET https://postman-echo.com/get?total=10 [200 OK, 1.21kB, 354ms]
  √  matches saved value from request 1
assertions 8 executed, 0 failed; total run duration: 3.3s
EXIT=0
```
With a deliberately failing assertion (`below(5)`): `1. AssertionError  stop_cost below 11`, EXIT_FAIL=1. Connection error: EXIT_CONNERR=1. Missing file: EXIT_BADFILE=1.

coll.json (works, v2.1.0):
```json
{
  "info": {
    "name": "R2 sample",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [{"key": "base_url", "value": "https://postman-echo.com"}],
  "item": [
    {
      "name": "Folder A",
      "item": [
        {
          "name": "1 echo query",
          "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": [
            "pm.test('status 200', function () { pm.response.to.have.status(200); });",
            "const body = pm.response.json();",
            "pm.test('start encoded round trip', function () { pm.expect(body.args.start).to.eql('New York, NY'); });",
            "pm.test('stop_cost equals 10', function () { pm.expect(body.args.stop_cost).to.eql('10'); });",
            "pm.test('stop_cost below 11', function () { pm.expect(Number(body.args.stop_cost)).to.be.below(11); });",
            "pm.test('stop_cost above 9', function () { pm.expect(Number(body.args.stop_cost)).to.be.above(9); });",
            "pm.test('args has 3 keys', function () { pm.expect(Object.keys(body.args)).to.have.lengthOf(3); });",
            "pm.test('response time under 5000ms', function () { pm.expect(pm.response.responseTime).to.be.below(5000); });",
            "pm.collectionVariables.set('saved_cost', body.args.stop_cost);",
            "pm.visualizer.set('<div>{{x}}</div>', {x: 1});"
          ]}}],
          "request": {
            "method": "GET",
            "header": [],
            "url": {
              "raw": "{{base_url}}/get?start=New York, NY&finish=Los Angeles, CA&stop_cost=10",
              "host": ["{{base_url}}"],
              "path": ["get"],
              "query": [
                {"key": "start", "value": "New York, NY"},
                {"key": "finish", "value": "Los Angeles, CA"},
                {"key": "stop_cost", "value": "10"}
              ]
            }
          }
        }
      ]
    },
    {
      "name": "Folder B",
      "item": [
        {
          "name": "2 compare to saved",
          "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": [
            "const body = pm.response.json();",
            "pm.test('matches saved value from request 1', function () {",
            "  pm.expect(body.args.total).to.eql(pm.collectionVariables.get('saved_cost'));",
            "});"
          ]}}],
          "request": {
            "method": "GET",
            "url": {
              "raw": "{{base_url}}/get?total={{saved_cost}}",
              "host": ["{{base_url}}"],
              "path": ["get"],
              "query": [{"key": "total", "value": "{{saved_cost}}"}]
            }
          }
        }
      ]
    }
  ]
}
```

## Appendix 1: Leaflet visualizer (test script)
```js
const body = pm.response.json();
const template = `
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>html,body{margin:0;padding:0;font-family:sans-serif}#m{height:90vh;min-height:480px}#note{padding:4px 8px;font-size:12px}</style>
<div id="note">Loading map...</div>
<div id="m"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
pm.getData(function (err, data) {
  var note = document.getElementById('note');
  if (err || !data || !data.map) { note.textContent = 'No map data'; return; }
  if (typeof L === 'undefined') { note.textContent = 'Leaflet did not load (CDN blocked?)'; return; }
  var map = L.map('m');
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);
  var lineBounds = null;
  data.map.features.forEach(function (f) {
    if (f.geometry.type === 'LineString') {
      var line = L.geoJSON(f, { style: function () { return { color: '#d6336c', weight: 4 }; } }).addTo(map);
      lineBounds = line.getBounds();
    } else if (f.geometry.type === 'Point') {
      var ll = [f.geometry.coordinates[1], f.geometry.coordinates[0]];
      var el = document.createElement('div');
      el.textContent = (f.properties && f.properties.title) || 'stop';
      L.marker(ll).addTo(map).bindPopup(el);
    }
  });
  if (lineBounds) { map.fitBounds(lineBounds, { padding: [20, 20] }); } else { map.setView([39, -98], 4); }
  note.textContent = data.map.features.length + ' features';
});
</script>`;
pm.visualizer.set(template, { map: body.map });
```

## Appendix 2: SVG fallback visualizer (test script)
```js
const body = pm.response.json();
const feats = body.map.features;
const W = 900, H = 520, PAD = 30;
const line = feats.find(f => f.geometry.type === 'LineString').geometry.coordinates;
const stops = feats.filter(f => f.geometry.type === 'Point');
const lons = line.map(c => c[0]), lats = line.map(c => c[1]);
const minLon = Math.min(...lons), maxLon = Math.max(...lons);
const minLat = Math.min(...lats), maxLat = Math.max(...lats);
// equirectangular, with longitude shrunk by cos(mid latitude) so the shape is not stretched
const k = Math.cos(((minLat + maxLat) / 2) * Math.PI / 180);
const spanX = (maxLon - minLon) * k || 1, spanY = (maxLat - minLat) || 1;
const s = Math.min((W - 2 * PAD) / spanX, (H - 2 * PAD) / spanY);
const offX = (W - spanX * s) / 2, offY = (H - spanY * s) / 2;
const px = lon => (offX + (lon - minLon) * k * s).toFixed(1);
const py = lat => (H - offY - (lat - minLat) * s).toFixed(1);
const esc = t => String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;');
const pts = line.map(c => px(c[0]) + ',' + py(c[1])).join(' ');
const dots = stops.map((f, i) => {
  const x = px(f.geometry.coordinates[0]), y = py(f.geometry.coordinates[1]);
  return '<g><title>' + esc((f.properties && f.properties.title) || '') + '</title>' +
    '<circle cx="' + x + '" cy="' + y + '" r="11" fill="#1c7ed6" stroke="#fff" stroke-width="2"/>' +
    '<text x="' + x + '" y="' + y + '" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#fff" font-family="sans-serif">' + (i + 1) + '</text></g>';
}).join('');
const svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + W + ' ' + H + '" width="100%" style="background:#f1f3f5">' +
  '<polyline fill="none" stroke="#d6336c" stroke-width="3" stroke-linejoin="round" points="' + pts + '"/>' + dots + '</svg>';
pm.visualizer.set('<div style="font-family:sans-serif">{{{svg}}}</div>', { svg: svg });
```
