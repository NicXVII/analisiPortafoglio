import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from portfolio_engine.analytics.optimization import (  # noqa: E402
    min_variance_portfolio,
    max_sharpe_portfolio,
    risk_parity_portfolio,
    efficient_frontier,
    select_key_portfolios,
    simulate_portfolio_mc,
    simulate_portfolios_mc,
)


def synthetic_returns(seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)
    dates = pd.date_range("2020-01-01", "2022-12-31", freq="B")
    mu_daily = np.array([0.0004, 0.0002, 0.0001])
    vol = np.array([0.02, 0.01, 0.008])
    corr = np.array([[1, 0.3, 0.2], [0.3, 1, 0.4], [0.2, 0.4, 1]])
    L = np.linalg.cholesky(corr)
    rets = []
    for _ in range(len(dates)):
        z = np.random.randn(3)
        eps = L @ z
        r = mu_daily + vol * eps
        rets.append(r)
    return pd.DataFrame(rets, index=dates, columns=["A", "B", "C"])


def test_min_variance_bounds_and_success():
    returns = synthetic_returns()
    res = min_variance_portfolio(returns, allow_short=False, max_weight=0.7)
    assert res.success
    assert np.isclose(res.weights.sum(), 1.0, atol=1e-6)
    assert (res.weights >= -1e-6).all()
    assert (res.weights <= 0.7 + 1e-6).all()


def test_max_sharpe_success_and_positive_sharpe():
    returns = synthetic_returns()
    res = max_sharpe_portfolio(returns, risk_free_annual=0.02, allow_short=False, max_weight=0.7)
    assert res.success
    assert res.sharpe > 0


def test_efficient_frontier_has_successful_points():
    returns = synthetic_returns()
    frontier = efficient_frontier(returns, target_points=7, allow_short=False, max_weight=0.7)
    successes = [r for r in frontier if r.success]
    assert len(successes) >= 3  # almeno alcuni punti trovati
    for r in successes:
        assert np.isclose(r.weights.sum(), 1.0, atol=1e-6)
        assert (r.weights >= -1e-6).all()
        assert (r.weights <= 0.7 + 1e-6).all()


def test_select_key_portfolios_returns_all_keys():
    returns = synthetic_returns()
    frontier = efficient_frontier(returns, target_points=7, allow_short=False, max_weight=0.7)
    rp = risk_parity_portfolio(returns, allow_short=False, max_weight=0.7)
    selected = select_key_portfolios(frontier, target_vol=0.12, max_weight_limit=0.7, risk_parity=rp)
    assert set(selected.keys()) <= {"min_variance", "max_sharpe", "max_return", "balanced", "risk_parity"}
    for res in selected.values():
        assert res.success


def test_simulate_portfolio_mc_basic():
    returns = synthetic_returns()
    res = min_variance_portfolio(returns, allow_short=False, max_weight=0.7)
    stats = simulate_portfolio_mc(res.weights, returns, n_sims=50, horizon_days=60, seed=123)
    assert "mean_return" in stats and "var_95" in stats and "max_dd_median" in stats


def test_simulate_portfolios_mc_collects_all():
    returns = synthetic_returns()
    frontier = efficient_frontier(returns, target_points=5, allow_short=False, max_weight=0.7)
    selected = select_key_portfolios(frontier, target_vol=0.12, max_weight_limit=0.7)
    out = simulate_portfolios_mc(selected, returns, n_sims=20, horizon_days=40, seed=321, tickers=["A", "B", "C"])
    assert set(out.keys()) == set(selected.keys())
    for name, data in out.items():
        assert "opt_result" in data and "mc" in data
        assert "weights_labeled" in data["opt_result"]


def test_risk_parity_success():
    returns = synthetic_returns()
    res = risk_parity_portfolio(returns, allow_short=False, max_weight=0.7)
    assert res.success
    assert np.isclose(res.weights.sum(), 1.0, atol=1e-6)
    assert (res.weights >= -1e-6).all()
    assert (res.weights <= 0.7 + 1e-6).all()


def test_risk_parity_equal_contribution():
    returns = synthetic_returns()
    res = risk_parity_portfolio(returns, allow_short=False, max_weight=0.7)
    if res.success:
        cov = returns.cov().values * 252
        port_vol = np.sqrt(res.weights @ cov @ res.weights)
        marginal = cov @ res.weights / port_vol
        rc = res.weights * marginal
        rc_pct = rc / rc.sum()
        target = 1.0 / len(res.weights)
        assert np.allclose(rc_pct, target, atol=0.10)


def test_risk_parity_with_shrinkage_differs():
    returns = synthetic_returns()
    res_raw = risk_parity_portfolio(returns, use_shrinkage=False)
    res_shrunk = risk_parity_portfolio(returns, use_shrinkage=True)
    assert res_raw.success and res_shrunk.success
    assert not np.allclose(res_raw.weights, res_shrunk.weights, atol=0.001)
