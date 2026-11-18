# Review 10R: Phase 10's changes

Reviewer 10R, 18 Nov 2026. Scope: brief `docs/plan/briefs/phase10-R-review.md`, the changes since `004cbcc`. While I worked, the controller committed them (`3f0f56f`, `ab5b976`, `838d1cb`, `978e63f`) and CI ran on them. At the end the working tree was clean and equal to `978e63f`. My experiments ran on a copy of the files taken at the start. I compared that copy's `tests/verify.py`, `trips/services/routing.py`, `answer.py`, `planner.py` and `stations/places.py` byte for byte with the repository, and they matched.

**Method.** I read the rulings, review 9-Q0b, the three briefs, the code and tests, and test-cases sections 4 and 9. I read the builders' reports only after that. I ran the suite (`449 passed, 1 deselected`), the slow test (`1 passed`), mypy, Ruff and `make` itself. Every test run used my own database, `milemarker_r`. I tested each suspicion in two ways:
- **Edits in the copy outside the repository.** Each fix reverted, wrong answers built, the planner's search radius changed.
- **Scratch scripts.** These covered R17 against all 6,626 stations, the R12 bracket at every point of every recorded line, a load test of the stand-in, and a stale-lockfile check.

I made no request to a routing server or to the running API, and touched no container. The only file I wrote in the repository is this report. I used read-only `git ls-remote`, `gh run list` and `gh run view` calls to check action tags and to read the CI run.

Severity counts: **0 Critical, 1 Important, 5 Minor, 11 Notes.**

## Findings

