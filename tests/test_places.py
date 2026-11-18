"""Cases PL-01 to PL-21: turning place names into coordinates, offline."""

import csv
import time

import pytest
from django.conf import settings

from stations import places
from stations.exceptions import OutsideCoverage, UnknownPlace
from stations.places import locate_city, resolve
from stations.sphere import haversine_miles

BIG_NAMES = [
    "New York, NY",
    "Los Angeles, CA",
    "Chicago, IL",
    "Houston, TX",
    "Phoenix, AZ",
    "Philadelphia, PA",
    "San Antonio, TX",
    "San Diego, CA",
    "Dallas, TX",
    "San Jose, CA",
    "Austin, TX",
    "Jacksonville, FL",
    "Fort Worth, TX",
    "Columbus, OH",
    "Charlotte, NC",
    "San Francisco, CA",
    "Indianapolis, IN",
    "Seattle, WA",
    "Denver, CO",
    "Washington, DC",
    "Boston, MA",
    "El Paso, TX",
    "Nashville, TN",
    "Detroit, MI",
    "Oklahoma City, OK",
    "Portland, OR",
    "Las Vegas, NV",
    "Memphis, TN",
    "Louisville, KY",
    "Baltimore, MD",
    "Milwaukee, WI",
    "Albuquerque, NM",
    "Tucson, AZ",
    "Fresno, CA",
    "Sacramento, CA",
    "Kansas City, MO",
    "Atlanta, GA",
    "Miami, FL",
    "Raleigh, NC",
    "Omaha, NE",
    "Minneapolis, MN",
    "New Orleans, LA",
    "Cleveland, OH",
    "Tampa, FL",
    "St. Louis, MO",
    "Pittsburgh, PA",
    "Cincinnati, OH",
    "Salt Lake City, UT",
    "Buffalo, NY",
    "Boise, ID",
    "Winston-Salem, NC",
    "Coeur d'Alene, ID",
    "St. Paul, MN",
    "Ft. Lauderdale, FL",
    "Mt. Pleasant, SC",
    "O'Fallon, MO",
    "Wilkes-Barre, PA",
    "McAllen, TX",
]


@pytest.fixture(autouse=True)
def _default_places_table():
    """Leave the default places table in place after any test that switches it."""
    yield
    places.use_cities_file(None)


def test_pl01_fifty_eight_names_resolve():
    assert len(BIG_NAMES) == 58
    for name in BIG_NAMES:
        assert isinstance(resolve(name, "start"), places.Place), name


def test_pl02_labels_use_the_tables_spelling():
    names = [
        "St. Louis, MO",
        "Winston-Salem, NC",
        "Coeur d'Alene, ID",
        "St. Paul, MN",
        "Ft. Lauderdale, FL",
        "Mt. Pleasant, SC",
        "O'Fallon, MO",
        "Wilkes-Barre, PA",
        "McAllen, TX",
    ]
    assert [resolve(n, "start").label for n in names] == [
        "Saint Louis, MO",
        "Winston Salem, NC",
        "Coeur D Alene, ID",
        "Saint Paul, MN",
        "Fort Lauderdale, FL",
        "Mount Pleasant, SC",
        "O Fallon, MO",
        "Wilkes Barre, PA",
        "Mcallen, TX",
    ]


@pytest.mark.parametrize(
    "text",
    [
        "Dallas, TX",
        "Dallas TX",
        "Dallas, Texas",
        "Dallas, TX, USA",
        "dallas tx",
        "DALLAS,TX",
        "  Dallas ,  TX  ",
        "Dallas TX US",
        "Dallas, Texas, United States",
    ],
)
def test_pl03_dallas_spellings(text):
    place = resolve(text, "start")
    assert (place.label, place.lat, place.lng) == ("Dallas, TX", 32.790439, -96.80439)


@pytest.mark.parametrize(
    "text", ["Washington, D.C.", "Washington DC", "washington, district of columbia"]
)
def test_pl04_washington_dc(text):
    place = resolve(text, "start")
    assert (place.label, place.lat, place.lng) == ("Washington, DC", 38.912217, -77.017691)


@pytest.mark.parametrize(
    "text",
    ["New York City, NY", "NYC, NY", "Manhattan, NY", "new york ny", "New York, New York"],
)
def test_pl05_new_york_aliases(text):
    place = resolve(text, "start")
    assert (place.label, place.lat, place.lng) == ("New York, NY", 40.74838, -73.996705)


def test_pl06_manhattan_kansas():
    place = resolve("Manhattan, KS", "start")
    assert (place.label, place.lat, place.lng) == ("Manhattan, KS", 39.193757, -96.585776)


