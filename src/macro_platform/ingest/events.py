"""Event calendar ingestion and trading-day mapping."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

ALLOWED_EVENT_TYPES = {"CPI", "NFP", "FOMC"}
REQUIRED_COLUMNS = {"event_id", "event_type", "release_date"}


def _validate_columns(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")


def _validate_event_types(df: pd.DataFrame) -> None:
    invalid = set(df["event_type"].unique()) - ALLOWED_EVENT_TYPES
    if invalid:
        raise ValueError(f"Invalid event_type values: {sorted(invalid)}")


def _validate_unique_event_ids(df: pd.DataFrame) -> None:
    dupes = df[df["event_id"].duplicated()]["event_id"].unique()
    if len(dupes):
        raise ValueError(f"Duplicate event_id values: {sorted(dupes)}")


def _validate_release_dates(df: pd.DataFrame) -> None:
    if df["release_date"].isna().any():
        raise ValueError("release_date contains invalid or unparseable values")


def load_events(path: Path) -> pd.DataFrame:
    """Load and validate events CSV."""

    if not path.exists():
        raise FileNotFoundError(f"Events CSV not found: {path}")

    df = pd.read_csv(path)
    _validate_columns(df)

    df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")
    _validate_release_dates(df)
    _validate_event_types(df)
    _validate_unique_event_ids(df)

    df = df.sort_values("release_date").reset_index(drop=True)
    return df


def map_to_trading_day(
    events_df: pd.DataFrame,
    market_calendar_dates: Iterable[pd.Timestamp],
) -> pd.DataFrame:
    """
    Map event release dates to the next available trading day.

    - If release_date is a trading day, keep it.
    - If not, choose the next trading date after release_date.
    - Does not forward fill prices; simply maps to the nearest future trading day.
    """

    if "release_date" not in events_df.columns:
        raise ValueError("release_date column missing")

    trading_dates = pd.DatetimeIndex(market_calendar_dates).sort_values()
    if trading_dates.empty:
        raise ValueError("market_calendar_dates is empty")

    def _map_date(dt: pd.Timestamp) -> pd.Timestamp:
        pos = trading_dates.searchsorted(dt, side="left")
        if pos >= len(trading_dates):
            raise ValueError(f"No available trading date on/after {dt.date()}")
        return trading_dates[pos]

    mapped = events_df.copy()
    mapped["release_date"] = pd.to_datetime(mapped["release_date"], errors="raise")
    mapped["trading_date"] = mapped["release_date"].apply(_map_date)
    return mapped
