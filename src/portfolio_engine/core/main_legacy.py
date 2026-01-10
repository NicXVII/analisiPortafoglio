"""
Portfolio Analysis Tool v3.0
============================
Versione modulare con architettura a componenti.

Moduli:
- metrics.py: Calcolo metriche (returns, CAGR, Sharpe, Sortino, VaR, etc.)
- taxonomy.py: Classificazione ETF, esposizioni geografiche/funzionali
- analysis.py: Portfolio type detection, issue analysis
- output.py: Funzioni di output/stampa
- export.py: Export dati (CSV, Excel, JSON, HTML, grafici)
- data.py: Download e gestione dati
- config.py: Configurazione portafoglio
- risk_intent.py: Risk Intent Analysis v3.0 (NEW)
- logger.py: Centralized logging framework (NEW)

Metodologie:
- Simple returns per aggregazione portafoglio
- CAGR geometrico dall'equity curve
- Sortino con Target Downside Deviation corretta
- VaR/CVaR storico
- Risk contribution basata su matrice covarianza
- Beta-adjusted metrics per evitare bias anti-equity (v3.0)
- Drawdown Attribution: Structural vs Regime-driven (v3.0)
"""

import numpy as np
import pandas as pd
import warnings
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any
warnings.filterwarnings('ignore', category=FutureWarning)

# === LOGGING SETUP ===
from portfolio_engine.utils.logger import get_logger, log_performance, ProgressLogger
logger = get_logger(__name__)

# === IMPORTS DAI MODULI ===
from portfolio_engine.config.user_config import get_config

# Production Readiness: Exception enforcement (Issue #1)
from portfolio_engine.utils.exceptions import (
    INCONCLUSIVEVerdictError,
    DataIntegrityError,
    BetaWindowError,
    IntentFailStructureInconclusiveError,
    UserAcknowledgment,
    log_override
)

# Production Readiness: Structured Output (Issue #3)
from portfolio_engine.models.portfolio import (
    AnalysisResult,
    MetricsSnapshot,
    PrescriptiveAction,
    PortfolioStructureType
)

from portfolio_engine.data.definitions.taxonomy import (
    quick_composition_estimate  # Rule 8: for benchmark comparison
)

from portfolio_engine.analytics.metrics_monolith import (
    calculate_simple_returns,
    calculate_cagr_correct,
    calculate_annualized_volatility,
    calculate_all_metrics,
    calculate_risk_contribution_correct,
    calculate_conditional_risk_contribution,
    calculate_conditional_correlations,
    calculate_benchmark_comparison,
    run_monte_carlo_stress_test,
    calculate_shrunk_correlation
)

from portfolio_engine.data.loader import (
    download_data,
    calculate_start_date,
    simulate_portfolio_correct,
    check_survivorship_bias_warning,
    validate_data_integrity,
    detect_crisis_in_data,
    DATA_START_POLICY
)

from portfolio_engine.analytics.analysis_monolith import (
    analyze_portfolio_issues
)

from portfolio_engine.reporting.console import (
    print_summary,
    print_portfolio_critique,
    print_senior_architect_analysis,
    plot_results
)

from portfolio_engine.reporting.export import (
    export_all_data,
    generate_pdf_report,
    export_ml_structured  # v3.1: ML-ready export
)

# Transaction costs and tax modeling
from portfolio_engine.utils.costs import (
    calculate_total_cost_adjustment,
    adjust_metrics_for_costs
)

# v3.0: Risk Intent Analysis
from portfolio_engine.decision.risk_intent import (
    run_risk_intent_analysis,
    print_risk_intent_analysis,
    get_risk_intent_spec,
    validate_risk_intent
)

# v4.1: Gate System
from portfolio_engine.decision.gate_system import (
    run_gate_analysis,
    print_gate_analysis,
    GateStatus,
    FinalVerdictType
)

# v4.3: Validation Framework (RAW/REG, Walk-Forward, Soft Labels)
from portfolio_engine.decision.validation import (
    create_dual_correlation,
    DualCorrelationMatrix,
    CorrelationUseCase,
    run_walk_forward_validation,
    analyze_rolling_stability,
    calculate_soft_classification,
    run_out_of_sample_stress
)

# Per catturare output per PDF
import sys
from io import StringIO

