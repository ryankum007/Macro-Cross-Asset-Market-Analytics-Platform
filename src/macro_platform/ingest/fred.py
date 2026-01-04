"""FRED ingestion utilities using pandas_datareader."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date

import pandas as pd
from pandas_datareader import data as pdr

logger = logging.getLogger(__name__)

FRED_SERIES: dict[str, str] = {
    "DGS2": "2Y Treasury",
    "DGS5": "5Y Treasury",
    "DGS10": "10Y Treasury",
    "DGS30": "30Y Treasury",
    "CPIAUCSL": "CPI (All Urban Consumers)",
}


Fetcher = Callable[[str, date, date], pd.DataFrame]


def _default_fetcher(series_id: str, start: date, end: date) -> pd.DataFrame:
    return pdr.DataReader(series_id, "fred", start, end)


def _ensure_business_calendar(start: date, end: date) -> pd.DatetimeIndex:
    if start > end:
        raise ValueError("start_date must be on or before end_date")
    return pd.date_range(start=start, end=end, freq="B", name="date")


def _forward_fill_limited(series: pd.Series, limit: int) -> pd.Series:
    """Forward fill with an upper limit on consecutive fills."""

    return series.ffill(limit=limit)


def download_fred_series(
    start_date: date, end_date: date, fetcher: Fetcher | None = None
) -> pd.DataFrame:
    """
    Download configured FRED series and return a business-day indexed DataFrame.

    - Yields are in percent levels.
    - For yields, forward fill up to 2 consecutive business days, then leave missing.
    - Yield changes in basis points are provided as <ID>_chg_bps.
    """

    _fetcher = fetcher or _default_fetcher
    calendar = _ensure_business_calendar(start_date, end_date)

    frames: list[pd.Series] = []
    for series_id in FRED_SERIES:
        logger.info("Fetching FRED series %s", series_id)
        raw = _fetcher(series_id, start_date, end_date)
        if raw.empty:
            series = pd.Series(dtype="float64", name=series_id)
        else:
            # DataReader returns a DataFrame with the series_id as the sole column
            series = raw.iloc[:, 0]

        series.index = pd.to_datetime(series.index)
        series.name = series_id
        series = series.reindex(calendar)

        if series_id.startswith("DGS"):
            series = _forward_fill_limited(series, limit=2)
        else:
            series = series.ffill()

        frames.append(series)

    data = pd.concat(frames, axis=1)

    # Compute basis point changes for yield series only
    for series_id in [sid for sid in FRED_SERIES if sid.startswith("DGS")]:
        chg_col = f"{series_id}_chg_bps"
        data[chg_col] = data[series_id].diff() * 100

    return data
