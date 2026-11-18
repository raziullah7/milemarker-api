"""URL configuration. Every address belongs to the trips app, including the catch-all
that answers unknown addresses in the API's own error shape."""

from django.urls import include, path

urlpatterns = [
    path("", include("trips.urls")),
]

# Failures outside the REST framework still answer in the API's JSON error shape: a request
# Django refuses to read (400) and an unexpected failure (500). No handler403 is set:
# nothing in the API can answer 403.
handler400 = "trips.views.bad_request"
handler500 = "trips.views.server_error"
