"""
Output Runner
=============
Handles reporting, exports, charts, and structured outputs.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from portfolio_engine.core.pipeline import _build_structured_result
from portfolio_engine.data.fund_info import (
    get_portfolio_sector_allocation,
    get_top_holdings_by_ticker,
)
from portfolio_engine.reporting.console import (
    print_summary,
    print_senior_architect_analysis,
    plot_results,
    print_integration_test_results,
    print_sector_and_holdings_report,
    print_aggregated_holdings_report,
    print_optimization_analysis,
    print_data_quality,
)
from portfolio_engine.reporting.export import export_all_data, export_ml_structured
from portfolio_engine.utils.test_runner import run_integration_tests


def emit_outputs(
    *,
    config: Dict[str, Any],
    prices: pd.DataFrame,
    equity: pd.Series,
    port_ret: pd.Series,
    metrics: Dict[str, Any],
    risk_contrib: pd.DataFrame,
    asset_df: pd.DataFrame,
    corr: pd.DataFrame,
    corr_raw: pd.DataFrame,
    shrinkage_delta: float,
    stress_test: Dict[str, Any],
    conditional_ccr: Dict[str, Any],
    conditional_corr: Dict[str, Any],
    benchmark_comparison: Dict[str, Any],
    verdict: Dict[str, Any],
    is_retail_mode: bool,
    tickers: List[str],
    weights: np.ndarray,
    regime_info: Dict[str, Any],
    issues: List[Dict[str, Any]],
    gate_result: Any,
    risk_analysis: Dict[str, Any],
    optimization: Any = None,
    data_quality: Dict[str, Any] | None = None,
    logger,
) -> Any:
    """
    Emit all outputs and return structured AnalysisResult.
    """
    print_summary(
        metrics,
        risk_contrib,
        corr,
        asset_df,
        stress_test=stress_test,
        conditional_ccr=conditional_ccr,
        conditional_corr=conditional_corr,
        benchmark_comparison=benchmark_comparison,
        corr_raw=corr_raw,
        shrinkage_intensity=shrinkage_delta,
        verdict_info=verdict,
    )


    # Sector allocation + holdings (text)
    try:
        reporting_cfg = config.get("reporting", {}) if isinstance(config, dict) else {}
        include_fund_info = reporting_cfg.get("include_fund_info", True)
        include_sector = reporting_cfg.get("include_sector", True)
        include_holdings = reporting_cfg.get("include_holdings", True)
        include_agg = reporting_cfg.get("include_aggregated_holdings", True)

        if include_fund_info and (include_sector or include_holdings):
            sector_report = (
                get_portfolio_sector_allocation(
                    tickers=tickers, weights=weights.tolist(), min_slice_pct=3.0
                )
                if include_sector
                else {}
            )
            holdings_report = (
                get_top_holdings_by_ticker(tickers=tickers, top_n=10)
                if include_holdings
                else {}
            )
            print_sector_and_holdings_report(sector_report, holdings_report, top_n=10)

            if include_agg and holdings_report:
                print_aggregated_holdings_report(holdings_report, tickers, weights.tolist(), top_n=10)

            os.makedirs("output/data", exist_ok=True)
            with open("output/data/sector_holdings_report.json", "w") as f:
                json.dump({"sectors": sector_report, "holdings": holdings_report}, f, separators=(",", ":"))
            # aggregated holdings
            if include_agg and holdings_report:
                try:
                    agg = []
                    by_ticker = holdings_report.get("by_ticker", {}) if holdings_report else {}
                    agg_map = {}
                    for t, w in zip(tickers, weights.tolist()):
                        for h in by_ticker.get(t, []):
                            sym = h.get("symbol") or h.get("Symbol") or h.get("name") or "UNKNOWN"
                            name = h.get("name") or h.get("Name") or sym
                            pct = h.get("weight_pct") or h.get("weight") or h.get("holding_percent") or h.get("percent") or h.get("Holding Percent")
                            if pct is None:
                                pct = 0.0
                            try:
                                pct = float(pct)
                            except Exception:
                                pct = 0.0
                            pct = pct / 100 if pct > 1 else pct
                            agg_map.setdefault(sym, {"symbol": sym, "name": name, "weight": 0.0})
                            agg_map[sym]["weight"] += w * pct
                    agg = sorted(agg_map.values(), key=lambda x: x["weight"], reverse=True)[:10]
                    with open("output/data/aggregated_holdings.json", "w") as f:
                        json.dump(agg, f, separators=(",", ":"))
                except Exception as exc:
                    logger.warning(f"Aggregated holdings export skipped: {exc}")
    except Exception as exc:
        logger.warning(f"Sector/Holdings report skipped: {exc}")

    if not is_retail_mode:
        print_senior_architect_analysis(
            tickers=tickers,
            weights=weights,
            metrics=metrics,
            regime_info=regime_info,
            issues=issues,
            corr=corr,
        )
    
    # Data quality section
    try:
        print_data_quality(data_quality)
    except Exception as exc:
        logger.warning(f"Data quality report skipped: {exc}")
    
    # Optimization analysis (Markowitz)
    print_optimization_analysis(optimization)

    # Optional integration tests
    if config.get("run_integration_tests", False):
        test_results = run_integration_tests()
        print_integration_test_results(test_results)
        os.makedirs("output/data", exist_ok=True)
        with open("output/data/integration_test_results.json", "w") as f:
            json.dump(test_results, f, separators=(",", ":"))

    # Export optimization results (if available)
    if optimization:
        def _ser(obj):
            if hasattr(obj, "to_dict"):
                return obj.to_dict(tickers)
            if hasattr(obj, "__dict__"):
                return {k: _ser(v) for k, v in obj.__dict__.items()}
            if isinstance(obj, (np.ndarray, list, tuple)):
                return np.asarray(obj).tolist()
            return obj

        try:
            os.makedirs("output/data", exist_ok=True)
            with open("output/data/optimization_result.json", "w") as f:
                json.dump(optimization, f, default=_ser, separators=(",", ":"))
        except Exception as exc:
            logger.warning(f"Optimization export skipped: {exc}")

    # Data quality export
    try:
        os.makedirs("output/data", exist_ok=True)
        dq = data_quality or {}
        if "shrinkage" in dq and dq["shrinkage"] is not None:
            dq["shrinkage"] = float(dq["shrinkage"])
        with open("output/data/data_quality.json", "w") as f:
            json.dump(dq, f, separators=(",", ":"))
    except Exception as exc:
        logger.warning(f"Data quality export skipped: {exc}")

    # Export files
    export_config = config.get("export", {})
    if export_config.get("enabled", False):
        data_range = (str(prices.index[0].date()), str(prices.index[-1].date()))
        export_all_data(
            export_config=export_config,
            equity=equity,
            returns=port_ret,
            metrics=metrics,
            risk_contrib=risk_contrib,
            asset_metrics=asset_df,
            corr=corr,
            prices=prices,
            config=config,
            data_range=data_range,
        )

    # ML structured export
    from portfolio_engine.config.user_config import OUTPUT_MODE

    if OUTPUT_MODE.lower() == "professional":
        output_dir = Path("output/data")
        output_dir.mkdir(parents=True, exist_ok=True)
        ml_export_path = export_ml_structured(
            output_dir=output_dir,
            metrics=metrics,
            risk_contrib=risk_contrib,
            asset_metrics=asset_df,
            corr=corr,
            corr_raw=corr_raw,
            verdict_info=verdict,
            regime_info=regime_info,
        )
        logger.info(f"ML structured export saved: {ml_export_path}")

    # Charts
    os.makedirs("output", exist_ok=True)
    plot_results(equity, port_ret, save_path="output/portfolio_analysis.png")

    # Structured output
    analysis_result = _build_structured_result(
        config=config,
        gate_result=gate_result,
        metrics=metrics,
        risk_analysis=risk_analysis,
        tickers=tickers,
        weights=weights,
    )

    os.makedirs("output/data", exist_ok=True)
    json_path = "output/data/analysis_result.json"
    analysis_result.save_json(json_path)
    logger.info(f"Structured output saved: {json_path}")

    is_valid, issues = analysis_result.validate_for_production()
    if not is_valid:
        logger.warning("PRODUCTION VALIDATION WARNINGS:")
        for issue in issues:
            logger.warning(f"  • {issue}")

    return analysis_result
