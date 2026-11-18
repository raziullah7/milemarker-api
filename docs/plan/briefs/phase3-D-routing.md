# Brief 3D: the routing client

Read `docs/plan/briefs/phase3-common.md` first. It applies in full.

## Goal

Ask a public routing server for the road between two points, fall back to a second server once if the first fails, and never take longer than the deadline.

## Your files

- `trips/services/routing.py`
- `tests/test_routing.py`
- Report: `docs/plan/reports/phase3-D.md`

## Read

- `docs/backend-architecture.md` section 9 (all of it)
- `docs/test-cases.md` section 2.9
- `config/settings.py`: `ROUTING_SERVERS`, `ROUTING_DEADLINE_SECONDS`, `ROUTING_USER_AGENT`
- `trips/exceptions.py`: `NoRoute`, `RoutingUnavailable`
- `docs/plan/reports/phase1-R1-stack.md` section F: tested facts about httpx, including the fake transport, the exception classes, and why a plain `timeout=` is not a total deadline

## Test cases

RT-01 to RT-14, exactly as `docs/test-cases.md` gives them. Every test uses `httpx.MockTransport`; none touches the network.

## Decisions already made

- **Addresses.** Each entry of `settings.ROUTING_SERVERS` is a template with `{coords}`, which becomes `lng,lat;lng,lat` (longitude first). Write coordinates with at most 6 decimals and no exponent. The `server` in the result is the template's host name.
- **A total deadline per attempt.** `httpx`'s `timeout=` applies to each phase separately, so a slow drip of bytes can outlast it. Send the request with `client.stream(...)`, with connect and read timeouts equal to the deadline, and while reading the body check a monotonic clock; once the deadline has passed, treat the attempt as timed out.
- **When to try the next server:** timeout, connection error, a 5xx or 429 status, a body that is not JSON, or JSON that does not hold a usable route (no `routes`, fewer than two points, a non-positive distance).
- **When not to:** the server answers with OSRM code `NoRoute` or `NoSegment` (it does so with HTTP status 400). Raise `NoRoute` at once.
- **Any other 4xx** is our own mistake in building the request; the second server would say the same. Treat it as a failure of that attempt and move on, so the caller gets `RoutingUnavailable` with reason `error`.
- **If every server failed:** `RoutingUnavailable(message, reason=...)`, where reason is `"timeout"` only when every attempt timed out and `"error"` otherwise (RT-14 covers both orders).
- **The client.** With no `client` argument, use one module-level `httpx.Client`, created on first use, with the User-Agent header from settings. Tests pass their own client built on a fake transport.
- **The result.** `coords` is a numpy array of shape (n, 2), rows `[lng, lat]`. `distance_miles` is the service's `distance` in metres ÷ 1609.344. `calls` counts the requests made.

## Notes for the tests

- RT-11 needs an answer that arrives too slowly. A fake handler that sleeps cannot be interrupted, so give the response a byte stream that yields slowly (a generator that sleeps between small chunks) and set the deadline setting to 0.2 seconds with `settings` from pytest-django. The call must give up in under 0.6 seconds.
- RT-13 changes `ROUTING_SERVERS` with the same `settings` fixture.
- Count requests in the fake handler.
