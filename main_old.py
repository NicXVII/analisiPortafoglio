"""
Portfolio Analysis Tool v2.1
============================
Versione corretta con metodologie quantitative professionali.

Correzioni rispetto a v1:
1. CAGR calcolato correttamente dall'equity (non dalla media dei log-returns)
2. Aggregazione portafoglio con SIMPLE returns (non log returns)
3. Sortino Ratio con Target Downside Deviation corretta
4. Aggiunta VaR e CVaR (Expected Shortfall)
5. Fix warning deprecation pandas/numpy
6. Aggiunta rolling metrics
7. Risk contribution che somma a 100%

Nuovo in v2.1:
8. Export dati in CSV, Excel, JSON
9. Export grafici in PNG/PDF
10. Report HTML completo
11. Configurazione esterna in config.py
"""

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime, timedelta
from scipy import stats
import warnings
import json
import os
import zipfile
import shutil
from pathlib import Path
warnings.filterwarnings('ignore', category=FutureWarning)

# Importa configurazione da file esterno
from config import get_config


# =========================
# CORE FUNCTIONS - CORRECTED
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


def calculate_cagr_correct(equity: pd.Series, periods_per_year: int = 252) -> float:
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


def calculate_calmar_ratio(cagr: float, max_dd: float) -> float:
    """Calmar Ratio = CAGR / |Max Drawdown|"""
    if max_dd == 0:
        return 0.0
    return float(cagr / abs(max_dd))


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


def calculate_risk_contribution_correct(
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


# =========================
# PORTFOLIO SIMULATION - CORRECTED
# =========================

def simulate_portfolio_correct(
    prices: pd.DataFrame,
    weights: np.ndarray,
    rebalance_freq: Optional[str] = None
) -> Tuple[pd.Series, pd.Series]:
    """
    Simula portafoglio con SIMPLE returns (matematicamente corretto).
    
    Args:
        prices: DataFrame prezzi
        weights: array pesi
        rebalance_freq: None=buy&hold, "ME"=mensile, "QE"=trimestrale
    
    Returns:
        (equity_series, returns_series)
    """
    simple_ret = calculate_simple_returns(prices)
    
    if rebalance_freq is None:
        # Buy & Hold: pesi fissi sui rendimenti semplici
        port_ret = (simple_ret * weights).sum(axis=1)
    else:
        # Con ribilanciamento
        port_ret = _simulate_rebalanced_correct(simple_ret, weights, rebalance_freq)
    
    # Costruisci equity da simple returns
    equity = (1 + port_ret).cumprod()
    
    return equity, port_ret


def _simulate_rebalanced_correct(
    simple_ret: pd.DataFrame,
    weights: np.ndarray,
    rebalance_freq: str
) -> pd.Series:
    """
    Simulazione ribilanciamento corretta con simple returns.
    """
    # Raggruppa per periodo di ribilanciamento
    periods = simple_ret.resample(rebalance_freq)
    
    port_returns = []
    
    for period_end, period_data in periods:
        if period_data.empty:
            continue
        
        # All'interno del periodo, i pesi restano fissi
        # Simple returns sono additivi per portfolio pesati
        period_port_ret = (period_data * weights).sum(axis=1)
        port_returns.append(period_port_ret)
    
    if not port_returns:
        return pd.Series(dtype=float)
    
    return pd.concat(port_returns)


# =========================
# ADVANCED METRICS
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
    cagr = calculate_cagr_correct(equity, periods)
    volatility = calculate_annualized_volatility(returns, periods)
    
    # Risk-adjusted
    sharpe = calculate_sharpe_ratio(returns, risk_free, periods)
    sortino = calculate_sortino_ratio(returns, risk_free, 0.0, periods)
    
    # Drawdown
    max_dd, peak_date, trough_date = calculate_max_drawdown(equity)
    calmar = calculate_calmar_ratio(cagr, max_dd)
    
    dd_series = equity / equity.cummax() - 1
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


# =========================
# PORTFOLIO TYPE ANALYSIS (Quant Analyst) - 8 PORTFOLIO TYPES
# =========================

# ================================================================================
# SISTEMA DI IDENTIFICAZIONE TIPO PORTAFOGLIO
# ================================================================================
# 10 TIPI DI PORTAFOGLIO RICONOSCIUTI:
# 1. EQUITY_GROWTH_CORE       - 100% equity, singolo asset >45%, beta concentrato
# 2. EQUITY_GROWTH_DIVERSIFIED- 100% equity, multi-core regionale, nessun >45%
# 3. EQUITY_MULTI_BLOCK       - 100% equity, pesi equilibrati, diversificazione intra-equity
# 4. EQUITY_CORE_DRIVEN       - World index >50% + satellite (es. VWCE 73%)
# 5. BALANCED                 - Multi-asset 60/40 - 70/30, bond significativi
# 6. DEFENSIVE                - Capital preservation, <40% equity, gold/bond
# 7. INCOME_YIELD             - Focus dividendi/cedole (ETF income)
# 8. BARBELL_THEMATIC         - Core + >25% satellite tematici
# 9. RISK_PARITY              - VERO risk parity: multi-asset con bond, pesi per rischio
# 10. TACTICAL                - Allocazione tattica, nessun pattern chiaro
# ================================================================================

# === CATEGORIE ETF PER CLASSIFICAZIONE (tassonomia granulare v2) ===
# 
# STRUTTURA CORRETTA:
# 1. Core Geografico: blocchi regionali strutturali
# 2. Fattoriale/Asset Class: small cap, REIT, value, momentum
# 3. Settoriale: biotech, healthcare, financials (non tematico)
# 4. Tematico Puro: trend specifici ad alto beta (uranio, AI, clean energy)
#

# === 1. CORE GEOGRAFICO ===
# Core Globale: All-World diversificati
CORE_GLOBAL_ETF = ['VWCE', 'IWDA', 'SWDA', 'VT', 'ACWI', 'URTH', 'MSCI', 'FTSE', 'ALLWORLD']

# Core Developed: USA, Europa, Japan, UK (blocchi geografici strutturali)
CORE_DEVELOPED_ETF = ['CSPX', 'SXR8', 'VOO', 'SPY', 'IVV', 'QQQ',   # USA Large
                      'EZU', 'VGK', 'IEUR', 'EXSA', 'MEUD',          # Europa
                      'EWJ', 'IJPN', 'SJPA',                          # Japan
                      'EWU', 'ISF', 'VUKE',                           # UK
                      'EWC', 'EWA', 'EWS',                            # Canada, Australia, Singapore
                      'EWT', 'EWY', 'EWH']                            # Taiwan, Korea, HK (DM Asia)

# Core Emerging Broad: EM diversificati (NON single-country)
EMERGING_BROAD_ETF = ['EIMI', 'EEM', 'VWO', 'IS3N', 'IEEM', 'AEEM', 'EMIM']

# === 2. FATTORIALE / ASSET CLASS (strutturali, NON satellite) ===
# Small Cap: fattore size, strutturale
SMALL_CAP_ETF = ['IUSN', 'VB', 'IJR', 'WSML', 'ZPRX', 'IWM', 'SCHA', 'VBR', 'VIOO']

# Real Estate / REIT: asset class distinta
REIT_ETF = ['VNQ', 'VNQI', 'IYR', 'SCHH', 'RWR', 'REET', 'XLRE', 'USRT', 'REM']

# Factor ETF: value, momentum, quality, min vol (strutturali)
FACTOR_ETF = ['VLUE', 'VTV', 'IWD', 'MTUM', 'QUAL', 'USMV', 'SPLV', 'EFAV',
              'ACWV', 'VFMF', 'GVAL', 'IVAL', 'FNDX', 'PRF']

# === 3. SETTORIALE (non tematico, cicli economici) ===
# Settori ciclici e difensivi tradizionali
SECTOR_ETF = ['XLF', 'XLV', 'XLI', 'XLP', 'XLU', 'XLC', 'XLB', 'XLY',  # SPDR Settori
              'IBB', 'XBI', 'IHI', 'IHF',                               # Healthcare/Biotech
              'ITA', 'PPA',                                              # Defense/Aerospace
              'XLE', 'XOP', 'OIH', 'VDE',                                # Energy tradizionale
              'KBE', 'KRE', 'IAI']                                       # Financials

# === 4. TEMATICO PURO (high beta, trend specifici) ===
# Questi sono i veri "satellite" speculativi
THEMATIC_PURE_ETF = ['URA', 'URNM', 'NUKL',                        # Uranio/Nucleare
                     'SRVR', 'SKYY', 'WCLD', 'CLOU',               # Cloud/Data Center
                     'ARKK', 'ARKG', 'ARKQ', 'ARKW', 'ARKF',       # ARK Innovation
                     'SOXX', 'SMH', 'SEMI', 'PSI',                 # Semiconduttori
                     'HACK', 'CIBR', 'CYBR', 'BUG',                # Cybersecurity
                     'ICLN', 'TAN', 'QCLN', 'PBW', 'FAN',          # Clean Energy
                     'BATT', 'LIT', 'DRIV', 'IDRV', 'KARS',        # EV/Batterie
                     'ROBO', 'BOTZ', 'IRBO', 'AIQ', 'CHAT',        # Robotics/AI
                     'MOON', 'HERO', 'ESPO', 'NERD', 'GAMR',       # Space/Gaming
                     'IBIT', 'BITO', 'GBTC', 'ETHE',               # Crypto
                     'MSTR', 'COIN', 'RING', 'GDXJ',               # Crypto-proxy/Gold miners
                     'ARKG', 'GNOM', 'XBI']                        # Genomics/Biotech speculativo

# === 5. SINGLE-COUNTRY EM (tilt geografico, rischio concentrato) ===
EM_SINGLE_COUNTRY_ETF = ['INDA', 'INDY', 'SMIN', 'NDIA',   # India
                         'EWZ', 'FLBR', 'BRF',              # Brasile
                         'MCHI', 'FXI', 'KWEB', 'ASHR',     # Cina
                         'EWW', 'FLMX',                     # Messico
                         'TUR', 'EZA', 'EPOL', 'ERUS']      # Altri single-country

# === 6. BOND, GOLD, DEFENSIVE ===
BOND_ETF = ['AGGH', 'BND', 'AGG', 'GOVT', 'TLT', 'IEF', 'LQD', 'HYG', 'IEAG', 'IBTA', 
            'VGOV', 'STHY', 'TIP', 'TIPS', 'IGLT', 'CORP', 'IBCI', 'VAGF', 'VAGS', 
            'VUTY', 'VGEA', 'VECP', 'VEMT', 'VGEB', 'VCSH', 'VCIT', 'VCLT',
            'STHE', 'DTLA', 'GOVE', 'IEGA', 'GIST', 'SEGA', 'XGLE', 'UEEF',
            'SHY', 'IEI', 'VGSH', 'VGIT', 'VGLT', 'EDV', 'ZROZ']

GOLD_COMMODITY_ETF = ['GLD', 'GOLD', 'IAU', 'SGOL', 'GLDM', 'PHAU', 'SGLD',
                      'DBC', 'PDBC', 'GSG', 'COMT', 'COPX', 'REMX', 'CMOD',
                      'SLV', 'PPLT', 'PALL', 'USO', 'UNG', 'WEAT', 'CORN']

DIVIDEND_INCOME_ETF = ['VIG', 'SCHD', 'VIGI', 'NOBL', 'SPHD', 'HDV', 'DVY', 'VHYL', 'IUKD',
                       'SPYD', 'JEPI', 'JEPQ', 'DIVO', 'IEDY', 'IDVY', 'VYMI', 'SDIV', 
                       'FDVV', 'VYM', 'DGRO', 'DIV', 'DIVD', 'QDIV', 'TDIV']

DEFENSIVE_ETF = ['USMV', 'SPLV', 'EFAV', 'ACWV', 'XMLV', 'XSLV', 'LVHD'] + GOLD_COMMODITY_ETF

# === ALIAS PER BACKWARD COMPATIBILITY ===
CORE_REGIONAL_ETF = CORE_DEVELOPED_ETF
EMERGING_ETF = EMERGING_BROAD_ETF
# SATELLITE ora include solo tematici puri + single-country EM
SATELLITE_KEYWORDS = THEMATIC_PURE_ETF + EM_SINGLE_COUNTRY_ETF
# NON-CORE STRUTTURALE (fattoriali + settoriali + REIT) - NON sono satellite
NON_CORE_STRUCTURAL_ETF = SMALL_CAP_ETF + REIT_ETF + FACTOR_ETF + SECTOR_ETF


# ================================================================================
# GEOGRAPHIC EXPOSURE MAPPING (esposizione geografica implicita)
# ================================================================================
# Ogni ETF ha un breakdown geografico approssimativo
# Fonte: factsheet ufficiali, dati medi storici

GEO_EXPOSURE = {
    # === GLOBAL ===
    "VT": {"USA": 0.60, "Europe": 0.15, "Japan": 0.06, "EM": 0.12, "Other_DM": 0.07},
    "VWCE": {"USA": 0.60, "Europe": 0.15, "Japan": 0.06, "EM": 0.12, "Other_DM": 0.07},
    "IWDA": {"USA": 0.68, "Europe": 0.18, "Japan": 0.07, "EM": 0.0, "Other_DM": 0.07},
    "ACWI": {"USA": 0.62, "Europe": 0.14, "Japan": 0.05, "EM": 0.12, "Other_DM": 0.07},
    
    # === USA ===
    "IVV": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "SPY": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "VOO": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "QQQ": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "IWM": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "VNQ": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "IBB": {"USA": 0.90, "Europe": 0.05, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.05},
    
    # === EUROPA ===
    "VGK": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "EXSA": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "EZU": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "EWU": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "IEUR": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    
    # === JAPAN / ASIA DM ===
    "EWJ": {"USA": 0.0, "Europe": 0.0, "Japan": 1.0, "EM": 0.0, "Other_DM": 0.0},
    "VPL": {"USA": 0.0, "Europe": 0.0, "Japan": 0.65, "EM": 0.0, "Other_DM": 0.35},
    "EWT": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 1.0},  # Taiwan = DM per MSCI
    "EWY": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 1.0},  # Korea
    
    # === EMERGING MARKETS ===
    "EEM": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},
    "VWO": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},
    "INDA": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},  # India
    "MCHI": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},  # Cina
    "EWZ": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},   # Brasile
    
    # === SMALL CAP ===
    "IUSN": {"USA": 0.60, "Europe": 0.20, "Japan": 0.10, "EM": 0.0, "Other_DM": 0.10},
    
    # === TEMATICI (prevalentemente USA) ===
    "ARKK": {"USA": 0.85, "Europe": 0.05, "Japan": 0.0, "EM": 0.05, "Other_DM": 0.05},
    "ARKQ": {"USA": 0.80, "Europe": 0.05, "Japan": 0.05, "EM": 0.05, "Other_DM": 0.05},
    "URA": {"USA": 0.40, "Europe": 0.10, "Japan": 0.05, "EM": 0.0, "Other_DM": 0.45},  # Canada, Australia
    "SRVR": {"USA": 0.85, "Europe": 0.05, "Japan": 0.05, "EM": 0.0, "Other_DM": 0.05},
    "SOXX": {"USA": 0.85, "Europe": 0.05, "Japan": 0.0, "EM": 0.05, "Other_DM": 0.05},
    
    # === SETTORIALI USA ===
    "XLE": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "XLF": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "XLV": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "ITA": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
}

