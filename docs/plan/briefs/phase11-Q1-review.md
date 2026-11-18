# Brief QA-1: adversarial review of the backend runtime

A Django API that ran as one process with an in-memory cache has just been rebuilt to run as two worker processes on a shared Redis cache with a fallback, with host checking, a health address, settings from the environment, a staged image and a one-off setup step. The person coordinating the work has read it. You built none of it. Your job is to break it: assume there is a fault in how it behaves under failure, concurrency and misconfiguration, and find it.

The repository root is the folder you were given; every path is relative to it. You were also given the commit the work started from; `git diff <that commit>` shows everything.

## Rules

- **Read-only in the repository.** Write only your report, `docs/plan/reports/phase11-Q1.md`. For experiments on the code, copy what you need to the scratch folder you were given and work there. No git command that changes anything. No other agents.
- **No request to a public routing server, ever.** You may start, stop and break the **end-to-end stack** (`docker compose -f docker-compose.yml -f docker-compose.e2e.yml ...`), which uses a stand-in routing server and recorded roads: stop Redis, stop the database, kill a worker, restart things. A trip is only safe to request when the API points at the stand-in: check `ROUTING_SERVERS` in the running container before you send one. When you finish, bring the ordinary stack back (`docker compose up -d`) and say what state you left.
- You may run the tests, one pytest process at a time, in the foreground, with the `DATABASE_URL` you were given. Use `127.0.0.1`, never `localhost`.

## Read first

- `docs/backend-architecture.md` sections 10, 11 and 18: what it is meant to do. `docs/requirements.md` NFR-16 to NFR-25, D-15 to D-17, D-21, acceptance checks 11 to 16.
- `docs/test-cases.md` sections 9.2 to 9.5: the cases written for it.
- Then the code and the diff. Read the builders' reports, `docs/plan/reports/phase11-K.md` and `phase11-S.md`, last, after you have formed your own view.

## Attack

1. **The cache and its fallback.** Stop Redis while requests are in flight. Make Redis slow instead of dead (pause its container). Start it again. Does any request fail, or take more than about half a second longer because of Redis? Does each worker log one warning per outage, or one per request, or none? After Redis returns, are the two workers' in-memory copies ever served in place of Redis, stale? Can a value written during fallback surprise a reader after recovery? What does the health address say at each moment, from each worker? Each Redis call runs on a pool of threads with a deadline of 0.4 seconds (`docs/plan/PHASE-11.md`, "Rulings on 11K's report"): can the pool be exhausted, can an abandoned call do harm when it finishes late, does anything leak, and does the first request after `docker compose stop redis` really come back within half a second on each worker?
2. **Keys.** Change the station data (reload with a changed price in a scratch copy of the CSV) while answers are cached: is an old answer ever served? Raise the key version: same question. Can two different trips share a key? Can a client make a key of unbounded length or with characters Redis or Django refuse?
3. **The rate limit.** With two workers on Redis, is the limit 60 a minute in total, or 60 per worker? During fallback? Send forged `X-Forwarded-For` with the proxy count at 0 and at 1. Is the health address really exempt, and are the schema and docs addresses really limited?
4. **Delete the safety and see if the tests notice.** In a scratch copy: remove the fallback, remove the 30-second pause, remove the version from the key, remove the fingerprint, remove the host check, remove the lock on the station index, set retries back to the client's default, remove the 0.4-second deadline on a Redis call, remove the check on a client's `X-Request-ID`. For each, do the tests fail? Name every removal the suite does not notice.
5. **Start-up and shutdown.** From `down -v`: does everything come up in order with no `.env`? What if the setup step fails (point it at a database that does not exist)? What if Redis is down at start? Start the stack twice: are stations doubled? Stop the API during a request that is waiting on routing (the stand-in can be paused): is the request cut, or allowed to finish? What happens to a worker that dies?
6. **Configuration.** Each environment variable with an empty value, a wrong type, a hostile value. `DJANGO_ALLOWED_HOSTS` with a foreign host, a port, a wildcard. `DJANGO_DEBUG=1`: does any error answer stop being JSON, or leak a traceback? Run `manage.py check --deploy --fail-level WARNING`, and read each silenced check's reason: is it true?
7. **The image.** What is in the running image that should not be (tests, documents, the lock tool, a compiler)? Who does it run as, and what can that user write? Are the base images pinned as claimed?
8. **The OpenAPI document.** Is everything it says true of the running code? Find a field, a type, a limit or an error it gets wrong or leaves out. Does the test that compares it with the code fail when the code changes (change a field in a scratch copy)?
9. **Regressions.** The body and status of the route's answers must be unchanged: the independent verifier and the regression pins prove it; run them. Anything else you notice in the diff.

## Your report: `docs/plan/reports/phase11-Q1.md`

- A findings table, most serious first: ID, severity (Critical, Important, Minor, Note), `file:line`, what is wrong, how you showed it (the command or the edit, and what happened), and the smallest fix.
- For attack 4, a row per removal: noticed by the tests or not.
- What you attacked and found sound, briefly. What you could not check, and why.

Reply to the controller with the count of findings by severity and one line for each Critical and Important.
