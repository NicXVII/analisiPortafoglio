"""
Pipeline Module
===============
Execution stages e helper functions per analyze_portfolio().

Estratto da main.py per ridurre complessità orchestratore.
Questo modulo contiene:
- Stage functions: _load_and_validate_data, _calculate_portfolio_metrics, _analyze_correlations
- Helper functions: _build_structured_result, _run_validation_framework, _prepare_gate_inputs, _prepare_benchmark_metrics

Refactored: 2026-01-09
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

# === LOGGING ===
from portfolio_engine.utils.logger import get_logger, log_performance
logger = get_logger(__name__)

# === IMPORTS DAI MODULI ===
from portfolio_engine.config.user_config import get_config

# Models and exceptions
from portfolio_engine.models.portfolio import (
    AnalysisResult,
    MetricsSnapshot,
    PrescriptiveAction,
    PortfolioStructureType
)
from portfolio_engine.decision.gate_system import GateAnalysisResult

from portfolio_engine.analytics.metrics import (
    calculate_simple_returns,
    calculate_cagr_correct,
    calculate_annualized_volatility,
    calculate_all_metrics,
    calculate_risk_contribution_correct,
    calculate_conditional_risk_contribution,
    calculate_shrunk_correlation
)

from portfolio_engine.data.loader import (
    download_data,
    calculate_start_date,
    simulate_portfolio_correct,
    check_survivorship_bias_warning,
    validate_data_integrity,
    get_currency_map,
    convert_to_base_currency,
    check_staleness,
)

from portfolio_engine.decision.risk_intent import (
    get_risk_intent_spec,
    validate_risk_intent
)

from portfolio_engine.decision.validation import (
    create_dual_correlation,
    run_walk_forward_validation,
    analyze_rolling_stability,
    run_out_of_sample_stress
)


# =========================
# HELPER FUNCTIONS
# =========================

def _build_structured_result(
    config: Dict[str, Any],
    gate_result: Any,
    metrics: Dict[str, Any],
    risk_analysis: Dict[str, Any],
    tickers: List[str],
    weights: np.ndarray
) -> AnalysisResult:
    """
    Build structured AnalysisResult from analysis components.
    
    Part of Issue #3: Structured Output.
    
    Args:
        config: Portfolio configuration
        gate_result: Gate system result
        metrics: Calculated metrics dict
        risk_analysis: Risk intent analysis result
        tickers: List of tickers
        weights: Portfolio weights
    
    Returns:
        AnalysisResult: Structured, machine-readable result
    """
    # Extract metrics snapshot
    # NOTE (Fix O1): metrics dict espone solo varianti annualizzate.
    # Mappiamo i campi snapshot sulle chiavi corrette per evitare var_95/cvar_95 a 0.0.
    metrics_snapshot = MetricsSnapshot(
        cagr=metrics.get('cagr', 0.0),
        sharpe=metrics.get('sharpe', 0.0),
        sortino=metrics.get('sortino', 0.0),
        max_drawdown=metrics.get('max_drawdown', 0.0),
        volatility=metrics.get('volatility', 0.0),
        var_95=metrics.get('var_95_annual', metrics.get('var_95', 0.0)),
        cvar_95=metrics.get('cvar_95_annual', metrics.get('cvar_95', 0.0)),
        cagr_ci_lower=metrics.get('cagr_ci', {}).get('ci_lower') if metrics.get('cagr_ci') else None,
        cagr_ci_upper=metrics.get('cagr_ci', {}).get('ci_upper') if metrics.get('cagr_ci') else None,
        sharpe_ci_lower=metrics.get('sharpe_ci', {}).get('ci_lower') if metrics.get('sharpe_ci') else None,
        sharpe_ci_upper=metrics.get('sharpe_ci', {}).get('ci_upper') if metrics.get('sharpe_ci') else None,
        calmar_ratio=metrics.get('calmar_ratio'),
        profit_factor=metrics.get('profit_factor'),
        win_rate_monthly=metrics.get('win_rate_monthly')
    )

    # Extract prescriptive actions
    prescriptive_actions: List[PrescriptiveAction] = []
    seen_keys = set()

    def _add_action(raw_action: Any):
        """Normalizza e deduplica le prescriptive actions (Fix O2)."""
        if raw_action is None:
            return
        if isinstance(raw_action, PrescriptiveAction):
            action_obj = raw_action
        elif isinstance(raw_action, dict):
            action_obj = PrescriptiveAction(
                issue_code=raw_action.get('issue_code', 'UNKNOWN'),
                priority=raw_action.get('priority', 'MEDIUM'),
                confidence=raw_action.get('confidence', 0.5),
                description=raw_action.get('description', ''),
                actions=raw_action.get('actions', []),
                blockers=raw_action.get('blockers', []),
                data_quality_impact=raw_action.get('data_quality_impact', 'NONE')
            )
        else:
            return

        key = (action_obj.issue_code, action_obj.description)
        if key not in seen_keys:
            seen_keys.add(key)
            prescriptive_actions.append(action_obj)

    for action in getattr(gate_result, 'prescriptive_actions', []):
        _add_action(action)

    # Integra eventuali azioni provenienti dall'analisi di intent/risk (se presenti)
    for action in risk_analysis.get('prescriptive_actions', []):
        _add_action(action)

    logger.debug("Prescriptive actions collected: %d", len(prescriptive_actions))
    
    # Determine structure type
    structure_type = gate_result.structure_type if hasattr(gate_result, 'structure_type') else PortfolioStructureType.GLOBAL_CORE
    
    # Build composition dict
    portfolio_composition = {ticker: float(weight) for ticker, weight in zip(tickers, weights)}
    
    # Extract data quality issues
    data_quality_issues = []
    if hasattr(gate_result, 'data_integrity_gate'):
        data_gate = gate_result.data_integrity_gate
        if hasattr(data_gate, 'details'):
            blocked = data_gate.details.get('blocked_analyses', [])
            data_quality_issues.extend(blocked)
    
    # Calculate quality score (0-100)
    quality_score = 100
    if 'INCONCLUSIVE' in gate_result.final_verdict.value:
        quality_score -= 40
    if len(data_quality_issues) > 0:
        quality_score -= min(30, len(data_quality_issues) * 10)
    # Use structure_confidence as proxy for overall confidence
    structure_conf = gate_result.structure_confidence if hasattr(gate_result, 'structure_confidence') else 0.7
    if structure_conf < 0.7:
        quality_score -= int((0.7 - structure_conf) * 50)
    quality_score = max(0, quality_score)
    
    # Determine allowed/prohibited actions
    is_inconclusive = 'INCONCLUSIVE' in gate_result.final_verdict.value
    allowed_actions = [] if is_inconclusive else [
        "Portfolio restructuring",
        "Asset rebalancing",
        "Risk adjustment"
    ]
    prohibited_actions = [
        "Portfolio restructuring",
        "Major allocation changes"
    ] if is_inconclusive else []
    
    # Build result
    # Use structure_confidence scaled to 0-100 as verdict_confidence
    structure_conf = gate_result.structure_confidence if hasattr(gate_result, 'structure_confidence') else 0.7
    verdict_confidence = int(structure_conf * 100)
    
    return AnalysisResult(
        verdict=gate_result.final_verdict,
        verdict_message=gate_result.verdict_message,
        verdict_confidence=verdict_confidence,
        risk_intent=config.get('risk_intent', 'GROWTH'),
        structure_type=structure_type,
        portfolio_composition=portfolio_composition,
        metrics=metrics_snapshot,
        is_actionable=not is_inconclusive,
        data_quality_issues=data_quality_issues,
        quality_score=quality_score,
        prescriptive_actions=prescriptive_actions,
        allowed_actions=allowed_actions,
        prohibited_actions=prohibited_actions,
        analysis_timestamp=datetime.now(),
        portfolio_id=config.get('portfolio_id')
    )


def _run_validation_framework(
    prices: pd.DataFrame,
    weights: np.ndarray,
    tickers: List[str],
    metrics: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Run complete validation framework (Fix C1: Decomposition).
    
    Includes:
    - Walk-forward validation
    - Rolling stability analysis
    - Out-of-sample stress test
    
    Returns:
        dict with validation results and any warnings to print
    """
    warnings_to_print = []
    
    # Walk-forward validation
    walk_forward = run_walk_forward_validation(prices, weights, tickers)
    if walk_forward.stability_score < 75:
        warnings_to_print.append({
            'section': '🔬 WALK-FORWARD VALIDATION',
            'lines': [
                f"   Stability Score: {walk_forward.stability_score:.0f}/100",
                f"   {walk_forward.interpretation}"
            ]
        })
    
    # Rolling stability analysis
    rolling_stability = analyze_rolling_stability(prices, weights)
    if rolling_stability.regime_changes_detected > 3:
        warnings_to_print.append({
            'section': '📈 ROLLING STABILITY',
            'lines': [
                f"   Regime changes detected: {rolling_stability.regime_changes_detected}",
                f"   Correlation stability: {rolling_stability.correlation_stability:.0%}"
            ]
        })
    
    # Out-of-sample stress test
    oos_stress = run_out_of_sample_stress(prices, weights)
    if oos_stress.get('valid', False):
        metrics['oos_validation'] = oos_stress
        if not oos_stress.get('passed_validation', True):
            warnings_to_print.append({
                'section': '⚠️ OUT-OF-SAMPLE WARNING',
                'lines': [
                    f"   {oos_stress['interpretation']}",
                    f"   Train Sharpe: {oos_stress['train_sharpe']:.2f} → Test: {oos_stress['test_sharpe']:.2f}"
                ]
            })
    
    return {
        'walk_forward': walk_forward,
        'rolling_stability': rolling_stability,
        'oos_stress': oos_stress,
        'warnings': warnings_to_print
    }


