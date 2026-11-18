# Report 9S: the specifications brought in line with Part 2

Status: done. Three files changed: `docs/requirements.md`, `docs/backend-architecture.md`, `docs/prd.md`. 27 gaps, each marked `**Open:**` (or `Open` in a table cell) where it sits in the architecture document. Nothing else touched; no git command, no tests, no containers.

Line numbers are those of the files as I left them. "Arch" is `docs/backend-architecture.md`, "Req" is `docs/requirements.md`.

## Where each row of "The spec changes" now lives

### Requirements changed

| Row | Where |
|---|---|
| FR-18, now Want | Req §4, line 72. Arch §19 (line 742 on) |
| FR-19, now Want | Req §4, line 73. Arch §11 "Other addresses", lines 457–488 |
| NFR-9 | Req §5, line 103. Arch §18, line 637 |
| NFR-16, sentence added | Req §5, line 110. Arch §18 front door, lines 704–705 |
| NFR-17, now Want | Req §5, line 111. Arch §13, line 552 |
| NFR-18, now Want | Req §5, line 112. Arch §10, lines 333–360 |

### Requirements added

| Row | Where |
|---|---|
| FR-20 | Req §4, line 74. Arch §11, lines 461, 465–475 |
| FR-21 | Req §4 "The viewer", line 82. Arch §19, lines 744–748 |
| FR-22 | Req line 83. Arch §19 "The animation", lines 775–798 |
| FR-23 | Req line 84. Arch §19, lines 767–769 |
| FR-24 | Req line 85. Arch §19, line 771 |
| FR-25 | Req line 86. Arch §19 "Fallbacks", lines 800–813 |
| FR-26 (Need) | Req line 87. Arch §19 "Map sources and credit", lines 815–825 |
| NFR-19 | Req line 113. Arch §12 line 502; §18 lines 641–656 |
| NFR-20 | Req line 114. Arch §12 line 513; §18 "Configuration", lines 669–687 |
| NFR-21 | Req line 115. Arch §12, line 517 |
| NFR-22 | Req line 116. Arch §18 "Start order" lines 658–667, "Stopping" line 691 |
| NFR-23 | Req line 117. Arch §18, line 707 |
| NFR-24 | Req line 118. Arch §18 "Logs", lines 693–697 |
| NFR-25 | Req line 119. Arch §18 "Images", line 722 |
| NFR-26 | Req line 120. Arch §13, lines 544, 550 |
| NFR-27 | Req line 121. Arch §13, lines 552–556 |
| NFR-28 | Req line 122. Arch §13 lines 545–548; §19 line 773 |
| NFR-29 | Req line 123. Arch §19, lines 794, 807 |
| NFR-30 | Req line 124. Arch §18 "Commands", lines 724–740 |
| NFR-31 | Req line 125 |

### Decisions changed and added

| Row | Where |
|---|---|
| D-2 | Req §6, line 134. Arch §19, line 744 |
| D-15 | Req line 147. Arch §10, lines 322–345 |
| D-16 | Req line 148. Arch §10 lines 347–360; §15 line 599; §16 line 618 |
| D-17 | Req line 149. Arch §18 front door, lines 704–706 |
| D-18 | Req line 150. Arch §15 line 605; §19 lines 755, 815–821 |
| D-19 | Req line 151. Arch §15 line 606; §19 line 746 |
| D-20 | Req line 152. Arch §11 lines 477–488; §16 line 623 |
| D-21 | Req line 153. Arch §12 line 513; §18 lines 675, 677 |
| D-22 | Req line 154. Arch §15 line 600; §16 line 616 |
| D-23 | Req line 155. Arch §12 line 517; §15 line 602; §16 line 621; §18 line 710 |
| D-24 | Req line 156. Arch §11 lines 447, 451; §18 line 708 |

### Other edits and the trial

