import pandas as pd
import pytest

from macro_platform.analytics.event_study import run_event_study


def test_cumulative_return_math(tmp_path):
    # Toy market data for a single asset
    market_data = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "asset_id": ["sp500", "sp500", "sp500"],
            "return_1d": [0.01, -0.005, 0.02],
        }
    )

    events = pd.DataFrame(
        {
            "event_id": ["E1"],
            "event_type": ["CPI"],
            "trading_date": pd.to_datetime(["2024-01-02"]),
        }
    )

    summary, details = run_event_study(
        market_data,
        events,
        event_windows=[(-1, 1)],
        output_dir=tmp_path,
    )

    expected_cum = (1 + 0.01) * (1 - 0.005) * (1 + 0.02) - 1
    assert pytest.approx(details.iloc[0]["cumulative_return"], rel=1e-9) == expected_cum
    assert summary.iloc[0]["mean"] == details.iloc[0]["cumulative_return"]


def test_event_skips_when_data_missing(tmp_path):
    market_data = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-03"]),
            "asset_id": ["sp500", "sp500"],
            "return_1d": [0.01, 0.02],
        }
    )
    events = pd.DataFrame(
        {"event_id": ["E1"], "event_type": ["CPI"], "trading_date": pd.to_datetime(["2024-01-02"])}
    )

    summary, details = run_event_study(
        market_data,
        events,
        event_windows=[(-1, 1)],
        output_dir=tmp_path,
    )

    assert details.empty
    assert summary.empty
