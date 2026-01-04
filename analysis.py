"""
Portfolio Analysis Module
=========================
Funzioni per l'analisi del tipo di portafoglio e delle criticità.

Include:
- Portfolio type detection (10 tipi)
- Type-specific thresholds
- Issue analysis (criticità)
- False diversification detection
- Senior Architect analysis helpers
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, List

from taxonomy import (
    CORE_GLOBAL_ETF, CORE_DEVELOPED_ETF, CORE_REGIONAL_ETF,
    EMERGING_BROAD_ETF, EMERGING_ETF,
    SMALL_CAP_ETF, REIT_ETF, FACTOR_ETF, SECTOR_ETF,
    THEMATIC_PURE_ETF, EM_SINGLE_COUNTRY_ETF,
    BOND_ETF, GOLD_COMMODITY_ETF, DIVIDEND_INCOME_ETF, DEFENSIVE_ETF,
    SATELLITE_KEYWORDS, NON_CORE_STRUCTURAL_ETF,
    GEO_EXPOSURE, DEFAULT_GEO, ASSET_FUNCTION,
    get_asset_function, calculate_geographic_exposure, analyze_function_exposure
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
            n_regional_blocks = sum(1 for w in weights if w >= 0.07)
            portfolio_type = "EQUITY_GROWTH_DIVERSIFIED"
            confidence = 0.85
            type_reason = f"Equity growth diversificato: {n_regional_blocks} blocchi regionali, max position {max_weight:.0%}"
    
    # TACTICAL (default)
    else:
        portfolio_type = "TACTICAL"
        confidence = 0.50 + (0.1 * n_positions / 10)
        type_reason = "Pattern non classificabile, allocation tattica/opportunistica"
    
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
    }
    
    return thresholds_map.get(portfolio_type, default)


# ================================================================================
# BACKWARD COMPATIBILITY
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


# ================================================================================
# SENIOR ARCHITECT HELPERS
# ================================================================================

def detect_false_diversification(
    tickers: list, 
    weights: np.ndarray,
    geo_exposure: Dict[str, float],
    corr: pd.DataFrame
) -> List[Dict]:
    """
    Rileva FALSE DIVERSIFICAZIONI.
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
    
    # 2. EM sottopesato
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
                "message": f"World ETF ({world_weight:.0%}) + Regional ({regional_weight:.0%}) = overlap significativo."
            })
    
    # 4. Correlazione media troppo alta
    if corr is not None and len(corr) > 2:
        corr_values = corr.values[np.triu_indices(len(corr), k=1)]
        avg_corr = np.mean(corr_values)
        if avg_corr > 0.80:
            warnings.append({
                "type": "HIGH_AVERAGE_CORRELATION",
                "severity": "structural",
                "message": f"Correlazione media {avg_corr:.2f}. Diversificazione limitata in scenari di stress."
            })
        elif avg_corr > 0.70:
            warnings.append({
                "type": "MODERATE_CORRELATION",
                "severity": "informational",
                "message": f"Correlazione media {avg_corr:.2f}. Normale per portafoglio equity-only."
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
    
    usa_pct = geo_exposure.get("USA", 0)
    if 0.40 <= usa_pct <= 0.65:
        strengths.append(f"Esposizione USA bilanciata ({usa_pct:.0%}), non eccessivamente concentrato né sottopesato")
    
    em_pct = geo_exposure.get("EM", 0)
    if em_pct >= 0.10:
        strengths.append(f"Esposizione EM adeguata ({em_pct:.0%}) per catturare crescita mercati emergenti")
    
    n_functions = len([f for f, w in function_exposure.items() if w > 0.05])
    if n_functions >= 4:
        strengths.append(f"{n_functions} funzioni economiche distinte → portafoglio multi-driver")
    
    if weights is not None and len(weights) > 0:
        max_pos = float(max(weights))
    else:
        max_pos = composition.get("details", {}).get("max_position", 0)
    if max_pos > 0 and max_pos < 0.25:
        strengths.append(f"Nessuna posizione dominante (max {max_pos:.0%}) → rischio idiosincratico contenuto")
    
    real_assets = function_exposure.get("REAL_ASSETS", 0)
    if real_assets >= 0.05:
        strengths.append(f"Presenza real assets ({real_assets:.0%}) per diversificazione e inflation hedge")
    
    factor_tilt = function_exposure.get("FACTOR_TILT", 0)
    if factor_tilt >= 0.08:
        strengths.append(f"Factor tilt ({factor_tilt:.0%}) per catturare premi fattoriali (size/value/momentum)")
    
    sortino = metrics.get("sortino", 0)
    if sortino > 0.70:
        strengths.append(f"Sortino Ratio {sortino:.2f} → gestione efficiente del downside risk")
    
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
    """
    bullets = []
    
    critical_issues = [i for i in issues if i.get("severity") == "🚨"]
    structural_issues = [i for i in issues if i.get("severity") in ["⚠️", "structural"]]
    
    bullets.append(f"Portafoglio classificato come {portfolio_type} con struttura coerente rispetto agli obiettivi impliciti")
    
    if strengths:
        bullets.append(strengths[0])
    
    if structural_issues:
        bullets.append(f"Trade-off identificato: {structural_issues[0].get('message', '')[:100]}...")
    elif len(strengths) > 1:
        bullets.append(strengths[1])
    
    cagr = metrics.get("cagr", 0)
    sortino = metrics.get("sortino", 0)
    max_dd = metrics.get("max_drawdown", 0)
    bullets.append(f"Metriche di lungo periodo: CAGR {cagr:.1%}, Sortino {sortino:.2f}, Max DD {max_dd:.0%}")
    
    if critical_issues:
        bullets.append("Criticità strutturali richiedono revisione prima di implementazione")
    elif structural_issues:
        bullets.append("Costruzione solida con trade-off consapevoli e documentati")
    else:
        bullets.append("Struttura robusta per orizzonti multi-decennali")
    
    return bullets[:5]


# ================================================================================
# PORTFOLIO ISSUE ANALYSIS
# ================================================================================

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
    satellite_tickers_set = set(regime_info.get("satellite_tickers", []))
    core_tickers_set = set(regime_info.get("core_tickers", []))
    
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
                    
                    t1_is_core = t1 in core_extended or any(kw in t1.upper() for kw in CORE_GLOBAL_ETF + CORE_REGIONAL_ETF + EMERGING_ETF)
                    t2_is_core = t2 in core_extended or any(kw in t2.upper() for kw in CORE_GLOBAL_ETF + CORE_REGIONAL_ETF + EMERGING_ETF)
                    
                    if t1_is_core or t2_is_core:
                        continue
                    
                    t1_is_sat = t1 in satellite_tickers_set or any(kw in t1.upper() for kw in SATELLITE_KEYWORDS)
                    t2_is_sat = t2 in satellite_tickers_set or any(kw in t2.upper() for kw in SATELLITE_KEYWORDS)
                    
                    if t1_is_sat and t2_is_sat:
                        high_corr_pairs.append((t1, t2, corr_val, combined_weight))
    
    for t1, t2, corr_val, comb_w in high_corr_pairs:
        reit_data_center_pair = (
            (any(kw in t1.upper() for kw in REIT_ETF) and any(kw in t2.upper() for kw in ['SRVR', 'DATA', 'CLOUD'])) or
            (any(kw in t2.upper() for kw in REIT_ETF) and any(kw in t1.upper() for kw in ['SRVR', 'DATA', 'CLOUD']))
        )
        
        if reit_data_center_pair:
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
    
    is_core_global = any(kw in max_ticker.upper() for kw in CORE_GLOBAL_ETF)
    high_concentration_types = ["EQUITY_CORE_DRIVEN", "EQUITY_GROWTH_CORE", "BARBELL_THEMATIC"]
    
    if max_weight > thresholds["max_single_position"]:
        if is_core_global and portfolio_type in high_concentration_types:
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
            
            if is_core and ratio <= thresholds["core_risk_contrib_ratio_max"]:
                continue
            
            if ratio > 1.8:
                issues.append({
                    "type": "RISK_INEFFICIENCY",
                    "severity": "⚠️",
                    "message": f"{t}: contribuisce {rc:.1%} al rischio con {w:.1%} del capitale. "
                              f"Rapporto {ratio:.1f}x → verifica se intenzionale."
                })
    
    # === 5. OVERLAP TRA ETF ===
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
    
    # 5b. OVERLAP IMPLICITI
    world_etfs = [t for t in tickers if any(w in t.upper() for w in ['VT', 'VWCE', 'ACWI', 'IWDA', 'SWDA', 'URTH'])]
    usa_etfs = [t for t in tickers if any(u in t.upper() for u in ['IVV', 'VOO', 'SPY', 'IWM', 'CSPX', 'SXR8', 'QQQ'])]
    
    if world_etfs and usa_etfs:
        world_w = sum(weights[i] for i, t in enumerate(tickers) if t in world_etfs)
        usa_w = sum(weights[i] for i, t in enumerate(tickers) if t in usa_etfs)
        implicit_usa_overlap = world_w * 0.60
        issues.append({
            "type": "IMPLICIT_OVERLAP",
            "severity": "ℹ️",
            "message": f"Overlap implicito USA: {', '.join(world_etfs)} contiene ~60% USA. "
                      f"Con {', '.join(usa_etfs)} ({usa_w:.0%}), esposizione USA effettiva ~{(implicit_usa_overlap + usa_w):.0%}."
        })
    
    # === 6. METRICHE RISK-ADJUSTED ===
    primary_metrics = thresholds.get("primary_metrics", ["sharpe", "sortino"])
    
    sharpe = metrics.get('sharpe', 0)
    if sharpe < thresholds["min_sharpe"]:
        severity = "⚠️" if "sharpe" in primary_metrics else "ℹ️"
        issues.append({
            "type": "LOW_SHARPE",
            "severity": severity,
            "message": f"Sharpe Ratio {sharpe:.2f} < {thresholds['min_sharpe']:.2f} (soglia tipo {portfolio_type})."
        })
    
    sortino = metrics.get('sortino', 0)
    if sortino < thresholds["min_sortino"]:
        severity = "⚠️" if "sortino" in primary_metrics else "ℹ️"
        issues.append({
            "type": "LOW_SORTINO",
            "severity": severity,
            "message": f"Sortino Ratio {sortino:.2f} < {thresholds['min_sortino']:.2f}."
        })
    
    # === 7. DRAWDOWN ===
    max_dd = metrics.get('max_drawdown', 0)
    max_dd_peak = metrics.get('max_dd_peak', None)
    
    gfc_period = False
    if max_dd_peak and hasattr(max_dd_peak, 'year'):
        if 2008 <= max_dd_peak.year <= 2009:
            gfc_period = True
    
    if max_dd < thresholds["max_drawdown"]:
        if portfolio_type in ["DEFENSIVE", "BALANCED", "INCOME_YIELD", "RISK_PARITY"]:
            severity = "🚨"
        elif gfc_period and portfolio_type in ["EQUITY_GROWTH_CORE", "EQUITY_GROWTH_DIVERSIFIED", 
                                                "EQUITY_CORE_DRIVEN", "EQUITY_MULTI_BLOCK"]:
            severity = "ℹ️"
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
    
    regime_info["trade_offs"] = trade_offs
    
    return issues, regime_info
