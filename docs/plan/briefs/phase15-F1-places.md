# Brief 15F1: suggestions for a place given with no state

The Mile Marker API (Django) resolves a start and a finish typed as "City, ST" against an offline table of US places (`stations/places.py`, built from `data/us_cities.csv`). When a place cannot be resolved, the 400 `unknown_place` error carries up to five suggestions.

The repository root is `F:\Spotter-AI\milemarker-api`. Every path below is relative to it.

## The bug (proved)

`_suggestions` (`stations/places.py`, about lines 185-194) has two cases.

- **With a known state:** it returns `difflib` close matches among that state's places. This is fine.
- **With no state, or a state it does not recognise:** it returns the exact city name in every state that has it, sorted alphabetically by state code and cut at five.
  - `Dallas` is offered `["Dallas, GA", "Dallas, IA", "Dallas, NC", "Dallas, OR", "Dallas, PA"]`, without Dallas, TX.
  - 8 of the 50 largest US cities miss their own state: Houston, Dallas, Austin, Columbus, Nashville, Portland, Memphis and Arlington.
  - A misspelling with no state (`Dalas`, `Houstan`) gets `[]`.

The proof is in `C:\Users\Bakemono\AppData\Local\Temp\claude\a83fc35170f12650\2174297b-dd78-49b7-8d5b-a766fb1b748a\scratchpad\proof\a\repo\tests\test_proof_i1.py`.

## The fix (decided; the reasons are in `docs/plan/PHASE-15.md`, "Rulings")

1. **Data.** The US Census Bureau's Vintage 2023 city and town estimates are already downloaded to `C:\Users\Bakemono\AppData\Local\Temp\claude\a83fc35170f12650\2174297b-dd78-49b7-8d5b-a766fb1b748a\scratchpad\census\sub-est2023.csv`. Source: `https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/cities/totals/sub-est2023.csv`, public domain. Do not download anything else.
   - Write `scripts/extract_large_places.py`. It takes the census file's path as an argument and writes `data/large_places.csv` with the columns `state,city,population`.
   - Rows: incorporated places (`SUMLEV` 162) in the states the API covers (`COVERED_STATES` in `places.py`), with `POPESTIMATE2023` of 50,000 or more.
   - `city` must be spelt as the places table spells that place, so that `(state, _city_key(city))` is a key of the table. Strip the census suffixes (" city", " town", " village", " borough", " municipality" and so on).
   - Map the consolidated governments by hand, in a small dict in the script. Examples: "Nashville-Davidson metropolitan government (balance)" → Nashville; "Louisville/Jefferson County metro government (balance)" → Louisville; "Indianapolis city (balance)" → Indianapolis; "Lexington-Fayette urban county" → Lexington.
   - **Every row must map to an existing table key.** The script fails, naming the rows, if any does not. Report how many rows there are, and every hand mapping.
   - Sort the rows by state, then city. Keep the census file out of the repository.
   - Add a section to `data/README.md` giving the source, the URL, the vintage, the threshold, the licence (public domain, US Government work), and the one command that regenerates the file.
2. **Ranking.** In `places.py`, load `data/large_places.csv` once, from `settings.DATA_DIR`. Do not edit `config/settings.py`, which another agent owns.
   - **No state, or an unrecognised one, and the exact city name exists:** order the states by that place's population, largest first. States not in the list come after, alphabetically by state code. Then cut at five.
   - **No state, and no exact name:** run `difflib.get_close_matches` over the large places' city keys only. Choose the cutoff by measurement; report the value and why. Return up to five labels, the largest places first.
   - **With a known state:** behaviour is unchanged.
3. **Tests**, in `tests/test_places.py`:
   - Each of the 50 most populous places in `data/large_places.csv`, typed with no state, gets its own `City, ST` as the first suggestion.
   - `Dallas` → `Dallas, TX` first. `Dalas` and `Houstan` with no state → `Dallas, TX` and `Houston, TX` among the suggestions.
   - A gibberish name with no state (for example `Qwxzy`) → `[]`.
   - The no-state fuzzy lookup takes under 5 ms. Measure it and report the figure. In the test, assert a generous bound such as 50 ms, so CI does not flake.

   These must still pass unchanged: PL-16 to PL-19, QB-12 (`Mexico, USA` still gives exactly its five states), and `tests/test_api.py` EP-15, EP-17 and EP-32. `tests/test_api.py` belongs to another agent: run it, but do not edit it.

## Rules

- You own only: `stations/places.py`, `data/large_places.csv` (new), `data/README.md`, `scripts/extract_large_places.py` (new), `tests/test_places.py`. Do not edit any other file. The documents are updated by a later agent; in your report, list the doc lines that state the old behaviour if you notice them.
- Never change the line endings of the existing `data/*.csv` files.
- Database for pytest: `DATABASE_URL=postgresql://milemarker:milemarker@127.0.0.1:5432/milemarker_f1`. Run `tests/test_places.py`, `tests/test_loader.py`, and `tests/test_api.py -k "ep15 or ep17 or ep32"`. **Never run `tests/test_cache.py` or the full suite.**
- Then run `uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy`.
- No request to any routing server. No container started or stopped. No git command that changes anything. No subagents.
- Write plainly: full sentences, common words. Match the code style of `places.py`.

## Report: `docs/plan/reports/phase15-F1.md`

Keep it under a page. Cover:
- what changed, file by file
- the row count and the hand mappings
- the 50-city result
- the fuzzy cutoff and timings
- the test results (counts)
- every claim marked **proved** (with the command and the decisive output) or **assumed**

Reply with: status, the files changed, the test counts, and any concern.
