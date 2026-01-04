from pathlib import Path

import pandas as pd

from macro_platform.ingest.csv_loader import load_event_data


def test_load_event_data(tmp_path: Path):
    sample = tmp_path / "events.csv"
    sample.write_text("date,ticker,event\n2024-01-01,SPY,Fed\n")
    df = load_event_data(sample)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df.loc[0, "ticker"] == "SPY"

