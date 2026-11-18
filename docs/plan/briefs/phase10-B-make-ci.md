# Brief 10B: Makefile, CI, pre-commit, Dependabot

A finished, tested Django API needs the everyday commands in one place and its checks run on every push. The repository is public on GitHub. It will be read by engineers judging whether the work is careful.

The repository root is the folder you were given; every path is relative to it.

## Rules

- **Your files only:** `Makefile`, `.github/workflows/ci.yml`, `.github/dependabot.yml`, `.pre-commit-config.yaml`, and your report `docs/plan/reports/phase10-B.md`. Change nothing else: not `pyproject.toml`, not the Compose files, not the README. No git command that changes anything: you cannot push, so you cannot see CI run; the controller does that. No other agents.
- **No request to the public routing servers.** Do not run `make live` or Newman.
- Every command you write must be one that exists. Take each from the file that defines it: `pyproject.toml`, `docker-compose.yml`, `README.md`, `scripts/live_check.py`.
- Check current facts before you write them (action versions, the uv setup action, service-container syntax, pre-commit hook revisions) against the projects' own documentation, not from memory.

## Read first

- `README.md`, `pyproject.toml`, `docker-compose.yml`, `Dockerfile`, `docker/entrypoint.sh`, `.env.example`.
- `docs/plan/briefs/phase10-A-harness.md`: another builder is adding `scripts/fake_osrm.py` and `docker-compose.e2e.yml` at the same time. Your `e2e` targets and CI job use them as that brief describes them.

## `Makefile`

GNU make. It must work on Linux, on macOS, and on Windows under both Git Bash and PowerShell, where a recipe may be run by `cmd.exe`. So: every recipe line is one plain command; no `&&` chains, no shell conditionals, no `VAR=value command` prefixes, no backticks. Variables go in make variables. Declare every target `.PHONY`. The first target is `help`.

| Target | Runs |
|---|---|
| `help` | Lists every target with its one-line description. It must work without `grep`, `awk` or `sed` (they do not exist under `cmd.exe`): write the list as plain `@echo` lines |
| `up` | The Compose stack, built, in the background |
| `down` | Stops it |
| `logs` | Follows the API's log |
| `ps` | Shows the services |
| `dev` | Two recipe lines: the database container up, then the API from source with auto-reload on port 8001 (a variable, `DEV_PORT`) |
| `migrate`, `load`, `shell` | `manage.py migrate`, `manage.py load_stations`, `manage.py shell`, from source |
| `test` | The suite from source |
| `test-slow` | The slow exactness test |
| `test-docker` | The suite in a container |
| `coverage` | The suite with a coverage report in the terminal |
| `lint` | Ruff's checks and its format check (two lines) |
| `format` | Ruff's fixes and formatter |
| `typecheck` | `uv run mypy` (its settings are in `pyproject.toml`) |
| `audit` | `uv run pip-audit` |
| `check` | `lint`, `typecheck`, `test`, as prerequisites |
| `e2e-up`, `e2e-down` | The end-to-end stack with the stand-in routing server |
| `e2e` | Newman on the whole Postman collection against the running end-to-end stack |
| `live` | `scripts/live_check.py` against the running stack. Its description says it calls the public routing server |
| `clean` | Stops everything and deletes the volumes |

GNU make is at `make` on Linux. On the build machine it may not be on the path of your shell yet; find `make.exe` under the user's WinGet packages folder and call it by its full path. Run `help`, `lint`, `ps` and `test` yourself under Git Bash and under PowerShell, and say what happened. Do not run `up`, `down`, `clean`, `dev`, `e2e*` or `live`: another builder is using the containers.

## `.github/workflows/ci.yml`

On every push and every pull request. Cancel a superseded run of the same branch. Least privilege: `permissions: contents: read`. Pin each action to a major version tag.

- **`checks` job**, on Ubuntu, with a PostgreSQL 17 service container that has a health check: install uv and the locked dependencies (`uv sync --frozen`); Ruff check; Ruff format check; mypy; `manage.py makemigrations --check --dry-run`; the suite with coverage, written to the job summary; the slow exactness test; `pip-audit`.
- **`image` job:** build the Docker image, with the build cache.
- **`e2e` job:** start the end-to-end stack, wait until the API answers, run the whole Postman collection with Newman, then read the stand-in's request log and fail if any request in it was not matched to a recording. On failure, print the containers' logs. Always stop the stack.

The database settings the suite needs are in `config/settings.py`: one `DATABASE_URL`, whose default already matches the service container if it uses the same user, password and database name as `docker-compose.yml`.

## `.github/dependabot.yml`

Weekly, grouped so each ecosystem opens at most one pull request a week: `uv`, `docker`, `github-actions`. (An `npm` entry is added in a later phase.)

## `.pre-commit-config.yaml`

Ruff's check and formatter from its official hook repository, at the revision matching the Ruff version in `uv.lock`, plus the standard hygiene hooks: trailing whitespace, end of file, YAML and TOML syntax, merge-conflict markers, large files. Exclude what must stay byte for byte: `data/`, and `*.gz`. Run it once over the whole repository and report what it would change; do not let it change files outside your ownership (run with `--all-files` and then restore anything it touched with `git checkout`, listing those files in your report so the controller can decide).

## Your report: `docs/plan/reports/phase10-B.md`

Each target with the command it runs and whether you ran it; where each fact you checked came from (URL); what pre-commit would change; anything you are unsure of.

Reply to the controller with: status, which targets you ran under which shell, and any concern.
