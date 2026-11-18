# ruff: noqa: E501
"""What the API says about itself: the declarations behind the OpenAPI document.

The route's view is a plain APIView, so the documentation tool can guess nothing from it.
Everything it reports is declared here: the three query parameters, the 200 body, the error
bodies, the health address, and a real example of each. The views carry these declarations as
decorators (trips/views.py); the facts come from the code they describe (architecture
section 11) and the tests hold the document to it (tests/test_schema.py).

The serializers below are only descriptions. Nothing is ever built or validated with them.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    PolymorphicProxySerializer,
    extend_schema,
    extend_schema_field,
)
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework import serializers
from rest_framework.exceptions import NotAcceptable
from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework.renderers import JSONRenderer

# --- The two documentation addresses ------------------------------------------------------


class _AnswersInJSON:
    """What the schema and docs views add to the library's, so they answer as every address
    does: an error is the standard JSON body, and an Accept header never causes one."""

    class Negotiation(DefaultContentNegotiation):
        """The best match for the Accept header; the first renderer when there is none, not
        a 406, which is not in the API's error table."""

        def select_renderer(self, request, renderers, format_suffix=None):
            try:
                return super().select_renderer(request, renderers, format_suffix)
            except NotAcceptable:
                return renderers[0], renderers[0].media_type

    content_negotiation_class = Negotiation

    def finalize_response(self, request, response, *args, **kwargs):
        """The page renders HTML and the document YAML; an error answer is JSON for both."""
        response = super().finalize_response(request, response, *args, **kwargs)
        if getattr(response, "exception", False):
            response.accepted_renderer = JSONRenderer()
            response.accepted_media_type = "application/json"
        return response


class SchemaView(_AnswersInJSON, SpectacularAPIView):
    """GET /api/v1/schema/: the OpenAPI document."""


class DocsView(_AnswersInJSON, SpectacularSwaggerView):
    """GET /api/v1/docs/: the Swagger page."""


# --- Small helpers -----------------------------------------------------------------------


def _only(*values: str, help_text: str, required: bool = True) -> serializers.Field:
    """A text field that takes exactly these values, written in the document as an inline
    enum. (ChoiceField makes a named component for each set, and the tool then warns that
    fields called `kind`, `type` or `code` collide.)"""
    field = type("OnlyField", (serializers.CharField,), {})
    extend_schema_field({"type": "string", "enum": list(values)})(field)
    return field(help_text=help_text, required=required)


def _number(help_text: str) -> serializers.FloatField:
    return serializers.FloatField(help_text=help_text)


# --- The 200 body --------------------------------------------------------------------------


class PlaceSerializer(serializers.Serializer):
    label = serializers.CharField(help_text="The place as the places table spells it.")
    lat = _number("Latitude, 5 decimals.")
    lng = _number("Longitude, 5 decimals.")


class SummarySerializer(serializers.Serializer):
    start = PlaceSerializer(help_text="The start place, as found.")
    finish = PlaceSerializer(help_text="The finish place, as found.")
    distance_miles = _number("Length of the road, in miles, 1 decimal.")
    gallons = _number("Gallons bought in all: the distance divided by 10, 2 decimals.")
    total_fuel_cost = _number(
        "Dollars paid for the fuel, 2 decimals: the sum of the stops' costs. The stop cost is "
        "never part of it."
    )
    stops = serializers.IntegerField(
        help_text="Number of fuel stops, the start's fill-up included."
    )
    lowest_possible_fuel_cost = _number(
        "Dollars the fuel would cost if stops were free (stop_cost 0). Never more than "
        "total_fuel_cost."
    )
    lowest_possible_stops = serializers.IntegerField(
        help_text="Number of stops of that free-stops plan, counted as `stops` is."
    )
    first_fill_distance_miles = _number(
        "Miles from the start place to the listed station where the first fill-up is priced."
    )


