"""Checks on the project itself: versions, settings, layering, and the network block.

Test IDs (PJ-01 ...) refer to docs/test-cases.md.
"""

import ast
import fnmatch
import json
import os
import re
import socket
import subprocess
import sys
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

    # A module can still load Django through a module it imports, so import it in a
    # fresh interpreter, where nothing else has loaded Django, and see what came with it.
    name = module.removesuffix(".py").replace("/", ".")
    script = f"import sys, {name}; print(sorted({{'django', 'rest_framework'}} & set(sys.modules)))"
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "[]"


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


def test_host_checking_is_on():
    """Reversed on purpose (D-21, architecture section 13). Release 1.0 had a test here that
    forbade DJANGO_ALLOWED_HOSTS, because nothing then read the Host header. Now the
    setting comes from that variable, no host is allowed by a wildcard, and CF-04 below
    reads it in a process of its own."""
    assert "*" not in settings.ALLOWED_HOSTS
    for path in (ROOT / ".env.example", ROOT / "config" / "settings.py"):
        assert "DJANGO_ALLOWED_HOSTS" in path.read_text(encoding="utf-8"), path


def test_qb11_the_routing_deadline_comment_says_what_it_bounds():
    """Review 9-Q0b, note N4: the comment beside the setting says what architecture section 9
    says, that an attempt can run to about twice the deadline."""
    lines = (ROOT / "config" / "settings.py").read_text(encoding="utf-8").splitlines()
    at = next(n for n, line in enumerate(lines) if line.startswith("ROUTING_DEADLINE_SECONDS"))
    comment = []
    for line in reversed(lines[:at]):
        if not line.startswith("#"):
            break
        comment.insert(0, line)
    text = " ".join(comment)

    assert "twice" in text
    assert "last byte" not in text


def test_the_suite_runs_on_the_in_memory_cache():
    """CA-17 runs this in a pytest of its own with REDIS_URL set (tests/test_cache.py)."""
    from django.core.cache import caches

    assert type(caches["default"]).__name__ == "LocMemCache"


def test_pj05_database_url_selects_postgresql():
    parsed = dj_database_url.parse("postgres://u:p@db:5432/x")
    assert parsed["ENGINE"] == "django.db.backends.postgresql"
    assert (parsed["HOST"], parsed["PORT"], parsed["NAME"]) == ("db", 5432, "x")
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"


# --- Settings from the environment (docs/test-cases.md, section 9.2) ----------------------

# What a Python process needs to start, on this machine or in a container. Nothing else of
# the test runner's environment is passed on.
_START_VARIABLES = ("PATH", "SYSTEMROOT", "TEMP", "TMP")


def run_new_process(code: str, **variables: str) -> subprocess.CompletedProcess:
    """Run `code` in a fresh Python process in the project's folder with only the named
    variables set, so the test runner's own settings (it adds "testserver" to the allowed
    hosts) and the shell's never enter."""
    env = {name: os.environ[name] for name in _START_VARIABLES if name in os.environ}
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env | variables,
        capture_output=True,
        text=True,
        check=False,
    )


SETTINGS_SCRIPT = """
import json, config.settings as s
db = s.DATABASES["default"]
print(json.dumps({
    "SECRET_KEY": s.SECRET_KEY,
    "DEBUG": s.DEBUG,
    "ALLOWED_HOSTS": s.ALLOWED_HOSTS,
    "NUM_PROXIES": s.REST_FRAMEWORK["NUM_PROXIES"],
    "DATABASE": [db["ENGINE"], db["HOST"], db["PORT"], db["NAME"], db["USER"]],
    "CACHES": s.CACHES,
}))
"""


