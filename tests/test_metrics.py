import pytest

from microstructure_lab.analytics.metrics import summarize


def test_sharpe_scales_with_periods_per_year():
    path = [0.0, 1.0, 0.0, 2.0, 1.0]
    inventory = [0.0] * len(path)

    a = summarize(path, inventory, fills=0, fees_paid=0.0, periods_per_year=1.0)
    b = summarize(path, inventory, fills=0, fees_paid=0.0, periods_per_year=4.0)

    assert a["sharpe_annualized"] != 0.0
    assert b["sharpe_annualized"] == pytest.approx(a["sharpe_annualized"] * 2.0)


def test_non_positive_periods_per_year_returns_zero_sharpe_when_std_positive():
    path = [0.0, 1.0, 0.0, 2.0, 1.0]
    inventory = [0.0] * len(path)

    out = summarize(path, inventory, fills=0, fees_paid=0.0, periods_per_year=0.0)

    assert out["sharpe_annualized"] == 0.0
