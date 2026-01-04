import numpy as np
import pandas as pd

from macro_platform.analytics.cross_asset import (
    build_returns_wide,
    compute_rolling_correlations,
    run_pca,
)


def _sample_market_data(dates: pd.DatetimeIndex) -> pd.DataFrame:
    rows = []
    for asset_id, base in [
        ("sp500", 0.001),
        ("vix", -0.0005),
        ("nasdaq", 0.0012),
        ("eurusd", 0.0003),
    ]:
        for i, dt in enumerate(dates):
            shock = 0.0001 * ((i % 5) - 2)  # deterministic variation
            rows.append({"date": dt, "asset_id": asset_id, "return_1d": base + shock})
    return pd.DataFrame(rows)


def _sample_fred_data(dates: pd.DatetimeIndex) -> pd.DataFrame:
    data = pd.DataFrame(
        {
            "DGS10": np.linspace(3.5, 3.7, len(dates)),
        },
        index=dates,
    )
    data["DGS10_chg_bps"] = data["DGS10"].diff().fillna(0) * 100
    return data


def test_rolling_correlation_shape():
    dates = pd.date_range("2024-01-01", periods=60, freq="B")
    market_data = _sample_market_data(dates)
    fred_df = _sample_fred_data(dates)

    returns_wide = build_returns_wide(market_data, fred_df)
    corr_df = compute_rolling_correlations(
        returns_wide, windows=[5, 10], pairs=[("sp500", "vix")]
    )

    assert set(corr_df["window"].unique()) == {5, 10}
    expected_len_5 = len(dates) - 5 + 1
    expected_len_10 = len(dates) - 10 + 1
    assert len(corr_df[corr_df["window"] == 5]) == expected_len_5
    assert len(corr_df[corr_df["window"] == 10]) == expected_len_10


def test_pca_output_dimensions():
    dates = pd.date_range("2024-01-01", periods=50, freq="B")
    market_data = _sample_market_data(dates)
    fred_df = _sample_fred_data(dates)

    returns_wide = build_returns_wide(market_data, fred_df)
    pca_df = run_pca(returns_wide[["sp500", "nasdaq", "eurusd", "vix"]])

    assets = {"sp500", "nasdaq", "eurusd", "vix"}
    assert set(pca_df["asset"].unique()) == assets
    components = set(pca_df["component"].unique())
    assert len(components) == len(assets)  # full rank components
    assert len(pca_df) == len(assets) * len(components)
