import numpy as np
import pandas as pd

from portfolio_engine.analytics.optimization import (
    min_variance_portfolio,
    max_sharpe_portfolio,
    risk_parity_portfolio,
    generate_efficient_frontier,
)


def synthetic_returns(rows: int = 300, cols: int = 3) -> pd.DataFrame:
    np.random.seed(42)
    data = np.random.randn(rows, cols) * 0.01
    return pd.DataFrame(data, columns=[f"A{i}" for i in range(cols)])


def test_min_variance_success():
    returns = synthetic_returns()
    res = min_variance_portfolio(returns, max_weight=0.7)
    assert res.success
    assert np.isclose(res.weights.sum(), 1.0, atol=1e-6)


def test_max_sharpe_success():
    returns = synthetic_returns()
    res = max_sharpe_portfolio(returns, max_weight=0.7)
    assert res.success
    assert np.isclose(res.weights.sum(), 1.0, atol=1e-6)


def test_risk_parity_success():
    returns = synthetic_returns()
    res = risk_parity_portfolio(returns, max_weight=0.7)
    assert res.success
    assert np.isclose(res.weights.sum(), 1.0, atol=1e-6)


def test_generate_frontier_points():
    returns = synthetic_returns(cols=4)
    frontier = generate_efficient_frontier(returns, n_points=5, max_weight=0.6)
    assert len(frontier.points) == 5
    assert frontier.min_variance.success
    assert frontier.max_sharpe.success
