"""Per-request context shared across layers (e.g. for log correlation).

The variable lives in ``diacare_shared`` so the shared error handler sees the same request id.
"""

from diacare_shared.request_context import get_request_id, request_id_var

__all__ = ["get_request_id", "request_id_var"]