| ID | Severity | Where | What is wrong | How I showed it | Smallest fix |
|---|---|---|---|---|---|
| R10-01 | Important | `tests/verify.py:59` (`NEAR_PLACE_MILES`), `:643` (R17) | **R17 cannot see the corridor-search regression it was added for.** It accepts a stop within 15 miles of *any* row of its city. That is three times the 5-mile search radius. Q0b-1 named "a radius in the wrong units" as the fault to catch, and it still passes every verifier check. The 15 miles assumed up to 10 miles of county averaging, but the measured worst is 4.91 miles. And "any row" lets 50 stations (Orlando, Philadelphia, Jacksonville…) be drawn up to 48 miles from where the app puts them. | (1) In the copy, the planner's radius was set to 5 × 1.609 (8.05 miles), then 10, 12 and 15. QB-02's 54 real answers and VF-01's 7 all passed `verify_response` each time. Only at 20 miles did R17 fire (20 of 61). Only the regression pins noticed 8.05 miles (5 of 8 failed). So the live checks, which have no pins, cannot. (2) On the New York answer, four stops were swapped for a station 9.5 to 12.1 miles from the stop's point, outside the 5-mile radius: North Jackson OH, Tonica IL, Aurora NE and Hudson CO. Each swap passed **all 17 rules**. (3) Over all 6,626 stations, the app's place is at most 4.91 miles from the nearest row of its city (Birmingham AL), but up to 48.1 miles from the farthest row (Orlando FL). | Use the place the app uses, as architecture section 6 documents it: a station stop must lie within 5.01 miles (5 plus rounding) of the mean of its city's rows, or of one row. Every one of the 6,626 stations' places is exactly one of those points (largest distance 0.0). In the copy, this rule passed all 198 tests in `test_api`, `test_answer`, `test_verify` and `test_regression`, including QB-02 and VR-03/04. It caught the 8.05-mile radius on 14 of 61 answers, a 6-mile radius on 6, and a 7-mile radius on 12. R17's text and its ruling change with it. |
| R10-02 | Minor | `tests/verify.py:498` (R12) with `:543` (R13) | **R12 takes the line's scale from the answer's own line, which R13 lets be padded.** The bracket uses `len(line)`. R13 allows the count to be 1% off. Repeated points at the end widen the bracket, so stops can be drawn miles past their markers. That brings back Q0b-2's fault: a stretch over 500 miles shown as 499.8. | New York answer: 30 copies of the last point added to the line. Each station stop moved to the farthest line point R12 still accepts for its marker. **All 17 rules passed.** Stops were drawn up to 13.5 miles past their markers, and the true stretch from stop 3 to stop 4 was 502.3 miles, shown as 499.8. With 20 copies it also passed (501.8). With 40 or more, R17 fired. | In R13, reject a repeated consecutive point. Tighten the count to 0.25% or 2 points, whichever is larger: that holds on all 21 recorded lines, whose worst is −11.2 points (0.18%). With R10-01's 5-mile R17, a padded line can then move a stop by at most about 5 miles. Say in R12's text that the line itself is trusted. |
| R10-03 | Minor | `config/settings.py:107-124` | **`ROUTING_SERVERS` accepts any number of entries, and the client tries each.** With three entries a route can take three calls. NFR-2 says "never more than two", and R15 and the response contract allow `routing_calls` 0, 1 or 2. | Scratch test: three templates, the first two answering 503. `fetch_route` returned `calls 3`, having asked s1, s2 and s3. | Refuse more than two entries with `ImproperlyConfigured`, as an empty entry is refused, and add a CF case. |
| R10-04 | Minor | `.github/workflows/ci.yml:41` | **`uv sync --frozen` lets a stale `uv.lock` through.** `--frozen` installs from the lockfile without checking it against `pyproject.toml`. A dependency or bound changed in `pyproject.toml` without `uv lock` is silently ignored, and every check then runs on the old set. | In the copy, `six>=1.16` was added to `dependencies`. `uv sync --frozen --dry-run` planned the install and exited 0. `uv sync --locked --dry-run` refused: "The lockfile at `uv.lock` needs to be updated". | `uv sync --locked`. |
| R10-05 | Minor | `.github/dependabot.yml:12` | **No ecosystem watches the Compose files' images.** Dependabot's `docker` ecosystem reads Dockerfiles. Compose files have their own ecosystem, `docker-compose`, generally available since 25 Feb 2025. So `postgres:17` in `docker-compose.yml`, and any image the Compose files gain, is never proposed. Ruling Q0a-21 relies on Dependabot keeping them current, and RP-03 expects updates for "the images". The CI service image `postgres:17` is in no ecosystem at all. | GitHub changelog, 25 Feb 2025, "Dependabot version updates now support Docker Compose in general availability", and the supported-ecosystems page (value `docker-compose`). | Add `package-ecosystem: docker-compose`, `directory: /`, grouped like the others. Keep the CI service image in step with the Compose file by hand, and say so in a comment. |
| R10-06 | Minor | `tests/test_fake_osrm.py:129-152` (SI-07) | **The settled rule "`path` without its query string" is untested.** SI-07 sends its requests with no query and checks `path` with `startswith`. A stand-in that logged the query passes all 19 tests. Builder A's own log, from an earlier build, shows `...;-118.247896,33.973093?overview=full&geometries=geojson`. The current code strips the query (CI's log has none), but nothing holds it there. "The closest recording when several match" is also untested: no two recordings overlap. | In the copy, `scripts/fake_osrm.py:160` was changed to log `self.path`. `tests/test_fake_osrm.py`: 19 passed. | In SI-07, send `?overview=full&geometries=geojson` and require `path` to equal the bare path. Optionally, add a case with two overlapping copies of a recording in a temporary folder. |
| R10-07 | Note | `trips/services/answer.py:90`; architecture `:261` | **The new count still differs from the plan's in one corner.** The plan always counts stop 1, even at 0.00 gallons, but `lowest_possible_stops` does not. At stop cost 0, with identical purchases, the comment's claim that "the two counts are equal" is false when the start purchase shows 0.00. It cannot happen on real data: the start purchase must reach a road point at least half a mile on, which is at least 0.05 gallons. | `build_answer`, plan = free-stops purchases (0.004, 10.003, 19.993) at (3.50, 3.00, 2.00), 300 miles, stop cost 0. Gallons shown 0.00, 10.01, 19.99; both bills 70.01; `stops` 3, `lowest_possible_stops` 2. | Either count the start always (`1 + sum(g > 0 for g in lowest_gallons[1:])`, with QB-13/AN-11 then expecting 3), or reword the comment and section 8 to "except the fill-up at the start". |
| R10-08 | Note | `docs/backend-architecture.md:162` | **Section 6 still says a final part `Mexico` or `Canada` is outside coverage.** N5 changed that for text ending in USA, but brief 10C could not edit section 6. There is a new asymmetry too: `Tijuana, Mexico, USA` is outside coverage (comma branch), while `Tijuana Mexico USA` and `Toronto Canada US` are now `unknown_place` with no suggestions (before: outside). | `resolve()` on 24 texts, with and without the fix. `Canada, USA` gives `unknown_place ['Canada, KY']`; `New Mexico USA`, `Mexico MO`, `Mexico, MO, USA`, `Mexico Maine USA` and `Canada KY` behave as before. | Add "unless the text ended in USA" to section 6. Decide whether a comma-free country before USA should stay outside coverage. |
| R10-09 | Note | `trips/services/routing.py:142` | **The "no road whatever the status, short of a server error" rule has no test beyond statuses 400 and 200.** Its behaviour matches the comments: 404, 403 and 302 with a `NoRoute` body end with `NoRoute` after one request, and 503 with one goes to server 2. Removing the `status < 500` guard fails none of the 120 tests in `test_routing`, `test_api` and `test_fake_osrm`. This predates 10C (F4). | Probe of 15 status/body pairs; the guard removed in the copy. | RT cases: 404 + `NoRoute` gives `NoRoute` with 1 request; 503 + `NoRoute` gives a route from server 2. |
| R10-10 | Note | `trips/services/routing.py:144` | As ruled, *any* 400 that is not "no road" ends the request, including one that is not OSRM's at all (an HTML 400 from a proxy in front of one server). The review's alternative was to end only on OSRM's `Invalid*` codes. | Probe: `400` with `<html>` body gives `RoutingUnavailable(error)` after 1 request; `404 InvalidUrl` goes to server 2. | None needed; worth one sentence in section 9 if the ruling is revisited. |
| R10-11 | Note | `scripts/fake_osrm.py:134` | The stand-in answers 404 for an unknown path. OSRM answers 400 (`InvalidUrl` or `InvalidService`), and the client now treats the two differently: 404 goes to the next server, 400 stops. With one server in the stack the end result is the same, `routing_unavailable`. Builder C noted it too. | Read; the client branch probed above. | Answer 400 `InvalidUrl`, or say in the docstring that it differs. |
| R10-12 | Note | `tests/verify.py:167` | `routing_hosts="fake-osrm"`, a bare string, becomes a set of letters: `fake-osrm` is then refused, and a host named `f` accepted. It fails closed, and `live_check.py` passes a list. | `verify_response(..., routing_hosts="fake-osrm")` reported R15; with `routing_server` `"f"` it returned `[]`. | Wrap a `str` in a list, or raise `TypeError`. |
| R10-13 | Note | `tests/test_verify.py:547` (VR-04) | VR-04 holds the verifier's copy of the five hand-added places only loosely to the app's values. A typo of 0.1° of longitude in the copy (about 5.5 miles) would pass it: the stop at the app's position is then 5.5 miles from the copy, within 15, and the stop 20 miles north is 20.7 miles away, so R17 still fires. | Worked from R17's 15 miles. | Compare the two tables directly in VR-04. Tests may import both. |
| R10-14 | Note | `.github/workflows/ci.yml` (all jobs) | No job sets `timeout-minutes`, and Newman has no request timeout, so a hung stack runs to GitHub's 6-hour default. The e2e check requires "non-empty, all matched", not EE-03's `count` 8. The run showed 8, but nothing enforces it. | Read; CI log of run 44330671434. | `timeout-minutes: 20` per job and `--timeout-request 60000` for Newman; optionally assert the count. |
| R10-15 | Note | (future) CI-02, CI-03 | When `manage.py check --deploy` joins CI, note that it exits 0 on warnings. Today it reports 4 warnings with exit code 0, so CI-03's "a check removed from `SILENCED_SYSTEM_CHECKS` fails the run" needs `--fail-level WARNING`. | `uv run python manage.py check --deploy`: 4 issues, exit 0. | Use `--fail-level WARNING` when the step is added (Phase 11). |
| R10-16 | Note | `tests/test_fuel.py:178-179`; `docs/test-cases.md:183` (FU-23) | Both still describe the removed 0.005-gallon counting rule. Builder C flagged this and it is still there. FU-23's count happens to be the same under the new rule. | grep. | Reword both. |
| R10-17 | Note | `docs/plan/reports/phase10-B.md:28` | B's report gives the `e2e` target as Newman with `--delay-request 1200`, but the Makefile has no delay. Without the delay is right: EE-03 has none, and 14 requests are far below the 60-a-minute limit. | `make -n e2e`. | Correct the report's row. |