# Default per ETF non mappati (assumption conservativa)
DEFAULT_GEO = {"USA": 0.60, "Europe": 0.15, "Japan": 0.05, "EM": 0.10, "Other_DM": 0.10}


# ================================================================================
# ASSET FUNCTION CLASSIFICATION (funzione economica)
# ================================================================================
ASSET_FUNCTION = {
    # Core Growth: driver principale di rendimento, diversificato
    "CORE_GROWTH": ["VT", "VWCE", "IWDA", "ACWI", "IVV", "SPY", "VOO", "QQQ"],
    
    # Regional Diversification: esposizione geografica specifica
    "REGIONAL_DIVERSIFICATION": ["VGK", "EZU", "EXSA", "EWJ", "EWU", "VPL", "EWT", "EWY"],
    
    # EM Exposure: crescita EM, rischio geopolitico
    "EM_EXPOSURE": ["EEM", "VWO", "INDA", "MCHI", "EWZ", "EIMI"],
    
    # Factor Tilt: esposizione fattoriale (size, value, momentum)
    "FACTOR_TILT": ["IUSN", "IWM", "VB", "MTUM", "QUAL", "VLUE", "VTV"],
    
    # Real Assets: REIT, infrastrutture, commodity equity
    "REAL_ASSETS": ["VNQ", "VNQI", "XLRE", "SRVR"],
    
    # Cyclical Hedge: settori ciclici, energy, materials
    "CYCLICAL_HEDGE": ["XLE", "XLF", "XLB", "XLI", "ITA"],
    
    # Defensive: healthcare, utilities, consumer staples
    "DEFENSIVE_SECTOR": ["XLV", "XLU", "XLP", "IBB"],
    
    # Thematic Alpha: scommesse tematiche ad alto beta
    "THEMATIC_ALPHA": ["ARKK", "ARKQ", "ARKG", "URA", "SOXX", "ICLN", "TAN", "LIT"],
    
    # Income: dividend, covered call
    "INCOME": ["VIG", "SCHD", "JEPI", "JEPQ", "VYM", "HDV"],
    
    # Tail Hedge: oro, volatilità, bond lunghi
    "TAIL_HEDGE": ["GLD", "TLT", "GOVT", "BND"],
}


def get_asset_function(ticker: str) -> str:
    """Determina la funzione economica di un asset."""
    ticker_clean = ticker.upper().split('.')[0]
    for function, tickers_list in ASSET_FUNCTION.items():
        if ticker_clean in tickers_list:
            return function
    # Default basato su categorie
    if ticker_clean in THEMATIC_PURE_ETF or any(kw in ticker_clean for kw in THEMATIC_PURE_ETF):
        return "THEMATIC_ALPHA"
    if ticker_clean in REIT_ETF or any(kw in ticker_clean for kw in REIT_ETF):
        return "REAL_ASSETS"
    if ticker_clean in SECTOR_ETF or any(kw in ticker_clean for kw in SECTOR_ETF):
        return "CYCLICAL_HEDGE"
    if ticker_clean in SMALL_CAP_ETF or any(kw in ticker_clean for kw in SMALL_CAP_ETF):
        return "FACTOR_TILT"
    if ticker_clean in EMERGING_BROAD_ETF or any(kw in ticker_clean for kw in EMERGING_BROAD_ETF):
        return "EM_EXPOSURE"
    if ticker_clean in CORE_DEVELOPED_ETF or any(kw in ticker_clean for kw in CORE_DEVELOPED_ETF):
        return "REGIONAL_DIVERSIFICATION"
    return "CORE_GROWTH"  # Default


def calculate_geographic_exposure(tickers: list, weights: np.ndarray) -> Dict[str, float]:
    """
    Calcola l'esposizione geografica REALE del portafoglio,
    considerando la composizione interna di ogni ETF.
    """
    geo_totals = {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0}
    
    for i, ticker in enumerate(tickers):
        ticker_clean = ticker.upper().split('.')[0]
        weight = weights[i]
        
        # Cerca mapping esatto o parziale
        geo_map = None
        if ticker_clean in GEO_EXPOSURE:
            geo_map = GEO_EXPOSURE[ticker_clean]
        else:
            # Cerca match parziale
            for key in GEO_EXPOSURE:
                if key in ticker_clean or ticker_clean in key:
                    geo_map = GEO_EXPOSURE[key]
                    break
        
        if geo_map is None:
            geo_map = DEFAULT_GEO
        
        for region, pct in geo_map.items():
            geo_totals[region] += weight * pct
    
    return geo_totals


def analyze_function_exposure(tickers: list, weights: np.ndarray) -> Dict[str, float]:
    """
    Analizza l'esposizione per FUNZIONE ECONOMICA.
    """
    function_totals = {}
    for i, ticker in enumerate(tickers):
        func = get_asset_function(ticker)
        function_totals[func] = function_totals.get(func, 0) + weights[i]
    return function_totals


def detect_false_diversification(
    tickers: list, 
    weights: np.ndarray,
    geo_exposure: Dict[str, float],
    corr: pd.DataFrame
) -> List[Dict]:
    """
    Rileva FALSE DIVERSIFICAZIONI:
    - Concentrazione geografica mascherata
    - Doppie esposizioni
    - Correlazioni elevate tra "diversificatori"
    """
    warnings = []
    
    # 1. Concentrazione USA mascherata (>70% effettivo)
    if geo_exposure.get("USA", 0) > 0.70:
        warnings.append({
            "type": "HIDDEN_USA_CONCENTRATION",
            "severity": "structural",
            "message": f"Esposizione USA effettiva {geo_exposure['USA']:.0%}. "
                      f"Diversificazione geografica apparente ma concentrazione reale su mercato USA."
        })
    
    # 2. EM sottopesato rispetto a global market cap (~12%)
    if geo_exposure.get("EM", 0) < 0.08 and geo_exposure.get("USA", 0) > 0.50:
        warnings.append({
            "type": "EM_UNDERWEIGHT",
            "severity": "informational",
            "message": f"EM al {geo_exposure['EM']:.0%} vs ~12% del mercato globale. "
                      f"Bias home/USA consapevole o sottodiversificazione?"
        })
    
    # 3. Overlap World + Regional
    world_tickers = [t for t in tickers if t.upper().split('.')[0] in CORE_GLOBAL_ETF]
    regional_tickers = [t for t in tickers if t.upper().split('.')[0] in CORE_DEVELOPED_ETF]
    
    if world_tickers and regional_tickers:
        world_weight = sum(weights[tickers.index(t)] for t in world_tickers)
        regional_weight = sum(weights[tickers.index(t)] for t in regional_tickers)
        if world_weight > 0.30 and regional_weight > 0.20:
            warnings.append({
                "type": "WORLD_REGIONAL_OVERLAP",
                "severity": "structural",
                "message": f"World ETF ({world_weight:.0%}) + Regional ({regional_weight:.0%}) = overlap significativo. "
                          f"Valutare se ridondanza intenzionale o inefficienza."
            })
    
    # 4. Correlazione media troppo alta (>0.80)
    if corr is not None and len(corr) > 2:
        # Calcola correlazione media escludendo diagonale
        corr_values = corr.values[np.triu_indices(len(corr), k=1)]
        avg_corr = np.mean(corr_values)
        if avg_corr > 0.80:
            warnings.append({
                "type": "HIGH_AVERAGE_CORRELATION",
                "severity": "structural",
                "message": f"Correlazione media {avg_corr:.2f}. "
                          f"Diversificazione limitata in scenari di stress."
            })
        elif avg_corr > 0.70:
            warnings.append({
                "type": "MODERATE_CORRELATION",
                "severity": "informational",
                "message": f"Correlazione media {avg_corr:.2f}. "
                          f"Normale per portafoglio equity-only, monitorare in stress."
            })
    
    return warnings


def identify_structural_strengths(
    composition: Dict,
    geo_exposure: Dict[str, float],
    function_exposure: Dict[str, float],
    metrics: Dict,
    weights: np.ndarray = None
) -> List[str]:
    """
    Identifica i PUNTI DI FORZA STRUTTURALI del portafoglio.
    """
    strengths = []
    
    # 1. Diversificazione geografica bilanciata
    usa_pct = geo_exposure.get("USA", 0)
    if 0.40 <= usa_pct <= 0.65:
        strengths.append(f"Esposizione USA bilanciata ({usa_pct:.0%}), non eccessivamente concentrato né sottopesato")
    
    # 2. Presenza EM significativa
    em_pct = geo_exposure.get("EM", 0)
    if em_pct >= 0.10:
        strengths.append(f"Esposizione EM adeguata ({em_pct:.0%}) per catturare crescita mercati emergenti")
    
    # 3. Mix funzionale diversificato
    n_functions = len([f for f, w in function_exposure.items() if w > 0.05])
    if n_functions >= 4:
        strengths.append(f"{n_functions} funzioni economiche distinte → portafoglio multi-driver")
    
    # 4. Nessuna posizione dominante (usa weights se disponibile)
    if weights is not None and len(weights) > 0:
        max_pos = float(max(weights))
    else:
        max_pos = composition.get("details", {}).get("max_position", 0)
    if max_pos > 0 and max_pos < 0.25:
        strengths.append(f"Nessuna posizione dominante (max {max_pos:.0%}) → rischio idiosincratico contenuto")
    
    # 5. Real assets per inflation hedge
    real_assets = function_exposure.get("REAL_ASSETS", 0)
    if real_assets >= 0.05:
        strengths.append(f"Presenza real assets ({real_assets:.0%}) per diversificazione e inflation hedge")
    
    # 6. Factor tilt consapevole
    factor_tilt = function_exposure.get("FACTOR_TILT", 0)
    if factor_tilt >= 0.08:
        strengths.append(f"Factor tilt ({factor_tilt:.0%}) per catturare premi fattoriali (size/value/momentum)")
    
    # 7. Sortino buono (downside protection)
    sortino = metrics.get("sortino", 0)
    if sortino > 0.70:
        strengths.append(f"Sortino Ratio {sortino:.2f} → gestione efficiente del downside risk")
    
    # 8. CAGR competitivo
    cagr = metrics.get("cagr", 0)
    if cagr > 0.08:
        strengths.append(f"CAGR {cagr:.1%} → rendimento composto competitivo nel lungo periodo")
    
    return strengths


def generate_verdict_bullets(
    portfolio_type: str,
    strengths: List[str],
    issues: List[Dict],
    metrics: Dict,
    composition: Dict
) -> List[str]:
    """
    Genera i bullet point motivazionali per il verdetto finale.
    Stile Vanguard: professionale, diretto, focalizzato sulla struttura.
    """
    bullets = []
    
    # Conta issue per severità
    critical_issues = [i for i in issues if i.get("severity") == "🚨"]
    structural_issues = [i for i in issues if i.get("severity") in ["⚠️", "structural"]]
    info_issues = [i for i in issues if i.get("severity") in ["ℹ️", "informational"]]
    
    # Bullet 1: Tipo e coerenza strutturale
    bullets.append(f"Portafoglio classificato come {portfolio_type} con struttura coerente rispetto agli obiettivi impliciti")
    
    # Bullet 2: Punto di forza principale
    if strengths:
        bullets.append(strengths[0])
    
    # Bullet 3: Trade-off principale (se presente)
    if structural_issues:
        bullets.append(f"Trade-off identificato: {structural_issues[0].get('message', '')[:100]}...")
    elif len(strengths) > 1:
        bullets.append(strengths[1])
    
    # Bullet 4: Metriche chiave
    cagr = metrics.get("cagr", 0)
    sortino = metrics.get("sortino", 0)
    max_dd = metrics.get("max_drawdown", 0)
    bullets.append(f"Metriche di lungo periodo: CAGR {cagr:.1%}, Sortino {sortino:.2f}, Max DD {max_dd:.0%}")
    
    # Bullet 5: Conclusione
    if critical_issues:
        bullets.append("Criticità strutturali richiedono revisione prima di implementazione")
    elif structural_issues:
        bullets.append("Costruzione solida con trade-off consapevoli e documentati")
    else:
        bullets.append("Struttura robusta per orizzonti multi-decennali")
    
    return bullets[:5]  # Max 5 bullet


