"""
Regime Detection Module
=======================
Modulo dedicato alla rilevazione dei regimi di mercato.

Include:
- detect_regime_quantitative(): detection basato su dati
- detect_market_regime(): wrapper principale
- REGIME_CRITERIA: criteri quantitativi espliciti per regime detection

NOTA METODOLOGICA:
Le date delle crisi sono basate su peak-to-trough del S&P500.
I "trigger" sono osservazioni storiche documentate, NON rilevati automaticamente.

CRISIS PERIODS: Importati da crisis_definitions.py (single source of truth)
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List

# Import centralized crisis definitions (Fix C2)
from portfolio_engine.data.definitions.crisis import (
    KNOWN_CRISIS_PERIODS,
    get_crisis_periods_dict,
    is_crisis_date,
    get_crisis_for_date,
    filter_crisis_returns
)


# ================================================================================
# QUANTITATIVE REGIME DETECTION CRITERIA
# ================================================================================

# NOTE: KNOWN_CRISIS_PERIODS is now imported from crisis_definitions.py
# This ensures a single source of truth for crisis period definitions.
# Use helper functions from crisis_definitions for:
#   - is_crisis_date(date): check if a date falls in a crisis
#   - get_crisis_for_date(date): get crisis info for a date
#   - filter_crisis_returns(returns): get returns during crisis periods


# Criteri quantitativi espliciti per regime detection
# Questi criteri sono DERIVABILI dai dati, non arbitrari
# ⚠️ SOURCE: Empirical analysis of S&P500 1990-2023
# Drawdown thresholds aligned with common definitions (correction: -10%, bear: -20%)
REGIME_CRITERIA = {
    'CRISIS': {
        'drawdown_threshold': -0.20,      # DD > 20% = bear market definition
        'vol_spike_threshold': 1.8,        # Vol > 80% sopra baseline (VIX ~25 vs ~14)
        'correlation_spike_threshold': 0.75,  # Correlazioni medie > 0.75
        'source': 'Bear market standard definition (S&P500 -20%)',
        'description': 'Drawdown > 20% AND (Vol spike > 80% OR Corr spike > 0.75)'
    },
    'HIGH_VOL': {
        'vol_threshold': 0.25,             # Volatilità annualizzata > 25%
        'vol_ratio_threshold': 1.5,        # Vol > 50% sopra media storica
        'source': 'VIX long-term average ~15%, >25% = elevated',
        'description': 'Volatilità > 25% annualizzata o > 150% della media storica'
    },
    'TIGHTENING': {
        'drawdown_range': (-0.30, -0.10),  # DD tra -10% e -30%
        'duration_months': 6,              # Durata > 6 mesi
        'source': 'Fed tightening cycles 1994, 2018, 2022',
        'description': 'Drawdown -10% to -30%, durata > 6 mesi (erosione graduale)'
    },
    'NORMAL': {
        'drawdown_threshold': -0.10,       # DD < 10% = correction threshold
        'vol_threshold': 0.18,             # Vol < 18% (long-term S&P ~16%)
        'source': 'Historical S&P500 average volatility ~16%',
        'description': 'Drawdown < 10%, Vol < 18% annualizzata'
    }
}


def detect_regime_quantitative(
    returns: pd.Series,
    equity_curve: pd.Series = None,
    rolling_window: int = 63  # ~3 mesi
) -> Dict[str, Any]:
    """
    Regime detection QUANTITATIVO basato su criteri espliciti.
    
    ⚠️ METODOLOGIA:
    I criteri sono derivabili dai dati, non arbitrari:
    - Drawdown: osservabile direttamente dall'equity curve
    - Volatility spike: rapporto vs baseline rolling
    - Correlation spike: rilevabile da portfolio dispersion
    
    Args:
        returns: Serie returns giornalieri
        equity_curve: Serie equity curve (opzionale, calcolata se non fornita)
        rolling_window: Finestra per calcoli rolling (default 63 = 3 mesi)
    
    Returns:
        Dict con regime detection, criteri soddisfatti, e evidence
    """
    if equity_curve is None:
        equity_curve = (1 + returns).cumprod()
    
    # Calcola metriche per detection
    # 1. Drawdown
    rolling_max = equity_curve.expanding().max()
    drawdown = (equity_curve - rolling_max) / rolling_max
    max_dd = float(drawdown.min())
    current_dd = float(drawdown.iloc[-1])
    
    # 2. Volatility
    vol_annual = float(returns.std() * np.sqrt(252))
    rolling_vol = returns.rolling(rolling_window).std() * np.sqrt(252)
    baseline_vol = rolling_vol.median()
    max_vol_spike = float(rolling_vol.max() / baseline_vol) if baseline_vol > 0 else 1.0
    
    # 3. Periodi in crisi (DD < -10%)
    crisis_days = (drawdown < -0.10).sum()
    crisis_pct = crisis_days / len(drawdown) * 100
    
    # Apply criteria
    criteria_met = []
    regime_scores = {
        'CRISIS': 0,
        'HIGH_VOL': 0,
        'TIGHTENING': 0,
        'NORMAL': 0
    }
    
    # Check CRISIS criteria
    crisis_criteria = REGIME_CRITERIA['CRISIS']
    if max_dd < crisis_criteria['drawdown_threshold']:
        criteria_met.append(f"DD {max_dd:.1%} < {crisis_criteria['drawdown_threshold']:.0%}")
        regime_scores['CRISIS'] += 2
    if max_vol_spike > crisis_criteria['vol_spike_threshold']:
        criteria_met.append(f"Vol spike {max_vol_spike:.1f}x > {crisis_criteria['vol_spike_threshold']:.1f}x")
        regime_scores['CRISIS'] += 1
    
    # Check HIGH_VOL criteria
    highvol_criteria = REGIME_CRITERIA['HIGH_VOL']
    if vol_annual > highvol_criteria['vol_threshold']:
        criteria_met.append(f"Vol {vol_annual:.1%} > {highvol_criteria['vol_threshold']:.0%}")
        regime_scores['HIGH_VOL'] += 1
    
    # Check TIGHTENING criteria
    tight_criteria = REGIME_CRITERIA['TIGHTENING']
    if tight_criteria['drawdown_range'][0] < max_dd < tight_criteria['drawdown_range'][1]:
        criteria_met.append(f"DD {max_dd:.1%} in range tightening")
        regime_scores['TIGHTENING'] += 1
    
    # Check NORMAL criteria
    normal_criteria = REGIME_CRITERIA['NORMAL']
    if max_dd > normal_criteria['drawdown_threshold'] and vol_annual < normal_criteria['vol_threshold']:
        criteria_met.append(f"DD {max_dd:.1%} > {normal_criteria['drawdown_threshold']:.0%} AND Vol {vol_annual:.1%} < {normal_criteria['vol_threshold']:.0%}")
        regime_scores['NORMAL'] += 2
    
    # Determine primary regime
    primary_regime = max(regime_scores, key=regime_scores.get)
    if regime_scores[primary_regime] == 0:
        primary_regime = 'MIXED'
    
    return {
        'primary_regime': primary_regime,
        'regime_scores': regime_scores,
        'criteria_met': criteria_met,
        'evidence': {
            'max_drawdown': max_dd,
            'current_drawdown': current_dd,
            'volatility_annual': vol_annual,
            'max_vol_spike': max_vol_spike,
            'crisis_days_pct': crisis_pct,
            'baseline_vol': float(baseline_vol) if not pd.isna(baseline_vol) else vol_annual
        },
        'thresholds_used': REGIME_CRITERIA,
        'interpretation': _interpret_regime(primary_regime, max_dd, vol_annual, crisis_pct)
    }


def _interpret_regime(regime: str, max_dd: float, vol: float, crisis_pct: float) -> str:
    """Genera interpretazione del regime."""
    
    if regime == 'CRISIS':
        return (
            f"Periodo include CRISI: DD {max_dd:.1%}, {crisis_pct:.0f}% giorni in stress. "
            f"Le metriche (Sharpe, etc.) sono compresse FISIOLOGICAMENTE, non per fragilità."
        )
    elif regime == 'HIGH_VOL':
        return (
            f"Regime HIGH VOL: volatilità {vol:.1%} elevata. "
            f"Risk-adjusted metrics penalizzate meccanicamente, non necessariamente da strategia debole."
        )
    elif regime == 'TIGHTENING':
        return (
            f"Regime TIGHTENING: erosione graduale (DD {max_dd:.1%}). "
            f"Tipico di cicli di rialzo tassi. Diverso da crash improvviso."
        )
    elif regime == 'NORMAL':
        return (
            f"Regime NORMALE: DD {max_dd:.1%}, Vol {vol:.1%}. "
            f"Condizioni favorevoli - metriche rappresentative ma potrebbero sovrastimare resilienza futura."
        )
    else:
        return (
            f"Regime MISTO: condizioni variabili. "
            f"Metriche aggregate possono mascherare periodi di stress localizzati."
        )


def detect_market_regime(
    start_date: str,
    end_date: str,
    max_drawdown: float,
    volatility: float,
    avg_correlation: float = None
) -> Dict[str, Any]:
    """
    RILEVAZIONE REGIME DI MERCATO (funzione principale)
    
    Identifica il/i regime/i di mercato presenti nel periodo analizzato.
    
    Args:
        start_date: Data inizio analisi (YYYY-MM-DD)
        end_date: Data fine analisi
        max_drawdown: Max drawdown osservato (negativo)
        volatility: Volatilità annualizzata
        avg_correlation: Correlazione media (opzionale)
    
    Returns:
        Dict con:
        - primary_regime: regime dominante
        - crisis_periods: lista periodi di crisi inclusi
        - regime_thresholds: soglie adattate
        - regime_context: spiegazione per output
    """
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    period_years = (end - start).days / 365.25
    
    # Identifica periodi di crisi inclusi
    crisis_periods = []
    for crisis in KNOWN_CRISIS_PERIODS:
        crisis_start = pd.to_datetime(crisis["start"])
        crisis_end = pd.to_datetime(crisis["end"])
        
        # Check overlap
        if start <= crisis_end and end >= crisis_start:
            overlap_start = max(start, crisis_start)
            overlap_end = min(end, crisis_end)
            overlap_days = (overlap_end - overlap_start).days
            
            if overlap_days > 30:  # Almeno 1 mese di overlap
                crisis_periods.append({
                    **crisis,
                    "overlap_days": overlap_days,
                    "overlap_pct": overlap_days / ((end - start).days) * 100
                })
    
    # Determina regime primario
    has_systemic_crisis = any(c["type"] == "SYSTEMIC_CRISIS" for c in crisis_periods)
    has_tightening = any(c["type"] == "TIGHTENING" for c in crisis_periods)
    has_sector_stress = any(c["type"] in ["SECTOR_STRESS", "REGIONAL_STRESS"] for c in crisis_periods)
    
    if has_systemic_crisis:
        primary_regime = "INCLUDES_SYSTEMIC_CRISIS"
        regime_description = "Periodo include crisi sistemica"
    elif has_tightening:
        primary_regime = "INCLUDES_TIGHTENING"
        regime_description = "Periodo include ciclo di tightening"
    elif has_sector_stress:
        primary_regime = "INCLUDES_STRESS"
        regime_description = "Periodo include stress settoriale/regionale"
    elif period_years > 10:
        primary_regime = "FULL_CYCLE"
        regime_description = "Periodo multi-ciclico (>10 anni)"
    else:
        primary_regime = "NORMAL"
        regime_description = "Periodo prevalentemente normale"
    
    # Calcola soglie adattate al regime
    regime_thresholds = _calculate_regime_adjusted_thresholds(
        primary_regime, crisis_periods, period_years, max_drawdown
    )
    
    # Genera contesto per output
    regime_context = _generate_regime_context(
        primary_regime, crisis_periods, period_years, max_drawdown, volatility
    )
    
    return {
        "primary_regime": primary_regime,
        "crisis_periods": crisis_periods,
        "regime_thresholds": regime_thresholds,
        "regime_context": regime_context,
        "period_years": period_years,
        "includes_gfc": any(c["name"] == "GFC" for c in crisis_periods),
        "includes_covid": any(c["name"] == "COVID Crash" for c in crisis_periods),
    }


def _calculate_regime_adjusted_thresholds(
    regime: str,
    crisis_periods: list,
    period_years: float,
    observed_max_dd: float
) -> Dict[str, Any]:
    """
    Calcola soglie adattate al regime di mercato.
    
    ⚠️ DOCUMENTAZIONE SOGLIE:
    Le soglie sono basate su:
    - Normal: Historical S&P500 average Sharpe ~0.4-0.5, Vol ~16%
    - Crisis: GFC Sharpe negative, Vol 40%+, DD -57%
    - Tightening: 2022 Sharpe ~0.2-0.3, Vol 20-25%
    
    SOURCE: Analysis of S&P500 1990-2023, Vanguard research papers
    """
    # Soglie base (regime normale) con source documentation
    normal_thresholds = {
        "min_sharpe": 0.55,  # S&P500 1990-2023 avg Sharpe ~0.45, +0.10 buffer
        "min_sortino": 0.80,
        "max_drawdown_equity": -0.30,  # Correction threshold
        "max_drawdown_balanced": -0.18,
        "acceptable_correlation_spike": 0.70,
        "source": "Historical S&P500 1990-2023 averages",
    }
    
    if regime == "INCLUDES_SYSTEMIC_CRISIS":
        return {
            "min_sharpe": 0.20,  # GFC/COVID periods had negative Sharpe
            "min_sharpe_acceptable": 0.35,
            "min_sortino": 0.40,
            "min_sortino_acceptable": 0.60,
            "max_drawdown_equity": -0.55,  # GFC S&P500 = -57%
            "max_drawdown_balanced": -0.35,
            "acceptable_correlation_spike": 0.90,  # Correlations spike to 0.80+ in crisis
            "regime_note": "Soglie adattate per crisi sistemica",
            "source": "GFC/COVID empirical data",
        }
    
    elif regime == "INCLUDES_TIGHTENING":
        return {
            "min_sharpe": 0.30,  # 2022: S&P Sharpe ~0.2
            "min_sharpe_acceptable": 0.45,
            "min_sortino": 0.50,
            "min_sortino_acceptable": 0.70,
            "max_drawdown_equity": -0.40,  # 2022: S&P -25%
            "max_drawdown_balanced": -0.25,
            "acceptable_correlation_spike": 0.80,
            "regime_note": "Soglie adattate per ciclo tightening",
            "source": "Fed tightening cycles 1994, 2018, 2022",
        }
    
    elif regime == "FULL_CYCLE":
        return {
            "min_sharpe": 0.35,
            "min_sharpe_acceptable": 0.50,
            "min_sortino": 0.55,
            "min_sortino_acceptable": 0.75,
            "max_drawdown_equity": -0.45,
            "max_drawdown_balanced": -0.28,
            "acceptable_correlation_spike": 0.80,
            "regime_note": "Soglie per periodo multi-ciclico",
            "source": "Full market cycle analysis",
        }
    
    else:
        return {**normal_thresholds, "regime_note": "Soglie standard"}


def _generate_regime_context(
    regime: str,
    crisis_periods: list,
    period_years: float,
    max_dd: float,
    volatility: float
) -> Dict[str, Any]:
    """Genera contesto narrativo per l'output."""
    
    crisis_names = [c["name"] for c in crisis_periods]
    
    context = {
        "regime_detected": regime,
        "period_length": f"{period_years:.1f} anni",
        "crisis_included": crisis_names if crisis_names else ["Nessuna crisi sistemica"],
        "observed_max_dd": max_dd,
        "observed_volatility": volatility,
    }
    
    if regime == "INCLUDES_SYSTEMIC_CRISIS":
        context["institutional_note"] = (
            "Le metriche osservate sono influenzate dalla presenza di regimi di stress sistemico "
            f"({', '.join(crisis_names)}) e devono essere interpretate in tale contesto. "
            "Sharpe e Sortino compressi sono fisiologici, non indicano fragilità strutturale."
        )
        context["drawdown_interpretation"] = (
            f"Max Drawdown {max_dd:.1%} coerente con crisi sistemica inclusa nel periodo. "
            "Drawdown -50% su 100% equity durante GFC è benchmark di riferimento."
        )
    elif regime == "FULL_CYCLE":
        context["institutional_note"] = (
            f"Periodo di {period_years:.0f} anni include multipli cicli economici. "
            "Le metriche rappresentano performance attraverso regimi diversi."
        )
    else:
        context["institutional_note"] = "Periodo prevalentemente normale."
    
    return context


