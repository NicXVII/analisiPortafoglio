"""
Markowitz Mean-Variance Optimization
====================================
Funzioni core (senza I/O) per MVP, Max Sharpe e Risk Parity.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from portfolio_engine.models.portfolio import OptimizationResult
from portfolio_engine.analytics.optimization.utils import (
    compute_covariance_matrix,
    compute_expected_returns,
    portfolio_statistics,
)

logger = logging.getLogger(__name__)


def _validate_inputs(returns: pd.DataFrame, min_periods: int = 60) -> None:
    if returns.empty:
        raise ValueError("Returns DataFrame is empty")
    if len(returns) < min_periods:
        raise ValueError(f"Need at least {min_periods} periods, got {len(returns)}")
    if returns.isnull().any().any():
        nan_cols = returns.columns[returns.isnull().any()].tolist()
        raise ValueError(f"Returns contain NaN in columns: {nan_cols}")
    zero_var = returns.columns[returns.std() == 0].tolist()
    if zero_var:
        raise ValueError(f"Zero variance in columns: {zero_var}")


def min_variance_portfolio(
    returns: pd.DataFrame,
    allow_short: bool = False,
    max_weight: float = 1.0,
    use_shrinkage: bool = True,
    _precomputed: Optional[tuple] = None,
) -> OptimizationResult:
    """Minimum Variance Portfolio."""
    _validate_inputs(returns)
    if _precomputed is not None:
        mu, cov = _precomputed
    else:
        mu = compute_expected_returns(returns)
        cov = compute_covariance_matrix(returns, use_shrinkage=use_shrinkage)
    n = len(mu)

    lb = -max_weight if allow_short else 0.0
    bounds = [(lb, max_weight) for _ in range(n)]
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
    x0 = np.ones(n) / n

    res = minimize(lambda w: w @ cov @ w, x0, method="SLSQP", bounds=bounds, constraints=constraints)

    if not res.success:
        logger.warning(f"MVP optimization failed: {res.message}")
        w = np.ones(n) / n
        ret, vol, sharpe = portfolio_statistics(w, mu, cov)
        return OptimizationResult(
            w, ret, vol, sharpe, False, f"FALLBACK equal weight. {res.message}", optimization_type="min_variance"
        )

    ret, vol, sharpe = portfolio_statistics(res.x, mu, cov)
    return OptimizationResult(res.x, ret, vol, sharpe, True, res.message, optimization_type="min_variance")


def max_sharpe_portfolio(
    returns: pd.DataFrame,
    risk_free_rate: float = 0.02,
    risk_free_annual: float | None = None,
    allow_short: bool = False,
    max_weight: float = 1.0,
    use_shrinkage: bool = True,
    _precomputed: Optional[tuple] = None,
) -> OptimizationResult:
    """Tangent portfolio (Sharpe massimo)."""
    if risk_free_annual is not None:
        risk_free_rate = risk_free_annual
    _validate_inputs(returns)
    if _precomputed is not None:
        mu, cov = _precomputed
    else:
        mu = compute_expected_returns(returns)
        cov = compute_covariance_matrix(returns, use_shrinkage=use_shrinkage)
    n = len(mu)

    lb = -max_weight if allow_short else 0.0
    bounds = [(lb, max_weight) for _ in range(n)]
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
    x0 = np.ones(n) / n

    def objective(w):
        ret, vol, _ = portfolio_statistics(w, mu, cov, risk_free_rate)
        if vol < 1e-10:
            return 1e10
        return -(ret - risk_free_rate) / vol

    res = minimize(objective, x0, method="SLSQP", bounds=bounds, constraints=constraints)

    if not res.success:
        logger.warning(f"MaxSharpe optimization failed: {res.message}")
        w = np.ones(n) / n
        ret, vol, sharpe = portfolio_statistics(w, mu, cov, risk_free_rate)
        return OptimizationResult(
            w, ret, vol, sharpe, False, f"FALLBACK equal weight. {res.message}", optimization_type="max_sharpe"
        )

    ret, vol, sharpe = portfolio_statistics(res.x, mu, cov, risk_free_rate)
    return OptimizationResult(res.x, ret, vol, sharpe, True, res.message, optimization_type="max_sharpe")


def risk_parity_portfolio(
    returns: pd.DataFrame,
    allow_short: bool = False,
    max_weight: float = 1.0,
    use_shrinkage: bool = True,
    _precomputed: Optional[tuple] = None,
) -> OptimizationResult:
    """Equal Risk Contribution portfolio."""
    _validate_inputs(returns)
    if _precomputed is not None:
        mu, cov = _precomputed
    else:
        mu = compute_expected_returns(returns)
        cov = compute_covariance_matrix(returns, use_shrinkage=use_shrinkage)
    n = len(mu)

    def risk_contribution(w: np.ndarray) -> np.ndarray:
        port_vol = np.sqrt(w @ cov @ w)
        if port_vol < 1e-10:
            return np.zeros(n)
        marginal = cov @ w / port_vol
        return w * marginal

    def objective(w: np.ndarray) -> float:
        rc = risk_contribution(w)
        total_rc = rc.sum()
        if total_rc < 1e-10:
            return 1e10
        rc_pct = rc / total_rc
        target = 1.0 / n
        return np.sum((rc_pct - target) ** 2)

    lb = 1e-6 if not allow_short else -max_weight
    bounds = [(lb, max_weight) for _ in range(n)]
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
    x0 = np.ones(n) / n

    res = minimize(
        objective,
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 1000, "ftol": 1e-10},
    )

    if not res.success:
        logger.warning(f"RiskParity optimization failed: {res.message}")
        w = np.ones(n) / n
        ret, vol, sharpe = portfolio_statistics(w, mu, cov)
        return OptimizationResult(
            w, ret, vol, sharpe, False, f"FALLBACK equal weight. {res.message}", optimization_type="risk_parity"
        )

    ret, vol, sharpe = portfolio_statistics(res.x, mu, cov)
    return OptimizationResult(res.x, ret, vol, sharpe, True, res.message, optimization_type="risk_parity")
