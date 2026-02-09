"""
Optimization Runner
===================
Stage opzionale per integrare l'ottimizzazione Markowitz nel pipeline principale.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from portfolio_engine.analytics.optimization.frontier import (
    generate_efficient_frontier,
    analyze_current_vs_optimal,
)
from portfolio_engine.utils.logger import get_logger
from portfolio_engine.analytics.optimization.utils import portfolio_statistics
from portfolio_engine.analytics.metrics.basic import (
    calculate_cagr_correct,
    calculate_annualized_volatility,
)
from portfolio_engine.analytics.metrics.risk import (
    calculate_sharpe_ratio,
    calculate_max_drawdown,
)

logger = get_logger(__name__)


def run_optimization_analysis(
    returns: pd.DataFrame,
    current_weights: np.ndarray,
    tickers: list,
    risk_free_rate: float = 0.02,
    max_weight: float = 0.5,
    n_frontier_points: int = 20,
    include_risk_parity: bool = True,
    use_shrinkage: bool = True,
    enabled: bool = True,
    monte_carlo: Dict[str, Any] | None = None,
) -> Optional[Dict[str, Any]]:
    """
    Esegue analisi di ottimizzazione se abilitata.
    Ritorna dict con frontiera, analisi corrente vs ottimale e portafogli chiave.
    """
    if not enabled:
        logger.info("Optimization analysis disabled")
        return None

    logger.info("Running Markowitz optimization analysis...")
    try:
        frontier = generate_efficient_frontier(
            returns,
            n_points=n_frontier_points,
            max_weight=max_weight,
            use_shrinkage=use_shrinkage,
            risk_free_rate=risk_free_rate,
            include_risk_parity=include_risk_parity,
        )
        analysis = analyze_current_vs_optimal(
            returns,
            current_weights,
            tickers,
            risk_free_rate=risk_free_rate,
            use_shrinkage=use_shrinkage,
        )

    key_metrics = _compute_key_portfolio_metrics(
        returns=returns,
        tickers=tickers,
        risk_free_rate=risk_free_rate,
        key_portfolios={
            "min_variance": frontier.min_variance,
            "max_sharpe": frontier.max_sharpe,
            "max_return": frontier.max_return,
            "risk_parity": frontier.risk_parity,
        },
    )
        current_hist = _compute_portfolio_metrics_from_weights(
            returns=returns,
            weights=current_weights,
            risk_free_rate=risk_free_rate,
        )
        mc_results = None
        if monte_carlo and monte_carlo.get("enabled", False):
            mc_results = _run_mc_on_key_portfolios(
                returns,
                frontier,
                n_sims=int(monte_carlo.get("n_sims", 20000)),
                horizon_days=int(monte_carlo.get("horizon_days", 252)),
                seed=monte_carlo.get("seed"),
                block_size=monte_carlo.get("block_size"),
            )
        logger.info("Optimization analysis completed successfully")
        return {
            "frontier": frontier,
            "current_vs_optimal": analysis,
            "key_portfolios": {
                "min_variance": frontier.min_variance,
                "max_sharpe": frontier.max_sharpe,
                "max_return": frontier.max_return,
                "risk_parity": frontier.risk_parity,
            },
            "key_portfolio_metrics": key_metrics,
            "current_historical_metrics": current_hist,
            "monte_carlo": mc_results,
        }
    except Exception as exc:
        logger.error(f"Optimization failed: {exc}")
        return {"error": str(exc)}


def _run_mc_on_key_portfolios(
    returns: pd.DataFrame,
    frontier,
    n_sims: int = 20000,
    horizon_days: int = 252,
    seed: int | None = None,
    block_size: int | None = None,
) -> Dict[str, Any]:
    """
    Esegue bootstrap Monte Carlo sui portafogli chiave.
    """
    rng = np.random.default_rng(seed)
    res = {}

    def _sample_path() -> np.ndarray:
        ret_vals = returns.values
        if not block_size or block_size <= 1:
            idx = rng.integers(0, len(ret_vals), size=horizon_days)
            return ret_vals[idx]

        # Block bootstrap: campiona blocchi consecutivi
        blocks = []
        n_blocks = int(np.ceil(horizon_days / block_size))
        max_start = len(ret_vals) - block_size
        for _ in range(n_blocks):
            start = int(rng.integers(0, max(1, max_start + 1)))
            blocks.append(ret_vals[start:start + block_size])
        path = np.vstack(blocks)[:horizon_days]
        return path

    def mc_stats(w: np.ndarray) -> Dict[str, float]:
        samples = []
        for _ in range(n_sims):
            path = _sample_path()
            port_path = (path @ w).astype(float)
            cum = np.prod(1 + port_path) - 1
            samples.append(cum)
        arr = np.array(samples)
        q05 = float(np.quantile(arr, 0.05))
        cvar = float(arr[arr <= q05].mean())
        # Convenzione: VaR/CVaR come perdita positiva
        var_loss = abs(q05)
        cvar_loss = abs(cvar)
        return {
            "mean": float(arr.mean()),
            "median": float(np.median(arr)),
            "var_95": var_loss,
            "cvar_95": cvar_loss,
        }

    key = {
        "min_variance": getattr(frontier, "min_variance", None),
        "max_sharpe": getattr(frontier, "max_sharpe", None),
        "max_return": getattr(frontier, "max_return", None),
        "risk_parity": getattr(frontier, "risk_parity", None),
    }
    for name, opt in key.items():
        if opt and getattr(opt, "success", False):
            res[name] = mc_stats(opt.weights)
    return res


def _compute_key_portfolio_metrics(
    returns: pd.DataFrame,
    tickers: list,
    risk_free_rate: float,
    key_portfolios: Dict[str, Any],
) -> Dict[str, Dict[str, float]]:
    """
    Calcola metriche per i portafogli chiave (CAGR, Vol, MaxDD, Sharpe).
    """
    metrics = {}
    if returns is None or returns.empty:
        return metrics

    for name, opt in key_portfolios.items():
        if not opt or not getattr(opt, "success", False):
            continue
        w = opt.weights
        port_ret = (returns * w).sum(axis=1)
        equity = (1 + port_ret).cumprod()
        cagr = calculate_cagr_correct(equity)
        vol = calculate_annualized_volatility(port_ret)
        sharpe = calculate_sharpe_ratio(port_ret, risk_free_rate)
        max_dd, _, _ = calculate_max_drawdown(equity)
        metrics[name] = {
            "cagr": float(cagr),
            "volatility": float(vol),
            "max_drawdown": float(max_dd),
            "sharpe": float(sharpe),
        }
    return metrics


def _compute_portfolio_metrics_from_weights(
    returns: pd.DataFrame,
    weights: np.ndarray,
    risk_free_rate: float,
) -> Dict[str, float]:
    """Calcola metriche storiche per un set di pesi."""
    if returns is None or returns.empty:
        return {}
    w = np.array(weights, dtype=float)
    w = w / w.sum()
    port_ret = (returns * w).sum(axis=1)
    equity = (1 + port_ret).cumprod()
    cagr = calculate_cagr_correct(equity)
    vol = calculate_annualized_volatility(port_ret)
    sharpe = calculate_sharpe_ratio(port_ret, risk_free_rate)
    max_dd, _, _ = calculate_max_drawdown(equity)
    return {
        "cagr": float(cagr),
        "volatility": float(vol),
        "max_drawdown": float(max_dd),
        "sharpe": float(sharpe),
    }
