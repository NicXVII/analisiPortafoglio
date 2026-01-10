"""
Portfolio Type Detection Module
===============================
Identifies portfolio type based on composition and assigns type-specific thresholds.

Contains:
- detect_portfolio_type: 10-type classification with mutual exclusion
- get_type_thresholds: Type-specific validation thresholds
- detect_portfolio_regime: Backward compatibility wrapper
- get_regime_thresholds: Backward compatibility wrapper

Portfolio Types (priority order):
1. INCOME_YIELD             - Dividend ETF >40% or income focus
2. DEFENSIVE                - Equity <40%, bond+gold >40%
3. BALANCED                 - Bond 20-50%, equity 50-80%
4. RISK_PARITY              - Multi-asset, balanced risk contribution
5. EQUITY_MULTI_BLOCK       - Equity only, balanced weights
6. EQUITY_CORE_DRIVEN       - World index >50%, bond <15%
7. BARBELL_THEMATIC         - Core >40% + satellite >20%
8. EQUITY_GROWTH_CORE       - 100% equity, single asset >45%
9. EQUITY_GROWTH_DIVERSIFIED- 100% equity, multi-core, none >45%
10. TACTICAL                - Default, no clear pattern
"""

import numpy as np
import pandas as pd
from typing import Dict, Any

from portfolio_engine.data.definitions.taxonomy import (
    CORE_GLOBAL_ETF, CORE_REGIONAL_ETF,
    EMERGING_ETF,
    SMALL_CAP_ETF, REIT_ETF, FACTOR_ETF, SECTOR_ETF,
    THEMATIC_PURE_ETF, EM_SINGLE_COUNTRY_ETF,
    BOND_ETF, GOLD_COMMODITY_ETF, DIVIDEND_INCOME_ETF,
)


# ================================================================================
# PORTFOLIO TYPE DETECTION
# ================================================================================

