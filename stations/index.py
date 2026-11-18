"""All stations in memory, loaded from the database once per process.

This is the only code, apart from the loader, that touches the database. Requests never
do: they search the arrays held here.
"""

from stations.exceptions import StationsNotLoaded
from stations.models import FuelStation
from stations.sphere import haversine_miles
from stations.types import StationIndex, StationInfo, build_index

# Distances this close are treated as equal, so stations in one city count as a tie.
TIE_MILES = 0.01

_index: StationIndex | None = None


def get_index() -> StationIndex:
    """The station index, read from the database the first time it is asked for.

    Rows are read in station-ID order. The result is remembered for the life of the
    process, so later calls make no query.

    Raises StationsNotLoaded if the table is empty. An empty table is never
    remembered: once load_stations has run, the next call succeeds without a restart.
    """
    global _index
    if _index is not None:
        return _index

    stations = [
        (
            StationInfo(
                opis_id=row.opis_id,
                name=row.name,
                address=row.address,
                city=row.city,
                state=row.state,
                price=row.price,
            ),
            row.lat,
            row.lng,
        )
        for row in FuelStation.objects.order_by("opis_id")
    ]
    if not stations:
        raise StationsNotLoaded("No fuel stations are loaded. Run: python manage.py load_stations")
    _index = build_index(stations)
    return _index


def reset_index() -> None:
    """Forget the remembered index, so the next get_index() reads the database again."""
    global _index
    _index = None


def nearest_station(index: StationIndex, lat: float, lng: float) -> tuple[int, float]:
    """The station nearest a point: (its position in the index, its distance in miles).

    Stations in one city share one position, so the nearest is often a tie. Among the
    stations within 0.01 mile of the smallest distance, the cheapest wins, and then
    the lowest station ID.
    """
    miles = haversine_miles(lat, lng, index.lat, index.lng)
    candidates = (miles <= miles.min() + TIE_MILES).nonzero()[0]
    # Compare the exact decimal prices, not the float copies, so equal prices really tie.
    best = min(candidates, key=lambda k: (index.info[k].price, index.info[k].opis_id))
    return int(best), float(miles[best])