## Scope item 1: the fixes

"Fails without it": I reverted that fix alone in the copy, ran its tests and saw them fail, then restored the file.

| Fix | Sound? | Fails without it? |
|---|---|---|
| Q0b-1, R17 | **No correct answer fails**: every station's place is within 4.91 miles of a row of its city, and QB-02's 54 answers pass. **Too loose, though** (R10-01). | **Yes.** R17 taken out of `RULES`: QB-01, VR-03 and all five VR-04 cases failed (7). |
| Q0b-2, R12 bracket | **Sound for correct answers**: no correct marker falls outside the bracket at any point of 19 recorded lines, and it is tight (table below). I reproduced the builder's reason for not following the ruling's formula: it fails 9 of QB-02's 54 correct answers (bos_sea ×2, nyc_la, sea_mia ×3, dal_phx ×3) plus 2 VF-01 answers. Defeated by a padded line (R10-02). | **Yes.** The old 0.5% + 0.05 tolerance restored: QB-03 failed. |
| Q0b-3, retry rule | **Sound.** Matches the ruling and section 9 across 15 status and body pairs. Every non-200 except 400 goes on (204, 3xx, 401, 403, 404, 408, 410, 413, 414, 451, 5xx, 429). A 400 that is not "no road" stops. A `NoRoute` or `NoSegment` body below 500 stops with `NoRoute`. A 200 with an empty `routes`, a JSON list or bytes that are not UTF-8 goes on. httpx does not follow redirects here, so a 302 is seen as a 302. | **Yes.** F4's rule restored: 9 failed (QB-04 ×3, QB-05 ×6). |
| N8, the lock | **Sound.** Creation only, no re-entry, held briefly. | **Yes.** Lock removed: QB-16 failed. |
| Q0b-4, the count | **Sound on every reachable input** (R10-07 is the unreachable corner). | **Yes.** Old count restored: QB-07 failed. AN-11 passes either way, because its counts happen to agree. |
| Q0b-5, R6 | **Sound.** Stop 1 at 0.00 is still caught, by R2: the tank goes below 0 on the way to stop 2. | **Yes.** QB-08, QB-09 and the stop-cost-0 case failed. |
| R15 option | **Sound** (R10-12 is a usability note). | **Yes.** VR-01 failed. |
| R17 places option | **Sound.** | **Yes** (VR-03, with R17 removed). |
| N1 | **Sound.** | Not reverted: QB-10 reads the docstring. |
| N5 | **Sound as ruled** (R10-08). | **Yes.** QB-12 `Mexico, USA` failed. |
| N7 (a) | **Sound.** | **Yes.** With the review's mutant (purchases under 0.005 gallons dropped from the lowest bill), AN-11 and QB-07 failed. |
| N7 (b) | **Sound**: QB-14 passes the whole answer to `verify_response`. | Not re-run; the builder reports a mutant it caught. |
| N7 (c) | **Sound**: exact tuples. | By construction. |
| Types | **No behaviour change.** `sphere.py` and `exceptions.py` gain annotations only. `fuel.py` gains two annotations and one `assert` stating what the next line already relied on: an impossible state now raises `AssertionError` instead of `AttributeError`. | Slow test 1 passed. mypy: no issues in 6 files. Suite passes. |