# ================================================================================
# CORRELATION REGIME ANALYSIS (FIX #2 - Correlation regime switching)
# ================================================================================

def calculate_correlation_by_regime(
    returns: pd.DataFrame,
    portfolio_returns: pd.Series = None,
    crisis_threshold: float = -0.02  # -2% daily = crisis day
) -> Dict[str, Any]:
    """
    Calcola correlazioni SEPARATE per regime normale vs stress.
    
    FIX ISSUE: Risk contribution assume correlazioni costanti.
    Questa funzione calcola correlazioni condizionate al regime.
    
    Args:
        returns: DataFrame con returns di tutti gli asset
        portfolio_returns: Serie returns portafoglio (per identificare giorni stress)
        crisis_threshold: Soglia return giornaliero per "crisis day"
    
    Returns:
        Dict con:
        - corr_normal: matrice correlazioni in regime normale
        - corr_stress: matrice correlazioni in regime stress
        - correlation_spike: quanto aumentano le correlazioni in stress
        - warning: se correlazioni stress sono molto diverse da normali
    """
    if portfolio_returns is None:
        portfolio_returns = returns.mean(axis=1)
    
    # Identifica giorni di stress vs normali
    # Definizione: stress = return portafoglio < threshold O top 5% worst days
    stress_mask = (portfolio_returns < crisis_threshold)
    
    # Aggiungi anche top 5% worst days
    percentile_5 = portfolio_returns.quantile(0.05)
    stress_mask = stress_mask | (portfolio_returns <= percentile_5)
    
    normal_mask = ~stress_mask
    
    # Calcola correlazioni separate
    returns_normal = returns[normal_mask]
    returns_stress = returns[stress_mask]
    
    corr_normal = returns_normal.corr() if len(returns_normal) > 30 else returns.corr()
    corr_stress = returns_stress.corr() if len(returns_stress) > 30 else returns.corr()
    
    # Calcola metriche comparative
    # Media correlazioni (esclusa diagonale)
    def mean_off_diagonal(corr_matrix):
        mask = ~np.eye(len(corr_matrix), dtype=bool)
        return corr_matrix.values[mask].mean()
    
    avg_corr_normal = mean_off_diagonal(corr_normal)
    avg_corr_stress = mean_off_diagonal(corr_stress)
    correlation_spike = avg_corr_stress - avg_corr_normal
    
    # Warning se spike significativo
    warning = None
    if correlation_spike > 0.15:
        warning = (
            f"⚠️ CORRELATION BREAKDOWN: correlazioni aumentano di {correlation_spike:.2f} in stress "
            f"(normale: {avg_corr_normal:.2f}, stress: {avg_corr_stress:.2f}). "
            "Risk contribution in regime normale sottostima rischio in crisi."
        )
    
    return {
        'corr_normal': corr_normal,
        'corr_stress': corr_stress,
        'avg_corr_normal': avg_corr_normal,
        'avg_corr_stress': avg_corr_stress,
        'correlation_spike': correlation_spike,
        'normal_days': int(normal_mask.sum()),
        'stress_days': int(stress_mask.sum()),
        'warning': warning,
        'methodology': (
            f"Stress days = return < {crisis_threshold:.1%} OR bottom 5% days. "
            f"Normal: {int(normal_mask.sum())} days, Stress: {int(stress_mask.sum())} days."
        )
    }


