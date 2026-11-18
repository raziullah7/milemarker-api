# Brief 12N: the front door

A Django API runs in Docker Compose behind its own published port. A map viewer, a React application in `web/`, is being built beside it by another builder. You are putting nginx in front of both: it serves the viewer, passes everything else to the API, and becomes the only way in. It is specified in full and its test cases are written.

The repository root is the folder you were given; every path is relative to it.

## Rules

- **Your files:** `web/Dockerfile`, `web/.dockerignore`, everything under `web/nginx/`, `docker-compose.yml`, `docker-compose.e2e.yml`, `.env.example`, `.github/workflows/ci.yml`, `.github/dependabot.yml`, `Makefile`, `tests/proxy/` (new), the `proxy` marker in `pyproject.toml` (that one addition only), and your report `docs/plan/reports/phase12-N.md`.
- **Not yours:** everything else under `web/` (the viewer's builder is working there now), the API's code and settings, `uv.lock`, the documents. If you believe one of those must change, stop and say so in your reply.
- **You own the containers:** only you start, stop and break them. The viewer's builder uses ports 5001, 5173 and 8001 from source; stay off those.
- **No request to a public routing server, ever.** Send trips only to the end-to-end stack (`docker-compose.yml` with `docker-compose.e2e.yml`), whose API points at the stand-in: check `ROUTING_SERVERS` in the running container before the first one. To see that the ordinary stack is alive, use the health address or a trip refused before routing (`start=Chicgo, IL`).
- **The API's answers pass through untouched:** body, status and its own headers. The independent verifier and the Postman collection must pass through nginx unchanged.
- **Test first.** The cases are written, with inputs and expected outputs: build to them. If one is wrong or cannot be built as written, do not change it: say so in your report, with what you built instead.
- **Simplest thing that meets the specification.** One nginx configuration, no templating unless a value must come from the environment.
- No git command that changes anything. No other agents.

## Read first, in full

- `docs/backend-architecture.md` section 18: "Services", "Start order", "Configuration", "The front door", "Images", "Commands". Section 11's error table, for the error shape nginx must write itself.
- `docs/requirements.md`: NFR-16, NFR-19, NFR-23, D-17, D-23, D-24, acceptance checks 14, 16 and 20.
- `docs/test-cases.md` section 9.1 (test data), 9.6 (PX: every case), 9.8 (EE), and in 9.2 the cases that waited for nginx: CF-18, CF-19, CF-21, CF-30, CF-33. In 9.12 the cases about the web jobs and targets.
- `docs/plan/PHASE-12.md`: "What both builders build to" (the npm script names, the ports, the image, and the content security policy's text) and the two rulings.
- `docs/plan/PHASE-9.md`: in "Rulings on the audits", findings Q0a-04 and N3; in the "settled" sections, every row about nginx, the proxy and the policy.
- `docker-compose.yml`, `docker-compose.e2e.yml`, `Dockerfile`, `Makefile`, `.github/workflows/ci.yml`, `gunicorn.conf.py`, `trips/middleware.py`, `config/settings.py`.

## Build

1. **The `web` image,** `web/Dockerfile`, build context `web/`: a Node stage that runs `npm ci` and `npm run build`; a final stage of unprivileged nginx holding `web/dist/` and your configuration, and nothing else. Base images pinned by digest. `web/.dockerignore` keeps `node_modules`, test output and the like out of the context.
2. **nginx,** as "The front door" specifies, point by point: the viewer at `/` and `/assets/`; everything else to `api`; the client's own `Host` passed on; a request ID of nginx's own replacing any the client sent; `X-Forwarded-For` overwritten, never appended to; compression of JSON and of the viewer's files; 30 seconds for the API to answer; `api_unavailable`, the 400 for a request it refuses and the 404 under `/assets/` written by nginx as JSON in the API's error shape; the security headers from one place each, never twice; the content security policy on the viewer's page only, with the text in `PHASE-12.md`; long cache lifetimes for the fingerprinted files under `/assets/` and none for the page itself; an access log line that carries the request ID.
3. **Compose:** a `web` service published on `${BIND_ADDRESS:-127.0.0.1}:${API_PORT:-8000}`, started after `api` is healthy, with a health check and a restart policy. `api` loses its published port and gets `DJANGO_NUM_PROXIES` 1. The API's network has no route out except what it needs: it must still reach the routing servers in the ordinary stack, so think before you isolate it, and say what you chose. In the end-to-end file the stand-in stays reachable from this machine on port 5000.
4. **The proxy tests,** `tests/proxy/`, in pytest with the marker `proxy`, left out of the ordinary run like the slow test: the PX cases against the running end-to-end stack. Those that stop or pause a service (PX-09, PX-10, PX-11) restore it afterwards, whatever happens. PX-08 needs a second client address: find a sound way to make one, and say what you chose.
5. **The Makefile:** `web-dev`; `e2e` runs Newman, then the proxy tests, then the viewer's browser tests (`npm run e2e` in `web/`); `up`, `logs` and the rest still true. Each recipe line one plain command, as now. `make help` lists the new targets.
6. **CI:** a `web` job (Node pinned, `npm ci`, `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`, and `npm audit --omit=dev --audit-level=high`); the image job builds the `web` image too; the end-to-end job runs the proxy tests and the browser tests against the stack, with Playwright's browser installed and its report kept on failure. Dependabot watches `web/` for npm and its Dockerfile.
7. **`.env.example`:** `BIND_ADDRESS` now read; `DJANGO_NUM_PROXIES` as the stack sets it; anything else that changed.

## Traps

- The viewer's builder is changing `web/` while you work. If `npm run build` fails inside your image because of work in progress, wait and try again; do not fix the viewer. To test nginx without waiting, a page that already builds is enough.
- nginx's `add_header` in a location replaces, not adds to, the headers of the level above: headers vanish silently. And `add_header` without `always` is not sent on error answers.
- `proxy_set_header X-Forwarded-For $remote_addr`, not `$proxy_add_x_forwarded_for`: the second appends to what the client sent, and the rate limit would count a forged address.
- Docker's embedded DNS answers for `api` at start-up only unless nginx is told to look again: after `api` is recreated, nginx must still find it.
- When the API is stopped its name leaves Docker's DNS: `api_unavailable` must still be JSON then, and must come promptly, not after a long name lookup.
- nginx's own 400 for a request line that is too long is sent before any `location` applies: check that PX-14 really gets JSON.
- The unprivileged nginx image listens on 8080 by default and cannot write to most of its file system.
- The Swagger page loads a script from a CDN: no content security policy on it.
- `docker compose down` on the end-to-end files stops the database too. Leave the ordinary stack running when you finish, and say what state you left.
- On this machine never use `localhost`: use `127.0.0.1`. Shell here-documents that contain apostrophes fail here: write a helper script to a file and run the file.
- The rate limit is 60 a minute for each client: a run of tests can use it up and fail the next run. Wait a minute between runs, or say how your tests avoid it.

## Prove it

1. `uv run pytest` in full, `uv run pytest --cov`, `uv run pytest -m slow`, `uv run mypy`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run python manage.py check --deploy --fail-level WARNING`: clean, as before.
2. From `docker compose down -v`: `docker compose up --build -d` with no `.env`. Show the services, the published ports (`api` has none), and the answers of `/`, `/api/v1/health/` and a trip refused before routing.
3. The end-to-end stack: `make e2e` in full: Newman (14 requests, 111 assertions), the proxy tests, the browser tests if the viewer has them yet. The stand-in's request count.
4. Each PX case, with what was sent and what came back.
5. `docker compose --profile test run --rm test`: the suite in a container.
6. Leave the ordinary stack running, and say what state you left it in.

Run one pytest process at a time, in the foreground. Leave nothing running in the background.

## Your report: `docs/plan/reports/phase12-N.md`

What you built, file by file; the nginx configuration's decisions, each with its reason; the PX cases, and any not built as written; the commands of "Prove it" with their output; anything you are unsure of.

Reply to the controller with: status, the test counts, the outcome of each "Prove it" step in a line, and any concern.