**R12: the largest shift of a stop, in line points, that passes with its marker kept.** For every point of each line, I took the marker the app shows there and tried positions up to 7 points either way.

| Line | Start third | Middle third | End third |
|---|---|---|---|
| The other 17 of the 19 recorded roads with a line (last straight gap 0.07 to 0.36 mile) | 0 | 0 | 0 |
| `dal_hou` (238 mi, last gap 0.079), `elpaso_delrio` (425 mi, last gap 0.032) | 0 | 0 | +1 (0.5 mile) |
| Synthetic 1,500 mi, last gap 0.01 | 0 | 0 | +1, from 80% of the way on |
| Synthetic 40 mi, last gap 0.01; 3 mi, last gap 0.02 | 0 | 0 | +1 |
| Synthetic 3.5 mi, last gap 0.49 | 0 | 0 | 0 |

No backward shift passes anywhere. On the New York answer, shifts of −5, −2, −1, +1, +2 and +5 on each of its six station stops all fire R12. On `dal_hou`, `elpaso_delrio`, `sea_mia` and `bos_sea` at stop costs 0, 10 and 25, no station stop passed a shift of −1, +1 or +2.

**Wrong answers built against all 17 rules** (New York answer unless stated; every figure made to agree with the change):

| Wrong answer | Result |
|---|---|
| Stop swapped for a station in a same-named city in another state (Youngstown OH to FL, Utica IL to NY, Henderson NE to KY, Green River UT to WY), point kept | R17 |
| The same, with the stop still claiming the original state | R5 |
| Stop swapped for a station 9.5 to 12.1 miles from its point (outside the 5-mile radius) | **Passes all 17** (R10-01) |
| Planner radius 8.05, 10, 12 or 15 miles; 61 real answers | **All pass** (R10-01) |
| Stop moved 1, 2 or 5 points, marker kept | R12 |
| Line padded with 20 or 30 repeated end points, stops moved to match | **Passes all 17**; a 502.3-mile stretch shown as 499.8 (R10-02) |
| An added stop buying exactly 0.00 (QB-08) | R6 |
| Stop 1 buying 0.00, stop 2 buying its fuel | R2 |
| `routing_server` `fake-osrm`, no option / option `["fake-osrm"]` / public host with the option | R15 / passes / passes |

