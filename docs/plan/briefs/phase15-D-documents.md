# Brief 15D: make every document true of release 2.1.0

The Mile Marker API (Django) plans fuel stops for a road trip. It is a take-home submission for a backend role. An independent review found 11 issues, all proved. Two commits have just fixed three of them in code. Your job is to make every document say exactly what the code now does, and to answer the other eight with one true sentence each. You add no new feature, no new section, and no prose beyond what truth needs.

The repository root is `F:\Spotter-AI\milemarker-api`; every path is relative to it.

## Read first

- `docs/plan/PHASE-15.md`: the findings and the rulings.
- `docs/plan/reports/phase15-F1.md` and `phase15-F2.md`: what was built, the new test IDs, and the stale document lines each builder found.
- The two commits: `git show 075e93a` (I1) and `git show 12e5127` (I2, M5, the cache version).
- `README.md`: the model for tone and length. It is written for a person who wants to run the thing. Keep it short.

## What the code now does (the three fixes)

**I1.** With no state, or an unrecognised state, the suggestions for an exact city name are that name in the states that have it, the most populous first by US Census population (`data/large_places.csv`, 748 places of 50,000 or more), then by state code, up to five. With no exact name, the suggestions are close names among the large places only (cutoff 0.7), largest first. With a known state, nothing changed. New tests: PL-22 (×50) and PL-23 (×4).

**I2.** A trip refused after routing is cached in the road's place for 24 hours, so a repeat makes no routing call and gets the identical answer. Refused here means: the road leaves the USA, there is no road, or the road is under half a mile. A routing failure is still never cached (EP-08). New tests: EP-41, EP-42, EP-43. The old unnamed test that pinned "not cached" was removed.

**M5.** When the stations cannot be read from the database, `/route/` and `/health/` answer 503 `stations_not_loaded` ("The fuel stations could not be read from the database. Try again later."). One warning line is logged, and the next request tries again. The default database connection gives up after 5 seconds (`connect_timeout`; one set in `DATABASE_URL` wins). New tests: EP-44, HS-22, LD-19; CF-06 extended.

**Cache version:** `CACHE_KEY_VERSION` is now 2.

## Tasks

1. **The three fixes in the documents.**
   - **I1:** `docs/backend-architecture.md:165` (and anything else describing the order of suggestions); the use cases for an unknown place.
   - **I2:** `README.md:3` is now true, so keep it. `docs/backend-architecture.md:130`, `:327` (the road row of the cache table), `:333`; `docs/use-cases.md:225` (A5) and `:607` (A2), if either says otherwise; D-15 in `docs/requirements.md` if it describes what the road cache holds.
   - **M5:**
     - `docs/backend-architecture.md:458`, `:481` and `:687`.
     - D-13 in `docs/requirements.md`: no request reads the database once the stations are loaded.
     - FR-20, so that it covers a database that cannot be read.
     - The 503 descriptions in `trips/schema.py` (about lines 452, 458, 739 and 860). Change description text only. Then regenerate `docs/openapi.yaml` with `uv run python manage.py spectacular --file docs/openapi.yaml`; never edit the YAML by hand.
     - The `StationsNotLoaded` docstring in `stations/exceptions.py` (docstring only).
   - **Cache version:** anything stating the number.
2. **The other eight, one true sentence each**, at the places named:
   - **M1:** `README.md:79` (the "Beyond the brief" row), NFR-16 and `docs/backend-architecture.md:313`. The rate limit keeps one client from leaning on the free routing servers through us. It does not hold routing calls to one a second: one client can send 60 requests in a second, and up to 8 routing calls run at once.
   - **M2:** the architecture's HEAD sentence (about line 467) and `docs/openapi.yaml`'s source text only if needed. HEAD is answered as GET without the body (RFC 9110, section 9.1), so a HEAD for a new trip makes its routing call, and the result is cached.
   - **M3:** README "Known limits". The detour from the road to a station, at most 5 miles each way, counts in neither the range nor the bill (D-8).
   - **M4:** `docs/backend-architecture.md:253`. The fallback to the full station list was measured at 180 to 350 ms on coast-to-coast roads; none of the recorded roads triggers it. This replaces "about half a second".
   - **M6:** `docs/development.md`, "Things to know". Redis is published on 127.0.0.1 with no password, for the tests and for running from source. Do not publish that port beyond the machine: the cache unpickles what it reads.
   - **M7:** README "What it assumes". Stop 1 is drawn at the start and priced at the station nearest it.
   - **M8:** the architecture, where the docs page's CDN is mentioned (outside the parked sections). The three files carry no integrity hash.
   - **M9:** `README.md:92`. A road is refused only if it runs through Canada or Mexico for more than 25 miles in a row.
3. **Test cases** (`docs/test-cases.md`). Add rows for PL-22, PL-23, EP-41 to EP-44, HS-22 and LD-19 in their sections, with inputs, expected results, and a result of Pass naming the test. Update CF-06 and the row at about line 438 ("Errors are not cached"). Update the recorded actual suggestion lists that changed: N05 (Springfield) is now MO, MA, IL, OR, OH. Check N03 and N04 against the code. Update the counts and the summary at the head and in section 9. The controller will give you the suite's total; until then write `TOTAL` and say so in your report.
4. **`scripts/live_check.py`.** Only if one of its expectations about suggestions is now false. Show the line.

## Rules

- **Your files:**
  - `README.md`, `docs/requirements.md`, `docs/backend-architecture.md`, `docs/use-cases.md`, `docs/test-cases.md`, `docs/development.md`.
  - `docs/openapi.yaml`, regenerated only.
  - Description text in `trips/schema.py`.
  - The docstring in `stations/exceptions.py`.
  - `scripts/live_check.py`, expectations only.
  - Your report, `docs/plan/reports/phase15-D.md`.
- **Not your files:** everything else, including `docs/plan/` apart from your report, and every other line of code.
- **Parked sections stay as they are.** Leave the sections marked "Not part of this submission" alone.
- **Shorter, not longer.** Where a sentence is untrue, correct it or cut it. Write plainly: full sentences, common words, no figures of speech. Follow the style of the documents as they are.
- **Database for pytest:** `DATABASE_URL=postgresql://milemarker:milemarker@127.0.0.1:5432/milemarker_d`.
- **Checks to run:**
  - `uv run pytest tests/test_schema.py tests/test_project.py -q`
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run python manage.py spectacular --validate --fail-on-warn --file <a scratch file>`
- **Never run `tests/test_cache.py` or the full suite.**
- **Forbidden:** any request to a routing server; starting or stopping a container; any git command that changes anything; subagents.

## Prove it

Search the whole repository outside `docs/plan/` for each old claim. Every hit must be gone, or stay with a reason:

- "not cached"
- "Errors are not cached"
- "about half a second"
- "half a second"
- "is refused." on the border
- "one request a second"
- "an empty table"
- "states that have it"
- "CACHE_KEY_VERSION = 1"

## Report: `docs/plan/reports/phase15-D.md`

Keep it under a page and a half. Cover:

- For each finding: what you changed, file by file, in a line or two.
- The search results.
- Every place where you were unsure what the code does, and how you settled it (quote the code line).

Mark each claim **proved** or **assumed**.

Reply with: status, the files changed, the search counts, and any concern.
