"""All stations in memory, loaded from the database once per process.

This is the only code, apart from the loader, that touches the database. Requests never
do: they search the arrays held here.
"""

from stations.types import StationIndex


def get_index() -> StationIndex:
    """The station index, read from the database the first time it is asked for.

    Rows are read in station-ID order. The result is remembered for the life of the
    process, so later calls make no query.

    Raises StationsNotLoaded if the table is empty. An empty table is never
    remembered: once load_stations has run, the next call succeeds without a restart.
    """
    raise NotImplementedError


def reset_index() -> None:
    """Forget the remembered index, so the next get_index() reads the database again."""
    raise NotImplementedError


def nearest_station(index: StationIndex, lat: float, lng: float) -> tuple[int, float]:
    """The station nearest a point: (its position in the index, its distance in miles).

    Stations in one city share one position, so the nearest is often a tie. Among the
    stations within 0.01 mile of the smallest distance, the cheapest wins, and then
    the lowest station ID.
    """
    raise NotImplementedError
