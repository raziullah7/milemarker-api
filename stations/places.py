"""Turn a place name into coordinates, using the offline table of US places.

The same lookup serves the station loader (each station's city) and the API (start and
finish), so both follow one set of rules. The rules are in the architecture document,
section 6, "The places table". No network call is ever made here.
"""

import csv
import difflib
import re
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

from stations.exceptions import OutsideCoverage, UnknownPlace

MAX_SUGGESTIONS = 5

# The lower 48 states and DC, which the API covers.
COVERED_STATES = {
    "AL": "Alabama", "AR": "Arkansas", "AZ": "Arizona", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DC": "District of Columbia", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "IA": "Iowa", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "MA": "Massachusetts", "MD": "Maryland", "ME": "Maine", "MI": "Michigan",
    "MN": "Minnesota", "MO": "Missouri", "MS": "Mississippi", "MT": "Montana",
    "NC": "North Carolina", "ND": "North Dakota", "NE": "Nebraska", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NV": "Nevada", "NY": "New York", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VA": "Virginia", "VT": "Vermont", "WA": "Washington",
    "WI": "Wisconsin", "WV": "West Virginia", "WY": "Wyoming",
}  # fmt: skip

# Real places the API does not cover: Alaska, Hawaii, Puerto Rico and the Canadian provinces.
OUTSIDE_STATES = {
    "AK": "Alaska", "HI": "Hawaii", "PR": "Puerto Rico",
    "AB": "Alberta", "BC": "British Columbia", "MB": "Manitoba", "NB": "New Brunswick",
    "NL": "Newfoundland and Labrador", "NS": "Nova Scotia", "NT": "Northwest Territories",
    "NU": "Nunavut", "ON": "Ontario", "PE": "Prince Edward Island", "QC": "Quebec",
    "SK": "Saskatchewan", "YT": "Yukon",
}  # fmt: skip

# Five places the supplied table lacks but the fuel CSV uses (OpenStreetMap, 18 Nov 2026).
# They are only used when the table itself has no such city, so "Henrico, NC" is unaffected.
HAND_ADDED_PLACES = {
    ("GA", "Port Wentworth"): (32.1491, -81.1632),
    ("VA", "Henrico"): (37.5131, -77.3465),
    ("AL", "Evergreen"): (31.4335, -86.9569),
    ("NJ", "Elizabethport"): (40.6501, -74.1871),
    ("IL", "University Park"): (41.4400, -87.6834),
}

# Cities the table lists under several counties whose rows are more than 10 miles apart
# (22 of them, measured). Averaging would land between the rows, so one county's row is
# used: the county the city is the seat of or mainly lies in.
COUNTY_FOR_CITY = {
    ("FL", "Orlando"): "Orange",
    ("TX", "Austin"): "Travis",
    ("PA", "Philadelphia"): "Philadelphia",
    ("FL", "Jacksonville"): "Duval",
    ("SC", "Greenville"): "Greenville",
    ("TX", "San Antonio"): "Bexar",
    ("MN", "Saint Paul"): "Ramsey",
    ("NE", "Omaha"): "Douglas",
    ("SC", "North Charleston"): "Charleston",
    ("PA", "Fort Washington"): "Montgomery",
    ("NJ", "Trenton"): "Mercer",
    ("TX", "Dallas"): "Dallas",
    ("OH", "Cincinnati"): "Hamilton",
    ("SC", "Charleston"): "Charleston",
    ("TX", "Houston"): "Harris",
    ("FL", "Kissimmee"): "Osceola",
    ("CO", "Denver"): "Denver",
    ("FL", "Wewahitchka"): "Gulf",
    ("IN", "Indianapolis"): "Marion",
    ("CA", "San Francisco"): "San Francisco",
    ("CO", "Littleton"): "Arapahoe",
    ("FL", "Tampa"): "Hillsborough",
}

_ABBREVIATIONS = {"ST": "SAINT", "STE": "SAINTE", "FT": "FORT", "MT": "MOUNT"}
_NEW_YORK_ALIASES = {"NEWYORKCITY", "NYC", "MANHATTAN"}
# Only a whole final word counts, so "Dallas TX US" loses its "US" but no city name is cut.
_TRAILING_COUNTRY = re.compile(
    r"[\s,]+(?:USA|US|UNITED\s+STATES(?:\s+OF\s+AMERICA)?)\s*$", re.IGNORECASE
)


@dataclass(frozen=True)
class Place:
    """A resolved place. `label` is "City, ST" in the table's own spelling."""

    label: str
    lat: float
    lng: float


@dataclass(frozen=True)
class _Table:
    """The places table in memory, keyed by (state code, city key)."""

    places: dict[tuple[str, str], Place]
    hand_added: frozenset[tuple[str, str]]


_table: _Table | None = None
_cities_path: Path | None = None  # None means settings.CITIES_CSV


def use_cities_file(path: Path | str | None) -> None:
    """Read places from `path` from now on; None goes back to settings.CITIES_CSV.

    The table is rebuilt the next time it is needed. The loader uses this for --cities.
    """
    global _table, _cities_path
    _cities_path = Path(path) if path is not None else None
    _table = None


def _city_key(city: str) -> str:
    """The name in capitals, St/Ste/Ft/Mt expanded, with everything but letters removed.

    So "St. Louis", "Saint Louis" and "st louis" are one key, as are "Winston-Salem"
    and "winston salem".
    """
    expanded = re.sub(r"\b(ST|STE|FT|MT)\b\.?", lambda m: _ABBREVIATIONS[m.group(1)], city.upper())
    return re.sub(r"[^A-Z]", "", expanded)