def detect_portfolio_type(
    weights: np.ndarray,
    tickers: list,
    asset_metrics: pd.DataFrame
) -> Dict[str, Any]:
    """
    IDENTIFICAZIONE TIPO PORTAFOGLIO - 8 TIPI
    
    Analizza composizione e assegna tipo con regole specifiche.
    
    Tipi (in ordine di priorità nel check):
    1. INCOME_YIELD             - Dividend ETF >40% o income focus
    2. DEFENSIVE                - Equity <40%, bond+gold >40%
    3. BALANCED                 - Bond 20-50%, equity 50-80%
    4. RISK_PARITY              - Max position <25%, ben distribuito
    5. EQUITY_CORE_DRIVEN       - World index >50%, bond <15%
    6. BARBELL_THEMATIC         - Core >40% + satellite >20%
    7. EQUITY_GROWTH_CORE       - 100% equity, singolo asset >45%
    8. EQUITY_GROWTH_DIVERSIFIED- 100% equity, multi-core, nessun >45%
    9. TACTICAL                 - Default, nessun pattern
    
    Returns:
        Dict con tipo, confidence, thresholds, composition
    """
    # === STEP 1: CLASSIFICA OGNI ASSET ===
    core_global_weight = 0.0
    core_regional_weight = 0.0
    emerging_weight = 0.0
    bond_weight = 0.0
    gold_commodity_weight = 0.0
    dividend_income_weight = 0.0
    defensive_weight = 0.0
    satellite_weight = 0.0
    
    # === NUOVA TASSONOMIA GRANULARE ===
    small_cap_weight = 0.0
    reit_weight = 0.0
    factor_weight = 0.0
    sector_weight = 0.0
    thematic_pure_weight = 0.0
    em_single_country_weight = 0.0
    
    core_global_tickers = []
    core_regional_tickers = []
    satellite_tickers = []
    bond_tickers = []
    income_tickers = []
    structural_noncore_tickers = []  # Small cap, REIT, settori
    thematic_pure_tickers = []
    
    for i, t in enumerate(tickers):
        ticker_upper = t.upper()
        # Rimuovi suffisso borsa per matching (es. ".DE", ".L")
        ticker_clean = ticker_upper.split('.')[0]
        w = weights[i]
        
        # Priority check (in order di specificità)
        # 1. Bond
        if any(kw in ticker_upper for kw in BOND_ETF) or any(kw == ticker_clean for kw in BOND_ETF):
            bond_weight += w
            bond_tickers.append(t)
        # 2. Gold/Commodity
        elif any(kw in ticker_upper for kw in GOLD_COMMODITY_ETF) or any(kw == ticker_clean for kw in GOLD_COMMODITY_ETF):
            gold_commodity_weight += w
            defensive_weight += w
        # 3. Dividend/Income ETF
        elif any(kw in ticker_upper for kw in DIVIDEND_INCOME_ETF) or any(kw == ticker_clean for kw in DIVIDEND_INCOME_ETF):
            dividend_income_weight += w
            income_tickers.append(t)
        # 4. Core Globale (VWCE, IWDA...)
        elif any(kw in ticker_upper for kw in CORE_GLOBAL_ETF) or any(kw == ticker_clean for kw in CORE_GLOBAL_ETF):
            core_global_weight += w
            core_global_tickers.append(t)
        # 5. TEMATICO PURO (prima dei settoriali per evitare conflitti)
        elif any(kw in ticker_upper for kw in THEMATIC_PURE_ETF) or any(kw == ticker_clean for kw in THEMATIC_PURE_ETF):
            thematic_pure_weight += w
            satellite_weight += w  # Tematici puri = veri satellite
            thematic_pure_tickers.append(t)
        # 6. Small Cap (strutturale, NON satellite)
        elif any(kw in ticker_upper for kw in SMALL_CAP_ETF) or any(kw == ticker_clean for kw in SMALL_CAP_ETF):
            small_cap_weight += w
            core_regional_weight += w  # Conta come core (fattoriale strutturale)
            structural_noncore_tickers.append(t)
        # 7. REIT (asset class, NON satellite)
        elif any(kw in ticker_upper for kw in REIT_ETF) or any(kw == ticker_clean for kw in REIT_ETF):
            reit_weight += w
            # REIT è asset class separata, non equity core ma neanche satellite
            structural_noncore_tickers.append(t)
        # 8. Factor ETF (strutturale)
        elif any(kw in ticker_upper for kw in FACTOR_ETF) or any(kw == ticker_clean for kw in FACTOR_ETF):
            factor_weight += w
            core_regional_weight += w
            structural_noncore_tickers.append(t)
        # 9. Settoriale (ciclico, NON satellite tematico)
        elif any(kw in ticker_upper for kw in SECTOR_ETF) or any(kw == ticker_clean for kw in SECTOR_ETF):
            sector_weight += w
            structural_noncore_tickers.append(t)
        # 10. Single-Country EM (tilt geografico, rischio medio)
        elif any(kw in ticker_upper for kw in EM_SINGLE_COUNTRY_ETF) or any(kw == ticker_clean for kw in EM_SINGLE_COUNTRY_ETF):
            em_single_country_weight += w
            emerging_weight += w
            core_regional_tickers.append(t)
        # 11. Emerging Markets Broad
        elif any(kw in ticker_upper for kw in EMERGING_ETF) or any(kw == ticker_clean for kw in EMERGING_ETF):
            emerging_weight += w
            core_regional_weight += w
            core_regional_tickers.append(t)
        # 12. Core Regionale Developed
        elif any(kw in ticker_upper for kw in CORE_REGIONAL_ETF) or any(kw == ticker_clean for kw in CORE_REGIONAL_ETF):
            core_regional_weight += w
            core_regional_tickers.append(t)
        # 13. Defensive ETF
        elif any(kw in ticker_upper for kw in DEFENSIVE_ETF) or any(kw == ticker_clean for kw in DEFENSIVE_ETF):
            defensive_weight += w
        # 14. Default: classifica per volatilità
        else:
            if t in asset_metrics.index:
                vol = asset_metrics.loc[t, 'Vol'] if 'Vol' in asset_metrics.columns else 0
                if vol > 0.35:  # Molto alta volatilità = tematico speculativo
                    thematic_pure_weight += w
                    satellite_weight += w
                    thematic_pure_tickers.append(t)
                elif vol > 0.25:  # Alta volatilità = settoriale
                    sector_weight += w
                    structural_noncore_tickers.append(t)
                elif vol < 0.12:  # Bassa volatilità = defensive
                    defensive_weight += w
                else:
                    core_regional_weight += w  # Default a core
                    core_regional_tickers.append(t)
            else:
                # Sconosciuto → conservativamente core
                core_regional_weight += w
                core_regional_tickers.append(t)
    
    # === CALCOLI AGGREGATI (nuova tassonomia) ===
    # Structural non-core = small cap + REIT + factor + sector (NON satellite!)
    structural_noncore_weight = small_cap_weight + reit_weight + factor_weight + sector_weight
    # Vero satellite = solo tematici puri
    true_satellite_weight = thematic_pure_weight
    
    total_equity = core_global_weight + core_regional_weight + structural_noncore_weight + true_satellite_weight + dividend_income_weight
    total_core = core_global_weight + core_regional_weight
    total_defensive_assets = bond_weight + gold_commodity_weight + defensive_weight
    max_weight = weights.max()
    max_ticker = tickers[weights.argmax()]
    n_positions = len(weights[weights > 0.01])  # Posizioni >1%
    
    # === STEP 2: IDENTIFICA TIPO ===
    portfolio_type = "TACTICAL"
    confidence = 0.50
    type_reason = "Nessun pattern chiaro identificato"
    
    # === TIPO 1: INCOME_YIELD ===
    # Criteri: Dividend ETF >40% OPPURE income ETF >30% con bond
    if dividend_income_weight >= 0.40:
        portfolio_type = "INCOME_YIELD"
        confidence = min(0.95, 0.6 + dividend_income_weight)
        type_reason = f"Dividend/Income ETF {dividend_income_weight:.0%} dominante"
    elif dividend_income_weight >= 0.25 and bond_weight >= 0.15:
        portfolio_type = "INCOME_YIELD"
        confidence = 0.80
        type_reason = f"Income focus: dividendi {dividend_income_weight:.0%} + bond {bond_weight:.0%}"
    
    # === TIPO 2: DEFENSIVE ===
    # Criteri: Equity <40%, defensive assets (bond+gold) >40%
    elif total_equity < 0.40 and total_defensive_assets >= 0.40:
        portfolio_type = "DEFENSIVE"
        confidence = min(0.95, 0.5 + total_defensive_assets)
        type_reason = f"Capital preservation: equity {total_equity:.0%}, defensive {total_defensive_assets:.0%}"
    elif total_equity < 0.50 and bond_weight >= 0.35:
        portfolio_type = "DEFENSIVE"
        confidence = 0.85
        type_reason = f"Bond-heavy defensive: bond {bond_weight:.0%}, equity {total_equity:.0%}"
    
    # === TIPO 3: BALANCED ===
    # Criteri: Bond 20-50%, equity 50-80%
    elif 0.20 <= bond_weight <= 0.50 and 0.50 <= total_equity <= 0.80:
        portfolio_type = "BALANCED"
        confidence = 0.90
        type_reason = f"Multi-asset balanced: equity {total_equity:.0%}, bond {bond_weight:.0%}"
    elif 0.15 <= bond_weight < 0.20 and total_equity <= 0.75:
        portfolio_type = "BALANCED"
        confidence = 0.75
        type_reason = f"Quasi-balanced: equity {total_equity:.0%}, bond {bond_weight:.0%}"
    
    # === TIPO 4: RISK_PARITY (VERO) ===
    # CRITICO: Risk Parity classico RICHIEDE multi-asset (bond obbligatori)
    # Se equity >= 90% e bond == 0, NON è Risk Parity → usa EQUITY_MULTI_BLOCK
    elif max_weight < 0.25 and n_positions >= 5:
        # Check distribuzione
        weight_std = np.std(weights[weights > 0.01])
        avg_weight = np.mean(weights[weights > 0.01])
        cv = weight_std / avg_weight if avg_weight > 0 else 99
        
        if cv < 0.5:  # Coefficiente di variazione basso = ben distribuito
            # === REGOLA FONDAMENTALE ===
            # Risk Parity classico: DEVE avere bond >= 10% per bilanciare rischio
            if bond_weight >= 0.10 and total_equity < 0.85:
                # VERO Risk Parity: multi-asset con bond
                portfolio_type = "RISK_PARITY"
                confidence = min(0.90, 0.6 + (1 - cv))
                type_reason = f"Risk Parity multi-asset: equity {total_equity:.0%}, bond {bond_weight:.0%}, CV {cv:.2f}"
            else:
                # EQUITY_MULTI_BLOCK: intra-equity risk-balanced (NON risk parity)
                portfolio_type = "EQUITY_MULTI_BLOCK"
                confidence = min(0.90, 0.6 + (1 - cv))
                type_reason = f"Equity multi-block: {n_positions} posizioni equilibrate, max {max_weight:.0%}, CV {cv:.2f}"
    
    # === TIPO 5: EQUITY_CORE_DRIVEN ===
    # Criteri: World index >50%, bond <15%, satellite <25%
    elif core_global_weight >= 0.50 and bond_weight < 0.15:
        portfolio_type = "EQUITY_CORE_DRIVEN"
        confidence = min(0.95, 0.5 + core_global_weight)
        type_reason = f"Core globale dominante: {core_global_weight:.0%} in world index"
        
        # Boost confidence se core è un All-World ETF noto
        if any(kw in max_ticker.upper() for kw in ['VWCE', 'VT', 'IWDA', 'ACWI']):
            confidence = min(0.98, confidence + 0.05)
            type_reason += f" ({max_ticker} è All-World diversificato)"
    
    # === TIPO 6: BARBELL_THEMATIC ===
    # Criteri: Core >40% + satellite tematici >20%
    elif total_core >= 0.40 and satellite_weight >= 0.20:
        portfolio_type = "BARBELL_THEMATIC"
        confidence = 0.85
        type_reason = f"Barbell: core {total_core:.0%} + satellite tematici {satellite_weight:.0%}"
    elif total_core >= 0.50 and satellite_weight >= 0.15:
        portfolio_type = "BARBELL_THEMATIC"
        confidence = 0.80
        type_reason = f"Core-satellite: core {total_core:.0%}, tematici {satellite_weight:.0%}"
    
    # === TIPO 7-8: EQUITY_GROWTH (Core vs Diversified) ===
    # Criteri base: 100% equity, bond <5%
    # CORE: singolo asset >45% = beta concentrato su un singolo driver
    # DIVERSIFIED: multi-core regionale, nessun asset >45% = diversificazione reale
    elif total_equity >= 0.90 and bond_weight < 0.05:
        if max_weight > 0.45:
            # EQUITY_GROWTH_CORE: concentrato su singolo beta
            portfolio_type = "EQUITY_GROWTH_CORE"
            confidence = 0.85
            type_reason = f"Equity growth concentrato: {max_ticker} al {max_weight:.0%} (beta dominante)"
        else:
            # EQUITY_GROWTH_DIVERSIFIED: multi-core regionale
            n_regional_blocks = sum(1 for w in weights if w >= 0.07)  # Blocchi >=7%
            portfolio_type = "EQUITY_GROWTH_DIVERSIFIED"
            confidence = 0.85
            type_reason = f"Equity growth diversificato: {n_regional_blocks} blocchi regionali, max position {max_weight:.0%}"
    
    # === TIPO 9: TACTICAL (default) ===
    # Se nessun pattern chiaro
    else:
        portfolio_type = "TACTICAL"
        confidence = 0.50 + (0.1 * n_positions / 10)  # Più posizioni = meno tattico
        type_reason = "Pattern non classificabile, allocation tattica/opportunistica"
    
    # === STEP 3: GET THRESHOLDS PER TIPO ===
    thresholds = get_type_thresholds(portfolio_type)
    
    # === STEP 4: COMPONI RISULTATO (tassonomia granulare) ===
    return {
        "type": portfolio_type,
        "confidence": confidence,
        "reason": type_reason,
        "thresholds": thresholds,
        "composition": {
            # Core
            "core_global": core_global_weight,
            "core_regional": core_regional_weight,
            "emerging": emerging_weight,
            "total_core": total_core,
            # Strutturale non-core (NON satellite!)
            "small_cap": small_cap_weight,
            "reit": reit_weight,
            "factor": factor_weight,
            "sector": sector_weight,
            "structural_noncore": structural_noncore_weight,
            # Tematico puro (vero satellite)
            "thematic_pure": thematic_pure_weight,
            "em_single_country": em_single_country_weight,
            "true_satellite": true_satellite_weight,  # Solo tematici puri
            # Difensivi
            "bond": bond_weight,
            "gold_commodity": gold_commodity_weight,
            "dividend_income": dividend_income_weight,
            "defensive": defensive_weight,
            # Totali
            "satellite": satellite_weight,  # Legacy (include true_satellite)
            "total_equity": total_equity,
            "total_defensive": total_defensive_assets,
        },
        "details": {
            "core_tickers": core_global_tickers + core_regional_tickers,
            "structural_noncore_tickers": structural_noncore_tickers,
            "thematic_pure_tickers": thematic_pure_tickers,
            "satellite_tickers": satellite_tickers,  # Legacy
            "bond_tickers": bond_tickers,
            "income_tickers": income_tickers,
            "n_positions": n_positions,
            "max_position": max_weight,
            "max_ticker": max_ticker,
        }
    }


