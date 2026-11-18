# Brief 12V: the map viewer

An API plans a road trip across the USA and returns the route as GeoJSON with the fuel stops and the costs. You are building the page that shows one such trip: a night-side globe that turns, a camera that flies down to the route, the route drawing itself along the road while the stops and the figures appear. It has to look excellent, and it has to be correct: every figure on screen is the API's own.

It is specified in full. Your work is in two parts, and you stop after the first.

The repository root is the folder you were given; every path is relative to it.

## Rules

- **Your files:** everything under `web/`, except `web/Dockerfile`, `web/.dockerignore` and `web/nginx/`, which belong to another builder working at the same time. Your report: `docs/plan/reports/phase12-V.md`. Nothing else: no Python, no Compose file, no CI file, no Makefile, no other document. If you believe one of those must change, say so in your reply.
- **No container started or stopped,** and nothing on ports 8000 or 5000: they are the other builder's. You run from source, as "Running it while you build" below says.
- **No request to a public routing server, ever.** Trips come from the stand-in routing server and its recorded roads.
- **The map servers** (`tiles.openfreemap.org`, `gibs.earthdata.nasa.gov`) may be reached from your own browser checks, lightly: a few page loads, not a loop. No automated test may reach them: the browser tests answer or refuse every such request themselves.
- **Test first** for the calculations and the panel: each behaviour starts with a test that fails for the stated reason. The test cases are written, with inputs and expected outputs: build to them. If a case is wrong or cannot be built as written, do not change it: say so in your report, with what you built instead.
- **Simplest thing that meets the specification.** No router, no state library, no UI kit, no option the specification does not ask for.
- Each module opens with a description of what it is for; comments say why, not what; plain names.
- No git command that changes anything. No other agents.
- Keep `npm run build` passing whenever you pause: the other builder builds the image from your folder.

## Read first, in full

- `docs/backend-architecture.md` section 19 ("The viewer"), and in section 18 "The front door". Section 11 for the API's answer, field by field, and its error table.
- `docs/requirements.md`: FR-18, FR-21 to FR-26, NFR-26 to NFR-29, D-18, D-19, acceptance checks 17 to 19.
- `docs/test-cases.md` section 9.1 (the test data and the test IDs, which are binding), 9.9 (VT: the calculations), 9.10 (VP: the panel), 9.11 (VB: in a browser).
- `docs/use-cases.md`: UC-21 to UC-28.
- `docs/plan/PHASE-9.md`: in the three "settled" sections, every row about the viewer.
- `docs/plan/PHASE-12.md`: "What both builders build to": the npm script names, the ports, and the content security policy your page must live under.
- `docs/openapi.yaml` for the answer's exact shape, and a real answer: ask the API for one (below).

## Running it while you build

Everything from source, on ports of your own. The database and Redis are already running in Docker on `127.0.0.1`; leave them alone.

1. The stand-in routing server: `uv run python scripts/fake_osrm.py --port 5001`.
2. The API, pointed at it, on port 8001 (set the variable in the way your shell needs): `ROUTING_SERVERS="http://127.0.0.1:5001/route/v1/driving/{coords}?overview=full&geometries=geojson"` then `uv run python manage.py runserver 127.0.0.1:8001`.
3. `npm run dev` in `web/`: Vite on `127.0.0.1:5173`, passing `/api` to port 8001.

The stand-in knows 21 recorded roads (`tests/conftest.py` lists them), among them the three example trips. A trip it does not know is answered as "no route". Stop all three when you finish each part; leave nothing running.

On this machine never use `localhost`: it stalls connections. Use `127.0.0.1`. Shell here-documents that contain apostrophes fail here: write a helper script to a file and run the file.

## What is known already

From research against the libraries' own documentation on 18 Nov 2026. Check each against the version you install; where one is wrong, say so in your report.

- Versions: `maplibre-gl` 6.19.0, `react` and `react-dom` 19.3.1, `vite` 8.3.8, `motion` 14.14.0, `vitest` 5.1.1, `@playwright/test` 1.65.1, TypeScript in strict mode. Pin exact versions, and commit the lock file.
- MapLibre 6 is ESM only and needs WebGL2. Under Vite its worker must be given to it: import `maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url` and pass the address to `setWorkerUrl` before the first map is made. The worker is then one of the page's own files, which the content security policy requires.
- The globe: the style's `projection` is `{type: 'globe'}`; the glow is the style's `sky` with `atmosphere-blend`.
- Night imagery: NASA GIBS layer `VIIRS_Black_Marble`, raster tiles, zoom 0 to 8.
- Up close: OpenFreeMap's dark style, `https://tiles.openfreemap.org/styles/dark`.
- The reveal: a line layer on a GeoJSON source with `lineMetrics: true`, and `line-gradient` set to `['step', ['line-progress'], colour, p, transparent]`. Each frame changes only `p`. `line-progress` measures length in Web Mercator, not on the ground: that is why section 19 keeps two running totals per point.
- Fitting the camera to the route: `fitBounds` with a pitch and a bearing. On the globe the fit ignores the pitch, so pad more than looks necessary.
- Markers are HTML markers, hidden when the globe covers them (`opacityWhenCovered: '0'`).
- Reduced motion: the finished state reached with `jumpTo`, no flight. The idle turn of the bare globe is a chain of `easeTo` calls.
- The pixel ratio is capped at 2.

