"""
Optimization Utilities
======================
Helper functions per ottimizzazione Markowitz.
Riusa shrinkage e metriche esistenti nel progetto.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd

from portfolio_engine.analytics.metrics_monolith import calculate_shrunk_correlation


def compute_covariance_matrix(
    returns: pd.DataFrame,
    annualize: bool = True,
    use_shrinkage: bool = True,
    periods_per_year: int = 252,
) -> np.ndarray:
    """Calcola matrice di covarianza, con opzione shrinkage Ledoit-Wolf (project-level)."""
    if use_shrinkage:
        corr_shrunk = calculate_shrunk_correlation(returns)
        # Funzione può restituire (corr, delta); gestisci tuple
        if isinstance(corr_shrunk, tuple):
            corr_shrunk = corr_shrunk[0]
        std = returns.std().values
        cov = corr_shrunk.values * np.outer(std, std)
    else:
        cov = returns.cov().values
    if annualize:
        cov = cov * periods_per_year
    return cov


def compute_expected_returns(
    returns: pd.DataFrame,
    annualize: bool = True,
    periods_per_year: int = 252,
    shrinkage_factor: float = 0.0,
) -> np.ndarray:
    """
    Calcola rendimenti attesi annualizzati; opzionale shrinkage verso media globale.
    
    Annualizzazione: (1 + mu_daily)^252 - 1 (compounding corretto).
    La formula mu * 252 sovrastima il rendimento composto atteso,
    specialmente per asset volatili (bias ~1-2% CAGR per vol > 30%).
    """
    mu = returns.mean().values
    if shrinkage_factor > 0:
        global_mean = mu.mean()
        mu = (1 - shrinkage_factor) * mu + shrinkage_factor * global_mean
    if annualize:
        # Compounding corretto invece di mu * periods_per_year
        mu = (1 + mu) ** periods_per_year - 1
    return mu


def portfolio_statistics(
    weights: np.ndarray,
    expected_returns: np.ndarray,
    covariance_matrix: np.ndarray,
    risk_free_rate: float = 0.0,
) -> Tuple[float, float, float]:
    """Calcola (return, volatility, sharpe)."""
    ret = float(weights @ expected_returns)
    vol = float(np.sqrt(weights @ covariance_matrix @ weights))
    sharpe = (ret - risk_free_rate) / vol if vol > 0 else 0.0
    return ret, vol, sharpe
