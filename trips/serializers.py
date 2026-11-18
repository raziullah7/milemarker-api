"""Checks the shape of a request's parameters before any work is done."""

from decimal import Decimal

from django.conf import settings
from rest_framework import serializers


class RouteQuery(serializers.Serializer):
    """The query parameters of GET /api/v1/route/. Unknown parameters are ignored.

    start, finish  required text, trimmed, not blank, at most 100 characters
    stop_cost      optional, 0 to 100 with at most 2 decimals; settings.DEFAULT_STOP_COST
                   when absent. Sent empty, it is an error, not the default.
    """

    # No place name is near 100 characters; the limit keeps the place lookup's work small.
    start = serializers.CharField(max_length=100)
    finish = serializers.CharField(max_length=100)
    stop_cost = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
        default=settings.DEFAULT_STOP_COST,
    )

    def validate_stop_cost(self, value: Decimal) -> Decimal:
        """-0 passes the minimum of 0. abs() makes it 0, so it is shown as 0.0 and shares
        the cached answer of 0. Every other allowed value is left as it is."""
        return abs(value)