| Row | Where |
|---|---|
| Req §7, the frontend line replaced | Req line 168 |
| Req §9, checks 11 to 20 | Req lines 190–199 |
| Arch §2, the proxy in the request flow | Arch lines 20, 40, 45 |
| Arch §3, the cache class and the schema declarations in their layers | Arch lines 51 (`schema.py`, API layer), 54 (`config/cache.py`, Integration layer) |
| Arch §10 rewritten for D-15 and D-16 | Arch lines 320–360 |
| Arch §11, health, schema and docs addresses and `api_unavailable` | Arch lines 447, 451, 457–488 |
| Arch §12 brought in line | Arch lines 501–509, 513–517 |
| Arch §13 brought in line | Arch lines 521, 533–556 |
| Arch §15 brought in line | Arch lines 599–606 |
| Arch §16 brought in line | Arch lines 616, 618, 621–624 |
| Arch "Running it" | Arch §18, lines 635–740 |
| Arch "The viewer" | Arch §19, lines 742–825 |
| Arch §4 and §14 left for Phase 13 | Untouched |
| PRD scope | `docs/prd.md` lines 34, 36 |
| PRD non-goals | `docs/prd.md` line 28 |
| PRD release criteria | `docs/prd.md` line 58 |
| Result of the `drf-spectacular` trial | Req D-20 "What we measured", line 152. Arch §11 lines 477–482; §16 line 623 |

## Gaps: what a builder would have to guess

Each is marked open in the architecture document at the line given.

