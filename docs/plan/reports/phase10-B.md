# Phase 10, brief B: Makefile, CI, pre-commit, Dependabot

Files: `Makefile`, `.github/workflows/ci.yml`, `.github/dependabot.yml`, `.pre-commit-config.yaml`, this report.

## Makefile targets

"Ran" means run for real. "Dry" means `make -n` printed the command, which was checked against its source.

| Target | Command | Ran |
|---|---|---|
| `help` | `@echo` lines, one per target | Yes, Git Bash and PowerShell |
| `up` | `docker compose up --build -d` | Dry (stack in use) |
| `down` | `docker compose down` | Dry |
| `logs` | `docker compose logs -f api` | Dry |
| `ps` | `docker compose ps` | Yes, Git Bash and PowerShell |
| `dev` | `docker compose up -d db`, then `uv run python manage.py runserver 127.0.0.1:$(DEV_PORT)` (8001; reload is runserver's default) | Dry |
| `migrate`, `load`, `shell` | `uv run python manage.py migrate`, `load_stations`, `shell` | Dry |
| `test` | `uv run pytest` | Yes, see concerns |
| `test-slow` | `uv run pytest -m slow` | Dry |
| `test-docker` | `docker compose --profile test run --rm test` | Dry |
| `coverage` | `uv run pytest --cov` (settings in `pyproject.toml`) | Dry |
| `lint` | `uv run ruff check .`, `uv run ruff format --check .` | Yes, Git Bash and PowerShell |
| `format` | `uv run ruff check --fix .`, `uv run ruff format .` | Dry (it would rewrite other builders' files) |
| `typecheck` | `uv run mypy` | Dry |
| `audit` | `uv run pip-audit` | Dry |
| `check` | prerequisites `lint typecheck test` | Dry |
| `e2e-up`, `e2e-down` | `docker compose -f docker-compose.yml -f docker-compose.e2e.yml up --build -d` / `down` | Dry |
| `e2e` | `npx --yes newman run docs/postman/milemarker.postman_collection.json --env-var base_url=http://127.0.0.1:8000 --delay-request 1200` (the README's command; the delay keeps under the 60/min throttle) | Dry |
| `live` | `uv run python scripts/live_check.py --base-url http://127.0.0.1:8000` | Dry; its help line says it calls the public routing server |
| `clean` | `docker compose -f docker-compose.yml -f docker-compose.e2e.yml down -v --remove-orphans` (covers both stacks) | Dry |

Results of the runs:

- `help`: exit 0 under both shells. The lines read `target - description`. They are unquoted, because quotes would print under `cmd.exe`, so `sh` collapses any column alignment; the dash format reads the same either way.
- `ps`: exit 0 under both shells; shows `api` and `db`.
- `lint`: it runs both Ruff commands and exits 1 under Git Bash and 2 under PowerShell, because Ruff reports one SIM105 finding in `scripts/fake_osrm.py`, builder A's file, which is still in progress. The Makefile is not at fault.
- `test`: the target starts pytest under both shells, but could not finish. At the first attempt `tests/test_verify.py` failed to import `places_from` from `tests/verify.py` (a file another builder was editing). With that file ignored, the run reached 21% in about seven minutes and I stopped it. The machine had many pytest processes running at once. I never saw the suite pass through `make test`.

## Facts checked

- Service container with health check, `ports: 5432:5432`, `localhost` from a job on the runner: https://docs.github.com/en/actions/using-containerized-services/creating-postgresql-service-containers
- `astral-sh/setup-uv`: current release v10.3.3; its tags are `v7` and exact versions from v10.0 on, with no moving `v10` (`git ls-remote --tags https://github.com/astral-sh/setup-uv`). `enable-cache` and the `version` input are documented at https://github.com/astral-sh/setup-uv
- Other actions' current moving major tags, from `git ls-remote --tags`: `actions/checkout` v7, `docker/setup-buildx-action` v4, `docker/build-push-action` v7.
- `astral-sh/ruff-pre-commit` has the tag `v0.17.5` (the `uv.lock` Ruff version); hook ids `ruff-check` and `ruff-format`: https://github.com/astral-sh/ruff-pre-commit
- `pre-commit/pre-commit-hooks` tag `v6.0.0` (latest) and the six hook ids: https://github.com/pre-commit/pre-commit-hooks
- Newman 6.2.3 is the current npm release (`npm view newman version`).

## Pre-commit

`pre-commit run --all-files` was run on a copy of the repository in the scratchpad, so no file in the real repository was touched and nothing needs restoring. All eight hooks passed and none would change a file. The copy held the other builders' files as they were at that moment.

## Concerns

1. The brief says to pin each action to a major tag. `astral-sh/setup-uv` has no moving tag for its current major, so `ci.yml` uses the exact `v10.3.3` (a comment says why). Dependabot will move it.
2. `docs/test-cases.md` rows differ from the brief: MK-01 lists a `web-dev` target, and CI-02 lists `manage.py check --deploy` and the viewer's steps. Neither is in this brief, so I did not add them. They come with the later phases.
3. The CI `e2e` job relies on builder A's files, as the brief describes them: `docker-compose.e2e.yml` with `fake-osrm` published on `127.0.0.1:5000`, `GET /_requests` returning `{"requests": [{"matched": ...}]}` (row 22 of PHASE-9). The job reads that port as 5000 (the default). It was not run; I cannot push. It treats an empty log as a failure too, so a collection that never reaches routing cannot pass.
4. The `e2e` job's first API start loads the stations, and the wait loop allows 5 minutes.
5. `.pre-commit-config.yaml` sets `--fix` on Ruff's check, the hook's documented default. Remove it if a hook should only report.
6. With three builders using one PostgreSQL, a pytest run killed part-way leaves its `test_*` database behind, and the next run then waits on a keep-or-delete prompt. I dropped the one I left (`test_milemarker_b`).
