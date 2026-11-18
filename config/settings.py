"""Settings for the Mile Marker API.

One file on purpose: every setting that differs between machines comes from an environment
variable (architecture document, section 18), and each has a default that works with the
Compose file, so a fresh clone runs with no configuration at all. `.env.example` lists them.

The service has no users, sessions, cookies or admin site, and one template, the Swagger
page's. That is why the app and middleware lists are short: Django REST Framework runs
without the auth apps when it is told there is no user (see REST_FRAMEWORK below).
"""

import os
import secrets
from decimal import Decimal
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _flag(name: str, default: bool) -> bool:
    """Read an on/off environment variable ("1", "true", "yes", "on" mean on)."""
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _text(name: str, default: str) -> str:
    """Read an environment variable. Empty or blank counts as not set, because Compose
    passes each variable through to the containers even when nothing sets it."""
    return os.environ.get(name, "").strip() or default


# --- Django ---------------------------------------------------------------------------

# Nothing in this service signs or encrypts anything (no sessions, no cookies, no tokens),
# so with no key given a random one is made at start-up, and the workers need not share it.
SECRET_KEY = _text("DJANGO_SECRET_KEY", secrets.token_urlsafe(50))

DEBUG = _flag("DJANGO_DEBUG", False)

# The host names the API answers to. Any other gets 400 invalid_request (D-21); the check
# itself is trips.middleware.AllowedHostsMiddleware.
ALLOWED_HOSTS = [
    host.strip()
    for host in _text("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",")
    if host.strip()
]
# Always 127.0.0.1, whatever the variable says: the container's health check asks under that
# name, and set to the deployment's own name alone the API would never be healthy (Q1-02).
# The API builds no address from the host name, so allowing this one opens nothing.
if "127.0.0.1" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("127.0.0.1")

INSTALLED_APPS = [
    "rest_framework",
    "drf_spectacular",
    "stations",
    "trips",
]

MIDDLEWARE = [
    # First, so that every log line written while a request is answered carries its ID,
    # a refused host's included.
    "trips.middleware.RequestIdMiddleware",
    # The security headers on every answer the API sends (architecture section 18).
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # A host that is not allowed gets the API's own 400, whatever DEBUG is.
    "trips.middleware.AllowedHostsMiddleware",
    # Checks the host again; with APPEND_SLASH off it never redirects, so both forms of an
    # address answer as themselves.
    "django.middleware.common.CommonMiddleware",
]

APPEND_SLASH = False

# The Swagger page is the one template in the service (architecture section 11).
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
    }
]

# One value everywhere, a reverse proxy's included, if one is put in front.
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# TLS, HSTS and the redirect to HTTPS belong to the TLS terminator put in front (D-23), so
# SECURE_HSTS_SECONDS stays 0 and SECURE_SSL_REDIRECT stays off.
SILENCED_SYSTEM_CHECKS = [
    "security.W003",  # CSRF: no cookies, no sessions and no forms, so nothing to forge
    "security.W004",  # HSTS: set by the TLS terminator in front, not here (D-23)
    "security.W008",  # redirect to HTTPS: the TLS terminator's job, not ours (D-23)
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

USE_TZ = True
TIME_ZONE = "UTC"

# --- Database -------------------------------------------------------------------------

# PostgreSQL, from one DATABASE_URL. The default matches docker-compose.yml, so
# "docker compose up -d db" followed by "manage.py migrate" works with nothing set.
DATABASES = {
    "default": dj_database_url.parse(
        _text("DATABASE_URL", "postgresql://milemarker:milemarker@127.0.0.1:5432/milemarker"),
        conn_max_age=60,
        conn_health_checks=True,
    )
}
# A database that does not answer is given up on after 5 seconds, and the request is answered
# 503 stations_not_loaded. Without it the driver can wait far longer. A connect_timeout in
# DATABASE_URL wins.
DATABASES["default"]["OPTIONS"] = {"connect_timeout": 5} | DATABASES["default"].get("OPTIONS", {})

# --- Cache ----------------------------------------------------------------------------

TRIP_CACHE_SECONDS = 24 * 60 * 60

# Part of every cache key (the cache's VERSION). A cached value can outlive the code that
# made it, in Redis, so raise this by hand whenever the shape of a cached value or a
# planning rule changes: entries made under the old number are then never read.
CACHE_KEY_VERSION = 2

# With REDIS_URL set, the two caches and the rate-limit counters are in Redis, shared by
# every worker, with each process's own memory as the fallback (config/cache.py). Without
# it they are in the process's own memory, as in release 1.0 (D-15).
REDIS_URL = _text("REDIS_URL", "")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "config.cache.RedisWithFallback",
            "LOCATION": REDIS_URL,
            "TIMEOUT": TRIP_CACHE_SECONDS,
            "VERSION": CACHE_KEY_VERSION,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "TIMEOUT": TRIP_CACHE_SECONDS,
            "VERSION": CACHE_KEY_VERSION,
            "OPTIONS": {"MAX_ENTRIES": 500},
        }
    }

