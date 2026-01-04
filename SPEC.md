# Macro Cross-Asset Analytics Platform – Scope

## Goals
- Provide a structured, production-friendly Python 3.11 codebase to analyze macro and cross-asset market data.
- Clean separation of concerns: ingest (data access), analytics (transformations + metrics), viz (plots), and UI (CLI orchestration).
- Configurable tickers, FRED series, date windows, and output paths through Pydantic settings/env vars.

## Ingest
- Input: CSV of macro/market events (sample in `data/sample_events.csv`).
- Extensible interfaces for future data sources (FRED, market data APIs, cloud storage).

## Analytics
- Baseline: event counts by ticker/event type as a placeholder for richer calculations.
- Future: factor returns, macro sensitivity, rolling correlations, anomaly detection, scenario/risk simulations.

## Visualization
- Baseline: static matplotlib chart of event counts per ticker, saved under `outputs/`.
- Future: richer chart library (Plotly/Altair), dashboards, and report generation (PDF/HTML).

## UI / Orchestration
- Typer CLI to run the pipeline end-to-end and display configuration.
- Entry module: `python -m macro_platform.app run`.

## Non-Goals (for now)
- Production data pipelines or job scheduling.
- Authentication/authorization for external data providers.
- Persistence layers (databases, data lake) and deployment automation.

## Quality & Tooling
- Dependency management with uv; dev tools include Ruff, Pytest, optional Mypy.
- Makefile tasks for install, lint, format, typecheck, test, run.