class AssumptionsSerializer(serializers.Serializer):
    range_miles = serializers.IntegerField(help_text="Miles a full tank travels.")
    miles_per_gallon = serializers.IntegerField(help_text="Miles the truck travels on a gallon.")
    tank_gallons = serializers.IntegerField(help_text="What a full tank holds, in gallons.")
    starting_fuel_gallons = serializers.IntegerField(
        help_text="Fuel in the tank when the trip starts: always 0, so the first fill-up is at the start."
    )
    stop_cost = _number(
        "The cost in dollars charged per stop while the plan was chosen: the request's "
        "stop_cost, or 10."
    )
    search_radius_miles = serializers.IntegerField(
        help_text="How many miles either side of the road stations are searched for."
    )


class FuelStopSerializer(serializers.Serializer):
    order = serializers.IntegerField(help_text="Position in the trip, from 1.")
    kind = _only(
        "start",
        "station",
        help_text=(
            "`start` for stop 1, the fuel bought before leaving, priced at the listed station "
            "nearest the start. `station` for every other stop."
        ),
    )
    station_id = serializers.IntegerField(help_text="The station's OPIS ID in the price table.")
    name = serializers.CharField(help_text="The station's name.")
    address = serializers.CharField(help_text="The station's address.")
    city = serializers.CharField(help_text="The station's city.")
    state = serializers.CharField(help_text="The station's state, two letters.")
    mile_marker = _number("Miles from the start along the road, 1 decimal. 0 for stop 1.")
    lat = _number(
        "Latitude, 5 decimals. For stop 1 the start place's; for every other stop the point "
        "where the road passes the station's city, so it sits on the route line."
    )
    lng = _number("Longitude, 5 decimals, placed as `lat` is.")
    price_per_gallon = _number("Dollars per gallon, every digit the price table has.")
    gallons = _number("Gallons bought here, 2 decimals.")
    cost = _number("Dollars paid here: gallons times price, rounded to the cent.")


class _Point(serializers.Serializer):
    type = _only("Point", help_text="GeoJSON geometry type.")
    coordinates = serializers.ListField(
        child=serializers.FloatField(),
        min_length=2,
        max_length=2,
        help_text="[longitude, latitude], 5 decimals.",
    )


class _LineString(serializers.Serializer):
    type = _only("LineString", help_text="GeoJSON geometry type.")
    coordinates = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField(), min_length=2, max_length=2),
        help_text="The road as [longitude, latitude] points, 5 decimals, in driving order.",
    )


class RouteProperties(serializers.Serializer):
    kind = _only("route", help_text="This feature is the route line.")
    distance_miles = _number("Length of the road, in miles: the summary's.")


class StopProperties(serializers.Serializer):
    kind = _only("stop", help_text="This feature is a fuel stop.")
    order = serializers.IntegerField(help_text="The stop's order, as in fuel_stops.")
    title = serializers.CharField(
        help_text="A label such as `2. SHEETZ #639, Youngstown OH`, which geojson.io shows."
    )
    name = serializers.CharField(help_text="The station's name.")
    mile_marker = _number("The stop's mile_marker.")
    price_per_gallon = _number("The stop's price_per_gallon.")
    gallons = _number("The stop's gallons.")
    cost = _number("The stop's cost.")
    locals()["marker-color"] = serializers.CharField(
        help_text="The marker's colour as a hex code, which geojson.io draws."
    )


class EndpointProperties(serializers.Serializer):
    kind = _only("start", "finish", help_text="Whether this feature is the start or the finish.")
    title = serializers.CharField(help_text="A label such as `Start: Chicago, IL`.")
    locals()["marker-color"] = serializers.CharField(
        help_text="The marker's colour as a hex code, which geojson.io draws."
    )


class RouteFeature(serializers.Serializer):
    type = _only("Feature", help_text="GeoJSON type.")
    properties = RouteProperties(help_text="The route line's properties.")
    geometry = _LineString(help_text="The road.")


class StopFeature(serializers.Serializer):
    type = _only("Feature", help_text="GeoJSON type.")
    properties = StopProperties(help_text="The stop's properties.")
    geometry = _Point(help_text="Where the stop is drawn: the stop's lat and lng.")


