"""
Data Module
===========
Funzioni per download e gestione dati.

Include:
- download_data: download dati da Yahoo Finance
- calculate_start_date: calcolo data inizio
- simulate_portfolio_correct: simulazione portafoglio
"""

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional, Tuple


# ================================================================================
# DATA DOWNLOAD
# ================================================================================

def download_data(tickers: list, start: str, end: Optional[str] = None) -> pd.DataFrame:
    """
    Scarica dati da Yahoo Finance.
    
    Args:
        tickers: Lista di ticker
        start: Data inizio (YYYY-MM-DD)
        end: Data fine (YYYY-MM-DD), default oggi
    
    Returns:
        DataFrame con prezzi di chiusura
    """
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
    """
    Calcola data inizio da anni di storico.
    
    Args:
        years: Numero di anni di storico
        end_date: Data fine (YYYY-MM-DD), default oggi
    
    Returns:
        Data inizio (YYYY-MM-DD)
    """
    end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.now()
    start = end - timedelta(days=years * 365)
    return start.strftime("%Y-%m-%d")


# ================================================================================
# PORTFOLIO SIMULATION
# ================================================================================

def simulate_portfolio_correct(
    prices: pd.DataFrame,
    weights: np.ndarray,
    rebalance: Optional[str] = None
) -> Tuple[pd.Series, pd.Series]:
    """
    Simula portafoglio con simple returns.
    
    Args:
        prices: DataFrame con prezzi
        weights: Array con pesi target
        rebalance: Frequenza ribilanciamento ('daily', 'monthly', 'quarterly', 'yearly', None)
    
    Returns:
        Tuple (equity_curve, portfolio_returns)
    """
    # Simple returns
    returns = prices.pct_change().dropna()
    
    if rebalance:
        # Portfolio con ribilanciamento periodico
        equity = simulate_rebalanced_portfolio(returns, weights, rebalance)
        # Calcola returns dalla equity curve
        port_ret = equity.pct_change().dropna()
    else:
        # Buy & Hold: ogni asset si muove indipendentemente
        # Simula come se comprasse units proporzionali ai pesi iniziali
        initial_prices = prices.iloc[0]
        units = weights / initial_prices
        
        # Valore portafoglio = somma (units * prices)
        portfolio_value = (prices * units).sum(axis=1)
        equity = portfolio_value / portfolio_value.iloc[0]
        port_ret = equity.pct_change().dropna()
    
    return equity, port_ret


def simulate_rebalanced_portfolio(
    returns: pd.DataFrame,
    weights: np.ndarray,
    rebalance: str
) -> pd.Series:
    """
    Simula portafoglio con ribilanciamento periodico.
    
    Args:
        returns: DataFrame con returns giornalieri
        weights: Array con pesi target
        rebalance: Frequenza ('daily', 'monthly', 'quarterly', 'yearly')
    
    Returns:
        Serie equity curve
    """
    # Mappa frequenza a pandas resampler
    freq_map = {
        'daily': 'D',
        'monthly': 'ME',
        'quarterly': 'QE',
        'yearly': 'YE'
    }
    
    if rebalance == 'daily':
        # Ribilanciamento giornaliero = weighted average returns
        port_ret = (returns * weights).sum(axis=1)
        equity = (1 + port_ret).cumprod()
    else:
        # Ribilanciamento periodico
        freq = freq_map.get(rebalance, 'ME')
        
        # Identifica date di ribilanciamento
        rebal_dates = returns.resample(freq).last().index
        
        equity_values = [1.0]
        current_weights = weights.copy()
        
        for i in range(len(returns)):
            date = returns.index[i]
            day_ret = returns.iloc[i].values
            
            # Calcola return portafoglio con pesi correnti
            port_day_ret = np.dot(current_weights, day_ret)
            new_equity = equity_values[-1] * (1 + port_day_ret)
            equity_values.append(new_equity)
            
            # Aggiorna pesi per drift
            current_weights = current_weights * (1 + day_ret)
            current_weights = current_weights / current_weights.sum()
            
            # Ribilancia se è data di rebalance
            if date in rebal_dates:
                current_weights = weights.copy()
        
        equity = pd.Series(equity_values[1:], index=returns.index)
    
    return equity


# ================================================================================
# RETURNS CALCULATION
# ================================================================================

def calculate_simple_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola simple returns.
    
    Args:
        prices: DataFrame con prezzi
    
    Returns:
        DataFrame con simple returns
    """
    return prices.pct_change().dropna()


def calculate_log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola log returns.
    
    Args:
        prices: DataFrame con prezzi
    
    Returns:
        DataFrame con log returns
    """
    return np.log(prices / prices.shift(1)).dropna()
