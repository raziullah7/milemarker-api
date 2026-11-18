# Brief QA-2: independent review of the viewer

A React application in `web/` shows one road trip on a globe: it asks an API once, flies the camera down to the route, draws the route along the road, and shows the fuel stops and the costs in a panel. It has just been built, and the person coordinating the work has read it. You built none of it. Assume it has faults in correctness, in accessibility and in how it fails, and find them.

The repository root is the folder you were given; every path is relative to it. You were also given the commit the work started from.

## Rules

- **Read-only in the repository.** Write only your report, `docs/plan/reports/phase12-Q2.md`. For experiments, copy what you need to the scratch folder you were given. No git command that changes anything. No other agents.
- **No container started or stopped,** and no request to a public routing server. The end-to-end stack is running on `http://127.0.0.1:8000`, with a stand-in routing server and recorded roads: use it. Do not loop requests at the map servers (`tiles.openfreemap.org`, `gibs.earthdata.nasa.gov`): a few page loads at most.
- The rate limit is 60 requests a minute for each client: pace yourself, or your own 429 will look like a fault.

## Read first

- `docs/backend-architecture.md` section 19, and "The front door" in section 18. `docs/requirements.md` FR-18, FR-21 to FR-26, NFR-26 to NFR-29, D-18, D-19.
- `docs/test-cases.md` sections 9.9 to 9.11.
- Then the code under `web/`. Read the builder's report, `docs/plan/reports/phase12-V.md`, last, after you have formed your own view.

## Review

1. **Every figure on screen is the API's.** Take three trips and compare each figure in the panel and on each stop card with the API's answer, by hand. Find any figure the viewer recomputes, rounds differently, or shows in a format the specification does not give.
2. **The timeline's mathematics.** The two running totals, the stop timing, the counters. Feed the pure functions awkward routes in a scratch copy: two points, a repeated point, a route crossing many latitudes, a stop at mile 0 and at the last mile. Does a stop ever appear before the head reaches it, or the counter pass the API's distance?
3. **One request per page view.** Replay, a stop's card, the scrubber, a resize, React's strict mode: does a second request ever reach the API?
4. **Every state, by keyboard only,** in a real browser: bare, loading, playing, finished, each error, suggestions, reduced motion, no WebGL2. Can every control be reached and worked? Is focus visible, and does it ever land somewhere hidden? What does a screen reader hear as the figures count up: a flood, or nothing?
5. **Failure.** The API slow, the API answering HTML, the API answering JSON of the wrong shape, an empty `fuel_stops`, a very long place name, a trip with a warning. The map servers slow, half-answering, answering late. The window resized during the animation; the tab hidden and shown; Skip pressed twice; Replay during a flight.
6. **The page as served:** the content security policy and the console (any violation, any error, any warning); what the page loads from where; the size of what it loads; whether anything is fetched from a third party that the credits do not name.
7. **The credits:** are they what each provider's own page asks for, in every state?
8. **The tests.** Delete a behaviour in a scratch copy (the Mercator timing, the pixel-ratio cap, the 4-second limit, the single request, the reduced-motion path) and see whether a test notices. Name every removal the tests do not notice.
9. **The code:** anything a senior frontend engineer would refuse in review: effects that leak, listeners never removed, a map never destroyed, state held in two places, dead code.

## Your report: `docs/plan/reports/phase12-Q2.md`

- A findings table, most serious first: ID, severity (Critical, Important, Minor, Note), `file:line`, what is wrong, how you showed it, and the smallest fix.
- For review 8, a row per removal: noticed by the tests or not.
- What you checked and found sound, briefly. What you could not check, and why.

Reply to the controller with the count of findings by severity and one line for each Critical and Important.