| # | Gap | Arch line |
|---|---|---|
| 1 | Redis's memory cap, and what it does when full (evict or refuse writes). With refused writes the fallback might take a full Redis for a dead one. | 339 |
| 2 | Where the cache key's version number is kept, and which code changes raise it (D-15). | 345 |
| 3 | How soon a process that has fallen back tries Redis again (NFR-18 "returns to Redis when it is back"). | 358 |
| 4 | "One warning": NFR-18 says one per process; check 13 says one warning is logged. With two workers both may fall back. | 360 |
| 5 | Whether the health answer's `redis` / `fallback` comes from a fresh probe of Redis or from the answering process's current state. Matters for check 13. | 473 |
| 6 | Whether `/api/v1/schema/` and `/api/v1/docs/` are rate limited. FR-20 exempts only health; the throttle is global today. | 462–463, 475 |
| 7 | Where the committed OpenAPI document lives, and whether it is YAML or JSON. | 486 |
| 8 | Whether the OpenAPI document lists `api_unavailable`, which only nginx sends (FR-19 and check 15 say "every error code"). | 488 |
| 9 | The coverage floor's value (NFR-27). | 554 |
| 10 | Whether the viewer's npm dependencies are audited, and by what. NFR-17 lists one audit, not among the viewer's checks. | 556 |
| 11 | Conflict: NFR-19 says only nginx has a published port; PLAN gives `db` 5432 on this machine, and `make dev` needs it. | 654 |
| 12 | Release 1.0's `API_PORT` and `POSTGRES_PORT`: kept or not, and whether `API_PORT` now moves `web`'s port. | 656 |
| 13 | Start gates not stated: whether `api` waits for `redis` to be healthy, whether `web` waits for `api`, and what each health check probes. | 667 |
| 14 | The format of `ROUTING_SERVERS` (a list in one variable). | 685 |
| 15 | The default of `LOG_LEVEL` (release 1.0 logs at INFO). | 683, 687 |
| 16 | Where the request ID is made (nginx or API), and whether it is returned in a header. | 697 |
| 17 | nginx's other upstream errors: status and code for a slow API (timeout) or similar, and nginx's timeouts against the API's ~20-second worst case. D-24 covers only "API down". | 712 |
| 18 | Which security headers nginx sets, and whether there is a content security policy (it would have to allow OpenFreeMap, NASA GIBS and the Swagger CDN). | 714 |
| 19 | Which `Host` the API sees behind nginx: the client's, or nginx's upstream name (which would then have to be in `DJANGO_ALLOWED_HOSTS`). Also affects e2e containers that address `web` by name. | 716 |
| 20 | What a disallowed host gets. Django's answer is a 400 HTML page, not the FR-11 error shape. | 718 |
| 21 | Conflict: `make dev` runs the API from source against Redis in Docker, but `redis` has no published port. | 740 |
| 22 | Which three example trips the bare viewer offers (FR-21). | 748 |
| 23 | Whether touch and keyboard input also cancel the intro (FR-22 names mouse and wheel). | 790 |
| 24 | Whether the distance counter shows ground miles at the head (so it matches each stop's mile marker as it pops) or fraction drawn × distance. Follows from the stop-timing rule. | 798 |
| 25 | What counts as "map servers cannot be reached", and how long the viewer waits before switching to the built-in outlines. | 811 |
| 26 | The pixel-density cap's value (NFR-29). | 813 |
| 27 | The exact credit wording and links each provider asks for. The sources give only the names. | 825 |

## Rulings added to PHASE-9.md while I worked

A section "Rulings on the audits (9.8)" appeared in `docs/plan/PHASE-9.md` after I had read it. It is outside "The spec changes", so I did not write it into the specs. The binding list itself is unchanged. Some rulings bear on the gaps above:

| Ruling | Effect on this report |
|---|---|
| Q0a-03: JSON `handler400` and `handler403`, foreign `Host` gets 400 in the error shape | Settles gap 20. Arch line 718 can drop its open mark. |
| Q0a-06: `API_PORT` added to `.env.example`; Compose passes each variable through | Settles part of gap 12 (`API_PORT` stays). Which port it moves is still open. |
| Q0a-02: database and API ports bound to `127.0.0.1` | Agrees with "5432, on this machine only". Gap 11, NFR-19's "only nginx has a published port", is still open. |
| Q0a-25: eight request slots; health check timeout and retries set above the routing worst case | Settles part of gap 13 (the API health check's timing). The start gates for `redis` and `web` are still open. |
| Q0a-08: "a road with no fuel plan is asked for again" is false; it is cached | That sentence is in Arch §10 (line 331). I left it as it was, since the ruling puts the fix in Phase 13. |
| Q0a-05: the routing-rate sentence in Arch §9 is false | Not in a section I changed; left for Phase 13. |

## Readings I made (please confirm)

These are not new decisions, but each is a choice of how to read the sources.

- **NFR-9:** "Now reads" taken to replace only the one-command sentence. I kept the label "Easy to run." and the sentence "The README covers setup, an example request and the assumptions.", which Part 2 does not withdraw.
- **Labels:** NFR-17 and NFR-18 keep their bold labels (`**CI**`, `**Shared cache.**`), as every other NFR row has one.
- **D-2 and D-15 merged, not replaced:** D-2 keeps its still-true first sentence after "Unchanged for the API:"; D-15 keeps how each cache is keyed ("by its two end points", "plus the stop cost") ahead of the new text.
- **From column:** every new row is "Ours", by the definition in Req §3; none is in the assignment.
- **What we measured:** filled for D-18 (from PLAN's viewer section: checked 18 Nov 2026, about 455 KB) and D-20 (the trial). The others are "—".
- **Section 4 header:** the first table keeps "The API…". FR-18 sits there and reads oddly under it, but its own text says the viewer is separate. FR-21 to FR-26 have their own table, headed "Requirement", under "### The viewer".
- **`WEB_CONCURRENCY` default 2:** from NFR-19, "two worker processes (set by `WEB_CONCURRENCY`)".
- **Health answer:** `stations` comes from the in-memory index, so the ORM rule of Arch §3 still holds; the meanings of `redis`, `fallback`, `memory` follow D-15, D-16 and check 13.
- **`config/cache.py` in the Integration layer**, beside `routing.py`, since it talks to Redis over the network.
- **Stopping:** "Compose must wait at least as long [30 s] before it kills the container; its own default is 10 seconds" is a consequence of NFR-22, not a new rule.
- **Unchanged defaults:** `DJANGO_DEBUG` off and the `DATABASE_URL` default are release 1.0's values from `config/settings.py`.

## Existing sentences changed that the sources did not name

| Where | Change | Why |
|---|---|---|
| Req line 6, status | One sentence added after the existing three | "Each one was tested against the supplied CSV or a real route" would be false for D-16 to D-24 and for the new requirements. |
| Req line 47, tiers | One paragraph added | Two sentences of §3 are false for the second release: wants "are cheap" (the viewer is not) and "every need first" (FR-26 is built in Phase 12, after wants in Phases 10 and 11). |
| Req D-2 | Dropped "The API serves no page of its own unless FR-18 is built." | False now: FR-18 is built as a separate application, and the API serves the Swagger page. |
| Arch line 31, step 5 | "(the ONE network call)" became "(the ONE outside call)" | With Redis the cache is a network call too. |
| Arch line 53, `routing.py` | "The only module that makes a network call" became "The only module that calls a service outside the stack" | Same reason. |
| Arch line 616, known limits | "A lock was rejected (D-22)." appended | D-22 says the limit is kept on purpose. |

Within the sections the sources name (§10, §12, §13, §16, PRD scope, non-goals, release criteria, known limits) I replaced only what had become false: §10's "in-memory backend" and its last paragraph; §12's "Any host name is accepted…" (reversed by D-21) and "the two routing server templates" in the in-code list (now overridden by `ROUTING_SERVERS`); §13's fixture sentence (it now also lets the Redis tests reach a local Redis); §16's "The cache is per process unless a shared cache is added"; PRD "ten acceptance checks", the "Later" line, and the "Cache is per process" limit.

## Left as they are, though now incomplete (not false)

- Req line 3 and Arch line 3 describe "the API"; both documents now also cover the viewer and the stack.
- Req §7 now names accounts twice (the first bullet, and the new line copied word for word from PHASE-9).
- Arch §4 still lists `docker/entrypoint.sh`, and §14 holds release 1.0's figures; both are Phase 13's, as the brief says.
- Arch §17 (build order) is release 1.0's record.
- PRD §1 ("a small Django service") and §4 (goals, no viewer) are outside the PRD sections the brief names.
- PLAN's cut lines (one worker if Redis misses Thursday noon; a flat map if the globe misses Thursday 8 pm) are not in the specs. If either is used, NFR-18, NFR-19, D-15 to D-17, FR-22 and D-18 need changing.
- NFR-24's "one line per planned trip" is left word for word. That the line carries "cache hit" suggests answers from the cache are logged too.

## Second pass: the gaps settled

The controller settled all 27 gaps, plus one point on unknown addresses, in `docs/plan/PHASE-9.md` under "Gaps found while writing the specs, settled". They are now written into the specs, and every open mark has been removed. A whole-word search for `Open` in the three documents finds nothing; the only matches for the letters are OpenAPI, OpenFreeMap, "Opened" and "Opens". Line numbers below are those after this pass; the line numbers in the tables above are from the first pass.

| # | Decision | Where it now lives |
|---|---|---|
| 1 | Redis capped at 256 MB, least recently used key evicted, no persistence | Arch §10 line 337; §18 services, line 643 |
| 2 | `CACHE_KEY_VERSION` in `config/settings.py`, the cache's `VERSION`, raised by hand | Arch §10 line 343; §12 "Settings in code", line 514 |
| 3 | 30 seconds without touching Redis after a fallback, then a retry | Arch §10 line 349 |
| 4 | One warning per process when it falls back, one line on return; check 13 reworded | Req check 13, line 192. Arch §10 line 350; §18 "Logs", line 696 |
| 5 | Health `cache`: `memory` without `REDIS_URL`, else the process's own state; one cheap cache read | Arch §11 lines 472–478 |
| 6 | Schema and docs rate limited; only health exempt | Arch §11 lines 465–468 |
| 7 | Committed document `docs/openapi.yaml` | Arch §11 line 487 |
| 8 | `api_unavailable` listed on the route as a 503 sent by the proxy | Arch §11 line 484 |
| 9 | Coverage floor: Phase 10's figure rounded down, in `pyproject.toml` | Arch §13 line 554 |
| 10 | `npm audit --omit=dev --audit-level=high` in CI | Req NFR-17, line 111. Arch §13 lines 551, 555 |
| 11 | Of the API and nginx only nginx is published; database and Redis on `127.0.0.1` only | Req NFR-19, line 113. Arch §18 lines 642–643, 649 |
| 12 | `API_PORT` (now nginx's port), `POSTGRES_PORT`, and the new `REDIS_PORT` | Arch §18 line 651 |
| 13 | Start conditions and health checks | Arch §18 "Start order", lines 657–672 |
| 14 | `ROUTING_SERVERS`: comma-separated templates with `{coords}`, tried in order | Arch §18 configuration, line 686 |
| 15 | `LOG_LEVEL` defaults to `INFO` | Arch §18 configuration, line 688 |
| 16 | Request ID made by nginx as `X-Request-ID`, made by the API if absent, logged and returned | Arch §2 line 20; §18 lines 698, 706 |
| 17 | nginx waits 30 s; down or too slow gives 503 `api_unavailable`; refused requests give 400 `invalid_request`; API errors pass through untouched | Arch §11 lines 444, 448–454; §18 lines 711–714 |
| 18 | Security headers, and the content security policy on the viewer's page only; browser tests fail on a violation | Arch §18 line 715; §13 line 546 |
| 19 | The client's own `Host` is passed on | Arch §18 line 705 |
| 20 | A host that is not allowed gets 400 `invalid_request` | Arch §11 lines 432, 450; §18 lines 682, 705 |
| 21 | Redis on `127.0.0.1:${REDIS_PORT:-6379}`; from source the cache is memory unless `REDIS_URL` is set; Redis tests use database 15 only | Arch §10 line 335; §13 lines 532, 536; §18 lines 643, 738 |
| 22 | The three example trips | Arch §19 line 744 |
| 23 | Press on the map, wheel, touch or Escape cancels the intro | Req FR-22, line 83. Arch §19 line 784 |
| 24 | Distance counter shows road miles at the head | Arch §19 line 792 |
| 25 | Outlines always the bottom layer; the remote style gets 4 seconds; failed tiles do not draw | Arch §19 line 803 |
| 26 | Pixel density capped at 2 | Req NFR-29, line 123. Arch §19 line 801 |
| 27 | Credit control stays expanded; exact wording and links copied in Phase 12 with the pages' addresses | Arch §19 line 815 |
| — | nginx serves `/` and `/assets/`; everything else goes to the API, so unknown addresses get the JSON 404 | Arch §12 line 502; §18 lines 646, 704 |

The two audit corrections asked for in this pass:

- Arch §10 line 331: the road is cached before the fuel plan is tried, so only a road refused for leaving the USA, and a failed routing call, are asked for again. §9 is left alone, as instructed.
- Arch §11 lines 432 and 450: a host that is not allowed gets 400 `invalid_request` in the error shape.

Req line 6 now also points to the settled-gaps section of PHASE-9.

### Points to check

- **nginx's published interface.** Decision 11 names the database and Redis as published on `127.0.0.1` only. Ruling Q0a-02 binds release 1.0's API port, 8000, to `127.0.0.1`, and decision 12 moves that port to nginx. Whether nginx's 8000 stays on `127.0.0.1` is not stated anywhere. I wrote only "8000" (Arch line 646).
- **The route's response gains a header.** PHASE-9 says the response of `GET /api/v1/route/` "does not change in any way". Decision 16 adds the `X-Request-ID` response header, and decision 18 and compression add headers too. I read "response" as the body and the status code.
- **`details` for the two new `invalid_request` cases.** The error table gives `invalid_request` the detail `fields`. For a request nginx refuses and for a host that is not allowed, no decision says what `details` holds. I wrote nothing about it. Empty `details`, as for `api_unavailable`, would be the obvious choice.
- **Warnings during a long outage.** Decision 4 says a warning is logged "each time it falls back", and decision 3 retries every 30 seconds. I wrote that a failed retry logs nothing new (Arch line 350). Otherwise a two-minute outage would log four warnings per worker, and check 13's "each worker logs one warning" would fail.
- **The database health check.** Decision 13 says `pg_isready` "on its network address"; ruling Q0a-11 says `pg_isready -h 127.0.0.1`. Both require a network connection rather than the local socket, and I wrote it that way (Arch line 663) without naming the host.
- **Where the 400 and 403 handlers come from.** Arch line 450 says Django's error page is replaced for 400 and 403. That detail comes from ruling Q0a-03, which decision 20 cites.

## Third pass: the test design's points

These come from `docs/plan/PHASE-9.md`, "Points raised by the test design, settled". Only the rows that are specification are written in, in `docs/requirements.md` and `docs/backend-architecture.md`. Rows 1, 10, 22 and 26 are test data or test cases, and are not in the specs. Architecture sections 4, 8, 9 and 14 are untouched. Line numbers are after this pass.

| Row | Where it now lives |
|---|---|
| 2 (R15 accepts a host its caller names; `--routing-host`, `fake-osrm`) | Arch §13 verifier row, line 536 |
| 3 (R17 against the places data its caller gives) | Arch §13 verifier row, line 536 |
| 4 (head at constant speed; progress linear from 8 s to 15 s) | Arch §19 "Revealing the route", line 842 |
| 5 (stop 1 at 8 s: marker, card, cost) | Arch §19 "The animation", line 834 |
| 6 (two running totals per point; Web Mercator; linear interpolation) | Arch §19 "Revealing the route", lines 844–849. "The map's projection" in the stop-timing paragraph is now "Web Mercator" |
| 7 (after cancelling, shown finished; camera stays) | Arch §19, line 836 |
| 8 (only `start` or only `finish`: ask the API, show `invalid_request`) | Arch §19, line 785 |
| 9 (number formats; error heading plus the API's `message`; fixed sentences written in Phase 12) | Arch §19 panel, lines 806–811; errors, lines 813–817 |
| 11 (reduced motion: the bare page's globe does not turn) | Arch §19 fallbacks, line 859 |
| 12 (a late remote style is ignored) | Arch §19, line 864 |
| 13 (credits name the sources in use; without WebGL2, Natural Earth) | Arch §19 map sources, lines 874, 876 |
| 14 (Redis timeouts 0.1 s and 0.25 s, no retries; the 0.5 s test limit) | Arch §10, line 349 |
| 15 (the per-trip line and its format; an error logs one WARNING line) | Arch §18 "Logs", lines 706–712 |
| 16 (nginx replaces a client's `X-Request-ID`) | Arch §18, lines 716, 724 |
| 17 (missing file under `/assets/`: 404 `not_found` written by nginx) | Arch §11 line 456; §18 line 722 |
| 18 (what the route lists in the OpenAPI document; `not_found` and `method_not_allowed` in its opening text) | Arch §11, line 489. FR-19 is unchanged: "covers … every error code" still holds |
| 19 (one `Referrer-Policy` value; Django for the API's answers, nginx for the viewer's; nothing sent twice) | Arch §18 security headers, lines 733–738 |
| 20 (the two map servers' host names; the policy's text written in Phase 12) | Arch §18 line 740; §19 map sources table |
| 21 (`ROUTING_SERVERS` trimmed, empty entries dropped, `ImproperlyConfigured` at start-up) | Arch §18 "Configuration", line 696 |
| 23 (the stand-in runs from the test image; the running image holds neither tests nor recordings) | Arch §18 "Images", line 747; §13 line 554 |
| 24 (pre-commit runs Ruff's checks, formatter and hygiene hooks) | Req NFR-27, line 121. Arch §13, line 561 |
| 25 (brief 10B's Makefile is binding) | Arch §18 "Commands", lines 755–777, with `web-dev` marked as coming with the viewer |
| 27 (only `handler400`) | Arch §11, line 453 |
| §13 sentence on connections (127.0.0.1 only) | Arch §13, line 525 |

### Other sentences changed in this pass

| Where | Change | Why |
|---|---|---|
| Arch §13, line 554 | "the 17 saved real roads" became "the saved real roads" | Row 1 adds three recordings and Los Angeles to Seattle, so 17 becomes false |
| Arch §13, CI paragraph | "pre-commit runs the same checks before a commit" moved to its own bullet and narrowed (line 561) | It contradicted row 24 and the new NFR-27 |
| Arch §18, below the Commands table | "Running from source, as `make dev` does…" now says `make dev` starts only the database container | Brief 10B's `dev` does not start Redis |
| Arch §11, line 409 | New paragraph: the body and status are as in release 1.0; only headers are added | One of the five points in "Settled after 9S's second pass". It was not in the documents |
| Arch §11, lines 453, 455 | The two new `invalid_request` answers have empty `details` | Same: listed as settled, but not in the documents |
