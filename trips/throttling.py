"""The rate limit: 60 requests a minute for each client (NFR-16; architecture document,
section 10, "The rate-limit counter"). The settings name it in place of the framework's
AnonRateThrottle, with the same rate setting and the same way of finding the client.

The count is kept in the cache, so every worker shares it. The framework's own limiter keeps
a client's history in one entry, which it reads, adds to and writes back: requests sent at
once read the same history and overwrite each other's entry, so most of them are never
counted (164 of 300 passed, review QA-1). This one counts each request with one atomic step,
the cache's own increment (Redis INCR).

- A window opens with a client's first request and lasts 60 seconds. One key holds its
  start, written with `add`, so that requests arriving together agree on one start.
- The count is held under a second key that carries the start, so each window counts from
  nothing. It lives twice as long as the window, so it cannot expire under an increment:
  Django's Redis increment checks that the key exists and then increments it, and an
  increment of a key that expired in between would make one with no expiry at all.
- The 61st request inside the window is refused, and the wait reported is the time left in
  the window, at least 1 second.
"""

import time

from rest_framework.throttling import SimpleRateThrottle


class FixedWindowThrottle(SimpleRateThrottle):
    """At most the "anon" rate of requests for each client, in a window that opens with its
    first request. The client is found by the framework's get_ident, so DJANGO_NUM_PROXIES
    works as it did for the framework's own limiter."""

    scope = "anon"

    def allow_request(self, request, view) -> bool:
        """Count this request in its client's window; True while the count is within the rate."""
        ident = self.get_ident(request)
        self.now = time.time()
        # get_or_set writes with add and reads back what is stored, so requests that find no
        # window at once all take the one start that was stored first.
        self.start = self.cache.get_or_set(
            f"throttle_{self.scope}_start_{ident}", self.now, self.duration
        )
        count_key = f"throttle_{self.scope}_count_{ident}_{self.start}"
        try:
            count = self.cache.incr(count_key)
        except ValueError:
            # The window's first count. Of requests that arrive together, one adds the key
            # and the others find it there and increment it.
            if self.cache.add(count_key, 1, 2 * self.duration):
                count = 1
            else:
                count = self.cache.incr(count_key)
        return count <= self.num_requests

    def wait(self) -> float:
        """The seconds left in the window, at least 1. Redis keeps time by its own clock, so
        it can still hold a window that this process's clock says is over."""
        return max(1.0, self.start + self.duration - self.now)