def get_type_thresholds(portfolio_type: str) -> Dict[str, Any]:
    """
    SOGLIE TYPE-SPECIFIC per validazione.
    
    Ogni tipo ha parametri diversi per:
    - Concentrazione (max single, top 3)
    - Satellite (singolo e totale)
    - Correlazioni
    - Drawdown atteso
    - Metriche risk-adjusted
    - Metriche primarie vs secondarie
    """
    
    # === DEFAULT (TACTICAL) ===
    default = {
        "max_single_position": 0.40,
        "max_top3": 0.70,
        "max_satellite_single": 0.08,
        "max_satellite_total": 0.20,
        "max_correlation_satellite": 0.65,
        "max_drawdown": -0.25,
        "min_sharpe": 0.50,
        "min_sortino": 0.70,
        "min_calmar": 0.30,
        "core_risk_contrib_ratio_max": 1.5,
        # Metriche primarie vs secondarie per tipo
        "primary_metrics": ["sharpe", "sortino", "max_drawdown"],
        "secondary_metrics": ["cagr", "calmar"],
        "description": "Allocation tattica - standard validation",
    }
    
    # === EQUITY_GROWTH_CORE (beta concentrato) ===
    if portfolio_type == "EQUITY_GROWTH_CORE":
        return {
            "max_single_position": 0.60,      # Concentrazione accettata (è il punto)
            "max_top3": 0.80,
            "max_satellite_single": 0.15,
            "max_satellite_total": 0.35,
            "max_correlation_satellite": 0.75,
            "max_drawdown": -0.45,            # Alta tolleranza (concentrato = volatile)
            "min_sharpe": 0.55,
            "min_sortino": 0.75,
            "min_calmar": 0.15,
            "core_risk_contrib_ratio_max": 2.0,  # Core può dominare il rischio
            "primary_metrics": ["cagr", "sortino"],  # Focus rendimento
            "secondary_metrics": ["sharpe", "max_drawdown"],
            "description": "Equity Growth Core - concentrazione su singolo beta driver",
        }
    
    # === EQUITY_GROWTH_DIVERSIFIED (multi-core regionale) ===
    if portfolio_type == "EQUITY_GROWTH_DIVERSIFIED":
        return {
            "max_single_position": 0.45,      # Nessun singolo dominante
            "max_top3": 0.70,
            "max_satellite_single": 0.15,     # Satellite growth possono essere grandi
            "max_satellite_total": 0.40,
            "max_correlation_satellite": 0.75,
            "max_drawdown": -0.40,            # Leggermente migliore (diversificato)
            "min_sharpe": 0.55,
            "min_sortino": 0.80,
            "min_calmar": 0.25,
            "core_risk_contrib_ratio_max": 1.8,
            "primary_metrics": ["cagr", "sortino"],
            "secondary_metrics": ["sharpe", "max_drawdown"],
            "description": "Equity Growth Diversified - multi-core regionale, rischio distribuito",
        }
    
    # === EQUITY_CORE_DRIVEN ===
    elif portfolio_type == "EQUITY_CORE_DRIVEN":
        return {
            "max_single_position": 0.85,      # Core globale può dominare
            "max_top3": 0.95,
            "max_satellite_single": 0.10,     # Satellite ridotti
            "max_satellite_total": 0.25,
            "max_correlation_satellite": 0.70,
            "max_drawdown": -0.35,
            "min_sharpe": 0.70,
            "min_sortino": 0.90,
            "min_calmar": 0.35,
            "core_risk_contrib_ratio_max": 1.3,  # Core guida rischio (normale)
            "primary_metrics": ["sharpe", "cagr"],
            "secondary_metrics": ["sortino", "max_drawdown"],
            "description": "Equity Core-Driven - concentrazione su World Index accettabile",
        }
    
    # === BALANCED ===
    elif portfolio_type == "BALANCED":
        return {
            "max_single_position": 0.45,
            "max_top3": 0.65,
            "max_satellite_single": 0.05,
            "max_satellite_total": 0.10,
            "max_correlation_satellite": 0.55,
            "max_drawdown": -0.18,            # Drawdown contenuto
            "min_sharpe": 0.55,
            "min_sortino": 0.75,
            "min_calmar": 0.45,               # Calmar importante
            "core_risk_contrib_ratio_max": 1.3,
            "primary_metrics": ["sharpe", "max_drawdown", "calmar"],
            "secondary_metrics": ["cagr", "sortino"],
            "description": "Balanced - focus risk-adjusted, drawdown contenuto",
        }
    
    # === DEFENSIVE ===
    elif portfolio_type == "DEFENSIVE":
        return {
            "max_single_position": 0.50,
            "max_top3": 0.70,
            "max_satellite_single": 0.03,     # Quasi no satellite
            "max_satellite_total": 0.05,
            "max_correlation_satellite": 0.45,
            "max_drawdown": -0.12,            # Drawdown molto basso
            "min_sharpe": 0.40,               # Sharpe basso accettabile
            "min_sortino": 0.50,
            "min_calmar": 0.60,               # Calmar critico
            "core_risk_contrib_ratio_max": 1.2,
            "primary_metrics": ["max_drawdown", "calmar", "volatility"],
            "secondary_metrics": ["sharpe", "sortino"],
            "description": "Defensive - preservazione capitale, drawdown minimo",
        }
    
    # === INCOME_YIELD ===
    elif portfolio_type == "INCOME_YIELD":
        return {
            "max_single_position": 0.40,
            "max_top3": 0.70,
            "max_satellite_single": 0.05,
            "max_satellite_total": 0.10,
            "max_correlation_satellite": 0.60,
            "max_drawdown": -0.20,
            "min_sharpe": 0.45,
            "min_sortino": 0.60,
            "min_calmar": 0.35,
            "core_risk_contrib_ratio_max": 1.4,
            "primary_metrics": ["yield_proxy", "sortino", "max_drawdown"],  # Yield è proxy
            "secondary_metrics": ["cagr", "sharpe"],
            "description": "Income/Yield - focus dividendi, stabilità income stream",
        }
    
    # === BARBELL_THEMATIC ===
    elif portfolio_type == "BARBELL_THEMATIC":
        return {
            "max_single_position": 0.65,
            "max_top3": 0.85,
            "max_satellite_single": 0.15,     # Satellite tematici grandi ok
            "max_satellite_total": 0.35,
            "max_correlation_satellite": 0.60,
            "max_drawdown": -0.30,
            "min_sharpe": 0.60,
            "min_sortino": 0.80,
            "min_calmar": 0.30,
            "core_risk_contrib_ratio_max": 1.5,
            "primary_metrics": ["cagr", "sharpe"],
            "secondary_metrics": ["sortino", "max_drawdown"],
            "description": "Barbell Thematic - core + scommesse tematiche",
        }
    
    # === RISK_PARITY (VERO - multi-asset) ===
    elif portfolio_type == "RISK_PARITY":
        return {
            "max_single_position": 0.30,      # Nessuno domina
            "max_top3": 0.60,
            "max_satellite_single": 0.10,
            "max_satellite_total": 0.20,
            "max_correlation_satellite": 0.50,
            "max_drawdown": -0.15,            # Multi-asset → DD contenuto
            "min_sharpe": 0.50,
            "min_sortino": 0.65,
            "min_calmar": 0.50,
            "core_risk_contrib_ratio_max": 1.15,  # Risk contribution equilibrata
            "primary_metrics": ["sharpe", "risk_contribution_balance"],
            "secondary_metrics": ["cagr", "max_drawdown"],
            "description": "Risk Parity multi-asset - bond+equity, risk contribution equilibrata",
        }
    
    # === EQUITY_MULTI_BLOCK (intra-equity diversified) ===
    # Soglie corrette per portafoglio equity multi-block growth
    elif portfolio_type == "EQUITY_MULTI_BLOCK":
        return {
            "max_single_position": 0.25,      # Nessuno domina
            "max_top3": 0.60,                 # Top 3 < 60%
            "max_satellite_single": 0.15,     # Tematici puri singoli fino a 15%
            "max_satellite_total": 0.30,      # Tematici puri totali fino a 30%
            "max_noncore_structural": 0.40,   # REIT + small cap + settori fino a 40%
            "max_correlation_satellite": 0.75, # Correlazione satellite declassata a info
            "max_drawdown": -0.40,            # Equity-only → DD -40% normale
            "min_sharpe": 0.40,               # Range realistico equity 2018-2026
            "min_sortino": 0.55,
            "min_calmar": 0.20,
            "core_risk_contrib_ratio_max": 1.5,
            "primary_metrics": ["cagr", "sortino", "risk_distribution"],
            "secondary_metrics": ["sharpe", "max_drawdown"],
            "description": "Equity Multi-Block - core geografico + fattoriali + settori + tematici",
        }
    
    return default


# === BACKWARD COMPATIBILITY ===
def detect_portfolio_regime(
    weights: np.ndarray,
    tickers: list,
    asset_metrics: pd.DataFrame
) -> Dict[str, Any]:
    """
    BACKWARD COMPATIBILITY - Wrapper per detect_portfolio_type.
    
    Mappa i nuovi 8 tipi ai vecchi nomi di regime per compatibilità.
    """
    type_info = detect_portfolio_type(weights, tickers, asset_metrics)
    
    # Mappa tipo -> vecchio nome regime
    type_to_regime = {
        "EQUITY_GROWTH_CORE": "EQUITY_CORE_DRIVEN",
        "EQUITY_GROWTH_DIVERSIFIED": "EQUITY_CORE_DRIVEN",
        "EQUITY_MULTI_BLOCK": "EQUITY_CORE_DRIVEN",  # Era erroneamente RISK_PARITY
        "EQUITY_CORE_DRIVEN": "EQUITY_CORE_DRIVEN",
        "BALANCED": "MULTI_ASSET_BALANCED",
        "DEFENSIVE": "MULTI_ASSET_BALANCED",
        "INCOME_YIELD": "MULTI_ASSET_BALANCED",
        "BARBELL_THEMATIC": "BARBELL_THEMATIC",
        "RISK_PARITY": "RISK_PARITY",  # Vero Risk Parity (multi-asset)
        "TACTICAL": "TACTICAL_ALLOCATION",
    }
    
    # Converti output per backward compatibility
    regime_info = {
        "regime": type_to_regime.get(type_info["type"], "TACTICAL_ALLOCATION"),
        "portfolio_type": type_info["type"],  # Nuovo: tipo specifico
        "confidence": type_info["confidence"],
        "thresholds": type_info["thresholds"],
        "composition": type_info["composition"],
        "core_tickers": type_info["details"]["core_tickers"],
        "satellite_tickers": type_info["details"]["satellite_tickers"],
        "type_reason": type_info["reason"],
    }
    
    return regime_info


def get_regime_thresholds(regime: str) -> Dict[str, Any]:
    """
    BACKWARD COMPATIBILITY - Wrapper per get_type_thresholds.
    """
    # Mappa vecchi regimi -> nuovi tipi
    regime_to_type = {
        "EQUITY_CORE_DRIVEN": "EQUITY_CORE_DRIVEN",
        "MULTI_ASSET_BALANCED": "BALANCED",
        "BARBELL_THEMATIC": "BARBELL_THEMATIC",
        "RISK_PARITY": "RISK_PARITY",
        "TACTICAL_ALLOCATION": "TACTICAL",
    }
    
    portfolio_type = regime_to_type.get(regime, "TACTICAL")
    return get_type_thresholds(portfolio_type)


