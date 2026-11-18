#!/bin/sh
# Stop at the first failing step: a failed migration or load must not leave a server running
# with no stations.
set -e

python manage.py migrate --noinput

# Replaces the stations table, so running it on every start is safe and never doubles the rows.
python manage.py load_stations

# One worker on purpose: the route cache, the throttle counters and the station index live in
# the process's memory, and a second worker would have its own copy of each.
# No --preload: the index is built from the database as the worker starts (config/wsgi.py),
# and that must happen inside the worker, not in the parent that forks it.
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1 --threads 4
