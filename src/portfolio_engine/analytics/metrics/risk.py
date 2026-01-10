"""
Risk Metrics Module
===================
Sharpe, Sortino, Calmar, Drawdown analysis, VaR/CVaR.
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any
from scipy import stats

from portfolio_engine.analytics.metrics.basic import calculate_cagr


# =========================
# RISK-ADJUSTED METRICS
# =========================

def calculate_sharpe_ratio(
    returns: pd.Series, 
    risk_free_annual: float = 0.02, 
    periods: int = 252
) -> float:
    """
    Sharpe Ratio calcolato correttamente.
    
    Formula: (Mean Return - Rf) / Std * sqrt(periods)
    """
    if returns.std() == 0:
        return 0.0
    
    rf_daily = (1 + risk_free_annual) ** (1/periods) - 1
    excess_return = returns.mean() - rf_daily
    
    return float(excess_return / returns.std(ddof=1) * np.sqrt(periods))


def calculate_sortino_ratio(
    returns: pd.Series,
    risk_free_annual: float = 0.02,
    target_return: float = 0.0,
    periods: int = 252
) -> float:
    """
    Sortino Ratio con Target Downside Deviation CORRETTA.
    
    TDD = sqrt(mean(min(0, R - T)^2))
    Sortino = (Mean Return - Rf) / TDD
    """
    rf_daily = (1 + risk_free_annual) ** (1/periods) - 1
    target_daily = (1 + target_return) ** (1/periods) - 1
    
    # Calcola downside deviation
    downside = np.minimum(returns - target_daily, 0)
    downside_var = (downside ** 2).mean()
    tdd = np.sqrt(downside_var) * np.sqrt(periods)
    
    if tdd == 0:
        return 0.0
    
    # Rendimento annualizzato
    ann_return = (1 + returns.mean()) ** periods - 1
    
    return float((ann_return - risk_free_annual) / tdd)


def calculate_calmar_ratio(cagr: float, max_dd: float) -> float:
    """Calmar Ratio = CAGR / |Max Drawdown|"""
    if max_dd == 0:
        return 0.0
    return float(cagr / abs(max_dd))


# =========================
# DRAWDOWN ANALYSIS
# =========================

def calculate_max_drawdown(equity: pd.Series) -> Tuple[float, pd.Timestamp, pd.Timestamp]:
    """
    Calcola Max Drawdown con date di picco e valle.
    
    Returns:
        (max_dd, peak_date, trough_date)
    """
    peak = equity.cummax()
    drawdown = (equity - peak) / peak
    
    max_dd = float(drawdown.min())
    trough_idx = drawdown.idxmin()
    peak_idx = equity.loc[:trough_idx].idxmax()
    
    return max_dd, peak_idx, trough_idx


def calculate_drawdown_series(equity: pd.Series) -> pd.Series:
    """Calcola la serie completa dei drawdown."""
    return equity / equity.cummax() - 1


def analyze_multi_trough_recovery(equity: pd.Series) -> Dict[str, Any]:
    """
    FIX ISSUE #20: Analisi recovery che gestisce multi-trough drawdowns.
    
    Crisi come 2008-2009 hanno multipli dip. Questa funzione:
    - Identifica tutti i trough significativi (>5% drawdown)
    - Calcola recovery time per ciascuno
    - Distingue false rally da true recovery
    - Fornisce analisi più realistica
    
    Returns:
        Dict con drawdown episodes, recovery times, multi-trough warnings
    """
    dd_series = calculate_drawdown_series(equity)
    
    # Identifica tutti i drawdown significativi (>5%)
    significant_dd_threshold = -0.05
    
    # Trova tutti i local minima (troughs)
    episodes = []
    in_drawdown = False
    episode_start = None
    episode_peak = None
    local_trough = 0
    local_trough_date = None
    
    for i, (date, dd) in enumerate(dd_series.items()):
        if dd < significant_dd_threshold and not in_drawdown:
            # Inizio nuovo drawdown episode
            in_drawdown = True
            episode_start = date
            # Peak è l'ultimo punto dove dd era 0
            if i > 0:
                episode_peak = dd_series.index[i-1]
            else:
                episode_peak = date
            local_trough = dd
            local_trough_date = date
            
        elif in_drawdown:
            if dd < local_trough:
                # Nuovo minimo locale
                local_trough = dd
                local_trough_date = date
            
            if dd >= 0:
                # Recovery completo
                recovery_date = date
                episode = {
                    'peak_date': episode_peak,
                    'trough_date': local_trough_date,
                    'recovery_date': recovery_date,
                    'max_dd': local_trough,
                    'days_to_trough': (local_trough_date - episode_peak).days if hasattr(episode_peak, 'days') else 0,
                    'days_to_recovery': (recovery_date - local_trough_date).days if hasattr(recovery_date, 'days') else 0,
                    'total_days': (recovery_date - episode_peak).days if hasattr(episode_peak, 'days') else 0,
                }
                episodes.append(episode)
                in_drawdown = False
                
    # Se ancora in drawdown alla fine
    if in_drawdown:
        episodes.append({
            'peak_date': episode_peak,
            'trough_date': local_trough_date,
            'recovery_date': None,  # Non ancora recuperato
            'max_dd': local_trough,
            'days_to_trough': (local_trough_date - episode_peak).days if hasattr(episode_peak, 'days') else 0,
            'days_to_recovery': None,
            'total_days': None,
            'still_in_drawdown': True
        })
    
    # Identifica multi-trough patterns (false rallies)
    multi_trough_warnings = []
    for i, ep in enumerate(episodes[:-1]):
        if ep['recovery_date'] is not None:
            next_ep = episodes[i + 1]
            # Se nuovo drawdown inizia entro 60 giorni da recovery = false rally
            days_between = (next_ep['peak_date'] - ep['recovery_date']).days if hasattr(next_ep['peak_date'], 'days') else 0
            if days_between < 60:
                multi_trough_warnings.append({
                    'first_recovery': ep['recovery_date'],
                    'second_peak': next_ep['peak_date'],
                    'days_between': days_between,
                    'warning': f"False rally: recovery il {ep['recovery_date'].date()} seguito da nuovo drawdown dopo {days_between} giorni"
                })
    
    # Calcola statistiche aggregate
    if episodes:
        completed_episodes = [e for e in episodes if e.get('recovery_date') is not None]
        avg_recovery_days = np.mean([e['days_to_recovery'] for e in completed_episodes]) if completed_episodes else None
        max_recovery_days = max([e['days_to_recovery'] for e in completed_episodes]) if completed_episodes else None
    else:
        avg_recovery_days = None
        max_recovery_days = None
    
    return {
        'total_episodes': len(episodes),
        'completed_recoveries': len([e for e in episodes if e.get('recovery_date')]),
        'episodes': episodes,
        'multi_trough_warnings': multi_trough_warnings,
        'has_multi_trough': len(multi_trough_warnings) > 0,
        'avg_recovery_days': avg_recovery_days,
        'max_recovery_days': max_recovery_days,
        'current_drawdown': float(dd_series.iloc[-1]) if len(dd_series) > 0 else 0,
        'methodology': (
            "Multi-trough analysis identifica false rallies e recovery reali. "
            "Recovery entro 60 giorni da nuovo drawdown = false rally."
        )
    }


# =========================
# VAR / CVAR
# =========================

def calculate_var_cvar(
    returns: pd.Series, 
    confidence: float = 0.95,
    periods: int = 252
) -> Tuple[float, float]:
    """
    Calcola Value at Risk (VaR) e Conditional VaR (CVaR/Expected Shortfall).
    
    NOTA METODOLOGICA:
    - VaR Parametrico assume normalità dei returns (SOTTOSTIMA tail risk)
    - VaR Storico è più robusto per fat tails ma richiede history sufficiente
    - Usiamo VaR STORICO come default (conservative)
    
    VaR: Perdita massima al livello di confidenza (es. 95%)
    CVaR: Media delle perdite oltre il VaR (Expected Shortfall - tail risk)
    
    Returns:
        (var_daily, cvar_daily) - valori giornalieri (negativi = perdita)
    """
    # VaR parametrico (assumendo normalità) - SOLO per reference
    # ATTENZIONE: Equity returns hanno fat tails (kurtosis > 3), questo sottostima rischio
    var_parametric = returns.mean() - stats.norm.ppf(confidence) * returns.std()
    
    # VaR storico (più robusto per fat tails)
    # Usa quantile empirico - non assume distribuzione
    var_historical = returns.quantile(1 - confidence)
    
    # CVaR (Expected Shortfall) - media dei rendimenti sotto il VaR
    # Più informativo del VaR perché considera la coda intera
    tail_returns = returns[returns <= var_historical]
    cvar = tail_returns.mean() if len(tail_returns) > 0 else var_historical
    
    # Sanity check: CVaR deve essere <= VaR (più negativo)
    if cvar > var_historical:
        cvar = var_historical
    
    return float(var_historical), float(cvar)
