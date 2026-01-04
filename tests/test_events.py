from pathlib import Path

import pandas as pd
import pytest

from macro_platform.ingest.events import (
    ALLOWED_EVENT_TYPES,
    load_events,
    map_to_trading_day,
)


def test_weekend_mapping():
    events = pd.DataFrame(
        {
            "event_id": ["E1", "E2"],
            "event_type": ["CPI", "NFP"],
            "release_date": pd.to_datetime(["2024-03-02", "2024-03-04"]),  # Sat, Mon
        }
    )
    calendar = pd.date_range("2024-03-01", "2024-03-08", freq="B")

    mapped = map_to_trading_day(events, calendar)

    assert mapped.loc[0, "trading_date"] == pd.to_datetime("2024-03-04")
    assert mapped.loc[1, "trading_date"] == pd.to_datetime("2024-03-04")


def test_invalid_event_type(tmp_path: Path):
    csv = tmp_path / "events.csv"
    csv.write_text(
        "event_id,event_type,release_date\n"
        "E1,CPI,2024-01-01\n"
        "E2,INVALID,2024-01-02\n"
    )

    with pytest.raises(ValueError) as exc:
        load_events(csv)

    assert "Invalid event_type" in str(exc.value)


def test_duplicate_event_id(tmp_path: Path):
    csv = tmp_path / "events.csv"
    csv.write_text(
        "event_id,event_type,release_date\n"
        "E1,CPI,2024-01-01\n"
        "E1,NFP,2024-01-02\n"
    )

    with pytest.raises(ValueError) as exc:
        load_events(csv)

    assert "Duplicate event_id" in str(exc.value)


def test_unparseable_release_date(tmp_path: Path):
    csv = tmp_path / "events.csv"
    csv.write_text(
        "event_id,event_type,release_date\n"
        "E1,CPI,not-a-date\n"
    )

    with pytest.raises(ValueError) as exc:
        load_events(csv)

    assert "release_date" in str(exc.value)


def test_allowed_event_types_constant():
    assert ALLOWED_EVENT_TYPES == {"CPI", "NFP", "FOMC"}

