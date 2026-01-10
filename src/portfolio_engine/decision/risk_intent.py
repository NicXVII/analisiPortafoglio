"""
Risk Intent Module v3.0
=======================
Implementazione delle specifiche da response.md:
- Risk Intent Declaration
- Beta-Adjusted Metrics
- Drawdown Attribution (Structural vs Regime)
- Confidence Model con Gating Rules
- Sottotipi TACTICAL (Factor, Sector, Timing)
- Verdetti Rule-Based

Questo modulo è OBBLIGATORIO per l'analisi v3.0.

Type Safety Migration (Issue #2):
- Uses RiskIntentLevel and RiskIntentSpec from models.py
- Returns typed dataclasses instead of dicts
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# Import from models.py for type safety
from portfolio_engine.models.portfolio import RiskIntentLevel, RiskIntentSpec, FinalVerdictType


# ================================================================================
# SEZIONE 0: RISK INTENT DECLARATION
# ================================================================================

# Definizioni Risk Intent con HARD CONSTRAINTS
# REGOLA: Il Risk Intent è DICHIARATO ex-ante, MAI derivato dai dati
RISK_INTENT_SPECS = {
    RiskIntentLevel.CONSERVATIVE: RiskIntentSpec(
        level=RiskIntentLevel.CONSERVATIVE,
        beta_range=(0.3, 0.5),
        min_beta_acceptable=0.1,  # Conservativo può avere beta molto basso
        beta_fail_threshold=0.0,  # Nessun fail per beta basso
        max_dd_expected=-0.15,
        benchmark="40/60",  # 40% equity / 60% bonds
        description="Portafoglio difensivo, priorità preservazione capitale",
    ),
    RiskIntentLevel.MODERATE: RiskIntentSpec(
        level=RiskIntentLevel.MODERATE,
        beta_range=(0.5, 0.8),
        min_beta_acceptable=0.3,
        beta_fail_threshold=0.2,
        max_dd_expected=-0.25,
        benchmark="60/40",
        description="Portafoglio bilanciato, compromesso rischio/rendimento",
    ),
    RiskIntentLevel.GROWTH: RiskIntentSpec(
        level=RiskIntentLevel.GROWTH,
        beta_range=(0.8, 1.0),
        min_beta_acceptable=0.6,
        beta_fail_threshold=0.4,
        max_dd_expected=-0.35,
        benchmark="VT",  # Global equity
        description="Portafoglio orientato alla crescita, accetta volatilità di mercato",
        vol_expected=(0.14, 0.18),
    ),
    RiskIntentLevel.GROWTH_DIVERSIFIED: RiskIntentSpec(
        level=RiskIntentLevel.GROWTH_DIVERSIFIED,
        beta_range=(0.45, 0.75),
        min_beta_acceptable=0.35,
        beta_fail_threshold=0.25,
        max_dd_expected=-0.32,
        benchmark="70/30",  # 70% equity / 30% bonds equivalent
        description="Portafoglio growth diversificato globalmente, beta controllato",
        vol_expected=(0.12, 0.16),
    ),
    RiskIntentLevel.AGGRESSIVE: RiskIntentSpec(
        level=RiskIntentLevel.AGGRESSIVE,
        beta_range=(1.0, 1.3),
        # === HARD CONSTRAINT AGGRESSIVE ===
        min_beta_acceptable=0.9,   # Beta minimo accettabile per AGGRESSIVE
        beta_fail_threshold=0.6,   # Sotto 0.6 → FAIL IMMEDIATO (intent mismatch)
        max_dd_expected=-0.45,
        benchmark="VT",
        description="Portafoglio aggressivo, cerca excess return con higher beta",
        vol_expected=(0.18, 0.22),
    ),
    RiskIntentLevel.HIGH_BETA: RiskIntentSpec(
        level=RiskIntentLevel.HIGH_BETA,
        beta_range=(1.3, 2.0),
        min_beta_acceptable=1.1,
        beta_fail_threshold=0.8,
        max_dd_expected=-0.55,
        benchmark="AVUV",  # Small Value come proxy high-beta
        description="Portafoglio high-beta, factor tilt aggressivi",
        vol_expected=(0.22, 0.30),
    ),
}


def get_risk_intent_spec(risk_intent: str) -> RiskIntentSpec:
    """
    Ottiene le specifiche per un dato risk intent.
    
    Args:
        risk_intent: Risk intent level as string (e.g., "GROWTH", "AGGRESSIVE")
    
    Returns:
        RiskIntentSpec dataclass with all specifications
    
    Note:
        Defaults to GROWTH if invalid intent provided.
    """
    try:
        level = RiskIntentLevel(risk_intent.upper())
        return RISK_INTENT_SPECS[level]
    except (ValueError, KeyError):
        # Default a GROWTH se non specificato o invalido
        return RISK_INTENT_SPECS[RiskIntentLevel.GROWTH]


def validate_risk_intent(risk_intent: str) -> Tuple[bool, str]:
    """
    Valida il risk intent dichiarato.
    
    Returns:
        (is_valid, message)
    """
    valid_intents = [e.value for e in RiskIntentLevel]
    if risk_intent.upper() in valid_intents:
        return True, f"Risk Intent '{risk_intent}' valido"
    else:
        return False, f"Risk Intent '{risk_intent}' non valido. Valori ammessi: {valid_intents}. Default: GROWTH"


# ================================================================================
# SEZIONE: BETA-ADJUSTED METRICS
# ================================================================================

def calculate_portfolio_beta(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series
) -> float:
    """
    Calcola il beta del portafoglio vs benchmark.
    
    Beta = Cov(R_portfolio, R_benchmark) / Var(R_benchmark)
    """
    # Allinea le serie
    aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
    if len(aligned) < 60:  # Minimo 3 mesi
        return 1.0  # Default a market beta
    
    port_ret = aligned.iloc[:, 0]
    bench_ret = aligned.iloc[:, 1]
    
    covariance = port_ret.cov(bench_ret)
    variance = bench_ret.var()
    
    if variance == 0:
        return 1.0
    
    return covariance / variance


def calculate_beta_adjusted_metrics(
    portfolio_metrics: Dict[str, Any],
    benchmark_metrics: Dict[str, Any],
    portfolio_beta: float
) -> Dict[str, Any]:
    """
    Calcola metriche beta-adjusted per evitare bias anti-equity.
    
    Metriche:
    - Relative Max Drawdown = DD_portfolio / DD_benchmark
    - Excess DD = DD_portfolio - (DD_benchmark × Beta)
    - Beta-Adjusted Volatility = Vol_portfolio / Beta
    - Expected DD = DD_benchmark × Beta
    - Expected Vol = Vol_benchmark × Beta
    
    Returns:
        Dict con metriche assolute, beta-adjusted, e verdetti
    """
    # Estrai valori
    dd_portfolio = portfolio_metrics.get('max_drawdown', 0)
    dd_benchmark = benchmark_metrics.get('max_drawdown', -0.34)  # Default VT GFC
    vol_portfolio = portfolio_metrics.get('volatility', 0)
    vol_benchmark = benchmark_metrics.get('volatility', 0.15)  # Default VT
    sharpe_portfolio = portfolio_metrics.get('sharpe', 0)
    sharpe_benchmark = benchmark_metrics.get('sharpe', 0.45)  # Default VT long-term
    sortino_portfolio = portfolio_metrics.get('sortino', 0)
    sortino_benchmark = benchmark_metrics.get('sortino', 0.60)
    
    # Calcola expected values (beta-adjusted)
    expected_dd = dd_benchmark * portfolio_beta
    expected_vol = vol_benchmark * portfolio_beta
    
    # Calcola excess/relative metrics
    excess_dd = dd_portfolio - expected_dd
    relative_dd = dd_portfolio / dd_benchmark if dd_benchmark != 0 else 1.0
    beta_adjusted_vol = vol_portfolio / portfolio_beta if portfolio_beta > 0 else vol_portfolio
    
    # Calcola excess volatility
    excess_vol = vol_portfolio - expected_vol
    
    # Verdetti
    verdicts = {}
    
    # DD Verdict
    if excess_dd <= 0.05:  # Entro 5% dell'atteso
        verdicts['dd'] = ('OK', f"DD coerente con beta {portfolio_beta:.2f}")
    elif excess_dd <= 0.15:
        verdicts['dd'] = ('WARNING', f"DD moderatamente elevato (excess {excess_dd:.1%})")
    else:
        verdicts['dd'] = ('STRUCTURAL', f"DD significativamente peggiore (excess {excess_dd:.1%})")
    
    # Vol Verdict
    if excess_vol <= 0.05:
        verdicts['vol'] = ('OK', f"Volatilità coerente con beta")
    elif excess_vol <= 0.10:
        verdicts['vol'] = ('WARNING', f"Volatilità moderatamente elevata (excess {excess_vol:.1%})")
    else:
        verdicts['vol'] = ('STRUCTURAL', f"Volatilità eccessiva (excess {excess_vol:.1%})")
    
    return {
        # Metriche Assolute
        'absolute': {
            'max_drawdown': dd_portfolio,
            'volatility': vol_portfolio,
            'sharpe': sharpe_portfolio,
            'sortino': sortino_portfolio,
        },
        # Metriche Beta-Adjusted
        'beta_adjusted': {
            'expected_dd': expected_dd,
            'excess_dd': excess_dd,
            'relative_dd': relative_dd,
            'expected_vol': expected_vol,
            'excess_vol': excess_vol,
            'beta_adjusted_vol': beta_adjusted_vol,
        },
        # Benchmark reference
        'benchmark': {
            'max_drawdown': dd_benchmark,
            'volatility': vol_benchmark,
            'sharpe': sharpe_benchmark,
            'sortino': sortino_benchmark,
        },
        # Portfolio beta
        'portfolio_beta': portfolio_beta,
        # Verdetti
        'verdicts': verdicts,
    }


# ================================================================================
# SEZIONE: DRAWDOWN ATTRIBUTION (Structural vs Regime)
# ================================================================================

class DrawdownType(Enum):
    """Tipi di drawdown."""
    REGIME_DRIVEN = "REGIME_DRIVEN"
    PARTIALLY_STRUCTURAL = "PARTIALLY_STRUCTURAL"
    STRUCTURAL_FRAGILITY = "STRUCTURAL_FRAGILITY"


# ================================================================================
# SEZIONE: NUOVI VERDETTI (FRAMEWORK ISTITUZIONALE)
# ================================================================================
# NOTE: FinalVerdictType is now imported from models.py for type safety.
# Local aliases for backward compatibility with existing code:
#   - STRUCTURALLY_COHERENT → STRUCTURALLY_COHERENT_INTENT_MATCH
#   - INTENT_MISALIGNED → INTENT_MISALIGNED_STRUCTURE_OK
#   - STRUCTURALLY_FRAGILE → STRUCTURALLY_FRAGILE (unchanged)


def check_beta_gating(
    portfolio_beta: float,
    risk_intent: str
) -> Dict[str, Any]:
    """
    BETA GATING - Regola non negoziabile.
    
    Se Risk Intent = AGGRESSIVE e Beta < 0.6:
    → FAIL IMMEDIATO per incoerenza di mandato
    Motivo: Risk Intent mismatch, NON fragilità strutturale
    
    Returns:
        Dict con:
        - passed: bool
        - verdict_type: FinalVerdictType
        - message: str
        - is_intent_mismatch: bool
        - thresholds_context: dict with fail_gate, min_acceptable, target_range
    """
    spec = get_risk_intent_spec(risk_intent)
    
    # Build thresholds context for clarity
    thresholds_context = {
        'fail_gate': spec.beta_fail_threshold,
        'min_acceptable': spec.min_beta_acceptable,
        'target_range': spec.beta_range,
        'risk_intent': risk_intent
    }
    
    # Check FAIL threshold (hard constraint)
    if portfolio_beta < spec.beta_fail_threshold:
        return {
            'passed': False,
            'verdict_type': FinalVerdictType.INTENT_MISALIGNED_STRUCTURE_OK,
            'message': f"❌ INTENT MISMATCH: Beta {portfolio_beta:.2f} < {spec.beta_fail_threshold:.1f} "
                      f"(HARD FAIL gate, target ≥{spec.min_beta_acceptable:.1f}) "
                      f"per risk intent {risk_intent}. Obiettivo errato, NON fragilità strutturale.",
            'is_intent_mismatch': True,
            'is_structural_issue': False,
            'beta': portfolio_beta,
            'threshold': spec.beta_fail_threshold,
            'min_acceptable': spec.min_beta_acceptable,
            'thresholds_context': thresholds_context,
        }
    
    # Check min acceptable (warning, non fail)
    if portfolio_beta < spec.min_beta_acceptable:
        return {
            'passed': True,  # Passa ma con warning
            'verdict_type': FinalVerdictType.INTENT_MISALIGNED_STRUCTURE_OK,
            'message': f"⚠️ INTENT WARNING: Beta {portfolio_beta:.2f} sopra fail gate ({spec.beta_fail_threshold:.1f}) "
                      f"ma sotto minimum acceptable ({spec.min_beta_acceptable:.1f}) per {risk_intent}. "
                      f"Struttura coerente ma obiettivo disallineato.",
            'is_intent_mismatch': True,
            'is_structural_issue': False,
            'beta': portfolio_beta,
            'threshold': spec.beta_fail_threshold,
            'min_acceptable': spec.min_beta_acceptable,
            'thresholds_context': thresholds_context,
        }
    
    # Check if in target range
    beta_low, beta_high = spec.beta_range
    if beta_low <= portfolio_beta <= beta_high:
        return {
            'passed': True,
            'verdict_type': FinalVerdictType.STRUCTURALLY_COHERENT_INTENT_MATCH,
            'message': f"✅ Beta {portfolio_beta:.2f} nel range target {beta_low:.1f}-{beta_high:.1f} "
                      f"per risk intent {risk_intent}.",
            'is_intent_mismatch': False,
            'is_structural_issue': False,
            'beta': portfolio_beta,
            'threshold': spec.beta_fail_threshold,
            'min_acceptable': spec.min_beta_acceptable,
            'thresholds_context': thresholds_context,
        }
    
    # Beta above target range (può essere ok per AGGRESSIVE)
    if portfolio_beta > beta_high:
        return {
            'passed': True,
            'verdict_type': FinalVerdictType.STRUCTURALLY_COHERENT_INTENT_MATCH,
            'message': f"ℹ️ Beta {portfolio_beta:.2f} sopra target {beta_high:.1f} - "
                      f"profilo più aggressivo del dichiarato.",
            'is_intent_mismatch': False,
            'is_structural_issue': False,
            'beta': portfolio_beta,
            'threshold': spec.beta_fail_threshold,
            'min_acceptable': spec.min_beta_acceptable,
            'thresholds_context': thresholds_context,
        }
    
    # Default: coerente
    return {
        'passed': True,
        'verdict_type': FinalVerdictType.STRUCTURALLY_COHERENT_INTENT_MATCH,
        'message': f"✅ Beta {portfolio_beta:.2f} accettabile per risk intent {risk_intent}.",
        'is_intent_mismatch': False,
        'is_structural_issue': False,
        'beta': portfolio_beta,
        'threshold': spec.beta_fail_threshold,
        'min_acceptable': spec.min_beta_acceptable,
        'thresholds_context': thresholds_context,
    }


def attribute_drawdown(
    dd_portfolio: float,
    dd_benchmark: float,
    portfolio_beta: float,
    risk_intent: str
) -> Dict[str, Any]:
    """
    Attribuisce il drawdown a regime (accettabile) o struttura (errore di design).
    
    REGOLE FRAMEWORK ISTITUZIONALE:
    - DD inferiore all'atteso → NON penalizzare (profilo più conservativo)
    - Excess_DD ≤ 5% → REGIME_DRIVEN (accettabile)
    - Excess_DD 5-15% → PARTIALLY_STRUCTURAL (warning)
    - Excess_DD > 15% → verificare se è fragilità O intent mismatch
    
    VIETATO usare 'FRAGILE' per:
    - Bassa beta
    - Volatilità contenuta
    - Protezione del downside
    
    Returns:
        Dict con attribution, excess_dd, e verdetto
    """
    # Calcola expected DD (beta-adjusted)
    expected_dd = dd_benchmark * portfolio_beta
    
    # DD osservato vs atteso (valori negativi)
    # Se |DD_osservato| > |DD_atteso| → excess positivo (peggiore del previsto)
    # Se |DD_osservato| < |DD_atteso| → excess negativo (meglio del previsto)
    excess_dd = abs(dd_portfolio) - abs(expected_dd)
    
    # Risk intent spec
    intent_spec = get_risk_intent_spec(risk_intent)
    
    # === NUOVA LOGICA: DD contenuto NON è mai penalizzante ===
    # Un DD più basso dell'atteso indica profilo più conservativo, non errore
    if excess_dd < 0:
        # DD migliore dell'atteso → sempre OK
        dd_type = DrawdownType.REGIME_DRIVEN
        verdict = f"DD {dd_portfolio:.1%} migliore dell'atteso ({expected_dd:.1%}) - profilo più conservativo"
        severity = "OK"
        is_structural = False
        is_intent_issue = False
    elif excess_dd <= 0.05:
        dd_type = DrawdownType.REGIME_DRIVEN
        verdict = "Drawdown coerente con esposizione di mercato"
        severity = "OK"
        is_structural = False
        is_intent_issue = False
    elif excess_dd <= 0.15:
        dd_type = DrawdownType.PARTIALLY_STRUCTURAL
        verdict = "Drawdown moderatamente elevato - verificare concentrazione/correlazioni"
        severity = "WARNING"
        is_structural = False
        is_intent_issue = False
    else:
        # Excess > 15%: distinguere STRUTTURA vs INTENT
        # Se beta è basso E intent è aggressivo → INTENT MISMATCH, non fragilità
        if portfolio_beta < intent_spec.min_beta_acceptable:
            dd_type = DrawdownType.PARTIALLY_STRUCTURAL
            verdict = f"DD elevato ma con beta {portfolio_beta:.2f} sotto target - verificare INTENT"
            severity = "WARNING"
            is_structural = False
            is_intent_issue = True  # Il problema è l'intent, non la struttura
        else:
            dd_type = DrawdownType.STRUCTURAL_FRAGILITY
            verdict = f"DD {excess_dd:.1%} oltre atteso - concentrazione o correlazioni problematiche"
            severity = "CRITICAL"
            is_structural = True
            is_intent_issue = False
    
    # DD vs intent declared (informativo)
    dd_vs_intent = abs(dd_portfolio) - abs(intent_spec.max_dd_expected)
    dd_within_intent = dd_vs_intent <= 0
    
    return {
        'dd_type': dd_type.value,
        'excess_dd': excess_dd,
        'expected_dd': expected_dd,
        'observed_dd': dd_portfolio,
        'benchmark_dd': dd_benchmark,
        'portfolio_beta': portfolio_beta,
        'verdict': verdict,
        'severity': severity,
        'is_structural': is_structural,
        'is_intent_issue': is_intent_issue,  # NUOVO: flag per problemi di intent
        'risk_intent': risk_intent,
        'intent_max_dd_expected': intent_spec.max_dd_expected,
        'dd_vs_intent': dd_vs_intent,
        'dd_within_intent': dd_within_intent,
    }


def format_drawdown_attribution(attribution: Dict[str, Any]) -> str:
    """Formatta l'attribution per output."""
    lines = [
        "┌─────────────────────────────────────────────────────────────────┐",
        "│ DRAWDOWN ATTRIBUTION                                            │",
        "├─────────────────────────────────────────────────────────────────┤",
        f"│ Risk Intent Declared:    {attribution['risk_intent']:<39}│",
        f"│ Portfolio Beta:          {attribution['portfolio_beta']:.2f}{' ' * 37}│",
        "├─────────────────────────────────────────────────────────────────┤",
        f"│ Portfolio Max DD:        {attribution['observed_dd']:.1%}{' ' * 35}│",
        f"│ Benchmark Max DD:        {attribution['benchmark_dd']:.1%}{' ' * 35}│",
        f"│ Expected DD (β-adj):     {attribution['expected_dd']:.1%}{' ' * 35}│",
    ]
    
    # Excess DD con simbolo
    excess = attribution['excess_dd']
    if attribution['severity'] == 'OK':
        symbol = "✅ REGIME-DRIVEN"
    elif attribution['severity'] == 'WARNING':
        symbol = "⚠️ PARTIAL STRUCTURAL"
    else:
        symbol = "🔴 STRUCTURAL FRAGILITY"
    
    lines.append(f"│ Excess DD:               {excess:+.1%}  {symbol:<22}│")
    lines.append("├─────────────────────────────────────────────────────────────────┤")
    
    # Wrap verdict
    verdict = attribution['verdict']
    lines.append(f"│ VERDICT: {verdict:<55}│")
    lines.append("└─────────────────────────────────────────────────────────────────┘")
    
    return "\n".join(lines)