## Scope item 2: the stand-in routing server (10A)

- **Wrong recording?** No. I resolved each of the collection's eight routed trips with the app's own places. Each lies within 1.4 miles of one recording at both ends, and no other recording has both ends within 60 miles of it. No two recordings have both ends within 60 miles of each other. Direction is honoured: `nyc_la` and `la_nyc` are both recorded, and each request got its own. CI's log on run 44330671434 holds exactly EE-03's eight: `nyc_la`, `la_nyc`, `sea_mia`, `dal_hou`, `stl_winstonsalem`, `dal_phx`, `det_buf`, `la_sea`, all status 200.
- **Answers as OSRM does, in every case the client distinguishes?** Yes for a route (200), "no road" (400 `NoRoute`) and a malformed request (400 `InvalidUrl`). An unknown path differs (R10-11). It ignores the query string, which brief 10A asks for; so an API template missing `geometries=geojson` would still be served GeoJSON. RT-01 pins the real template.
- **The log under concurrency.** 400 requests from 32 threads, mixing matched, unmatched and both paths, with a reader polling `/_requests` 30 times meanwhile: `count` 400, and every snapshot had `count` equal to the length of `requests`. Append, snapshot and reset are all under one lock.
- **A test that passes while the stand-in is wrong:** R10-06.
- **`ROUTING_SERVERS`:** the edge cases of row 21 behave as the CF tests say. More than two entries is R10-03.
- **Compose file:** `api` waits for `fake-osrm` to be healthy. `{coords}` survives Compose interpolation, the port is published on `127.0.0.1` only, and SIGTERM ends the process. Proven in CI: the stack came up and Newman ran 14 requests and 111 assertions with none failing.

