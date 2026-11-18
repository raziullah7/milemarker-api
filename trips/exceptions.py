"""Errors raised while planning a trip. Plain exceptions: see stations/exceptions.py."""

from stations.exceptions import MileMarkerError


class InvalidRequest(MileMarkerError):
    """The request is malformed, or its start and finish are the same place.

    details: fields, a dict of parameter name -> list of messages
    """

    code = "invalid_request"

    def __init__(self, message: str, *, fields: dict[str, list[str]]):
        super().__init__(message, fields=fields)


class NoRoute(MileMarkerError):
    """The routing service says no road joins the two points."""

    code = "no_route"


class RouteLeavesUSA(MileMarkerError):
    """The road runs through Canada or Mexico for more than the allowed stretch.

    details: miles_abroad, the longest unbroken stretch outside the USA, to 0.1 mile
    """

    code = "route_leaves_usa"

    def __init__(self, message: str, *, miles_abroad: float):
        # Miles are shown to 1 decimal everywhere; the caller reads these details.
        super().__init__(message, miles_abroad=round(miles_abroad, 1))


class NoFuelPlan(MileMarkerError):
    """A stretch of more than 500 miles has no station, so no plan exists.

    details: gap_start_mile (where that stretch begins), gap_miles (its length), each
             to 0.1 mile
    """

    code = "no_fuel_plan"

    def __init__(self, message: str, *, gap_start_mile: float, gap_miles: float):
        # Rounded only here, in what the caller reads; the fuel routines that find the
        # gap keep working with exact miles.
        super().__init__(
            message, gap_start_mile=round(gap_start_mile, 1), gap_miles=round(gap_miles, 1)
        )


class RoutingUnavailable(MileMarkerError):
    """Both routing servers failed.

    details: reason, "timeout" when every attempt timed out and "error" otherwise
    """

    code = "routing_unavailable"

    def __init__(self, message: str, *, reason: str):
        super().__init__(message, reason=reason)