@pytest.mark.parametrize("text", ["Sault Ste. Marie, MI", "Sault Ste Marie MI"])
def test_pl07_sault_sainte_marie(text):
    assert resolve(text, "start").label == "Sault Sainte Marie, MI"


@pytest.mark.parametrize("text", ["Santa Fe New Mexico", "Santa Fe, New Mexico", "santa fe nm"])
def test_pl08_santa_fe_is_not_mexico(text):
    place = resolve(text, "start")
    assert (place.label, place.lat, place.lng) == ("Santa Fe, NM", 35.702472, -105.974818)


@pytest.mark.parametrize("text", ["Ft Worth, TX", "Ft. Worth TX", "fort worth, texas"])
def test_pl09_fort_worth_abbreviations(text):
    place = resolve(text, "start")
    assert (place.label, place.lat, place.lng) == ("Fort Worth, TX", 32.7469, -97.3268)


def test_pl10_two_rows_are_averaged():
    place = resolve("Saint Louis, MO", "start")
    assert place.lat == pytest.approx(38.638595, abs=1e-6)
    assert place.lng == pytest.approx(-90.257751, abs=1e-6)


def test_pl11_named_county_row_is_used():
    expected = {
        "Orlando, FL": (28.539882, -81.372668),
        "Saint Paul, MN": (44.969963, -93.083167),
        "Houston, TX": (29.7652, -95.3657),
        "San Francisco, CA": (37.775, -122.4183),
        "Dallas, TX": (32.790439, -96.80439),
    }
    for name, (lat, lng) in expected.items():
        place = resolve(name, "start")
        assert (place.lat, place.lng) == (lat, lng), name


