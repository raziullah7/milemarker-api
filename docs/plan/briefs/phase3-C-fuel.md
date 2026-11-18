# Brief 3C: the fuel plan

Read `docs/plan/briefs/phase3-common.md` first. It applies in full.

## Goal

Given stations on a line with their prices, decide where the truck stops and how much it buys, so the trip costs as little as possible. This is the core of the product: a mistake here is a wrong dollar figure.

## Your files

- `trips/services/fuel.py`
- `tests/test_fuel.py`
- `tests/exact.py` (test-only helpers: the two exact methods)
- Report: `docs/plan/reports/phase3-C.md`

## Read

- `docs/backend-architecture.md` section 8 (all of it)
- `docs/requirements.md` decisions D-1, D-7, D-9
- `docs/test-cases.md` sections 2.6 and 2.7
- `trips/exceptions.py` (`NoFuelPlan`)
- Prototype: `docs/plan/research/scripts/s5_optimiser.py` (`dp`, `greedy`, `lp`, `brute`). It already matched both exact methods to the cent. Two things in it must change, as below.

## Test cases

FU-01 to FU-25 and EX-01 to EX-04, exactly as `docs/test-cases.md` gives them.

## Decisions already made

- **`plan_stops` is a loop, not a function that calls itself.** The prototype's `dp` is recursive and raises the interpreter's recursion limit; that is not acceptable in a server. Work from the last station back to the first, filling a table indexed by (station, station where the tank was last filled, or "arrived empty").
- **`find_gap` decides whether a plan exists**, in one pass over the mile markers. `plan_stops` and `cheapest_fuel` call it first and raise `NoFuelPlan(message, gap_start_mile=..., gap_miles=...)`.
- **No zero purchases.** `plan_stops` never returns a purchase of zero gallons. `cheapest_fuel` may return very small ones (FU-23).
- **Ties are settled the same way every time.** When two choices cost the same, take the one with fewer stops, then the earlier station, so the same input always gives the same plan.
- **Pure Python.** No numpy in `fuel.py`: the inputs are short lists, and plain loops are easier to explain.
- Several stations may share one mile marker (FU-10).

## The two exact methods (`tests/exact.py`)

- `lp_cost(miles, prices, total_miles) -> float | None`: the true lowest fuel cost with free stops, by `scipy.optimize.linprog(..., method="highs")`. Variables are the gallons bought at each station. Constraints: the tank is never below empty on arrival anywhere, including the finish, and never above 50 gallons on leaving a station. Returns `None` when no plan exists.
- `brute_cost(miles, prices, total_miles, stop_cost) -> float | None`: the minimum, over every subset of stations that includes the start, of `lp_cost` on that subset plus `stop_cost` × the number of stations in it that buy more than a negligible amount. **Each subset is priced by `lp_cost`, not by the greedy rule**, so the check shares no code with `fuel.py`. Skip a subset whose gaps make it impossible before calling the solver.

The brute-force check is expensive: every subset of 9 stations is 512 solver calls. Measure it. The exactness tests that run by default must finish in **about 20 seconds or less** on this machine. If EX-02 as written (250 trips of up to 10 stations) takes longer, keep the default run smaller, put the full-size run behind `@pytest.mark.slow`, and say in your report exactly what sizes you chose and how long each takes. The controller will update `docs/test-cases.md` to match.

## Speed

Put these in your report, best of five runs: `plan_stops` on 100 stations spread over 2,800 miles, and on 400 stations (the rare fallback to every station); `cheapest_fuel` on 400 stations. The first should be a few milliseconds.