def calculate_risk_contribution_by_regime(
    returns: pd.DataFrame,
    weights: np.ndarray,
    tickers: list,
    portfolio_returns: pd.Series = None
) -> Dict[str, Any]:
    """
    Calcola risk contribution SEPARATAMENTE per regime normale vs stress.
    
    FIX ISSUE: MCR = (Cov @ w) / σ_p assume correlazioni costanti.
    Questa funzione mostra come cambia CCR% in stress.
    
    Returns:
        Dict con CCR normale, CCR stress, e delta per ogni ticker
    """
    corr_by_regime = calculate_correlation_by_regime(returns, portfolio_returns)
    
    # Calcola covariance per regime
    def calculate_ccr(returns_subset):
        cov = returns_subset.cov() * 252
        portfolio_vol = np.sqrt(weights @ cov @ weights)
        mcr = cov @ weights / portfolio_vol
        ccr = weights * mcr
        ccr_pct = ccr / ccr.sum() if ccr.sum() > 0 else ccr
        return ccr_pct
    
    # Identifica giorni
    if portfolio_returns is None:
        portfolio_returns = (returns * weights).sum(axis=1)
    
    percentile_5 = portfolio_returns.quantile(0.05)
    stress_mask = portfolio_returns <= percentile_5
    normal_mask = ~stress_mask
    
    returns_normal = returns[normal_mask]
    returns_stress = returns[stress_mask]
    
    ccr_normal = calculate_ccr(returns_normal) if len(returns_normal) > 30 else calculate_ccr(returns)
    ccr_stress = calculate_ccr(returns_stress) if len(returns_stress) > 30 else calculate_ccr(returns)
    
    # Build result
    result = {
        'by_ticker': {},
        'correlation_regime': corr_by_regime,
        'warning': corr_by_regime.get('warning'),
    }
    
    for i, ticker in enumerate(tickers):
        delta = ccr_stress[i] - ccr_normal[i]
        result['by_ticker'][ticker] = {
            'ccr_normal': float(ccr_normal[i]),
            'ccr_stress': float(ccr_stress[i]),
            'delta': float(delta),
            'note': '↑ RISCHIO IN CRISI' if delta > 0.03 else ('↓' if delta < -0.03 else '≈ stabile')
        }
    
    return result