# ================================================================================
# SEZIONE: CONFIDENCE MODEL CON GATING RULES
# ================================================================================

class ConfidenceLevel(Enum):
    """Livelli di confidence."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass
class ConfidenceResult:
    """Risultato del confidence model."""
    score: float
    level: ConfidenceLevel
    components: Dict[str, float]
    gating: Dict[str, bool]
    blocked_metrics: List[str]
    warnings: List[str]


def calculate_confidence_score(
    returns: pd.DataFrame,
    tickers: List[str],
    weights: np.ndarray,
    corr_matrix: pd.DataFrame
) -> ConfidenceResult:
    """
    Calcola il Confidence Score secondo la formula in response.md.
    
    CONFIDENCE = 0.30 × DataCoverage + 0.30 × PairwiseCoverage + 
                 0.20 × StabilityScore + 0.20 × HistoryLength
    
    Returns:
        ConfidenceResult con score, level, e gating rules
    """
    warnings = []
    
    # 1. Data Coverage (0-100)
    nan_count = returns.isna().any(axis=1).sum()
    total_days = len(returns)
    nan_ratio = nan_count / total_days if total_days > 0 else 1.0
    data_coverage = 100 * (1 - nan_ratio)
    
    # 2. Pairwise Coverage (0-100)
    n_tickers = len(tickers)
    n_pairs = n_tickers * (n_tickers - 1) // 2
    
    valid_pairs = 0
    min_overlap = 252  # 1 anno minimo
    
    for i in range(n_tickers):
        for j in range(i + 1, n_tickers):
            # Conta overlap
            overlap = returns[[tickers[i], tickers[j]]].dropna()
            if len(overlap) >= min_overlap:
                valid_pairs += 1
    
    pairwise_coverage = 100 * (valid_pairs / n_pairs) if n_pairs > 0 else 0
    
    # 3. Stability Score (0-100)
    # Basato su volatilità delle rolling correlations
    stability_score = 80  # Default se non calcolabile
    
    if len(returns) >= 126:  # Almeno 6 mesi
        try:
            # Rolling correlations (60 giorni)
            rolling_corrs = []
            window = 60
            for start in range(0, len(returns) - window, 20):
                window_returns = returns.iloc[start:start + window]
                corr = window_returns.corr()
                # Media delle correlazioni non-diagonali
                mask = ~np.eye(len(tickers), dtype=bool)
                avg_corr = corr.values[mask].mean()
                rolling_corrs.append(avg_corr)
            
            if rolling_corrs:
                corr_volatility = np.std(rolling_corrs)
                stability_score = max(0, 100 - corr_volatility * 200)
        except Exception:
            pass  # Usa default
    
    # 4. History Length (0-100)
    min_history = min(returns[t].dropna().count() for t in tickers)
    target_days = 1260  # 5 anni
    history_length = min(100, (min_history / target_days) * 100)
    
    # Calcola score complessivo
    score = (
        0.30 * data_coverage +
        0.30 * pairwise_coverage +
        0.20 * stability_score +
        0.20 * history_length
    )
    
    # Determina level
    if score >= 80:
        level = ConfidenceLevel.HIGH
    elif score >= 60:
        level = ConfidenceLevel.MEDIUM
    elif score >= 40:
        level = ConfidenceLevel.LOW
    else:
        level = ConfidenceLevel.INSUFFICIENT
    
    # Gating Rules (da response.md)
    nan_ratio_corr = (corr_matrix.isna().sum().sum() / (n_tickers * n_tickers)) if corr_matrix is not None else 1.0
    
    gating = {
        'ccr_allowed': level in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM] and pairwise_coverage >= 70,
        'correlation_verdict_allowed': nan_ratio_corr < 0.20,
        'structural_verdict_allowed': level in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM],
        'full_analysis_allowed': level != ConfidenceLevel.INSUFFICIENT,
    }
    
    # Determina metriche bloccate
    blocked_metrics = []
    
    if level in [ConfidenceLevel.LOW, ConfidenceLevel.INSUFFICIENT]:
        blocked_metrics.extend(['CCR', 'MCR', 'correlation_analysis'])
        warnings.append(f"⛔ CCR/Correlazioni BLOCCATE: Confidence {score:.0f}% insufficiente")
    
    if level == ConfidenceLevel.MEDIUM and pairwise_coverage < 70:
        blocked_metrics.append('CCR')
        warnings.append(f"⛔ CCR BLOCCATO: Pairwise coverage {pairwise_coverage:.0f}% < 70%")
    
    if nan_ratio_corr >= 0.20:
        blocked_metrics.append('diversification_verdict')
        warnings.append(f"⛔ Verdetto diversificazione BLOCCATO: {nan_ratio_corr:.0%} correlazioni NaN")
    
    if level == ConfidenceLevel.INSUFFICIENT:
        blocked_metrics.append('structural_verdict')
        warnings.append("⛔ Verdetto strutturale SOSPESO: Dati insufficienti")
    
    return ConfidenceResult(
        score=score,
        level=level,
        components={
            'data_coverage': data_coverage,
            'pairwise_coverage': pairwise_coverage,
            'stability_score': stability_score,
            'history_length': history_length,
        },
        gating=gating,
        blocked_metrics=list(set(blocked_metrics)),
        warnings=warnings,
    )


def format_confidence_result(result: ConfidenceResult) -> str:
    """Formatta il risultato confidence per output."""
    lines = [
        "┌─────────────────────────────────────────────────────────────────┐",
        "│ CONFIDENCE MODEL                                                │",
        "├─────────────────────────────────────────────────────────────────┤",
        f"│ Overall Score:           {result.score:.0f}/100 ({result.level.value}){' ' * 26}│",
        "├─────────────────────────────────────────────────────────────────┤",
        f"│ Data Coverage:           {result.components['data_coverage']:.0f}/100{' ' * 34}│",
        f"│ Pairwise Coverage:       {result.components['pairwise_coverage']:.0f}/100{' ' * 34}│",
        f"│ Stability Score:         {result.components['stability_score']:.0f}/100{' ' * 34}│",
        f"│ History Length:          {result.components['history_length']:.0f}/100{' ' * 34}│",
        "├─────────────────────────────────────────────────────────────────┤",
        "│ GATING RULES:                                                   │",
    ]
    
    for gate, allowed in result.gating.items():
        symbol = "✅" if allowed else "⛔"
        gate_name = gate.replace('_', ' ').title()
        lines.append(f"│   {symbol} {gate_name:<55}│")
    
    if result.blocked_metrics:
        lines.append("├─────────────────────────────────────────────────────────────────┤")
        lines.append("│ BLOCKED METRICS:                                                │")
        for metric in result.blocked_metrics[:5]:  # Max 5
            lines.append(f"│   ⛔ {metric:<58}│")
    
    lines.append("└─────────────────────────────────────────────────────────────────┘")
    
    return "\n".join(lines)


# ================================================================================
# SEZIONE: SOTTOTIPI TACTICAL
# ================================================================================

class TacticalSubtype(Enum):
    """Sottotipi per portafogli TACTICAL."""
    FACTOR = "TACTICAL-FACTOR"
    SECTOR = "TACTICAL-SECTOR"
    TIMING = "TACTICAL-TIMING"
    MIXED = "TACTICAL-MIXED"


# Beta tipici per settori (da response.md)
SECTOR_BETAS = {
    'technology': (1.15, 1.30),
    'semiconductors': (1.30, 1.50),
    'healthcare': (0.80, 1.00),
    'utilities': (0.50, 0.70),
    'financials': (1.10, 1.30),
    'energy': (1.00, 1.40),
    'consumer_discretionary': (1.00, 1.20),
    'industrials': (1.00, 1.20),
    'materials': (1.00, 1.30),
    'communication': (0.90, 1.10),
    'consumer_staples': (0.60, 0.80),
    'real_estate': (0.80, 1.10),
}


def detect_tactical_subtype(
    tickers: List[str],
    weights: np.ndarray,
    sector_allocation: Dict[str, float],
    factor_allocation: Dict[str, float],
    turnover: float = 0.10
) -> Tuple[TacticalSubtype, Dict[str, Any]]:
    """
    Determina il sottotipo TACTICAL del portafoglio.
    
    Returns:
        (subtype, details)
    """
    details: Dict[str, Any] = {
        'factor_pct': sum(factor_allocation.values()),
        'sector_pct': sum(sector_allocation.values()),
        'turnover': turnover,
        'triggers': [],
    }
    
    # Check TACTICAL-FACTOR
    factor_pct = details['factor_pct']
    if factor_pct > 0.15:
        details['triggers'].append(f"Factor allocation {factor_pct:.0%} > 15%")
    
    # Check TACTICAL-SECTOR
    sector_pct = details['sector_pct']
    if sector_pct > 0.10:
        details['triggers'].append(f"Sector allocation {sector_pct:.0%} > 10%")
    
    # Check TACTICAL-TIMING
    if turnover > 0.20:
        details['triggers'].append(f"Turnover {turnover:.0%} > 20%")
    
    # Determina subtype
    is_factor = factor_pct > 0.15
    is_sector = sector_pct > 0.10
    is_timing = turnover > 0.20
    
    if is_factor and not is_sector:
        subtype = TacticalSubtype.FACTOR
        details['benchmark'] = "Factor Index (es. MSCI World Value)"
        details['beta_expected'] = (1.0, 1.3)
    elif is_sector and not is_factor:
        subtype = TacticalSubtype.SECTOR
        details['benchmark'] = "Sector-weighted blend"
        # Calcola beta atteso in base ai settori
        avg_beta_low = np.mean([SECTOR_BETAS.get(s, (1.0, 1.0))[0] for s in sector_allocation.keys()])
        avg_beta_high = np.mean([SECTOR_BETAS.get(s, (1.0, 1.0))[1] for s in sector_allocation.keys()])
        details['beta_expected'] = (avg_beta_low, avg_beta_high)
    elif is_timing:
        subtype = TacticalSubtype.TIMING
        details['benchmark'] = "Static equivalent"
        details['beta_expected'] = (0.8, 1.2)
    else:
        subtype = TacticalSubtype.MIXED
        details['benchmark'] = "VT"
        details['beta_expected'] = (0.9, 1.3)
    
    return subtype, details


# ================================================================================
# SEZIONE: VERDETTI RULE-BASED
# ================================================================================

@dataclass
class RuleVerdict:
    """Un verdetto basato su regola."""
    rule_id: str
    condition: str
    satisfied: bool
    verdict_type: str  # 'OK', 'WARNING', 'STRUCTURAL', 'REGIME'
    message: str


def evaluate_verdicts(
    portfolio_metrics: Dict[str, Any],
    benchmark_metrics: Dict[str, Any],
    beta_adjusted: Dict[str, Any],
    risk_intent: str,
    confidence: ConfidenceResult,
    corr_matrix: pd.DataFrame,
    ccr_data: pd.DataFrame
) -> List[RuleVerdict]:
    """
    Valuta tutti i verdetti rule-based.
    
    Ogni verdetto ha formato: SE [condizione] → [verdetto]
    
    Returns:
        Lista di RuleVerdict
    """
    verdicts = []
    intent_spec = get_risk_intent_spec(risk_intent)
    
    # Solo se confidence permette verdetti
    if confidence.level == ConfidenceLevel.INSUFFICIENT:
        verdicts.append(RuleVerdict(
            rule_id="G0",
            condition="Confidence < 40",
            satisfied=True,
            verdict_type="BLOCKED",
            message="⛔ VERDETTI BLOCCATI: Confidence insufficiente per analisi strutturale"
        ))
        return verdicts
    
    # === VERDETTI POSITIVI ===
    
    # V1: Efficienza
    sharpe_port = portfolio_metrics.get('sharpe', 0)
    sharpe_bench = benchmark_metrics.get('sharpe', 0.45)
    te = portfolio_metrics.get('tracking_error', 0)
    
    if sharpe_port >= sharpe_bench and te <= 0.03:
        verdicts.append(RuleVerdict(
            rule_id="V1",
            condition=f"Sharpe {sharpe_port:.2f} ≥ Benchmark {sharpe_bench:.2f} AND TE {te:.1%} ≤ 3%",
            satisfied=True,
            verdict_type="OK",
            message="✅ EFFICIENTE: Risk-adjusted return ≥ benchmark con tracking error contenuto"
        ))
    
    # V2: CCR - NUOVA INTERPRETAZIONE FRAMEWORK ISTITUZIONALE
    # Una concentrazione di rischio (CCR > peso) è:
    # - ACCETTABILE se coerente con Risk Intent
    # - PROBLEMATICA solo se: non dichiarata, non compensata, incoerente con obiettivo
    if ccr_data is not None and 'CCR' not in confidence.blocked_metrics:
        weights = ccr_data['Weight'].values if 'Weight' in ccr_data.columns else None
        ccr_pct = ccr_data['CCR%'].values if 'CCR%' in ccr_data.columns else None
        
        if weights is not None and ccr_pct is not None:
            ccr_w_ratios = ccr_pct / weights
            valid_ratios = ccr_w_ratios[~np.isnan(ccr_w_ratios)]
            max_ratio = valid_ratios.max() if len(valid_ratios) > 0 else 0
            
            # Trova asset con alto leverage
            high_leverage_idx = np.where(ccr_w_ratios > 1.5)[0]
            high_leverage_assets = []
            if len(high_leverage_idx) > 0 and hasattr(ccr_data, 'index'):
                high_leverage_assets = ccr_data.index[high_leverage_idx].tolist()
            
            # === NUOVA LOGICA: CCR coerente con Intent ===
            # Per AGGRESSIVE/HIGH_BETA: CCR concentrato è ATTESO e ACCETTABILE
            intent_level = intent_spec.level
            
            if max_ratio <= 1.5:
                verdicts.append(RuleVerdict(
                    rule_id="V2",
                    condition=f"max(CCR/Weight) = {max_ratio:.2f} ≤ 1.5",
                    satisfied=True,
                    verdict_type="OK",
                    message="✅ CCR BILANCIATO: Nessun asset con risk leverage > 1.5x"
                ))
            elif intent_level in [RiskIntentLevel.AGGRESSIVE, RiskIntentLevel.HIGH_BETA]:
                # Per intent aggressivo, CCR concentrato è COERENTE (non problema strutturale)
                verdicts.append(RuleVerdict(
                    rule_id="V2",
                    condition=f"max(CCR/Weight) = {max_ratio:.2f} > 1.5 AND Intent={risk_intent}",
                    satisfied=True,
                    verdict_type="OK",
                    message=f"✅ CCR INTENZIONALE: {high_leverage_assets} risk leverage {max_ratio:.1f}x coerente con intent {risk_intent}"
                ))
            elif intent_level == RiskIntentLevel.GROWTH:
                # Per GROWTH: warning ma non structural
                verdicts.append(RuleVerdict(
                    rule_id="V2",
                    condition=f"max(CCR/Weight) = {max_ratio:.2f} > 1.5",
                    satisfied=True,  # Passa con warning
                    verdict_type="INFO",
                    message=f"ℹ️ CCR CONCENTRATO: {high_leverage_assets} risk leverage {max_ratio:.1f}x - verificare se intenzionale"
                ))
            else:
                # Per CONSERVATIVE/MODERATE: concentrazione è problematica
                verdicts.append(RuleVerdict(
                    rule_id="V2",
                    condition=f"max(CCR/Weight) = {max_ratio:.2f} > 1.5 AND Intent={risk_intent}",
                    satisfied=False,
                    verdict_type="WARNING",
                    message=f"⚠️ CCR INCOERENTE: {high_leverage_assets} risk leverage {max_ratio:.1f}x non coerente con intent {risk_intent}"
                ))
    
    # V3: Diversificazione (solo se correlazioni disponibili)
    if corr_matrix is not None and 'diversification_verdict' not in confidence.blocked_metrics:
        # Media correlazioni non-diagonali
        mask = ~np.eye(len(corr_matrix), dtype=bool)
        corr_values = corr_matrix.values[mask]
        nan_ratio = np.isnan(corr_values).sum() / len(corr_values)
        
        if nan_ratio < 0.10:  # Meno di 10% NaN
            mean_corr = np.nanmean(corr_values)
            
            if mean_corr < 0.70:
                verdicts.append(RuleVerdict(
                    rule_id="V3",
                    condition=f"mean(Corr) = {mean_corr:.2f} < 0.70 AND NaN ratio {nan_ratio:.0%} < 10%",
                    satisfied=True,
                    verdict_type="OK",
                    message=f"✅ DIVERSIFICATO: Correlazione media {mean_corr:.2f} < 0.70 (matrice completa)"
                ))
            elif mean_corr >= 0.85:
                verdicts.append(RuleVerdict(
                    rule_id="V3",
                    condition=f"mean(Corr) = {mean_corr:.2f} ≥ 0.85",
                    satisfied=False,
                    verdict_type="STRUCTURAL",
                    message=f"⚠️ STRUCTURAL: Alta ridondanza, correlazione media {mean_corr:.2f}"
                ))
    
    # V4: Drawdown Attribution - AGGIORNATO per nuova logica
    excess_dd = beta_adjusted.get('beta_adjusted', {}).get('excess_dd', 0)
    
    # DD negativo (meglio dell'atteso) → sempre OK
    if excess_dd < 0:
        verdicts.append(RuleVerdict(
            rule_id="V4",
            condition=f"Excess DD = {excess_dd:.1%} < 0 (meglio dell'atteso)",
            satisfied=True,
            verdict_type="OK",
            message=f"✅ DD ECCELLENTE: Drawdown migliore dell'atteso per beta - profilo conservativo"
        ))
    elif excess_dd <= 0.05:
        verdicts.append(RuleVerdict(
            rule_id="V4",
            condition=f"Excess DD = {excess_dd:.1%} ≤ 5%",
            satisfied=True,
            verdict_type="OK",
            message=f"✅ DD COERENTE: Drawdown in linea con risk intent ({risk_intent})"
        ))
    elif excess_dd <= 0.15:
        verdicts.append(RuleVerdict(
            rule_id="V4",
            condition=f"Excess DD = {excess_dd:.1%} > 5% AND ≤ 15%",
            satisfied=True,  # Warning ma passa
            verdict_type="WARNING",
            message=f"⚠️ DD elevato (excess {excess_dd:.1%}) - verificare concentrazione"
        ))
    else:
        # Excess > 15%: problema, ma distingui intent vs structural
        portfolio_beta = beta_adjusted.get('portfolio_beta', 1.0)
        if portfolio_beta < intent_spec.min_beta_acceptable:
            # Beta basso con intent aggressivo → INTENT MISMATCH, non structural
            verdicts.append(RuleVerdict(
                rule_id="V4",
                condition=f"Excess DD = {excess_dd:.1%} > 15% AND Beta {portfolio_beta:.2f} < min acceptable",
                satisfied=False,
                verdict_type="INTENT_MISMATCH",
                message=f"⚠️ INTENT MISMATCH: DD elevato con beta {portfolio_beta:.2f} sotto target - verificare RISK INTENT"
            ))
        else:
            verdicts.append(RuleVerdict(
                rule_id="V4",
                condition=f"Excess DD = {excess_dd:.1%} > 15%",
                satisfied=False,
                verdict_type="STRUCTURAL",
                message=f"🔴 DD STRUTTURALE: Excess {excess_dd:.1%} indica concentrazione o correlazioni problematiche"
            ))
    
    # V5: Beta Coerenza - USA NUOVA LOGICA BETA GATING
    portfolio_beta = beta_adjusted.get('portfolio_beta', 1.0)
    beta_gating = check_beta_gating(portfolio_beta, risk_intent)
    
    if beta_gating['passed'] and not beta_gating['is_intent_mismatch']:
        verdicts.append(RuleVerdict(
            rule_id="V5",
            condition=beta_gating['message'],
            satisfied=True,
            verdict_type="OK",
            message=beta_gating['message']
        ))
    elif beta_gating['is_intent_mismatch']:
        # INTENT MISMATCH - non structural fragility
        verdicts.append(RuleVerdict(
            rule_id="V5",
            condition=f"Beta {portfolio_beta:.2f} vs Intent {risk_intent}",
            satisfied=False,
            verdict_type="INTENT_MISMATCH",
            message=beta_gating['message']
        ))
    else:
        verdicts.append(RuleVerdict(
            rule_id="V5",
            condition=f"Beta {portfolio_beta:.2f} fuori range",
            satisfied=False,
            verdict_type="WARNING",
            message=beta_gating['message']
        ))
    
    # === VERDETTI NEGATIVI ===
    
    # V6: Sharpe negativo
    if sharpe_port < 0:
        severity = "CRITICAL" if sharpe_port < -0.20 else "WARNING"
        verdicts.append(RuleVerdict(
            rule_id="V6",
            condition=f"Sharpe = {sharpe_port:.2f} < 0",
            satisfied=False,
            verdict_type=severity,
            message=f"🔴 SHARPE NEGATIVO ({sharpe_port:.2f}): Rendimento inferiore al risk-free"
        ))
    
    # V7: Information Ratio non significativo
    ir = portfolio_metrics.get('information_ratio', 0)
    if 0 < ir < 0.30 and te > 0.02:
        verdicts.append(RuleVerdict(
            rule_id="V7",
            condition=f"IR = {ir:.2f} < 0.30 AND TE = {te:.1%} > 2%",
            satisfied=False,
            verdict_type="WARNING",
            message=f"📈 IR {ir:.2f} NON STATISTICAMENTE SIGNIFICATIVO: Non interpretare come alpha"
        ))
    
    if ir < 0 and te > 0.03:
        verdicts.append(RuleVerdict(
            rule_id="V7b",
            condition=f"IR = {ir:.2f} < 0 AND TE = {te:.1%} > 3%",
            satisfied=False,
            verdict_type="STRUCTURAL",
            message=f"⚠️ STRUCTURAL: Active risk non remunerato (IR={ir:.2f}, TE={te:.1%})"
        ))
    
    return verdicts


def format_verdicts(verdicts: List[RuleVerdict]) -> str:
    """Formatta i verdetti per output."""
    lines = [
        "┌─────────────────────────────────────────────────────────────────┐",
        "│ VERDETTI RULE-BASED                                             │",
        "├─────────────────────────────────────────────────────────────────┤",
    ]
    
    # Raggruppa per tipo
    by_type: Dict[str, List[Any]] = {'OK': [], 'WARNING': [], 'STRUCTURAL': [], 'REGIME': [], 'BLOCKED': [], 'CRITICAL': []}
    for v in verdicts:
        by_type.get(v.verdict_type, []).append(v)
    
    # OK verdicts
    if by_type['OK']:
        for v in by_type['OK']:
            lines.append(f"│ {v.message:<63}│")
    
    # Warnings
    if by_type['WARNING']:
        lines.append("├─────────────────────────────────────────────────────────────────┤")
        for v in by_type['WARNING']:
            lines.append(f"│ {v.message:<63}│")
    
    # Structural issues
    if by_type['STRUCTURAL'] or by_type['CRITICAL']:
        lines.append("├─────────────────────────────────────────────────────────────────┤")
        lines.append("│ ⚠️  PROBLEMI STRUTTURALI:                                       │")
        for v in by_type['STRUCTURAL'] + by_type['CRITICAL']:
            lines.append(f"│ {v.message:<63}│")
    
    # Blocked
    if by_type['BLOCKED']:
        lines.append("├─────────────────────────────────────────────────────────────────┤")
        for v in by_type['BLOCKED']:
            lines.append(f"│ {v.message:<63}│")
    
    lines.append("└─────────────────────────────────────────────────────────────────┘")
    
    return "\n".join(lines)


# ================================================================================
# SEZIONE: AGGREGATE VERDICT
# ================================================================================

def calculate_aggregate_verdict(
    confidence: ConfidenceResult,
    verdicts: List[RuleVerdict],
    risk_intent: str,
    drawdown_attribution: Dict[str, Any],
    beta_gating_result: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Calcola il verdetto aggregato finale.
    
    FRAMEWORK ISTITUZIONALE - VERDETTO OBBLIGATORIO:
    1. Risk Intent dichiarato
    2. Coerenza Intent vs Dati (OK / MISMATCH)
    3. Coerenza Strutturale interna (OK / FAIL)
    4. Motivazione unica e non contraddittoria
    5. Confidence score giustificato
    
    Returns:
        Dict con scores modulari e verdetto finale
    """
    # Conta verdetti per tipo
    ok_count = sum(1 for v in verdicts if v.verdict_type == 'OK')
    warning_count = sum(1 for v in verdicts if v.verdict_type == 'WARNING')
    structural_count = sum(1 for v in verdicts if v.verdict_type in ['STRUCTURAL', 'CRITICAL'])
    intent_mismatch_count = sum(1 for v in verdicts if v.verdict_type == 'INTENT_MISMATCH')
    info_count = sum(1 for v in verdicts if v.verdict_type == 'INFO')
    
    # Calcola scores modulari (0-100)
    total_verdicts = max(1, len(verdicts))
    
    # A) Data Integrity Score
    data_integrity = confidence.score
    
    # B) Structural Coherence Score - SOLO structural issues, non intent mismatch
    if structural_count > 0:
        structural_coherence = max(0, 100 - structural_count * 25)
    elif warning_count > 0:
        structural_coherence = max(50, 100 - warning_count * 10)
    else:
        structural_coherence = 100
    
    # C) Efficiency vs Benchmark Score
    efficiency_verdicts = [v for v in verdicts if v.rule_id in ['V1', 'V7', 'V7b']]
    if efficiency_verdicts:
        efficiency_ok = sum(1 for v in efficiency_verdicts if v.verdict_type == 'OK')
        efficiency = (efficiency_ok / len(efficiency_verdicts)) * 100
    else:
        efficiency = 50  # Neutro se non valutabile
    
    # D) Tail Risk Score - aggiornato per nuova logica
    if drawdown_attribution.get('is_structural', False):
        tail_risk = 30
    elif drawdown_attribution.get('is_intent_issue', False):
        tail_risk = 70  # Intent issue non è structural, quindi non penalizzare troppo
    elif drawdown_attribution.get('severity') == 'WARNING':
        tail_risk = 60
    else:
        tail_risk = 85
    
    # Aggregate
    aggregate_score = (
        0.25 * data_integrity +
        0.30 * structural_coherence +
        0.25 * efficiency +
        0.20 * tail_risk
    )
    
    # === NUOVO FRAMEWORK: Determina FinalVerdictType ===
    # REGOLE:
    # 1. Intent Mismatch → INTENT_MISALIGNED (non fragile)
    # 2. Structural issues → STRUCTURALLY_FRAGILE (vero problema)
    # 3. Nessun problema → STRUCTURALLY_COHERENT
    
    if confidence.level == ConfidenceLevel.INSUFFICIENT:
        final_verdict_type = None  # Analisi incompleta
        final_verdict = "⚠️ ANALYSIS_INCOMPLETE - Dati insufficienti per valutazione"
        final_qualifier = "Raccogli più dati prima di giudicare"
        intent_coherence = "NON VALUTABILE"
        structural_coherence_status = "NON VALUTABILE"
    elif intent_mismatch_count > 0 and structural_count == 0:
        # INTENT MISMATCH ma struttura OK → obiettivo errato, non fragilità
        final_verdict_type = FinalVerdictType.INTENT_MISALIGNED_STRUCTURE_OK
        final_verdict = f"⚠️ INTENT MISALIGNED - Struttura coerente ma obiettivo errato"
        final_qualifier = "Verifica Risk Intent dichiarato vs struttura portafoglio"
        intent_coherence = "MISMATCH"
        structural_coherence_status = "OK"
    elif structural_count > 0:
        # Veri problemi strutturali
        final_verdict_type = FinalVerdictType.STRUCTURALLY_FRAGILE
        final_verdict = f"❌ STRUCTURALLY FRAGILE - {structural_count} problemi strutturali"
        final_qualifier = "Richiede intervento sulla struttura"
        intent_coherence = "OK" if intent_mismatch_count == 0 else "MISMATCH"
        structural_coherence_status = "FAIL"
    elif warning_count > 3:
        # Molti warning ma non structural
        final_verdict_type = FinalVerdictType.STRUCTURALLY_COHERENT_INTENT_MATCH
        final_verdict = f"⚠️ REVIEW_NEEDED - {warning_count} aree richiedono attenzione"
        final_qualifier = "Monitorare, non ristrutturare"
        intent_coherence = "OK"
        structural_coherence_status = "OK"
    elif aggregate_score >= 75:
        final_verdict_type = FinalVerdictType.STRUCTURALLY_COHERENT_INTENT_MATCH
        final_verdict = "✅ STRUCTURALLY COHERENT - Struttura robusta e allineata"
        final_qualifier = None
        intent_coherence = "OK"
        structural_coherence_status = "OK"
    elif aggregate_score >= 60:
        final_verdict_type = FinalVerdictType.STRUCTURALLY_COHERENT_INTENT_MATCH
        final_verdict = "✅ ACCEPTABLE - Trade-off ragionevoli documentati"
        final_qualifier = "Alcune aree ottimizzabili ma struttura solida"
        intent_coherence = "OK"
        structural_coherence_status = "OK"
    else:
        final_verdict_type = FinalVerdictType.STRUCTURALLY_COHERENT_INTENT_MATCH
        final_verdict = "⚠️ SUB-OPTIMAL - Performance non giustifica complessità"
        final_qualifier = "Valutare semplificazione"
        intent_coherence = "OK"
        structural_coherence_status = "OK"
    
    return {
        'scores': {
            'data_integrity': data_integrity,
            'structural_coherence': structural_coherence,
            'efficiency': efficiency,
            'tail_risk': tail_risk,
            'aggregate': aggregate_score,
        },
        'confidence_level': confidence.level.value,
        'verdict_counts': {
            'ok': ok_count,
            'warning': warning_count,
            'structural': structural_count,
            'intent_mismatch': intent_mismatch_count,
            'info': info_count,
        },
        # === NUOVO: Struttura verdetto obbligatoria ===
        'risk_intent_declared': risk_intent,
        'intent_coherence': intent_coherence,  # OK / MISMATCH
        'structural_coherence_status': structural_coherence_status,  # OK / FAIL
        'final_verdict_type': final_verdict_type.value if final_verdict_type else "INCOMPLETE",
        'final_verdict': final_verdict,
        'final_qualifier': final_qualifier,
        'risk_intent': risk_intent,
    }


