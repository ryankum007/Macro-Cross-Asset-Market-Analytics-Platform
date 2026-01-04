"""Streamlit application to demo the macro platform end-to-end."""

# ruff: noqa: E402, E501

from __future__ import annotations

import io

# Ensure src/ is on path when run via `streamlit run`
import sys
import zipfile
from datetime import date
from pathlib import Path

PROJECT_SRC = Path(__file__).resolve().parents[2]
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

import pandas as pd
import streamlit as st

from macro_platform.analytics.cross_asset import run_cross_asset_analytics
from macro_platform.analytics.event_study import run_event_study

try:
    from macro_platform.analytics.yield_curve import (
        BondSpec,
        apply_scenario,
        build_curve_from_fred,
        run_yield_curve_scenarios,
    )
except ImportError:
    from macro_platform.analytics.yield_curve import (
        BondSpec,
        build_curve_from_fred,
        run_yield_curve_scenarios,
    )
    from macro_platform.analytics.yield_curve import (
        _apply_scenario as apply_scenario,
    )
from macro_platform.config import Settings, get_settings
from macro_platform.ingest.events import load_events, map_to_trading_day
from macro_platform.ingest.fred import download_fred_series
from macro_platform.ingest.market_data import ASSET_METADATA, download_market_data
from macro_platform.viz.charts import (
    correlation_heatmap,
    event_study_cumret_plot,
    regime_timeline_plot,
    rolling_correlation_plot,
    yield_curve_plot,
)

st.set_page_config(page_title="Macro Cross-Asset Analytics", page_icon="📈", layout="wide", initial_sidebar_state="expanded")


# ---------- Caching ----------
@st.cache_data(show_spinner=False)
def load_data(start: date, end: date):
    market = download_market_data(start, end)
    fred = download_fred_series(start, end)
    events = load_events(get_settings().data_dir / "events.csv")
    calendar = pd.to_datetime(market["date"].unique())
    mapped_events = map_to_trading_day(events, calendar)
    return market, fred, mapped_events


@st.cache_data(show_spinner=False)
def cached_event_study(market, events, event_windows):
    return run_event_study(market, events, event_windows=event_windows, output_dir=get_settings().output_dir)


@st.cache_data(show_spinner=False)
def cached_yield_scenarios(fred_df, as_of, scenarios, bond: BondSpec):
    # run_yield_curve_scenarios saves outputs; we also return base/shocked for plotting
    run_yield_curve_scenarios(fred_df, as_of, scenarios=scenarios, bond=bond, output_dir=get_settings().output_dir)
    base_curve = build_curve_from_fred(fred_df, as_of)
    scenario_name, magnitude = next(iter(scenarios))
    shocked_curve = apply_scenario(base_curve, scenario_name, magnitude)
    return base_curve, shocked_curve


@st.cache_data(show_spinner=False)
def cached_cross_asset(market, fred, windows):
    return run_cross_asset_analytics(market, fred, windows=windows, output_dir=get_settings().output_dir)