def detect_portfolio_type(
    weights: np.ndarray,
    tickers: list,
    asset_metrics: pd.DataFrame
) -> Dict[str, Any]:
    """
    IDENTIFICAZIONE TIPO PORTAFOGLIO - 10 TIPI
    
    Analizza composizione e assegna tipo con regole specifiche.
    BUCKET MUTUAMENTE ESCLUSIVI - ogni ticker è assegnato a UN solo bucket.
    
    Tipi (in ordine di priorità nel check):
    1. INCOME_YIELD             - Dividend ETF >40% o income focus
    2. DEFENSIVE                - Equity <40%, bond+gold >40%
    3. BALANCED                 - Bond 20-50%, equity 50-80%
    4. RISK_PARITY              - Multi-asset con bond, risk contribution equilibrata
    5. EQUITY_MULTI_BLOCK       - Equity only, pesi equilibrati
    6. EQUITY_CORE_DRIVEN       - World index >50%, bond <15%
    7. BARBELL_THEMATIC         - Core >40% + satellite >20%
    8. EQUITY_GROWTH_CORE       - 100% equity, singolo asset >45%
    9. EQUITY_GROWTH_DIVERSIFIED- 100% equity, multi-core, nessun >45%
    10. TACTICAL                - Default, nessun pattern
    
    Returns:
        Dict con tipo, confidence, thresholds, composition
    """
    # === STEP 1: CLASSIFICA OGNI ASSET (BUCKET MUTUAMENTE ESCLUSIVI) ===
    # Ogni ticker va in UN SOLO bucket
    
    # Bucket primari (esclusivi)
    core_global_weight = 0.0
    core_regional_weight = 0.0
    small_cap_weight = 0.0
    reit_weight = 0.0
    factor_weight = 0.0
    sector_weight = 0.0
    thematic_pure_weight = 0.0
    em_broad_weight = 0.0
    em_single_country_weight = 0.0
    bond_weight = 0.0
    gold_commodity_weight = 0.0
    dividend_income_weight = 0.0
    other_equity_weight = 0.0
    
    # Liste per tracking
    core_global_tickers = []
    core_regional_tickers = []
    small_cap_tickers = []
    reit_tickers = []
    factor_tickers = []
    sector_tickers = []
    thematic_pure_tickers = []
    em_broad_tickers = []
    em_single_country_tickers = []
    bond_tickers = []
    gold_commodity_tickers = []
    income_tickers = []
    other_tickers = []
    
    for i, t in enumerate(tickers):
        ticker_upper = t.upper()
        ticker_clean = ticker_upper.split('.')[0]
        w = weights[i]
        
        # === CLASSIFICAZIONE MUTUAMENTE ESCLUSIVA (ordine di priorità) ===
        # Prima checka i tipi più specifici, poi quelli più generali
        
        if any(kw == ticker_clean for kw in BOND_ETF) or any(kw in ticker_upper for kw in BOND_ETF):
            bond_weight += w
            bond_tickers.append(t)
        elif any(kw == ticker_clean for kw in GOLD_COMMODITY_ETF) or any(kw in ticker_upper for kw in GOLD_COMMODITY_ETF):
            gold_commodity_weight += w
            gold_commodity_tickers.append(t)
        elif any(kw == ticker_clean for kw in DIVIDEND_INCOME_ETF) or any(kw in ticker_upper for kw in DIVIDEND_INCOME_ETF):
            dividend_income_weight += w
            income_tickers.append(t)
        elif any(kw == ticker_clean for kw in CORE_GLOBAL_ETF) or any(kw in ticker_upper for kw in CORE_GLOBAL_ETF):
            core_global_weight += w
            core_global_tickers.append(t)
        elif any(kw == ticker_clean for kw in THEMATIC_PURE_ETF) or any(kw in ticker_upper for kw in THEMATIC_PURE_ETF):
            thematic_pure_weight += w
            thematic_pure_tickers.append(t)
        elif any(kw == ticker_clean for kw in SMALL_CAP_ETF) or any(kw in ticker_upper for kw in SMALL_CAP_ETF):
            small_cap_weight += w
            small_cap_tickers.append(t)
        elif any(kw == ticker_clean for kw in REIT_ETF) or any(kw in ticker_upper for kw in REIT_ETF):
            reit_weight += w
            reit_tickers.append(t)
        elif any(kw == ticker_clean for kw in FACTOR_ETF) or any(kw in ticker_upper for kw in FACTOR_ETF):
            factor_weight += w
            factor_tickers.append(t)
        elif any(kw == ticker_clean for kw in SECTOR_ETF) or any(kw in ticker_upper for kw in SECTOR_ETF):
            sector_weight += w
            sector_tickers.append(t)
        elif any(kw == ticker_clean for kw in EM_SINGLE_COUNTRY_ETF) or any(kw in ticker_upper for kw in EM_SINGLE_COUNTRY_ETF):
            em_single_country_weight += w
            em_single_country_tickers.append(t)
        elif any(kw == ticker_clean for kw in EMERGING_ETF) or any(kw in ticker_upper for kw in EMERGING_ETF):
            em_broad_weight += w
            em_broad_tickers.append(t)
        elif any(kw == ticker_clean for kw in CORE_REGIONAL_ETF) or any(kw in ticker_upper for kw in CORE_REGIONAL_ETF):
            core_regional_weight += w
            core_regional_tickers.append(t)
        else:
            # Default: classifica per volatilità se disponibile
            if t in asset_metrics.index and 'Vol' in asset_metrics.columns:
                vol = asset_metrics.loc[t, 'Vol']
                if vol > 0.35:
                    thematic_pure_weight += w
                    thematic_pure_tickers.append(t)
                elif vol > 0.25:
                    sector_weight += w
                    sector_tickers.append(t)
                else:
                    other_equity_weight += w
                    other_tickers.append(t)
            else:
                other_equity_weight += w
                other_tickers.append(t)
    
    # === CALCOLI AGGREGATI (non overlapping) ===
    total_emerging = em_broad_weight + em_single_country_weight
    structural_noncore_weight = small_cap_weight + reit_weight + factor_weight + sector_weight
    
    # Total Equity = somma di tutti i bucket equity (MUTUAMENTE ESCLUSIVI)
    total_equity = (core_global_weight + core_regional_weight + 
                   small_cap_weight + reit_weight + factor_weight + sector_weight +
                   thematic_pure_weight + em_broad_weight + em_single_country_weight +
                   dividend_income_weight + other_equity_weight)
    
    total_core = core_global_weight + core_regional_weight
    total_defensive_assets = bond_weight + gold_commodity_weight
    
    # Satellite = solo tematici puri (NON include settoriali/fattoriali)
    true_satellite_weight = thematic_pure_weight
    
    max_weight = weights.max()
    max_ticker = tickers[weights.argmax()]
    n_positions = len(weights[weights > 0.01])
    
    # === SANITY CHECK ===
    total_allocated = (core_global_weight + core_regional_weight + 
                      small_cap_weight + reit_weight + factor_weight + sector_weight +
                      thematic_pure_weight + em_broad_weight + em_single_country_weight +
                      dividend_income_weight + other_equity_weight +
                      bond_weight + gold_commodity_weight)
    
    # Verifica che somma = 1.0 (tolleranza per floating point)
    if abs(total_allocated - 1.0) > 0.01:
        print(f"⚠️ WARNING: Somma bucket = {total_allocated:.2%}, atteso 100%")
    
    # === STEP 2: IDENTIFICA TIPO ===
    portfolio_type = "TACTICAL"
    confidence = 0.50
    type_reason = "Nessun pattern chiaro identificato"
    
    # INCOME_YIELD
    if dividend_income_weight >= 0.40:
        portfolio_type = "INCOME_YIELD"
        confidence = min(0.95, 0.6 + dividend_income_weight)
        type_reason = f"Dividend/Income ETF {dividend_income_weight:.0%} dominante"
    elif dividend_income_weight >= 0.25 and bond_weight >= 0.15:
        portfolio_type = "INCOME_YIELD"
        confidence = 0.80
        type_reason = f"Income focus: dividendi {dividend_income_weight:.0%} + bond {bond_weight:.0%}"
    
    # DEFENSIVE
    elif total_equity < 0.40 and total_defensive_assets >= 0.40:
        portfolio_type = "DEFENSIVE"
        confidence = min(0.95, 0.5 + total_defensive_assets)
        type_reason = f"Capital preservation: equity {total_equity:.0%}, defensive {total_defensive_assets:.0%}"
    elif total_equity < 0.50 and bond_weight >= 0.35:
        portfolio_type = "DEFENSIVE"
        confidence = 0.85
        type_reason = f"Bond-heavy defensive: bond {bond_weight:.0%}, equity {total_equity:.0%}"
    
    # BALANCED
    elif 0.20 <= bond_weight <= 0.50 and 0.50 <= total_equity <= 0.80:
        portfolio_type = "BALANCED"
        confidence = 0.90
        type_reason = f"Multi-asset balanced: equity {total_equity:.0%}, bond {bond_weight:.0%}"
    elif 0.15 <= bond_weight < 0.20 and total_equity <= 0.75:
        portfolio_type = "BALANCED"
        confidence = 0.75
        type_reason = f"Quasi-balanced: equity {total_equity:.0%}, bond {bond_weight:.0%}"
    
    # RISK_PARITY vs EQUITY_MULTI_BLOCK
    elif max_weight < 0.25 and n_positions >= 5:
        weight_std = np.std(weights[weights > 0.01])
        avg_weight = np.mean(weights[weights > 0.01])
        cv = weight_std / avg_weight if avg_weight > 0 else 99
        
        if cv < 0.5:
            if bond_weight >= 0.10 and total_equity < 0.85:
                portfolio_type = "RISK_PARITY"
                confidence = min(0.90, 0.6 + (1 - cv))
                type_reason = f"Risk Parity multi-asset: equity {total_equity:.0%}, bond {bond_weight:.0%}, CV {cv:.2f}"
            else:
                portfolio_type = "EQUITY_MULTI_BLOCK"
                confidence = min(0.90, 0.6 + (1 - cv))
                type_reason = f"Equity multi-block: {n_positions} posizioni equilibrate, max {max_weight:.0%}, CV {cv:.2f}"
    
    # EQUITY_CORE_DRIVEN
    elif core_global_weight >= 0.50 and bond_weight < 0.15:
        portfolio_type = "EQUITY_CORE_DRIVEN"
        confidence = min(0.95, 0.5 + core_global_weight)
        type_reason = f"Core globale dominante: {core_global_weight:.0%} in world index"
        if any(kw in max_ticker.upper() for kw in ['VWCE', 'VT', 'IWDA', 'ACWI']):
            confidence = min(0.98, confidence + 0.05)
            type_reason += f" ({max_ticker} è All-World diversificato)"
    
    # BARBELL_THEMATIC
    elif total_core >= 0.40 and true_satellite_weight >= 0.20:
        portfolio_type = "BARBELL_THEMATIC"
        confidence = 0.85
        type_reason = f"Barbell: core {total_core:.0%} + satellite tematici {true_satellite_weight:.0%}"
    elif total_core >= 0.50 and true_satellite_weight >= 0.15:
        portfolio_type = "BARBELL_THEMATIC"
        confidence = 0.80
        type_reason = f"Core-satellite: core {total_core:.0%}, tematici {true_satellite_weight:.0%}"
    
    # EQUITY_GROWTH
    elif total_equity >= 0.90 and bond_weight < 0.05:
        if max_weight > 0.45:
            portfolio_type = "EQUITY_GROWTH_CORE"
            confidence = 0.85
            type_reason = f"Equity growth concentrato: {max_ticker} al {max_weight:.0%} (beta dominante)"
        else:
            n_tilts = sum(1 for w in weights if w >= 0.07)
            portfolio_type = "EQUITY_GROWTH_DIVERSIFIED"
            confidence = 0.85
            type_reason = f"Global core + {n_tilts} regional tilts (con overlap), max position {max_weight:.0%}"
    
    # === NUOVE CATEGORIE (Framework Istituzionale) ===
    
    # LOW_BETA_DIVERSIFIED - Portafoglio con beta strutturalmente basso
    # NON usare TACTICAL come fallback per portafogli conservativi
    elif total_equity >= 0.60 and total_equity <= 0.85 and bond_weight >= 0.10:
        # Multi-asset con bias conservativo
        portfolio_type = "STRUCTURED_MULTI_ASSET"
        confidence = 0.80
        type_reason = f"Multi-asset strutturato: equity {total_equity:.0%}, bond {bond_weight:.0%}"
    
    # CORE_SATELLITES_STATIC - Core stabile + satellite definiti
    elif total_core >= 0.50 and (structural_noncore_weight + thematic_pure_weight) > 0.10:
        portfolio_type = "CORE_SATELLITES_STATIC"
        confidence = 0.80
        type_reason = f"Core {total_core:.0%} + satellites {structural_noncore_weight + thematic_pure_weight:.0%} (statico)"
    
    # TACTICAL (default) - USO LIMITATO
    # Un portafoglio può essere TACTICAL solo se presenta almeno 2 di:
    # - market timing, rotazione esplicita, leverage, esposizioni dinamiche, beta > 1 persistente
    # In assenza → vietato usare TACTICAL come fallback
    else:
        # Verifica criteri TACTICAL (almeno 2 devono essere veri)
        tactical_criteria = 0
        
        # Criterio 1: Alta volatilità media degli asset (proxy per beta > 1)
        if t in asset_metrics.index and 'Vol' in asset_metrics.columns:
            avg_vol = asset_metrics['Vol'].mean()
            if avg_vol > 0.25:  # Vol > 25% suggerisce esposizioni aggressive
                tactical_criteria += 1
        
        # Criterio 2: Alta concentrazione settoriale/tematica
        if sector_weight + thematic_pure_weight > 0.30:
            tactical_criteria += 1
        
        # Criterio 3: Factor tilts significativi
        if factor_weight > 0.15:
            tactical_criteria += 1
        
        # Criterio 4: EM single country exposure (scommessa specifica)
        if em_single_country_weight > 0.10:
            tactical_criteria += 1
        
        # Criterio 5: Assenza di core (nessun anchor stabile)
        if total_core < 0.20:
            tactical_criteria += 1
        
        if tactical_criteria >= 2:
            portfolio_type = "TACTICAL"
            confidence = 0.50 + (0.1 * tactical_criteria / 5)
            type_reason = f"TACTICAL: {tactical_criteria} criteri soddisfatti (settoriale/factor/timing)"
        else:
            # Fallback: STRUCTURED_MULTI_ASSET o LOW_BETA_DIVERSIFIED
            if total_defensive_assets > 0.15:
                portfolio_type = "STRUCTURED_MULTI_ASSET"
                confidence = 0.65
                type_reason = f"Multi-asset: equity {total_equity:.0%}, defensive {total_defensive_assets:.0%}"
            else:
                portfolio_type = "LOW_BETA_DIVERSIFIED"
                confidence = 0.60
                type_reason = f"Equity diversificato a basso beta: {n_positions} posizioni, max {max_weight:.0%}"
    
    # === STEP 3: GET THRESHOLDS ===
    thresholds = get_type_thresholds(portfolio_type)
    
    # === STEP 4: COMPONI RISULTATO ===
    return {
        "type": portfolio_type,
        "confidence": confidence,
        "reason": type_reason,
        "thresholds": thresholds,
        "composition": {
            "core_global": core_global_weight,
            "core_regional": core_regional_weight,
            "emerging_broad": em_broad_weight,
            "em_single_country": em_single_country_weight,
            "total_emerging": total_emerging,
            "total_core": total_core,
            "small_cap": small_cap_weight,
            "reit": reit_weight,
            "factor": factor_weight,
            "sector": sector_weight,
            "structural_noncore": structural_noncore_weight,
            "thematic_pure": thematic_pure_weight,
            "true_satellite": true_satellite_weight,
            "bond": bond_weight,
            "gold_commodity": gold_commodity_weight,
            "dividend_income": dividend_income_weight,
            "other_equity": other_equity_weight,
            "total_equity": total_equity,
            "total_defensive": total_defensive_assets,
            "total_allocated": total_allocated,
        },
        "details": {
            "core_global_tickers": core_global_tickers,
            "core_regional_tickers": core_regional_tickers,
            "small_cap_tickers": small_cap_tickers,
            "reit_tickers": reit_tickers,
            "factor_tickers": factor_tickers,
            "sector_tickers": sector_tickers,
            "thematic_pure_tickers": thematic_pure_tickers,
            "em_broad_tickers": em_broad_tickers,
            "em_single_country_tickers": em_single_country_tickers,
            "bond_tickers": bond_tickers,
            "gold_commodity_tickers": gold_commodity_tickers,
            "income_tickers": income_tickers,
            "other_tickers": other_tickers,
            "n_positions": n_positions,
            "max_position": max_weight,
            "max_ticker": max_ticker,
        }
    }