## Scope item 3: Makefile and CI (10B)

- **Action versions** (`git ls-remote --tags`): `actions/checkout` `v7`, `docker/setup-buildx-action` `v4` and `docker/build-push-action` `v7` are moving major tags. `astral-sh/setup-uv` has moving tags only up to `v7`. From v8 on there are exact versions only, so `v10.3.3` is the right pin. Its README at that tag has no required input, and `enable-cache` is documented. `ruff-pre-commit` `v0.17.5` exists and matches `uv.lock`; `pre-commit-hooks` `v6.0.0` is the latest.
- **Service container.** The syntax is right, and the health command runs `pg_isready` inside the container. Proven in CI: the suite reached PostgreSQL on `127.0.0.1:5432`.
- **The workflow has now run.** Run 44330671434, on `978e63f`, is green:
  - **`checks`**, on ubuntu-26.04 with CPython 3.12.16: Ruff, the format check and mypy clean; `makemigrations` "No changes detected"; `449 passed`; coverage 98.40% against a floor of 98.0. pytest-cov reads `fail_under` from `pyproject.toml`; I confirmed this in its plugin source. Slow test `1 passed`; `pip-audit` "No known vulnerabilities found".
  - **`image`**: built in 24 s, with a cache hit.
  - **`e2e`**: as above.

  The previous run failed at "Wait for the API" (the health address does not exist yet), so the job does fail when it should.
- **Steps that can pass while broken:** the coverage summary step ends in `|| true` on purpose, and the test step itself enforces the floor. Otherwise see R10-04 and R10-14.
- **Makefile under `cmd.exe`.** I ran it with `SHELL=cmd.exe` from PowerShell:
  - `help` and `lint`: exit 0.
  - `test`: `449 passed`, exit 0.
  - `-n` on every other target printed the commands.

  Under Git Bash, `help`, `lint` and `typecheck` exited 0. There is no `&&`, conditional, prefix assignment or backtick, and no `@echo` line holds `& | < > ^ %`. `make help` lacks `web-dev`, which comes in Phase 12.

## Checked and found sound

- **Suite, slow test and lint.** Suite, slow test, Ruff and mypy are clean in the repository. Coverage is 98.40% in the copy and in CI.
- **R17's city key.** It is character for character the app's (`_city_key` in `stations/places.py`). Every one of the 6,626 stations has a row of its city in R17's default places.
- **R12's bracket.** It contains the correct marker at every point of all 21 recorded lines.
- **The retry rule.** It matches section 9's new text exactly.
- **`Mexico` names.** `Canada, USA`, `New Mexico USA`, `Mexico MO`, `Mexico, MO, USA`, `Mexico US`, `Mexico, United States` and `mexico usa` all give a sensible answer.
- **Endpoint tests.** They now give the verifier their own places, built from the stations they create. QB-14 runs all 17 rules.
- **`live_check.py`.** It passes `--routing-host` values as a list.

## What I could not check

- **Real OSRM error statuses.** I could not see what the real servers send for an unknown path or a blocked client (R10-11), because requests to them were off limits. That part is from OSRM's documented behaviour.
- **Containers.** I did not start any. The end-to-end evidence is CI's run log, not a run of my own.
- **pre-commit.** I did not run it myself; builder B reports a clean run on a copy.
- **Dependabot.** Its behaviour is from GitHub's documentation, not observed.
- **N7 (b).** I did not re-run the builder's mutant.
