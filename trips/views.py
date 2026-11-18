"""The API layer: read the request, call plan_trip(), return JSON. No rules live here."""

from django.http import HttpRequest, JsonResponse
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.parsers import BaseParser
from rest_framework.renderers import BaseRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from trips.errors import INTERNAL_ERROR, NOT_FOUND, json_error
from trips.serializers import RouteQuery
from trips.services.planner import plan_trip


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
        return Response(plan_trip(params["start"], params["finish"], params["stop_cost"]))


def not_found(request: HttpRequest) -> JsonResponse:
    """Every address the API does not have, whatever the method or DEBUG."""
    return json_error("not_found", NOT_FOUND)


def server_error(request: HttpRequest) -> JsonResponse:
    """Django's handler500: a failure outside the REST framework, when DEBUG is off."""
    return json_error("internal_error", INTERNAL_ERROR)
