"""gunicorn's settings for the API (architecture document, section 18).

gunicorn reads this file from the folder it starts in: `gunicorn -c gunicorn.conf.py`.
"""

import os

wsgi_app = "config.wsgi:application"
bind = "0.0.0.0:8000"

# Two worker processes by default (NFR-19), each with four threads: eight requests at once,
# so a hung routing server cannot take every slot from the health check (Q0a-25).
# An empty value counts as not set, because Compose passes the variable through.
workers = int(os.environ.get("WEB_CONCURRENCY", "").strip() or 2)
worker_class = "gthread"
threads = 4

# No preload. Each worker loads the places, the borders and the stations as it starts
# (config/wsgi.py); preloaded, the workers would share the parent's open database
# connection and HTTP client.
preload_app = False

# A stop lets a request in flight finish, for up to 30 seconds (NFR-22). Its slowest
# proper answer, two routing attempts that each time out, takes about 20.
graceful_timeout = 30

# The lowest level of message written, as for the API's own lines.
loglevel = os.environ.get("LOG_LEVEL", "").strip().lower() or "info"

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
