# Brief 5Q2: review the whole project

You are a senior reviewer seeing this project for the first time. It is a take-home assessment for a Backend Django Engineer role: an API that plans the cheapest fuel stops along a driving route. It will be published, read by the hiring team, and its author must be able to explain every line. Other people built it; you wrote none of it.

The repository root is the folder you were given. **Read only. Change nothing** except your report file. No git commands that change anything (`git log`, `git diff` and `git show` are fine). No other agents.

## Read

- `docs/requirements.md` and `docs/backend-architecture.md`: what was promised
- `docs/test-cases.md` and `docs/use-cases.md`: how it is meant to be proven
- All the code: `config/`, `stations/`, `trips/`, `tests/`, `docker-compose.yml`, `pyproject.toml`, `.env.example`, `.gitignore`, `data/README.md`
- You may run `uv run pytest -q` and `uv run ruff check .` (PostgreSQL is running). Do not start the server and do not call the public routing servers.

## What to look for, most serious first

1. **Wrong results.** Any input for which the API would return a wrong plan, a wrong figure, a crash, or a 500. Trace real paths through the code; try to construct the input. Arithmetic, rounding, off-by-one at the 500-mile, 5-mile, 10-mile and 25-mile limits, ties, empty lists, a trip with no stations, the caches returning something stale or belonging to another request.
2. **A promise with no proof.** A requirement, decision or documented behaviour that no test would catch if it broke. Name the requirement and the missing test.
3. **Documents and code that disagree.** Field names, error codes, status codes, defaults, limits, the order of steps.
4. **A layer doing another's job.** The architecture's section 3 says what each layer may do. Rules in the view, HTTP in the business layer, Django in a module that must be pure, a second place that maps errors to statuses.
5. **Concurrency and process state.** The server runs as one process with several threads. Module-level caches, lazy loading, the shared HTTP client, the in-memory index.
6. **Code nobody asked for.** Options, abstractions, error handling for cases that cannot happen, anything a spec line does not justify. This project's rule is the minimum code that solves the problem.
7. **Code that is hard to explain.** Anything the author would struggle to walk through in an interview: clever tricks, misleading names, comments that say what and not why, or comments that are wrong.
8. **What a hiring reviewer would notice.** Secrets or personal data in the repository, files that should not be committed, a setup step that would fail on a fresh clone, anything unprofessional.

## Your report: `docs/plan/reports/phase5-Q2-review.md`

A numbered list of findings, most serious first. For each:

- **Severity:** Critical (wrong result or crash a user can reach), Important (should be fixed before publishing), Minor (worth fixing if cheap), Note (no action needed).
- **Where:** file and line.
- **What is wrong**, in one or two sentences, and **the input or situation that shows it**. For a Critical or Important finding, give the concrete request or values.
- **Whether you confirmed it** by running something, or only read it.
- **The fix you suggest**, in a sentence.

Do not pad. Ten findings that matter beat forty that do not. Say plainly what you checked and found sound, in a short closing section, so the absence of a finding means something.

Reply to the controller with the count of findings by severity and a one-line summary of each Critical and Important one.