# ================================================================================
# TYPE-SPECIFIC THRESHOLDS
# ================================================================================

def get_type_thresholds(portfolio_type: str) -> Dict[str, Any]:
    """
    SOGLIE TYPE-SPECIFIC per validazione.
    """
    
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
        "primary_metrics": ["sharpe", "sortino", "max_drawdown"],
        "secondary_metrics": ["cagr", "calmar"],
        "description": "Allocation tattica - standard validation",
    }
    
    thresholds_map = {
        "EQUITY_GROWTH_CORE": {
            "max_single_position": 0.60,
            "max_top3": 0.80,
            "max_satellite_single": 0.15,
            "max_satellite_total": 0.35,
            "max_correlation_satellite": 0.75,
            "max_drawdown": -0.45,
            "min_sharpe": 0.55,
            "min_sortino": 0.75,
            "min_calmar": 0.15,
            "core_risk_contrib_ratio_max": 2.0,
            "primary_metrics": ["cagr", "sortino"],
            "secondary_metrics": ["sharpe", "max_drawdown"],
            "description": "Equity Growth Core - concentrazione su singolo beta driver",
        },
        "EQUITY_GROWTH_DIVERSIFIED": {
            "max_single_position": 0.45,
            "max_top3": 0.70,
            "max_satellite_single": 0.15,
            "max_satellite_total": 0.40,
            "max_correlation_satellite": 0.75,
            "max_drawdown": -0.40,
            "min_sharpe": 0.55,
            "min_sortino": 0.80,
            "min_calmar": 0.25,
            "core_risk_contrib_ratio_max": 1.8,
            "primary_metrics": ["cagr", "sortino"],
            "secondary_metrics": ["sharpe", "max_drawdown"],
            "description": "Equity Growth Diversified - multi-core regionale",
        },
        "EQUITY_GROWTH": {
            "max_single_position": 0.35,
            "max_top3": 0.65,
            "max_satellite_single": 0.15,
            "max_satellite_total": 0.40,
            "max_correlation_satellite": 0.75,
            "max_drawdown": -0.40,
            "min_sharpe": 0.60,
            "min_sortino": 0.80,
            "min_calmar": 0.25,
            "core_risk_contrib_ratio_max": 1.8,
            "primary_metrics": ["cagr", "sortino"],
            "secondary_metrics": ["sharpe", "max_drawdown"],
            "description": "Equity Growth - focus rendimento, tolleranza rischio alta",
        },
        "EQUITY_CORE_DRIVEN": {
            "max_single_position": 0.85,
            "max_top3": 0.95,
            "max_satellite_single": 0.10,
            "max_satellite_total": 0.25,
            "max_correlation_satellite": 0.70,
            "max_drawdown": -0.35,
            "min_sharpe": 0.70,
            "min_sortino": 0.90,
            "min_calmar": 0.35,
            "core_risk_contrib_ratio_max": 1.3,
            "primary_metrics": ["sharpe", "cagr"],
            "secondary_metrics": ["sortino", "max_drawdown"],
            "description": "Equity Core-Driven - World Index dominante",
        },
        "EQUITY_MULTI_BLOCK": {
            "max_single_position": 0.25,
            "max_top3": 0.60,
            "max_satellite_single": 0.15,
            "max_satellite_total": 0.30,
            "max_noncore_structural": 0.40,
            "max_correlation_satellite": 0.75,
            "max_drawdown": -0.40,
            "min_sharpe": 0.40,
            "min_sortino": 0.55,
            "min_calmar": 0.20,
            "core_risk_contrib_ratio_max": 1.5,
            "primary_metrics": ["cagr", "sortino", "risk_distribution"],
            "secondary_metrics": ["sharpe", "max_drawdown"],
            "description": "Equity Multi-Block - core + fattoriali + settori + tematici",
        },
        "BALANCED": {
            "max_single_position": 0.45,
            "max_top3": 0.65,
            "max_satellite_single": 0.05,
            "max_satellite_total": 0.10,
            "max_correlation_satellite": 0.55,
            "max_drawdown": -0.18,
            "min_sharpe": 0.55,
            "min_sortino": 0.75,
            "min_calmar": 0.45,
            "core_risk_contrib_ratio_max": 1.3,
            "primary_metrics": ["sharpe", "max_drawdown", "calmar"],
            "secondary_metrics": ["cagr", "sortino"],
            "description": "Balanced - focus risk-adjusted, drawdown contenuto",
        },
        "DEFENSIVE": {
            "max_single_position": 0.50,
            "max_top3": 0.70,
            "max_satellite_single": 0.03,
            "max_satellite_total": 0.05,
            "max_correlation_satellite": 0.45,
            "max_drawdown": -0.12,
            "min_sharpe": 0.40,
            "min_sortino": 0.50,
            "min_calmar": 0.60,
            "core_risk_contrib_ratio_max": 1.2,
            "primary_metrics": ["max_drawdown", "calmar", "volatility"],
            "secondary_metrics": ["sharpe", "sortino"],
            "description": "Defensive - preservazione capitale",
        },
        "INCOME_YIELD": {
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
            "primary_metrics": ["yield_proxy", "sortino", "max_drawdown"],
            "secondary_metrics": ["cagr", "sharpe"],
            "description": "Income/Yield - focus dividendi",
        },
        "BARBELL_THEMATIC": {
            "max_single_position": 0.65,
            "max_top3": 0.85,
            "max_satellite_single": 0.15,
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
        },
        "RISK_PARITY": {
            "max_single_position": 0.30,
            "max_top3": 0.60,
            "max_satellite_single": 0.10,
            "max_satellite_total": 0.20,
            "max_correlation_satellite": 0.50,
            "max_drawdown": -0.15,
            "min_sharpe": 0.50,
            "min_sortino": 0.65,
            "min_calmar": 0.50,
            "core_risk_contrib_ratio_max": 1.15,
            "primary_metrics": ["sharpe", "risk_contribution_balance"],
            "secondary_metrics": ["cagr", "max_drawdown"],
            "description": "Risk Parity multi-asset - risk contribution equilibrata",
        },
        # === NUOVE CATEGORIE (Framework Istituzionale) ===
        "STRUCTURED_MULTI_ASSET": {
            "max_single_position": 0.40,
            "max_top3": 0.70,
            "max_satellite_single": 0.08,
            "max_satellite_total": 0.15,
            "max_correlation_satellite": 0.60,
            "max_drawdown": -0.25,
            "min_sharpe": 0.45,
            "min_sortino": 0.60,
            "min_calmar": 0.35,
            "core_risk_contrib_ratio_max": 1.4,
            "primary_metrics": ["sharpe", "max_drawdown", "volatility"],
            "secondary_metrics": ["cagr", "sortino"],
            "description": "Multi-asset strutturato - allocazione strategica stabile",
        },
        "CORE_SATELLITES_STATIC": {
            "max_single_position": 0.55,
            "max_top3": 0.75,
            "max_satellite_single": 0.12,
            "max_satellite_total": 0.30,
            "max_correlation_satellite": 0.65,
            "max_drawdown": -0.35,
            "min_sharpe": 0.50,
            "min_sortino": 0.70,
            "min_calmar": 0.25,
            "core_risk_contrib_ratio_max": 1.5,
            "primary_metrics": ["cagr", "sharpe"],
            "secondary_metrics": ["sortino", "max_drawdown"],
            "description": "Core + Satellites statico - allocazione buy&hold con tilt",
        },
        "LOW_BETA_DIVERSIFIED": {
            "max_single_position": 0.35,
            "max_top3": 0.65,
            "max_satellite_single": 0.10,
            "max_satellite_total": 0.25,
            "max_correlation_satellite": 0.55,
            "max_drawdown": -0.20,
            "min_sharpe": 0.40,  # Sharpe basso OK per low-beta
            "min_sortino": 0.55,
            "min_calmar": 0.40,
            "core_risk_contrib_ratio_max": 1.3,
            "primary_metrics": ["max_drawdown", "volatility", "calmar"],
            "secondary_metrics": ["sharpe", "cagr"],
            "description": "Low-beta diversificato - profilo conservativo strutturale",
        },
    }
    
    return thresholds_map.get(portfolio_type, default)


