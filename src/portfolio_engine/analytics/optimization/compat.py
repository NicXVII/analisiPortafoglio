"""
Legacy-compatible API for Markowitz helpers used by tests and sandbox tools.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from portfolio_engine.models.portfolio import OptimizationResult
from portfolio_engine.analytics.optimization.frontier import generate_efficient_frontier


def _validate_weights(weights: np.ndarray, n_assets: int) -> None:
    if len(weights) != n_assets:
        raise ValueError(f"Weights length {len(weights)} != n_assets {n_assets}")
    if not np.isclose(np.sum(weights), 1.0, atol=1e-4):
        raise ValueError(f"Weights sum to {np.sum(weights)} (expected 1.0)")


def efficient_frontier(
    returns: pd.DataFrame,
    target_points: int = 20,
    allow_short: bool = False,
    max_weight: float = 1.0,
    use_shrinkage: bool = True,
    risk_free_annual: float = 0.02,
    include_risk_parity: bool = True,
) -> List[OptimizationResult]:
    """Legacy wrapper returning a list of OptimizationResult points."""
    frontier = generate_efficient_frontier(
        returns,
        n_points=target_points,
        allow_short=allow_short,
        max_weight=max_weight,
        use_shrinkage=use_shrinkage,
        risk_free_rate=risk_free_annual,
        include_risk_parity=include_risk_parity,
    )
    return list(frontier.points)


def select_key_portfolios(
    frontier: List[OptimizationResult],
    min_variance: OptimizationResult | None = None,
    max_sharpe: OptimizationResult | None = None,
    risk_parity: OptimizationResult | None = None,
    target_vol: float | None = None,
    max_weight_limit: float | None = None,
) -> Dict[str, OptimizationResult]:
    """Select key portfolios from a frontier list."""
    succ = [r for r in frontier if r.success]
    if not succ:
        return {}

    mv = min_variance or min(succ, key=lambda r: r.volatility)
    ms = max_sharpe or max(succ, key=lambda r: r.sharpe_ratio)
    mr = max(succ, key=lambda r: r.expected_return)

    vol_min = min(r.volatility for r in succ)
    vol_max = max(r.volatility for r in succ)
    tv = target_vol if target_vol is not None else 0.5 * (vol_min + vol_max)
    balanced = min(succ, key=lambda r: abs(r.volatility - tv))

    selected = {
        "min_variance": mv,
        "max_sharpe": ms,
        "max_return": mr,
        "balanced": balanced,
    }
    if risk_parity is not None and risk_parity.success:
        selected["risk_parity"] = risk_parity

    if max_weight_limit is not None:
        def within_limit(res: OptimizationResult) -> bool:
            return float(np.max(res.weights)) <= max_weight_limit + 1e-8
        selected = {k: v for k, v in selected.items() if within_limit(v)}

    return selected


def simulate_portfolio_mc(
    weights: np.ndarray,
    returns: pd.DataFrame,
    n_sims: int = 500,
    horizon_days: int = 252,
    seed: Optional[int] = None,
) -> Dict[str, float]:
    """Bootstrap daily returns to simulate cumulative return distribution."""
    _validate_weights(np.array(weights, dtype=float), returns.shape[1])
    rng = np.random.default_rng(seed)
    w = np.array(weights, dtype=float)
    w = w / w.sum()

    ret_vals = returns.dropna().values
    if len(ret_vals) == 0:
        return {"mean_return": 0.0, "median_return": 0.0, "var_95": 0.0, "cvar_95": 0.0, "max_dd_median": 0.0}

    cum_returns = []
    max_dds = []
    for _ in range(int(n_sims)):
        idx = rng.integers(0, len(ret_vals), size=int(horizon_days))
        path = ret_vals[idx] @ w
        equity = (1 + path).cumprod()
        cum_returns.append(float(equity[-1] - 1))
        dd = (equity / np.maximum.accumulate(equity)) - 1
        max_dds.append(float(dd.min()))

    arr = np.array(cum_returns)
    q05 = float(np.quantile(arr, 0.05))
    cvar = float(arr[arr <= q05].mean()) if np.any(arr <= q05) else q05
    return {
        "mean_return": float(arr.mean()),
        "median_return": float(np.median(arr)),
        "var_95": abs(q05),
        "cvar_95": abs(cvar),
        "max_dd_median": float(np.median(max_dds)),
    }


def simulate_portfolios_mc(
    selected: Dict[str, OptimizationResult],
    returns: pd.DataFrame,
    n_sims: int = 500,
    horizon_days: int = 252,
    seed: Optional[int] = None,
    tickers: Optional[List[str]] = None,
) -> Dict[str, Dict[str, object]]:
    """Run Monte Carlo on multiple key portfolios."""
    out: Dict[str, Dict[str, object]] = {}
    labels = tickers or list(returns.columns)
    for name, opt in selected.items():
        if not opt.success:
            continue
        opt_dict = opt.to_dict(labels if len(labels) == len(opt.weights) else None)
        opt_dict["weights_labeled"] = opt_dict.get("weights_by_ticker", {})
        out[name] = {
            "opt_result": opt_dict,
            "mc": simulate_portfolio_mc(opt.weights, returns, n_sims=n_sims, horizon_days=horizon_days, seed=seed),
        }
    return out


def run_frontier_with_mc(
    returns: pd.DataFrame,
    tickers: List[str],
    target_points: int = 20,
    target_vol: float | None = None,
    allow_short: bool = False,
    max_weight: float = 0.7,
    n_sims: int = 20000,
    horizon_days: int = 252,
    seed: Optional[int] = None,
    output_dir: str = "output/markowitz",
    include_random_cloud: bool = False,
    cloud_size: int = 20000,
    risk_free_annual: float = 0.02,
    use_shrinkage: bool = True,
    include_risk_parity: bool = True,
) -> Dict[str, object]:
    """Legacy entrypoint: frontier, key portfolios, MC, and output files."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    frontier_obj = generate_efficient_frontier(
        returns,
        n_points=target_points,
        allow_short=allow_short,
        max_weight=max_weight,
        use_shrinkage=use_shrinkage,
        risk_free_rate=risk_free_annual,
        include_risk_parity=include_risk_parity,
    )
    frontier = list(frontier_obj.points)

    key = select_key_portfolios(
        frontier,
        min_variance=frontier_obj.min_variance,
        max_sharpe=frontier_obj.max_sharpe,
        risk_parity=frontier_obj.risk_parity,
        target_vol=target_vol,
        max_weight_limit=max_weight,
    )

    # Save frontier.csv
    rows = []
    for p in frontier:
        rows.append({
            "expected_return": p.expected_return,
            "volatility": p.volatility,
            "sharpe": p.sharpe_ratio,
            "success": p.success,
            "weights": json.dumps(p.weights.tolist()),
        })
    pd.DataFrame(rows).to_csv(out_dir / "frontier.csv", index=False)

    # Save key_portfolios.json
    key_payload = {k: v.to_dict(tickers) for k, v in key.items()}
    for k, v in key_payload.items():
        v["weights_labeled"] = v.get("weights_by_ticker", {})
    with (out_dir / "key_portfolios.json").open("w", encoding="utf-8") as f:
        json.dump(key_payload, f, ensure_ascii=True, separators=(",", ":"))

    # Optional random cloud (basic)
    if include_random_cloud:
        rng = np.random.default_rng(seed)
        cloud = []
        for _ in range(int(cloud_size)):
            w = rng.random(len(tickers))
            w = w / w.sum()
            port = (returns.values @ w).astype(float)
            ret = float(np.mean(port) * 252)
            vol = float(np.std(port, ddof=1) * np.sqrt(252))
            sharpe = (ret - risk_free_annual) / vol if vol > 0 else 0.0
            cloud.append({"expected_return": ret, "volatility": vol, "sharpe": sharpe, "weights": json.dumps(w.tolist())})
        pd.DataFrame(cloud).to_csv(out_dir / "cloud.csv", index=False)

    mc = simulate_portfolios_mc(key, returns, n_sims=n_sims, horizon_days=horizon_days, seed=seed, tickers=tickers)

    return {
        "frontier": frontier,
        "key_portfolios": key,
        "monte_carlo": mc,
        "output_dir": str(out_dir),
    }