def analyze_portfolio_issues(
    weights: np.ndarray,
    tickers: list,
    corr: pd.DataFrame,
    risk_contrib: pd.DataFrame,
    asset_metrics: pd.DataFrame,
    metrics: dict
) -> Tuple[list, Dict[str, Any]]:
    """
    Analisi critica del portafoglio da prospettiva quant.
    TYPE-AWARE: applica soglie appropriate al tipo di portafoglio.
    
    Returns:
        Tuple di (lista criticità, regime_info)
    """
    # === FASE 1: DETECT REGIME ===
    regime_info = detect_portfolio_regime(weights, tickers, asset_metrics)
    regime = regime_info["regime"]
    thresholds = regime_info["thresholds"]
    composition = regime_info["composition"]
    
    issues = []
    trade_offs = []  # Trade-off consapevoli (non errori)
    
    # === 1. CORRELAZIONI PROBLEMATICHE ===
    # Critichiamo correlazioni elevate SOLO tra satellite-satellite
    # Core-core, core-satellite, core-EM sono normali e non vanno segnalate
    satellite_tickers_set = set(regime_info.get("satellite_tickers", []))
    core_tickers_set = set(regime_info.get("core_tickers", []))
    
    # Estendi core tickers con EM (considerato core regionale)
    em_set = set()
    for t in tickers:
        if any(kw in t.upper() for kw in EMERGING_ETF):
            em_set.add(t)
    core_extended = core_tickers_set | em_set
    
    high_corr_pairs = []
    for i, t1 in enumerate(tickers):
        for j, t2 in enumerate(tickers):
            if i < j:
                corr_val = corr.loc[t1, t2]
                if pd.notna(corr_val) and corr_val > thresholds["max_correlation_satellite"]:
                    combined_weight = weights[i] + weights[j]
                    
                    # Check se entrambi sono core/EM - correlazione normale
                    t1_is_core = t1 in core_extended or any(kw in t1.upper() for kw in CORE_GLOBAL_ETF + CORE_REGIONAL_ETF + EMERGING_ETF)
                    t2_is_core = t2 in core_extended or any(kw in t2.upper() for kw in CORE_GLOBAL_ETF + CORE_REGIONAL_ETF + EMERGING_ETF)
                    
                    # Skip se almeno uno è core (correlazione core-X è normale)
                    if t1_is_core or t2_is_core:
                        continue  # Non è un problema - correlazioni con core sono attese
                    
                    # Solo correlazioni satellite-satellite sono problematiche
                    t1_is_sat = t1 in satellite_tickers_set or any(kw in t1.upper() for kw in SATELLITE_KEYWORDS)
                    t2_is_sat = t2 in satellite_tickers_set or any(kw in t2.upper() for kw in SATELLITE_KEYWORDS)
                    
                    if t1_is_sat and t2_is_sat:
                        high_corr_pairs.append((t1, t2, corr_val, combined_weight))
    
    for t1, t2, corr_val, comb_w in high_corr_pairs:
        # Declassa a info se correlazione è tra asset con driver fondamentali diversi
        # Es: VNQ (REIT tradizionali) vs SRVR (data center) - alta corr in stress ma driver diversi
        reit_data_center_pair = (
            (any(kw in t1.upper() for kw in REIT_ETF) and any(kw in t2.upper() for kw in ['SRVR', 'DATA', 'CLOUD'])) or
            (any(kw in t2.upper() for kw in REIT_ETF) and any(kw in t1.upper() for kw in ['SRVR', 'DATA', 'CLOUD']))
        )
        
        if reit_data_center_pair:
            # Declassa a nota informativa
            issues.append({
                "type": "CORRELATION_INFO",
                "severity": "ℹ️",
                "message": f"Correlazione statistica ({corr_val:.2f}) tra {t1} e {t2}. "
                          f"Driver fondamentali diversi → rischio economico non identico."
            })
        else:
            issues.append({
                "type": "HIGH_CORRELATION",
                "severity": "⚠️",
                "message": f"Correlazione elevata ({corr_val:.2f}) tra satelliti {t1} e {t2}. "
                          f"Peso combinato {comb_w:.1%} → diversificazione limitata tra satelliti."
            })
    
    # === 2. ASSET SATELLITE CON PESO ECCESSIVO ===
    satellites = []
    portfolio_type = regime_info.get("portfolio_type", regime)
    
    for i, t in enumerate(tickers):
        ticker_upper = t.upper()
        is_satellite = any(kw in ticker_upper for kw in SATELLITE_KEYWORDS)
        
        if t in asset_metrics.index:
            vol = asset_metrics.loc[t, 'Vol'] if 'Vol' in asset_metrics.columns else 0
            if vol > 0.25:
                is_satellite = True
        
        if is_satellite:
            satellites.append((t, weights[i]))
            if weights[i] > thresholds["max_satellite_single"]:
                # È un problema o un trade-off consapevole?
                # Per tipi che accettano più satellite, è trade-off
                acceptable_types = ["EQUITY_CORE_DRIVEN", "BARBELL_THEMATIC", "EQUITY_GROWTH_CORE", 
                                   "EQUITY_GROWTH_DIVERSIFIED", "EQUITY_MULTI_BLOCK"]
                if portfolio_type in acceptable_types and weights[i] <= 0.15:
                    trade_offs.append({
                        "type": "SATELLITE_WEIGHT",
                        "message": f"{t} al {weights[i]:.1%} (soglia: {thresholds['max_satellite_single']:.0%}). "
                                  f"Trade-off accettabile per tipo {portfolio_type}."
                    })
                else:
                    issues.append({
                        "type": "SATELLITE_OVERWEIGHT",
                        "severity": "⚠️",
                        "message": f"{t} è un asset satellite con peso {weights[i]:.1%}. "
                                  f"Soglia tipo {portfolio_type}: max {thresholds['max_satellite_single']:.0%}."
                    })
    
    # Totale satellite
    total_satellite_weight = sum(w for _, w in satellites)
    if total_satellite_weight > thresholds["max_satellite_total"]:
        issues.append({
            "type": "SATELLITE_TOTAL_EXCESSIVE",
            "severity": "🚨" if total_satellite_weight > thresholds["max_satellite_total"] * 1.5 else "⚠️",
            "message": f"Totale satellite {total_satellite_weight:.1%} > {thresholds['max_satellite_total']:.0%} (soglia tipo {portfolio_type})."
        })
    
    # === 3. CONCENTRAZIONE ===
    sorted_weights = np.sort(weights)[::-1]
    top3_weight = sorted_weights[:3].sum()
    max_weight = weights.max()
    max_ticker = tickers[weights.argmax()]
    
    # Check se il ticker dominante è un core globale diversificato
    is_core_global = any(kw in max_ticker.upper() for kw in CORE_GLOBAL_ETF)
    
    # Tipi che accettano alta concentrazione su core
    high_concentration_types = ["EQUITY_CORE_DRIVEN", "EQUITY_GROWTH_CORE", "BARBELL_THEMATIC"]
    
    # Single position check
    if max_weight > thresholds["max_single_position"]:
        if is_core_global and portfolio_type in high_concentration_types:
            # È un trade-off consapevole, non un errore
            trade_offs.append({
                "type": "CORE_CONCENTRATION",
                "message": f"{max_ticker} (core globale diversificato) al {max_weight:.1%}. "
                          f"Concentrazione accettabile per tipo {portfolio_type}."
            })
        else:
            issues.append({
                "type": "SINGLE_CONCENTRATION",
                "severity": "🚨",
                "message": f"{max_ticker} pesa {max_weight:.1%} > {thresholds['max_single_position']:.0%}. "
                          f"Posizione dominante non coerente con tipo {portfolio_type}."
            })
    
    # Top 3 check
    if top3_weight > thresholds["max_top3"]:
        if is_core_global and portfolio_type in high_concentration_types:
            trade_offs.append({
                "type": "TOP3_CONCENTRATION",
                "message": f"Top 3 = {top3_weight:.1%}. Accettabile per tipo {portfolio_type} con core."
            })
        else:
            issues.append({
                "type": "CONCENTRATION",
                "severity": "⚠️",
                "message": f"Top 3 posizioni = {top3_weight:.1%} > {thresholds['max_top3']:.0%} (soglia tipo {portfolio_type})."
            })
    
    # === 4. RISK CONTRIBUTION ANOMALA ===
    for t in risk_contrib.index:
        w = risk_contrib.loc[t, 'Weight']
        rc = risk_contrib.loc[t, 'CCR%']
        if pd.notna(rc) and w > 0.02:
            ratio = rc / w if w > 0 else 0
            is_core = any(kw in t.upper() for kw in CORE_GLOBAL_ETF + CORE_REGIONAL_ETF + EMERGING_ETF)
            
            # Per il core, risk contribution > weight è normale
            if is_core and ratio <= thresholds["core_risk_contrib_ratio_max"]:
                continue
            
            if ratio > 1.8:  # Soglia più alta per inefficienza reale
                issues.append({
                    "type": "RISK_INEFFICIENCY",
                    "severity": "⚠️",
                    "message": f"{t}: contribuisce {rc:.1%} al rischio con {w:.1%} del capitale. "
                              f"Rapporto {ratio:.1f}x → verifica se intenzionale."
                })
    
    # === 5. OVERLAP TRA ETF (gruppi specifici + overlap impliciti) ===
    overlap_groups = {
        "World Equity": ['VWCE', 'IWDA', 'SWDA', 'VT', 'ACWI', 'URTH'],
        "US Large Cap": ['VOO', 'SPY', 'IVV', 'CSPX', 'SXR8'],
        "EM": ['IS3N', 'EIMI', 'EEM', 'VWO', 'IEEM'],
        "Japan": ['EWJ', 'TOPX', 'DXJ', 'HEWJ'],
        "Pacific": ['VPL', 'EPP', 'IPAC'],
    }
    
    for group_name, group_tickers in overlap_groups.items():
        matching = [t for t in tickers if any(gt in t.upper() for gt in group_tickers)]
        if len(matching) > 1:
            total_w = sum(weights[i] for i, t in enumerate(tickers) if t in matching)
            issues.append({
                "type": "ETF_OVERLAP",
                "severity": "⚠️",
                "message": f"Possibile overlap in '{group_name}': {', '.join(matching)}. "
                          f"Peso totale {total_w:.1%}."
            })
    
    # === 5b. OVERLAP IMPLICITI (World contiene USA/EU/Japan) ===
    world_etfs = [t for t in tickers if any(w in t.upper() for w in ['VT', 'VWCE', 'ACWI', 'IWDA', 'SWDA', 'URTH'])]
    usa_etfs = [t for t in tickers if any(u in t.upper() for u in ['IVV', 'VOO', 'SPY', 'IWM', 'CSPX', 'SXR8', 'QQQ'])]
    japan_pacific = [t for t in tickers if any(j in t.upper() for j in ['EWJ', 'VPL', 'EPP', 'IPAC'])]
    
    if world_etfs and usa_etfs:
        world_w = sum(weights[i] for i, t in enumerate(tickers) if t in world_etfs)
        usa_w = sum(weights[i] for i, t in enumerate(tickers) if t in usa_etfs)
        # VT/VWCE contiene ~60% USA, quindi overlap implicito
        implicit_usa_overlap = world_w * 0.60
        issues.append({
            "type": "IMPLICIT_OVERLAP",
            "severity": "ℹ️",
            "message": f"Overlap implicito USA: {', '.join(world_etfs)} contiene ~60% USA. "
                      f"Con {', '.join(usa_etfs)} ({usa_w:.0%}), esposizione USA effettiva ~{(implicit_usa_overlap + usa_w):.0%}."
        })
    
    # Check Japan in VPL (VPL contiene ~65% Japan)
    ewj_tickers = [t for t in tickers if 'EWJ' in t.upper()]
    vpl_tickers = [t for t in tickers if 'VPL' in t.upper()]
    if ewj_tickers and vpl_tickers:
        ewj_w = sum(weights[i] for i, t in enumerate(tickers) if t in ewj_tickers)
        vpl_w = sum(weights[i] for i, t in enumerate(tickers) if t in vpl_tickers)
        issues.append({
            "type": "IMPLICIT_OVERLAP",
            "severity": "ℹ️",
            "message": f"Overlap Japan: VPL contiene ~65% Japan. Con EWJ ({ewj_w:.0%}), esposizione Japan ~{(ewj_w + vpl_w*0.65):.0%}."
        })
    
    # === 6. METRICHE RISK-ADJUSTED (type-aware) ===
    # Valuta metriche in base a quelle primarie per il tipo
    primary_metrics = thresholds.get("primary_metrics", ["sharpe", "sortino"])
    
    # Sharpe
    sharpe = metrics.get('sharpe', 0)
    if sharpe < thresholds["min_sharpe"]:
        severity = "⚠️" if "sharpe" in primary_metrics else "ℹ️"
        issues.append({
            "type": "LOW_SHARPE",
            "severity": severity,
            "message": f"Sharpe Ratio {sharpe:.2f} < {thresholds['min_sharpe']:.2f} (soglia tipo {portfolio_type})."
        })
    
    # Sortino
    sortino = metrics.get('sortino', 0)
    if sortino < thresholds["min_sortino"]:
        severity = "⚠️" if "sortino" in primary_metrics else "ℹ️"
        issues.append({
            "type": "LOW_SORTINO",
            "severity": severity,
            "message": f"Sortino Ratio {sortino:.2f} < {thresholds['min_sortino']:.2f}."
        })
    
    # === 7. DRAWDOWN (critico per tipi defensive/balanced) ===
    max_dd = metrics.get('max_drawdown', 0)
    max_dd_peak = metrics.get('max_dd_peak', None)
    
    # Contestualizza: se DD è durante GFC 2008-2009, è atteso
    gfc_period = False
    if max_dd_peak and hasattr(max_dd_peak, 'year'):
        if 2008 <= max_dd_peak.year <= 2009:
            gfc_period = True
    
    if max_dd < thresholds["max_drawdown"]:  # DD è negativo, quindi < è peggio
        # Severità dipende dal tipo e dal contesto storico
        # Per tipi difensivi, DD alto è critico
        if portfolio_type in ["DEFENSIVE", "BALANCED", "INCOME_YIELD", "RISK_PARITY"]:
            severity = "🚨"  # Critico per questi tipi
        # Per equity-only, periodi di crisi (GFC, COVID) sono attesi
        elif gfc_period and portfolio_type in ["EQUITY_GROWTH_CORE", "EQUITY_GROWTH_DIVERSIFIED", 
                                                "EQUITY_CORE_DRIVEN", "EQUITY_MULTI_BLOCK"]:
            severity = "ℹ️"  # GFC/COVID per equity è atteso
        else:
            severity = "⚠️"
        
        context_note = " (include GFC 2008-09)" if gfc_period else ""
        issues.append({
            "type": "HIGH_DRAWDOWN",
            "severity": severity,
            "message": f"Max Drawdown {max_dd:.1%} > {thresholds['max_drawdown']:.0%} atteso per tipo {portfolio_type}{context_note}."
        })
    
    # === 8. DATI MANCANTI ===
    nan_corr = corr.isna().sum().sum()
    if nan_corr > 0:
        issues.append({
            "type": "DATA_QUALITY",
            "severity": "🚨",
            "message": f"Matrice correlazione contiene {nan_corr} valori NaN. Dati incompleti."
        })
    
    # Aggiungi trade-offs al regime_info
    regime_info["trade_offs"] = trade_offs
    
    return issues, regime_info


def print_portfolio_critique(issues: list, regime_info: Dict[str, Any]) -> None:
    """
    Stampa analisi critica del portafoglio con identificazione tipo.
    
    OUTPUT COMPLETO:
    1. Tipo portafoglio identificato (8 tipi)
    2. Composizione dettagliata
    3. Soglie type-specific applicate
    4. Trade-off consapevoli
    5. Criticità raggruppate per severità
    6. Verdetto finale
    """
    
    regime = regime_info["regime"]
    portfolio_type = regime_info.get("portfolio_type", regime)
    confidence = regime_info["confidence"]
    composition = regime_info["composition"]
    trade_offs = regime_info.get("trade_offs", [])
    thresholds = regime_info["thresholds"]
    type_reason = regime_info.get("type_reason", "")
    
    print("\n" + "=" * 70)
    print("🔍 QUANT PORTFOLIO TYPE ANALYSIS")
    print("=" * 70)
    
    # === TIPO IDENTIFICATO (10 tipi) ===
    type_display = {
        "EQUITY_GROWTH_CORE": "📈 EQUITY GROWTH (Core-Driven)",
        "EQUITY_GROWTH_DIVERSIFIED": "🌍 EQUITY GROWTH (Diversified)",
        "EQUITY_MULTI_BLOCK": "🧱 EQUITY MULTI-BLOCK",
        "EQUITY_CORE_DRIVEN": "📊 EQUITY CORE-DRIVEN",
        "BALANCED": "⚖️ BALANCED (60/40)",
        "DEFENSIVE": "🛡️ DEFENSIVE / CAPITAL PRESERVATION",
        "INCOME_YIELD": "💰 INCOME / YIELD",
        "BARBELL_THEMATIC": "🎯 BARBELL THEMATIC",
        "RISK_PARITY": "📐 RISK PARITY (Multi-Asset)",
        "TACTICAL": "🎲 TACTICAL / OPPORTUNISTIC",
    }
    
    type_descriptions = {
        "EQUITY_GROWTH_CORE": "Beta concentrato su singolo driver, alta volatilità",
        "EQUITY_GROWTH_DIVERSIFIED": "Multi-core regionale, rischio distribuito ✓",
        "EQUITY_MULTI_BLOCK": "Pesi equilibrati, diversificazione intra-equity",
        "EQUITY_CORE_DRIVEN": "World index dominante + satellite",
        "BALANCED": "Multi-asset, drawdown contenuto",
        "DEFENSIVE": "Preservazione capitale, min drawdown",
        "INCOME_YIELD": "Dividendi/cedole, income stream",
        "BARBELL_THEMATIC": "Core + scommesse tematiche",
        "RISK_PARITY": "Multi-asset (bond+equity), risk contribution equilibrata",
        "TACTICAL": "Allocazione opportunistica",
    }
    
    print(f"\n🏷️  TIPO IDENTIFICATO: {type_display.get(portfolio_type, portfolio_type)}")
    print(f"   {type_descriptions.get(portfolio_type, '')}")
    print(f"   Confidence: {confidence:.0%}")
    if type_reason:
        print(f"   Motivazione: {type_reason}")
    
    # === COMPOSIZIONE DETTAGLIATA (tassonomia granulare v2) ===
    print("\n📊 COMPOSIZIONE PORTAFOGLIO:")
    print("-" * 50)
    print(f"   Core Globale:       {composition['core_global']:>6.1%}  (VT, VWCE, IWDA)")
    print(f"   Core Regionale:     {composition['core_regional']:>6.1%}  (IVV, EWJ, VGK...)")
    
    # Mostra breakdown strutturale non-core se presente
    if composition.get('structural_noncore', 0) > 0:
        print(f"   --- Strutturale Non-Core ---")
        if composition.get('small_cap', 0) > 0:
            print(f"     Small Cap:        {composition['small_cap']:>6.1%}  (IUSN, IWM...)")
        if composition.get('reit', 0) > 0:
            print(f"     REIT:             {composition['reit']:>6.1%}  (VNQ, VNQI...)")
        if composition.get('factor', 0) > 0:
            print(f"     Fattoriale:       {composition['factor']:>6.1%}  (MTUM, QUAL...)")
        if composition.get('sector', 0) > 0:
            print(f"     Settoriale:       {composition['sector']:>6.1%}  (IBB, XLF...)")
    
    # Mostra tematici puri (veri satellite)
    if composition.get('thematic_pure', 0) > 0 or composition.get('true_satellite', 0) > 0:
        thematic = composition.get('thematic_pure', 0) or composition.get('true_satellite', 0)
        print(f"   Tematico Puro:      {thematic:>6.1%}  (URA, ARKK, SRVR...)")
    elif composition.get('satellite', 0) > 0:
        print(f"   Satellite:          {composition['satellite']:>6.1%}  (Tematici)")
    
    print(f"   Bond:               {composition['bond']:>6.1%}")
    if composition.get('gold_commodity', 0) > 0:
        print(f"   Gold/Commodity:     {composition['gold_commodity']:>6.1%}")
    if composition.get('dividend_income', 0) > 0:
        print(f"   Dividend/Income:    {composition['dividend_income']:>6.1%}")
    print("-" * 50)
    print(f"   TOTALE EQUITY:      {composition['total_equity']:>6.1%}")
    if composition.get('total_defensive', 0) > 0:
        print(f"   TOTALE DEFENSIVE:   {composition['total_defensive']:>6.1%}")
    
    # === SOGLIE TYPE-SPECIFIC ===
    print(f"\n📏 SOGLIE PER TIPO '{portfolio_type}':")
    print("-" * 50)
    print(f"   Max singola posizione:  {thresholds['max_single_position']:>6.0%}")
    print(f"   Max top 3:              {thresholds['max_top3']:>6.0%}")
    print(f"   Max satellite singolo:  {thresholds['max_satellite_single']:>6.0%}")
    print(f"   Max satellite totale:   {thresholds['max_satellite_total']:>6.0%}")
    print(f"   Max drawdown accettato: {thresholds['max_drawdown']:>6.0%}")
    print(f"   Min Sharpe atteso:      {thresholds['min_sharpe']:>6.2f}")
    if 'description' in thresholds:
        print(f"   → {thresholds['description']}")
    
    # === METRICHE PRIMARIE vs SECONDARIE ===
    if 'primary_metrics' in thresholds:
        print(f"\n📌 METRICHE PRIMARIE: {', '.join(thresholds['primary_metrics'])}")
        print(f"   (Queste metriche sono critiche per tipo {portfolio_type})")
    if 'secondary_metrics' in thresholds:
        print(f"   Secondarie: {', '.join(thresholds['secondary_metrics'])}")
    
    # === TRADE-OFF CONSAPEVOLI ===
    if trade_offs:
        print("\n✅ TRADE-OFF CONSAPEVOLI (coerenti con il tipo):")
        print("-" * 50)
        for to in trade_offs:
            print(f"   • {to['message']}")
    
    # === CRITICITÀ ===
    if not issues:
        print("\n" + "=" * 70)
        print("✅ NESSUNA CRITICITÀ RILEVATA")
        print(f"   Portafoglio pienamente coerente con tipo {portfolio_type}")
        print("=" * 70)
    else:
        severity_order = {"🚨": 0, "⚠️": 1, "ℹ️": 2}
        issues_sorted = sorted(issues, key=lambda x: severity_order.get(x["severity"], 3))
        
        critical = [i for i in issues_sorted if i["severity"] == "🚨"]
        warnings = [i for i in issues_sorted if i["severity"] == "⚠️"]
        info = [i for i in issues_sorted if i["severity"] == "ℹ️"]
        
        if critical:
            print("\n🚨 CRITICITÀ SEVERE:")
            print("-" * 50)
            for issue in critical:
                print(f"   • {issue['message']}")
        
        if warnings:
            print("\n⚠️  ATTENZIONE:")
            print("-" * 50)
            for issue in warnings:
                print(f"   • {issue['message']}")
        
        if info:
            print("\nℹ️  NOTE:")
            print("-" * 50)
            for issue in info:
                print(f"   • {issue['message']}")
    
    # === VERDETTO FINALE ===
    print("\n" + "=" * 70)
    
    # Conta solo criticità reali (escludi data quality per verdetto)
    real_critical = [i for i in issues if i["severity"] == "🚨" and i["type"] != "DATA_QUALITY"]
    real_warnings = [i for i in issues if i["severity"] == "⚠️"]
    
    if real_critical:
        print("📋 VERDETTO: ❌ DA RISTRUTTURARE")
        print(f"   Criticità severe non coerenti con tipo {portfolio_type}.")
        print("   Suggerimento: rivedi la composizione o considera un tipo diverso.")
    elif len(real_warnings) >= 3:
        print("📋 VERDETTO: ⚠️ APPROVATO CON RISERVE")
        print(f"   Diverse aree di miglioramento per tipo {portfolio_type}.")
        print("   Il portafoglio funziona ma può essere ottimizzato.")
    elif real_warnings:
        print("📋 VERDETTO: ✅ APPROVATO CON TRADE-OFF CONSAPEVOLI")
        print(f"   Portafoglio coerente con tipo {portfolio_type}.")
        print(f"   Trade-off identificati e accettabili per la strategia.")
    else:
        print("📋 VERDETTO: ✅ APPROVATO - STRUTTURALMENTE SOLIDO")
        print(f"   Portafoglio pienamente coerente con tipo {portfolio_type}.")
        print("   Nessuna criticità, costruzione solida.")
    
    print("=" * 70)


