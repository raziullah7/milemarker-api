# Brief 9-Q0a: independent audit of the delivery side

This repository is a finished take-home assessment: a Django API that plans the cheapest fuel stops for a road trip in the USA. It is public and will be read by the engineers who set the task. You built none of it. Find what is wrong, weak, false or below the standard a careful senior backend engineer expects, in the parts below. No independent reviewer has read these parts before.

You were given two folders: a frozen copy of release `v1.0.0` to audit, and the path for your report. Every path below is relative to the frozen copy.

## Rules

- **Read-only.** Write only your report. No git command that changes anything. No other agents.
- **Do not run pytest. Do not start, stop or rebuild containers.** Another reviewer is using the test database, and the running stack must stay as it is.
- **No request may reach the public routing servers.** The API from this release is running at `http://127.0.0.1:8000`. You may send it `GET /api/v1/route/?start=Dallas, TX&finish=Houston, TX` (cached, free) and any request that is refused before routing: a missing parameter, an unknown place, a place outside coverage, a wrong method, an unknown path. Send no other trip.
- You may run read-only commands: `docker compose config`, `docker compose ps`, `docker compose logs api`, `docker image ls`, `docker history`, `git log`, `git ls-files`, `uv tree`.
- Judge what is there. Do not accept a thing as right because a document says it was checked.

## Scope

1. **Configuration and security:** `config/settings.py`, `config/urls.py`, `config/wsgi.py`, `.env.example`, `.gitignore`, `.gitattributes`, `pyproject.toml`, `uv.lock`.
2. **Container:** `Dockerfile`, `.dockerignore`, `docker/entrypoint.sh`, `docker-compose.yml`. What is in the image, who it runs as, how it starts, how it fails, what a restart does.
3. **The README:** every command, path, number and claim checked against the repository and the running API. Follow it as a stranger would. Note what a reviewer of a take-home would look for and not find.
4. **The Postman collection:** `docs/postman/milemarker.postman_collection.json`. Is each check meaningful? Could a check pass on a wrong answer? Will it import and read well in the Postman app? Is the map script on the Demo requests sound? It has only ever run under Newman; nobody has seen it draw.
5. **The repository as a public artifact:** the file tree, the commit history and messages, anything tracked that should not be, anything missing, and whether `docs/` agrees with the code. Sample `docs/requirements.md` section 9, `docs/backend-architecture.md` sections 4, 9, 10, 11 and 16, `docs/test-cases.md` section 7, and `data/README.md`.

The assignment, for reference: build an API in the latest stable Django that takes a start and a finish in the USA and returns a map of the route, the cheapest fuel stops for a vehicle with a 500-mile range at 10 miles per gallon, and the total fuel cost, using the supplied price file and a free routing API, with as few routing calls as possible (one is ideal) and a fast response. Deliverables: the code, and a short video demonstrating it in Postman.

## What is already going to change

The next stage of work replaces or adds these, so a finding that only says one of them is missing is worth a single line, not an investigation:

- Settings read from the environment; host checking on; the security middleware; no secret key in code.
- nginx in front of gunicorn; two workers; Redis for the caches and the rate limit; migrations and the station load moved out of the entrypoint into a one-off service.
- A health endpoint, health checks, graceful shutdown, a multi-stage image.
- An OpenAPI page, CI, a Makefile, a licence file, a web page that draws the map.

Spend your time on what those changes will not fix by themselves: wrong or unprovable claims, checks that prove nothing, traps the new work will fall into, and anything in the surviving files that a reviewer would mark down.

## Standard

Common practice for a small production-minded Django service and its repository. Some choices here are deliberate and written down (`docs/requirements.md` section 6, `docs/backend-architecture.md` sections 15 and 16, comments in `config/settings.py`). A written reason does not make a choice right. Where you think one is wrong, say so, mark it "documented decision", and give your reason.

Do not propose features. A finding is a fault, a risk, a false or unprovable claim, or a gap a reviewer would notice.

## Your report

- A findings table, most serious first: ID, severity (Critical, Important, Minor, Note), `file:line`, what is wrong, a concrete scenario in which it bites, and the smallest fix.
- What you checked and found sound, briefly, so the coverage of the audit is visible.
- What you could not check, and why.

Reply to the controller with the count of findings by severity and one line for each Critical and Important.
