"""URL configuration. Every address belongs to the trips app, including the catch-all
that answers unknown addresses in the API's own error shape."""

from django.urls import include, path

from trips.schema import DocsView, SchemaView

urlpatterns = [
    # Before the include: the last pattern of trips.urls matches every address.
    path("api/v1/schema/", SchemaView.as_view(), name="schema"),
    path("api/v1/docs/", DocsView.as_view(url_name="schema"), name="docs"),
    path("", include("trips.urls")),
]

# Failures outside the REST framework still answer in the API's JSON error shape: a request
# Django refuses to read (400) and an unexpected failure (500). No handler403 is set:
# nothing in the API can answer 403.
handler400 = "trips.views.bad_request"
handler500 = "trips.views.server_error"
