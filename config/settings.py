"""Settings for the Mile Marker API.

One file on purpose: the project needs three environment variables, and each has a default
that works with the Compose file, so a fresh clone runs with no configuration at all.

The service has no users, sessions, templates or admin site. That is why the app and
middleware lists are nearly empty: Django REST Framework runs without the auth apps when
it is told there is no user (see REST_FRAMEWORK below).
"""

import os
from decimal import Decimal
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


def _flag(name: str, default: bool) -> bool:
    """Read an on/off environment variable ("1", "true", "yes", "on" mean on)."""
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


# --- Django ---------------------------------------------------------------------------

# Nothing in this service signs or encrypts anything (no sessions, no cookies, no tokens),
# so the default below is safe for local use. A real deployment sets its own.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "local-development-key-not-a-secret")

DEBUG = _flag("DJANGO_DEBUG", False)

# Any host. With no middleware nothing checks the Host header anyway, and nothing needs it
# to: the API never builds an absolute address from it, and has no cookies or sessions.
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "rest_framework",
    "stations",
    "trips",
]

# No middleware. In particular no CommonMiddleware: it would answer a missing trailing
# slash with a redirect, which is awkward for API clients. The route accepts both forms.
MIDDLEWARE: list[str] = []

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

USE_TZ = True
TIME_ZONE = "UTC"

# --- Database -------------------------------------------------------------------------

# PostgreSQL, from one DATABASE_URL. The default matches docker-compose.yml, so
# "docker compose up -d db" followed by "manage.py migrate" works with nothing set.
DATABASES = {
    "default": dj_database_url.config(
        default="postgresql://milemarker:milemarker@localhost:5432/milemarker",
        conn_max_age=60,
        conn_health_checks=True,
    )
}

# --- Cache ----------------------------------------------------------------------------

TRIP_CACHE_SECONDS = 24 * 60 * 60

# In memory, inside this process. The API runs as one process with threads, so every
# request shares it. Several processes would need a shared cache instead.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "TIMEOUT": TRIP_CACHE_SECONDS,
        "OPTIONS": {"MAX_ENTRIES": 500},
    }
}

# --- Django REST Framework -------------------------------------------------------------

REST_FRAMEWORK = {
    # Every error, ours or the framework's, leaves through one handler in one shape.
    "EXCEPTION_HANDLER": "trips.errors.handler",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    # No accounts: these three lines are what let DRF run without django.contrib.auth.
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    # Per client. It keeps one caller from leaning on the free routing servers through
    # us; it does not limit all callers together.
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min"},
    # No proxy in front: a client is its connection's address, never X-Forwarded-For.
    "NUM_PROXIES": 0,
}

# --- Routing service -------------------------------------------------------------------

# Tried in order: the first is the OSRM public server, the second takes the one retry.
# They run the same software, but note that their paths differ.
# {coords} becomes "lng,lat;lng,lat" (longitude first, as OSRM expects).
ROUTING_SERVERS = [
    "https://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson",
    "https://routing.openstreetmap.de/routed-car/route/v1/driving/{coords}?overview=full&geometries=geojson",
]

# Total time allowed for one attempt, from sending the request to reading the last byte.
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

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
