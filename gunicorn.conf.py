"""gunicorn's settings for the API (architecture document, section 18).

gunicorn reads this file from the folder it starts in: `gunicorn -c gunicorn.conf.py`.
"""

import os

wsgi_app = "config.wsgi:application"
bind = "0.0.0.0:8000"


# The two values this file reads from the environment are checked as config/settings.py
# checks its own, with the same words: a bad one stops the start, naming the variable and
# the value (Q1-07).
def _workers() -> int:
    """WEB_CONCURRENCY, or 2. At 0 gunicorn would listen with no worker and answer nothing."""
    value = os.environ.get("WEB_CONCURRENCY", "").strip()
    if not value:
        return 2
    if not value.isdecimal() or int(value) < 1:
        raise ValueError(f"WEB_CONCURRENCY must be a whole number of 1 or more, not {value!r}.")
    return int(value)


def _log_level() -> str:
    """LOG_LEVEL in small letters, or "info". Any other name would make gunicorn fail to set
    up its logger, and restart again and again."""
    value = os.environ.get("LOG_LEVEL", "").strip() or "info"
    if value.upper() not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError(
            f"LOG_LEVEL must be one of DEBUG, INFO, WARNING, ERROR or CRITICAL, not {value!r}."
        )
    return value.lower()


# Two worker processes by default (NFR-19), each with four threads: eight requests at once,
# so a hung routing server cannot take every slot from the health check (Q0a-25).
# gunicorn reads WEB_CONCURRENCY itself as it loads, before this file, and fails on an empty
# or non-numeric value; the Compose file therefore gives it 2 when nothing sets it.
workers = _workers()
worker_class = "gthread"
threads = 4

# No preload. Each worker loads the places, the borders and the stations as it starts
# (config/wsgi.py); preloaded, the workers would share the parent's open database
# connection and HTTP client.
preload_app = False

# A stop lets a request in flight finish, for up to 30 seconds (NFR-22). Its slowest
# proper answer, two routing attempts that each time out, takes about 20.
graceful_timeout = 30

# A request line of up to 8,190 bytes, gunicorn's highest (its default is 4,094), so a long
# address reaches the API and gets the API's JSON answer. gunicorn answers a longer line
# itself, with an HTML 414 it gives no way to change. A reverse proxy, if one is put in
# front, would need a limit below this one to refuse such a line first (Q1-05).
limit_request_line = 8190

# The lowest level of message written, as for the API's own lines.
loglevel = _log_level()

# One line per request on standard output, with the request's ID from the answer's
# X-Request-ID header (trips/middleware.py), and the worker that answered.
accesslog = "-"
access_log_format = '[%({x-request-id}o)s] %(h)s "%(r)s" %(s)s %(b)s %(M)sms worker %(p)s'

# gunicorn's own lines in the API's form: a time, a level, then the line. Its own lines
# belong to no request, so they carry "-" where the API's carry the request's ID.
logconfig_dict = {
    "formatters": {
        "server": {"format": "%(asctime)s %(levelname)s [-] %(name)s: %(message)s"},
        "access": {"format": "%(asctime)s %(levelname)s %(message)s"},
    },
    "handlers": {
        "server": {
            "class": "logging.StreamHandler",
            "formatter": "server",
            "stream": "ext://sys.stdout",
        },
        "access": {
            "class": "logging.StreamHandler",
            "formatter": "access",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {"level": loglevel.upper(), "handlers": []},
    "loggers": {
        "gunicorn.error": {"level": loglevel.upper(), "handlers": ["server"], "propagate": False},
        "gunicorn.access": {"level": loglevel.upper(), "handlers": ["access"], "propagate": False},
    },
}