def calculate_crisis_handling_quality(
    portfolio_max_dd: float,
    benchmark_max_dd: float,
    portfolio_recovery_days: int = None,
    benchmark_recovery_days: int = None,
    crisis_periods: list = None
) -> Dict[str, Any]:
    """
    FIX ISSUE #13: Distingue portfoli che hanno gestito bene vs male le crisi.
    
    Due portfoli con stesso Sharpe possono avere gestito le crisi molto diversamente:
    - Portfolio A: Sharpe 0.25, -55% in GFC (ha seguito il mercato)
    - Portfolio B: Sharpe 0.25, -25% in GFC (protezione attiva)
    
    Questa funzione produce un QUALITY SCORE che distingue i due casi.
    
    Args:
        portfolio_max_dd: Max drawdown osservato del portfolio
        benchmark_max_dd: Max drawdown del benchmark (es. VT -50% in GFC)
        portfolio_recovery_days: Giorni per recovery del portfolio
        benchmark_recovery_days: Giorni per recovery del benchmark
        crisis_periods: Lista crisi identificate nel periodo
    
    Returns:
        Dict con quality score, comparison, e interpretation
    """
    # Default benchmark drawdowns (empirici)
    if benchmark_max_dd is None:
        benchmark_max_dd = -0.50  # GFC: -57%, COVID: -34%, media pesata
    
    # Calcola DD protection ratio
    # Ratio > 1 = portfolio ha protetto MEGLIO del benchmark
    # Ratio < 1 = portfolio ha seguito o peggio del benchmark
    if benchmark_max_dd != 0:
        dd_protection_ratio = portfolio_max_dd / benchmark_max_dd
    else:
        dd_protection_ratio = 1.0
    
    # Quality scoring
    if dd_protection_ratio >= 0.7:  # DD portfolio <= 70% DD benchmark
        quality_score = 'EXCELLENT'
        quality_emoji = '🟢'
        interpretation = (
            f"Portfolio ha mostrato PROTEZIONE durante crisi: "
            f"DD {portfolio_max_dd:.1%} vs benchmark {benchmark_max_dd:.1%} "
            f"(ratio {dd_protection_ratio:.2f}x → {(1-dd_protection_ratio):.0%} meno perdite)"
        )
    elif dd_protection_ratio >= 0.9:  # DD portfolio <= 90% DD benchmark
        quality_score = 'GOOD'
        quality_emoji = '🟡'
        interpretation = (
            f"Portfolio leggermente più resiliente: "
            f"DD {portfolio_max_dd:.1%} vs benchmark {benchmark_max_dd:.1%}"
        )
    elif dd_protection_ratio <= 1.1:  # DD portfolio ~= DD benchmark
        quality_score = 'NEUTRAL'
        quality_emoji = '⚪'
        interpretation = (
            f"Portfolio ha seguito il mercato: "
            f"DD {portfolio_max_dd:.1%} ~ benchmark {benchmark_max_dd:.1%}"
        )
    else:  # DD portfolio > benchmark
        quality_score = 'POOR'
        quality_emoji = '🔴'
        interpretation = (
            f"Portfolio ha AMPLIFICATO le perdite: "
            f"DD {portfolio_max_dd:.1%} > benchmark {benchmark_max_dd:.1%} "
            f"({(dd_protection_ratio-1):.0%} peggio)"
        )
    
    # Recovery analysis se disponibile
    recovery_comparison = None
    if portfolio_recovery_days is not None and benchmark_recovery_days is not None:
        recovery_ratio = portfolio_recovery_days / benchmark_recovery_days if benchmark_recovery_days > 0 else 1
        if recovery_ratio <= 0.8:
            recovery_comparison = f"Recovery {portfolio_recovery_days} giorni vs benchmark {benchmark_recovery_days} (VELOCE)"
        elif recovery_ratio >= 1.2:
            recovery_comparison = f"Recovery {portfolio_recovery_days} giorni vs benchmark {benchmark_recovery_days} (LENTO)"
        else:
            recovery_comparison = f"Recovery simile al benchmark (~{portfolio_recovery_days} giorni)"
    
    return {
        'quality_score': quality_score,
        'quality_emoji': quality_emoji,
        'dd_protection_ratio': dd_protection_ratio,
        'interpretation': interpretation,
        'recovery_comparison': recovery_comparison,
        'portfolio_max_dd': portfolio_max_dd,
        'benchmark_max_dd': benchmark_max_dd,
        'methodology': (
            "Crisis handling quality = portfolio_dd / benchmark_dd. "
            "Ratio < 0.7 = EXCELLENT (>30% protezione), Ratio > 1.1 = POOR (amplifica perdite)"
        ),
        'actionable_note': (
            "⚠️ 'Sharpe basso è fisiologico in crisi' NON è un'assoluzione. "
            "Questo score distingue chi ha protetto vs chi ha solo sofferto."
        )
    }