def print_senior_architect_analysis(
    tickers: list,
    weights: np.ndarray,
    metrics: dict,
    regime_info: Dict[str, Any],
    issues: list,
    corr: pd.DataFrame = None
) -> None:
    """
    SENIOR PORTFOLIO ARCHITECT ANALYSIS (Vanguard Style)
    
    Analisi approfondita che include:
    1. Esposizione geografica REALE (considerando composizione interna ETF)
    2. Classificazione per FUNZIONE ECONOMICA
    3. Analisi overlap e false diversificazioni
    4. Punti di forza strutturali
    5. Verdetto con bullet point motivazionali
    """
    
    portfolio_type = regime_info.get("portfolio_type", "TACTICAL")
    composition = regime_info.get("composition", {})
    thresholds = regime_info.get("thresholds", {})
    
    print("\n" + "=" * 70)
    print("🏛️  SENIOR PORTFOLIO ARCHITECT ANALYSIS")
    print("    Framework Istituzionale (Vanguard Style)")
    print("=" * 70)
    
    # === 1. ESPOSIZIONE GEOGRAFICA REALE ===
    geo_exposure = calculate_geographic_exposure(tickers, weights)
    
    print("\n🌍 ESPOSIZIONE GEOGRAFICA EFFETTIVA:")
    print("-" * 50)
    print("   (Calcolata considerando composizione interna ETF)")
    print()
    
    # Ordina per peso decrescente
    geo_sorted = sorted(geo_exposure.items(), key=lambda x: x[1], reverse=True)
    total_geo = sum(geo_exposure.values())
    
    for region, pct in geo_sorted:
        if pct > 0.01:
            bar_len = int(pct * 40)
            bar = "█" * bar_len
            region_names = {
                "USA": "🇺🇸 USA",
                "Europe": "🇪🇺 Europa",
                "Japan": "🇯🇵 Giappone",
                "EM": "🌏 Emergenti",
                "Other_DM": "🌐 Altri DM"
            }
            print(f"   {region_names.get(region, region):<18} {pct:>6.1%}  {bar}")
    
    print("-" * 50)
    print(f"   Totale:                     {total_geo:>6.1%}")
    
    # Analisi concentrazione geografica
    usa_pct = geo_exposure.get("USA", 0)
    if usa_pct > 0.70:
        print(f"\n   ⚠️ CONCENTRAZIONE USA ELEVATA ({usa_pct:.0%})")
        print(f"      Rischio: esposizione eccessiva a un singolo mercato")
    elif usa_pct > 0.60:
        print(f"\n   ℹ️ Bias USA moderato ({usa_pct:.0%}) - comune per portafogli growth")
    elif usa_pct < 0.45:
        print(f"\n   ✓ Esposizione USA contenuta ({usa_pct:.0%}) - diversificazione effettiva")
    
    # === 2. ESPOSIZIONE PER FUNZIONE ECONOMICA ===
    function_exposure = analyze_function_exposure(tickers, weights)
    
    print("\n\n⚙️  ESPOSIZIONE PER FUNZIONE ECONOMICA:")
    print("-" * 50)
    
    function_names = {
        "CORE_GROWTH": "📈 Core Growth (rendimento principale)",
        "REGIONAL_DIVERSIFICATION": "🌍 Diversificazione Regionale",
        "EM_EXPOSURE": "🌏 Esposizione Emergenti",
        "FACTOR_TILT": "📊 Factor Tilt (size/value/momentum)",
        "REAL_ASSETS": "🏢 Real Assets (REIT/infrastrutture)",
        "CYCLICAL_HEDGE": "⚡ Settori Ciclici",
        "DEFENSIVE_SECTOR": "🛡️ Settori Difensivi",
        "THEMATIC_ALPHA": "🎯 Tematici Alpha (scommesse)",
        "INCOME": "💰 Income (dividendi/cedole)",
        "TAIL_HEDGE": "🔒 Tail Hedge (oro/bond lunghi)"
    }
    
    func_sorted = sorted(function_exposure.items(), key=lambda x: x[1], reverse=True)
    for func, pct in func_sorted:
        if pct > 0.01:
            bar_len = int(pct * 35)
            bar = "▓" * bar_len
            print(f"   {function_names.get(func, func):<40} {pct:>6.1%}  {bar}")
    
    # === 3. CONCENTRAZIONE E FALSE DIVERSIFICAZIONI ===
    print("\n\n🔬 ANALISI CONCENTRAZIONE E OVERLAP:")
    print("-" * 50)
    
    # Calcola metriche concentrazione
    weights_sorted = sorted(weights, reverse=True)
    max_position = weights_sorted[0] if weights_sorted else 0
    top3 = sum(weights_sorted[:3]) if len(weights_sorted) >= 3 else sum(weights_sorted)
    top5 = sum(weights_sorted[:5]) if len(weights_sorted) >= 5 else sum(weights_sorted)
    hhi = sum(w**2 for w in weights)  # Herfindahl-Hirschman Index
    effective_n = 1 / hhi if hhi > 0 else len(weights)  # Numero effettivo di posizioni
    
    print(f"   Max posizione singola:    {max_position:>6.1%}")
    print(f"   Top 3 posizioni:          {top3:>6.1%}")
    print(f"   Top 5 posizioni:          {top5:>6.1%}")
    print(f"   HHI (concentrazione):     {hhi:>6.3f}  (più basso = più diversificato)")
    print(f"   N. effettivo posizioni:   {effective_n:>6.1f}  (vs {len(weights)} nominali)")
    
    # False diversificazioni
    false_div_warnings = detect_false_diversification(tickers, weights, geo_exposure, corr)
    
    if false_div_warnings:
        print("\n   🔎 FALSE DIVERSIFICAZIONI RILEVATE:")
        for w in false_div_warnings:
            severity_icon = "🚨" if w["severity"] == "structural" else "ℹ️"
            print(f"      {severity_icon} {w['message']}")
    else:
        print("\n   ✓ Nessuna falsa diversificazione significativa rilevata")
    
    # === 4. PUNTI DI FORZA STRUTTURALI ===
    strengths = identify_structural_strengths(composition, geo_exposure, function_exposure, metrics, weights)
    
    if strengths:
        print("\n\n💪 PUNTI DI FORZA STRUTTURALI:")
        print("-" * 50)
        for i, s in enumerate(strengths, 1):
            print(f"   {i}. {s}")
    
    # === 5. VERDETTO FINALE CON BULLET POINT ===
    bullets = generate_verdict_bullets(portfolio_type, strengths, issues, metrics, composition)
    
    # Determina verdetto
    real_critical = [i for i in issues if i.get("severity") == "🚨" and i.get("type") != "DATA_QUALITY"]
    structural_issues = [i for i in issues if i.get("severity") == "⚠️"]
    false_div_structural = [w for w in false_div_warnings if w.get("severity") == "structural"]
    
    print("\n" + "=" * 70)
    
    if real_critical or len(false_div_structural) >= 2:
        print("📋 VERDETTO FINALE: ⛔ STRUTTURALMENTE INCOERENTE")
        print("   Richiede ristrutturazione prima di implementazione")
    elif structural_issues or false_div_structural:
        print("📋 VERDETTO FINALE: ✅ APPROVATO CON TRADE-OFF CONSAPEVOLI")
    elif len(strengths) >= 4:
        print("📋 VERDETTO FINALE: ✅ APPROVATO - COSTRUZIONE ISTITUZIONALE")
    else:
        print("📋 VERDETTO FINALE: ✅ APPROVATO - STRUTTURALMENTE SOLIDO")
    
    print("\n   Motivazioni:")
    for bullet in bullets:
        print(f"   • {bullet}")
    
    # Firma istituzionale
    print("\n" + "-" * 70)
    print("   Analisi condotta secondo framework Senior Portfolio Architect")
    print("   Standard: Vanguard/BlackRock Institutional Guidelines")
    print("=" * 70)


# =========================
# OUTPUT FUNCTIONS
# =========================