class EndpointFeature(serializers.Serializer):
    type = _only("Feature", help_text="GeoJSON type.")
    properties = EndpointProperties(help_text="The place's properties.")
    geometry = _Point(help_text="The place's position.")


_FEATURE = PolymorphicProxySerializer(
    component_name="MapFeature",
    serializers=[RouteFeature, StopFeature, EndpointFeature],
    resource_type_field_name=None,
    many=True,
)


class MapSerializer(serializers.Serializer):
    type = _only("FeatureCollection", help_text="GeoJSON type.")

    @extend_schema_field(_FEATURE)
    class _Features(serializers.Field):
        pass

    features = _Features(
        help_text=(
            "In order: the route line, one point for each stop, the start, the finish. "
            "Ready to paste into geojson.io."
        )
    )


class TimingsSerializer(serializers.Serializer):
    routing = _number("Milliseconds spent in the call to the routing service; 0 with no call.")
    own = _number("Milliseconds of this API's own work, up to handing the answer to the framework.")
    total = _number("Milliseconds in all: routing plus own.")


class MetaSerializer(serializers.Serializer):
    routing_calls = serializers.IntegerField(
        help_text="Requests made to routing servers for this answer: 0 from the cache, else 1 or 2."
    )
    cache_hit = serializers.BooleanField(
        help_text="Whether the finished answer came from the cache."
    )
    routing_server = serializers.CharField(
        help_text="Host name of the routing server that supplied the road, now or when it was cached."
    )
    timings_ms = TimingsSerializer(help_text="Where the time went, for this request.")


class RouteAnswerSerializer(serializers.Serializer):
    summary = SummarySerializer(help_text="The trip in a few figures.")
    warnings = serializers.ListField(
        child=serializers.CharField(),
        help_text=(
            "Plain sentences. One is added when the station of the first fill-up is more than "
            "25 miles from the start."
        ),
    )
    assumptions = AssumptionsSerializer(help_text="What the plan was made with.")
    fuel_stops = FuelStopSerializer(many=True, help_text="The plan, in driving order.")
    map = MapSerializer(help_text="The route and its stops as a GeoJSON FeatureCollection.")
    meta = MetaSerializer(help_text="How this answer was made. Not cached: built for every answer.")


class HealthSerializer(serializers.Serializer):
    status = _only(
        "ok", help_text="Always ok: when the stations are not loaded the answer is a 503."
    )
    stations = serializers.IntegerField(
        help_text="Stations in the index of the worker that answered."
    )
    cache = _only(
        "redis",
        "fallback",
        "memory",
        help_text=(
            "The cache of the worker that answered. `memory`: no REDIS_URL is set, so it is "
            "the worker's own memory. `redis`: it is using Redis. `fallback`: REDIS_URL is "
            "set, but Redis could not be reached, so for 30 seconds the worker uses its own "
            "memory."
        ),
    )


# --- The error bodies --------------------------------------------------------------------


@extend_schema_field({"type": "object", "maxProperties": 0})
class NoDetails(serializers.DictField):
    """`details` for the codes that carry nothing: always `{}`."""


def _error_body(status: str, codes: dict[str, str], details: type[serializers.Field]):
    """The standard error body, for the codes a status can carry."""
    content = type(
        f"Error{status}Content",
        (serializers.Serializer,),
        {
            "code": _only(
                *codes,
                help_text="\n".join(f"`{code}`: {meaning}" for code, meaning in codes.items()),
            ),
            "message": serializers.CharField(help_text="One plain sentence for a person."),
            "details": details(
                help_text=(
                    "Always empty."
                    if details is NoDetails
                    else "Extra facts, whose keys depend on the code; each key names its code."
                )
            ),
        },
    )
    return type(
        f"Error{status}",
        (serializers.Serializer,),
        {"error": content(help_text="The error.")},
    )


