import pytest

from macro_platform.analytics.yield_curve import BondSpec, bond_risk_measures


def test_dv01_sign_and_duration_relationship():
    measures = bond_risk_measures(3.0, BondSpec(maturity_years=5, coupon_rate=0.02))

    assert measures["dv01"] < 0  # price falls when yield rises

    bump = 0.0001
    expected_duration = -measures["dv01"] / (measures["price"] * bump)
    assert pytest.approx(measures["mod_duration"], rel=1e-3) == expected_duration

