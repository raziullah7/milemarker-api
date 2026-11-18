"""The cache: Redis, shared by every worker, or this process's own memory when Redis cannot
be reached (architecture document, section 10; D-15, D-16).

It holds the road cache, the answer cache and the rate-limit counters: the settings make it
Django's default cache when REDIS_URL is set. It knows nothing of what it holds.

- Every call goes to Redis, through Django's own Redis backend, with short socket timeouts
  and no retry. It runs on a small pool of threads of this process's own, and the caller
  waits for it at most REDIS_DEADLINE_SECONDS: some faults no socket timeout can see, such
  as a name that takes seconds to fail to resolve when the Redis container is stopped. So
  a Redis that is down, hung or gone costs a request at most about half a second.
- When a call fails with any error of the Redis client, or misses the deadline, memory
  serves it, and this process falls back to its own memory, logs one warning naming
  itself, and leaves Redis alone for 30 seconds. Then the next call tries Redis again: a
  try that fails starts another 30 seconds, and logs nothing new; one that works brings
  the process back to Redis, and logs one line. Only that try can end a fallback.
- Django makes one cache object per thread. What the threads of one process must share, the
  fallback state, the memory and the pool, is kept per process, in `_processes`.
"""

import logging
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from django.core.cache import caches
from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache
from django.core.cache.backends.locmem import LocMemCache
from django.core.cache.backends.redis import RedisCache
from redis.backoff import NoBackoff
from redis.exceptions import RedisError
from redis.retry import Retry

logger = logging.getLogger(__name__)

# How long a process that fell back leaves Redis alone before it tries again.
RETRY_AFTER_SECONDS = 30.0

# The Redis client's options. 0.1 s to connect and 0.25 s for a command; and no retry, said
# outright, so the bounds hold whatever the client library's own default.
REDIS_OPTIONS = {
    "socket_connect_timeout": 0.1,
    "socket_timeout": 0.25,
    "retry": Retry(NoBackoff(), 0),
}

# The longest a caller waits for one Redis call. Above the two socket timeouts together
# (0.1 + 0.25), so those still fire first for every fault they can see; this catches the
# rest, a slow name lookup above all, which no socket timeout bounds.
REDIS_DEADLINE_SECONDS = 0.4

# The threads that run the Redis calls of one process. More than a worker's four, so a call
# waits behind another only when Redis is stuck, and then it misses its deadline, as it should.
REDIS_THREADS = 8

# The process's own memory holds as many entries as the in-memory cache of the settings.
MEMORY_ENTRIES = 500


class _Process:
    """What every cache object of this process shares for one Redis."""

    def __init__(self, params: dict):
        self.lock = threading.Lock()
        # Redis is not touched before this time, by time.monotonic(). 0 while it is in use.
        self.retry_at = 0.0
        # True from the warning to the line that says Redis is back.
        self.falling_back = False
        # A name of its own, so that no other cache shares its entries.
        self.memory = LocMemCache(
            f"fallback-{uuid.uuid4().hex}", {**params, "OPTIONS": {"MAX_ENTRIES": MEMORY_ENTRIES}}
        )
        # Made with the first cache object, inside the worker: gunicorn does not preload the
        # application, so no pool is ever made before the fork. Its threads start on first use.
        self.pool = ThreadPoolExecutor(max_workers=REDIS_THREADS, thread_name_prefix="redis")


# One entry per Redis address, for the life of the process.
_processes: dict[str, _Process] = {}
_processes_lock = threading.Lock()


