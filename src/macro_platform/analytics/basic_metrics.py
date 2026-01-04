"""Simple analytics routines for macro events."""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def summarize_events(events: pd.DataFrame) -> dict[str, Any]:
    """Return summary statistics for ingested events."""

    if events.empty:
        logger.warning("No events provided for analysis")
        return {"total": 0, "by_ticker": {}, "by_event": {}}

    by_ticker = Counter(events["ticker"])
    by_event = Counter(events["event"])
    summary = {
        "total": int(len(events)),
        "by_ticker": dict(by_ticker),
        "by_event": dict(by_event),
    }
    logger.info(
        "Computed summary: total=%s, tickers=%s, events=%s",
        summary["total"],
        list(by_ticker.keys()),
        list(by_event.keys()),
    )
    return summary

