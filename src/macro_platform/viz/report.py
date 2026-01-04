"""Report generator that runs analytics and produces plots/CSVs."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from datetime import date
from pathlib import Path

import pandas as pd

from macro_platform.analytics.cross_asset import run_cross_asset_analytics
from macro_platform.analytics.event_study import run_event_study

try:
    from macro_platform.analytics.yield_curve import (
        apply_scenario,
        build_curve_from_fred,
        run_yield_curve_scenarios,
    )
except ImportError:
    from macro_platform.analytics.yield_curve import (
        _apply_scenario as apply_scenario,
    )
    from macro_platform.analytics.yield_curve import (
        build_curve_from_fred,
        run_yield_curve_scenarios,
    )
from macro_platform.config import Settings, get_settings
from macro_platform.ingest.events import load_events, map_to_trading_day
from macro_platform.ingest.fred import download_fred_series
from macro_platform.ingest.market_data import download_market_data
from macro_platform.logging_utils import setup_logging
from macro_platform.viz.charts import (
    correlation_heatmap,
    event_study_cumret_plot,
    regime_timeline_plot,
    rolling_correlation_plot,
    save_fig,
    yield_curve_plot,
)

logger = logging.getLogger(__name__)

EventWindow = tuple[int, int]


def generate_report(
    start_date: date | None = None,
    end_date: date | None = None,
    event_windows: Sequence[EventWindow] = ((-1, 3), (-3, 5), (0, 1)),
    scenarios: Iterable[tuple[str, float]] = (
        ("parallel", 25),
        ("steepener", 20),
        ("flattener", 20),
    ),
    output_dir: Path | None = None,
) -> None:
    """Run end-to-end analytics and save plots/CSVs to outputs/."""

    settings: Settings = get_settings()
    out_dir = output_dir or settings.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = out_dir / "report_plots"

    # Dates
    start = start_date or settings.date_range.start_date
    end = end_date or settings.date_range.end_date

    logger.info("Running report from %s to %s", start, end)

    # Data ingestion
    market_data = download_market_data(start, end)
    fred_df = download_fred_series(start, end)

    events_path = settings.data_dir / "events.csv"
    events_df = load_events(events_path)
    calendar = pd.to_datetime(market_data["date"].unique())
    mapped_events = map_to_trading_day(events_df, calendar)

    # Event study
    run_event_study(market_data, mapped_events, event_windows=event_windows, output_dir=out_dir)
    # Plot example event study curve for CPI / sp500
    fig = event_study_cumret_plot(
        market_data, mapped_events, event_windows, asset_id="sp500", event_type="CPI"
    )
    save_fig(fig, plots_dir / "event_study_cumret.png")

    # Yield curve scenarios
    as_of = pd.to_datetime(fred_df.dropna().index.max()).date()
    run_yield_curve_scenarios(fred_df, as_of, scenarios=scenarios, output_dir=out_dir)
    base_curve = build_curve_from_fred(fred_df, as_of)
    scenario_name, magnitude = next(iter(scenarios))
    shocked_curve = apply_scenario(base_curve, scenario_name, magnitude)
    fig = yield_curve_plot(base_curve, shocked_curve, scenario_name, magnitude)
    save_fig(fig, plots_dir / "yield_curve.png")

    # Cross-asset analytics
    cross = run_cross_asset_analytics(market_data, fred_df, output_dir=out_dir)
    corr_df = cross["rolling_correlations"]
    static_corr = cross["static_correlations"]
    regimes = cross["regimes"]

    fig = correlation_heatmap(static_corr)
    save_fig(fig, plots_dir / "correlation_heatmap.png")

    if not corr_df.empty:
        target_pair = corr_df["pair"].iloc[0]
        fig = rolling_correlation_plot(corr_df, target_pair)
        save_fig(fig, plots_dir / "rolling_correlation.png")

    if not regimes.empty:
        fig = regime_timeline_plot(regimes)
        save_fig(fig, plots_dir / "regime_timeline.png")

    logger.info("Report generation completed. Outputs in %s", out_dir)


if __name__ == "__main__":
    setup_logging()
    generate_report()
