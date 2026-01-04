"""Cross-asset analytics: correlations, PCA, and regimes."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from macro_platform.config import get_settings

logger = logging.getLogger(__name__)

TARGET_ASSETS = {"sp500", "nasdaq", "eurusd", "vix"}
DEFAULT_PAIRS: list[tuple[str, str]] = [
    ("sp500", "nasdaq"),
    ("sp500", "vix"),
    ("sp500", "eurusd"),
    ("sp500", "rates_factor"),
    ("nasdaq", "vix"),
    ("eurusd", "rates_factor"),
]


def build_returns_wide(market_data: pd.DataFrame, fred_df: pd.DataFrame) -> pd.DataFrame:
    """Pivot market returns to a wide table and add rates factor from 10Y bps changes."""

    required_market_cols = {"date", "asset_id", "return_1d"}
    missing = required_market_cols - set(market_data.columns)
    if missing:
        raise ValueError(f"market_data missing columns: {sorted(missing)}")

    market = market_data.copy()
    market["date"] = pd.to_datetime(market["date"])
    market = market[market["asset_id"].isin(TARGET_ASSETS)]

    wide = (
        market.pivot_table(index="date", columns="asset_id", values="return_1d", aggfunc="last")
        .sort_index()
        .copy()
    )

    if "DGS10_chg_bps" not in fred_df.columns:
        raise ValueError("fred_df must include DGS10_chg_bps for rates factor")

    fred = fred_df.copy()
    fred.index = pd.to_datetime(fred.index)
    rates = fred["DGS10_chg_bps"].rename("rates_factor")
    wide = wide.join(rates, how="inner")

    wide = wide.dropna(how="all")
    return wide


def compute_rolling_correlations(
    returns_wide: pd.DataFrame,
    windows: Sequence[int] = (30, 90),
    pairs: Sequence[tuple[str, str]] | None = None,
) -> pd.DataFrame:
    """Compute rolling correlations for specified pairs and windows."""

    returns_wide = returns_wide.sort_index()
    pairs = pairs or DEFAULT_PAIRS
    pairs = [(a, b) for a, b in pairs if a in returns_wide.columns and b in returns_wide.columns]
    records: list[dict] = []

    for a, b in pairs:
        for window in windows:
            corr_series = returns_wide[a].rolling(window).corr(returns_wide[b])
            df = pd.DataFrame(
                {
                    "date": corr_series.index,
                    "pair": f"{a}__{b}",
                    "window": window,
                    "rolling_corr": corr_series.values,
                }
            ).dropna()
            records.append(df)

    if not records:
        return pd.DataFrame(columns=["date", "pair", "window", "rolling_corr", "zscore", "anomaly"])

    corr_df = pd.concat(records, ignore_index=True)
    corr_df = _detect_correlation_anomalies(corr_df)
    return corr_df


def _detect_correlation_anomalies(corr_df: pd.DataFrame) -> pd.DataFrame:
    """Add z-score and anomaly flag when abs(z) > 2 for >=5 consecutive days."""

    if corr_df.empty:
        return corr_df.assign(zscore=pd.Series(dtype=float), anomaly=pd.Series(dtype=bool))

    corr_df = corr_df.copy()
    corr_df["zscore"] = np.nan
    corr_df["anomaly"] = False

    for (pair, window), group in corr_df.groupby(["pair", "window"]):
        mean = group["rolling_corr"].mean()
        std = group["rolling_corr"].std()
        if std == 0 or np.isnan(std):
            corr_df.loc[group.index, "zscore"] = 0.0
            continue

        z = (group["rolling_corr"] - mean) / std
        corr_df.loc[group.index, "zscore"] = z

        high = z.abs() > 2
        runs = (high != high.shift()).cumsum()
        run_lengths = high.groupby(runs).transform("size")
        anomalies = high & (run_lengths >= 5)
        corr_df.loc[group.index, "anomaly"] = anomalies

    return corr_df


def run_pca(returns_wide: pd.DataFrame) -> pd.DataFrame:
    """Run PCA on standardized returns and return loadings."""

    clean = returns_wide.dropna().copy()
    if clean.empty:
        return pd.DataFrame(
            columns=["component", "asset", "loading", "explained_variance_ratio"]
        )

    scaler = StandardScaler()
    scaled = scaler.fit_transform(clean.values)

    n_components = min(scaled.shape[0], scaled.shape[1])
    pca = PCA(n_components=n_components)
    pca.fit(scaled)

    loadings = pca.components_
    assets = list(clean.columns)

    records = []
    for i, component in enumerate(loadings):
        for asset, loading in zip(assets, component):
            records.append(
                {
                    "component": i + 1,
                    "asset": asset,
                    "loading": loading,
                    "explained_variance_ratio": pca.explained_variance_ratio_[i],
                }
            )

    return pd.DataFrame(records)


def compute_regimes(returns_wide: pd.DataFrame) -> pd.DataFrame:
    """Label risk regimes using SP500 and VIX 5d moves."""

    if "sp500" not in returns_wide.columns or "vix" not in returns_wide.columns:
        raise ValueError("returns_wide must include sp500 and vix columns for regimes")

    def _roll_cum(series: pd.Series, window: int) -> pd.Series:
        return (1 + series).rolling(window=window).apply(np.prod, raw=True) - 1

    spx_5d = _roll_cum(returns_wide["sp500"], 5)
    vix_5d = _roll_cum(returns_wide["vix"], 5)
    regime = np.where((spx_5d < 0) & (vix_5d > 0), "risk_off", "risk_on")

    out = pd.DataFrame(
        {
            "date": returns_wide.index,
            "spx_5d_return": spx_5d.values,
            "vix_5d_return": vix_5d.values,
            "regime": regime,
        }
    ).dropna()
    return out


def _plot_rolling_correlations(corr_df: pd.DataFrame, output_dir: Path) -> None:
    if corr_df.empty:
        logger.warning("No rolling correlations to plot.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    for pair, group in corr_df.groupby("pair"):
        fig, ax = plt.subplots(figsize=(8, 4))
        for window, wgroup in group.groupby("window"):
            ax.plot(wgroup["date"], wgroup["rolling_corr"], label=f"{window}d")

        anomalies = group[group["anomaly"]]
        if not anomalies.empty:
            ax.scatter(anomalies["date"], anomalies["rolling_corr"], color="red", label="Anomaly")

        ax.set_title(f"Rolling correlation: {pair}")
        ax.set_ylabel("Correlation")
        ax.grid(True, linestyle="--", alpha=0.4)
        ax.legend()
        plt.tight_layout()

        path = output_dir / f"{pair}.png"
        fig.savefig(path)
        plt.close(fig)
        logger.info("Saved correlation plot to %s", path)


def run_cross_asset_analytics(
    market_data: pd.DataFrame,
    fred_df: pd.DataFrame,
    output_dir: Path | None = None,
    windows: Sequence[int] = (30, 90),
) -> dict[str, pd.DataFrame]:
    """Run cross-asset analytics and persist outputs."""

    settings = get_settings()
    out_dir = output_dir or settings.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    plot_dir = out_dir / "correlation_plots"
    plot_dir.mkdir(parents=True, exist_ok=True)

    returns_wide = build_returns_wide(market_data, fred_df)
    static_corr = returns_wide.corr()
    corr_df = compute_rolling_correlations(returns_wide, windows=windows)
    pca_df = run_pca(returns_wide)
    regime_df = compute_regimes(returns_wide)

    corr_path = out_dir / "rolling_correlations.csv"
    pca_path = out_dir / "pca_loadings.csv"
    regime_path = out_dir / "regimes.csv"
    static_corr_path = out_dir / "static_correlations.csv"

    corr_df.to_csv(corr_path, index=False)
    pca_df.to_csv(pca_path, index=False)
    regime_df.to_csv(regime_path, index=False)
    static_corr.to_csv(static_corr_path)

    logger.info("Saved rolling correlations to %s", corr_path)
    logger.info("Saved PCA loadings to %s", pca_path)
    logger.info("Saved regimes to %s", regime_path)
    logger.info("Saved static correlations to %s", static_corr_path)

    _plot_rolling_correlations(corr_df, plot_dir)

    return {
        "returns_wide": returns_wide,
        "rolling_correlations": corr_df,
        "pca_loadings": pca_df,
        "regimes": regime_df,
        "static_correlations": static_corr,
    }
