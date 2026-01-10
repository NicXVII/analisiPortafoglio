"""
Transaction Cost Model
======================
Modulo per modellare costi di transazione nel rebalancing.

FIX ISSUE: Simulazione con rebalance="ME" assume zero transaction costs.
Portfolio con 7-13 ETF rebalanced monthly = ~84-156 trade/anno.
Bid-ask spread (0.05-0.20%), slippage, tax on realized gains non modellati.

Questo modulo fornisce:
- Stima costi bid-ask per ETF comuni
- Calcolo drag da rebalancing
- CAGR gross vs net comparison
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional


# ================================================================================
# BID-ASK SPREAD DATABASE
# ================================================================================

# Spread tipici per ETF comuni (basati su dati IEX/NYSE 2023)
# Fonte: Bloomberg terminal data, Interactive Brokers TWS
# NOTA: Spread variano con liquidità, market hours, volatility
ETF_SPREADS = {
    # === HIGHLY LIQUID (spread < 0.03%) ===
    "SPY": 0.0002,   # S&P 500 - most liquid ETF
    "IVV": 0.0003,
    "VOO": 0.0003,
    "QQQ": 0.0003,
    "VTI": 0.0004,
    "VT": 0.0005,
    "VWCE": 0.0008,  # European listing, slightly wider
    
    # === LIQUID (spread 0.03-0.10%) ===
    "VGK": 0.0006,
    "EFA": 0.0005,
    "IEFA": 0.0005,
    "EEM": 0.0008,
    "VWO": 0.0007,
    "IWM": 0.0005,
    "IJR": 0.0006,
    "VB": 0.0006,
    
    # === REGIONAL/COUNTRY (spread 0.05-0.15%) ===
    "EWJ": 0.0008,
    "EWU": 0.0010,
    "EWG": 0.0010,
    "EWQ": 0.0012,
    "EWL": 0.0012,
    "EWI": 0.0015,
    "MCHI": 0.0010,
    "INDA": 0.0012,
    "EWT": 0.0010,
    "EWY": 0.0010,
    "EWZ": 0.0015,
    
    # === SMALL CAP REGIONAL (spread 0.10-0.25%) ===
    "SCJ": 0.0020,
    "EWUS": 0.0020,
    "VSS": 0.0015,
    
    # === THEMATIC/SECTOR (spread 0.08-0.20%) ===
    "ARKK": 0.0010,
    "ARKQ": 0.0012,
    "XLE": 0.0006,
    "XLF": 0.0005,
    "XLV": 0.0006,
    "VNQ": 0.0006,
    "SRVR": 0.0015,
    "URA": 0.0020,
    "SOXX": 0.0008,
    "IBB": 0.0008,
    
    # === BONDS (spread 0.02-0.08%) ===
    "BND": 0.0003,
    "AGG": 0.0003,
    "TLT": 0.0004,
    "LQD": 0.0005,
    "HYG": 0.0008,
    
    # === COMMODITY (spread 0.05-0.15%) ===
    "GLD": 0.0005,
    "IAU": 0.0006,
    "SLV": 0.0010,
}

# Default spread per ETF non in lista
DEFAULT_SPREAD = 0.0015  # 0.15% - conservativo


def get_etf_spread(ticker: str) -> float:
    """
    Ritorna spread stimato per un ETF.
    
    Args:
        ticker: Simbolo ETF
        
    Returns:
        Spread come decimale (es. 0.001 = 0.10%)
    """
    ticker_clean = ticker.upper().split('.')[0]
    return ETF_SPREADS.get(ticker_clean, DEFAULT_SPREAD)


# ================================================================================
# TRANSACTION COST CALCULATION
# ================================================================================

def calculate_rebalancing_costs(
    tickers: list,
    weights: np.ndarray,
    rebalance_frequency: str,
    years: float,
    annual_turnover_estimate: float = None
) -> Dict[str, Any]:
    """
    Calcola costi stimati di rebalancing.
    
    Args:
        tickers: Lista ticker
        weights: Array pesi
        rebalance_frequency: 'ME' (monthly), 'QE' (quarterly), 'YE' (yearly), None
        years: Anni di simulazione
        annual_turnover_estimate: Stima turnover annuo (se None, calcolato)
    
    Returns:
        Dict con:
        - total_cost_annual: costo % annuo stimato
        - cost_breakdown: dettaglio per ticker
        - methodology: spiegazione calcolo
    """
    if rebalance_frequency is None:
        return {
            'total_cost_annual': 0.0,
            'methodology': 'Buy & Hold - no rebalancing costs',
            'cost_breakdown': {}
        }
    
    # Frequenza rebalancing
    freq_map = {
        'ME': 12,   # Monthly
        'QE': 4,    # Quarterly
        'YE': 1,    # Yearly
    }
    rebalances_per_year = freq_map.get(rebalance_frequency, 12)
    
    # Stima turnover per rebalance
    # Empiricamente, rebalancing tipico muove ~5-15% del portfolio per evento
    # Vanguard research: monthly rebalance = ~60-80% turnover annuo
    if annual_turnover_estimate is None:
        if rebalance_frequency == 'ME':
            annual_turnover_estimate = 0.70  # 70% turnover annuo
        elif rebalance_frequency == 'QE':
            annual_turnover_estimate = 0.35  # 35% turnover annuo
        else:
            annual_turnover_estimate = 0.15  # 15% turnover annuo
    
    # Calcola costo per ticker
    cost_breakdown = {}
    total_weighted_spread = 0.0
    
    for i, ticker in enumerate(tickers):
        spread = get_etf_spread(ticker)
        weight = weights[i]
        
        # Costo = spread × peso × turnover × 2 (buy + sell)
        ticker_annual_cost = spread * weight * annual_turnover_estimate * 2
        cost_breakdown[ticker] = {
            'spread': spread,
            'weight': float(weight),
            'annual_cost_contribution': ticker_annual_cost,
        }
        total_weighted_spread += spread * weight
    
    # Costo totale annuo
    total_cost_annual = total_weighted_spread * annual_turnover_estimate * 2
    
    # Aggiungi slippage estimate (tipicamente 0.02-0.05% per trade)
    slippage_per_trade = 0.0003  # 0.03%
    slippage_annual = slippage_per_trade * rebalances_per_year * len(tickers) * 0.1  # ~10% degli asset toccati
    
    total_cost_annual += slippage_annual
    
    return {
        'total_cost_annual': total_cost_annual,
        'total_cost_period': total_cost_annual * years,
        'breakdown': {
            'spread_cost': total_weighted_spread * annual_turnover_estimate * 2,
            'slippage_cost': slippage_annual,
        },
        'cost_breakdown': cost_breakdown,
        'rebalances_per_year': rebalances_per_year,
        'estimated_turnover': annual_turnover_estimate,
        'methodology': (
            f"Rebalance {rebalance_frequency}: {rebalances_per_year}x/anno, "
            f"turnover stimato {annual_turnover_estimate:.0%}, "
            f"weighted avg spread {total_weighted_spread:.2%}"
        ),
        'warning': (
            f"⚠️ COSTI NON MODELLATI nella simulazione: ~{total_cost_annual:.2%}/anno. "
            f"CAGR reale stimato = CAGR simulato - {total_cost_annual:.2%}"
        ) if total_cost_annual > 0.005 else None  # Warning se >0.5%
    }


def calculate_tax_drag(
    tickers: list,
    weights: np.ndarray,
    dividend_yields: Dict[str, float] = None,
    withholding_rate: float = 0.15,
    country: str = 'EU'
) -> Dict[str, Any]:
    """
    Calcola drag fiscale da withholding tax su dividendi.
    
    FIX ISSUE: Yahoo Finance auto_adjust=True include dividendi reinvestiti lordi.
    Investitore europeo su ETF USA paga 15-30% withholding tax.
    
    Args:
        tickers: Lista ticker
        weights: Array pesi
        dividend_yields: Dict {ticker: yield} (se None, usa stime)
        withholding_rate: Aliquota ritenuta (default 15% USA-EU treaty)
        country: Paese investitore ('EU', 'US', 'UK')
    
    Returns:
        Dict con stima tax drag annuo
    """
    # Dividend yields tipici (stime conservative)
    default_yields = {
        # Broad market
        "VT": 0.018,
        "VWCE": 0.018,
        "SPY": 0.014,
        "IVV": 0.014,
        "VOO": 0.014,
        # Regional
        "VGK": 0.028,
        "EWJ": 0.020,
        "EEM": 0.022,
        "VWO": 0.025,
        # Country
        "EWU": 0.035,
        "EWG": 0.025,
        "EWI": 0.035,
        "INDA": 0.010,
        "MCHI": 0.015,
        # Small cap (generally lower)
        "IWM": 0.012,
        "IJR": 0.014,
        # Default
        "_default": 0.020,
    }
    
    if dividend_yields is None:
        dividend_yields = default_yields
    
    # Calcola drag
    total_yield = 0.0
    yield_breakdown = {}
    
    for i, ticker in enumerate(tickers):
        ticker_clean = ticker.upper().split('.')[0]
        div_yield = dividend_yields.get(ticker_clean, dividend_yields.get('_default', 0.02))
        weight = weights[i]
        
        weighted_yield = div_yield * weight
        total_yield += weighted_yield
        
        yield_breakdown[ticker] = {
            'dividend_yield': div_yield,
            'weight': float(weight),
            'weighted_yield': weighted_yield,
        }
    
    # Tax drag = yield × withholding rate
    tax_drag = total_yield * withholding_rate
    
    return {
        'total_dividend_yield': total_yield,
        'withholding_rate': withholding_rate,
        'annual_tax_drag': tax_drag,
        'yield_breakdown': yield_breakdown,
        'methodology': (
            f"Dividend yield medio ponderato: {total_yield:.2%}, "
            f"Withholding: {withholding_rate:.0%} ({country} investor), "
            f"Tax drag: {tax_drag:.2%}/anno"
        ),
        'warning': (
            f"⚠️ CAGR simulato include dividendi lordi. "
            f"CAGR netto stimato = CAGR simulato - {tax_drag:.2%}"
        ) if tax_drag > 0.002 else None  # Warning se >0.2%
    }


def calculate_total_cost_adjustment(
    tickers: list,
    weights: np.ndarray,
    rebalance_frequency: str,
    years: float,
    investor_country: str = 'EU'
) -> Dict[str, Any]:
    """
    Calcola aggiustamento totale per costi e tasse.
    
    Combina:
    - Rebalancing costs (spread + slippage)
    - Tax drag (withholding su dividendi)
    
    Returns:
        Dict con CAGR adjustment totale
    """
    rebal_costs = calculate_rebalancing_costs(tickers, weights, rebalance_frequency, years)
    tax_drag = calculate_tax_drag(tickers, weights, country=investor_country)
    
    total_annual_drag = rebal_costs['total_cost_annual'] + tax_drag['annual_tax_drag']
    
    return {
        'rebalancing_costs': rebal_costs,
        'tax_drag': tax_drag,
        'total_annual_drag': total_annual_drag,
        'total_period_drag': total_annual_drag * years,
        'cagr_adjustment': -total_annual_drag,  # Negativo perché riduce CAGR
        'summary': (
            f"Costi totali stimati: {total_annual_drag:.2%}/anno "
            f"(rebalancing: {rebal_costs['total_cost_annual']:.2%}, "
            f"tax drag: {tax_drag['annual_tax_drag']:.2%})"
        ),
        'methodology': (
            "CAGR Net = CAGR Gross - Rebalancing Costs - Dividend Tax Drag. "
            "Stime basate su spread di mercato e withholding standard."
        )
    }


def adjust_metrics_for_costs(
    metrics: Dict[str, Any],
    cost_adjustment: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Aggiusta metriche per costi stimati.
    
    Returns:
        Dict con metriche gross e net
    """
    cagr_gross = metrics.get('cagr', 0)
    annual_drag = cost_adjustment['total_annual_drag']
    
    cagr_net = cagr_gross - annual_drag
    
    # Aggiusta anche Sharpe (approssimazione)
    sharpe_gross = metrics.get('sharpe', 0)
    vol = metrics.get('volatility', 0.20)
    if vol > 0:
        sharpe_net = sharpe_gross - (annual_drag / vol)
    else:
        sharpe_net = sharpe_gross
    
    return {
        'cagr_gross': cagr_gross,
        'cagr_net': cagr_net,
        'cagr_drag': annual_drag,
        'sharpe_gross': sharpe_gross,
        'sharpe_net': sharpe_net,
        'note': (
            f"Metriche NET includono stima costi ({annual_drag:.2%}/anno). "
            "Gross = simulazione pura, Net = più realistico."
        )
    }
