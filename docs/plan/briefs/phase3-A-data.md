# Brief 3A: the data side

Read `docs/plan/briefs/phase3-common.md` first. It applies in full.

## Goal

Turn the supplied CSV into station rows in PostgreSQL, hold them in memory, and resolve place names offline.

## Your files

- `stations/models.py`, `stations/migrations/0001_initial.py`
- `stations/places.py`
- `stations/index.py`
- `stations/management/commands/load_stations.py`
- `tests/test_places.py`, `tests/test_loader.py`, `tests/test_index.py`
- Report: `docs/plan/reports/phase3-A.md`

## Read

- `docs/backend-architecture.md` section 6 (all of it), and section 5 step 5
- `docs/requirements.md` decisions D-1, D-3, D-4, D-5, D-6
- `docs/test-cases.md` sections 2.1, 2.2 and 2.3
- `docs/plan/reports/phase1-cities-and-no-fuel.md` for the 22 named counties
- The finished helpers you build on: `stations/sphere.py`, `stations/types.py` (use `build_index`), `stations/exceptions.py`
- Prototype for the name rules: `docs/plan/research/scripts/s6_cities.py`

## Test cases

PL-01 to PL-21 and LD-01 to LD-18, exactly as `docs/test-cases.md` gives them.

## Decisions already made

**The model.** `FuelStation`: `opis_id` (positive integer, unique), `name`, `address`, `city`, `state` (2 characters), `rack_id` (integer), `price` (`DecimalField(max_digits=11, decimal_places=8)`), `lat`, `lng` (floats). Nothing else: no timestamps. Create the migration with `uv run python manage.py makemigrations stations` and apply it with `migrate`.

**The five hand-added places** (looked up on OpenStreetMap, 18 Nov 2026). They live in `places.py`:

| Place | lat | lng |
|---|---|---|
| Port Wentworth, GA | 32.1491 | −81.1632 |
| Henrico, VA | 37.5131 | −77.3465 |
| Evergreen, AL | 31.4335 | −86.9569 |
| Elizabethport, NJ | 40.6501 | −74.1871 |
| University Park, IL | 41.4400 | −87.6834 |

**The places table** is read from `settings.CITIES_CSV` the first time it is needed, and kept. `load_stations --cities <path>` must be able to point the lookup at another file, so give `places.py` a small function for that, and make sure tests leave the default in place afterwards.

**What the loader prints**, one line each, in this order, so tests can read them:

```text
Rows read: 8151
Stations: 6738
In the lower 48 and DC: 6626
Placed from the places table: 6615
Placed from hand-added places: 11
Saved: 6626
```

If any station in the lower 48 or DC cannot be placed, the command raises `CommandError` naming each one as `station <id> <name>: <City>, <ST>`, and the table is left exactly as it was. Replacing the table happens inside one transaction, with `bulk_create`.

**The index.** `get_index()` reads the rows ordered by `opis_id` and builds the index with `stations.types.build_index`. It remembers a non-empty index only. `nearest_station` breaks ties as its docstring says.

**Coverage.** The lower 48 states and DC are covered. Alaska, Hawaii, Puerto Rico, Canadian provinces (by code or name), and a final part that is `Canada` or `Mexico`, raise `OutsideCoverage`.

## The database

PostgreSQL is already running in Docker. `uv run pytest tests/test_loader.py tests/test_index.py -q` creates and removes its own test database. Tests that touch the database need `@pytest.mark.django_db`. The index is remembered per process, so reset it (`reset_index()`) around tests that load different stations.

LD-11 and LD-12 use the real file at `settings.STATIONS_CSV`. LD-18 needs the real stations loaded and takes its two start points from `resolve()`.
