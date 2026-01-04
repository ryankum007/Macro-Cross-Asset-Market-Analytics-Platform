from datetime import date

import pandas as pd
import pytest

from macro_platform.ingest.fred import download_fred_series


def _mock_fetcher(series_id: str, start, end):
    # Build deterministic series with some gaps
    idx = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-05"])
    values = {
        "DGS2": [4.0, 4.1, None],  # Missing on 2024-01-05
        "DGS5": [3.8, None, 3.85],  # Single missing inside limit
        "DGS10": [3.5, 3.55, 3.6],
        "DGS30": [3.7, None, None],  # Two consecutive missing after first point
        "CPIAUCSL": [300.0, 300.0, 300.1],
    }
    data = pd.DataFrame({series_id: values.get(series_id, [])}, index=idx)
    return data


def test_download_fred_series_bps_and_fill_limit():
    start = date(2024, 1, 1)
    end = date(2024, 1, 8)

    df = download_fred_series(start, end, fetcher=_mock_fetcher)

    # Expected business days
    expected_dates = pd.bdate_range(start, end)
    assert (df.index == expected_dates).all()

    # Basis points change calculation: (4.1 - 4.0) * 100 = 10 bps
    dgs2_chg = df.loc[pd.to_datetime("2024-01-02"), "DGS2_chg_bps"]
    assert pytest.approx(dgs2_chg, rel=1e-9) == 10.0

    # Forward fill up to 2 days, then stop: DGS30 missing two consecutive after first value
    assert pd.isna(df.loc[pd.to_datetime("2024-01-05"), "DGS30"])  # limit exceeded

    # Single gap filled for DGS5 and later real observation remains
    assert df.loc[pd.to_datetime("2024-01-02"), "DGS5"] == 3.8
    assert df.loc[pd.to_datetime("2024-01-05"), "DGS5"] == 3.85

    # CPI is present and forward filled implicitly by reindex
    assert df.loc[pd.to_datetime("2024-01-03"), "CPIAUCSL"] == 300.0
