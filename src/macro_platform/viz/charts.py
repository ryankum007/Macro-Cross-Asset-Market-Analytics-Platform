"""Reusable plotting utilities for the macro platform."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

Window = tuple[int, int]


def event_study_cumret_plot(
    market_data: pd.DataFrame,
    events: pd.DataFrame,
    event_windows: Sequence[Window],
    asset_id: str,
    event_type: str,
    date_col: str = "trading_date",
    ax: plt.Axes | None = None,
) -> plt.Figure:
    """Plot average cumulative returns around events for a specific asset and event type."""

    from macro_platform.analytics.event_study import _global_window_bounds, _prepare_market_returns

    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 4))
    else:
        fig = ax.figure

    market_returns = _prepare_market_returns(market_data)
    if asset_id not in market_returns:
        raise ValueError(f"asset_id {asset_id} not found in market_data")

    events = events.copy()
    events[date_col] = pd.to_datetime(events[date_col])
    min_offset, max_offset = _global_window_bounds(event_windows)
    offsets = list(range(min_offset, max_offset + 1))
    curves: dict[int, list[float]] = {off: [] for off in offsets}

    series = market_returns[asset_id]
    for _, ev in events[events["event_type"] == event_type].iterrows():
        event_date = ev[date_col]
        if event_date not in series.index:
            continue
        pos = series.index.get_loc(event_date)
        start = pos + min_offset
        end = pos + max_offset
        if start < 0 or end >= len(series):
            continue
        window_slice = series.iloc[start : end + 1]
        if window_slice.isna().any():
            continue
        cum = (1 + window_slice).cumprod() - 1
        for idx, off in enumerate(offsets):
            curves[off].append(float(cum.iloc[idx]))

    if not any(curves.values()):
        logger.warning("No event study data to plot for %s / %s", asset_id, event_type)
        return fig

    avg_curve = {off: (np.mean(vals) if vals else np.nan) for off, vals in curves.items()}
    xs = list(avg_curve.keys())
    ys = [avg_curve[x] for x in xs]
    ax.plot(xs, ys, marker="o")
    ax.axvline(0, color="gray", linestyle="--", linewidth=1, label="Event day")
    ax.set_title(f"Avg cumulative returns: {event_type} - {asset_id}")
    ax.set_xlabel("Days relative to event")
    ax.set_ylabel("Cumulative return")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend()
    return fig


def yield_curve_plot(
    base_curve: dict[str, float],
    shocked_curve: dict[str, float],
    scenario_name: str,
    magnitude_bps: float,
    ax: plt.Axes | None = None,
) -> plt.Figure:
    """Plot base vs shocked yield curve."""

    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 4))
    else:
        fig = ax.figure

    tenors = np.array([2, 5, 10, 30], dtype=float)
    base = np.array([base_curve["2Y"], base_curve["5Y"], base_curve["10Y"], base_curve["30Y"]])
    shocked = np.array(
        [shocked_curve["2Y"], shocked_curve["5Y"], shocked_curve["10Y"], shocked_curve["30Y"]]
    )

    ax.plot(tenors, base, marker="o", label="Base")
    ax.plot(tenors, shocked, marker="o", label=f"{scenario_name} ({magnitude_bps}bps)")
    ax.set_xlabel("Tenor (years)")
    ax.set_ylabel("Yield (%)")
    ax.set_title(f"Yield Curve: {scenario_name}")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    return fig


def correlation_heatmap(corr: pd.DataFrame, ax: plt.Axes | None = None) -> plt.Figure:
    """Correlation heatmap."""

    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 5))
    else:
        fig = ax.figure

    im = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(corr.index)))
    ax.set_yticklabels(corr.index)
    ax.set_title("Correlation heatmap")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    return fig


def rolling_correlation_plot(
    corr_df: pd.DataFrame, pair: str, ax: plt.Axes | None = None
) -> plt.Figure:
    """Plot rolling correlations for a single pair (pair format 'a__b')."""

    subset = corr_df[corr_df["pair"] == pair]
    if subset.empty:
        raise ValueError(f"No rolling correlations found for pair {pair}")

    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 4))
    else:
        fig = ax.figure

    for window, group in subset.groupby("window"):
        ax.plot(group["date"], group["rolling_corr"], label=f"{window}d")
    anomalies = subset[subset["anomaly"]]
    if not anomalies.empty:
        ax.scatter(anomalies["date"], anomalies["rolling_corr"], color="red", label="Anomaly")

    ax.set_title(f"Rolling correlation: {pair}")
    ax.set_ylabel("Correlation")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend()
    return fig


def regime_timeline_plot(regimes: pd.DataFrame, ax: plt.Axes | None = None) -> plt.Figure:
    """Plot a simple regime timeline (risk_on/off)."""

    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 2.5))
    else:
        fig = ax.figure

    regimes = regimes.copy()
    regimes = regimes.sort_values("date")
    regimes["regime_flag"] = np.where(regimes["regime"] == "risk_off", 1, 0)

    ax.step(regimes["date"], regimes["regime_flag"], where="post", label="Risk-off=1, Risk-on=0")
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["risk_on", "risk_off"])
    ax.set_title("Regime timeline")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend()
    return fig


def save_fig(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