def settings_with(**variables: str) -> dict:
    """The settings config/settings.py makes with only `variables` set, read in a new process."""
    result = run_new_process(SETTINGS_SCRIPT, **variables)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_cf01_no_secret_key_set_makes_a_random_one():
    first, second = settings_with()["SECRET_KEY"], settings_with()["SECRET_KEY"]

    assert first
    assert second
    assert first != second
    # No key text is written in the code as a default (D-21): the line that reads the
    # variable holds no string but the variable's name.
    source = (ROOT / "config" / "settings.py").read_text(encoding="utf-8")
    [line] = [line for line in source.splitlines() if line.startswith("SECRET_KEY")]
    assert re.findall(r'"[^"]*"', line) == ['"DJANGO_SECRET_KEY"']


def test_cf02_secret_key_from_the_environment():
    key = "cf-02-0123456789-abcdefghijklmnopqrstuvwxyz-0123456789"

    assert settings_with(DJANGO_SECRET_KEY=key)["SECRET_KEY"] == key


def test_cf03_debug_is_off_unless_switched_on():
    assert settings_with()["DEBUG"] is False
    assert settings_with(DJANGO_DEBUG="1")["DEBUG"] is True


def test_cf04_allowed_hosts():
    unset = settings_with()["ALLOWED_HOSTS"]
    given = settings_with(DJANGO_ALLOWED_HOSTS="api.example,api2.example")["ALLOWED_HOSTS"]

    assert unset == ["localhost", "127.0.0.1", "[::1]"]
    assert given == ["api.example", "api2.example"]
    # Compose passes the variable through, so on a fresh clone it arrives empty.
    assert settings_with(DJANGO_ALLOWED_HOSTS="")["ALLOWED_HOSTS"] == unset


def test_cf05_proxies_trusted():
    assert settings_with()["NUM_PROXIES"] == 0
    assert settings_with(DJANGO_NUM_PROXIES="1")["NUM_PROXIES"] == 1
    assert settings_with(DJANGO_NUM_PROXIES="")["NUM_PROXIES"] == 0


def test_cf06_default_database():
    engine, host, port, name, user = settings_with()["DATABASE"]

    assert engine == "django.db.backends.postgresql"
    assert (host, port, name, user) == ("127.0.0.1", 5432, "milemarker", "milemarker")


def test_cf07_redis_url_selects_the_cache():
    """The other half of CF-07, health reporting each, is HS-01 and HS-03."""
    memory = settings_with()["CACHES"]["default"]
    redis = settings_with(REDIS_URL="redis://127.0.0.1:6379/15")["CACHES"]["default"]

    assert memory["BACKEND"] == "django.core.cache.backends.locmem.LocMemCache"
    assert settings_with(REDIS_URL="")["CACHES"]["default"] == memory
    assert redis["BACKEND"] == "config.cache.RedisWithFallback"
    assert redis["LOCATION"] == "redis://127.0.0.1:6379/15"
    for cache in (memory, redis):
        assert cache["TIMEOUT"] == 86_400
        assert cache["VERSION"] == settings.CACHE_KEY_VERSION


GUNICORN_SCRIPT = """
import json, runpy
c = runpy.run_path("gunicorn.conf.py")
names = ("workers", "threads", "worker_class", "preload_app", "graceful_timeout",
         "accesslog", "access_log_format")
print(json.dumps({name: c[name] for name in names}))
"""


def gunicorn_settings(**variables: str) -> dict:
    """The values gunicorn.conf.py sets, read in a new process with only `variables` set."""
    result = run_new_process(GUNICORN_SCRIPT, **variables)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_cf10_two_workers_of_four_threads_unless_web_concurrency_says_otherwise():
    default = gunicorn_settings()

    assert (default["workers"], default["threads"]) == (2, 4)
    assert default["worker_class"] == "gthread"
    assert gunicorn_settings(WEB_CONCURRENCY="3")["workers"] == 3
    # Architecture section 18: no preload (each worker loads its own stations), a stop
    # that waits 30 seconds, and an access log on standard output with the request ID.
    assert default["preload_app"] is False
    assert default["graceful_timeout"] == 30
    assert default["accesslog"] == "-"
    assert "%({x-request-id}o)s" in default["access_log_format"]


LOG_SCRIPT = """
import django, logging
django.setup()
logging.getLogger("trips").info("an info line")
logging.getLogger("trips").warning("a warning line")
"""