def format_aggregate_verdict(agg: Dict[str, Any]) -> str:
    """Formatta il verdetto aggregato per output."""
    scores = agg['scores']
    
    lines = [
        "╔═════════════════════════════════════════════════════════════════╗",
        "║                    VERDETTO AGGREGATO                           ║",
        "╠═════════════════════════════════════════════════════════════════╣",
        f"║ A) Data Integrity Score:      {scores['data_integrity']:>5.0f}/100                       ║",
        f"║ B) Structural Coherence:      {scores['structural_coherence']:>5.0f}/100                       ║",
        f"║ C) Efficiency vs Benchmark:   {scores['efficiency']:>5.0f}/100                       ║",
        f"║ D) Tail Risk Assessment:      {scores['tail_risk']:>5.0f}/100                       ║",
        "║─────────────────────────────────────────────────────────────────║",
        f"║ AGGREGATE SCORE:              {scores['aggregate']:>5.0f}/100                       ║",
        f"║ Confidence:                   {agg['confidence_level']:<30}║",
        "╠═════════════════════════════════════════════════════════════════╣",
    ]
    
    # Final verdict (può essere lungo, wrapping)
    verdict = agg['final_verdict']
    lines.append(f"║ {verdict:<63}║")
    
    if agg['final_qualifier']:
        lines.append(f"║ → {agg['final_qualifier']:<61}║")
    
    lines.append("╚═════════════════════════════════════════════════════════════════╝")
    
    return "\n".join(lines)


