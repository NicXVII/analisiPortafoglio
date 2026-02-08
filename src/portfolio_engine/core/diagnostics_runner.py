"""
Diagnostics Runner
==================
Compute portfolio diagnostics, benchmark comparison, stress tests,
cost adjustments, and issue analysis in a modular way.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from portfolio_engine.analytics.analysis import analyze_portfolio_issues
from portfolio_engine.analytics.metrics import (
    calculate_benchmark_comparison,
    run_monte_carlo_stress_test,
    calculate_conditional_correlations,
)
from portfolio_engine.data.definitions.taxonomy import quick_composition_estimate
from portfolio_engine.core.pipeline import _run_validation_framework
from portfolio_engine.data.loader import detect_crisis_in_data
from portfolio_engine.reporting.console import print_portfolio_critique
from portfolio_engine.utils.costs import (
    calculate_total_cost_adjustment,
    adjust_metrics_for_costs,
)


def run_diagnostics(
    *,
    prices: pd.DataFrame,
    benchmark_prices: pd.DataFrame,
    simple_ret: pd.DataFrame,
    port_ret: pd.Series,
    tickers: List[str],
    weights: np.ndarray,
    corr: pd.DataFrame,
    risk_contrib: pd.DataFrame,
    asset_df: pd.DataFrame,
    metrics: Dict[str, Any],
    data_integrity: Dict[str, Any],
    rebalance: Optional[str],
    is_retail_mode: bool,
    logger,
) -> Dict[str, Any]:
    """
    Returns a dict with:
    - benchmark_comparison
    - crisis_info
    - stress_test
    - conditional_corr
    - issues
    - regime_info
    """
    # Conditional correlations
    portfolio_ret = (simple_ret * weights).sum(axis=1)
    conditional_corr = calculate_conditional_correlations(simple_ret, portfolio_ret)

    # Benchmark comparison
    benchmark_comparison = None
    if not benchmark_prices.empty:
        quick_comp = quick_composition_estimate(tickers, weights)
        provisional_portfolio_type = "EQUITY_MULTI_BLOCK"
        benchmark_comparison = calculate_benchmark_comparison(
            portfolio_returns=port_ret,
            portfolio_metrics=metrics,
            benchmark_prices=benchmark_prices,
            portfolio_type=provisional_portfolio_type,
            total_defensive_pct=quick_comp["total_defensive"],
            has_sector_tilts=quick_comp["has_sector_tilts"],
        )

    # Crisis detection
    crisis_info = detect_crisis_in_data(prices, simple_ret)
    if not is_retail_mode and crisis_info.get("includes_crisis"):
        logger.warning("CRISIS DETECTION:")
        logger.warning(
            f"  I dati includono {len(crisis_info.get('crisis_periods', []))} periodi di crisi:"
        )
        for cp in crisis_info.get("crisis_periods", [])[:3]:
            logger.warning(f"  • {cp.get('name', 'Unknown')} ({cp.get('detection', '')})")
        logger.warning(f"  Max Drawdown osservato: {crisis_info.get('max_drawdown_observed', 0):.1%}")
        logger.info("  → Monte Carlo userà scenari strutturali, non vol doubling")

    # Monte Carlo stress test
    stress_test = run_monte_carlo_stress_test(
        simple_ret, weights, n_simulations=500, includes_crisis=crisis_info["includes_crisis"]
    )
    stress_test["crisis_info"] = crisis_info

    # Transaction costs & tax drag
    years_of_data = (prices.index[-1] - prices.index[0]).days / 365.25
    cost_adjustment = calculate_total_cost_adjustment(
        tickers=tickers,
        weights=weights,
        rebalance_frequency=rebalance,
        years=years_of_data,
        investor_country="EU",
    )
    metrics_adjusted = adjust_metrics_for_costs(metrics, cost_adjustment)
    metrics["cost_adjustment"] = cost_adjustment
    metrics["cagr_net"] = metrics_adjusted["cagr_net"]
    metrics["sharpe_net"] = metrics_adjusted["sharpe_net"]

    if not is_retail_mode and cost_adjustment["total_annual_drag"] > 0.005:
        logger.info("COSTI TRANSAZIONE E FISCALI:")
        logger.info(
            f"  Rebalancing costs:     {cost_adjustment['rebalancing_costs']['total_cost_annual']:.2%}/anno"
        )
        logger.info(f"  Tax drag (dividendi):  {cost_adjustment['tax_drag']['annual_tax_drag']:.2%}/anno")
        logger.info("  ─────────────────────────")
        logger.info(f"  TOTALE:                {cost_adjustment['total_annual_drag']:.2%}/anno")
        logger.info(f"  CAGR Gross → Net:      {metrics['cagr']:.2%} → {metrics['cagr_net']:.2%}")

    # Validation framework (walk-forward, rolling, OOS)
    validation_results = _run_validation_framework(prices, weights, tickers, metrics)
    if not is_retail_mode:
        for warn in validation_results["warnings"]:
            logger.warning(f"{warn['section']}:")
            for line in warn["lines"]:
                logger.warning(line)

    # Issues / regime info
    data_start = str(prices.index[0].date())
    data_end = str(prices.index[-1].date())
    issues, regime_info = analyze_portfolio_issues(
        weights=weights,
        tickers=tickers,
        corr=corr,
        risk_contrib=risk_contrib,
        asset_metrics=asset_df,
        metrics=metrics,
        data_start=data_start,
        data_end=data_end,
        equity_curve=metrics.get("equity_curve"),
        returns=metrics.get("returns"),
    )

    # Propagate data integrity into regime info
    regime_info["data_integrity"] = data_integrity
    if data_integrity.get("is_provisional", False):
        regime_info["analysis_status"] = "PROVISIONAL"
        issues.insert(
            0,
            {
                "type": "DATA_QUALITY_GATE",
                "severity": "🚨",
                "message": (
                    f"ANALYSIS PROVISIONAL: {data_integrity.get('nan_removed', 0)} righe con dati incompleti "
                    "rimossi dopo common-start. Risultati da validare."
                ),
            },
        )
    else:
        regime_info["analysis_status"] = "VALIDATED"

    # Benchmark underperformance → issue
    if benchmark_comparison:
        overall_verdict = benchmark_comparison.get("overall_verdict", "")
        if overall_verdict == "REVIEW_NEEDED":
            inferior_benchmarks = []
            for bench_key, bench_data in benchmark_comparison.get("benchmarks", {}).items():
                if bench_data.get("comparison_type") == "SAME_CATEGORY":
                    if bench_data.get("verdict") == "INFERIOR":
                        inferior_benchmarks.append(bench_data.get("name", bench_key))
            if inferior_benchmarks:
                issues.insert(
                    0,
                    {
                        "type": "BENCHMARK_UNDERPERFORMANCE",
                        "severity": "🚨",
                        "message": (
                            f"INFERIOR vs benchmark same-category: {', '.join(inferior_benchmarks)}. "
                            "Il portafoglio non giustifica la complessità rispetto ad alternative passive equivalenti."
                        ),
                    },
                )

        regime_info["benchmark_comparison"] = benchmark_comparison

    if not is_retail_mode:
        print_portfolio_critique(issues, regime_info)

    return {
        "benchmark_comparison": benchmark_comparison,
        "crisis_info": crisis_info,
        "stress_test": stress_test,
        "conditional_corr": conditional_corr,
        "issues": issues,
        "regime_info": regime_info,
    }
