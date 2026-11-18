"""The API layer: read the request, call one business function, return JSON. No rules live here."""

import logging

from django.core.exceptions import DisallowedHost
from django.http import HttpRequest, JsonResponse
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.parsers import BaseParser
from rest_framework.renderers import BaseRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from trips.errors import HOST_NOT_ALLOWED, INTERNAL_ERROR, MALFORMED_REQUEST, NOT_FOUND, json_error
from trips.serializers import RouteQuery
from trips.services.planner import health, plan_trip

# The one line per planned trip is written to this logger, by name (architecture section 18).
trip_log = logging.getLogger("trips")


class AlwaysJSON(BaseContentNegotiation):
    """Answer in JSON whatever the Accept header asks for. JSON is the API's only format,
    and refusing a request over its Accept header is not in the API's error table."""

    def select_parser(self, request: Request, parsers: list[BaseParser]) -> BaseParser:
        """The first parser. A GET has no body, so none is ever used."""
        return parsers[0]

    def select_renderer(
        self, request: Request, renderers: list[BaseRenderer], format_suffix: str | None = None
    ) -> tuple[BaseRenderer, str]:
        """The first renderer, which settings make the only one: JSON."""
        return renderers[0], renderers[0].media_type


class RouteView(APIView):
    """GET /api/v1/route/?start=...&finish=...[&stop_cost=...]"""

    # Set here, not as DEFAULT_CONTENT_NEGOTIATION_CLASS in settings: the framework reads
    # that setting while this module is still being imported, a circular import.
    content_negotiation_class = AlwaysJSON

    def get(self, request: Request) -> Response:
        """Check the parameters, plan the trip, answer with the plan."""
        # A plain dict, not the QueryDict: given a QueryDict, the framework reads an empty
        # optional parameter as absent, so "stop_cost=" would quietly become the default.
        query = RouteQuery(data=request.query_params.dict())
        query.is_valid(raise_exception=True)
        params = query.validated_data
        body = plan_trip(params["start"], params["finish"], params["stop_cost"])
        _log_trip(body)
        return Response(body)


class HealthView(APIView):
    """GET /api/v1/health/: the stations loaded in this worker, and where its cache is."""

    content_negotiation_class = AlwaysJSON
    # The one address that is never rate limited (FR-20).
    throttle_classes = ()

    def get(self, request: Request) -> Response:
        """200 with the count and the cache's state, or 503 stations_not_loaded."""
        return Response(health())


def _log_trip(body: dict) -> None:
    """One line at INFO for every 200 of the route, cache hits included, in the form
    architecture section 18 gives. The labels are the places table's own spelling, never
    the text the client sent."""
    summary, meta = body["summary"], body["meta"]
    trip_log.info(
        'trip start="%s" finish="%s" stop_cost=%s miles=%s stops=%s total=%s '
        "routing_calls=%s cache_hit=%s own_ms=%s",
        summary["start"]["label"],
        summary["finish"]["label"],
        f"{body['assumptions']['stop_cost']:g}",
        summary["distance_miles"],
        summary["stops"],
        summary["total_fuel_cost"],
        meta["routing_calls"],
        "true" if meta["cache_hit"] else "false",
        meta["timings_ms"]["own"],
    )


def not_found(request: HttpRequest) -> JsonResponse:
    """Every address the API does not have, whatever the method or DEBUG."""
    return json_error("not_found", NOT_FOUND)


def bad_request(request: HttpRequest, exception: Exception) -> JsonResponse:
    """Django's handler400, and the answer to a host that is not allowed: 400
    invalid_request with empty details (D-21)."""
    message = HOST_NOT_ALLOWED if isinstance(exception, DisallowedHost) else MALFORMED_REQUEST
    return json_error("invalid_request", message)


def server_error(request: HttpRequest) -> JsonResponse:
    """Django's handler500: a failure outside the REST framework, when DEBUG is off."""
    return json_error("internal_error", INTERNAL_ERROR)
