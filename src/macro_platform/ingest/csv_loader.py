"""CSV-based ingestion utilities."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def load_event_data(csv_path: Path) -> pd.DataFrame:
    """Load event data from CSV into a DataFrame."""

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    logger.info("Loading events from %s", csv_path)
    df = pd.read_csv(csv_path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    logger.debug("Loaded %s rows", len(df))
    return df

