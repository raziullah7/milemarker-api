# Brief R4: write the product requirements document

A small Django API has been fully specified but not built yet. Write its PRD: the one page someone reads first to understand what the product is for and what "done" means. Do not write code. Do not spawn other agents. Edit only the file named below.

## Read first

1. `docs/requirements.md`
2. `docs/backend-architecture.md` (sections 1, 2, 11 and 16 are enough)

## Write `docs/prd.md`

Sections, in this order:

1. **Summary.** Two or three sentences: what the product is and who it is for.
2. **Problem.** Why choosing fuel stops is worth solving, using the facts in `requirements.md` (price spread, the 500-mile range, uneven station coverage).
3. **Users and what they need.** The driver or dispatcher, the operator who loads the data, and a reviewer running the project.
4. **Goals.** What the product must achieve. Each goal names the requirement IDs behind it.
5. **Non-goals.** What it deliberately does not do, from the out-of-scope list.
6. **Scope.** What is in the first release (needs and wants) and what is left for later (nice-to-haves), by requirement ID. Do **not** copy the requirement tables; refer to them.
7. **How it behaves.** A short walk through one request and its answer, in words, with the example request. Mention the stop cost and why it exists.
8. **Success measures.** The measurable targets: speed, number of routing calls, correctness of the fuel bill, fewer than 10 stops coast to coast.
9. **Release criteria.** The acceptance checks, summarised, pointing to `requirements.md` section 9.
10. **Risks and known limits.** From the architecture document's known limits, each with what is done about it.
11. **Related documents.** `requirements.md`, `backend-architecture.md`, `use-cases.md`, `test-cases.md`.

## Rules

- About one page: aim for 450 to 650 words. It links to the other documents and does not repeat their tables.
- Every number comes from the two documents you read. Do not invent figures.
- This file goes into a public repository. Write plain, direct sentences. No filler, no marketing language. Do not mention agents, plans or how the document was produced.

## Reply to me with

- The word count.
- Anything in the two documents you found unclear or contradictory, with the section it is in.
