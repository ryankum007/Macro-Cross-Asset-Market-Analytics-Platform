"""Logging configuration helpers."""

from __future__ import annotations

import logging
from logging import Logger


def setup_logging(level: str = "INFO") -> Logger:
    """Configure application-wide logging and return root logger."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logger = logging.getLogger("macro_platform")
    logger.debug("Logging initialized at level %s", level)
    return logger

