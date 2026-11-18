"""Turn every error into one response shape:

    {"error": {"code": "...", "message": "...", "details": {...}}}

This is the only place that knows which HTTP status a code maps to.
"""


def handler(exc, context):
    """The Django REST Framework exception handler named in settings."""
    raise NotImplementedError
