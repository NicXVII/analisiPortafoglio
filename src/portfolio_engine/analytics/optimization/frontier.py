"""
Efficient Frontier Generation
=============================
Genera frontiera efficiente e analisi corrente vs ottimale.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import List, Dict, Any
from scipy.optimize import minimize

from portfolio_engine.models.portfolio import OptimizationResult, EfficientFrontier
from portfolio_engine.analytics.optimization.utils import (
    compute_covariance_matrix,
    compute_expected_returns,
    portfolio_statistics,
)
from portfolio_engine.analytics.optimization.markowitz import (
    _validate_inputs,
    min_variance_portfolio,
    max_sharpe_portfolio,
    risk_parity_portfolio,
)


def generate_efficient_frontier(
    returns: pd.DataFrame,
    n_points: int = 20,
    allow_short: bool = False,
    max_weight: float = 1.0,
    use_shrinkage: bool = True,
    risk_free_rate: float = 0.02,
    include_risk_parity: bool = True,
    warm_start: bool = True,
) -> EfficientFrontier:
    """Genera frontiera efficiente completa con portafogli chiave."""
    _validate_inputs(returns)
    mu = compute_expected_returns(returns)
    cov = compute_covariance_matrix(returns, use_shrinkage=use_shrinkage)
    n = len(mu)

    # Calcola portafogli speciali — passando mu/cov pre-calcolati per evitare ricalcoli
    mv = min_variance_portfolio(returns, allow_short, max_weight, use_shrinkage, _precomputed=(mu, cov))
    ms = max_sharpe_portfolio(returns, risk_free_rate, allow_short, max_weight, use_shrinkage, _precomputed=(mu, cov))
    rp = risk_parity_portfolio(returns, allow_short, max_weight, use_shrinkage, _precomputed=(mu, cov)) if include_risk_parity else None

    mu_min, mu_max = mu.min(), mu.max()
    if mu_max <= mu_min:
        return EfficientFrontier([], mv, ms, mv, rp)

    eps = 0.02 * (mu_max - mu_min)
    targets = np.linspace(mu_min + eps, mu_max - eps, n_points)

    lb = -max_weight if allow_short else 0.0
    bounds = [(lb, max_weight) for _ in range(n)]
    x0 = mv.weights if warm_start and mv.success else np.ones(n) / n
    points: List[OptimizationResult] = []

    for target in targets:
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            {"type": "eq", "fun": lambda w, t=target: w @ mu - t},
        ]
        res = minimize(lambda w: w @ cov @ w, x0, method="SLSQP", bounds=bounds, constraints=constraints)

        # fallback inequality
        if not res.success:
            constraints = [
                {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
                {"type": "ineq", "fun": lambda w, t=target: w @ mu - t},
            ]
            res = minimize(lambda w: w @ cov @ w, x0, method="SLSQP", bounds=bounds, constraints=constraints)

        if res.success:
            ret, vol, sharpe = portfolio_statistics(res.x, mu, cov, risk_free_rate)
        else:
            ret, vol, sharpe = 0.0, 0.0, 0.0
        if warm_start and res.success:
            x0 = res.x
        points.append(
            OptimizationResult(
                res.x,
                ret,
                vol,
                sharpe,
                res.success,
                res.message,
                optimization_type=f"frontier_target_{target:.4f}",
            )
        )

    max_ret = max(points, key=lambda p: p.expected_return if p.success else -np.inf)
    return EfficientFrontier(points, mv, ms, max_ret, rp)


def analyze_current_vs_optimal(
    returns: pd.DataFrame,
    current_weights: np.ndarray,
    tickers: List[str],
    risk_free_rate: float = 0.02,
    use_shrinkage: bool = True,
) -> Dict[str, Any]:
    """Confronta portafoglio attuale con portafogli ottimali."""
    mu = compute_expected_returns(returns)
    cov = compute_covariance_matrix(returns, use_shrinkage=use_shrinkage)

    curr_ret, curr_vol, curr_sharpe = portfolio_statistics(current_weights, mu, cov, risk_free_rate)

    mv = min_variance_portfolio(returns, use_shrinkage=use_shrinkage)
    ms = max_sharpe_portfolio(returns, risk_free_rate, use_shrinkage=use_shrinkage)
    rp = risk_parity_portfolio(returns, use_shrinkage=use_shrinkage)

    sharpe_gap = ms.sharpe_ratio - curr_sharpe if ms.success else None
    vol_gap = curr_vol - mv.volatility if mv.success else None

    is_efficient = False
    if ms.success and ms.sharpe_ratio > 0:
        if curr_sharpe >= ms.sharpe_ratio * 0.95:
            is_efficient = True

    analysis = {
        "current": {
            "expected_return": curr_ret,
            "volatility": curr_vol,
            "sharpe_ratio": curr_sharpe,
            "weights": dict(zip(tickers, current_weights.tolist())),
        },
        "optimal": {
            "min_variance": mv.to_dict(tickers) if mv.success else None,
            "max_sharpe": ms.to_dict(tickers) if ms.success else None,
            "risk_parity": rp.to_dict(tickers) if rp and rp.success else None,
        },
        "efficiency_analysis": {
            "sharpe_gap": sharpe_gap,
            "volatility_gap": vol_gap,
            "is_efficient": is_efficient,
            "efficiency_score": curr_sharpe / ms.sharpe_ratio if ms.success and ms.sharpe_ratio > 0 else None,
        },
        "suggestions": _generate_suggestions(curr_sharpe, curr_vol, ms, mv),
    }
    return analysis


def _generate_suggestions(
    curr_sharpe: float,
    curr_vol: float,
    max_sharpe: OptimizationResult,
    min_var: OptimizationResult,
) -> List[str]:
    suggestions: List[str] = []
    if max_sharpe.success:
        sharpe_gap = max_sharpe.sharpe_ratio - curr_sharpe
        if sharpe_gap > 0.15:
            suggestions.append(
                f"Sharpe sub-ottimale: {curr_sharpe:.2f} vs {max_sharpe.sharpe_ratio:.2f} (gap {sharpe_gap:.2f})"
            )
        elif sharpe_gap > 0.05:
            suggestions.append(
                f"Sharpe migliorabile: {curr_sharpe:.2f} vs {max_sharpe.sharpe_ratio:.2f} (gap {sharpe_gap:.2f})"
            )
    if min_var.success:
        vol_gap = curr_vol - min_var.volatility
        if vol_gap > 0.03:
            suggestions.append(
                f"Volatilità riducibile: {curr_vol:.1%} vs {min_var.volatility:.1%} (gap {vol_gap:.1%})"
            )
    if not suggestions:
        suggestions.append("Portafoglio già vicino alla frontiera efficiente")
    return suggestions
