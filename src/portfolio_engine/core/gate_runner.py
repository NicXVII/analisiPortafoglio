"""
Gate Runner
===========
Runs risk intent analysis and gate system with override handling.
Keeps orchestration modular and reusable.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import pandas as pd

from portfolio_engine.core.pipeline import _prepare_gate_inputs, _prepare_benchmark_metrics
from portfolio_engine.decision.risk_intent import (
    run_risk_intent_analysis,
    print_risk_intent_analysis,
    get_risk_intent_spec,
)
from portfolio_engine.decision.gate_system import (
    run_gate_analysis,
    print_gate_analysis,
)
from portfolio_engine.decision.validation import calculate_soft_classification
from portfolio_engine.utils.exceptions import (
    INCONCLUSIVEVerdictError,
    UserAcknowledgment,
    log_override,
)


def run_risk_intent_and_gate(
    prices: pd.DataFrame,
    benchmark_prices: pd.DataFrame,
    benchmark_comparison: Optional[Dict[str, Any]],
    port_ret: pd.Series,
    simple_ret: pd.DataFrame,
    tickers: List[str],
    weights: np.ndarray,
    corr: pd.DataFrame,
    risk_contrib: pd.DataFrame,
    asset_df: pd.DataFrame,
    metrics: Dict[str, Any],
    risk_intent: str,
    data_integrity: Dict[str, Any],
    issues: List[Dict[str, Any]],
    regime_info: Dict[str, Any],
    override: Optional[UserAcknowledgment],
    is_retail_mode: bool,
    logger,
) -> Tuple[Any, Dict[str, Any], Dict[str, Any]]:
    """
    Run risk intent analysis + gate system and return gate_result, risk_analysis, verdict info.
    """
    if not is_retail_mode:
        logger.info("=" * 69)
        logger.info("                 RISK INTENT ANALYSIS v3.0")
        logger.info("=" * 69)

    benchmark_ret, benchmark_metrics = _prepare_benchmark_metrics(
        benchmark_prices, benchmark_comparison
    )
    if benchmark_ret is None:
        benchmark_ret = port_ret

    risk_analysis = run_risk_intent_analysis(
        portfolio_returns=port_ret,
        benchmark_returns=benchmark_ret,
        returns_df=simple_ret,
        tickers=tickers,
        weights=weights,
        corr_matrix=corr,
        ccr_data=risk_contrib,
        portfolio_metrics=metrics,
        benchmark_metrics=benchmark_metrics,
        risk_intent=risk_intent,
    )

    if not is_retail_mode:
        print_risk_intent_analysis(risk_analysis)

    if not is_retail_mode:
        logger.info("=" * 69)
        logger.info("                 GATE SYSTEM v4.1")
        logger.info("=" * 69)

    intent_spec = get_risk_intent_spec(risk_intent)
    intent_specs_dict = {
        "beta_range": intent_spec.beta_range,
        "min_beta_acceptable": intent_spec.min_beta_acceptable,
        "beta_fail_threshold": intent_spec.beta_fail_threshold,
        "max_dd_expected": intent_spec.max_dd_expected,
    }

    gate_inputs = _prepare_gate_inputs(
        prices, port_ret, simple_ret, data_integrity, issues, benchmark_comparison
    )

    try:
        gate_result = run_gate_analysis(
            corr_matrix=corr,
            portfolio_beta=risk_analysis.get("portfolio_beta", 0.5),
            risk_intent=risk_intent,
            intent_specs=intent_specs_dict,
            tickers=tickers,
            weights=weights,
            ccr_data=risk_contrib,
            benchmark_results=gate_inputs["benchmark_results"],
            asset_metrics=asset_df,
            structural_issues=gate_inputs["structural_issues"],
            beta_window_years=gate_inputs["beta_window_years"],
            crisis_sample_days=gate_inputs["crisis_sample_days"],
            returns_df=gate_inputs["returns_df"],
            ticker_starts=gate_inputs["ticker_starts"],
            earliest_date=gate_inputs["earliest_date"],
        )
    except INCONCLUSIVEVerdictError as e:
        if override is None:
            logger.error("=" * 80)
            logger.error("⛔ INSTITUTIONAL GATE FAILURE: INCONCLUSIVE VERDICT")
            logger.error("=" * 80)
            logger.error(f"{e}")
            logger.error("❌ Analysis cannot proceed without explicit override.")
            logger.info("To override this verdict, provide a UserAcknowledgment:")
            logger.info("  override = UserAcknowledgment(")
            logger.info(f"      verdict_type='{e.verdict_type}',")
            logger.info("      authorized_by='[YOUR_NAME]',")
            logger.info("      reason='[JUSTIFICATION]',")
            logger.info("      date=datetime.now()")
            logger.info("  )")
            logger.error("=" * 80)
            raise

        is_valid, validation_error = override.validate()
        if not is_valid:
            logger.error("=" * 80)
            logger.error("⛔ INVALID OVERRIDE")
            logger.error("=" * 80)
            logger.error(f"❌ {validation_error}")
            logger.error("=" * 80)
            raise ValueError(f"Invalid override: {validation_error}") from e

        if override.verdict_type != e.verdict_type:
            logger.error("=" * 80)
            logger.error("⛔ OVERRIDE VERDICT MISMATCH")
            logger.error("=" * 80)
            logger.error(f"Expected: {e.verdict_type}")
            logger.error(f"Provided: {override.verdict_type}")
            logger.error("=" * 80)
            raise ValueError(
                f"Override verdict type '{override.verdict_type}' does not match exception '{e.verdict_type}'"
            ) from e

        log_override(override)

        logger.warning("=" * 80)
        logger.warning("⚠️  OVERRIDE APPLIED - INCONCLUSIVE VERDICT ACKNOWLEDGED")
        logger.warning("=" * 80)
        logger.warning(f"Verdict Type:    {override.verdict_type}")
        logger.warning(f"Authorized By:   {override.authorized_by}")
        logger.warning(f"Date:            {override.date.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.warning(f"Reason:          {override.reason}")
        if override.expiry_date:
            logger.warning(f"Expires:         {override.expiry_date.strftime('%Y-%m-%d')}")
        logger.warning("Analysis will continue with OVERRIDDEN verdict.")
        logger.warning("=" * 80)

        gate_result = e.gate_result
        gate_result["override_applied"] = True
        gate_result["override_details"] = {
            "authorized_by": override.authorized_by,
            "reason": override.reason,
            "date": override.date.isoformat(),
            "expiry_date": override.expiry_date.isoformat() if override.expiry_date else None,
        }

    portfolio_beta = risk_analysis.get("portfolio_beta", 0.8)
    soft_class = calculate_soft_classification(weights, tickers, asset_df, portfolio_beta)

    if not is_retail_mode and (
        soft_class.conviction_score < 70
        or soft_class.primary_type != gate_result.portfolio_classification.get("type", "")
    ):
        logger.info("SOFT CLASSIFICATION (v4.3):")
        logger.info(f"  Core Score:     {soft_class.core_score:.0f}/100")
        logger.info(f"  Tactical Score: {soft_class.tactical_score:.0f}/100")
        logger.info(f"  Conviction:     {soft_class.conviction_score:.0f}/100")
        logger.info(
            f"  Primary Type:   {soft_class.primary_type} (confidence: {soft_class.confidence:.0%})"
        )
        if soft_class.alternative_types:
            alts = ", ".join([f"{t}({c:.0%})" for t, c in soft_class.alternative_types[:2]])
            logger.info(f"  Alternatives:   {alts}")
        logger.info(f"  {soft_class.reasoning.split(chr(10))[0]}")

    metrics["soft_classification"] = {
        "core_score": soft_class.core_score,
        "tactical_score": soft_class.tactical_score,
        "conviction_score": soft_class.conviction_score,
        "primary_type": soft_class.primary_type,
    }

    if not is_retail_mode:
        print_gate_analysis(gate_result)

    regime_info["risk_intent_analysis"] = risk_analysis
    regime_info["gate_analysis"] = {
        "data_integrity": gate_result.data_integrity_gate.status.value,
        "intent_gate": gate_result.intent_gate.status.value,
        "structural_gate": gate_result.output_summary.get("Structural Gate", "UNKNOWN"),
        "final_verdict": gate_result.final_verdict.value,
        "verdict_message": gate_result.verdict_message,
        "why_not_contradictory": gate_result.why_not_contradictory,
        "is_inconclusive": "INCONCLUSIVE" in gate_result.final_verdict.value,
        "allows_portfolio_action": "INCONCLUSIVE" not in gate_result.final_verdict.value,
    }

    verdict = {
        "type": gate_result.final_verdict.value,
        "confidence": 85
        if gate_result.final_verdict.value == "APPROVED"
        else (70 if "REVIEW" in gate_result.final_verdict.value else 60),
        "message": gate_result.verdict_message,
        "action": gate_result.output_summary.get(
            "Recommended Action", "Review portfolio configuration"
        ),
    }

    return gate_result, risk_analysis, verdict
