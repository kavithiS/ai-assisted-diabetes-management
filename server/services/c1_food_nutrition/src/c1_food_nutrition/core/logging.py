"""Structured JSON logging built on the standard library (no structlog, see ADR 0001)."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from c1_food_nutrition.core.context import get_request_id

# Attributes present on every LogRecord; anything else was passed via ``extra=``.
_RESERVED_ATTRS: frozenset[str] = frozenset(
    vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys() | {"message", "asctime"}
)


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON objects.

    Every line includes ``timestamp``, ``level``, ``logger``, ``message`` and
    ``request_id``. Fields passed through ``extra=`` are added as top-level keys.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Render ``record`` as a JSON string."""
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


def configure_logging(level: str = "INFO") -> None:
    """Route root and uvicorn logs through a single JSON stdout handler.

    Safe to call more than once: existing root handlers are replaced.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    for name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
    # Access logs are replaced by our own request-completed log line.
    logging.getLogger("uvicorn.access").disabled = True