# --- Django REST Framework -------------------------------------------------------------


def _num_proxies() -> int:
    """DJANGO_NUM_PROXIES, or 0. Anything but a whole number of 0 or more stops the start,
    naming the variable and the value: at -1 every request carrying X-Forwarded-For would
    answer 500 (Q1-07)."""
    value = _text("DJANGO_NUM_PROXIES", "0")
    if not value.isdecimal():
        raise ImproperlyConfigured(
            f"DJANGO_NUM_PROXIES must be a whole number of 0 or more, not {value!r}."
        )
    return int(value)


REST_FRAMEWORK = {
    # Every error, ours or the framework's, leaves through one handler in one shape.
    "EXCEPTION_HANDLER": "trips.errors.handler",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    # No accounts: these three lines are what let DRF run without django.contrib.auth.
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    # Per client. It keeps one caller from leaning on the free routing servers through
    # us; it does not limit all callers together. Ours, not the framework's AnonRateThrottle,
    # which loses count of requests sent at once (trips/throttling.py).
    "DEFAULT_THROTTLE_CLASSES": ["trips.throttling.FixedWindowThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min"},
    # How many proxies in front to trust when finding a client's address (D-17). At 0 a
    # client is its connection's address and X-Forwarded-For is ignored. Behind exactly
    # one proxy that overwrites the header, 1: the client is the address it wrote.
    "NUM_PROXIES": _num_proxies(),
    # Without a declaration the tool can guess nothing about a plain APIView (trips/schema.py).
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# --- The OpenAPI document and the Swagger page ------------------------------------------

SPECTACULAR_SETTINGS = {
    "TITLE": "Mile Marker API",
    "DESCRIPTION": (
        "Plans the fuel stops of a truck trip between two places in the lower 48 states and "
        "DC, and prices them from a table of listed station prices. The truck goes 500 miles "
        "on a full 50-gallon tank, at 10 miles per gallon, and leaves with an empty tank.\n\n"
        "**Addresses.** `GET /api/v1/route/` plans a trip. `GET /api/v1/health/` says whether "
        "the stations are loaded. `GET /api/v1/schema/` is this document, as YAML, or as JSON "
        "for `Accept: application/vnd.oai.openapi+json`. `GET /api/v1/docs/` is the page that "
        "shows it. The route, the schema and the docs share one limit of 60 requests a "
        "minute for each client; the 61st is answered `429 rate_limited` with a "
        "`Retry-After` header. Health is never limited.\n\n"
        "**Errors.** Every error, whatever raised it, has one body: "
        '`{"error": {"code": "...", "message": "...", "details": {...}}}`. The route lists '
        "the statuses it can answer with and the codes each carries. Two codes belong to "
        "every address and are not listed on the route. `not_found` (404): there is nothing "
        "at the address, whatever the method. `method_not_allowed` (405): the address exists "
        "and the method is not GET (HEAD and OPTIONS are left to the framework). Both have "
        "empty `details`.\n\n"
        "**Request ID.** Every answer carries an `X-Request-ID` header, the same ID the "
        "server writes on its log lines for the request. A request that arrives with an "
        "`X-Request-ID` keeps it if it is 1 to 64 characters of letters, digits, `.`, `_` "
        "and `-`; any other is replaced with one of the server's own.\n\n"
        "**Numbers.** Every number is a JSON number. Unknown query parameters are ignored."
    ),
    "VERSION": "2.0.0",
    # The document describes the API's trip and health addresses; the schema and docs
    # addresses are described in its opening text, not listed in it.
    "SERVE_INCLUDE_SCHEMA": False,
    # The default hook lifts every enum into a component of its own and then warns that the
    # fields called `kind`, `type` and `code` collide. Each enum stays where it is declared.
    "POSTPROCESSING_HOOKS": [],
    # One exact version, not the library's @latest: the page must not change under us.
    "SWAGGER_UI_DIST": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14",
    "SWAGGER_UI_FAVICON_HREF": "",
}

# --- Routing service -------------------------------------------------------------------


# Tried in order: the first is the OSRM public server, the second takes the one retry.
# They run the same software, but note that their paths differ.
# {coords} becomes "lng,lat;lng,lat" (longitude first, as OSRM expects).
# The environment variable ROUTING_SERVERS replaces both: one or two templates separated by
# commas, so the end-to-end run can point the API at a stand-in. Empty or blank counts as
# not set, because Compose passes the variable through even when nothing sets it.
def _routing_servers() -> list[str]:
    """The templates from ROUTING_SERVERS, or the two public servers if it is not set."""
    value = os.environ.get("ROUTING_SERVERS", "")
    if not value.strip():
        return [
            "https://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson",
            "https://routing.openstreetmap.de/routed-car/route/v1/driving/{coords}?overview=full&geometries=geojson",
        ]
    templates = [entry.strip() for entry in value.split(",") if entry.strip()]
    if not templates:
        raise ImproperlyConfigured(f"ROUTING_SERVERS has no entry in {value!r}.")
    # The client tries each server once, and a route may take two calls at most (NFR-2).
    if len(templates) > 2:
        raise ImproperlyConfigured(
            f"ROUTING_SERVERS has {len(templates)} entries; at most 2 are allowed."
        )
    for template in templates:
        if "{coords}" not in template:
            raise ImproperlyConfigured(f"ROUTING_SERVERS entry {template!r} has no {{coords}}.")
    return templates


ROUTING_SERVERS = _routing_servers()

# The time allowed for one attempt. The HTTP library times connecting and waiting for the
# answer separately, and our own clock is checked as the answer is read, so an attempt whose
# server is slow both to answer and to send can run to about twice this (architecture
# section 9).
ROUTING_DEADLINE_SECONDS = 5.0

# The second server's usage rules ask applications to identify themselves.
ROUTING_USER_AGENT = "milemarker-api"

# --- Trip planning ---------------------------------------------------------------------

# Charged per stop while the plan is chosen. Never added to the fuel bill.
DEFAULT_STOP_COST = Decimal("10")

# --- Data files ------------------------------------------------------------------------

DATA_DIR = BASE_DIR / "data"
STATIONS_CSV = DATA_DIR / "fuel-prices-for-be-assessment.csv"
CITIES_CSV = DATA_DIR / "us_cities.csv"
BORDERS_FILE = DATA_DIR / "borders.json"

# --- Logging ---------------------------------------------------------------------------


def _log_level() -> str:
    """LOG_LEVEL in capitals, or INFO. Any other name stops the start, naming the variable and
    the value, rather than leaving the logging library to refuse it without a word of where
    it came from (Q1-07). gunicorn.conf.py checks it in the same words."""
    value = _text("LOG_LEVEL", "INFO")
    if value.upper() not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ImproperlyConfigured(
            f"LOG_LEVEL must be one of DEBUG, INFO, WARNING, ERROR or CRITICAL, not {value!r}."
        )
    return value.upper()


# Plain lines, each with a time, a level and the ID of the request it was written for, or
# "-" outside a request (NFR-24). LOG_LEVEL is the lowest level written.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {"()": "config.logs.RequestIdFilter"},
        "failures_only": {"()": "config.logs.FailuresOnly"},
    },
    "formatters": {
        "plain": {"format": "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"}
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "plain",
            "filters": ["request_id"],
        }
    },
    "root": {"handlers": ["console"], "level": _log_level()},
    "loggers": {
        # Each answer is logged once, by the API itself: a trip line, or one WARNING line
        # with the error code (trips/errors.py). Django's own "Bad Request: /api/v1/route/"
        # would be a second line, so only its record of an unexpected failure, which
        # carries the traceback, is kept.
        "django.request": {"filters": ["failures_only"]},
    },
}
