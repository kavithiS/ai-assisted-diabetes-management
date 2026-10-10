"""Logging setup shared by every server package."""

import logging


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging with one consistent format."""
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
