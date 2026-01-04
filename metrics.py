"""
Portfolio Metrics Module
========================
Funzioni per il calcolo delle metriche di portafoglio.

Includes:
- Returns calculation (simple, log)
- Risk metrics (volatility, VaR, CVaR)
- Performance metrics (CAGR, Sharpe, Sortino, Calmar)
- Drawdown analysis
- Risk contribution
"""

import numpy as np
import pandas as pd
from typing import Tuple
from scipy import stats


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

def calculate_cagr(equity: pd.Series, periods_per_year: int = 252) -> float:
    """
    Calcola il CAGR CORRETTO dall'equity curve.
    
    Formula: CAGR = (Final/Initial)^(1/years) - 1
    """
    if len(equity) < 2:
        return 0.0
    
    total_return = equity.iloc[-1] / equity.iloc[0]
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


# =========================
# RISK METRICS
# =========================

def calculate_var_cvar(
    returns: pd.Series, 
    confidence: float = 0.95,
    periods: int = 252
) -> Tuple[float, float]:
    """
    Calcola Value at Risk (VaR) e Conditional VaR (CVaR/Expected Shortfall).
    
    VaR: Perdita massima al livello di confidenza (es. 95%)
    CVaR: Media delle perdite oltre il VaR (tail risk)
    
    Returns:
        (var_daily, cvar_daily) - valori giornalieri (negativi = perdita)
    """
    # VaR parametrico (assumendo normalità)
    var_parametric = returns.mean() - stats.norm.ppf(confidence) * returns.std()
    
    # VaR storico (più robusto)
    var_historical = returns.quantile(1 - confidence)
    
    # CVaR (Expected Shortfall) - media dei rendimenti sotto il VaR
    cvar = returns[returns <= var_historical].mean()
    
    return float(var_historical), float(cvar)


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
    
    # Marginal Contribution to Risk
    mcr = (cov.values @ w).flatten() / port_vol
    
    # Component Contribution to Risk (pesi * MCR)
    ccr = weights * mcr
    
    # Percentuale di contribuzione (somma a 1)
    ccr_pct = ccr / port_vol
    
    return pd.DataFrame({
        "Weight": weights,
        "MCR": mcr,
        "CCR": ccr,
        "CCR%": ccr_pct
    }, index=tickers)

# Alias per compatibilità
calculate_risk_contribution_correct = calculate_risk_contribution


# =========================
# COMPREHENSIVE METRICS
# =========================

def calculate_all_metrics(
    equity: pd.Series,
    returns: pd.Series,
    risk_free: float = 0.02,
    var_confidence: float = 0.95
) -> dict:
    """Calcola tutte le metriche del portafoglio."""
    
    periods = 252
    
    # Performance
    total_roi = float(equity.iloc[-1] / equity.iloc[0] - 1)
    cagr = calculate_cagr(equity, periods)
    volatility = calculate_annualized_volatility(returns, periods)
    
    # Risk-adjusted
    sharpe = calculate_sharpe_ratio(returns, risk_free, periods)
    sortino = calculate_sortino_ratio(returns, risk_free, 0.0, periods)
    
    # Drawdown
    max_dd, peak_date, trough_date = calculate_max_drawdown(equity)
    calmar = calculate_calmar_ratio(cagr, max_dd)
    
    dd_series = calculate_drawdown_series(equity)
    avg_dd = float(dd_series.mean())
    current_dd = float(dd_series.iloc[-1])
    
    # VaR e CVaR
    var_daily, cvar_daily = calculate_var_cvar(returns, var_confidence, periods)
    var_annual = var_daily * np.sqrt(periods)
    cvar_annual = cvar_daily * np.sqrt(periods)
    
    # Monthly stats
    monthly_ret = returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)
    months_up = int((monthly_ret > 0).sum())
    months_down = int((monthly_ret < 0).sum())
    months_total = len(monthly_ret)
    
    # Yearly stats
    yearly_ret = returns.resample('YE').apply(lambda x: (1 + x).prod() - 1)
    years_up = int((yearly_ret > 0).sum())
    years_down = int((yearly_ret < 0).sum())
    years_total = len(yearly_ret)
    
    # Daily stats
    days_up = int((returns > 0).sum())
    days_down = int((returns < 0).sum())
    days_total = len(returns)
    
    # Gain/Loss metrics
    gains = returns[returns > 0]
    losses = returns[returns < 0]
    
    avg_gain = float(gains.mean()) if len(gains) > 0 else 0
    avg_loss = float(abs(losses.mean())) if len(losses) > 0 else 0
    gain_loss_ratio = avg_gain / avg_loss if avg_loss > 0 else 0
    
    total_gains = gains.sum() if len(gains) > 0 else 0
    total_losses = abs(losses.sum()) if len(losses) > 0 else 0
    profit_factor = float(total_gains / total_losses) if total_losses > 0 else 0
    
    return {
        # Performance
        "total_roi": total_roi,
        "cagr": cagr,
        "volatility": volatility,
        
        # Risk-adjusted
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        
        # Drawdown
        "max_drawdown": max_dd,
        "max_dd_peak": peak_date,
        "max_dd_trough": trough_date,
        "avg_drawdown": avg_dd,
        "current_drawdown": current_dd,
        
        # VaR/CVaR
        "var_95_daily": var_daily,
        "cvar_95_daily": cvar_daily,
        "var_95_annual": var_annual,
        "cvar_95_annual": cvar_annual,
        
        # Monthly
        "months_up": months_up,
        "months_down": months_down,
        "months_total": months_total,
        "win_rate_monthly": months_up / months_total if months_total > 0 else 0,
        "best_month": float(monthly_ret.max()) if len(monthly_ret) > 0 else 0,
        "worst_month": float(monthly_ret.min()) if len(monthly_ret) > 0 else 0,
        "avg_month": float(monthly_ret.mean()) if len(monthly_ret) > 0 else 0,
        
        # Yearly
        "years_up": years_up,
        "years_down": years_down,
        "years_total": years_total,
        "best_year": float(yearly_ret.max()) if len(yearly_ret) > 0 else 0,
        "worst_year": float(yearly_ret.min()) if len(yearly_ret) > 0 else 0,
        
        # Daily
        "days_up": days_up,
        "days_down": days_down,
        "days_total": days_total,
        "best_day": float(returns.max()),
        "worst_day": float(returns.min()),
        
        # Ratios
        "gain_loss_ratio": gain_loss_ratio,
        "profit_factor": profit_factor,
    }