# ================================================================================
# MAIN ANALYSIS FUNCTION (v3.1 - Framework Istituzionale)
# ================================================================================

def run_risk_intent_analysis(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
    returns_df: pd.DataFrame,
    tickers: List[str],
    weights: np.ndarray,
    corr_matrix: pd.DataFrame,
    ccr_data: pd.DataFrame,
    portfolio_metrics: Dict[str, Any],
    benchmark_metrics: Dict[str, Any],
    risk_intent: str = "GROWTH"
) -> Dict[str, Any]:
    """
    Esegue l'analisi completa Risk Intent v3.1 (Framework Istituzionale).
    
    NUOVO FRAMEWORK:
    - Beta Gating con hard constraints
    - Separazione INTENT vs STRUCTURAL issues
    - Verdetti mutuamente esclusivi
    - CCR interpretato in base a Risk Intent
    
    Returns:
        Dict con tutti i risultati:
        - risk_intent_spec (con hard constraints)
        - portfolio_beta
        - beta_gating (NUOVO)
        - beta_adjusted_metrics
        - drawdown_attribution
        - confidence
        - verdicts
        - aggregate_verdict (con nuova struttura)
    """
    # 1. Validate Risk Intent (DICHIARATO, mai derivato)
    is_valid, message = validate_risk_intent(risk_intent)
    if not is_valid:
        risk_intent = "GROWTH"  # Default
    
    intent_spec = get_risk_intent_spec(risk_intent)
    
    # 2. Calculate Portfolio Beta
    portfolio_beta = calculate_portfolio_beta(portfolio_returns, benchmark_returns)
    
    # 3. NUOVO: Beta Gating (hard constraint check)
    beta_gating = check_beta_gating(portfolio_beta, risk_intent)
    
    # 4. Calculate Beta-Adjusted Metrics
    beta_adjusted = calculate_beta_adjusted_metrics(
        portfolio_metrics, benchmark_metrics, portfolio_beta
    )
    
    # 5. Drawdown Attribution (aggiornato per intent vs structural)
    dd_portfolio = portfolio_metrics.get('max_drawdown', -0.30)
    dd_benchmark = benchmark_metrics.get('max_drawdown', -0.34)
    
    drawdown_attr = attribute_drawdown(
        dd_portfolio, dd_benchmark, portfolio_beta, risk_intent
    )
    
    # 6. Confidence Model
    confidence = calculate_confidence_score(
        returns_df, tickers, weights, corr_matrix
    )
    
    # 7. Rule-Based Verdicts (aggiornati per nuovo framework)
    verdicts = evaluate_verdicts(
        portfolio_metrics,
        benchmark_metrics,
        beta_adjusted,
        risk_intent,
        confidence,
        corr_matrix,
        ccr_data
    )
    
    # 8. Aggregate Verdict (con nuova struttura obbligatoria)
    aggregate = calculate_aggregate_verdict(
        confidence, verdicts, risk_intent, drawdown_attr, beta_gating
    )
    
    return {
        'risk_intent': risk_intent,
        'risk_intent_spec': {
            'level': intent_spec.level.value,
            'beta_range': intent_spec.beta_range,
            'benchmark': intent_spec.benchmark,
            'max_dd_expected': intent_spec.max_dd_expected,
            'vol_expected': intent_spec.vol_expected,
            'description': intent_spec.description,
            # NUOVO: hard constraints
            'min_beta_acceptable': intent_spec.min_beta_acceptable,
            'beta_fail_threshold': intent_spec.beta_fail_threshold,
        },
        'portfolio_beta': portfolio_beta,
        # NUOVO: Beta Gating result
        'beta_gating': {
            'passed': beta_gating['passed'],
            'is_intent_mismatch': beta_gating['is_intent_mismatch'],
            'message': beta_gating['message'],
            'verdict_type': beta_gating['verdict_type'].value,
        },
        'beta_adjusted_metrics': beta_adjusted,
        'drawdown_attribution': drawdown_attr,
        'confidence': {
            'score': confidence.score,
            'level': confidence.level.value,
            'components': confidence.components,
            'gating': confidence.gating,
            'blocked_metrics': confidence.blocked_metrics,
            'warnings': confidence.warnings,
        },
        'verdicts': [
            {
                'rule_id': v.rule_id,
                'condition': v.condition,
                'satisfied': v.satisfied,
                'type': v.verdict_type,
                'message': v.message,
            }
            for v in verdicts
        ],
        'aggregate_verdict': aggregate,
    }


