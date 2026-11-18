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

## Rulings

- Ruling: the trial is the first part of the viewer builder's work, and the builder stops after it. The controller then opens the trial page in a real browser on this machine, looks at it, measures the frame rate, and decides globe or flat map before the build goes on. Why: a headless browser draws with software, so its frame rate says nothing; only a look on real graphics settles it. Cost if wrong: one round trip.
- Ruling: the proxy tests live in `tests/proxy/` and are not part of the ordinary suite: they need the running end-to-end stack, so they are marked `proxy`, left out by default like the slow test, and run by `make e2e` and by CI's end-to-end job. Why: the ordinary suite must run with no container but the database and Redis.

## Gate 12 checklist

- [ ] The controller has seen the trial in a real browser and recorded what it saw and the frame rate.
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

(Filled in when the phase closes.)
