# Brief 15F3: the fix wave from QA-5

The Mile Marker API (Django) is at release 2.1.0, in progress. An independent review, QA-5, found the items below, and the controller has ruled on them. The full report and the rulings are in `docs/plan/reports/phase15-QA.md`; read that first. Fix exactly the items ruled **Fix**, and nothing else.

The repository root is `F:\Spotter-AI\milemarker-api`.

## Items

1. **Misspelling order** (Important), `stations/places.py`, `_suggestions`, in the no-state branch with no exact name.
   - Keep the order `difflib.get_close_matches` returns, closest first. Population only orders the states that share one city key (for example, two states that both have a large "Springfield").
   - Up to five labels, as now.
   - Add test **PL-24** in `tests/test_places.py`:
     - `Orlndo` → `Orlando, FL` first
     - `Minnepolis` → `Minneapolis, MN` first
     - `Lexigton` → `Lexington, KY` first
     - `Tacma` → `Tacoma, WA` first
     - `Dalas` and `Houstan` still give `Dallas, TX` and `Houston, TX` first.
   - Then correct the documents that describe this case as "largest first":
     - `docs/backend-architecture.md`, about line 165. Say "closest name first". Also write "incorporated places" there (item 10).
     - `docs/use-cases.md`, UC-07 A1.
     - `docs/test-cases.md`: PL-23's wording (the test times `Houstan`, not `Dalas`), and a new PL-24 row in the style of PL-23.
2. **Version 2.1.0.**
   - `pyproject.toml`.
   - The OpenAPI `VERSION` in `config/settings.py`. Change that one line only.
   - Regenerate `docs/openapi.yaml` with `uv run python manage.py spectacular --file docs/openapi.yaml`.
   - Run `uv lock --offline`. If it needs the network, run `uv lock`, and report which one you ran.
3. **N05** in `docs/test-cases.md`. Put back the Actual from the run of 18 Nov: `["Springfield, AR", "Springfield, CO", "Springfield, GA", "Springfield, ID", "Springfield, IL"]` (see `git show b3d3bef:docs/test-cases.md`). Then add one sentence: on 19 Nov, the same request to the 2.1.0 API gave `["Springfield, MO", "Springfield, MA", "Springfield, IL", "Springfield, OR", "Springfield, OH"]` (observed by the controller).
4. **M4 figure.** `docs/backend-architecture.md`, about line 257: "180 to 350 ms" becomes "150 to 350 ms".
8. **Warnings.** `docs/backend-architecture.md`, about line 179, says "(one warning is logged)". Make it true: one warning names the database error, besides the line every error answer gets.
9. **Emptying the cache.** `docs/development.md`, about line 51, where it says to empty the cache after changing `ROUTING_SERVERS`: say that cached refusals (no road, leaves the USA, same place) are emptied with the roads.
10. **Nits.**
    - `data/README.md`: `large_places.csv` is also the list that a no-state misspelling is matched against, not "used only" for ranking.
    - `docs/test-cases.md` line 14: the coverage at the close of Phase 15 is **98.52%** (measured by the controller on 5cd97c0), against the floor of 98%.

## Rules

- **Your files:** `stations/places.py`, `tests/test_places.py`, `pyproject.toml`, `uv.lock`, `config/settings.py` (the VERSION line only), `docs/openapi.yaml` (regenerated only), `docs/backend-architecture.md`, `docs/use-cases.md`, `docs/test-cases.md`, `docs/development.md`, `data/README.md`. Nothing else.
- **Database for pytest:** `DATABASE_URL=postgresql://milemarker:milemarker@127.0.0.1:5432/milemarker_f1`.
- **Tests to run:** `tests/test_places.py`, `tests/test_loader.py`, `tests/test_schema.py`, `tests/test_project.py`, and `tests/test_api.py -k "ep15 or ep17 or ep32"`.
- **Never run:** `tests/test_cache.py` or the full suite.
- **Then run:** `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`.
- **No:** requests to a routing server; starting or stopping a container; git commands that change anything; subagents.
- **Style:** write plainly and briefly, and match the surrounding style.

## Reply

Status, files changed, the test counts, and which `uv lock` you ran, with each claim marked **proved** or **assumed**. Write no report file; the controller records your reply.
