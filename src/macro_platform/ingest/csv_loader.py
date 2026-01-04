"""CSV-based ingestion utilities."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def _resolve_csv_path(csv_path: Path) -> Path:
    if csv_path.exists():
        return csv_path

    if not csv_path.is_absolute():
        project_root = Path(__file__).resolve().parents[2]
        candidate = project_root / csv_path
        if candidate.exists():
            return candidate

    raise FileNotFoundError(f"CSV not found: {csv_path}")


def load_event_data(csv_path: Path) -> pd.DataFrame:
    """Load event data from CSV into a DataFrame."""

    csv_path = _resolve_csv_path(csv_path)

    logger.info("Loading events from %s", csv_path)
    df = pd.read_csv(csv_path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    logger.debug("Loaded %s rows", len(df))
    return df
