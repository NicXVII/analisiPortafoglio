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
import json
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
)

# Production Readiness: Structured Output (Issue #3)
from portfolio_engine.models.portfolio import (
    AnalysisResult,
)

from portfolio_engine.data.loader import (
    download_data,
    calculate_start_date,
    simulate_portfolio_correct,
    check_survivorship_bias_warning,
    validate_data_integrity,
    DATA_START_POLICY,
)
from portfolio_engine.core.storage_runner import auto_save_portfolio
from portfolio_engine.core.pipeline_runner import run_pipeline
from portfolio_engine.core.diagnostics_runner import run_diagnostics
from portfolio_engine.core.gate_runner import run_risk_intent_and_gate
from portfolio_engine.core.output_runner import emit_outputs
from portfolio_engine.core.pipeline import (
    _load_and_validate_data,
    _calculate_portfolio_metrics,
    _analyze_correlations,
)

from portfolio_engine.reporting.export import generate_pdf_report

# v3.0: Risk Intent Analysis
from portfolio_engine.decision.risk_intent import (
    validate_risk_intent,
)

# v4.1: Gate System
from portfolio_engine.decision.gate_system import (
    GateStatus,
    FinalVerdictType,
)

# v4.3: Validation Framework (RAW/REG, Walk-Forward, Soft Labels)
from portfolio_engine.decision.validation import (
    create_dual_correlation,
    DualCorrelationMatrix,
    CorrelationUseCase,
    run_walk_forward_validation,
    analyze_rolling_stability,
    run_out_of_sample_stress,
)

# Per catturare output per PDF
import sys
from io import StringIO

# === PIPELINE IMPORTS (Refactor: 2026-01-09) ===
# Estratte 7 funzioni helper/stage in pipeline.py per ridurre dimensione main.py
# Note: pipeline stage helpers are encapsulated in pipeline_runner/diagnostics_runner.

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

    # === PORTFOLIO STORAGE (AUTO-SAVE) ===
    auto_save_portfolio(config, logger)

    # === PIPELINE (LOAD + METRICS + CORRELATIONS) ===
    pipeline = run_pipeline(config)
    prices = pipeline["prices"]
    benchmark_prices = pipeline["benchmark_prices"]
    data_integrity = pipeline["data_integrity"]
    risk_intent = pipeline["risk_intent"]
    tickers = pipeline["tickers"]
    weights = pipeline["weights"]
    rebalance = pipeline["rebalance"]
    equity = pipeline["equity"]
    port_ret = pipeline["port_ret"]
    metrics = pipeline["metrics"]
    asset_df = pipeline["asset_df"]
    risk_contrib = pipeline["risk_contrib"]
    conditional_ccr = pipeline["conditional_ccr"]
    corr = pipeline["corr"]
    corr_raw = pipeline["corr_raw"]
    shrinkage_delta = pipeline["shrinkage_delta"]
    simple_ret = pipeline["simple_ret"]
    optimization_result = pipeline.get("optimization")
    data_quality = pipeline.get("data_quality")
    
    diagnostics = run_diagnostics(
        prices=prices,
        benchmark_prices=benchmark_prices,
        simple_ret=simple_ret,
        port_ret=port_ret,
        tickers=tickers,
        weights=weights,
        corr=corr,
        risk_contrib=risk_contrib,
        asset_df=asset_df,
        metrics=metrics,
        data_integrity=data_integrity,
        rebalance=rebalance,
        is_retail_mode=is_retail_mode,
        logger=logger,
    )
    benchmark_comparison = diagnostics["benchmark_comparison"]
    stress_test = diagnostics["stress_test"]
    conditional_corr = diagnostics["conditional_corr"]
    issues = diagnostics["issues"]
    regime_info = diagnostics["regime_info"]
    
    gate_result, risk_analysis, verdict = run_risk_intent_and_gate(
        prices=prices,
        benchmark_prices=benchmark_prices,
        benchmark_comparison=benchmark_comparison,
        port_ret=port_ret,
        simple_ret=simple_ret,
        tickers=tickers,
        weights=weights,
        corr=corr,
        risk_contrib=risk_contrib,
        asset_df=asset_df,
        metrics=metrics,
        risk_intent=risk_intent,
        data_integrity=data_integrity,
        issues=issues,
        regime_info=regime_info,
        override=override,
        is_retail_mode=is_retail_mode,
        logger=logger,
    )

    analysis_result = emit_outputs(
        config=config,
        prices=prices,
        equity=equity,
        port_ret=port_ret,
        metrics=metrics,
        risk_contrib=risk_contrib,
        asset_df=asset_df,
        corr=corr,
        corr_raw=corr_raw,
        shrinkage_delta=shrinkage_delta,
        stress_test=stress_test,
        conditional_ccr=conditional_ccr,
        conditional_corr=conditional_corr,
        benchmark_comparison=benchmark_comparison,
        verdict=verdict,
        is_retail_mode=is_retail_mode,
        tickers=tickers,
        weights=weights,
        regime_info=regime_info,
        issues=issues,
        gate_result=gate_result,
        risk_analysis=risk_analysis,
        optimization=optimization_result,
        data_quality=data_quality,
        logger=logger,
    )

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
