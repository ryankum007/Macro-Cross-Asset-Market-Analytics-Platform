from datetime import date
from pathlib import Path

import pandas as pd

from macro_platform.config import get_settings
from macro_platform.ingest.market_data import ASSET_METADATA, download_market_data


def _mock_download(ticker, start=None, end=None, progress=None, auto_adjust=None):
    # Build deterministic mock data with a couple of days of prices
    idx = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-04"])
    data = {
        "Close": pd.Series([100.0, 101.0, 102.0], index=idx),
        "Adj Close": pd.Series([99.0, 100.0, 101.0], index=idx),
    }
    return pd.DataFrame(data)


def test_download_market_data_schema_and_no_duplicates(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("MACRO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("MACRO_OUTPUT_DIR", str(tmp_path))
    get_settings.cache_clear()
    monkeypatch.setattr("macro_platform.ingest.market_data.yf.download", _mock_download)

    df = download_market_data(date(2024, 1, 1), date(2024, 1, 5))

    # Schema
    assert list(df.columns) == ["date", "asset_id", "close", "adj_close", "return_1d"]
    assert set(df["asset_id"].unique()) == set(ASSET_METADATA.keys())

    # No duplicate date/asset rows
    duplicates = df.duplicated(subset=["date", "asset_id"]).sum()
    assert duplicates == 0

    # Deterministic values for mock data
    sample = df[(df["asset_id"] == "sp500") & (df["date"] == pd.to_datetime("2024-01-02"))]
    assert sample.iloc[0]["close"] == 101.0
    assert round(sample.iloc[0]["return_1d"], 6) == round((101.0 - 100.0) / 100.0, 6)

    get_settings.cache_clear()

