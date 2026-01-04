"""Yield curve scenario simulator and bond risk measures."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")

from macro_platform.config import get_settings

logger = logging.getLogger(__name__)

ScenarioType = Literal["parallel", "steepener", "flattener", "twist"]
Curve = dict[str, float]


YIELD_ORDER = ["2Y", "5Y", "10Y", "30Y"]


@dataclass
class BondSpec:
    maturity_years: float = 10.0
    coupon_rate: float = 0.02  # annual coupon rate (2%)
    face: float = 100.0
    frequency: int = 2  # semiannual


def _validate_curve(curve: Curve) -> None:
    missing = [t for t in YIELD_ORDER if t not in curve]
    if missing:
        raise ValueError(f"Curve missing tenors: {missing}")


def build_curve_from_fred(fred_df: pd.DataFrame, as_of: date) -> Curve:
    """Extract a spot curve from FRED data (percent levels) for the as-of date."""

    as_of_ts = pd.to_datetime(as_of)
    if as_of_ts not in fred_df.index:
        raise ValueError(f"As-of date {as_of} not found in FRED data")

    row = fred_df.loc[as_of_ts]
    curve = {
        "2Y": float(row["DGS2"]),
        "5Y": float(row["DGS5"]),
        "10Y": float(row["DGS10"]),
        "30Y": float(row["DGS30"]),
    }
    _validate_curve(curve)
    return curve


def apply_scenario(curve: Curve, scenario: ScenarioType, magnitude_bps: float) -> Curve:
    _validate_curve(curve)
    shock = magnitude_bps / 100  # convert bps to percent

    shocked = curve.copy()
    if scenario == "parallel":
        shocked = {k: v + shock for k, v in curve.items()}
    elif scenario == "steepener":
        shocked["2Y"] = curve["2Y"] - shock
        shocked["5Y"] = curve["5Y"] - shock / 2
        shocked["10Y"] = curve["10Y"] + shock / 2
        shocked["30Y"] = curve["30Y"] + shock
    elif scenario == "flattener":
        shocked["2Y"] = curve["2Y"] + shock
        shocked["5Y"] = curve["5Y"] + shock / 2
        shocked["10Y"] = curve["10Y"] - shock / 2
        shocked["30Y"] = curve["30Y"] - shock
    elif scenario == "twist":
        shocked["2Y"] = curve["2Y"] + shock
        shocked["5Y"] = curve["5Y"] - shock / 2
        shocked["10Y"] = curve["10Y"] + shock / 2
        shocked["30Y"] = curve["30Y"] - shock
    else:
        raise ValueError(f"Unknown scenario {scenario}")

    return shocked


def _apply_scenario(curve: Curve, scenario: ScenarioType, magnitude_bps: float) -> Curve:
    """Backward-compatible wrapper for apply_scenario."""

    return apply_scenario(curve, scenario, magnitude_bps)


def price_fixed_rate_bond(yield_percent: float, spec: BondSpec | None = None) -> float:
    """Price a fixed-rate bond given yield in percent."""

    spec = spec or BondSpec()
    y = yield_percent / 100
    periods = int(spec.maturity_years * spec.frequency)
    coupon = spec.coupon_rate * spec.face / spec.frequency
    discount = 1 + y / spec.frequency

    cashflows = np.full(periods, coupon, dtype=float)
    cashflows[-1] += spec.face

    times = np.arange(1, periods + 1)
    present_values = cashflows / (discount**times)
    return float(present_values.sum())


def bond_risk_measures(yield_percent: float, spec: BondSpec | None = None) -> dict[str, float]:
    """Compute price, DV01, modified duration, convexity via finite differences."""

    spec = spec or BondSpec()
    base_price = price_fixed_rate_bond(yield_percent, spec)
    bump = 0.0001  # 1bp in decimal terms

    price_up = price_fixed_rate_bond(yield_percent + 0.01, spec)  # +1bp = +0.01%
    price_down = price_fixed_rate_bond(yield_percent - 0.01, spec)

    dv01 = (price_up - price_down) / 2  # change per +1bp
    mod_duration = -dv01 / (base_price * bump)
    convexity = (price_down + price_up - 2 * base_price) / (base_price * (bump**2))

    return {
        "price": base_price,
        "dv01": dv01,
        "mod_duration": mod_duration,
        "convexity": convexity,
    }


def scenario_table(
    base_curve: Curve, scenarios: Iterable[tuple[ScenarioType, float]]
) -> pd.DataFrame:
    """Return table of shocked yields for each scenario."""

    records = []
    for scenario, magnitude in scenarios:
        shocked = apply_scenario(base_curve, scenario, magnitude)
        for tenor in YIELD_ORDER:
            records.append(
                {
                    "scenario": scenario,
                    "magnitude_bps": magnitude,
                    "tenor": tenor,
                    "base_yield": base_curve[tenor],
                    "shocked_yield": shocked[tenor],
                }
            )
    return pd.DataFrame(records)


def scenario_pnl(
    base_curve: Curve,
    scenarios: Iterable[tuple[ScenarioType, float]],
    bond: BondSpec | None = None,
) -> pd.DataFrame:
    """Estimate PnL for the default bond using 10Y yield under each scenario."""

    bond = bond or BondSpec()
    base_yield = base_curve["10Y"]
    base_measures = bond_risk_measures(base_yield, bond)
    base_price = base_measures["price"]

    rows = []
    for scenario, magnitude in scenarios:
        shocked_curve = apply_scenario(base_curve, scenario, magnitude)
        shocked_yield = shocked_curve["10Y"]
        shocked_price = price_fixed_rate_bond(shocked_yield, bond)
        pnl = shocked_price - base_price
        rows.append(
            {
                "scenario": scenario,
                "magnitude_bps": magnitude,
                "base_yield_10Y": base_yield,
                "shocked_yield_10Y": shocked_yield,
                "base_price": base_price,
                "shocked_price": shocked_price,
                "pnl": pnl,
                "dv01": base_measures["dv01"],
                "mod_duration": base_measures["mod_duration"],
                "convexity": base_measures["convexity"],
            }
        )
    return pd.DataFrame(rows)


def plot_curve(
    base_curve: Curve,
    scenario_curve: Curve,
    scenario_name: str,
    magnitude_bps: float,
    output_dir: Path,
) -> Path:
    from macro_platform.viz.charts import save_fig, yield_curve_plot

    output_dir.mkdir(parents=True, exist_ok=True)
    fig = yield_curve_plot(base_curve, scenario_curve, scenario_name, magnitude_bps)
    path = output_dir / f"{scenario_name}_{int(magnitude_bps)}bps.png"
    save_fig(fig, path)
    return path


def run_yield_curve_scenarios(
    fred_df: pd.DataFrame,
    as_of: date,
    scenarios: Iterable[tuple[ScenarioType, float]],
    bond: BondSpec | None = None,
    output_dir: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build base curve, apply scenarios, price bond risk, and persist outputs.

    Returns (scenario_yields_df, pnl_df).
    """

    settings = get_settings()
    out_dir = output_dir or settings.output_dir
    plots_dir = out_dir / "yield_curve_plots"
    out_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)

    bond = bond or BondSpec()
    base_curve = build_curve_from_fred(fred_df, as_of)
    yields_df = scenario_table(base_curve, scenarios)
    pnl_df = scenario_pnl(base_curve, scenarios, bond)

    yields_path = out_dir / "yield_curve_scenarios.csv"
    yields_df.to_csv(yields_path, index=False)
    pnl_path = out_dir / "yield_curve_pnl.csv"
    pnl_df.to_csv(pnl_path, index=False)
    logger.info("Saved yield scenarios to %s", yields_path)
    logger.info("Saved scenario PnL to %s", pnl_path)

    for scenario, magnitude in scenarios:
        shocked_curve = apply_scenario(base_curve, scenario, magnitude)
        plot_curve(base_curve, shocked_curve, scenario, magnitude, plots_dir)

    return yields_df, pnl_df
