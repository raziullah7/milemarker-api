"""Turn every error into one response shape:

    {"error": {"code": "...", "message": "...", "details": {...}}}

This is the only place that knows which HTTP status a code maps to.
"""

import logging

from django.http import Http404, JsonResponse
from rest_framework.exceptions import MethodNotAllowed, NotFound, Throttled, ValidationError
from rest_framework.response import Response

from stations.exceptions import MileMarkerError

logger = logging.getLogger(__name__)

# The error table of the architecture document, section 11.
STATUS_FOR_CODE = {
    "invalid_request": 400,
    "unknown_place": 400,
    "not_found": 404,
    "method_not_allowed": 405,
    "outside_coverage": 422,
    "route_leaves_usa": 422,
    "no_route": 422,
    "no_fuel_plan": 422,
    "rate_limited": 429,
    "internal_error": 500,
    "routing_unavailable": 502,
    "stations_not_loaded": 503,
}

NOT_FOUND = "There is nothing at this address. Try GET /api/v1/route/?start=...&finish=..."
INTERNAL_ERROR = "Something went wrong on our side. Please try again later."


def error_body(code: str, message: str, details: dict | None = None) -> dict:
    """The one error shape. `details` holds the keys the code's row lists, or nothing."""
    return {"error": {"code": code, "message": message, "details": details or {}}}


def handler(exc: Exception, context: dict) -> Response:
    """The Django REST Framework exception handler named in settings.

    It answers every exception, so an unexpected failure is JSON whatever DEBUG is.
    """
    if isinstance(exc, MileMarkerError):
        return _response(exc.code, exc.message, exc.details)

    if isinstance(exc, ValidationError):
        # The serializer's errors: {parameter: [message, ...]}.
        fields = {name: [str(m) for m in messages] for name, messages in exc.detail.items()}
        message = "These parameters are missing or not valid: " + ", ".join(fields) + "."
        return _response("invalid_request", message, {"fields": fields})

    if isinstance(exc, Throttled):
        # The framework has already rounded the wait up to whole seconds.
        seconds = exc.wait
        return _response(
            "rate_limited",
            f"Too many requests. Try again in {seconds} seconds.",
            {"retry_after_seconds": seconds},
            headers={"Retry-After": str(seconds)},
        )

    if isinstance(exc, MethodNotAllowed):
        return _response("method_not_allowed", "Only GET is allowed at this address.")

    if isinstance(exc, NotFound | Http404):
        return _response("not_found", NOT_FOUND)

    logger.exception("Unexpected failure while answering a request", exc_info=exc)
    return _response("internal_error", INTERNAL_ERROR)


def json_error(code: str, message: str) -> JsonResponse:
    """The standard body as a plain Django response, for views outside the REST framework."""
    return JsonResponse(error_body(code, message), status=STATUS_FOR_CODE[code])


def _response(
    code: str, message: str, details: dict | None = None, headers: dict | None = None
) -> Response:
    """The standard body in a REST framework response, with the status its code maps to."""
    return Response(
        error_body(code, message, details), status=STATUS_FOR_CODE[code], headers=headers
    )
