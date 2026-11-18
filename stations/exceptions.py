"""Errors raised by the data side, and the base class every API error shares.

These are plain Python exceptions. They carry a code, a message and details, and know
nothing about HTTP: trips/errors.py is the one place that maps a code to a status.
"""


class MileMarkerError(Exception):
    """Base for every error the API reports on purpose.

    code     a short machine-readable name, e.g. "unknown_place"
    message  one plain sentence for a person
    details  a dict whose keys are fixed per code (see the error table in the architecture doc)
    """

    code = "error"

    def __init__(self, message: str, **details):
        super().__init__(message)
        self.message = message
        self.details = details


class UnknownPlace(MileMarkerError):
    """A place name is not in the places table.

    details: field ("start" or "finish"), query (the text as given),
             suggestions (up to five "City, ST" strings, possibly none)
    """

    code = "unknown_place"

    def __init__(self, message: str, *, field: str, query: str, suggestions: list[str]):
        super().__init__(message, field=field, query=query, suggestions=suggestions)


class OutsideCoverage(MileMarkerError):
    """A place is real but outside the lower 48 states and DC.

    details: field, query
    """

    code = "outside_coverage"

    def __init__(self, message: str, *, field: str, query: str):
        super().__init__(message, field=field, query=query)


class StationsNotLoaded(MileMarkerError):
    """The station table is empty: load_stations has not been run."""

    code = "stations_not_loaded"
