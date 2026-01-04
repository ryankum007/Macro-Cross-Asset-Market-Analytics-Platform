"""Visualization helpers for analytics outputs."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


def plot_event_counts(by_ticker: Mapping[str, int], output_dir: Path) -> Path:
    """Plot event counts by ticker and save to the outputs directory."""

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "event_counts.png"

    if not by_ticker:
        logger.warning("No ticker counts to plot")
        return output_path

    tickers = list(by_ticker.keys())
    counts = list(by_ticker.values())

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(tickers, counts, color="#2F80ED")
    ax.set_title("Event Counts by Ticker")
    ax.set_xlabel("Ticker")
    ax.set_ylabel("Count")
    plt.tight_layout()

    fig.savefig(output_path)
    plt.close(fig)
    logger.info("Saved plot to %s", output_path)
    return output_path