class Error400Details(serializers.Serializer):
    fields = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        required=False,
        help_text=(
            "`invalid_request`: the messages for each parameter. May be empty, or absent, when "
            "the request was refused as a whole (a host that is not allowed, a request that "
            "could not be read)."
        ),
    )
    field = _only(
        "start",
        "finish",
        help_text="`unknown_place`: the parameter whose place was not found.",
        required=False,
    )
    query = serializers.CharField(
        required=False, help_text="`unknown_place`: the text as it was sent."
    )
    suggestions = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="`unknown_place`: up to 5 places such as `Chicago, IL`, possibly none.",
    )


class Error422Details(serializers.Serializer):
    field = _only(
        "start",
        "finish",
        help_text="`outside_coverage`: the parameter whose place is outside the area.",
        required=False,
    )
    query = serializers.CharField(
        required=False, help_text="`outside_coverage`: the text as it was sent."
    )
    miles_abroad = serializers.FloatField(
        required=False,
        help_text="`route_leaves_usa`: miles of the longest unbroken stretch outside the USA, 1 decimal.",
    )
    gap_start_mile = serializers.FloatField(
        required=False,
        help_text="`no_fuel_plan`: the mile marker where the stretch without a station begins, 1 decimal.",
    )
    gap_miles = serializers.FloatField(
        required=False,
        help_text="`no_fuel_plan`: the length of that stretch in miles, 1 decimal.",
    )


class Error429Details(serializers.Serializer):
    retry_after_seconds = serializers.IntegerField(
        help_text="Whole seconds to wait: the same as the Retry-After header."
    )


class Error502Details(serializers.Serializer):
    reason = _only(
        "timeout",
        "error",
        help_text="`timeout` when every attempt timed out, `error` otherwise.",
    )


Error400 = _error_body(
    "400",
    {
        "invalid_request": (
            "a parameter is missing, empty or malformed, or start and finish are the same "
            "place. Also a host the API does not answer to, and a request that could not be read"
        ),
        "unknown_place": "a place is not in the table",
    },
    Error400Details,
)
Error422 = _error_body(
    "422",
    {
        "outside_coverage": "a place in Alaska, Hawaii, Puerto Rico, Canada or Mexico",
        "route_leaves_usa": "the road runs through Canada or Mexico for more than 25 miles in a row",
        "no_route": "the routing service finds no road between the points",
        "no_fuel_plan": "a stretch of more than 500 miles has no station listed",
    },
    Error422Details,
)
Error429 = _error_body(
    "429", {"rate_limited": "too many requests from one client"}, Error429Details
)
Error500 = _error_body(
    "500", {"internal_error": "anything unexpected; no detail is given"}, NoDetails
)
Error502 = _error_body(
    "502",
    {"routing_unavailable": "both routing servers failed or timed out"},
    Error502Details,
)
Error503 = _error_body(
    "503",
    {
        "stations_not_loaded": "the station table is empty: `load_stations` has not been run",
        "api_unavailable": (
            "sent by the proxy, not by the API, when the API cannot be reached or does not "
            "answer within 30 seconds"
        ),
    },
    NoDetails,
)
HealthError503 = _error_body(
    "503Health",
    {"stations_not_loaded": "the station table is empty: `load_stations` has not been run"},
    NoDetails,
)


# --- Examples ----------------------------------------------------------------------------


def _error(code: str, message: str, details: dict, status: int, name: str, summary: str):
    return OpenApiExample(
        name,
        summary=summary,
        value={"error": {"code": code, "message": message, "details": details}},
        response_only=True,
        status_codes=[str(status)],
    )


