import pandas as pd
import numpy as np

from portfolio_engine.data.loader import convert_to_base_currency
from portfolio_engine.analytics.metrics.risk import calculate_var_cvar


def test_convert_to_base_currency_alignment():
    dates_prices = pd.date_range("2020-01-01", periods=3, freq="D")
    prices = pd.DataFrame({"EUR_ETF": [100, 101, 102]}, index=dates_prices)
    # FX shorter and misaligned index
    dates_fx = pd.date_range("2020-01-02", periods=2, freq="D")
    fx_series = pd.Series([1.1, 1.2], index=dates_fx)
    currency_map = {"EUR_ETF": "EUR"}
    converted, info = convert_to_base_currency(
        prices,
        currency_map,
        base_currency="USD",
        manual_rates={"EURUSD=X": fx_series.iloc[-1]},
        warn_on_missing=False,
        return_info=True,
    )
    assert "EUR_ETF" in converted.columns
    assert len(converted) == len(prices)
    assert info["converted"] == ["EUR_ETF"] or "EUR_ETF" in info["converted"]


def test_var_positive_sign():
    rng = np.random.default_rng(0)
    returns = pd.Series(rng.normal(0.0005, 0.01, size=500))
    var, cvar = calculate_var_cvar(returns, confidence=0.95, periods=252, method="historical")
    assert var >= 0
    assert cvar >= 0
