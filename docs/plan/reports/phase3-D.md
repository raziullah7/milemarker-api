# Phase 3 report: builder D, routing client

## 1. Files

- `trips/services/routing.py` (implemented `fetch_route`; `Route` unchanged)
- `tests/test_routing.py` (new)

## 2. Test command and output

`uv run pytest tests/test_routing.py -q`

```
................                                                         [100%]
16 passed in 1.44s
```

`uv run ruff check` and `uv run ruff format` on both files: clean.

## 3. Test-case map

| ID | Test |
|---|---|
| RT-01 | test_rt01_request_address |
| RT-02 | test_rt02_route_result |
| RT-03 | test_rt03_server_error_tries_second_server |
| RT-04 | test_rt04_too_many_requests_tries_second_server |
| RT-05 | test_rt05_timeout_tries_second_server |
| RT-06 | test_rt06_refused_connection_tries_second_server |
| RT-07 | test_rt07_unreadable_answer_tries_second_server (two params: not_json, no_routes) |
| RT-08 | test_rt08_no_route_is_final |
| RT-09 | test_rt09_both_servers_error |
| RT-10 | test_rt10_both_servers_time_out |
| RT-11 | test_rt11_total_deadline |
| RT-12 | test_rt12_user_agent_header; test_rt12_shared_client_sends_user_agent |
| RT-13 | test_rt13_server_template_setting |
| RT-14 | test_rt14_reason_is_timeout_only_if_every_attempt_timed_out |

## 4. Differences from the brief

- None in behaviour. `NoSegment` is handled like `NoRoute`, as the brief says.
- RT-12: a client passed by a test carries its own headers, so the test client is built with the configured name. A second test checks that the module's shared client takes its User-Agent from settings. The header-on-the-wire path for the shared client is therefore checked by inspecting the client, not by a request.

## 5. Unclear or untestable

- RT-11 as written ("both servers answer only after 1 s") is tested with a body that drips for about 1 s in 20 ms chunks. Overrun is bounded by one chunk gap, so each attempt ends near 0.22 s and the call near 0.45 s, under the 0.6 s limit. A single stalled chunk longer than the read timeout is caught by httpx's own read timeout.

## 6. Not sure

- An empty `ROUTING_SERVERS` would report reason `timeout` (`all([])` is true). It cannot happen with the shipped settings, so no handling was added.
- Only a 400 with a `NoRoute`/`NoSegment` code is final; a 400 with any other body counts as a failed attempt, per the brief.
