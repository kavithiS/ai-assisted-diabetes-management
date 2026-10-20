"""Logging setup shared by every server package."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from diacare_shared.request_context import get_request_id

# Attributes present on every LogRecord; anything else was passed via ``extra=``.
_RESERVED_ATTRS: frozenset[str] = frozenset(
    vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys() | {"message", "asctime"}
)


class JsonFormatter(logging.Formatter):
    """One JSON object per line, with ``request_id`` and any ``extra=`` fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
        }
        for key, value in vars(record).items():
            if key not in _RESERVED_ATTRS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO", *, json_logs: bool = True) -> None:
    """Configure root logging: JSON lines on stdout (default) or the plain text format."""
    if not json_logs:
        logging.basicConfig(
            level=level.upper(),
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True
    # Replaced by the "request completed" line of RequestContextMiddleware.
    logging.getLogger("uvicorn.access").disabled = True
