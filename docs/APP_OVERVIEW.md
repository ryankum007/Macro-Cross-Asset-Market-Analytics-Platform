Macro Cross-Asset Market Analytics Platform - System Overview
=============================================================

Purpose
-------
This project is a Python analytics platform for measuring how macro events
(CPI, NFP, FOMC) impact markets across equities, FX, rates, and volatility.
It ingests real-world data, runs analytics, and presents results in a
Streamlit UI.

High-Level Flow
---------------
1) Ingest
   - Market data from yfinance (equities, FX, volatility).
   - Rates and macro series from FRED.
   - Event calendar from CSV.
2) Analytics
   - Event study (cumulative returns around events).
   - Yield curve scenarios and bond risk measures.
   - Cross-asset correlations, PCA, regimes, anomalies.
3) Visualization + UI
   - Matplotlib charts saved to outputs/.
   - Streamlit app for interactive exploration.

Data Sources and Meaning
------------------------
Market data (yfinance)
- Assets tracked (by default): sp500, nasdaq, eurusd, vix
- Columns:
  - date: business day
  - asset_id: logical asset name
  - close, adj_close: prices
  - return_1d: daily percent return based on close
- Implementation: src/macro_platform/ingest/market_data.py
- Cache: data/cache/*.parquet (created on first run)

Rates and macro series (FRED)
- Series: DGS2, DGS5, DGS10, DGS30 (Treasury yields), CPIAUCSL
- Yield levels are percent.
- Computed columns: DGS*_chg_bps = daily change in basis points.
- Implementation: src/macro_platform/ingest/fred.py
- Forward fill:
  - Yields: forward fill up to 2 business days (limited).
  - CPI: forward fill without limit (monthly series).

Event calendar (CSV)
- Main app uses data/events.csv with:
  - event_id, event_type, release_date, notes (notes optional).
  - event_type allowed: CPI, NFP, FOMC
- Events are mapped to the next available trading day for analysis.
- Implementation: src/macro_platform/ingest/events.py

CLI sample data
- The CLI demo uses data/sample_events.csv with columns:
  - date, ticker, event, impact
- This is a separate, lightweight example dataset for the CLI only.
- Implementation: src/macro_platform/ingest/csv_loader.py

Analytics Modules (What They Do)
--------------------------------
Event Study
- File: src/macro_platform/analytics/event_study.py
- Goal: quantify average cumulative return around event dates.
- Inputs: market_data (returns), events (with trading_date), windows.
- Output:
  - outputs/event_study_summary.csv
  - outputs/event_study_details.csv
- Logic:
  - For each event and asset, compute cumulative return over each window.
  - Aggregate mean/median/std, count, percent positive.

Yield Curve Scenarios
- File: src/macro_platform/analytics/yield_curve.py
- Goal: simulate curve shocks and quantify bond risk.
- Scenarios: parallel, steepener, flattener, twist (in basis points).
- Outputs:
  - outputs/yield_curve_scenarios.csv
  - outputs/yield_curve_pnl.csv
- Risk measures:
  - DV01, modified duration, convexity via finite differences.

Cross-Asset Analytics
- File: src/macro_platform/analytics/cross_asset.py
- Goal: measure correlations, factor exposure, and regimes.
- Steps:
  - Build wide returns table and add rates_factor (DGS10_chg_bps).
  - Rolling correlations for asset pairs.
  - PCA loadings on standardized returns.
  - Regime detection using SP500 and VIX 5-day moves.
- Outputs:
  - outputs/rolling_correlations.csv
  - outputs/static_correlations.csv
  - outputs/pca_loadings.csv
  - outputs/regimes.csv

Visuals and Reports
-------------------
- Chart helpers: src/macro_platform/viz/charts.py
- Report generator: src/macro_platform/viz/report.py
- Saved plots:
  - outputs/event_study_plots/*.png
  - outputs/yield_curve_plots/*.png
  - outputs/correlation_plots/*.png
  - outputs/report_plots/*.png

UI (Streamlit)
--------------
Entry point: src/macro_platform/ui/app.py

Pages
1) Dashboard Overview
   - Data coverage, last date, event calendar preview.
2) Macro Event Impact
   - Event study controls and outputs.
3) Yield Curve Scenarios
   - Scenario inputs, chart, and table of yields.
4) Correlations & Regimes
   - Heatmap, rolling correlations, PCA, regime timeline.

Caching
- Streamlit caches ingestion and analytics to avoid repeated downloads.
- You can clear cached data from the sidebar.

Configuration
-------------
- Settings are in src/macro_platform/config.py
- Defaults can be overridden with environment variables:
  - Prefix: MACRO_
  - Example: MACRO_LOGGING_LEVEL=DEBUG
  - Example: MACRO_DATE_RANGE__START_DATE=2020-01-01

Design Decisions (Why)
----------------------
- No forward fill for market prices:
  Prevents artificial smoothing of returns and keeps gaps honest.
- Map events to trading days:
  A release can occur on non-trading days; mapping avoids missing windows.
- Daily data only:
  Keeps scope small and stable for a demo platform.

Limitations
-----------
- Daily frequency only (no intraday reaction modeling).
- yfinance and FRED are convenient but can have outages or gaps.
- CLI sample dataset is small and not meant for production analysis.

How to Explain This to a Recruiter or Dev
-----------------------------------------
- The project cleanly separates ingest, analytics, visualization, and UI.
- It uses real market data to quantify macro event impact and rates risk.
- Event studies are computed per asset and window with transparent outputs.
- Yield curve scenarios quantify interest-rate risk via DV01/duration/convexity.
- Cross-asset analytics highlight correlation shifts and regimes.

Quick Runbook
-------------
- Install deps: uv sync
- Run pipeline (CLI): uv run python -m macro_platform.app run
- Launch UI: streamlit run src/macro_platform/ui/app.py
- Full demo: ./scripts/run_all.sh
