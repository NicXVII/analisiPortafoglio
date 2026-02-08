"""
Test live con dati reali (richiede rete).
Marcare come live per escludere in CI/offline.
"""

import pytest
import numpy as np
import pandas as pd
import sys
from pathlib import Path

# Assicura che la root del repo sia nel path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

yf = pytest.importorskip("yfinance")
from yfinance import cache as yf_cache

from portfolio_engine.analytics.optimization import run_frontier_with_mc


def pytest_configure(config):
    # registra il marker 'live' per evitare warning
    config.addinivalue_line("markers", "live: test che richiede rete/yfinance")


pytestmark = pytest.mark.live


@pytest.mark.live
def test_real_etf_frontier_mc(tmp_path):
    # Ensure yfinance cache uses a writable temp directory
    yf_cache.set_cache_location(str(tmp_path / "yf_cache"))
    # Scarica 1 anno di dati per 4 ETF core/diversificati
    tickers = ["SPY", "AGG", "GLD", "VNQ"]
    data = yf.download(tickers, period="1y", progress=False)
    # Gestisce sia MultiIndex che singolo livello
    if isinstance(data.columns, pd.MultiIndex):
        level0 = data.columns.get_level_values(0)
        if "Adj Close" in level0:
            prices = data.xs("Adj Close", axis=1, level=0)
        elif "Close" in level0:
            prices = data.xs("Close", axis=1, level=0)
        else:
            pytest.skip("No price columns available")
    else:
        if "Adj Close" in data.columns:
            prices = data["Adj Close"]
        elif "Close" in data.columns:
            prices = data["Close"]
        else:
            prices = data
    returns = prices.pct_change().dropna()

    # Esegui una versione ridotta per velocità test
    out_dir = tmp_path / "markowitz_real"
    res = run_frontier_with_mc(
        returns,
        tickers=tickers,
        target_points=8,
        allow_short=False,
        max_weight=0.6,
        n_sims=500,              # ridotto per il test
        horizon_days=126,        # ~6 mesi
        seed=123,
        output_dir=str(out_dir),
        include_random_cloud=False,  # più veloce
        use_shrinkage=True,
        include_risk_parity=True,
    )

    # Verifiche di base
    assert out_dir.joinpath("frontier.csv").exists()
    assert out_dir.joinpath("key_portfolios.json").exists()
    assert res["key_portfolios"]
    assert len([f for f in res["frontier"] if f.success]) >= 3