def print_risk_intent_analysis(analysis: Dict[str, Any]) -> None:
    """Stampa l'analisi Risk Intent completa (Framework Istituzionale)."""
    print("\n" + "=" * 69)
    print("          RISK INTENT ANALYSIS v3.1 (Framework Istituzionale)")
    print("=" * 69)
    
    # Risk Intent Declaration (SUPREMA - mai derivata)
    spec = analysis['risk_intent_spec']
    print(f"\n📋 RISK INTENT DICHIARATO: {analysis['risk_intent']}")
    print(f"   {spec['description']}")
    print(f"   Beta target: {spec['beta_range'][0]:.1f} - {spec['beta_range'][1]:.1f}")
    print(f"   Beta min accettabile: {spec['min_beta_acceptable']:.1f}")
    print(f"   Beta FAIL threshold: {spec['beta_fail_threshold']:.1f}")
    print(f"   Benchmark: {spec['benchmark']}")
    print(f"   Max DD atteso: {spec['max_dd_expected']:.0%}")
    
    # Beta effettivo e gating
    beta = analysis['portfolio_beta']
    gating = analysis['beta_gating']
    print(f"\n🎯 BETA GATING:")
    print(f"   Portfolio Beta: {beta:.2f}")
    print(f"   {gating['message']}")
    
    # Show thresholds table if there's intent mismatch
    if gating['is_intent_mismatch'] and 'thresholds_context' in gating:
        ctx = gating['thresholds_context']
        print(f"\n   📊 {ctx['risk_intent']} Intent Thresholds:")
        print(f"      • Hard Fail (gate):        < {ctx['fail_gate']:.1f}  ❌")
        print(f"      • Minimum Acceptable:      ≥ {ctx['min_acceptable']:.1f}  ⚠️")
        print(f"      • Target Range:      {ctx['target_range'][0]:.1f} - {ctx['target_range'][1]:.1f}  ✅")
        print(f"   ⚠️ NOTA: {ctx['fail_gate']:.1f} è il fail threshold, non il target. Target: ≥{ctx['min_acceptable']:.1f}")
    
    if gating['is_intent_mismatch']:
        print(f"   ⚠️ NOTA: Questo è un problema di OBIETTIVO, non di STRUTTURA")
    
    # Confidence Model
    conf = analysis['confidence']
    print(f"\n📊 CONFIDENCE: {conf['score']:.0f}/100 ({conf['level']})")
    for warning in conf['warnings']:
        print(f"   {warning}")
    
    # Drawdown Attribution
    dd = analysis['drawdown_attribution']
    print(f"\n📉 DRAWDOWN ATTRIBUTION:")
    print(f"   Tipo: {dd['dd_type']}")
    print(f"   Osservato: {dd['observed_dd']:.1%}")
    print(f"   Atteso (β-adj): {dd['expected_dd']:.1%}")
    excess = dd['excess_dd']
    excess_symbol = "✅" if excess <= 0.05 else "⚠️" if excess <= 0.15 else "🔴"
    print(f"   Excess DD: {excess:.1%} {excess_symbol}")
    print(f"   → {dd['verdict']}")
    if dd.get('is_intent_issue'):
        print(f"   ℹ️ NOTA: Problema di INTENT, non fragilità strutturale")
    
    # Verdetti con categorizzazione
    print(f"\n✓ VERDETTI ({len(analysis['verdicts'])} regole valutate):")
    for v in analysis['verdicts']:
        if v['type'] == 'OK':
            symbol = "✅"
        elif v['type'] == 'INFO':
            symbol = "ℹ️"
        elif v['type'] in ['WARNING', 'INTENT_MISMATCH']:
            symbol = "⚠️"
        else:
            symbol = "🔴"
        # Mostra tipo per chiarezza
        type_tag = f"[{v['type']}]" if v['type'] == 'INTENT_MISMATCH' else ""
        print(f"   {symbol} [{v['rule_id']}] {type_tag} {v['message'][:55]}")
    
    # Aggregate - NUOVA STRUTTURA OBBLIGATORIA
    agg = analysis['aggregate_verdict']
    print(f"\n" + "═" * 69)
    print("              VERDETTO FINALE (Framework Istituzionale)")
    print("═" * 69)
    
    # Struttura obbligatoria
    print(f"\n   1. Risk Intent Dichiarato: {agg['risk_intent_declared']}")
    print(f"   2. Coerenza Intent vs Dati: {agg['intent_coherence']}")
    print(f"   3. Coerenza Strutturale: {agg['structural_coherence_status']}")
    
    scores = agg['scores']
    print(f"\n   Scores:")
    print(f"      Data Integrity:       {scores['data_integrity']:>5.0f}/100")
    print(f"      Structural Coherence: {scores['structural_coherence']:>5.0f}/100")
    print(f"      Efficiency:           {scores['efficiency']:>5.0f}/100")
    print(f"      Tail Risk:            {scores['tail_risk']:>5.0f}/100")
    print(f"      ─────────────────────────────")
    print(f"      AGGREGATE:            {scores['aggregate']:>5.0f}/100")
    
    # Verdetto finale
    print(f"\n   4. VERDETTO: {agg['final_verdict']}")
    if agg['final_qualifier']:
        print(f"      → {agg['final_qualifier']}")
    
    # Counts
    counts = agg['verdict_counts']
    print(f"\n   Riepilogo: {counts['ok']} OK, {counts['warning']} Warning, "
          f"{counts['structural']} Structural, {counts['intent_mismatch']} Intent Mismatch")
    
    print("═" * 69)
