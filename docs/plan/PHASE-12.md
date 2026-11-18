# Phase 12: The map viewer and the front door

Baseline: `PLAN.md`, Part 2, Phase 12. Specification: `docs/backend-architecture.md` sections 18 ("The front door", "Images") and 19 ("The viewer"); `docs/requirements.md` FR-18, FR-21 to FR-26, NFR-16, NFR-23, NFR-26 to NFR-29, D-17 to D-19, D-23, D-24; `docs/test-cases.md` sections 9.6 and 9.8 to 9.11.

## Inputs from Phase 11

- The API runs on two workers with Redis, a health address, host checking, request IDs and a staged image. It still has a published port on `127.0.0.1` and trusts no proxy: this phase moves the port to nginx and sets `DJANGO_NUM_PROXIES` to 1.
- The OpenAPI document and the Swagger page exist at `/api/v1/schema/` and `/api/v1/docs/`.
- Two public routing calls remain. This phase uses none: everything runs on the stand-in.
- Cut line: if the globe has not passed its gate by Thursday 19 Nov, 8 pm, the viewer ships as a flat map with the same panel, the same data and the same route reveal.

## Tasks

| ID | Task | Who | Owns |
|---|---|---|---|
| 12T | The trial: a throwaway page that proves the globe with night imagery and atmosphere, the fly-in, and the route reveal on the full New York to Los Angeles line | Opus (the viewer's builder, first step) | `web/` |
| 12V | The viewer | Opus, the same agent, after the controller has seen the trial | everything under `web/` except `web/Dockerfile`, `web/.dockerignore` and `web/nginx/` |
| 12N | The front door: nginx, the `web` image, the port move, the proxy tests, CI for the web, the Makefile targets | Sonnet, once the trial has left a `web/` that builds | `web/Dockerfile`, `web/.dockerignore`, `web/nginx/`, both Compose files, `.env.example`, `.github/workflows/ci.yml`, `.github/dependabot.yml`, `Makefile`, `tests/proxy/` |
| QA-2 | Independent review of the viewer: the code, and a keyboard-only walk through every state | Opus | `reports/phase12-Q2.md` |
| QA-3 | Independent security review: nginx, Compose, the settings, both images, the policy | Opus | `reports/phase12-Q3.md` |

Briefs: `briefs/phase12-V-viewer.md` (the trial is its first part), `briefs/phase12-N-frontdoor.md`, `briefs/phase12-Q2-viewer-review.md`, `briefs/phase12-Q3-security.md`.

## What both builders build to

Two agents work at once on things that meet, so the meeting points are fixed here.

**npm scripts**, in `web/package.json`. CI, the Makefile and the image call these names and nothing else:

| Script | Does |
|---|---|
| `npm run dev` | Vite's dev server on `127.0.0.1:5173`, passing `/api` to `http://127.0.0.1:8001` |
| `npm run build` | Type check, then the production build into `web/dist/` |
| `npm run lint` | ESLint |
| `npm run typecheck` | `tsc --noEmit` |
| `npm test` | Vitest, once, not watching |
| `npm run e2e` | Playwright against `VIEWER_URL`, default `http://127.0.0.1:8000` |

**Ports.** The containers belong to 12N: nginx on 8000, the stand-in on 5000. The viewer's builder runs everything from source and starts or stops no container: its own stand-in on 5001, the API from source on 8001 pointed at it, Vite on 5173. Its browser tests take their address from `VIEWER_URL`, so the same tests run against Vite while it builds and against nginx at the gate.

**The image.** `web/Dockerfile`, build context `web/`: a Node stage runs `npm ci` and `npm run build`; the final stage is unprivileged nginx with `web/dist/` and the configuration in `web/nginx/`. Base images pinned by digest.

**The content security policy**, on the viewer's page only. The viewer is built to live under it; 12N sends it. Its starting text, to be changed only with a recorded reason:

```
default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https://tiles.openfreemap.org https://gibs.earthdata.nasa.gov; connect-src 'self' https://tiles.openfreemap.org https://gibs.earthdata.nasa.gov; worker-src 'self' blob:; child-src 'self' blob:; font-src 'self'; object-src 'none'; base-uri 'self'; form-action 'none'; frame-ancestors 'none'
```

**nginx's own error answers** use these messages, which the OpenAPI document already shows: `api_unavailable`, "The API cannot be reached."; the others in the wording the API uses for the same code.

It follows that the viewer loads no script, style or font from another origin: fonts are bundled, and the map library's worker is one of the page's own files.

**Request lines.** gunicorn accepts a request line of up to 8,190 bytes and answers a longer one with its own HTML, which cannot be changed. nginx must therefore refuse, in JSON, any line gunicorn would refuse: its own limit sits below 8,190 bytes. A line of 5,000 bytes must pass nginx and get the API's JSON 400 (review QA-1, finding Q1-05).

## Rulings

- Ruling: the trial is the first part of the viewer builder's work, and the builder stops after it. The controller reads the trial's screenshots as images and decides globe or flat map before the build goes on. Why: the three risky things must be seen to draw before a night is spent on them. Changed on 19 Nov: the controller was to open the page on real graphics and measure the frame rate, but the build runs overnight with nobody at the screen, and the app's own browser does not draw while its window is hidden. So the frame rate on real graphics is judged in the morning, by the user and the controller together, and the flat map stays available until the cut line. Cost if wrong: the globe is built and then replaced, a few hours of the builder's work on the map module only; the panel, the timeline and the tests carry over.
- Ruling: the proxy tests live in `tests/proxy/` and are not part of the ordinary suite: they need the running end-to-end stack, so they are marked `proxy`, left out by default like the slow test, and run by `make e2e` and by CI's end-to-end job. Why: the ordinary suite must run with no container but the database and Redis.

- Ruling: the user explores the backend on this machine for the first hours of this phase. Until the user says so, only the viewer's builder runs: it touches nothing but `web/` and no container. 12N, which rebuilds and restarts containers, starts after that.
- Ruling, on spending (the user asked on 18 Nov for careful use of the weekly limit, without loss of quality): Opus builds the viewer and runs the two adversarial reviews; Sonnet builds the front door, makes specified fixes and re-reads them. A builder runs each suite once at the end, and the controller once more. The reading is logged at each gate; no new work starts above 93%.

### The trial, and the rulings on it

The trial page drew all three things on the full New York to Los Angeles line (5,594 points), in headless Chromium with the real map servers. The controller read its four screenshots (`web/trial-shots/`, not committed):

- 1 s: the night-side globe on a black page, city lights across the eastern United States, a thin lit rim along the upper edge. It reads as the Earth at night.
- 5 s: in flight over North America, the lights crisp, a glowing horizon.
- 10 s and 16 s: arrived and tilted; the route drawn in cyan with seven amber stops, correct and on the road. But the view no longer reads as night: a flat grey road map, dense place names that compete with the route, a thin line, the lower third of the screen given to Mexico and the Gulf, and the map library's light credit box glaring on the dark page.

Frame times were about 135 ms in software drawing, which says nothing of real graphics; three updates a frame, as specified.

- Ruling: **the globe is built.** Why: the three risky things work, the area around the globe is transparent, and what is wrong at arrival is styling, not feasibility. The flat map stays the fallback until the cut line, to be judged on real graphics when the user is back.
- Ruling: **the US state lines come from `us-atlas`,** the US Census Bureau's cartographic boundaries (public domain), and land and country lines from `world-atlas`, which is Natural Earth. Why: no npm package carries Natural Earth's state lines, and fetching a file from outside npm needs a permission nobody is awake to give. The specification said Natural Earth for both; architecture section 19 is corrected, and the credit names both sources. Cost if wrong: one data file and one credit line to swap.
- Ruling, for the build: the arrival view must still read as night. The route is the brightest thing on screen; place names are few and dim; the built-in outlines do not show doubled beside the road map's own lines; the route sits in the middle of the map area the panel leaves free; the finish marker is not hidden under the line's head; the credits are styled for a dark page and still always on screen, and name only the sources whose tiles are actually drawn.
- Found by the trial and carried into the build: the glow needs the style's `light` as well as its `sky`; NASA's tile address is row before column; TypeScript is pinned at 6.0.3, the newest the lint tools accept; shapes cut at the antimeridian must be made continuous.

## Gate 12 checklist

- [x] The controller has read the trial's screenshots and recorded what it saw; the frame rate on real graphics is recorded when the user is back.
- [ ] The controller has read every diff.
- [ ] Web: `npm run lint`, `npm run typecheck`, `npm test` and `npm run build` are clean.
- [ ] The backend suite, coverage, the slow test, mypy, Ruff and the deployment check are still clean.
- [ ] From `down -v`, `docker compose up --build` with no `.env` serves the viewer at `http://127.0.0.1:8000/` and the API behind it; `api` has no published port.
- [ ] Through nginx: Newman passes; the 61st request with forged forwarded addresses gets 429; a second client has its own bucket; responses are compressed; with `api` stopped the answer is JSON `api_unavailable`; a foreign `Host` gets 400.
- [ ] The browser tests pass through nginx on the end-to-end stack, with the accessibility scan, no WebGL2, reduced motion, and no request to a map server.
- [ ] The controller has watched the whole animation on the ordinary stack in a real browser, with the real map servers, and recorded what it saw (VB-27).
- [ ] The values left open by the specification are recorded in the test cases: the fixed sentences, the credit wording with its sources, the policy's text, the route colour and the image tolerances.
- [ ] QA-2's and QA-3's findings are ruled, fixed, and re-read by a reviewer who did not write the fixes.
- [ ] CI is green on `next`, with the web jobs. `next` is merged into `main`.
- [ ] Committed.

## Result

**Parked on 19 Nov 2026, by the owner's decision.** The assignment is for a backend role, and an outside reading of the repository found it far beyond the task. The viewer and the front door are not part of this submission (`PHASE-13.md` records the decision in the owner's words).

- **What exists,** on the branch `viewer` (commit c833b98, not on `main`): the React, TypeScript and Vite scaffold with its six scripts, and the trial page, which draws the night-side globe, flies down to the route and reveals it on the full New York to Los Angeles line. Four screenshots of the trial are kept with it. The builder's report, `reports/phase12-V.md` on that branch, ends with what to do first.
- **Not built:** the viewer itself (the panel, the timeline, the map module, the animation, the tests), nginx, the `web` service, and the two reviews QA-2 and QA-3.
- **Never measured:** the frame rate on real graphics.
- **The gate above was not run.** Its specification stays in the documents, marked as parked, so the branch keeps the text it was being built to.
