"""plan_trip(): the one function the API layer calls.

It runs the steps of the request flow in order (architecture document, sections 2 and 5)
and owns the two caches (section 10). Everything it calls is in the modules beside it
and in the stations app; the rules themselves live there, not here.
"""

from decimal import Decimal


def plan_trip(start_text: str, finish_text: str, stop_cost: Decimal) -> dict:
    """Plan a trip and return the whole response body, including `meta`.

    Order of work, so that nothing knowable before the routing call is raised after it:
    resolve start, resolve finish, same-place check, answer cache, stations loaded and
    nearest station to the start, road (cache or one routing call), border check,
    stations along the road, fuel plan, answer.

    Raises the errors in stations/exceptions.py and trips/exceptions.py.
    """
    raise NotImplementedError
