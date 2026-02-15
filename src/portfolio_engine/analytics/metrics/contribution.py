"""
Risk Contribution Module
========================
Marginal and Component risk contribution, conditional CCR.
"""

import numpy as np
import pandas as pd
from typing import Dict


# =========================
# RISK CONTRIBUTION
# =========================

def calculate_risk_contribution(
    returns: pd.DataFrame,
    weights: np.ndarray,
    tickers: list,
    periods: int = 252
) -> pd.DataFrame:
    """
    Risk Contribution calcolata correttamente.
    
    MCR_i = (Cov @ w)_i / sigma_p
    CCR_i = w_i * MCR_i
    
    Le CCR sommano a sigma_p (100% del rischio).
    """
    cov = returns.cov() * periods
    w = weights.reshape(-1, 1)
    
    # Varianza e volatilità del portafoglio
    port_var = float((w.T @ cov.values @ w).item())
    port_vol = np.sqrt(port_var)
    if port_vol == 0:
        zeros = np.zeros_like(weights, dtype=float)
        return pd.DataFrame({
            "Weight": weights,
            "MCR": zeros,
            "CCR": zeros,
            "RC%": zeros
        }, index=tickers)
    
    # Marginal Contribution to Risk
    mcr = (cov.values @ w).flatten() / port_vol
    
    # Component Contribution to Risk (pesi * MCR)
    ccr = weights * mcr
    
    # Risk Contribution percentuale (somma a 1.0 = 100% del rischio)
    rc_pct = ccr / port_vol
    
    return pd.DataFrame({
        "Weight": weights,
        "MCR": mcr,
        "CCR": ccr,
        "RC%": rc_pct
    }, index=tickers)


def calculate_conditional_risk_contribution(
    returns: pd.DataFrame,
    weights: np.ndarray,
    tickers: list,
    periods: int = 252,
    crisis_threshold: float | None = None,
    crisis_sigma: float = 2.0
) -> Dict[str, pd.DataFrame]:
    """
    Calcola Risk Contribution condizionata a regime normale vs crisi.
    
    ⚠️ IMPORTANTE per l'interpretazione:
    La CCR% in condizioni NORMALI può essere molto diversa da quella in CRISI.
    Asset apparentemente a basso rischio possono contribuire molto più in crisi
    quando le correlazioni convergono verso 1.
    
    Metodologia:
    - Normale: giorni con return portafoglio >= crisis_threshold
    - Crisi: giorni con return portafoglio < crisis_threshold (tipicamente -2%)
    
    Args:
        returns: DataFrame returns giornalieri
        weights: Array pesi
        tickers: Lista ticker
        periods: Giorni annui
        crisis_threshold: Soglia per definire "crisi" (se None usa -crisis_sigma * vol)
        crisis_sigma: Moltiplicatore della volatilità per stimare la soglia di crisi
    
    Returns:
        Dict con 'normal', 'crisis', 'comparison', 'summary'
    """
    # Calcola returns portafoglio
    port_returns = (returns * weights).sum(axis=1)
    
    # Split normale vs crisi
    if crisis_threshold is None:
        crisis_threshold = -crisis_sigma * port_returns.std(ddof=1)
    normal_mask = port_returns >= crisis_threshold
    crisis_mask = port_returns < crisis_threshold
    
    returns_normal = returns[normal_mask]
    returns_crisis = returns[crisis_mask]
    
    # CCR in condizioni normali
    if len(returns_normal) > 30:  # Minimo 30 osservazioni
        ccr_normal = calculate_risk_contribution(returns_normal, weights, tickers, periods)
    else:
        ccr_normal = calculate_risk_contribution(returns, weights, tickers, periods)
    
    # CCR in condizioni di crisi
    if len(returns_crisis) > 30:
        ccr_crisis = calculate_risk_contribution(returns_crisis, weights, tickers, periods)
    else:
        # Non abbastanza dati crisi - usa correlazione simulata crisi
        # Simula correlazioni convergenti verso 0.9
        cov_normal = returns.cov() * periods
        std_devs = np.sqrt(np.diag(cov_normal.values))
        crisis_corr = np.full((len(tickers), len(tickers)), 0.85)
        np.fill_diagonal(crisis_corr, 1.0)
        cov_crisis_sim = np.outer(std_devs, std_devs) * crisis_corr
        
        # Calcola CCR con covarianza crisi simulata
        w = weights.reshape(-1, 1)
        port_var = float((w.T @ cov_crisis_sim @ w).item())
        port_vol = np.sqrt(port_var)
        mcr = (cov_crisis_sim @ w).flatten() / port_vol
        ccr = weights * mcr
        ccr_pct = ccr / port_vol
        
        ccr_crisis = pd.DataFrame({
            "Weight": weights,
            "MCR": mcr,
            "CCR": ccr,
            "RC%": ccr_pct
        }, index=tickers)
    
    # Confronto: quanto cambia la RC% in crisi vs normale
    comparison = pd.DataFrame({
        "RC%_normal": ccr_normal["RC%"],
        "RC%_crisis": ccr_crisis["RC%"],
        "Delta": ccr_crisis["RC%"] - ccr_normal["RC%"],
        "Multiplier": ccr_crisis["RC%"] / ccr_normal["RC%"].replace(0, np.nan)
    }, index=tickers)
    
    return {
        'normal': ccr_normal,
        'crisis': ccr_crisis,
        'comparison': comparison,
        'summary': {
            'normal_days': len(returns_normal),
            'crisis_days': len(returns_crisis),
            'crisis_threshold': crisis_threshold,
            'crisis_sigma': crisis_sigma if crisis_threshold is not None else None,
            'simulated_crisis': len(returns_crisis) < 30
        }
    }


# Alias per compatibilità
calculate_risk_contribution_correct = calculate_risk_contribution