def print_summary(
    metrics: dict,
    risk_contrib: pd.DataFrame,
    corr: pd.DataFrame,
    asset_metrics: pd.DataFrame
) -> None:
    """Stampa report completo."""
    
    print("\n" + "=" * 70)
    print("                      PORTFOLIO ANALYSIS REPORT")
    print("                          (Methodology v2.0)")
    print("=" * 70)
    
    # === PERFORMANCE ===
    print("\n📈 PERFORMANCE")
    print("-" * 50)
    print(f"  Total ROI:              {metrics['total_roi']:>12.2%}")
    print(f"  CAGR (geometric):       {metrics['cagr']:>12.2%}")
    print(f"  Volatility (ann.):      {metrics['volatility']:>12.2%}")
    
    # === RISK-ADJUSTED ===
    print("\n📊 RISK-ADJUSTED METRICS")
    print("-" * 50)
    print(f"  Sharpe Ratio:           {metrics['sharpe']:>12.2f}")
    print(f"  Sortino Ratio:          {metrics['sortino']:>12.2f}")
    print(f"  Calmar Ratio:           {metrics['calmar']:>12.2f}")
    print(f"  Profit Factor:          {metrics['profit_factor']:>12.2f}")
    print(f"  Gain/Loss Ratio:        {metrics['gain_loss_ratio']:>12.2f}")
    
    # === DRAWDOWN ===
    print("\n📉 DRAWDOWN ANALYSIS")
    print("-" * 50)
    print(f"  Max Drawdown:           {metrics['max_drawdown']:>12.2%}")
    print(f"    Peak Date:            {metrics['max_dd_peak'].strftime('%Y-%m-%d'):>12}")
    print(f"    Trough Date:          {metrics['max_dd_trough'].strftime('%Y-%m-%d'):>12}")
    print(f"  Avg Drawdown:           {metrics['avg_drawdown']:>12.2%}")
    print(f"  Current Drawdown:       {metrics['current_drawdown']:>12.2%}")
    
    # === VAR/CVAR ===
    print("\n⚠️  TAIL RISK (95% confidence)")
    print("-" * 50)
    print(f"  VaR (daily):            {metrics['var_95_daily']:>12.2%}")
    print(f"  CVaR (daily):           {metrics['cvar_95_daily']:>12.2%}")
    print(f"  VaR (annualized):       {metrics['var_95_annual']:>12.2%}")
    print(f"  CVaR (annualized):      {metrics['cvar_95_annual']:>12.2%}")
    
    # === MONTHLY ===
    print("\n📅 MONTHLY STATISTICS")
    print("-" * 50)
    print(f"  Months Up:              {metrics['months_up']:>8} / {metrics['months_total']} ({metrics['win_rate_monthly']:.1%})")
    print(f"  Months Down:            {metrics['months_down']:>8} / {metrics['months_total']}")
    print(f"  Best Month:             {metrics['best_month']:>12.2%}")
    print(f"  Worst Month:            {metrics['worst_month']:>12.2%}")
    print(f"  Avg Month:              {metrics['avg_month']:>12.2%}")
    
    # === YEARLY ===
    print("\n📆 YEARLY STATISTICS")
    print("-" * 50)
    print(f"  Years Up:               {metrics['years_up']:>8} / {metrics['years_total']}")
    print(f"  Years Down:             {metrics['years_down']:>8} / {metrics['years_total']}")
    print(f"  Best Year:              {metrics['best_year']:>12.2%}")
    print(f"  Worst Year:             {metrics['worst_year']:>12.2%}")
    
    # === DAILY ===
    print("\n📌 DAILY STATISTICS")
    print("-" * 50)
    win_rate = metrics['days_up'] / metrics['days_total'] if metrics['days_total'] > 0 else 0
    print(f"  Days Up:                {metrics['days_up']:>8} / {metrics['days_total']} ({win_rate:.1%})")
    print(f"  Days Down:              {metrics['days_down']:>8} / {metrics['days_total']}")
    print(f"  Best Day:               {metrics['best_day']:>12.2%}")
    print(f"  Worst Day:              {metrics['worst_day']:>12.2%}")
    
    # === RISK CONTRIBUTION ===
    print("\n" + "=" * 70)
    print("RISK CONTRIBUTION (Component Contribution to Risk)")
    print("=" * 70)
    print(f"{'Ticker':<12} {'Weight':>8} {'MCR':>10} {'CCR':>10} {'CCR%':>10}")
    print("-" * 50)
    for ticker in risk_contrib.index:
        row = risk_contrib.loc[ticker]
        print(f"{ticker:<12} {row['Weight']:>8.2%} {row['MCR']:>10.4f} {row['CCR']:>10.4f} {row['CCR%']:>10.2%}")
    print("-" * 50)
    print(f"{'TOTAL':<12} {risk_contrib['Weight'].sum():>8.2%} {'':<10} {risk_contrib['CCR'].sum():>10.4f} {risk_contrib['CCR%'].sum():>10.2%}")
    
    # === ASSET METRICS ===
    print("\n" + "=" * 70)
    print("INDIVIDUAL ASSET METRICS (annualized)")
    print("=" * 70)
    print(asset_metrics.to_string(float_format=lambda x: f"{x:.4f}"))
    
    # === CORRELATION ===
    print("\n" + "=" * 70)
    print("CORRELATION MATRIX")
    print("=" * 70)
    print(corr.round(2).to_string())


# =========================
# EXPORT FUNCTIONS
# =========================

def create_output_dir(output_dir: str) -> Path:
    """Crea la directory di output se non esiste."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_timestamp() -> str:
    """Genera timestamp per i nomi dei file."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def export_to_csv(
    output_dir: Path,
    equity: pd.Series,
    returns: pd.Series,
    metrics: dict,
    risk_contrib: pd.DataFrame,
    asset_metrics: pd.DataFrame,
    corr: pd.DataFrame,
    prices: pd.DataFrame
) -> list:
    """Esporta tutti i dati in formato CSV."""
    timestamp = get_timestamp()
    exported_files = []
    
    # 1. Equity curve
    equity_df = pd.DataFrame({'date': equity.index, 'equity': equity.values})
    equity_file = output_dir / f"equity_curve_{timestamp}.csv"
    equity_df.to_csv(equity_file, index=False)
    exported_files.append(equity_file)
    
    # 2. Daily returns
    returns_df = pd.DataFrame({'date': returns.index, 'return': returns.values})
    returns_file = output_dir / f"daily_returns_{timestamp}.csv"
    returns_df.to_csv(returns_file, index=False)
    exported_files.append(returns_file)
    
    # 3. Monthly returns
    monthly_ret = returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)
    monthly_df = pd.DataFrame({'date': monthly_ret.index, 'return': monthly_ret.values})
    monthly_file = output_dir / f"monthly_returns_{timestamp}.csv"
    monthly_df.to_csv(monthly_file, index=False)
    exported_files.append(monthly_file)
    
    # 4. Portfolio metrics
    metrics_df = pd.DataFrame([metrics]).T
    metrics_df.columns = ['value']
    metrics_file = output_dir / f"portfolio_metrics_{timestamp}.csv"
    metrics_df.to_csv(metrics_file)
    exported_files.append(metrics_file)
    
    # 5. Risk contribution
    risk_file = output_dir / f"risk_contribution_{timestamp}.csv"
    risk_contrib.to_csv(risk_file)
    exported_files.append(risk_file)
    
    # 6. Asset metrics
    asset_file = output_dir / f"asset_metrics_{timestamp}.csv"
    asset_metrics.to_csv(asset_file)
    exported_files.append(asset_file)
    
    # 7. Correlation matrix
    corr_file = output_dir / f"correlation_matrix_{timestamp}.csv"
    corr.to_csv(corr_file)
    exported_files.append(corr_file)
    
    # 8. Raw prices
    prices_file = output_dir / f"prices_{timestamp}.csv"
    prices.to_csv(prices_file)
    exported_files.append(prices_file)
    
    return exported_files


def export_to_excel(
    output_dir: Path,
    equity: pd.Series,
    returns: pd.Series,
    metrics: dict,
    risk_contrib: pd.DataFrame,
    asset_metrics: pd.DataFrame,
    corr: pd.DataFrame,
    prices: pd.DataFrame
) -> Path:
    """Esporta tutti i dati in un unico file Excel con più fogli."""
    timestamp = get_timestamp()
    excel_file = output_dir / f"portfolio_analysis_{timestamp}.xlsx"
    
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        # Summary metrics
        metrics_clean = {k: v for k, v in metrics.items() 
                        if not isinstance(v, (pd.Timestamp, datetime))}
        # Converti timestamp separatamente
        for k, v in metrics.items():
            if isinstance(v, (pd.Timestamp, datetime)):
                metrics_clean[k] = str(v.date()) if hasattr(v, 'date') else str(v)
        
        pd.DataFrame([metrics_clean]).T.to_excel(writer, sheet_name='Summary')
        
        # Equity curve
        pd.DataFrame({'equity': equity}).to_excel(writer, sheet_name='Equity')
        
        # Daily returns
        pd.DataFrame({'return': returns}).to_excel(writer, sheet_name='Daily Returns')
        
        # Monthly returns
        monthly_ret = returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)
        pd.DataFrame({'return': monthly_ret}).to_excel(writer, sheet_name='Monthly Returns')
        
        # Risk contribution
        risk_contrib.to_excel(writer, sheet_name='Risk Contribution')
        
        # Asset metrics
        asset_metrics.to_excel(writer, sheet_name='Asset Metrics')
        
        # Correlation
        corr.to_excel(writer, sheet_name='Correlation')
        
        # Prices
        prices.to_excel(writer, sheet_name='Prices')
    
    return excel_file


def export_to_json(
    output_dir: Path,
    equity: pd.Series,
    returns: pd.Series,
    metrics: dict,
    risk_contrib: pd.DataFrame,
    asset_metrics: pd.DataFrame,
    corr: pd.DataFrame,
    config: dict
) -> Path:
    """Esporta i dati in formato JSON."""
    timestamp = get_timestamp()
    json_file = output_dir / f"portfolio_analysis_{timestamp}.json"
    
    # Prepara dati per JSON
    export_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "version": "2.1",
            "config": {
                "tickers": config["tickers"],
                "weights": config["weights"],
                "risk_free": config["risk_free_annual"],
                "rebalance": config.get("rebalance"),
            }
        },
        "metrics": {},
        "equity_curve": {
            "dates": [d.isoformat() for d in equity.index],
            "values": equity.values.tolist()
        },
        "monthly_returns": {},
        "risk_contribution": risk_contrib.to_dict(),
        "asset_metrics": asset_metrics.to_dict(),
        "correlation": corr.to_dict()
    }
    
    # Converti metrics con gestione timestamp
    for k, v in metrics.items():
        if isinstance(v, (pd.Timestamp, datetime)):
            export_data["metrics"][k] = v.isoformat()
        elif isinstance(v, (np.floating, np.integer)):
            export_data["metrics"][k] = float(v)
        else:
            export_data["metrics"][k] = v
    
    # Monthly returns
    monthly_ret = returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)
    export_data["monthly_returns"] = {
        "dates": [d.isoformat() for d in monthly_ret.index],
        "values": monthly_ret.values.tolist()
    }
    
    with open(json_file, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    return json_file


def export_charts(
    output_dir: Path,
    equity: pd.Series,
    returns: pd.Series,
    chart_format: str = "png"
) -> list:
    """Esporta grafici come immagini."""
    timestamp = get_timestamp()
    exported_files = []
    
    # Usa backend non interattivo per export
    plt.switch_backend('Agg')
    
    # 1. Equity Curve
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(equity.index, equity.values, color='blue', linewidth=1.5)
    ax.set_title("Portfolio Equity Curve", fontsize=14)
    ax.set_ylabel("Value (base 1)")
    ax.grid(True, alpha=0.3)
    ax.axhline(y=1, color='gray', linestyle='--', alpha=0.5)
    equity_chart = output_dir / f"chart_equity_{timestamp}.{chart_format}"
    plt.savefig(equity_chart, dpi=150, bbox_inches='tight')
    plt.close()
    exported_files.append(equity_chart)
    
    # 2. Drawdown
    fig, ax = plt.subplots(figsize=(12, 6))
    dd = equity / equity.cummax() - 1
    ax.fill_between(dd.index, dd.values, 0, color='red', alpha=0.3)
    ax.plot(dd.index, dd.values, color='red', linewidth=1)
    ax.set_title("Drawdown", fontsize=14)
    ax.set_ylabel("Drawdown %")
    ax.grid(True, alpha=0.3)
    dd_chart = output_dir / f"chart_drawdown_{timestamp}.{chart_format}"
    plt.savefig(dd_chart, dpi=150, bbox_inches='tight')
    plt.close()
    exported_files.append(dd_chart)
    
    # 3. Returns Distribution
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(returns, bins=50, color='steelblue', alpha=0.7, edgecolor='black')
    ax.axvline(returns.mean(), color='green', linestyle='--', label=f'Mean: {returns.mean():.4f}')
    ax.axvline(returns.quantile(0.05), color='red', linestyle='--', label=f'VaR 5%: {returns.quantile(0.05):.4f}')
    ax.set_title("Daily Returns Distribution", fontsize=14)
    ax.legend()
    ax.grid(True, alpha=0.3)
    dist_chart = output_dir / f"chart_distribution_{timestamp}.{chart_format}"
    plt.savefig(dist_chart, dpi=150, bbox_inches='tight')
    plt.close()
    exported_files.append(dist_chart)
    
    # 4. Monthly Returns
    fig, ax = plt.subplots(figsize=(14, 6))
    monthly = returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)
    colors = ['green' if x > 0 else 'red' for x in monthly]
    ax.bar(monthly.index, monthly.values, color=colors, alpha=0.7, width=20)
    ax.set_title("Monthly Returns", fontsize=14)
    ax.set_ylabel("Return %")
    ax.axhline(y=0, color='black', linewidth=0.5)
    ax.grid(True, alpha=0.3)
    monthly_chart = output_dir / f"chart_monthly_{timestamp}.{chart_format}"
    plt.savefig(monthly_chart, dpi=150, bbox_inches='tight')
    plt.close()
    exported_files.append(monthly_chart)
    
    # 5. Dashboard completa
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    axes[0, 0].plot(equity.index, equity.values, color='blue', linewidth=1.5)
    axes[0, 0].set_title("Equity Curve")
    axes[0, 0].grid(True, alpha=0.3)
    
    axes[0, 1].fill_between(dd.index, dd.values, 0, color='red', alpha=0.3)
    axes[0, 1].set_title("Drawdown")
    axes[0, 1].grid(True, alpha=0.3)
    
    axes[1, 0].hist(returns, bins=50, color='steelblue', alpha=0.7)
    axes[1, 0].set_title("Returns Distribution")
    axes[1, 0].grid(True, alpha=0.3)
    
    axes[1, 1].bar(monthly.index, monthly.values, color=colors, alpha=0.7, width=20)
    axes[1, 1].set_title("Monthly Returns")
    axes[1, 1].axhline(y=0, color='black', linewidth=0.5)
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    dashboard_chart = output_dir / f"chart_dashboard_{timestamp}.{chart_format}"
    plt.savefig(dashboard_chart, dpi=150, bbox_inches='tight')
    plt.close()
    exported_files.append(dashboard_chart)
    
    # Ripristina backend interattivo
    plt.switch_backend('TkAgg')
    
    return exported_files


