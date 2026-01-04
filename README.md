# Macro Cross-Asset Market Analytics Platform

Production-ready Python 3.11 skeleton for ingesting macro events, running analytics, and producing lightweight visualizations with a clear separation between ingest, analytics, viz, and UI layers.

## Prerequisites
- Python 3.11
- [uv](https://docs.astral.sh/uv/) installed (`pip install uv` if needed)

## Setup
```bash
uv sync
```
This creates a virtual environment, installs runtime + dev dependencies, and pins them in `uv.lock` (generated on first sync).

## Usage
Run the full pipeline (ingest -> analytics -> viz) against the bundled sample events:
```bash
uv run python -m macro_platform.app run
```
Launch the Streamlit demo UI:
```bash
streamlit run src/macro_platform/ui/app.py
```
Show active configuration (including tickers, FRED series, paths):
```bash
uv run python -m macro_platform.app config
```

### One-command demo
```bash
./scripts/run_all.sh
```
Syncs deps with uv, builds analytics outputs, and launches the Streamlit UI.

## Deployment
- Docker: `docker build -t macro-platform .` then `docker run -p 8501:8501 macro-platform`.
- GitHub Actions CI runs lint and tests via uv (see `.github/workflows/ci.yml`).
- Streamlit Community Cloud: point to `src/macro_platform/ui/app.py`, set Python 3.11, run `pip install uv && uv sync && streamlit run src/macro_platform/ui/app.py`. Ensure `data/events.csv` is present (already tracked) and no secrets required. If providing a FRED API key, set env var `FRED_API_KEY`; otherwise pandas_datareader uses public access where available.

## Limitations
- Uses daily data; intraday reactions are not captured.
- Sample data is minimal and uses yfinance/FRED; outages or throttling may limit coverage.

## Future work
- Intraday event reaction analysis and volatility decay modeling.
- Surprise vs. forecast analytics, including consensus data ingestion.
- Richer dashboards (Plotly), portfolio impact, and scenario comparison.

## Makefile shortcuts
- `make install` – sync environment with uv
- `make lint` – `ruff check .`
- `make format` – `ruff format .`
- `make typecheck` – `mypy src`
- `make test` – `pytest`
- `make run` – run the CLI pipeline

## Project layout
```
src/macro_platform/
  config.py          # Pydantic settings (tickers, FRED series, dates, paths)
  logging_utils.py   # Logging setup
  ingest/            # Data loaders (CSV, APIs, yfinance market data)
  analytics/         # Metrics & factor calculations
  viz/               # Plotting helpers
  ui/cli.py          # Typer CLI entrypoints
  app.py             # Module entrypoint

data/                # Local datasets (gitignored except sample_events.csv)
                     # Includes events.csv calendar for macro releases
outputs/             # Generated charts/reports (gitignored)
```

## Configuration
- Defaults are in `src/macro_platform/config.py` and can be overridden via environment variables prefixed with `MACRO_`, e.g. `MACRO_LOGGING_LEVEL=DEBUG` or `MACRO_MARKET__TICKERS="[\"SPY\", \"QQQ\"]"`.
- Output and data directories are created on startup if missing.
- FRED API key is optional; set `FRED_API_KEY` if you want authenticated requests, otherwise public access is used where available.

## Testing & Quality
- Ruff is used for linting and formatting.
- Mypy is configured (non-strict) for optional type checking.
- Pytest drives tests in `tests/`.

## Next steps
- Extend ingest to pull live data (FRED, market data APIs).
- Add richer analytics (factor models, correlations, regime detection).
- Build dashboards in `macro_platform.ui` using your preferred framework.