def test_cf11_log_level():
    variables = {"DJANGO_SETTINGS_MODULE": "config.settings"}
    unset = run_new_process(LOG_SCRIPT, **variables).stderr
    warning = run_new_process(LOG_SCRIPT, LOG_LEVEL="WARNING", **variables).stderr

    assert "an info line" in unset
    assert "a warning line" in unset
    assert "an info line" not in warning
    assert "a warning line" in warning
    # Each line has a time, a level and the request's ID, "-" outside a request.
    line = r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3} WARNING \[-\] trips: a warning line$"
    assert re.search(line, warning, re.MULTILINE)


CHECK_SCRIPT = """
from django.core.management import execute_from_command_line
execute_from_command_line(["manage.py", "check", "--deploy", "--fail-level", "WARNING"])
"""


def test_cf12_deployment_check_passes():
    result = run_new_process(CHECK_SCRIPT, DJANGO_SETTINGS_MODULE="config.settings")

    assert result.returncode == 0, result.stderr
    assert "System check identified no issues" in result.stdout
    # TLS, HSTS and the redirect to HTTPS belong to the TLS terminator in front (D-23).
    assert settings.SECURE_HSTS_SECONDS == 0
    assert settings.SECURE_SSL_REDIRECT is False
    # Every check switched off has its reason beside it.
    source = (ROOT / "config" / "settings.py").read_text(encoding="utf-8")
    listed = source.split("SILENCED_SYSTEM_CHECKS = [", 1)[1].split("]", 1)[0]
    entries = [line.strip() for line in listed.splitlines() if line.strip().startswith('"')]
    assert len(entries) == len(settings.SILENCED_SYSTEM_CHECKS) > 0
    for entry in entries:
        assert re.fullmatch(r'"[\w.]+",\s+#\s+\S.*', entry), f"no reason beside {entry}"


# Who reads each variable: the API (Django or gunicorn) or Compose alone.
ALL_VARIABLES = {
    "DJANGO_SECRET_KEY": "the API",
    "DJANGO_DEBUG": "the API",
    "DJANGO_ALLOWED_HOSTS": "the API",
    "DJANGO_NUM_PROXIES": "the API",
    "DATABASE_URL": "the API",
    "REDIS_URL": "the API",
    "ROUTING_SERVERS": "the API",
    "WEB_CONCURRENCY": "the API",
    "LOG_LEVEL": "the API",
    "API_PORT": "Compose",
    "POSTGRES_PORT": "Compose",
    "REDIS_PORT": "Compose",
    "BIND_ADDRESS": "Compose",
}


def test_cf16_env_example_names_every_variable_and_who_reads_it():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    blocks = text.split("\n\n")

    for name, reader in ALL_VARIABLES.items():
        [block] = [b for b in blocks if re.search(rf"^{name}=", b, re.MULTILINE)]
        assert f"Read by {reader}" in block, name
    # No key or token: the secret key's line is left empty.
    assert re.search(r"^DJANGO_SECRET_KEY=$", text, re.MULTILINE)


def ignored_by(ignore_file: str, name: str) -> bool:
    """Whether a file `name` in the project's root is ignored by `ignore_file`, read as git
    and Docker read these simple patterns: the last pattern that matches decides, and a
    pattern starting with ! takes the file back."""
    ignored = False
    for line in (ROOT / ignore_file).read_text(encoding="utf-8").splitlines():
        pattern = line.strip()
        if not pattern or pattern.startswith("#"):
            continue
        if fnmatch.fnmatchcase(name, pattern.removeprefix("!").rstrip("/")):
            ignored = not pattern.startswith("!")
    return ignored


@pytest.mark.parametrize("ignore_file", [".gitignore", ".dockerignore"])
def test_cf17_env_files_are_ignored_but_the_example(ignore_file):
    for name in (".env", ".env.local", ".env.production"):
        assert ignored_by(ignore_file, name), name
    assert not ignored_by(ignore_file, ".env.example")
