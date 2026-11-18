"""Turn a place name into coordinates, using the offline table of US places.

The same lookup serves the station loader (each station's city) and the API (start and
finish), so both follow one set of rules. The rules are in the architecture document,
section 6, "The places table". No network call is ever made here.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Place:
    """A resolved place. `label` is "City, ST" in the table's own spelling."""

    label: str
    lat: float
    lng: float


def resolve(text: str, field: str) -> Place:
    """Resolve what a caller typed for `field` ("start" or "finish").

    Accepts everyday spellings: "Dallas, TX", "Dallas TX", "Dallas, Texas",
    "Dallas, TX, USA", "st. louis, mo", "Washington, D.C.", "New York City, NY".

    Raises UnknownPlace (with suggestions) or OutsideCoverage, each carrying `field`
    and the text exactly as given.
    """
    raise NotImplementedError


def locate_city(city: str, state: str) -> tuple[float, float] | None:
    """(lat, lng) of a city in a state, or None if the table does not have it.

    `state` is a two-letter code. Used by the loader, which already has city and state
    in separate columns.
    """
    raise NotImplementedError
