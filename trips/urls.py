"""Addresses the API answers."""

from django.urls import re_path

from trips.views import RouteView, not_found

urlpatterns = [
    # The trailing slash is optional; there is no redirect from one form to the other.
    re_path(r"^api/v1/route/?$", RouteView.as_view(), name="route"),
    # Last, so it only catches what nothing above matched. A view, not Django's 404
    # handling, so the answer is the same JSON whatever DEBUG is.
    re_path(r"^.*$", not_found),
]