# === PIPELINE IMPORTS (Refactor: 2026-01-09) ===
# Estratte 7 funzioni helper/stage in pipeline.py per ridurre dimensione main.py
from portfolio_engine.core.pipeline import (
    _load_and_validate_data,
    _calculate_portfolio_metrics,
    _analyze_correlations,
    _build_structured_result,
    _run_validation_framework,
    _prepare_gate_inputs,
    _prepare_benchmark_metrics
)

# MAIN ANALYSIS FUNCTION
# =========================

def analyze_portfolio(config: Dict[str, Any], override: Optional[UserAcknowledgment] = None) -> Optional[AnalysisResult]:
    """
    Funzione principale di analisi portafoglio.
    
    PRODUCTION READINESS (Issue #1):
    Raises INCONCLUSIVEVerdictError if data quality is insufficient.
    Use 'override' parameter to explicitly acknowledge and proceed.
    
    PRODUCTION READINESS (Issue #3):
    Returns AnalysisResult - structured, machine-readable output for programmatic validation.
    
    Args:
        config: Dizionario configurazione con:
            - tickers: lista ticker
            - weights: lista pesi
            - years_history: anni di storico
            - end_date: data fine
            - start_date: data inizio (opzionale)
            - risk_free_annual: tasso risk-free
            - rebalance: frequenza ribilanciamento
            - var_confidence: confidenza VaR
            - risk_intent: livello di rischio dichiarato (v3.0)
            - export: config export
        override: Optional UserAcknowledgment for INCONCLUSIVE verdicts
    
    Returns:
        AnalysisResult: Structured analysis result with quality flags and recommendations.
                       Returns None if run in legacy mode (export only).
    
    Raises:
        DataIntegrityError: If correlation NaN ratio > 20%
        BetaWindowError: If beta window < 3 years
        IntentFailStructureInconclusiveError: If intent fails but structure unknown
    
    Example with override:
        ```python
        from portfolio_engine.utils.exceptions import UserAcknowledgment
        from datetime import datetime
        
        try:
            analyze_portfolio(config)
        except INCONCLUSIVEVerdictError as e:
            logger.error(f"Analysis blocked: {e.verdict_type}")
            logger.info(f"Allowed actions: {e.allowed_actions}")
            
            # Provide explicit override with reason
            ack = UserAcknowledgment(
                timestamp=datetime.now(),
                user_id='analyst_001',
                verdict_type=e.verdict_type,
                reason_for_override='Interim quarterly review with stale data',
                responsibility_acceptance=True
            )
            analyze_portfolio(config, override=ack)
        ```
    """
    # Check if retail mode - skip verbose outputs
    from portfolio_engine.config.user_config import OUTPUT_MODE
    is_retail_mode = OUTPUT_MODE.lower() == 'retail'
    
    logger.info("Starting portfolio analysis")
    
    # === STAGE 1: DATA LOADING & VALIDATION ===
    prices, benchmark_prices, data_integrity, is_provisional, risk_intent = \
        _load_and_validate_data(config)
    
    # === CONFIG ===
    tickers = config["tickers"]
    weights = np.array(config["weights"], dtype=float)
    weights = weights / weights.sum()  # Normalizza a 100%
    risk_free = config["risk_free_annual"]
    rebalance = config.get("rebalance")
    var_conf = config.get("var_confidence", 0.95)
    
    # === STAGE 2: PORTFOLIO METRICS CALCULATION ===
    equity, port_ret, metrics, asset_df, risk_contrib, conditional_ccr = \
        _calculate_portfolio_metrics(
            prices, weights, tickers, rebalance, risk_free, var_conf, data_integrity
        )
    
    # === STAGE 3: CORRELATION ANALYSIS ===
    corr, corr_raw, shrinkage_delta, dual_corr, simple_ret = \
        _analyze_correlations(prices)
    
    # === CORRELAZIONI CONDIZIONALI (normale vs crisi) ===
    portfolio_ret = (simple_ret * weights).sum(axis=1)
    conditional_corr = calculate_conditional_correlations(simple_ret, portfolio_ret)
    
    # === BENCHMARK COMPARISON ===
    # FIX INCONGRUENZA #6: passa portfolio_type per distinguere same-category vs opportunity-cost
    # Rule 8 v4.2: Quick composition estimate for benchmark classification
    benchmark_comparison = None
    if not benchmark_prices.empty:
        # Rule 8: Get quick composition estimate for defensive% and tilts
        quick_comp = quick_composition_estimate(tickers, weights)
        provisional_portfolio_type = 'EQUITY_MULTI_BLOCK'  # Default conservativo
        
        benchmark_comparison = calculate_benchmark_comparison(
            portfolio_returns=port_ret,
            portfolio_metrics=metrics,
            benchmark_prices=benchmark_prices,
            portfolio_type=provisional_portfolio_type,
            total_defensive_pct=quick_comp['total_defensive'],
            has_sector_tilts=quick_comp['has_sector_tilts']
        )
    
    # === CRISIS DETECTION (per Monte Carlo) ===
    crisis_info = detect_crisis_in_data(prices, simple_ret)
    
    if not is_retail_mode and crisis_info['includes_crisis']:
        logger.warning(f"CRISIS DETECTION:")
        logger.warning(f"  I dati includono {len(crisis_info['crisis_periods'])} periodi di crisi:")
        for cp in crisis_info['crisis_periods'][:3]:  # Max 3
            logger.warning(f"  • {cp.get('name', 'Unknown')} ({cp.get('detection', '')})")
        logger.warning(f"  Max Drawdown osservato: {crisis_info['max_drawdown_observed']:.1%}")
        logger.info(f"  → Monte Carlo userà scenari strutturali, non vol doubling")
    
    # === MONTE CARLO STRESS TEST ===
    stress_test = run_monte_carlo_stress_test(
        simple_ret, weights, 
        n_simulations=500,
        includes_crisis=crisis_info['includes_crisis']
    )
    stress_test['crisis_info'] = crisis_info  # Passa info per output
    
    # === TRANSACTION COSTS & TAX DRAG (FIX ISSUES #6, #7) ===
    years_of_data = (prices.index[-1] - prices.index[0]).days / 365.25
    cost_adjustment = calculate_total_cost_adjustment(
        tickers=tickers,
        weights=weights,
        rebalance_frequency=rebalance,
        years=years_of_data,
        investor_country='EU'  # Default EU investor
    )
    metrics_adjusted = adjust_metrics_for_costs(metrics, cost_adjustment)
    
    # Add to metrics for output
    metrics['cost_adjustment'] = cost_adjustment
    metrics['cagr_net'] = metrics_adjusted['cagr_net']
    metrics['sharpe_net'] = metrics_adjusted['sharpe_net']
    
    # Print cost warning if significant
    if not is_retail_mode and cost_adjustment['total_annual_drag'] > 0.005:  # > 0.5%
        logger.info(f"COSTI TRANSAZIONE E FISCALI:")
        logger.info(f"  Rebalancing costs:     {cost_adjustment['rebalancing_costs']['total_cost_annual']:.2%}/anno")
        logger.info(f"  Tax drag (dividendi):  {cost_adjustment['tax_drag']['annual_tax_drag']:.2%}/anno")
        logger.info(f"  ─────────────────────────")
        logger.info(f"  TOTALE:                {cost_adjustment['total_annual_drag']:.2%}/anno")
        logger.info(f"  CAGR Gross → Net:      {metrics['cagr']:.2%} → {metrics['cagr_net']:.2%}")
    
    # === v4.3: VALIDATION FRAMEWORK (Fix C1: Use helper) ===
    validation_results = _run_validation_framework(prices, weights, tickers, metrics)
    
    # Print validation warnings
    if not is_retail_mode:
        for warn in validation_results['warnings']:
            logger.warning(f"{warn['section']}:")
            for line in warn['lines']:
                logger.warning(line)
    
    # === OUTPUT PRINCIPALE - MOVED AFTER GATE SYSTEM ===
    # Will be called after verdict is available
    
    # === ANALISI CRITICITÀ (TYPE-AWARE + REGIME-CONDITIONED) ===
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
        equity_curve=metrics.get('equity_curve'),
        returns=metrics.get('returns')
    )
    
    # FIX INCONGRUENZA #8: Propaga data_integrity al regime_info
    regime_info['data_integrity'] = data_integrity
    if data_integrity.get('is_provisional', False):
        regime_info['analysis_status'] = 'PROVISIONAL'
        # Aggiungi issue critica per visibilità
        issues.insert(0, {
            "type": "DATA_QUALITY_GATE",
            "severity": "🚨",
            "message": f"ANALYSIS PROVISIONAL: {data_integrity.get('nan_removed', 0)} righe con dati incompleti rimossi dopo common-start. Risultati da validare."
        })
    else:
        regime_info['analysis_status'] = 'VALIDATED'
    
    # FIX INCONGRUENZA #C: Verdetti coerenti - INFERIOR benchmark = criticità
    # Se REVIEW_NEEDED, il portafoglio non batte i benchmark same-category → criticità
    if benchmark_comparison:
        overall_verdict = benchmark_comparison.get('overall_verdict', '')
        if overall_verdict == 'REVIEW_NEEDED':
            # Raccoglie i benchmark con verdetto INFERIOR
            inferior_benchmarks = []
            for bench_key, bench_data in benchmark_comparison.get('benchmarks', {}).items():
                if bench_data.get('comparison_type') == 'SAME_CATEGORY':
                    if bench_data.get('verdict') == 'INFERIOR':
                        inferior_benchmarks.append(bench_data.get('name', bench_key))
            
            if inferior_benchmarks:
                issues.insert(0, {
                    "type": "BENCHMARK_UNDERPERFORMANCE",
                    "severity": "🚨",
                    "message": f"INFERIOR vs benchmark same-category: {', '.join(inferior_benchmarks)}. "
                              f"Il portafoglio non giustifica la complessità rispetto ad alternative passive equivalenti."
                })
        
        # Propaga al regime_info per output
        regime_info['benchmark_comparison'] = benchmark_comparison
    
    # RETAIL MODE: Skip verbose analysis outputs
    if not is_retail_mode:
        print_portfolio_critique(issues, regime_info)
    
    # === RISK INTENT ANALYSIS v3.0 ===
    # Analisi completa con Beta-Adjusted Metrics, Drawdown Attribution, Confidence Model
    if not is_retail_mode:
        logger.info("=" * 69)
        logger.info("                 RISK INTENT ANALYSIS v3.0")
        logger.info("=" * 69)
    
    # Prepara benchmark (Fix C1: Use helper)
    benchmark_ret, benchmark_metrics = _prepare_benchmark_metrics(benchmark_prices, benchmark_comparison)
    if benchmark_ret is None:
        benchmark_ret = port_ret  # Fallback: usa portfolio come proxy (beta = 1)
    
    # Run Risk Intent Analysis
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
        risk_intent=risk_intent
    )
    
    # Print Risk Intent Analysis
    if not is_retail_mode:
        print_risk_intent_analysis(risk_analysis)
    
    # === GATE SYSTEM v4.1 ===
    # Investment Committee Validator con priorità logica
    if not is_retail_mode:
        logger.info("=" * 69)
        logger.info("                 GATE SYSTEM v4.1")
        logger.info("=" * 69)
    
    # Prepara intent specs per gate system
    intent_spec = get_risk_intent_spec(risk_intent)
    intent_specs_dict = {
        'beta_range': intent_spec.beta_range,
        'min_beta_acceptable': intent_spec.min_beta_acceptable,
        'beta_fail_threshold': intent_spec.beta_fail_threshold,
        'max_dd_expected': intent_spec.max_dd_expected,
    }
    
    # Prepara gate inputs (Fix C1: Use helper)
    gate_inputs = _prepare_gate_inputs(
        prices, port_ret, simple_ret, data_integrity, issues, benchmark_comparison
    )
    
    # Run Gate Analysis with Exception Enforcement (PRODUCTION_READINESS Issue #1)
    try:
        gate_result = run_gate_analysis(
            corr_matrix=corr,
            portfolio_beta=risk_analysis.get('portfolio_beta', 0.5),
            risk_intent=risk_intent,
            intent_specs=intent_specs_dict,
            tickers=tickers,
            weights=weights,
            ccr_data=risk_contrib,
            benchmark_results=gate_inputs['benchmark_results'],
            asset_metrics=asset_df,
            structural_issues=gate_inputs['structural_issues'],
            beta_window_years=gate_inputs['beta_window_years'],
            crisis_sample_days=gate_inputs['crisis_sample_days'],
            # FIX BUG #3: Pass inception data for NaN distinction
            returns_df=gate_inputs['returns_df'],
            ticker_starts=gate_inputs['ticker_starts'],
            earliest_date=gate_inputs['earliest_date']
        )
    except INCONCLUSIVEVerdictError as e:
        # INCONCLUSIVE verdict detected - requires explicit override
        if override is None:
            # No override provided - block analysis for compliance
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
            raise  # Re-raise to block execution
        
        # Override provided - validate it
        is_valid, validation_error = override.validate()
        if not is_valid:
            logger.error("=" * 80)
            logger.error("⛔ INVALID OVERRIDE")
            logger.error("=" * 80)
            logger.error(f"❌ {validation_error}")
            logger.error("=" * 80)
            raise ValueError(f"Invalid override: {validation_error}") from e
        
        # Validate verdict type matches
        if override.verdict_type != e.verdict_type:
            logger.error("=" * 80)
            logger.error("⛔ OVERRIDE VERDICT MISMATCH")
            logger.error("=" * 80)
            logger.error(f"Expected: {e.verdict_type}")
            logger.error(f"Provided: {override.verdict_type}")
            logger.error("=" * 80)
            raise ValueError(f"Override verdict type '{override.verdict_type}' does not match exception '{e.verdict_type}'") from e
        
        # Log override for audit trail
        log_override(override)
        
        # Print override notification
        logger.warning("=" * 80)
        logger.warning("⚠️  OVERRIDE APPLIED - INCONCLUSIVE VERDICT ACKNOWLEDGED")
        logger.warning("=" * 80)
        logger.warning(f"Verdict Type:    {override.verdict_type}")
        logger.warning(f"Authorized By:   {override.authorized_by}")
        logger.warning(f"Date:            {override.date.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.warning(f"Reason:          {override.reason}")
        if override.expiry_date:
            logger.warning(f"Expires:         {override.expiry_date.strftime('%Y-%m-%d')}")
        logger.warning(f"Analysis will continue with OVERRIDDEN verdict.")
        logger.warning("=" * 80)
        
        # Extract gate_result from exception and mark as overridden
        gate_result = e.gate_result
        gate_result['override_applied'] = True
        gate_result['override_details'] = {
            'authorized_by': override.authorized_by,
            'reason': override.reason,
            'date': override.date.isoformat(),
            'expiry_date': override.expiry_date.isoformat() if override.expiry_date else None
        }
    
    # === v4.3: SOFT CLASSIFICATION (replaces binary TACTICAL/OPPORTUNISTIC) ===
    portfolio_beta = risk_analysis.get('portfolio_beta', 0.8)
    soft_class = calculate_soft_classification(weights, tickers, asset_df, portfolio_beta)
    
    # Print soft classification if conviction is low or different from gate
    if not is_retail_mode and (soft_class.conviction_score < 70 or soft_class.primary_type != gate_result.portfolio_classification.get('type', '')):
        logger.info(f"SOFT CLASSIFICATION (v4.3):")
        logger.info(f"  Core Score:     {soft_class.core_score:.0f}/100")
        logger.info(f"  Tactical Score: {soft_class.tactical_score:.0f}/100")
        logger.info(f"  Conviction:     {soft_class.conviction_score:.0f}/100")
        logger.info(f"  Primary Type:   {soft_class.primary_type} (confidence: {soft_class.confidence:.0%})")
        if soft_class.alternative_types:
            alts = ", ".join([f"{t}({c:.0%})" for t, c in soft_class.alternative_types[:2]])
            logger.info(f"  Alternatives:   {alts}")
        logger.info(f"  {soft_class.reasoning.split(chr(10))[0]}")  # First line of reasoning
    
    # Add to metrics for report
    metrics['soft_classification'] = {
        'core_score': soft_class.core_score,
        'tactical_score': soft_class.tactical_score,
        'conviction_score': soft_class.conviction_score,
        'primary_type': soft_class.primary_type
    }
    
    # Print Gate Analysis
    if not is_retail_mode:
        print_gate_analysis(gate_result)
    
    # Propaga risultati al regime_info
    regime_info['risk_intent_analysis'] = risk_analysis
    regime_info['gate_analysis'] = {
        'data_integrity': gate_result.data_integrity_gate.status.value,
        'intent_gate': gate_result.intent_gate.status.value,
        'structural_gate': gate_result.output_summary.get('Structural Gate', 'UNKNOWN'),
        'final_verdict': gate_result.final_verdict.value,
        'verdict_message': gate_result.verdict_message,
        'why_not_contradictory': gate_result.why_not_contradictory,
        'is_inconclusive': 'INCONCLUSIVE' in gate_result.final_verdict.value,
        'allows_portfolio_action': 'INCONCLUSIVE' not in gate_result.final_verdict.value,
    }
    
    # === BUILD VERDICT INFO FOR RETAIL REPORT (v3.1) ===
    verdict = {
        'type': gate_result.final_verdict.value,
        'confidence': 85 if gate_result.final_verdict.value == 'APPROVED' else 
                     (70 if 'REVIEW' in gate_result.final_verdict.value else 60),
        'message': gate_result.verdict_message,
        'action': gate_result.output_summary.get('Recommended Action', 'Review portfolio configuration')
    }
    
    # === OUTPUT PRINCIPALE (v3.1 - Moved after gate system) ===
    # FIX BUG #1: Pass both raw and shrunk correlation matrices
    # v3.1: Pass verdict_info for retail report
    print_summary(
        metrics, risk_contrib, corr, asset_df, 
        stress_test=stress_test,
        conditional_ccr=conditional_ccr,
        conditional_corr=conditional_corr,
        benchmark_comparison=benchmark_comparison,
        corr_raw=corr_raw,
        shrinkage_intensity=shrinkage_delta,
        verdict_info=verdict
    )
    
    # === SENIOR ARCHITECT ANALYSIS ===
    if not is_retail_mode:
        print_senior_architect_analysis(
            tickers=tickers,
            weights=weights,
            metrics=metrics,
            regime_info=regime_info,
            issues=issues,
            corr=corr
        )
    
    # === EXPORT ===
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
            data_range=data_range
        )
    
    # === ML STRUCTURED EXPORT (v3.1 - Professional Mode Only) ===
    from portfolio_engine.config.user_config import OUTPUT_MODE
    if OUTPUT_MODE.lower() == 'professional':
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)
        ml_export_path = export_ml_structured(
            output_dir=output_dir,
            metrics=metrics,
            risk_contrib=risk_contrib,
            asset_metrics=asset_df,
            corr=corr,
            corr_raw=corr_raw,
            verdict_info=verdict,
            regime_info=regime_info
        )
        logger.info(f"ML structured export saved: {ml_export_path}")
    
    # === GRAFICI ===
    # Salva sempre il grafico base
    os.makedirs('output', exist_ok=True)
    plot_results(equity, port_ret, save_path='output/portfolio_analysis.png')
    
    # === STRUCTURED OUTPUT (Issue #3) ===
    # Build machine-readable result for programmatic validation
    analysis_result = _build_structured_result(
        config=config,
        gate_result=gate_result,
        metrics=metrics,
        risk_analysis=risk_analysis,
        tickers=tickers,
        weights=weights
    )
    
    # Save JSON output
    json_path = 'output/analysis_result.json'
    os.makedirs('output', exist_ok=True)
    analysis_result.save_json(json_path)
    logger.info(f"Structured output saved: {json_path}")
    
    # Validation check
    is_valid, issues = analysis_result.validate_for_production()
    if not is_valid:
        logger.warning(f"PRODUCTION VALIDATION WARNINGS:")
        for issue in issues:
            logger.warning(f"  • {issue}")
    
    return analysis_result