def _get_table() -> _Table:
    """The places table, read from disk the first time it is needed."""
    global _table
    if _table is None:
        _table = _read_table(_cities_path or Path(settings.CITIES_CSV))
    return _table


def _read_table(path: Path) -> _Table:
    """Read the CSV: one Place per (state, city), plus the hand-added places the CSV lacks."""
    rows_by_place: dict[tuple[str, str], list[dict[str, str]]] = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["STATE_CODE"] in COVERED_STATES:
                key = (row["STATE_CODE"], _city_key(row["CITY"]))
                rows_by_place.setdefault(key, []).append(row)

    county_for_key = {(s, _city_key(c)): county for (s, c), county in COUNTY_FOR_CITY.items()}
    places: dict[tuple[str, str], Place] = {}
    for (state, key), rows in rows_by_place.items():
        chosen = rows
        county = county_for_key.get((state, key))
        if county is not None:
            chosen = [r for r in rows if r["COUNTY"].casefold() == county.casefold()] or rows
        # Several rows (one per county) are averaged, so the point is in the middle of them.
        lat = sum(float(r["LATITUDE"]) for r in chosen) / len(chosen)
        lng = sum(float(r["LONGITUDE"]) for r in chosen) / len(chosen)
        places[(state, key)] = Place(f"{rows[0]['CITY']}, {state}", lat, lng)

    hand_added = set()
    for (state, city), (lat, lng) in HAND_ADDED_PLACES.items():
        key = (state, _city_key(city))
        if key not in places:
            places[key] = Place(f"{city}, {state}", lat, lng)
            hand_added.add(key)
    return _Table(places, frozenset(hand_added))


def _state_code(text: str) -> str | None:
    """The state code for text such as "TX", "Texas" or "D.C.", or None if it is no state."""
    letters = re.sub(r"[^A-Z]", "", text.upper())
    for states in (COVERED_STATES, OUTSIDE_STATES):
        for code, name in states.items():
            if letters in (code, re.sub(r"[^A-Z]", "", name.upper())):
                return code
    return None


def _split_trailing_state(text: str) -> tuple[str, str | None]:
    """Split "Santa Fe New Mexico" into ("Santa Fe", "NM"), trying the longest state name first.

    A state on its own, with no city before it, is not a place: the text comes back whole.
    """
    words = text.split()
    for count in range(min(3, len(words) - 1), 0, -1):
        code = _state_code(" ".join(words[-count:]))
        if code is not None:
            return " ".join(words[:-count]), code
    return text, None


def _suggestions(city_key: str, state: str | None, table: _Table) -> list[str]:
    """Up to five "City, ST" labels: close names in the state, or the city in other states."""
    if not city_key:
        return []
    if state in COVERED_STATES:
        keys_in_state = [k for (s, k) in table.places if s == state]
        close = difflib.get_close_matches(city_key, keys_in_state, n=MAX_SUGGESTIONS)
        return [table.places[(state, k)].label for k in close]
    states_with_city = sorted(s for (s, k) in table.places if k == city_key)
    return [table.places[(s, city_key)].label for s in states_with_city[:MAX_SUGGESTIONS]]


def resolve(text: str, field: str) -> Place:
    """Resolve what a caller typed for `field` ("start" or "finish").

    Accepts everyday spellings: "Dallas, TX", "Dallas TX", "Dallas, Texas",
    "Dallas, TX, USA", "st. louis, mo", "Washington, D.C.", "New York City, NY".

    Raises UnknownPlace (with suggestions) or OutsideCoverage, each carrying `field`
    and the text exactly as given.
    """
    outside = OutsideCoverage(
        f"{text.strip()!r} is outside the area covered (the lower 48 states and DC).",
        field=field,
        query=text,
    )
    cleaned = _TRAILING_COUNTRY.sub("", text.strip())

    if "," in cleaned:
        city_text, state_text = cleaned.rsplit(",", 1)
        # A country counts only as the whole final part, so "Santa Fe, New Mexico" is safe.
        if state_text.strip().casefold() in ("canada", "mexico"):
            raise outside
        state = _state_code(state_text)
    else:
        city_text, state = _split_trailing_state(cleaned)

    if state in OUTSIDE_STATES:
        raise outside

    table = _get_table()
    city_key = _city_key(city_text)
    if state == "NY" and city_key in _NEW_YORK_ALIASES:
        city_key = "NEWYORK"
    found = table.places.get((state, city_key)) if state else None
    if found is not None:
        return found

    raise UnknownPlace(
        f"Could not find {text.strip()!r}. Try a city and state, such as 'Dallas, TX'.",
        field=field,
        query=text,
        suggestions=_suggestions(city_key, state, table),
    )


def locate_city(city: str, state: str) -> tuple[float, float] | None:
    """(lat, lng) of a city in a state, or None if the table does not have it.

    `state` is a two-letter code. Used by the loader, which already has city and state
    in separate columns.
    """
    place = _get_table().places.get((state, _city_key(city)))
    return (place.lat, place.lng) if place else None


def is_hand_added(city: str, state: str) -> bool:
    """True if the city's position comes from HAND_ADDED_PLACES, not from the table."""
    return (state, _city_key(city)) in _get_table().hand_added
