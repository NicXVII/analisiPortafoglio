"""
Pipeline Runner
===============
Runs core pipeline stages and returns a structured bundle of results.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np

from portfolio_engine.core.pipeline import (
    _load_and_validate_data,
    _calculate_portfolio_metrics,
    _analyze_correlations,
)
from portfolio_engine.core.optimization_runner import run_optimization_analysis


def run_pipeline(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute core pipeline stages (load/metrics/correlation).
    """
    prices, benchmark_prices, data_integrity, is_provisional, risk_intent, data_quality = _load_and_validate_data(config)

    tickers = data_integrity.get("tickers_used", config["tickers"])
    weights = np.array(data_integrity.get("weights_used", config["weights"]), dtype=float)
    weights = weights / weights.sum()
    risk_free = config["risk_free_annual"]
    rebalance = config.get("rebalance")
    var_conf = config.get("var_confidence", 0.95)

    equity, port_ret, metrics, asset_df, risk_contrib, conditional_ccr = _calculate_portfolio_metrics(
        prices,
        weights,
        tickers,
        rebalance,
        risk_free,
        var_conf,
        data_integrity,
        fees_config=config.get("fees", {}),
        bias_config=config.get("bias", {}),
        var_method=config.get("risk", {}).get("var_method", "historical") if isinstance(config.get("risk"), dict) else "historical",
        var_bootstrap_samples=config.get("risk", {}).get("var_bootstrap_samples", 0) if isinstance(config.get("risk"), dict) else 0,
    )

    corr, corr_raw, shrinkage_delta, dual_corr, simple_ret = _analyze_correlations(prices)
    if data_quality is not None:
        data_quality["shrinkage"] = shrinkage_delta

    # Optional: optimization analysis
    optimization_config = config.get("optimization", {}) if isinstance(config, dict) else {}
    optimization_result = None
    if optimization_config.get("enabled", False):
        optimization_result = run_optimization_analysis(
            returns=simple_ret,
            current_weights=weights,
            tickers=tickers,
            risk_free_rate=risk_free,
            max_weight=optimization_config.get("max_weight", 0.5),
            n_frontier_points=optimization_config.get("n_frontier_points", 20),
            include_risk_parity=optimization_config.get("include_risk_parity", True),
            use_shrinkage=optimization_config.get("use_shrinkage", True),
            enabled=True,
            monte_carlo=optimization_config.get("monte_carlo", {}),
        )

    return {
        "prices": prices,
        "benchmark_prices": benchmark_prices,
        "data_integrity": data_integrity,
        "is_provisional": is_provisional,
        "risk_intent": risk_intent,
        "tickers": tickers,
        "weights": weights,
        "risk_free": risk_free,
        "rebalance": rebalance,
        "var_conf": var_conf,
        "equity": equity,
        "port_ret": port_ret,
        "metrics": metrics,
        "asset_df": asset_df,
        "risk_contrib": risk_contrib,
        "conditional_ccr": conditional_ccr,
        "corr": corr,
        "corr_raw": corr_raw,
        "shrinkage_delta": shrinkage_delta,
        "simple_ret": simple_ret,
        "optimization": optimization_result,
        "data_quality": data_quality,
    }
