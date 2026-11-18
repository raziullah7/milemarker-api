"""What the log lines carry: the ID of the request each was written for (NFR-24).

The settings' LOGGING names the two filters below. Django reads them while it is still
starting, before the apps are loaded, so this module imports nothing but the standard
library. trips/middleware.py sets the ID for the time a request is answered.
"""

import logging
from contextvars import ContextVar

# The ID of the request this thread is answering, or "-" outside a request. A context
# variable, so each of a worker's threads has its own.
request_id: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Gives every record a `request_id`, for the line format of the settings."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add the ID; never drop the record."""
        record.request_id = request_id.get()
        return True


class FailuresOnly(logging.Filter):
    """For Django's request logger: keep a failure, which Django logs with its traceback,
    and drop the line it writes for every other 4xx and 5xx answer, which the API has
    already logged in its own words."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Keep the record only if it carries an exception."""
        return record.exc_info is not None