# Taken from a real answer of the running code: Chicago, IL to Houston, TX at the default stop
# cost, on the real price table and a recorded road. Shortened in one place: the route line keeps
# 9 of its 2,177 points (the first and the last among them). The numbers are the answer's own.
# tests/test_schema.py makes the same request and compares every other value.
ROUTE_200_EXAMPLE: dict = {
    "summary": {
        "start": {"label": "Chicago, IL", "lat": 41.88585, "lng": -87.61812},
        "finish": {"label": "Houston, TX", "lat": 29.7652, "lng": -95.3657},
        "distance_miles": 1086.9,
        "gallons": 108.69,
        "total_fuel_cost": 331.24,
        "stops": 3,
        "lowest_possible_fuel_cost": 319.62,
        "lowest_possible_stops": 11,
        "first_fill_distance_miles": 0.0,
    },
    "warnings": [],
    "assumptions": {
        "range_miles": 500,
        "miles_per_gallon": 10,
        "tank_gallons": 50,
        "starting_fuel_gallons": 0,
        "stop_cost": 10.0,
        "search_radius_miles": 5,
    },
    "fuel_stops": [
        {
            "order": 1,
            "kind": "start",
            "station_id": 73127,
            "name": "Gas N Wash",
            "address": "I-55, EXIT 285",
            "city": "Chicago",
            "state": "IL",
            "mile_marker": 0.0,
            "lat": 41.88585,
            "lng": -87.61812,
            "price_per_gallon": 3.399,
            "gallons": 31.83,
            "cost": 108.19,
        },
        {
            "order": 2,
            "kind": "station",
            "station_id": 69861,
            "name": "HUCKS FOOD & FUEL #379",
            "address": "I-57, EXIT 53",
            "city": "Marion",
            "state": "IL",
            "mile_marker": 318.3,
            "lat": 37.72464,
            "lng": -88.9587,
            "price_per_gallon": 2.929,
            "gallons": 47.81,
            "cost": 140.04,
        },
        {
            "order": 3,
            "kind": "station",
            "station_id": 72594,
            "name": "Quiktrip #7900",
            "address": "I-30 & FM-989",
            "city": "Texarkana",
            "state": "TX",
            "mile_marker": 796.4,
            "lat": 33.40872,
            "lng": -94.09757,
            "price_per_gallon": 2.85733333,
            "gallons": 29.05,
            "cost": 83.01,
        },
    ],
    "map": {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"kind": "route", "distance_miles": 1086.9},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-87.61799, 41.88551],
                        [-88.30519, 40.11785],
                        [-88.95011, 38.37442],
                        [-89.53853, 36.66324],
                        [-90.52452, 35.12698],
                        [-92.67832, 34.53061],
                        [-94.1551, 33.15016],
                        [-94.72653, 31.46724],
                        [-95.36593, 29.76526],
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {
                    "kind": "stop",
                    "order": 1,
                    "title": "1. Gas N Wash, Chicago IL",
                    "name": "Gas N Wash",
                    "mile_marker": 0.0,
                    "price_per_gallon": 3.399,
                    "gallons": 31.83,
                    "cost": 108.19,
                    "marker-color": "#d9480f",
                },
                "geometry": {"type": "Point", "coordinates": [-87.61812, 41.88585]},
            },
            {
                "type": "Feature",
                "properties": {
                    "kind": "stop",
                    "order": 2,
                    "title": "2. HUCKS FOOD & FUEL #379, Marion IL",
                    "name": "HUCKS FOOD & FUEL #379",
                    "mile_marker": 318.3,
                    "price_per_gallon": 2.929,
                    "gallons": 47.81,
                    "cost": 140.04,
                    "marker-color": "#d9480f",
                },
                "geometry": {"type": "Point", "coordinates": [-88.9587, 37.72464]},
            },
            {
                "type": "Feature",
                "properties": {
                    "kind": "stop",
                    "order": 3,
                    "title": "3. Quiktrip #7900, Texarkana TX",
                    "name": "Quiktrip #7900",
                    "mile_marker": 796.4,
                    "price_per_gallon": 2.85733333,
                    "gallons": 29.05,
                    "cost": 83.01,
                    "marker-color": "#d9480f",
                },
                "geometry": {"type": "Point", "coordinates": [-94.09757, 33.40872]},
            },
            {
                "type": "Feature",
                "properties": {
                    "kind": "start",
                    "title": "Start: Chicago, IL",
                    "marker-color": "#2b8a3e",
                },
                "geometry": {"type": "Point", "coordinates": [-87.61812, 41.88585]},
            },
            {
                "type": "Feature",
                "properties": {
                    "kind": "finish",
                    "title": "Finish: Houston, TX",
                    "marker-color": "#1864ab",
                },
                "geometry": {"type": "Point", "coordinates": [-95.3657, 29.7652]},
            },
        ],
    },
    "meta": {
        "routing_calls": 1,
        "cache_hit": False,
        "routing_server": "router.project-osrm.org",
        "timings_ms": {"routing": 9.0, "own": 37.7, "total": 46.7},
    },
}