class RedisWithFallback(BaseCache):
    """Django's Redis cache, with this process's own memory in its place while Redis cannot
    be reached. Named in the settings as the default cache when REDIS_URL is set."""

    def __init__(self, server: str, params: dict):
        super().__init__(params)
        self._redis = RedisCache(server, {**params, "OPTIONS": REDIS_OPTIONS})
        with _processes_lock:
            if server not in _processes:
                _processes[server] = _Process(params)
            self._process = _processes[server]

    @property
    def falling_back(self) -> bool:
        """Whether this process is on its own memory, Redis having failed."""
        return self._process.falling_back

    # Django's six basic cache operations, and incr. Its others (get_many, get_or_set, decr
    # and the rest) are built on these, so they follow the same path.

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        """Store a value only if the key is not held yet."""
        return self._call("add", key, value, timeout, version=version)

    def get(self, key, default=None, version=None):
        """The value held for the key, or `default`."""
        return self._call("get", key, default, version=version)

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        """Store a value."""
        return self._call("set", key, value, timeout, version=version)

    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        """Give a held key a new time to live."""
        return self._call("touch", key, timeout, version=version)

    def delete(self, key, version=None):
        """Forget a key."""
        return self._call("delete", key, version=version)

    def clear(self):
        """Forget every key: in Redis, its whole database."""
        return self._call("clear")

    def incr(self, key, delta=1, version=None):
        """Add `delta` to a held number in one atomic step, Redis's INCRBY or memory's own;
        ValueError if the key is not held. Django would otherwise build it from a read and a
        write, and increments sent at once, as the rate limit's are, would be lost."""
        return self._call("incr", key, delta, version=version)

    def _call(self, method: str, *args, **kwargs):
        """Run one cache operation on Redis, or on this process's memory while it falls back.

        On Redis it runs on the process's pool, and is waited for at most
        REDIS_DEADLINE_SECONDS. One that misses the deadline is left to finish by itself; its
        result or error is dropped, and memory serves this call, as after a connection error.
        """
        where = self._where()
        if where != "memory":
            call = self._process.pool.submit(getattr(self._redis, method), *args, **kwargs)
            try:
                result = call.result(timeout=REDIS_DEADLINE_SECONDS)
            except RedisError as error:
                # Every error of the Redis client, not only a refused connection or a timeout:
                # an error Redis answers with, such as a database that does not exist or a
                # server that is read-only, would otherwise fail every request (Q1-03).
                self._fall_back(error)
            except TimeoutError:
                self._fall_back(TimeoutError(f"no answer within {REDIS_DEADLINE_SECONDS} s"))
            else:
                # Only the try ends a fallback. Any other answer is to a call sent before the
                # fallback began, and says nothing of Redis now (Q1-04).
                if where == "try":
                    self._redis_answered()
                return result
        return getattr(self._process.memory, method)(*args, **kwargs)

    def _where(self) -> str:
        """Where this call goes: "memory" while this process is inside its 30 seconds away
        from Redis, "try" for the one call that tries Redis again when they are over, and
        "redis" otherwise.

        The try's own 30 seconds start at once, so the process's other threads keep to memory
        meanwhile.
        """
        process = self._process
        with process.lock:
            now = time.monotonic()
            if now < process.retry_at:
                return "memory"
            if process.falling_back:
                process.retry_at = now + RETRY_AFTER_SECONDS
                return "try"
            return "redis"

    def _fall_back(self, error: Exception) -> None:
        """Redis failed: keep away from it for 30 seconds, and warn once per outage."""
        process = self._process
        with process.lock:
            process.retry_at = time.monotonic() + RETRY_AFTER_SECONDS
            first = not process.falling_back
            process.falling_back = True
        if first:
            logger.warning(
                "Redis cannot be reached (%s: %s). Process %s keeps the cache and the rate "
                "limit in its own memory and tries Redis again every %.0f seconds.",
                type(error).__name__,
                error,
                os.getpid(),
                RETRY_AFTER_SECONDS,
            )

    def _redis_answered(self) -> None:
        """The try worked: this process is back on Redis, and says so once. There is one try
        at a time, made only while the process falls back, so this runs once per outage."""
        process = self._process
        with process.lock:
            process.falling_back = False
            process.retry_at = 0.0
        logger.info("Redis answers again. Process %s keeps the cache in Redis again.", os.getpid())


def cache_state() -> str:
    """Where this process's cache is, for the health answer (architecture section 11):
    "memory" with REDIS_URL unset, else "redis", or "fallback" while it falls back.

    With Redis, one cheap read first, so that a Redis that has gone, or come back, is
    noticed now and the state is current.
    """
    cache = caches["default"]
    if not isinstance(cache, RedisWithFallback):
        return "memory"
    cache.get("health")
    return "fallback" if cache.falling_back else "redis"
