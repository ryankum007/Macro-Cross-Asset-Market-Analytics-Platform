"""Event study analytics on daily market data."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from macro_platform.config import get_settings
from macro_platform.logging_utils import setup_logging

logger = logging.getLogger(__name__)

Window = tuple[int, int]


def _prepare_market_returns(market_data: pd.DataFrame) -> dict[str, pd.Series]:
    """Normalize market data and return a mapping of asset_id to returns series."""
    required_cols = {"date", "asset_id", "return_1d"}
    missing = required_cols - set(market_data.columns)
    if missing:
        raise ValueError(f"market_data missing columns: {sorted(missing)}")

    market_data = market_data.copy()
    market_data["date"] = pd.to_datetime(market_data["date"])
    market_data.sort_values(["asset_id", "date"], inplace=True)

    returns: dict[str, pd.Series] = {}
    for asset_id, group in market_data.groupby("asset_id"):
        series = group.set_index("date")["return_1d"]
        returns[asset_id] = series
    return returns


def _compute_cumulative_return(series: pd.Series, event_date: pd.Timestamp, window: Window) -> float | None:
    """Return cumulative return for a series in the provided window or None if invalid."""
    start_offset, end_offset = window
    if start_offset > end_offset:
        raise ValueError(f"Invalid window {window}: start_offset > end_offset")

    if event_date not in series.index:
        return None

    pos = series.index.get_loc(event_date)
    start_pos = pos + start_offset
    end_pos = pos + end_offset
    if start_pos < 0 or end_pos >= len(series):
        return None

    window_slice = series.iloc[start_pos : end_pos + 1]
    if window_slice.isna().any():
        return None

    cumulative_return = (1 + window_slice).prod() - 1
    return float(cumulative_return)


def _format_window(window: Window) -> str:
    return f"{window[0]}_{window[1]}"


def _global_window_bounds(windows: Sequence[Window]) -> Window:
    mins = [w[0] for w in windows]
    maxs = [w[1] for w in windows]
    return min(mins), max(maxs)


def run_event_study(
    market_data: pd.DataFrame,
    events: pd.DataFrame,
    event_windows: Sequence[Window],
    output_dir: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Compute event study statistics and persist outputs.

    Returns (summary_df, detail_df).
    """

    if "event_id" not in events.columns or "event_type" not in events.columns:
        raise ValueError("events must include event_id and event_type")

    date_col = "trading_date" if "trading_date" in events.columns else "release_date"
    if date_col not in events.columns:
        raise ValueError("events must include trading_date or release_date")

    if output_dir is None:
        output_dir = get_settings().output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = output_dir / "event_study_plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    market_returns = _prepare_market_returns(market_data)

    events = events.copy()
    events[date_col] = pd.to_datetime(events[date_col])

    detail_rows = []
    for _, event in events.iterrows():
        event_date = event[date_col]
        event_id = event["event_id"]
        event_type = event["event_type"]

        for asset_id, series in market_returns.items():
            for window in event_windows:
                cum_ret = _compute_cumulative_return(series, event_date, window)
                if cum_ret is None:
                    continue
                detail_rows.append(
                    {
                        "event_id": event_id,
                        "event_type": event_type,
                        "asset_id": asset_id,
                        "window": _format_window(window),
                        "start_offset": window[0],
                        "end_offset": window[1],
                        "cumulative_return": cum_ret,
                    }
                )

    detail_df = pd.DataFrame(detail_rows)
    if not detail_df.empty:
        summary_df = (
            detail_df.groupby(["event_type", "asset_id", "window"])
            .agg(
                mean=("cumulative_return", "mean"),
                median=("cumulative_return", "median"),
                std=("cumulative_return", "std"),
                n=("cumulative_return", "count"),
                pct_positive=("cumulative_return", lambda x: (x > 0).mean() * 100),
            )
            .reset_index()
        )
    else:
        summary_df = pd.DataFrame(
            columns=["event_type", "asset_id", "window", "mean", "median", "std", "n", "pct_positive"]
        )

    summary_path = output_dir / "event_study_summary.csv"
    detail_path = output_dir / "event_study_details.csv"
    summary_df.to_csv(summary_path, index=False)
    detail_df.to_csv(detail_path, index=False)
    logger.info("Saved event study summary to %s", summary_path)
    logger.info("Saved event study details to %s", detail_path)

    _plot_average_curves(detail_df, market_returns, events, event_windows, date_col, plots_dir)

    return summary_df, detail_df


def _plot_average_curves(
    detail_df: pd.DataFrame,
    market_returns: dict[str, pd.Series],
    events: pd.DataFrame,
    event_windows: Sequence[Window],
    date_col: str,
    plots_dir: Path,
) -> None:
    """Plot per-event average cumulative return curves grouped by event/asset."""
    if detail_df.empty:
        logger.warning("No detail rows to plot.")
        return

    min_offset, max_offset = _global_window_bounds(event_windows)
    offsets = list(range(min_offset, max_offset + 1))

    for (event_type, asset_id), _ in detail_df.groupby(["event_type", "asset_id"]):
        series = market_returns.get(asset_id)
        if series is None:
            continue

        curves: dict[int, list[float]] = {offset: [] for offset in offsets}

        for _, event in events[events["event_type"] == event_type].iterrows():
            event_date = pd.to_datetime(event[date_col])
            if event_date not in series.index:
                continue

            pos = series.index.get_loc(event_date)
            start_pos = pos + min_offset
            end_pos = pos + max_offset
            if start_pos < 0 or end_pos >= len(series):
                continue

            window_slice = series.iloc[start_pos : end_pos + 1]
            if window_slice.isna().any():
                continue

            cum_returns = (1 + window_slice).cumprod() - 1
            for idx, offset in enumerate(offsets):
                curves[offset].append(float(cum_returns.iloc[idx]))

        # Skip plotting if no data
        if not any(curves[offset] for offset in offsets):
            continue

        avg_curve = {offset: (pd.Series(vals).mean() if vals else None) for offset, vals in curves.items()}
        xs = list(avg_curve.keys())
        ys = [avg_curve[x] for x in xs]

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(xs, ys, marker="o")
        ax.axvline(0, color="gray", linestyle="--", linewidth=1, label="Event day")
        ax.set_title(f"Average cumulative returns: {event_type} - {asset_id}")
        ax.set_xlabel("Days relative to event")
        ax.set_ylabel("Cumulative return")
        ax.grid(True, linestyle="--", alpha=0.4)
        ax.legend()
        plt.tight_layout()

        out_path = plots_dir / f"{event_type}_{asset_id}.png"
        fig.savefig(out_path)
        plt.close(fig)
        logger.info("Saved event study plot to %s", out_path)


if __name__ == "__main__":
    # Example manual run (expects preloaded market_data and events DataFrames)
    setup_logging()
    logger.info("Event study module executed directly. Import and call run_event_study in code.")
