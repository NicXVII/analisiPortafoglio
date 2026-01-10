"""
Temporal Decomposition Module
=============================
Decomposes portfolio performance across different time periods and market regimes.

This module provides:
- Crisis vs expansion performance separation
- Recovery analysis (time-to-recover, speed)
- Rolling metrics calculation
- Worst periods identification
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List


def calculate_temporal_decomposition(
    equity: pd.Series,
    returns: pd.Series,
    crisis_periods: list
) -> Dict[str, Any]:
    """
    FASE 3 OBBLIGATORIA: Decomposizione temporale delle performance.
    
    Separa l'analisi in:
    - Performance in-crisis
    - Performance in expansion
    - Recovery analysis (time-to-recover, speed)
    - Rolling metrics
    - Worst periods
    
    Args:
        equity: Portfolio equity curve
        returns: Portfolio daily returns
        crisis_periods: List of crisis period dictionaries with 'start', 'end', 'name'
    
    Returns:
        Dict con decomposizione completa
    """
    result = {
        "crisis_performance": [],
        "expansion_performance": {},
        "recovery_analysis": [],
        "rolling_metrics": {},
        "worst_periods": {},
    }
    
    if equity is None or len(equity) < 252:
        return result
    
    # === 1. PERFORMANCE IN-CRISIS vs EXPANSION ===
    crisis_days = set()
    
    # Allinea indici equity e returns
    common_idx = equity.index.intersection(returns.index)
    equity = equity.loc[common_idx]
    returns = returns.loc[common_idx]
    
    for crisis in crisis_periods:
        crisis_start = pd.to_datetime(crisis["start"])
        crisis_end = pd.to_datetime(crisis["end"])
        
        # Trova giorni in crisi
        mask = (equity.index >= crisis_start) & (equity.index <= crisis_end)
        crisis_idx = equity.index[mask]
        crisis_days.update(crisis_idx)
        
        if len(crisis_idx) >= 20:
            # Usa .reindex per gestire indici mancanti
            crisis_returns = returns.reindex(crisis_idx).dropna()
            crisis_equity = equity.reindex(crisis_idx).dropna()
            
            # Performance durante la crisi
            if len(crisis_equity) >= 2:
                crisis_return = (crisis_equity.iloc[-1] / crisis_equity.iloc[0]) - 1
                crisis_vol = crisis_returns.std() * np.sqrt(252) if len(crisis_returns) > 5 else np.nan
                crisis_dd = (crisis_equity / crisis_equity.cummax() - 1).min()
                
                result["crisis_performance"].append({
                    "name": crisis["name"],
                    "start": str(crisis_start.date()),
                    "end": str(crisis_end.date()),
                    "return": crisis_return,
                    "volatility": crisis_vol,
                    "max_drawdown": crisis_dd,
                    "days": len(crisis_idx),
                })
    
    # Performance in expansion (non-crisis)
    expansion_idx = equity.index.difference(pd.DatetimeIndex(list(crisis_days)))
    if len(expansion_idx) >= 20:
        expansion_returns = returns.reindex(expansion_idx).dropna()
        expansion_equity = equity.reindex(expansion_idx).dropna()
        
        # Calcola metriche expansion
        if len(expansion_equity) >= 2:
            # CAGR in expansion
            years_expansion = len(expansion_idx) / 252
            total_expansion_return = (expansion_equity.iloc[-1] / expansion_equity.iloc[0]) - 1
            cagr_expansion = (1 + total_expansion_return) ** (1 / years_expansion) - 1 if years_expansion > 0 else 0
            
            result["expansion_performance"] = {
                "days": len(expansion_idx),
                "years": years_expansion,
                "total_return": total_expansion_return,
                "cagr": cagr_expansion,
                "volatility": expansion_returns.std() * np.sqrt(252) if len(expansion_returns) > 1 else 0,
                "sharpe": (expansion_returns.mean() * 252 - 0.02) / (expansion_returns.std() * np.sqrt(252)) if expansion_returns.std() > 0 else 0,
            }
    
    # === 2. RECOVERY ANALYSIS ===
    drawdown = equity / equity.cummax() - 1
    
    for crisis in crisis_periods:
        crisis_end = pd.to_datetime(crisis["end"])
        
        # Trova il punto di minimo durante/dopo la crisi
        post_crisis_mask = equity.index >= crisis_end
        if post_crisis_mask.sum() < 20:
            continue
            
        # Trova quando ha recuperato (drawdown torna a 0)
        post_crisis_dd = drawdown.loc[post_crisis_mask]
        recovery_mask = post_crisis_dd >= 0  # Recovery = ritorno a nuovo ATH (0% drawdown)
        
        if recovery_mask.any():
            recovery_date = post_crisis_dd[recovery_mask].index[0]
            days_to_recover = (recovery_date - crisis_end).days
            
            # Calcola speed of recovery (return annualizzato durante recovery)
            recovery_period_equity = equity.loc[crisis_end:recovery_date]
            if len(recovery_period_equity) >= 2:
                recovery_return = (recovery_period_equity.iloc[-1] / recovery_period_equity.iloc[0]) - 1
                years_recovery = days_to_recover / 365.25
                recovery_cagr = (1 + recovery_return) ** (1 / years_recovery) - 1 if years_recovery > 0 else 0
            else:
                recovery_return = 0
                recovery_cagr = 0
            
            result["recovery_analysis"].append({
                "crisis": crisis["name"],
                "crisis_end": str(crisis_end.date()),
                "recovery_date": str(recovery_date.date()),
                "days_to_recover": days_to_recover,
                "months_to_recover": days_to_recover / 30.44,
                "recovery_return": recovery_return,
                "recovery_cagr": recovery_cagr,
            })
    
    # === 3. ROLLING METRICS ===
    # Rolling 3Y Sharpe
    if len(returns) >= 756:  # 3 anni
        rolling_3y_ret = returns.rolling(756).mean() * 252
        rolling_3y_vol = returns.rolling(756).std() * np.sqrt(252)
        rolling_3y_sharpe = (rolling_3y_ret - 0.02) / rolling_3y_vol
        
        result["rolling_metrics"]["sharpe_3y"] = {
            "current": rolling_3y_sharpe.iloc[-1] if not rolling_3y_sharpe.empty else np.nan,
            "min": rolling_3y_sharpe.min(),
            "max": rolling_3y_sharpe.max(),
            "median": rolling_3y_sharpe.median(),
        }
    
    # Rolling 5Y Sharpe
    if len(returns) >= 1260:  # 5 anni
        rolling_5y_ret = returns.rolling(1260).mean() * 252
        rolling_5y_vol = returns.rolling(1260).std() * np.sqrt(252)
        rolling_5y_sharpe = (rolling_5y_ret - 0.02) / rolling_5y_vol
        
        result["rolling_metrics"]["sharpe_5y"] = {
            "current": rolling_5y_sharpe.iloc[-1] if not rolling_5y_sharpe.empty else np.nan,
            "min": rolling_5y_sharpe.min(),
            "max": rolling_5y_sharpe.max(),
            "median": rolling_5y_sharpe.median(),
        }
    
    # === 4. WORST PERIODS ===
    # Worst 12M return
    if len(returns) >= 252:
        rolling_12m_ret = (1 + returns).rolling(252).apply(lambda x: x.prod() - 1, raw=True)
        worst_12m_idx = rolling_12m_ret.idxmin()
        result["worst_periods"]["worst_12m"] = {
            "return": rolling_12m_ret.min(),
            "end_date": str(worst_12m_idx.date()) if pd.notna(worst_12m_idx) else None,
        }
    
    # Worst 24M return
    if len(returns) >= 504:
        rolling_24m_ret = (1 + returns).rolling(504).apply(lambda x: x.prod() - 1, raw=True)
        worst_24m_idx = rolling_24m_ret.idxmin()
        result["worst_periods"]["worst_24m"] = {
            "return": rolling_24m_ret.min(),
            "end_date": str(worst_24m_idx.date()) if pd.notna(worst_24m_idx) else None,
        }
    
    return result
