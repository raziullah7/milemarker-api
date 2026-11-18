"""Checks on the project itself: versions, settings, layering, and the network block.

Test IDs (PJ-01 ...) refer to docs/test-cases.md.
"""

import ast
import socket
from pathlib import Path

import dj_database_url
import django
import pytest
from django.conf import settings
from django.db import connection
from pytest_socket import SocketConnectBlockedError

ROOT = Path(__file__).resolve().parent.parent

# Modules that hold the rules. They must stay free of Django so they can be tested,
# and understood, on their own.
PURE_MODULES = [
    "trips/services/fuel.py",
    "trips/services/geo.py",
    "trips/services/corridor.py",
    "trips/services/answer.py",
    "stations/types.py",
    "stations/sphere.py",
]


def test_pj01_django_is_a_6_1_release():
    major, minor, patch = (int(part) for part in django.get_version().split(".")[:3])
    assert (major, minor) == (6, 1)
    assert patch >= 3


@pytest.mark.parametrize("module", PURE_MODULES)
def test_pj02_pure_modules_do_not_import_django(module):
    tree = ast.parse((ROOT / module).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported & {"django", "rest_framework"}


@pytest.mark.django_db
@pytest.mark.filterwarnings("ignore:A test tried to use socket")
def test_pj03_outside_connections_are_blocked_but_the_database_works():
    # 192.0.2.1 is reserved for documentation, so nothing real is ever contacted:
    # the block raises before any packet leaves.
    with pytest.raises(SocketConnectBlockedError):
        socket.create_connection(("192.0.2.1", 80), timeout=1)

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        assert cursor.fetchone() == (1,)


def test_pj04_settings_hold_the_values_the_specs_fix():
    first, second = settings.ROUTING_SERVERS
    assert first.startswith("https://router.project-osrm.org/route/v1/driving/")
    assert second.startswith("https://routing.openstreetmap.de/routed-car/route/v1/driving/")
    for template in (first, second):
        assert "{coords}" in template
        assert template.endswith("?overview=full&geometries=geojson")

    assert settings.ROUTING_DEADLINE_SECONDS == 5
    assert settings.ROUTING_USER_AGENT
    assert settings.DEFAULT_STOP_COST == 10
    assert settings.TRIP_CACHE_SECONDS == 86_400
    assert settings.CACHES["default"]["TIMEOUT"] == 86_400
    assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["anon"] == "60/min"


def test_pj05_database_url_selects_postgresql():
    parsed = dj_database_url.parse("postgres://u:p@db:5432/x")
    assert parsed["ENGINE"] == "django.db.backends.postgresql"
    assert (parsed["HOST"], parsed["PORT"], parsed["NAME"]) == ("db", 5432, "x")
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"
