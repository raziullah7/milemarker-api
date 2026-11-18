"""URL configuration. Every address belongs to the trips app, including the catch-all
that answers unknown addresses in the API's own error shape."""

from django.urls import include, path

urlpatterns = [
    path("", include("trips.urls")),
]