def _rows_by_place() -> dict[tuple[str, str], list[dict]]:
    """The places table, grouped by (state, city name in the table's own spelling)."""
    grouped: dict[tuple[str, str], list[dict]] = {}
    with open(settings.CITIES_CSV, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            grouped.setdefault((row["STATE_CODE"], row["CITY"]), []).append(row)
    return grouped


def test_pl12_exactly_22_places_use_a_named_county():
    expected_counties = {
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
    spread_over_10 = set()
    for (state, city), rows in _rows_by_place().items():
        widest = max(
            haversine_miles(
                float(a["LATITUDE"]),
                float(a["LONGITUDE"]),
                float(b["LATITUDE"]),
                float(b["LONGITUDE"]),
            )
            for a in rows
            for b in rows
        )
        if widest > 10:
            spread_over_10.add((state, city))
    assert spread_over_10 == set(expected_counties)

    grouped = _rows_by_place()
    for (state, city), county in expected_counties.items():
        row = next(r for r in grouped[(state, city)] if r["COUNTY"].casefold() == county.casefold())
        place = resolve(f"{city}, {state}", "start")
        assert (place.lat, place.lng) == (float(row["LATITUDE"]), float(row["LONGITUDE"])), city


def test_pl13_hand_added_places():
    expected = {
        "Port Wentworth, GA": (32.1491, -81.1632),
        "Henrico, VA": (37.5131, -77.3465),
        "Evergreen, AL": (31.4335, -86.9569),
        "Elizabethport, NJ": (40.6501, -74.1871),
        "University Park, IL": (41.4400, -87.6834),
    }
    for name, (lat, lng) in expected.items():
        place = resolve(name, "start")
        assert (place.label, place.lat, place.lng) == (name, lat, lng)
    henrico_nc = resolve("Henrico, NC", "start")
    assert (henrico_nc.lat, henrico_nc.lng) == (36.527409, -77.854625)


def test_pl14_locate_city():
    assert locate_city("ST LOUIS", "MO") == (38.638595, -90.257751)
    assert locate_city("Fort Worth", "TX") == (32.7469, -97.3268)
    assert locate_city("Henrico", "VA") == (37.5131, -77.3465)
    assert locate_city("Nowhereville", "TX") is None


@pytest.mark.parametrize(
    "text",
    [
        "Honolulu, HI",
        "Anchorage, AK",
        "Juneau, Alaska",
        "San Juan, PR",
        "Toronto, ON",
        "Vancouver, BC",
        "Montreal, Canada",
        "Tijuana, Mexico",
        "Tijuana Mexico",
        "Toronto Canada",
    ],
)
def test_pl15_outside_coverage(text):
    with pytest.raises(OutsideCoverage) as caught:
        resolve(text, "finish")
    assert caught.value.details == {"field": "finish", "query": text}


def test_pl16_misspelt_city_gets_suggestions():
    with pytest.raises(UnknownPlace) as caught:
        resolve("Chicgo, IL", "start")
    suggestions = caught.value.details["suggestions"]
    assert "Chicago, IL" in suggestions
    assert 1 <= len(suggestions) <= 5
    assert all(s.endswith(", IL") for s in suggestions)


def test_pl17_city_without_state_lists_the_states_that_have_it():
    with pytest.raises(UnknownPlace) as caught:
        resolve("Chicago", "start")
    assert caught.value.details["suggestions"] == ["Chicago, IL"]


def test_pl18_springfield_gets_five_different_states():
    with pytest.raises(UnknownPlace) as caught:
        resolve("Springfield", "start")
    suggestions = caught.value.details["suggestions"]
    assert len(suggestions) == 5
    assert all(s.startswith("Springfield, ") for s in suggestions)
    assert len({s[-2:] for s in suggestions}) == 5


def test_pl19_unrecognised_state_still_suggests():
    with pytest.raises(UnknownPlace) as caught:
        resolve("Springfield, ZZ", "start")
    assert len(caught.value.details["suggestions"]) <= 5


def _suggestions_for(text):
    with pytest.raises(UnknownPlace) as caught:
        resolve(text, "start")
    return caught.value.details["suggestions"]


def _fifty_largest_places():
    path = settings.DATA_DIR / "large_places.csv"
    with open(path, encoding="utf-8", newline="") as f:
        rows = sorted(csv.DictReader(f), key=lambda r: -int(r["population"]))
    return [(r["city"], r["state"]) for r in rows[:50]]


@pytest.mark.parametrize(("city", "state"), _fifty_largest_places())
def test_pl22_a_large_city_with_no_state_gets_its_own_state_first(city, state):
    assert _suggestions_for(city)[0] == f"{city}, {state}"


def test_pl23_dallas_with_no_state_offers_texas_first():
    assert _suggestions_for("Dallas")[0] == "Dallas, TX"


def test_pl23_a_misspelt_large_city_with_no_state_is_found():
    assert "Dallas, TX" in _suggestions_for("Dalas")
    assert "Houston, TX" in _suggestions_for("Houstan")


def test_pl23_gibberish_with_no_state_gets_nothing():
    assert _suggestions_for("Qwxzy") == []


def test_pl23_the_no_state_fuzzy_lookup_is_fast():
    _suggestions_for("Dalas")  # reads data/large_places.csv the first time
    start = time.perf_counter()
    for _ in range(20):
        _suggestions_for("Houstan")
    assert (time.perf_counter() - start) / 20 < 0.05


@pytest.mark.parametrize("text", ["75201", "1600 Pennsylvania Ave, Washington, DC"])
def test_pl20_zip_codes_and_street_addresses_are_unknown(text):
    with pytest.raises(UnknownPlace):
        resolve(text, "start")


def test_pl21_error_carries_the_field_and_query():
    with pytest.raises(UnknownPlace) as caught:
        resolve("Chicgo, IL", field="finish")
    assert caught.value.details["field"] == "finish"
    assert caught.value.details["query"] == "Chicgo, IL"


def test_qb12_a_place_called_mexico_in_the_usa_is_not_the_country():
    """Review 9-Q0b, note N5. With a trailing USA the caller has said the place is in the
    United States, and several US places are called Mexico."""
    with pytest.raises(UnknownPlace) as caught:
        resolve("Mexico, USA", "start")
    assert sorted(caught.value.details["suggestions"]) == [
        "Mexico, IN",
        "Mexico, ME",
        "Mexico, MO",
        "Mexico, NY",
        "Mexico, PA",
    ]


@pytest.mark.parametrize("text", ["Mexico", "Tijuana Mexico"])
def test_qb12_the_country_without_a_comma_is_still_outside_coverage(text):
    with pytest.raises(OutsideCoverage):
        resolve(text, "start")


@pytest.mark.parametrize("text", ["Texas", "New Mexico"])
def test_a_state_name_on_its_own_is_unknown(text):
    # "New Mexico" ends in "Mexico", but it is a state, not the country.
    with pytest.raises(UnknownPlace):
        resolve(text, "start")


def test_use_cities_file_switches_the_table(tmp_path):
    """The loader's --cities option relies on this: another file replaces the table."""
    small = tmp_path / "cities.csv"
    small.write_text(
        "ID,STATE_CODE,STATE_NAME,CITY,COUNTY,LATITUDE,LONGITUDE\n"
        "1,TX,Texas,Smallville,Nowhere,30.5,-97.5\n",
        encoding="utf-8",
    )
    places.use_cities_file(small)
    assert locate_city("Smallville", "TX") == (30.5, -97.5)
    assert locate_city("Dallas", "TX") is None
    places.use_cities_file(None)
    assert locate_city("Dallas", "TX") is not None
