"""Market data ingestion via yfinance with caching and normalization."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import TypedDict

import pandas as pd
import yfinance as yf

from macro_platform.config import Settings, get_settings

logger = logging.getLogger(__name__)


class AssetMeta(TypedDict):
    ticker: str
    name: str


ASSET_METADATA: dict[str, AssetMeta] = {
    "sp500": {"ticker": "^GSPC", "name": "S&P 500"},
    "nasdaq": {"ticker": "^IXIC", "name": "Nasdaq Composite"},
    "eurusd": {"ticker": "EURUSD=X", "name": "EUR/USD"},
    "vix": {"ticker": "^VIX", "name": "CBOE Volatility Index"},
}


def _cache_path(cache_dir: Path, start: date, end: date) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"market_data_{start.isoformat()}_{end.isoformat()}.parquet"


def _build_calendar(start: date, end: date) -> pd.DatetimeIndex:
    if start > end:
        raise ValueError("start_date must be on or before end_date")
    return pd.date_range(start=start, end=end, freq="B", name="date")


def download_market_data(start_date: date, end_date: date) -> pd.DataFrame:
    """
    Download OHLC data for configured assets and return normalized DataFrame.

    Columns: date, asset_id, close, adj_close, return_1d.
    Business-day calendar is unified across assets; missing prices remain null (no ffill).
    Results are cached as Parquet under data/cache.
    """

    settings: Settings = get_settings()
    cache_file = _cache_path(settings.data_dir / "cache", start_date, end_date)
    if cache_file.exists():
        logger.info("Loading cached market data from %s", cache_file)
        return pd.read_parquet(cache_file)

    calendar = _build_calendar(start_date, end_date)
    frames: list[pd.DataFrame] = []
    yf_end = end_date + timedelta(days=1)  # yfinance end is exclusive

    for asset_id, meta in ASSET_METADATA.items():
        ticker = meta["ticker"]
        logger.info("Downloading %s (%s) from %s to %s", asset_id, ticker, start_date, end_date)
        raw = yf.download(
            ticker,
            start=start_date,
            end=yf_end,
            progress=False,
            auto_adjust=False,
        )

        # Normalize columns and align to unified business-day calendar
        if raw.empty:
            close = pd.Series(dtype="float", name="Close")
            adj_close = pd.Series(dtype="float", name="Adj Close")
        else:
            close = raw.get("Close", pd.Series(dtype="float"))
            adj_close = raw.get("Adj Close", pd.Series(dtype="float"))

        df = pd.DataFrame(index=calendar)
        df["close"] = close.reindex(calendar)
        df["adj_close"] = adj_close.reindex(calendar)
        df["asset_id"] = asset_id

        # Compute simple daily returns; no forward fill to avoid synthetic continuity
        df["return_1d"] = df["close"].pct_change(fill_method=None)

        frames.append(df.reset_index())

    result = pd.concat(frames, ignore_index=True)
    result = result[["date", "asset_id", "close", "adj_close", "return_1d"]]
    result.sort_values(["date", "asset_id"], inplace=True, ignore_index=True)

    result.to_parquet(cache_file, index=False)
    logger.info("Saved market data cache to %s", cache_file)
    return result
