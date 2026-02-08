"""
Synthetic data fixtures for deterministic tests.

Simula serie prezzo realistiche con drift, volatilità e correlazioni.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def generate_synthetic_prices(
    tickers,
    start_date: str = "2020-01-01",
    end_date: str = "2024-12-31",
    seed: int = 42,
) -> pd.DataFrame:
    np.random.seed(seed)
    dates = pd.date_range(start=start_date, end=end_date, freq="B")
    n = len(dates)
    m = len(tickers)

    # simple correlated gaussian returns
    base_vol = 0.20 / np.sqrt(252)
    corr = 0.7
    cov = np.full((m, m), corr * base_vol**2)
    np.fill_diagonal(cov, base_vol**2)
    L = np.linalg.cholesky(cov)

    prices = np.zeros((n, m))
    prices[0, :] = 100
    for i in range(1, n):
        z = np.random.randn(m)
        r = L @ z + 0.0003  # ~7.5% annuo drift
        prices[i, :] = prices[i - 1, :] * (1 + r)
    return pd.DataFrame(prices, index=dates, columns=tickers)


def generate_crisis_scenario(prices: pd.DataFrame, drawdown_pct: float = -0.30) -> pd.DataFrame:
    crisis = prices.copy()
    # apply single drawdown window mid-period
    mid = len(crisis) // 2
    window = 40
    dd = (1 + drawdown_pct) ** (1 / window) - 1
    for i in range(window):
        crisis.iloc[mid + i] *= 1 + dd
    return crisis


FIXTURE_TICKERS = ["VWCE.DE", "IWDA.L", "AGGH.L"]
FIXTURE_WEIGHTS = [0.5, 0.3, 0.2]


def get_standard_fixture():
    prices = generate_synthetic_prices(FIXTURE_TICKERS)
    return prices, FIXTURE_TICKERS, FIXTURE_WEIGHTS
