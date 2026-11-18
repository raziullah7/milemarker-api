# Brief 7R: the README, and two sections of the architecture document

A finished, tested API needs the page a stranger reads first. The reader is an engineer at the company that set this as a take-home assessment. They will clone the repository, read the README, run it, and decide in a few minutes whether the work is careful. Write for that reader.

The repository root is the folder you were given; every path is relative to it.

## Rules

- **Your files only:** `README.md`; in `docs/backend-architecture.md`, sections 4 (folder layout) and 14 (speed) and nothing else; and your report `docs/plan/reports/phase7-R.md`. No git commands that change anything. No other agents.
- **Every command and every number must be true.** Take commands from the files that define them and numbers from the documents named below. Do not invent, estimate or round differently. If you cannot find a figure, leave it out and say so in your report.
- You may run read-only commands to check what you write (`docker compose config`, `uv run pytest --collect-only -q`, `ls`). The API is running at `http://127.0.0.1:8000`; you may send it the two requests named under "Example" below, which are cached and cost nothing. Do not request any other trip.
- Plain, direct sentences. No marketing words, no filler, no emoji. Short paragraphs, tables where rows share a shape. Explain a term the first time it appears. Do not mention how the project was produced, beyond linking `docs/plan/` in the list of documents.

## Read

- `docs/requirements.md` (all), `docs/backend-architecture.md` (all), `docs/prd.md`
- `docs/test-cases.md` sections 1, 3, 5 and 7
- `docs/plan/PHASE-4.md`, `PHASE-5.md` and `PHASE-6.md`, the Result sections: the measured figures
- `docker-compose.yml`, `Dockerfile`, `docker/entrypoint.sh`, `.env.example`, `pyproject.toml`, `data/README.md`, `scripts/live_check.py` (its usage text), and the folder tree

## `README.md`

In this order. Aim for a page a reader can take in within three minutes, about 600 to 900 words outside the tables and code blocks.

1. **Title and two sentences:** what the API does and what makes its answer good (cheapest fuel, few stops, one routing call).
2. **Run it.** With Docker: clone, `docker compose up --build`, wait for the line that shows the stations are loaded, then the example request. Say what the reader needs (git and Docker) and that there is no API key and no account.
3. **Example.** The request `GET /api/v1/route/?start=New York, NY&finish=Los Angeles, CA` as a `curl` command that works when pasted, and the real response, shortened: the whole `summary`, `warnings`, `assumptions`, the first two `fuel_stops` then `…`, `map` reduced to its type and a note, and `meta`. Get it from the running API. Then one line each on the two parameters, and one on `stop_cost=0`.
4. **How it works.** Six to eight numbered steps from request to answer, each one sentence, naming the module that does it. Then a short paragraph on the fuel plan: the two moves, why a stop costs $10 while choosing, and that the result is checked against two exact methods. Link to the architecture document for the rest.
5. **What it assumes.** A table of the decisions D-1 to D-15 from `docs/requirements.md`: the question and the decision in a few words each. This is required: a check in the test catalogue (M02) looks for all fifteen.
6. **Errors.** The table of codes and statuses, from architecture section 11.
7. **Speed.** The measured figures: our own work for a new coast-to-coast trip, for a repeat, and for the same trip with another stop cost; and what the routing call itself takes. Say where they were measured.
8. **Tests.** How to run them (in a container, and from source with uv and the Compose database), how many there are, and the kinds: unit, exactness against a linear-programming solver and brute force, integration, an independent verifier, and the live run with its result. How to run the live cases and the Postman collection.
9. **Run from source.** The uv commands, for someone who wants to change the code.
10. **Project layout.** The top-level folders, one line each.
11. **Known limits.** From architecture section 16, shortened, each in a line.
12. **Documents.** A list of what is in `docs/`, one line each, including `docs/plan/` described as the build plan, phase by phase, with the result of each phase.
13. **Data and licences.** One paragraph pointing to `data/README.md`.

To see a trip on a map, the README tells the reader to copy the response's `map` value into geojson.io. Do not claim anything about Postman's Visualize tab.

## `docs/backend-architecture.md`

- **Section 4, folder layout:** make the tree match the repository as it is now (the Docker files, `scripts/`, the test files, the documents). Keep its style: one short description per entry.
- **Section 14, speed:** replace the research figures with the ones measured on the finished API, from the Result sections of `PHASE-3.md`, `PHASE-4.md` and `PHASE-5.md`. Keep the paragraph on the border check's sampling. Remove the sentence saying each figure is a single run of a research script, and say instead where and how these were measured.

## Your report: `docs/plan/reports/phase7-R.md`

Where each number in the README comes from (file and line), any figure you looked for and could not find, and the word count.

Reply to the controller with: status, the word count, and anything you could not source.
