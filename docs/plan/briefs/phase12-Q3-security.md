# Brief QA-3: independent security review of the whole stack

A Django API, a React viewer, nginx in front of both, PostgreSQL and Redis behind, in Docker Compose. It is meant to be safe to put behind a TLS terminator and run. It has no users, no sessions, no cookies and no secrets beyond a local development database password. The person coordinating the work has read it. You built none of it. Assume it can be abused, and find how.

The repository root is the folder you were given; every path is relative to it. You were also given the commit the work started from.

## Rules

- **Read-only in the repository.** Write only your report, `docs/plan/reports/phase12-Q3.md`. For experiments, copy what you need to the scratch folder you were given. No git command that changes anything. No other agents.
- **No request to a public routing server, ever.** You may start, stop and break the **end-to-end stack** (`docker compose -f docker-compose.yml -f docker-compose.e2e.yml ...`), which uses a stand-in routing server: check `ROUTING_SERVERS` in the running container before you send a trip. When you finish, bring the ordinary stack back (`docker compose up -d`) and say what state you left.
- Attack only this machine's own stack on `127.0.0.1`. Nothing else.

## Read first

- `docs/backend-architecture.md` sections 12 and 18. `docs/requirements.md` NFR-16, NFR-20, NFR-21, NFR-25, D-17, D-21, D-23, D-24.
- Then the code: `web/nginx/`, `web/Dockerfile`, both Compose files, `Dockerfile`, `config/settings.py`, `trips/middleware.py`, `gunicorn.conf.py`, `.github/`.
- The builders' reports last.

## Attack

1. **The rate limit.** Any way for one client to get more than 60 requests a minute: forged `X-Forwarded-For` in every form (several values, IPv6, garbage), `X-Real-IP`, `Forwarded`, reaching the API without nginx, the addresses that are exempt, upper and lower case, a trailing slash, HTTP/1.0, pipelining. Any way for one client to exhaust another's bucket.
2. **What is reachable.** Every published port and what it is bound to. Can Redis or PostgreSQL be reached from another machine? Can the API be reached without nginx? What can a container reach that it should not?
3. **nginx.** Request smuggling between nginx and gunicorn (conflicting lengths, chunked tricks); path tricks under `/assets/` (`..`, encoded slashes, a file outside the folder); a `Host` header used to poison anything; header injection through the request ID or any header nginx copies; an oversized header, body or address; slow requests holding connections; what an error page reveals (versions, paths).
4. **Headers and the policy.** Each security header on each kind of answer, once and only once. Read the content security policy as an attacker: what does it allow that the page does not need? Can the Swagger page, which has no policy, be used against the viewer on the same origin?
5. **The viewer as an injection surface.** Place names, station names, the API's `message`, suggestions and the address's own parameters all reach the page: can any of them run script or forge a link? Try a `start` that is HTML, a `javascript:` address, a suggestion link built from hostile text.
6. **The images.** Who each process runs as; what it can write; what is in each image that should not be; whether base images are pinned; whether a secret, a key or a personal detail is in any layer, in the repository, or in its history.
7. **Configuration.** `DJANGO_DEBUG=1` through the whole stack: does anything leak? A wildcard or empty `DJANGO_ALLOWED_HOSTS`. `BIND_ADDRESS=0.0.0.0`: what is then exposed, and does the README say so?
8. **The supply chain.** Dependencies with known faults (`pip-audit`, `npm audit`), scripts that run at install, the CDN script of the Swagger page (pinned? with an integrity hash?), the workflow's permissions and the actions it uses.
9. **The logs.** Can a client write a false line, or a very long one, into them? Is anything logged that should not be?

## Your report: `docs/plan/reports/phase12-Q3.md`

- A findings table, most serious first: ID, severity (Critical, Important, Minor, Note), `file:line`, what is wrong, how you showed it (the request or the command, and what came back), and the smallest fix.
- What you attacked and found sound, briefly. What you could not check, and why.

Reply to the controller with the count of findings by severity and one line for each Critical and Important.