# ================================================================================
# BACKWARD COMPATIBILITY WRAPPERS
# ================================================================================

def detect_portfolio_regime(
    weights: np.ndarray,
    tickers: list,
    asset_metrics: pd.DataFrame
) -> Dict[str, Any]:
    """
    BACKWARD COMPATIBILITY - Wrapper per detect_portfolio_type.
    """
    type_info = detect_portfolio_type(weights, tickers, asset_metrics)
    
    type_to_regime = {
        "EQUITY_GROWTH_CORE": "EQUITY_CORE_DRIVEN",
        "EQUITY_GROWTH_DIVERSIFIED": "EQUITY_CORE_DRIVEN",
        "EQUITY_GROWTH": "EQUITY_CORE_DRIVEN",
        "EQUITY_MULTI_BLOCK": "EQUITY_CORE_DRIVEN",
        "EQUITY_CORE_DRIVEN": "EQUITY_CORE_DRIVEN",
        "BALANCED": "MULTI_ASSET_BALANCED",
        "DEFENSIVE": "MULTI_ASSET_BALANCED",
        "INCOME_YIELD": "MULTI_ASSET_BALANCED",
        "BARBELL_THEMATIC": "BARBELL_THEMATIC",
        "RISK_PARITY": "RISK_PARITY",
        "TACTICAL": "TACTICAL_ALLOCATION",
    }
    
    # Costruisci liste di ticker combinate per backward compatibility
    core_tickers = (type_info["details"].get("core_global_tickers", []) + 
                   type_info["details"].get("core_regional_tickers", []))
    satellite_tickers = type_info["details"].get("thematic_pure_tickers", [])
    
    return {
        "regime": type_to_regime.get(type_info["type"], "TACTICAL_ALLOCATION"),
        "portfolio_type": type_info["type"],
        "confidence": type_info["confidence"],
        "thresholds": type_info["thresholds"],
        "composition": type_info["composition"],
        "core_tickers": core_tickers,
        "satellite_tickers": satellite_tickers,
        "type_reason": type_info["reason"],
        "details": type_info["details"],  # passa tutti i dettagli
    }


def get_regime_thresholds(regime: str) -> Dict[str, Any]:
    """BACKWARD COMPATIBILITY - Wrapper per get_type_thresholds."""
    regime_to_type = {
        "EQUITY_CORE_DRIVEN": "EQUITY_CORE_DRIVEN",
        "MULTI_ASSET_BALANCED": "BALANCED",
        "BARBELL_THEMATIC": "BARBELL_THEMATIC",
        "RISK_PARITY": "RISK_PARITY",
        "TACTICAL_ALLOCATION": "TACTICAL",
    }
    return get_type_thresholds(regime_to_type.get(regime, "TACTICAL"))