def _apply_theme():
    st.markdown(
        """
        <style>
        :root {
            --brand: #111827;
            --accent: #2563eb;
            --muted: #4b5563;
            --bg: #f8fafc;
            --panel: #ffffff;
            --border: #e5e7eb;
            --shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        }
        body, .stApp {
            background: var(--bg) !important;
            color: var(--brand);
            font-family: "SF Pro Display", "SF Pro Text", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        header[data-testid="stHeader"] {
            background: var(--bg) !important;
            border-bottom: 1px solid var(--border) !important;
            z-index: 1001;
        }
        .block-container { padding: 2rem 2.4rem 3rem; }
        .app-hero {
            display: flex;
            gap: 2rem;
            padding: 1.5rem 1.75rem;
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 18px;
            box-shadow: var(--shadow);
            align-items: center;
        }
        .app-hero h1 { margin: 0; font-size: 2rem; color: var(--brand); letter-spacing: -0.01em; }
        .hero-copy { color: var(--muted); margin-top: 0.35rem; }
        .hero-pill { display: inline-block; padding: 0.32rem 0.65rem; border-radius: 999px; background: #eef1f7; color: var(--brand); font-weight: 700; font-size: 0.82rem; letter-spacing: 0.02em; }
        .badge { display: inline-block; padding: 0.32rem 0.55rem; border-radius: 999px; border: 1px solid var(--border); margin-right: 0.4rem; color: var(--muted); background: #f8fafc; font-size: 0.82rem; }
        .badge.accent { border-color: rgba(0, 122, 255, 0.2); color: #0f172a; background: rgba(0, 122, 255, 0.08); }
        .hero-right { min-width: 240px; }
        .hero-card {
            background: linear-gradient(135deg, rgba(0, 122, 255, 0.08), rgba(255, 255, 255, 0.94));
            padding: 1rem 1.25rem;
            border-radius: 14px;
            border: 1px solid var(--border);
            box-shadow: var(--shadow);
        }
        .hero-label { color: var(--muted); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.06em; }
        .hero-value { font-size: 1.6rem; font-weight: 700; color: var(--brand); line-height: 1.1; }
        .hero-meta { color: var(--muted); font-size: 0.9rem; }
        .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem; margin-top: 1rem; }
        .metric-card {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 0.85rem 1rem;
            box-shadow: var(--shadow);
        }
        .metric-card .label { color: var(--muted); font-size: 0.9rem; }
        .metric-card .value { font-size: 1.4rem; font-weight: 700; color: var(--brand); }
        .section-card {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1rem 1.2rem;
            box-shadow: var(--shadow);
        }
        .section-title { font-weight: 700; color: #0f172a; }
        .stTabs [data-baseweb="tab-list"] { gap: 0.35rem; }
        .stTabs [data-baseweb="tab"] {
            background: #f3f4f6;
            padding: 0.8rem 1rem;
            border-radius: 10px 10px 0 0;
            border: 1px solid var(--border);
            color: var(--muted);
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            color: var(--brand);
            border-bottom-color: #fff;
            background: #ffffff;
        }
        /* Ensure all widget labels and headings are readable */
        label[data-testid="stWidgetLabel"],
        [data-testid="stCaptionContainer"],
        .stMarkdown p,
        .stMarkdown span,
        .stMarkdown li,
        h1, h2, h3, h4, h5, h6 {
            color: var(--brand) !important;
        }
        .hero-copy { color: var(--muted) !important; }
        /* Metric text */
        [data-testid="stMetricValue"], [data-testid="stMetricDelta"], [data-testid="stMetricLabel"] {
            color: var(--brand) !important;
        }
        /* Light chips */
        [data-baseweb="tag"] {
            background: #e8ecf4 !important;
            color: var(--brand) !important;
            border-radius: 12px !important;
            border: 1px solid #d9dde4 !important;
        }
        .stButton>button, .stDownloadButton>button {
            background: #ffffff;
            color: var(--brand);
            border: 1px solid #d1d5db;
            border-radius: 10px;
            padding: 0.5rem 0.9rem;
            font-weight: 600;
            box-shadow: none;
        }
        .stButton>button:hover, .stDownloadButton>button:hover { background: #f3f4f6; }
        .stDownloadButton>button { width: 100%; }
        .callout {
            padding: 0.9rem 1rem;
            border-radius: 12px;
            border: 1px solid var(--border);
            background: #f5f7fb;
            color: var(--muted);
        }
        /* Inputs on light background */
        .stTextInput>div>div>input,
        .stDateInput>div>div>input,
        .stSelectbox>div>div>div>input {
            background: #ffffff !important;
            color: var(--brand);
            border: 1px solid #d7d9df;
            border-radius: 10px;
        }
        [data-baseweb="select"] > div {
            background: #ffffff;
            border: 1px solid #d7d9df;
            border-radius: 10px;
            color: var(--brand);
        }
        /* Ensure select labels/options stay dark */
        .stSelectbox label, .stMultiselect label { color: var(--brand) !important; }
        [data-baseweb="select"] * { color: var(--brand) !important; }
        ul[role="listbox"] li { color: var(--brand) !important; background: #ffffff !important; }
        div[role="listbox"] div { color: var(--brand) !important; }
        .css-1yk1gt9 option { color: var(--brand) !important; }
        [data-baseweb="tag"] * { color: var(--brand) !important; }
        /* Sidebar */
        [data-testid="stSidebar"] {
            background: #f3f4f6 !important;
            border-right: 1px solid var(--border) !important;
        }
        [data-testid="stSidebar"] * { color: var(--brand) !important; }
        [data-testid="stSidebar"] input { background: #ffffff !important; color: var(--brand) !important; }
        [data-testid="stSidebar"] .stButton>button,
        [data-testid="stSidebar"] .stDownloadButton>button { color: var(--brand); background: #ffffff; border: 1px solid #d1d5db; }
        /* Force readable labels across widgets */
        .stTextInput *, .stNumberInput *, .stSelectbox *, .stMultiselect *, .stDateInput *, .stSlider * {
            color: var(--brand) !important;
        }
        .header-brand {
            position: fixed;
            top: 0.25rem;
            left: 0.75rem;
            z-index: 1000;
            display: inline-flex;
            align-items: center;
            gap: 0.6rem;
            padding: 0.25rem 0.6rem;
            border-radius: 999px;
            background: #ffffff;
            border: 1px solid var(--border);
        }
        .header-brand .brand-mark {
            width: 28px;
            height: 28px;
            font-size: 0.8rem;
            margin-right: 0;
        }
        .header-brand .brand-title {
            font-weight: 600;
            color: var(--brand);
            font-size: 0.9rem;
        }
        .header-title {
            position: fixed;
            top: 0.2rem;
            left: 50%;
            transform: translateX(-50%);
            z-index: 1002;
            font-weight: 600;
            color: var(--brand);
            font-size: 1.1rem;
            line-height: 2.4rem;
            height: 2.4rem;
            pointer-events: none;
        }
        .brand-mark {
            width: 46px;
            height: 46px;
            border-radius: 50%;
            background: #e6ebf5;
            color: var(--brand);
            border: 1px solid var(--border);
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            letter-spacing: 0.02em;
            margin-right: 0.75rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _sidebar_controls(settings: Settings):
    st.sidebar.header("Global Controls")
    start = st.sidebar.date_input("Start date", value=settings.date_range.start_date)
    end = st.sidebar.date_input("End date", value=settings.date_range.end_date)
    if start > end:
        st.sidebar.error("Start date must be before end date")
    refresh = st.sidebar.button("Refresh data (clear cache)")
    if refresh:
        st.cache_data.clear()
        st.rerun()

    export = st.sidebar.button("Export outputs to zip")
    if export:
        zip_bytes = _zip_outputs(get_settings().output_dir)
        st.sidebar.download_button(
            "Download outputs.zip",
            data=zip_bytes.getvalue(),
            file_name="outputs.zip",
            mime="application/zip",
        )
    return start, end


def _zip_outputs(out_dir: Path) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if out_dir.exists():
            for path in out_dir.rglob("*"):
                if path.is_file():
                    zf.write(path, path.relative_to(out_dir))
    buf.seek(0)
    return buf


def _hero(market: pd.DataFrame):
    dates = pd.to_datetime(market["date"])
    last_date = dates.max().date()
    first_date = dates.min().date()
    st.markdown(
        f"""
        <div class="app-hero">
            <div class="hero-left">
                <div style="display:flex;align-items:center;gap:0.4rem;margin-bottom:0.25rem;">
                    <div class="brand-mark">RK</div>
                    <div style="display:flex;flex-direction:column;">
                        <span class="hero-pill">Market Analytics</span>
                        <span style="color: var(--muted); font-size: 0.85rem; margin-top: 0.15rem;">Developed by Ryan Kumar</span>
                    </div>
                </div>
                <h1>Macro Cross-Asset-Market Analytics Platform</h1>
                <div class="hero-copy">
                    This platform analyzes how major US macroeconomic events like CPI, NFP, and FOMC decisions impact equities, FX, rates, and volatility. It combines event studies, yield-curve scenario analysis, and cross-asset correlation analytics to reveal market regimes and risk dynamics.
                </div>
                <div style="margin-top: 0.6rem;">
                    <span class="badge accent">Events → Markets → Analytics</span>
                    <span class="badge">Python · uv · Streamlit</span>
                </div>
            </div>
            <div class="hero-right">
                <div class="hero-card">
                    <div class="hero-label">Data through</div>
                    <div class="hero-value">{last_date}</div>
                    <div class="hero-meta">Coverage: {first_date} → {last_date}<br/>{len(market):,} rows · {len(ASSET_METADATA)} assets</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="metric-grid">
            <div class="metric-card">
                <div class="label">Assets tracked</div>
                <div class="value">Equity, FX, Vol</div>
                <div class="label">""" + ", ".join(sorted(ASSET_METADATA.keys())) + """</div>
            </div>
            <div class="metric-card">
                <div class="label">Event types</div>
                <div class="value">CPI · NFP · FOMC</div>
                <div class="label">Mapped to next trading day</div>
            </div>
            <div class="metric-card">
                <div class="label">Data quality</div>
                <div class="value">No forward fill</div>
                <div class="label">Raw gaps preserved for honest analytics</div>
            </div>
            <div class="metric-card">
                <div class="label">Export</div>
                <div class="value">Outputs.zip</div>
                <div class="label">Grab from sidebar after a run</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _header_brand():
    st.markdown(
        """
        <style>
        .header-title {
            text-align: center;
            width: 100%;
            font-size: 36px;
            font-weight: 600;
            margin-top: 0.6rem;
        }
        </style>

        <div class="header-brand">
            <div class="brand-mark">RK</div>
        </div>

        <div class="header-title">
            Macro Cross-Asset-Market Analytics Platform
        </div>
        """,
        unsafe_allow_html=True
    )



def page_overview(market: pd.DataFrame, events: pd.DataFrame, settings: Settings):
    st.title("Dashboard Overview")
    st.write("High-level snapshot of data coverage, freshness, and calendar health.")

    dates = pd.to_datetime(market["date"])
    last_date = dates.max().date()
    first_date = dates.min().date()
    trading_days = dates.nunique()
    rows = len(market)

    st.markdown(
        f"""
        <div class="section-card">
            <div class="section-title">Coverage</div>
            <p class="hero-copy" style="margin: 0.25rem 0 0.5rem 0;">Business-day aligned prices with cached downloads under <code>{settings.data_dir}/cache</code>.</p>
            <div class="metric-grid" style="margin-top: 0.35rem;">
                <div class="metric-card"><div class="label">Trading days</div><div class="value">{trading_days}</div><div class="label">{first_date} → {last_date}</div></div>
                <div class="metric-card"><div class="label">Observations</div><div class="value">{rows:,}</div><div class="label">{len(ASSET_METADATA)} assets × daily rows</div></div>
                <div class="metric-card"><div class="label">Latest close</div><div class="value">{last_date}</div><div class="label">Aligned across all assets</div></div>
                <div class="metric-card"><div class="label">Event calendar</div><div class="value">{len(events):,} rows</div><div class="label">Validated + deduped</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    market_preview = market.tail(10)[["date", "asset_id", "return_1d"]].rename(
        columns={"date": "Date", "asset_id": "Asset", "return_1d": "Return (1d)"}
    )
    event_cols = [col for col in ["event_type", "release_date", "trading_date", "notes"] if col in events.columns]
    event_preview = events.tail(8)[event_cols].rename(
        columns={
            "event_type": "Type",
            "release_date": "Release",
            "trading_date": "Trading day",
            "notes": "Notes",
        }
    )

    col1, col2 = st.columns([1.35, 1])
    with col1:
        st.subheader("Recent market prints")
        st.caption("Returns are simple (no forward fill). Nulls surface real gaps.")
        st.dataframe(market_preview, use_container_width=True)
    with col2:
        st.subheader("Event calendar")
        st.caption("Release dates mapped to trading days for event studies.")
        st.dataframe(event_preview, use_container_width=True)


def page_event_study(market, events):
    st.title("Macro Event Impact")
    st.write("Analyze cumulative returns around macro events with guided presets and clean tables.")

    event_types = sorted(events["event_type"].unique())
    event_type = st.selectbox("Event type", event_types, index=0)
    windows_input = st.text_input("Event windows (start:end, comma-separated)", value="-1:3,-3:5,0:1")

    event_windows = []
    invalid_tokens = []
    for token in windows_input.split(","):
        token = token.strip()
        if not token:
            continue
        if ":" not in token:
            invalid_tokens.append(token)
            continue
        try:
            start, end = token.split(":")
            event_windows.append((int(start), int(end)))
        except ValueError:
            invalid_tokens.append(token)
    if not event_windows:
        event_windows = [(-1, 1)]
    if invalid_tokens:
        st.warning(f"Skipped invalid window tokens: {', '.join(invalid_tokens)}")

    assets = st.multiselect("Assets", options=sorted(ASSET_METADATA.keys()), default=["sp500", "nasdaq"])

    summary, details = cached_event_study(market, events, tuple(event_windows))

    filtered = details[details["event_type"] == event_type]
    if assets:
        filtered = filtered[filtered["asset_id"].isin(assets)]

    col1, col2 = st.columns([1, 1])
    with col1:
        st.metric("Events analyzed", len(filtered["event_id"].unique()), help="Unique event_id rows in the window")
    with col2:
        st.metric("Assets selected", len(assets) if assets else len(ASSET_METADATA))

    plot_tab, table_tab = st.tabs(["Visuals", "Data tables"])

    with plot_tab:
        st.subheader("Average cumulative return")
        focus_asset = assets[0] if assets else "sp500"
        fig = event_study_cumret_plot(market, events, event_windows, asset_id=focus_asset, event_type=event_type)
        st.pyplot(fig, use_container_width=True)
        st.caption(f"Viewing {event_type} | Asset: {focus_asset} | Windows: {event_windows}")

    with table_tab:
        st.subheader("Summary")
        st.dataframe(summary[summary["event_type"] == event_type], use_container_width=True)
        st.subheader("Per-event cumulative returns")
        st.dataframe(filtered, use_container_width=True)
        if not filtered.empty:
            csv_bytes = filtered.to_csv(index=False).encode("utf-8")
            st.download_button("Download per-event CSV", csv_bytes, file_name="event_study_details.csv")


def page_yield_curve(fred_df: pd.DataFrame):
    st.title("Yield Curve Scenarios")
    st.write("Shock the curve, price a bond, and view scenario PnL with crisp visuals.")

    as_of_options = sorted([d.date() for d in pd.to_datetime(fred_df.dropna().index)])
    if not as_of_options:
        st.warning("No FRED data available for the selected date range.")
        return
    as_of = st.selectbox("As-of date", options=as_of_options, index=len(as_of_options) - 1)
    scenario = st.selectbox("Scenario", options=["parallel", "steepener", "flattener", "twist"])
    magnitude = st.slider("Magnitude (bps)", 1, 100, 25, step=5)
    maturity = st.number_input("Bond maturity (years)", value=10.0, min_value=1.0, max_value=50.0, step=0.5)
    coupon = st.number_input("Coupon rate (%)", value=2.0, min_value=0.0, max_value=10.0, step=0.25)
    bond = BondSpec(maturity_years=float(maturity), coupon_rate=float(coupon) / 100)

    base_curve, shocked_curve = cached_yield_scenarios(
        fred_df, as_of, ((scenario, float(magnitude)),), bond
    )

    col1, col2 = st.columns([1.3, 1])
    with col1:
        fig = yield_curve_plot(base_curve, shocked_curve, scenario, float(magnitude))
        st.pyplot(fig, use_container_width=True)
        st.caption("Scenario applied to a bootstrapped curve derived from FRED series.")
    with col2:
        st.markdown("### Scenario snapshot")
        st.write(
            f"""
            **Scenario:** {scenario.title()} • **Magnitude:** {magnitude} bps<br/>
            **Bond:** {bond.maturity_years:.1f}Y @ {coupon:.2f}% coupon<br/>
            **As of:** {as_of}
            """
        )
        curve_df = pd.DataFrame(
            {
                "tenor": ["2Y", "5Y", "10Y", "30Y"],
                "base_yield": [base_curve["2Y"], base_curve["5Y"], base_curve["10Y"], base_curve["30Y"]],
                "shocked_yield": [shocked_curve["2Y"], shocked_curve["5Y"], shocked_curve["10Y"], shocked_curve["30Y"]],
            }
        )
        st.dataframe(curve_df, use_container_width=True)


def page_correlations(market, fred):
    st.title("Correlations & Regimes")
    st.write("Explore cross-asset correlations, anomalies, PCA, and regime states with curated visuals.")

    window_choices = st.multiselect("Rolling windows", options=[20, 30, 60, 90, 120], default=[30, 90])
    if not window_choices:
        st.warning("Select at least one rolling window.")
        return

    cross_results = cached_cross_asset(market, fred, windows=tuple(window_choices))

    corr_df = cross_results["rolling_correlations"]
    static_corr = cross_results["static_correlations"]
    regimes = cross_results["regimes"]
    pca_df = cross_results["pca_loadings"]

    st.subheader("Static correlation heatmap")
    fig = correlation_heatmap(static_corr)
    st.pyplot(fig, use_container_width=True)

    if not corr_df.empty:
        pair = st.selectbox("Rolling correlation pair", options=corr_df["pair"].unique())
        fig = rolling_correlation_plot(corr_df, pair)
        st.pyplot(fig, use_container_width=True)
        st.caption("Values remain unfilled to surface real gaps in market coverage.")
        st.dataframe(corr_df[corr_df["pair"] == pair].sort_values("date"), use_container_width=True)

    st.subheader("PCA loadings")
    st.dataframe(pca_df, use_container_width=True)

    if not regimes.empty:
        st.subheader("Regime timeline")
        fig = regime_timeline_plot(regimes)
        st.pyplot(fig, use_container_width=True)
        st.dataframe(regimes, use_container_width=True)


def main():
    _apply_theme()
    _header_brand()
    settings = get_settings()
    start, end = _sidebar_controls(settings)
    if start > end:
        st.stop()

    with st.spinner("Loading data..."):
        market, fred, events = load_data(start, end)

    _hero(market)

    tabs = st.tabs(["Dashboard", "Macro Event Impact", "Yield Curve Scenarios", "Correlations & Regimes"])

    with tabs[0]:
        page_overview(market, events, settings)
    with tabs[1]:
        page_event_study(market, events)
    with tabs[2]:
        page_yield_curve(fred)
    with tabs[3]:
        page_correlations(market, fred)


if __name__ == "__main__":
    main()
