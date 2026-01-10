"""
Basic Return Calculations
=========================
Simple returns, log returns, basic performance metrics.
"""

import numpy as np
import pandas as pd


# =========================
# RETURNS CALCULATION
# =========================

def calculate_simple_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola i SIMPLE returns (non log returns).
    I simple returns sono additivi per portfolio pesati.
    """
    return prices.pct_change().dropna()


def calculate_log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Calcola i log returns (per analisi singolo asset)."""
    return np.log(prices / prices.shift(1)).dropna()


# =========================
# PERFORMANCE METRICS
# =========================

def calculate_cagr(equity: pd.Series, periods_per_year: int = None) -> float:
    """
    Calcola il CAGR CORRETTO dall'equity curve.
    
    FIX ISSUE #8: Usa trading days REALI invece di assumere 252.
    Anni reali variano: 251-253 trading days.
    
    Formula: CAGR = (Final/Initial)^(1/years) - 1
    
    Args:
        equity: Serie equity curve con DatetimeIndex
        periods_per_year: Se None, calcola dai dati reali (consigliato)
    
    Returns:
        CAGR come float
    """
    if len(equity) < 2:
        return 0.0
    
    total_return = equity.iloc[-1] / equity.iloc[0]
    
    # FIX ISSUE #8: Calcola anni reali dai timestamp se disponibili
    if periods_per_year is None and hasattr(equity.index, 'date'):
        # Calcola anni solari reali invece di assumere 252 trading days
        start_date = equity.index[0]
        end_date = equity.index[-1]
        n_years = (end_date - start_date).days / 365.25
    else:
        # Fallback a metodo tradizionale
        periods_per_year = periods_per_year or 252
        n_years = len(equity) / periods_per_year
    
    if n_years <= 0:
        return 0.0
    
    cagr = total_return ** (1 / n_years) - 1
    return float(cagr)


# Alias per compatibilità
calculate_cagr_correct = calculate_cagr


def calculate_annualized_volatility(returns: pd.Series, periods: int = 252) -> float:
    """Volatilità annualizzata dai rendimenti giornalieri."""
    return float(returns.std(ddof=1) * np.sqrt(periods))
