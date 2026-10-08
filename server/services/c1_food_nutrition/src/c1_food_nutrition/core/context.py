"""Per-request context shared across layers (e.g. for log correlation)."""

from contextvars import ContextVar

#: Correlation ID of the request being handled, or ``None`` outside a request.
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """Return the current request's correlation ID, if any."""
    return request_id_var.get()