_ERRORS = [
    _error(
        "invalid_request",
        "These parameters are missing or not valid: start.",
        {"fields": {"start": ["This field is required."]}},
        400,
        "missing_parameter",
        "A parameter is missing",
    ),
    _error(
        "invalid_request",
        "Start and finish are the same place.",
        {"fields": {"finish": ["Start and finish are the same place."]}},
        400,
        "same_place",
        "Start and finish are the same place",
    ),
    _error(
        "unknown_place",
        "Could not find 'Chicgo, IL'. Try a city and state, such as 'Dallas, TX'.",
        {
            "field": "start",
            "query": "Chicgo, IL",
            "suggestions": [
                "Chicago, IL",
                "Cisco, IL",
                "West Chicago, IL",
                "North Chicago, IL",
                "Cicero, IL",
            ],
        },
        400,
        "unknown_place",
        "A place is not in the table",
    ),
    _error(
        "outside_coverage",
        "'Honolulu, HI' is outside the area covered (the lower 48 states and DC).",
        {"field": "start", "query": "Honolulu, HI"},
        422,
        "outside_coverage",
        "A place is outside the area",
    ),
    _error(
        "route_leaves_usa",
        "The road runs through Canada or Mexico for 252 miles in a row. Only trips that stay in the USA are planned.",
        {"miles_abroad": 252.0},
        422,
        "route_leaves_usa",
        "The road runs through Canada",
    ),
    _error(
        "no_route",
        "No road joins the start and the finish.",
        {},
        422,
        "no_route",
        "The routing service finds no road",
    ),
    _error(
        "no_fuel_plan",
        "No fuel station is listed for 885.3 miles from mile 0.0, more than the truck's range of 500 miles.",
        {"gap_start_mile": 0.0, "gap_miles": 885.3},
        422,
        "no_fuel_plan",
        "A stretch is longer than the range",
    ),
    _error(
        "rate_limited",
        "Too many requests. Try again in 60 seconds.",
        {"retry_after_seconds": 60},
        429,
        "rate_limited",
        "The 61st request in a minute",
    ),
    _error(
        "internal_error",
        "Something went wrong on our side. Please try again later.",
        {},
        500,
        "internal_error",
        "An unexpected failure",
    ),
    _error(
        "routing_unavailable",
        "The routing service could not be reached.",
        {"reason": "timeout"},
        502,
        "routing_unavailable",
        "Both routing servers timed out",
    ),
    _error(
        "stations_not_loaded",
        "No fuel stations are loaded. Run: python manage.py load_stations",
        {},
        503,
        "stations_not_loaded",
        "The station table is empty",
    ),
    _error(
        "api_unavailable",
        "The API cannot be reached.",
        {},
        503,
        "api_unavailable",
        "Sent by the proxy when the API cannot be reached",
    ),
]


def _examples(status: int) -> list[OpenApiExample]:
    return [example for example in _ERRORS if example.status_codes == [str(status)]]


_REQUEST_ID = OpenApiParameter(
    "X-Request-ID",
    OpenApiTypes.STR,
    OpenApiParameter.HEADER,
    response=True,
    description=(
        "The request's ID, as written on the server's log lines for it. A well-formed ID "
        "sent with the request is kept."
    ),
)
_RETRY_AFTER = OpenApiParameter(
    "Retry-After",
    OpenApiTypes.INT,
    OpenApiParameter.HEADER,
    response=[429],
    description="Whole seconds to wait before asking again.",
)


# --- The declarations the views carry ------------------------------------------------------