Not known, and for the trial to find out: whether the area around the globe is transparent (so a star field can sit behind it) or painted; how the night imagery and the vector map are best cross-faded as the camera comes down; whether the built-in outlines read well under both.

## Part 1: the trial, then stop

One throwaway page, reachable at `http://127.0.0.1:5173/trial.html`, that settles whether the globe is worth building. It shows, on the full New York to Los Angeles line from the API (about 5,600 points):

1. the globe with the night imagery and the atmosphere, on a black page, turning;
2. the flight from space down to the route, tilted on arrival, the night imagery giving way to the dark road map;
3. the route revealing itself by the moving colour boundary, with a glow and a bright head;
4. a frame counter on the page: the average and the worst frame time over the reveal, written into the page as text and to `window.__trial` so it can be read from outside.

Set the project up properly while you do it (the scaffold, the scripts of `PHASE-12.md`, the pinned versions, strict TypeScript, ESLint), because the build goes on from it; only the trial page itself is thrown away.

Look at it yourself: take screenshots with Playwright at 1, 5, 10 and 16 seconds and read them as images. A headless browser draws with software, so its frame times mean nothing on their own; record them anyway, and save the four screenshots under `web/trial-shots/` (a folder git ignores) so the controller can read them. Say plainly what you see in each screenshot, including what looks wrong.

Then write the first section of your report and **stop**. Reply with: whether the three things work, what you saw, the answers to the three unknowns above, anything in "What is known already" that turned out wrong, and the exact commands to start the three processes so the controller can open the page. Leave the three processes stopped.

## Part 2: the build, only when the controller says go

The controller will tell you one of: build the globe as specified, or build the flat map (the same panel, data and reveal on a flat projection). Then:

1. **The timeline:** pure functions with no React, no map library and no network. The VT cases.
2. **The API client:** the one module that calls the API. Errors as the code and the details, and the unreachable API as its own outcome.
3. **The panel:** its components and every state: bare with the three examples, loading, a plan, each of the 13 error codes, suggestions as links, the warning, reduced motion, no WebGL2. The VP cases. The formats of section 19, exactly.
4. **The map module:** the only code that touches MapLibre: the globe, the camera, the outlines beneath everything, the remote map with its 4-second limit, the route and its boundary, the markers, the flight to a stop.
5. **The animation,** on one clock, to the storyboard of section 19: the beats, Skip, Replay, the scrubber, and cancelling by a press, a wheel turn, a touch or Escape.
6. **The fallbacks** of section 19, and the credits, on screen in every state, with the wording and links each provider asks for, copied from the provider's own page.
7. **The browser tests:** the VB cases, in Playwright, against `VIEWER_URL`. They must pass against your Vite server now and against nginx on port 8000 later, unchanged. VB-20 (the policy) can only be seen through nginx: write it so it holds there.
8. **Design.** Use the `frontend-design` skill before you style anything. The brief is: night, altitude, instruments. A black page, the globe as the only light, a panel that reads like a flight instrument and not like a dashboard template: restrained type, figures in a tabular face, nothing decorative that does not carry information. It must hold at a phone's width (the panel under the map) and on a wide screen (the panel beside it).

## Traps

- The answer's `map` is GeoJSON: a feature collection whose line has about 5,600 points coast to coast. Give it to the map once per trip.
- A stop's `lat` and `lng` lie on the route line, but not at one of its points: place it by the nearest segment.
- Stop 1 is at mile 0: it appears as the line starts, at 8 s, not before.
- The API's money and miles are numbers; a price per gallon is shown exactly as given, three decimals. Never recompute a figure the API gave.
- With only `start` or only `finish` in the address, ask the API and show its `invalid_request`; "no trip" means neither.
- A second request to the API must never happen for one page view: not on Replay, not on a card, not on a re-render in React's strict mode.
- The browser tests must not depend on a map server: answer or refuse those requests in the test.
- Screenshots compared in a test must come from the built-in outlines only, with animations settled; software drawing differs between machines, so say what tolerance you chose and why.

## Prove it

`npm run lint`, `npm run typecheck`, `npm test`, `npm run build`: clean. `npm run e2e` against your Vite server: every VB case that does not need nginx passes; name each that does. Then say what you saw: screenshots at the bare page, loading, 5 s, 10 s, the finished state, an error, the phone width, read as images and described honestly.

## Your report: `docs/plan/reports/phase12-V.md`

Part 1: as above. Part 2: what you built, module by module; the cases built in each section, and any not built as written; every value the specification left to this phase: each fixed sentence, the credit wording with the address of the page it came from, the route's colour, the screenshot tolerance; the commands with their output; what you saw; anything you are unsure of.

Reply to the controller with: status, the test counts, and any concern.
