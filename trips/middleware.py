"""What every request passes through before it reaches a view (settings.MIDDLEWARE).

RequestIdMiddleware gives each request an ID for its log lines and its answer.
AllowedHostsMiddleware refuses a host that is not allowed, in the API's own error shape.
"""

import re
import uuid
from collections.abc import Callable

from django.core.exceptions import DisallowedHost
from django.http import HttpRequest, HttpResponse

from config.logs import request_id
from trips.views import bad_request

# A request ID that may be written into the log: 1 to 64 letters, digits, ".", "_" and "-".
# nginx's own, 32 hexadecimal characters, pass.
GOOD_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")


class RequestIdMiddleware:
    """The request's ID: the X-Request-ID it came with, which nginx sets, or a new one when
    none came, as when the API is run from source. It is on every log line written while
    the request is answered (config/logs.py) and in the answer's X-Request-ID header.

    The API can be reached with no nginx in front, so an ID that came is used only if it
    has the form of GOOD_REQUEST_ID; any other is replaced, as if none had come.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Answer the request with its ID set, then put the ID on the answer."""
        given = request.headers.get("X-Request-ID", "")
        good = GOOD_REQUEST_ID.fullmatch(given) is not None
        token = request_id.set(given if good else uuid.uuid4().hex)
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = request_id.get()
        finally:
            request_id.reset(token)
        return response


class AllowedHostsMiddleware:
    """A request whose Host is not in ALLOWED_HOSTS gets 400 invalid_request with empty
    details (D-21), as JSON whatever DEBUG is.

    CommonMiddleware checks the host too, but a host it refuses goes to Django's handler400
    only when DEBUG is off; with DEBUG on Django answers with its HTML debug page. Checking
    first, here, keeps every answer in the API's shape."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Refuse a host that is not allowed; pass every other request on."""
        try:
            request.get_host()
        except DisallowedHost as error:
            return bad_request(request, error)
        return self.get_response(request)
