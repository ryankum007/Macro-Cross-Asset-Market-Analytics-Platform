import pandas as pd

from macro_platform.analytics.basic_metrics import summarize_events


def test_summarize_events_counts():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "ticker": ["SPY", "SPY"],
            "event": ["CPI", "FOMC"],
        }
    )
    summary = summarize_events(df)
    assert summary["total"] == 2
    assert summary["by_ticker"]["SPY"] == 2
    assert set(summary["by_event"].keys()) == {"CPI", "FOMC"}

