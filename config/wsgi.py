"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()

# Load the places table, the border outlines, the views (with scipy) and the station index
# now, so the first request does not wait about 1.3 s for them and its timings are like any
# other's. Only a server goes through this file (gunicorn, or manage.py runserver). Other
# manage.py commands, such as migrate and load_stations, and the tests do not, so they never
# try to read stations at start-up. Imported here, not at the top: it needs Django set up.
from trips.services.planner import warm_up  # noqa: E402

warm_up()