def run_analysis_to_pdf(
    config: Dict[str, Any],
    pdf_path: str = "output/analisi.pdf",
    override: Optional[UserAcknowledgment] = None
) -> None:
    """
    Esegue l'analisi e salva l'output in PDF.
    
    Args:
        config: Configurazione portafoglio
        pdf_path: Percorso file PDF di output
        override: Override per verdetti INCONCLUSIVE (opzionale)
    
    Raises:
        INCONCLUSIVEVerdictError: Se il Gate System ritorna INCONCLUSIVE e non è fornito override
        ValueError: Se override fornito non è valido
    
    Example:
        # Normal execution (will raise exception if INCONCLUSIVE)
        run_analysis_to_pdf(config)
        
        # With override for INCONCLUSIVE verdict
        override = UserAcknowledgment(
            verdict_type='INCONCLUSIVE_DATA_FAIL',
            authorized_by='John Doe',
            reason='Acknowledged high NaN ratio - portfolio under construction',
            date=datetime.now()
        )
        run_analysis_to_pdf(config, override=override)
    """
    # Cattura stdout
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    
    try:
        # Esegui analisi (output va in captured_output)
        analyze_portfolio(config, override=override)
    except INCONCLUSIVEVerdictError:
        # Restore stdout before re-raising to show error message
        sys.stdout = old_stdout
        raise
    finally:
        # Ripristina stdout
        sys.stdout = old_stdout
    
    # Ottieni testo catturato
    output_text = captured_output.getvalue()
    
    # Genera PDF
    pdf_file = generate_pdf_report(
        output_text=output_text,
        output_path=pdf_path,
        chart_path='output/portfolio_analysis.png'
    )
    
    logger.info(f"Report PDF generato: {pdf_file.absolute()}")


# =========================
# MAIN ENTRY POINT
# =========================

if __name__ == "__main__":
    CONFIG = get_config()
    
    # Genera output in PDF
    run_analysis_to_pdf(CONFIG, pdf_path="output/analisi.pdf")