def generate_html_report(
    output_dir: Path,
    metrics: dict,
    risk_contrib: pd.DataFrame,
    asset_metrics: pd.DataFrame,
    corr: pd.DataFrame,
    config: dict,
    data_range: tuple
) -> Path:
    """Genera un report HTML completo."""
    timestamp = get_timestamp()
    html_file = output_dir / f"portfolio_report_{timestamp}.html"
    
    # CSS styling
    css = """
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: right; }
        th { background: #3498db; color: white; }
        tr:nth-child(even) { background: #f9f9f9; }
        tr:hover { background: #f1f1f1; }
        .metric-card { display: inline-block; background: #ecf0f1; padding: 15px 25px; margin: 10px; border-radius: 8px; min-width: 150px; }
        .metric-card .value { font-size: 24px; font-weight: bold; color: #2c3e50; }
        .metric-card .label { font-size: 12px; color: #7f8c8d; text-transform: uppercase; }
        .positive { color: #27ae60; }
        .negative { color: #e74c3c; }
        .section { margin: 30px 0; padding: 20px; background: #fafafa; border-radius: 8px; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #7f8c8d; font-size: 12px; }
    </style>
    """
    
    # Calcola valori per classi CSS
    roi_class = 'positive' if metrics['total_roi'] > 0 else 'negative'
    cagr_class = 'positive' if metrics['cagr'] > 0 else 'negative'
    
    # Genera HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Portfolio Analysis Report</title>
        {css}
    </head>
    <body>
        <div class="container">
            <h1>📊 Portfolio Analysis Report</h1>
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Data Range:</strong> {data_range[0]} to {data_range[1]}</p>
            
            <h2>📈 Performance Summary</h2>
            <div class="section">
                <div class="metric-card">
                    <div class="value {roi_class}">{metrics['total_roi']:.2%}</div>
                    <div class="label">Total ROI</div>
                </div>
                <div class="metric-card">
                    <div class="value {cagr_class}">{metrics['cagr']:.2%}</div>
                    <div class="label">CAGR</div>
                </div>
                <div class="metric-card">
                    <div class="value">{metrics['volatility']:.2%}</div>
                    <div class="label">Volatility</div>
                </div>
                <div class="metric-card">
                    <div class="value">{metrics['sharpe']:.2f}</div>
                    <div class="label">Sharpe Ratio</div>
                </div>
                <div class="metric-card">
                    <div class="value">{metrics['sortino']:.2f}</div>
                    <div class="label">Sortino Ratio</div>
                </div>
                <div class="metric-card">
                    <div class="value negative">{metrics['max_drawdown']:.2%}</div>
                    <div class="label">Max Drawdown</div>
                </div>
            </div>
            
            <h2>⚠️ Risk Metrics</h2>
            <div class="section">
                <div class="metric-card">
                    <div class="value negative">{metrics['var_95_daily']:.2%}</div>
                    <div class="label">VaR 95% (daily)</div>
                </div>
                <div class="metric-card">
                    <div class="value negative">{metrics['cvar_95_daily']:.2%}</div>
                    <div class="label">CVaR 95% (daily)</div>
                </div>
                <div class="metric-card">
                    <div class="value">{metrics['calmar']:.2f}</div>
                    <div class="label">Calmar Ratio</div>
                </div>
            </div>
            
            <h2>📊 Asset Allocation</h2>
            {asset_metrics.to_html(classes='', float_format=lambda x: f'{x:.4f}')}
            
            <h2>🎯 Risk Contribution</h2>
            {risk_contrib.to_html(classes='', float_format=lambda x: f'{x:.4f}')}
            
            <h2>🔗 Correlation Matrix</h2>
            {corr.round(2).to_html(classes='')}
            
            <h2>📅 Time Statistics</h2>
            <div class="section">
                <table>
                    <tr><th>Period</th><th>Up</th><th>Down</th><th>Win Rate</th><th>Best</th><th>Worst</th></tr>
                    <tr>
                        <td>Daily</td>
                        <td>{metrics['days_up']}</td>
                        <td>{metrics['days_down']}</td>
                        <td>{metrics['days_up']/metrics['days_total']:.1%}</td>
                        <td class="positive">{metrics['best_day']:.2%}</td>
                        <td class="negative">{metrics['worst_day']:.2%}</td>
                    </tr>
                    <tr>
                        <td>Monthly</td>
                        <td>{metrics['months_up']}</td>
                        <td>{metrics['months_down']}</td>
                        <td>{metrics['win_rate_monthly']:.1%}</td>
                        <td class="positive">{metrics['best_month']:.2%}</td>
                        <td class="negative">{metrics['worst_month']:.2%}</td>
                    </tr>
                    <tr>
                        <td>Yearly</td>
                        <td>{metrics['years_up']}</td>
                        <td>{metrics['years_down']}</td>
                        <td>{metrics['years_up']/metrics['years_total']:.1%}</td>
                        <td class="positive">{metrics['best_year']:.2%}</td>
                        <td class="negative">{metrics['worst_year']:.2%}</td>
                    </tr>
                </table>
            </div>
            
            <div class="footer">
                <p>Generated by Portfolio Analysis Tool v2.1 | Methodology: Simple Returns, Geometric CAGR</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return html_file


def export_all_data(
    export_config: dict,
    equity: pd.Series,
    returns: pd.Series,
    metrics: dict,
    risk_contrib: pd.DataFrame,
    asset_metrics: pd.DataFrame,
    corr: pd.DataFrame,
    prices: pd.DataFrame,
    config: dict,
    data_range: tuple
) -> Optional[Path]:
    """
    Esporta tutti i dati nei formati richiesti.
    
    Returns:
        Path del file ZIP se creato, None altrimenti
    """
    
    if not export_config.get("enabled", False):
        print("\n📌 Export disabilitato. Per salvare i dati, imposta export.enabled = True")
        return None
    
    output_dir = create_output_dir(export_config.get("output_dir", "./output"))
    formats = export_config.get("formats", [])
    timestamp = get_timestamp()
    
    print(f"\n{'='*70}")
    print("EXPORTING DATA")
    print("="*70)
    
    exported_files = []
    
    # CSV
    if "csv" in formats:
        csv_files = export_to_csv(output_dir, equity, returns, metrics, 
                                   risk_contrib, asset_metrics, corr, prices)
        exported_files.extend(csv_files)
        print(f"  ✓ CSV files exported ({len(csv_files)} files)")
    
    # Excel
    if "xlsx" in formats:
        try:
            excel_file = export_to_excel(output_dir, equity, returns, metrics,
                                         risk_contrib, asset_metrics, corr, prices)
            exported_files.append(excel_file)
            print(f"  ✓ Excel file exported: {excel_file.name}")
        except ImportError:
            print("  ⚠ Excel export requires openpyxl: pip install openpyxl")
        except Exception as e:
            print(f"  ⚠ Excel export failed: {e}")
    
    # JSON
    if "json" in formats:
        json_file = export_to_json(output_dir, equity, returns, metrics,
                                   risk_contrib, asset_metrics, corr, config)
        exported_files.append(json_file)
        print(f"  ✓ JSON file exported: {json_file.name}")
    
    # Charts
    if export_config.get("export_charts", False):
        chart_format = export_config.get("chart_format", "png")
        chart_files = export_charts(output_dir, equity, returns, chart_format)
        exported_files.extend(chart_files)
        print(f"  ✓ Charts exported ({len(chart_files)} files, format: {chart_format})")
    
    # HTML Report
    if export_config.get("export_html_report", False):
        html_file = generate_html_report(output_dir, metrics, risk_contrib,
                                         asset_metrics, corr, config, data_range)
        exported_files.append(html_file)
        print(f"  ✓ HTML report exported: {html_file.name}")
    
    # Crea ZIP se richiesto
    zip_file = None
    if export_config.get("create_zip", True) and exported_files:
        zip_file = create_zip_archive(output_dir, exported_files, timestamp)
        print(f"\n  📦 ZIP archive created: {zip_file.name}")
        
        # Elimina file singoli se richiesto
        if export_config.get("delete_files_after_zip", True):
            for f in exported_files:
                try:
                    f.unlink()
                except Exception:
                    pass
            print(f"  🗑️  Individual files removed (kept only ZIP)")
    
    print(f"\n  📁 Output directory: {output_dir.absolute()}")
    if zip_file:
        print(f"  📦 Archive: {zip_file.name}")
        zip_size_mb = zip_file.stat().st_size / (1024 * 1024)
        print(f"  💾 Size: {zip_size_mb:.2f} MB")
    else:
        print(f"  📄 Total files exported: {len(exported_files)}")
    
    return zip_file


def create_zip_archive(output_dir: Path, files: list, timestamp: str) -> Path:
    """
    Crea un archivio ZIP con tutti i file esportati.
    
    Args:
        output_dir: Directory di output
        files: Lista di Path dei file da includere
        timestamp: Timestamp per il nome del file
    
    Returns:
        Path del file ZIP creato
    """
    zip_filename = output_dir / f"portfolio_analysis_{timestamp}.zip"
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in files:
            if file_path.exists():
                # Aggiungi il file con solo il nome (non il path completo)
                zipf.write(file_path, file_path.name)
    
    return zip_filename


def plot_results(equity: pd.Series, returns: pd.Series) -> None:
    """Genera grafici avanzati."""
    
    fig, axes = plt.subplots(3, 2, figsize=(14, 12))
    
    # 1. Equity Curve
    axes[0, 0].plot(equity.index, equity.values, color='blue', linewidth=1.5)
    axes[0, 0].set_title("Portfolio Equity Curve")
    axes[0, 0].set_ylabel("Value (base 1)")
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].axhline(y=1, color='gray', linestyle='--', alpha=0.5)
    
    # 2. Drawdown
    dd = equity / equity.cummax() - 1
    axes[0, 1].fill_between(dd.index, dd.values, 0, color='red', alpha=0.3)
    axes[0, 1].plot(dd.index, dd.values, color='red', linewidth=1)
    axes[0, 1].set_title("Drawdown")
    axes[0, 1].set_ylabel("Drawdown %")
    axes[0, 1].grid(True, alpha=0.3)
    
    # 3. Returns Distribution
    axes[1, 0].hist(returns, bins=50, color='steelblue', alpha=0.7, edgecolor='black')
    axes[1, 0].axvline(returns.mean(), color='green', linestyle='--', label=f'Mean: {returns.mean():.4f}')
    axes[1, 0].axvline(returns.quantile(0.05), color='red', linestyle='--', label=f'VaR 5%: {returns.quantile(0.05):.4f}')
    axes[1, 0].set_title("Daily Returns Distribution")
    axes[1, 0].set_xlabel("Return")
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # 4. Monthly Returns
    monthly = returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)
    colors = ['green' if x > 0 else 'red' for x in monthly]
    axes[1, 1].bar(monthly.index, monthly.values, color=colors, alpha=0.7, width=20)
    axes[1, 1].set_title("Monthly Returns")
    axes[1, 1].set_ylabel("Return %")
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].axhline(y=0, color='black', linewidth=0.5)
    
    # 5. Rolling Sharpe (1Y)
    rolling_window = 252
    if len(returns) > rolling_window:
        rolling_mean = returns.rolling(rolling_window).mean() * 252
        rolling_std = returns.rolling(rolling_window).std() * np.sqrt(252)
        rolling_sharpe = rolling_mean / rolling_std
        axes[2, 0].plot(rolling_sharpe.dropna(), color='purple', linewidth=1)
        axes[2, 0].axhline(y=0, color='gray', linestyle='--')
        axes[2, 0].axhline(y=1, color='green', linestyle='--', alpha=0.5, label='Sharpe=1')
    axes[2, 0].set_title("Rolling Sharpe Ratio (1Y)")
    axes[2, 0].set_ylabel("Sharpe")
    axes[2, 0].grid(True, alpha=0.3)
    axes[2, 0].legend()
    
    # 6. Rolling Volatility (1Y)
    if len(returns) > rolling_window:
        rolling_vol = returns.rolling(rolling_window).std() * np.sqrt(252)
        axes[2, 1].plot(rolling_vol.dropna(), color='orange', linewidth=1)
    axes[2, 1].set_title("Rolling Volatility (1Y, annualized)")
    axes[2, 1].set_ylabel("Volatility")
    axes[2, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Salva sempre il grafico
    import os
    os.makedirs('output', exist_ok=True)
    plt.savefig('output/portfolio_analysis.png', dpi=150, bbox_inches='tight')
    print("\n📊 Grafico salvato in: output/portfolio_analysis.png")
    
    # Show solo se esplicitamente richiesto (default: non mostrare)
    # Per mostrare il grafico: PORTFOLIO_SHOW_PLOT=1 python main.py
    if os.environ.get('PORTFOLIO_SHOW_PLOT') == '1':
        plt.show()
    else:
        plt.close()


# =========================
# MAIN ANALYSIS
# =========================

def download_data(tickers: list, start: str, end: Optional[str] = None) -> pd.DataFrame:
    """Scarica dati da Yahoo Finance."""
    data = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    
    if isinstance(data.columns, pd.MultiIndex):
        data = data["Close"]
    else:
        if len(tickers) == 1:
            data = data[["Close"]].rename(columns={"Close": tickers[0]})
        else:
            data = data["Close"]
    
    return data


def calculate_start_date(years: int, end_date: Optional[str] = None) -> str:
    """Calcola data inizio da anni di storico."""
    end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.now()
    start = end - timedelta(days=years * 365)
    return start.strftime("%Y-%m-%d")


def analyze_portfolio(config: dict) -> None:
    """Funzione principale."""
    
    # Config
    tickers = config["tickers"]
    weights = np.array(config["weights"], dtype=float)
    years = config.get("years_history", 5)
    end = config["end_date"]
    start = config["start_date"] or calculate_start_date(years, end)
    risk_free = config["risk_free_annual"]
    rebalance = config.get("rebalance")
    var_conf = config.get("var_confidence", 0.95)
    
    # Validazione
    if len(tickers) != len(weights):
        raise ValueError("Tickers e weights devono avere stessa lunghezza")
    
    weights = weights / weights.sum()  # Normalizza
    
    # Download
    print(f"Downloading data for {len(tickers)} tickers...")
    prices = download_data(tickers, start, end)
    
    # Validazione dati
    if prices.empty:
        raise RuntimeError("Nessun dato scaricato")
    
    missing = [t for t in tickers if t not in prices.columns]
    if missing:
        raise RuntimeError(f"Mancano dati per: {missing}")
    
    empty_cols = [c for c in prices.columns if prices[c].isna().all()]
    if empty_cols:
        raise RuntimeError(f"Ticker vuoti: {empty_cols}")
    
    prices = prices.dropna(how="all").ffill().dropna()
    
    print(f"Data range: {prices.index[0].date()} to {prices.index[-1].date()}")
    print(f"Trading days: {len(prices)}")
    
    # Simula portafoglio (CORRETTO con simple returns)
    equity, port_ret = simulate_portfolio_correct(prices, weights, rebalance)
    
    # Metriche complete
    metrics = calculate_all_metrics(equity, port_ret, risk_free, var_conf)
    
    # Simple returns per asset
    simple_ret = calculate_simple_returns(prices)
    
    # Asset metrics
    asset_cagr = {}
    asset_vol = {}
    for t in tickers:
        asset_eq = (1 + simple_ret[t]).cumprod()
        asset_cagr[t] = calculate_cagr_correct(asset_eq)
        asset_vol[t] = calculate_annualized_volatility(simple_ret[t])
    
    # Risk contribution (CORRETTA)
    risk_contrib = calculate_risk_contribution_correct(simple_ret, weights, tickers)
    
    # Asset summary
    asset_df = pd.DataFrame({
        "Weight": weights,
        "CAGR": [asset_cagr[t] for t in tickers],
        "Vol": [asset_vol[t] for t in tickers],
    }, index=tickers)
    
    # Merge con risk contribution
    asset_df = asset_df.join(risk_contrib[['CCR%']].rename(columns={'CCR%': 'RiskContrib%'}))
    
    # Correlazione
    corr = simple_ret.corr()
    
    # Output
    print_summary(metrics, risk_contrib, corr, asset_df)
    
    # Quant Analyst Critique (REGIME-AWARE)
    issues, regime_info = analyze_portfolio_issues(
        weights=weights,
        tickers=tickers,
        corr=corr,
        risk_contrib=risk_contrib,
        asset_metrics=asset_df,
        metrics=metrics
    )
    print_portfolio_critique(issues, regime_info)
    
    # Senior Portfolio Architect Analysis (Advanced)
    print_senior_architect_analysis(
        tickers=tickers,
        weights=weights,
        metrics=metrics,
        regime_info=regime_info,
        issues=issues,
        corr=corr
    )
    
    # Export data
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
    
    # Show plots (after export to avoid blocking)
    plot_results(equity, port_ret)


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    # Carica configurazione da config.py
    CONFIG = get_config()
    analyze_portfolio(CONFIG)
