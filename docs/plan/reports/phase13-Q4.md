# Report QA-4: the stranger test

An agent given only the repository's address and its README cloned the branch into an empty folder and followed the README literally. It could not write this file itself; the controller wrote it from its reply.

**Verdict:** a stranger can run it from the README alone. Everything worked first time.

| README says | What happened |
|---|---|
| `docker compose up --build -d`, ready in about a minute | Up in 14 s with the image layers cached; a cold build was not timed |
| The docs page at `/api/v1/docs/` | 200, "Mile Marker API" |
| New York to Los Angeles: 2,800.6 mi, 280.06 gal, $867.27, 7 stops; first stop DELTA, Jersey City NJ, $3.239, 39.21 gal, $127.00 | Identical, figure for figure, from the real routing servers |
| `routing_calls` 1 on a new trip | **2**: the first public server failed and the second answered, in 7.3 s |
| A repeat is a cache hit | `routing_calls` 0, `cache_hit` true, 12 ms |
| Health | `{"status":"ok","stations":6626,"cache":"redis"}` |
| 597 tests, about two minutes | 597 passed in 95.7 s |
| Every link and file named | All exist; the Makefile has the nine commands |

**Findings: 0 Critical, 2 Important, 5 Minor, 3 Notes.**

| ID | Severity | Finding | Ruling |
|---|---|---|---|
| Q4-1 | Important | The README said one routing call; a new trip can make two | Fixed: the README says a second server is tried only if the first fails |
| Q4-2 | Important | Compose names the project after its folder, and the test machine already had stopped containers of that name | Stands: an artefact of testing on the machine the project was built on. A reader who has never run it has no such containers, and one who has wants them reused |
| Q4-3 | Minor | "All fifteen decisions": there are 24 | Fixed |
| Q4-4 | Minor | The sample answer is shortened without saying so, and "both figures" are not named | Fixed |
| Q4-5 | Minor | Timings loose: start-up, the first trip's seconds, two different test times | Fixed |
| Q4-6 | Minor | The docs page loads its script from a CDN | Fixed: said in one clause |
| Q4-7 | Minor | `up -d` returns before the API is ready | Fixed: the README names the health address as the sign it is ready |
| Q4-8 | Note | The health address was not in the README | Fixed with Q4-7 |
| Q4-9 | Note | "597 tests" against "597 passed, 1 deselected" | Stands: the slow test is described in `docs/development.md` |
| Q4-10 | Note | The README clones the default branch; the test used `next` | No action: the same after the merge |

As a stranger after ten minutes: "I know what it does and how to run it, and the numbers are honest." What it missed, the task itself, is now the README's second paragraph.