route_schema = extend_schema(
    operation_id="planRoute",
    summary="Plan the fuel stops of a trip",
    description=(
        "Finds the road between two places, the fuel stations along it, and the cheapest way "
        "to buy the fuel the trip needs, with the truck's 500-mile range and a stop cost "
        "charged while the plan is chosen. Planning reads data and changes nothing, so the "
        "request can be repeated, or tried from a browser's address bar. Finished answers are "
        "cached for 24 hours."
    ),
    parameters=[
        OpenApiParameter(
            "start",
            {"type": "string", "minLength": 1, "maxLength": 100},
            OpenApiParameter.QUERY,
            required=True,
            description=(
                "Where the trip starts, as a city and state: `Dallas, TX`, `Dallas TX` or "
                "`Dallas, Texas`. Spaces at either end are removed; it cannot be blank."
            ),
            examples=[OpenApiExample("city", value="New York, NY")],
        ),
        OpenApiParameter(
            "finish",
            {"type": "string", "minLength": 1, "maxLength": 100},
            OpenApiParameter.QUERY,
            required=True,
            description="Where the trip ends, written as `start` is. It must not be the same place as `start`.",
            examples=[OpenApiExample("city", value="Los Angeles, CA")],
        ),
        OpenApiParameter(
            "stop_cost",
            {"type": "number", "minimum": 0, "maximum": 100, "default": 10},
            OpenApiParameter.QUERY,
            required=False,
            description=(
                "What one stop costs, in dollars, while the plan is chosen: a dearer stop "
                "means fewer, longer fills. 0 to 100, at most 2 decimals, 10 when left out. "
                "Sent empty it is an error, not the default. Never added to the fuel bill."
            ),
        ),
        _REQUEST_ID,
        _RETRY_AFTER,
    ],
    responses={
        200: OpenApiResponse(
            RouteAnswerSerializer,
            description="The plan: small parts first and the map last.",
            examples=[
                OpenApiExample(
                    "chicago_to_houston",
                    summary="Chicago, IL to Houston, TX (the route line shortened)",
                    value=ROUTE_200_EXAMPLE,
                    response_only=True,
                )
            ],
        ),
        400: OpenApiResponse(
            Error400,
            description="The request cannot be used. `invalid_request` or `unknown_place`.",
            examples=_examples(400),
        ),
        422: OpenApiResponse(
            Error422,
            description="The request is well formed but no plan can be made.",
            examples=_examples(422),
        ),
        429: OpenApiResponse(
            Error429,
            description="Too many requests from one client: 60 a minute.",
            examples=_examples(429),
        ),
        500: OpenApiResponse(
            Error500, description="An unexpected failure.", examples=_examples(500)
        ),
        502: OpenApiResponse(
            Error502,
            description="The routing service could not give a road.",
            examples=_examples(502),
        ),
        503: OpenApiResponse(
            Error503,
            description=(
                "The API cannot answer. `stations_not_loaded` comes from the API. "
                "`api_unavailable` is sent by the proxy in front of it when the API cannot be "
                "reached or does not answer within 30 seconds."
            ),
            examples=_examples(503),
        ),
    },
)

health_schema = extend_schema(
    operation_id="health",
    summary="Check that the API is ready",
    description=(
        "Says whether the stations are loaded and where the answering worker's cache is. "
        "Never rate limited."
    ),
    parameters=[_REQUEST_ID],
    responses={
        200: OpenApiResponse(
            HealthSerializer,
            description="The stations are loaded.",
            examples=[
                OpenApiExample(
                    "ready",
                    value={"status": "ok", "stations": 6626, "cache": "redis"},
                    response_only=True,
                )
            ],
        ),
        503: OpenApiResponse(
            HealthError503,
            description="No stations are loaded.",
            examples=[
                OpenApiExample(
                    "not_loaded",
                    value={
                        "error": {
                            "code": "stations_not_loaded",
                            "message": "No fuel stations are loaded. Run: python manage.py load_stations",
                            "details": {},
                        }
                    },
                    response_only=True,
                )
            ],
        ),
    },
)