def _prepare_gate_inputs(
    prices: pd.DataFrame,
    port_ret: pd.Series,
    simple_ret: pd.DataFrame,
    data_integrity: Dict[str, Any],
    issues: List[Dict[str, Any]],
    benchmark_comparison: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Prepare all inputs needed for Gate System (Fix C1: Decomposition).
    
    Returns:
        dict with all gate input parameters
    """
    # Beta window years (Rule 2 & 3)
    beta_window_years = (prices.index[-1] - prices.index[0]).days / 365.25
    
    # Crisis sample days (Rule 6)
    crisis_sample_days = len(port_ret[port_ret < port_ret.quantile(0.05)])
    
    # Inception info for NaN distinction (Fix Bug #3)
    ticker_starts = data_integrity.get('ticker_starts', {})
    staggered_info = data_integrity.get('staggered_info', {})
    earliest_date = staggered_info.get('earliest_data') or str(prices.index[0].date())
    
    # Structural issues extraction
    structural_issues_list = [
        issue['message'] for issue in issues 
        if issue.get('severity') in ['🚨', '⚠️'] and 
           issue.get('type') not in ['DATA_QUALITY_GATE', 'BENCHMARK_UNDERPERFORMANCE']
    ]
    
    # Benchmark results for gate
    benchmark_results_for_gate = {'benchmarks': {}}
    if benchmark_comparison and 'benchmarks' in benchmark_comparison:
        for k, v in benchmark_comparison['benchmarks'].items():
            benchmark_results_for_gate['benchmarks'][k] = {
                'excess_return': v.get('excess_return', 0),
                'information_ratio': v.get('information_ratio', 0),
                'tracking_error': v.get('tracking_error', 0),
            }
    
    return {
        'beta_window_years': beta_window_years,
        'crisis_sample_days': crisis_sample_days,
        'ticker_starts': ticker_starts,
        'earliest_date': earliest_date,
        'structural_issues': structural_issues_list,
        'benchmark_results': benchmark_results_for_gate,
        'returns_df': simple_ret
    }


def _prepare_benchmark_metrics(
    benchmark_prices: pd.DataFrame,
    benchmark_comparison: Dict[str, Any]
) -> Tuple[Optional[pd.Series], Dict[str, float]]:
    """
    Prepare benchmark returns and metrics (Fix C1: Decomposition).
    
    Returns:
        tuple: (benchmark_returns, benchmark_metrics_dict)
    """
    # Benchmark returns
    if 'VT' in benchmark_prices.columns:
        benchmark_ret = calculate_simple_returns(benchmark_prices[['VT']])['VT']
    elif not benchmark_prices.empty:
        benchmark_ret = calculate_simple_returns(benchmark_prices.iloc[:, :1]).iloc[:, 0]
    else:
        benchmark_ret = None  # Will use portfolio as proxy
    
    # Benchmark metrics
    if benchmark_comparison and 'benchmarks' in benchmark_comparison:
        vt_bench = benchmark_comparison['benchmarks'].get('VT', {})
        benchmark_metrics = {
            'max_drawdown': vt_bench.get('max_dd', -0.34),
            'volatility': vt_bench.get('volatility', 0.15),
            'sharpe': vt_bench.get('sharpe', 0.45),
            'sortino': vt_bench.get('sortino', 0.60),
        }
    else:
        benchmark_metrics = {
            'max_drawdown': -0.34,
            'volatility': 0.15,
            'sharpe': 0.45,
            'sortino': 0.60,
        }
    
    return benchmark_ret, benchmark_metrics


# =========================
# STAGE 1: DATA LOADING & VALIDATION
# =========================

@log_performance(logger)
def _load_and_validate_data(config: Dict[str, Any]) -> Tuple[pd.DataFrame, pd.DataFrame, Dict, bool, str, Dict]:
    """
    Stage 1: Load and validate portfolio and benchmark data.
    
    Performs:
    - Config parsing and validation
    - Risk intent validation
    - Data download (portfolio + benchmarks)
    - Data integrity checks
    - Survivorship bias warning
    
    Args:
        config: Portfolio configuration dictionary
        
    Returns:
        prices: Portfolio price DataFrame
        benchmark_prices: Benchmark price DataFrame
        data_integrity: Data integrity info dict
        is_provisional: Whether analysis is provisional
        risk_intent: Validated risk intent string
        
    Raises:
        ValueError: Invalid configuration
        RuntimeError: Data download or validation errors
    """
    # === CONFIG ===
    tickers = config["tickers"]
    weights = np.array(config["weights"], dtype=float)
    years = config.get("years_history", 5)
    end = config["end_date"]
    start = config["start_date"] or calculate_start_date(years, end)
    start_dt = datetime.strptime(start, "%Y-%m-%d") if isinstance(start, str) else start
    risk_intent = config.get("risk_intent", "GROWTH")
    
    # === RISK INTENT VALIDATION ===
    is_valid, intent_msg = validate_risk_intent(risk_intent)
    if not is_valid:
        logger.warning(f"{intent_msg}")
        risk_intent = "GROWTH"
    
    intent_spec = get_risk_intent_spec(risk_intent)
    logger.info(f"RISK INTENT: {risk_intent}")
    logger.info(f"  {intent_spec.description}")
    logger.info(f"  Beta atteso: {intent_spec.beta_range[0]:.1f} - {intent_spec.beta_range[1]:.1f}")
    logger.info(f"  Benchmark naturale: {intent_spec.benchmark}")
    logger.info(f"  Max DD atteso: {intent_spec.max_dd_expected:.0%}")
    
    # === VALIDAZIONE ===
    if len(tickers) != len(weights):
        raise ValueError("Tickers e weights devono avere stessa lunghezza")
    
    # === DOWNLOAD DATI ===
    logger.info(f"Downloading data for {len(tickers)} tickers...")
    prices = download_data(tickers, start, end)

    # FX conversion to base currency (if multiple currencies)
    fx_config = config.get("fx", {})
    base_ccy = fx_config.get("base_currency", "USD")
    currency_map = get_currency_map(tickers)
    prices, fx_info = convert_to_base_currency(
        prices,
        currency_map,
        base_currency=base_ccy,
        manual_rates=fx_config.get("manual_rates", {}),
        warn_on_missing=fx_config.get("warn_on_missing", True),
        return_info=True,
    )

    # Staleness check
    staleness_msg = check_staleness(prices, limit_days=fx_config.get("stale_days_warning", 3))
    is_provisional = False
    if staleness_msg:
        logger.warning(f"DATA STALENESS: {staleness_msg}")
        is_provisional = True
    if fx_info.get("missing") or fx_info.get("skipped"):
        is_provisional = True
    
    # === DOWNLOAD BENCHMARK ===
    logger.info("Downloading benchmark data (VT, SPY, BND)...")
    benchmark_tickers = ['VT', 'SPY', 'BND']
    bench_to_download = [t for t in benchmark_tickers if t not in tickers]
    benchmark_prices = download_data(bench_to_download, start, end) if bench_to_download else pd.DataFrame()

    # Convert benchmark to base currency too
    if not benchmark_prices.empty:
        bench_currency_map = get_currency_map(list(benchmark_prices.columns))
        benchmark_prices, bench_fx_info = convert_to_base_currency(
            benchmark_prices,
            bench_currency_map,
            base_currency=base_ccy,
            manual_rates=fx_config.get("manual_rates", {}),
            warn_on_missing=fx_config.get("warn_on_missing", True),
            return_info=True,
        )
    else:
        bench_fx_info = {"missing": [], "converted": [], "skipped": []}
    
    # Merge con quelli già scaricati
    for t in benchmark_tickers:
        if t in prices.columns and t not in benchmark_prices.columns:
            benchmark_prices[t] = prices[t]
    
    # === VALIDAZIONE DATI ===
    if prices.empty:
        raise RuntimeError("Nessun dato scaricato")
    
    missing = [t for t in tickers if t not in prices.columns]
    if missing:
        raise RuntimeError(f"Mancano dati per: {missing}")
    
    empty_cols = [c for c in prices.columns if prices[c].isna().all()]
    dropped_tickers: list[str] = []
    weights_used = weights.copy()
    if empty_cols:
        dropped_tickers = [t for t in empty_cols if t in tickers]
        if dropped_tickers:
            logger.warning(f"Ticker vuoti (drop): {dropped_tickers}")
            keep_mask = [t not in dropped_tickers for t in tickers]
            if not any(keep_mask):
                raise RuntimeError(f"Tutti i ticker sono vuoti: {dropped_tickers}")
            # Drop from prices and adjust tickers/weights
            prices = prices.drop(columns=dropped_tickers, errors="ignore")
            tickers = [t for t in tickers if t not in dropped_tickers]
            weights_used = np.array(weights)[keep_mask]
            weights_used = weights_used / weights_used.sum()
            is_provisional = True
        else:
            raise RuntimeError(f"Ticker vuoti: {empty_cols}")
    
    # === DATA INTEGRITY LAYER ===
    prices, data_integrity = validate_data_integrity(prices, tickers)
    
    logger.info(f"DATA INTEGRITY ({data_integrity['policy']}):")
    logger.info(f"  {data_integrity['policy_description']}")
    
    if data_integrity['policy'] == 'STAGGERED_ENTRY' and 'staggered_info' in data_integrity:
        stag = data_integrity['staggered_info']
        logger.info(f"  Earliest data: {stag.get('earliest_data', 'N/A')}")
        logger.info(f"  Latest inception: {stag.get('latest_inception', 'N/A')} (common start)")
    else:
        logger.info(f"  Common start: {data_integrity['common_start']}")
    
    for warning in data_integrity.get('warnings', []):
        logger.warning(f"  {warning}")

    if dropped_tickers:
        data_integrity["dropped_tickers"] = dropped_tickers
        data_integrity["tickers_used"] = tickers
        data_integrity["weights_used"] = weights_used.tolist()
        data_integrity["warnings"].append(
            f"⚠️ Ticker rimossi per dati vuoti: {dropped_tickers}. "
            "Pesi rinormalizzati sui ticker rimanenti."
        )
    
    # === DATA QUALITY GATE ===
    is_provisional = False
    if data_integrity.get('data_quality_issue', False):
        nan_removed = data_integrity.get('nan_removed', 0)
        nan_threshold = 5
        
        if nan_removed >= nan_threshold:
            logger.error("DATA QUALITY GATE FAILED:")
            logger.error(f"  {nan_removed} righe con dati incompleti rimossi dopo common-start.")
            logger.error(f"  Questo indica problemi di integrità dati significativi.")
            logger.warning(f"  L'ANALISI PROCEDE MA È MARCATA COME 'PROVISIONAL'.")
            is_provisional = True
        else:
            logger.warning(f"DATA QUALITY: {nan_removed} righe con dati incompleti rimossi.")
    
    logger.info(f"Data range: {prices.index[0].date()} to {prices.index[-1].date()}")
    logger.info(f"Trading days: {len(prices)}")
    if is_provisional:
        logger.warning(f"STATUS: PROVISIONAL ANALYSIS (data quality issues detected)")
    
    # Passa is_provisional al data_integrity
    data_integrity['is_provisional'] = is_provisional
    
    # === SURVIVORSHIP BIAS CHECK ===
    simple_returns_preview = prices.pct_change().dropna()
    surv_bias = check_survivorship_bias_warning(
        tickers=tickers,
        returns=simple_returns_preview,
        start_date=start_dt
    )
    if surv_bias['warning_level'] != 'LOW':
        logger.warning(f"{surv_bias['message']}")
    data_integrity['survivorship'] = surv_bias
    
    # Data quality bundle
    data_quality = {
        "staleness": staleness_msg,
        "fx": fx_info,
        "benchmark_fx": bench_fx_info,
        "survivorship": surv_bias,
    }
    
    return prices, benchmark_prices, data_integrity, is_provisional, risk_intent, data_quality


# =========================
# STAGE 2: PORTFOLIO METRICS CALCULATION
# =========================

@log_performance(logger)
def _calculate_portfolio_metrics(
    prices: pd.DataFrame,
    weights: np.ndarray,
    tickers: List[str],
    rebalance: str,
    risk_free: float,
    var_conf: float,
    data_integrity: Dict,
    fees_config: Dict | None = None,
    bias_config: Dict | None = None,
    var_method: str = "historical",
    var_bootstrap_samples: int = 0,
) -> Tuple[pd.Series, pd.Series, Dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Stage 2: Calculate portfolio and asset-level metrics.
    
    Args:
        prices: Price DataFrame
        weights: Portfolio weights
        tickers: List of tickers
        rebalance: Rebalance frequency
        risk_free: Risk-free rate
        var_conf: VaR confidence level
        data_integrity: Data integrity info
        
    Returns:
        equity: Portfolio equity curve
        port_ret: Portfolio returns
        metrics: Portfolio metrics dict
        asset_df: Asset-level metrics DataFrame
        risk_contrib: Risk contribution DataFrame
        conditional_ccr: Conditional risk contribution
    """
    # Simulazione portafoglio
    use_staggered = (data_integrity.get('policy') == 'STAGGERED_ENTRY')
    equity, port_ret = simulate_portfolio_correct(prices, weights, rebalance, staggered_entry=use_staggered)

    # Applica costi/fee annuali (bps) se configurati
    fees_config = fees_config or {}
    fee_bps = float(fees_config.get("annual_fee_bps", 0.0))
    if fee_bps > 0:
        daily_fee = (fee_bps / 10000.0) / 252.0
        port_ret = port_ret - daily_fee
        equity = (1 + port_ret).cumprod()
    
    # Calcolo metriche portfolio
    metrics = calculate_all_metrics(
        equity,
        port_ret,
        risk_free,
        var_conf,
        var_method=var_method,
        var_bootstrap_samples=var_bootstrap_samples,
    )

    # Applicazione haircut per survivorship bias (se configurato)
    survivorship = data_integrity.get("survivorship")
    bias_config = bias_config or {}
    if bias_config.get("apply_survivorship_haircut", False) and survivorship:
        conf = float(survivorship.get("confidence_score", 0.85))
        max_penalty = float(bias_config.get("max_annual_penalty", 0.03))
        # scala lineare: se conf ≤0.30 → penalità massima; conf ≥0.85 → zero
        factor = max(0.0, min(1.0, (0.85 - conf) / (0.85 - 0.30)))
        annual_penalty = max_penalty * factor
        if annual_penalty > 0:
            daily_penalty = annual_penalty / 252.0
            port_ret_adj = port_ret - daily_penalty
            equity_adj = (1 + port_ret_adj).cumprod()
            metrics = calculate_all_metrics(
                equity_adj,
                port_ret_adj,
                risk_free,
                var_conf,
                var_method=var_method,
                var_bootstrap_samples=var_bootstrap_samples,
            )
            metrics["survivorship_penalty_applied"] = annual_penalty
            metrics["survivorship_confidence"] = conf
            port_ret = port_ret_adj
            equity = equity_adj
    
    # Metriche per asset
    simple_ret = calculate_simple_returns(prices)
    
    asset_cagr = {}
    asset_vol = {}
    for t in tickers:
        asset_eq = (1 + simple_ret[t]).cumprod()
        asset_cagr[t] = calculate_cagr_correct(asset_eq)
        asset_vol[t] = calculate_annualized_volatility(simple_ret[t])
    
    # Risk contribution
    risk_contrib = calculate_risk_contribution_correct(simple_ret, weights, tickers)
    conditional_ccr = calculate_conditional_risk_contribution(simple_ret, weights, tickers)
    
    # Asset summary
    asset_df = pd.DataFrame({
        "Weight": weights,
        "CAGR": [asset_cagr[t] for t in tickers],
        "Vol": [asset_vol[t] for t in tickers],
    }, index=tickers)
    
    asset_df = asset_df.join(risk_contrib[['CCR%']].rename(columns={'CCR%': 'RiskContrib%'}))
    
    return equity, port_ret, metrics, asset_df, risk_contrib, conditional_ccr


# =========================
# STAGE 3: CORRELATION ANALYSIS
# =========================

@log_performance(logger)
def _analyze_correlations(
    prices: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame, float, Any, pd.Series]:
    """
    Stage 3: Calculate correlation matrices with shrinkage.
    
    Args:
        prices: Price DataFrame
        
    Returns:
        corr: Shrunk correlation (for calculations)
        corr_raw: Raw correlation (for diagnosis)
        shrinkage_delta: Shrinkage intensity
        dual_corr: Dual-correlation framework object
        simple_ret: Simple returns DataFrame
    """
    simple_ret = calculate_simple_returns(prices)
    
    # Correlazione raw e shrunk
    corr_raw = simple_ret.corr()
    corr_shrunk, shrinkage_delta = calculate_shrunk_correlation(simple_ret)
    
    # Dual-correlation framework
    dual_corr = create_dual_correlation(simple_ret, corr_raw, corr_shrunk, shrinkage_delta)
    
    # Usa correlazione shrunk per calcoli (più stabile)
    corr = corr_shrunk
    
    # Warning se shrinkage significativo
    if shrinkage_delta is not None and abs(shrinkage_delta) > 0.05:
        logger.info(f"DUAL-CORRELATION FRAMEWORK (v4.3):")
        logger.info(f"  Ledoit-Wolf shrinkage intensity: {shrinkage_delta:.1%}")
        diagnosis = dual_corr.get_diagnosis_summary()
        logger.info(f"  Avg correlation RAW: {diagnosis['avg_corr_raw']:.2f} | REG: {diagnosis['avg_corr_reg']:.2f}")
        logger.info(f"  Framework rule: RAW for diagnosis, REG for calculations")
        if diagnosis['n_high_corr'] > 0:
            logger.warning(f"  {diagnosis['n_high_corr']} high-correlation pairs detected (RAW)")
        logger.info(f"  Interpretation: {diagnosis['interpretation'][:100]}...")
    
    return corr, corr_raw, shrinkage_delta, dual_corr, simple_ret
