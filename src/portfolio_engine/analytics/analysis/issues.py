"""
Issue analysis helpers extracted from analysis_monolith (legacy).
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, List
from portfolio_engine.data.definitions.taxonomy import (
    CORE_GLOBAL_ETF,
    CORE_REGIONAL_ETF,
    CORE_DEVELOPED_ETF,
    EMERGING_ETF,
    SATELLITE_KEYWORDS,
    DEFAULT_GEO,
    GEO_EXPOSURE,
    calculate_geographic_exposure,
)
from portfolio_engine.analytics.portfolio_analysis.type_detection import (
    detect_portfolio_regime,
)
from portfolio_engine.analytics.regime import detect_market_regime
from portfolio_engine.analytics.portfolio_analysis.temporal import calculate_temporal_decomposition
from portfolio_engine.analytics.portfolio_analysis.resilience import (
    calculate_robustness_score, calculate_resilience_efficiency,
)
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
    # Nota: per portafogli equity growth, questo è un trade-off consapevole, NON una fragilità
    world_tickers = [t for t in tickers if t.upper().split('.')[0] in CORE_GLOBAL_ETF]
    regional_tickers = [t for t in tickers if t.upper().split('.')[0] in CORE_DEVELOPED_ETF]
    
    if world_tickers and regional_tickers:
        world_weight = sum(weights[tickers.index(t)] for t in world_tickers)
        regional_weight = sum(weights[tickers.index(t)] for t in regional_tickers)
        if world_weight > 0.30 and regional_weight > 0.20:
            warnings.append({
                "type": "WORLD_REGIONAL_OVERLAP",
                "severity": "informational",  # Non "structural" - è un trade-off consapevole
                "message": f"World ETF ({world_weight:.0%}) + Regional ({regional_weight:.0%}) = overlap, "
                          f"ma coerente con strategia equity growth multi-block."
            })
    
    # 4. Correlazione media
    # Nota: correlazioni alte sono FISIOLOGICHE in:
    # - Periodi di crisi sistemica
    # - Portafogli equity-only (tutti gli asset sono equity)
    if corr is not None and len(corr) > 2:
        corr_values = corr.values[np.triu_indices(len(corr), k=1)]
        avg_corr = np.mean(corr_values)
        if avg_corr > 0.80:
            warnings.append({
                "type": "HIGH_AVERAGE_CORRELATION",
                "severity": "informational",  # In equity-only, correlazione alta è NORMALE
                "message": f"Correlazione media {avg_corr:.2f}. Fisiologica per portafoglio equity-only, "
                          f"aumenta in stress sistemico."
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
    composition: Dict,
    prohibit_portfolio_actions: bool = False  # Rule 7: when INCONCLUSIVE, no portfolio actions
) -> List[str]:
    """
    Genera i bullet point motivazionali per il verdetto finale.
    
    Rule 7: IF prohibit_portfolio_actions=True (INCONCLUSIVE verdict):
            - Prohibit any portfolio restructuring recommendations
            - Only allow data/methodology improvement suggestions
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
    
    # Rule 7: When INCONCLUSIVE, no portfolio action recommendations
    if prohibit_portfolio_actions:
        # Only allow data/methodology improvement, not portfolio restructuring
        bullets.append("⚠️ Verdetto INCONCLUSO - migliorare qualità dati prima di qualsiasi giudizio")
    elif critical_issues:
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
    metrics: dict,
    data_start: str = None,
    data_end: str = None,
    equity_curve: pd.Series = None,
    returns: pd.Series = None
) -> Tuple[list, Dict[str, Any]]:
    """
    Analisi critica del portafoglio da prospettiva quant.
    TYPE-AWARE: applica soglie appropriate al tipo di portafoglio.
    REGIME-CONDITIONED: adatta valutazione al regime di mercato.
    
    Returns:
        Tuple di (lista criticità, regime_info)
    """
    # === FASE 1: DETECT PORTFOLIO TYPE ===
    regime_info = detect_portfolio_regime(weights, tickers, asset_metrics)
    regime = regime_info["regime"]
    thresholds = regime_info["thresholds"]
    composition = regime_info["composition"]
    
    # === FASE 2: DETECT MARKET REGIME (se date fornite) ===
    market_regime = None
    if data_start and data_end:
        max_dd = metrics.get('max_drawdown', 0)
        volatility = metrics.get('volatility', 0.20)
        avg_corr = corr.mean().mean() if corr is not None else None
        
        market_regime = detect_market_regime(
            start_date=data_start,
            end_date=data_end,
            max_drawdown=max_dd,
            volatility=volatility,
            avg_correlation=avg_corr
        )
        regime_info["market_regime"] = market_regime
        
        # Adatta soglie al regime di mercato
        if market_regime["primary_regime"] in ["INCLUDES_SYSTEMIC_CRISIS", "INCLUDES_TIGHTENING", "FULL_CYCLE"]:
            regime_thresholds = market_regime["regime_thresholds"]
            # Override soglie metriche con quelle regime-adjusted
            thresholds["min_sharpe"] = regime_thresholds.get("min_sharpe", thresholds["min_sharpe"])
            thresholds["min_sortino"] = regime_thresholds.get("min_sortino", thresholds["min_sortino"])
            thresholds["max_drawdown"] = regime_thresholds.get("max_drawdown_equity", thresholds["max_drawdown"])
            thresholds["regime_adjusted"] = True
            thresholds["regime_note"] = regime_thresholds.get("regime_note", "")
            regime_info["thresholds"] = thresholds
    
    # === FASE 3: DECOMPOSIZIONE TEMPORALE (OBBLIGATORIA) ===
    temporal_decomposition = None
    robustness_score = None
    resilience_efficiency = None
    if equity_curve is not None and returns is not None and market_regime:
        crisis_periods = market_regime.get("crisis_periods", [])
        temporal_decomposition = calculate_temporal_decomposition(
            equity=equity_curve,
            returns=returns,
            crisis_periods=crisis_periods
        )
        regime_info["temporal_decomposition"] = temporal_decomposition
        
        # Calcola robustness score basato su evidenza quantitativa
        robustness_score = calculate_robustness_score(
            temporal_decomposition=temporal_decomposition,
            metrics=metrics,
            crisis_periods=crisis_periods
        )
        regime_info["robustness_score"] = robustness_score
        
        # Calcola Resilience vs Efficiency (two-axis evaluation)
        # FIX INCONGRUENZA #5: passa composizione per evitare "DEFENSIVE" su 100% equity
        resilience_efficiency = calculate_resilience_efficiency(
            metrics=metrics,
            temporal_decomposition=temporal_decomposition,
            composition=composition
        )
        regime_info["resilience_efficiency"] = resilience_efficiency
    
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
    
    # In regime di crisi, correlazioni alte sono FISIOLOGICHE, non errore
    correlation_threshold = thresholds["max_correlation_satellite"]
    if market_regime and market_regime["primary_regime"] == "INCLUDES_SYSTEMIC_CRISIS":
        correlation_threshold = market_regime["regime_thresholds"].get("acceptable_correlation_spike", 0.90)
    
    high_corr_pairs = []
    for i, t1 in enumerate(tickers):
        for j, t2 in enumerate(tickers):
            if i < j:
                corr_val = corr.loc[t1, t2]
                if pd.notna(corr_val) and corr_val > correlation_threshold:
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
    
    # === 6. METRICHE RISK-ADJUSTED (REGIME-CONDITIONED) ===
    primary_metrics = thresholds.get("primary_metrics", ["sharpe", "sortino"])
    is_regime_adjusted = thresholds.get("regime_adjusted", False)
    regime_note = thresholds.get("regime_note", "")
    
    sharpe = metrics.get('sharpe', 0)
    min_sharpe = thresholds["min_sharpe"]
    
    # In regime di crisi, non penalizzare Sharpe basso
    if sharpe < min_sharpe:
        if is_regime_adjusted and market_regime and market_regime["primary_regime"] == "INCLUDES_SYSTEMIC_CRISIS":
            # Sharpe basso in crisi sistemica = INFORMATIVO, non criticità
            issues.append({
                "type": "LOW_SHARPE_REGIME_ADJUSTED",
                "severity": "ℹ️",
                "message": f"Sharpe Ratio {sharpe:.2f} compresso per presenza crisi sistemica nel periodo. "
                          f"Soglia regime-adjusted: {min_sharpe:.2f}. Fisiologico, non fragilità strutturale."
            })
        else:
            severity = "⚠️" if "sharpe" in primary_metrics else "ℹ️"
            issues.append({
                "type": "LOW_SHARPE",
                "severity": severity,
                "message": f"Sharpe Ratio {sharpe:.2f} < {min_sharpe:.2f} (soglia tipo {portfolio_type})."
            })
    
    sortino = metrics.get('sortino', 0)
    min_sortino = thresholds["min_sortino"]
    
    if sortino < min_sortino:
        if is_regime_adjusted and market_regime and market_regime["primary_regime"] == "INCLUDES_SYSTEMIC_CRISIS":
            issues.append({
                "type": "LOW_SORTINO_REGIME_ADJUSTED",
                "severity": "ℹ️",
                "message": f"Sortino Ratio {sortino:.2f} compresso per presenza crisi sistemica. "
                          f"Soglia regime-adjusted: {min_sortino:.2f}."
            })
        else:
            severity = "⚠️" if "sortino" in primary_metrics else "ℹ️"
            issues.append({
                "type": "LOW_SORTINO",
                "severity": severity,
                "message": f"Sortino Ratio {sortino:.2f} < {min_sortino:.2f}."
            })
    
    # === 7. DRAWDOWN (REGIME-CONDITIONED) ===
    max_dd = metrics.get('max_drawdown', 0)
    max_dd_peak = metrics.get('max_dd_peak', None)
    max_dd_threshold = thresholds["max_drawdown"]
    
    gfc_period = False
    covid_period = False
    if max_dd_peak and hasattr(max_dd_peak, 'year'):
        if 2008 <= max_dd_peak.year <= 2009:
            gfc_period = True
        elif max_dd_peak.year == 2020 and hasattr(max_dd_peak, 'month') and max_dd_peak.month <= 4:
            covid_period = True
    
    # Usa soglie regime-adjusted se disponibili
    if market_regime:
        if market_regime["includes_gfc"] or market_regime["includes_covid"]:
            max_dd_threshold = market_regime["regime_thresholds"].get("max_drawdown_equity", -0.55)
    
    if max_dd < max_dd_threshold:
        # In crisi sistemica, drawdown elevato è FISIOLOGICO
        if is_regime_adjusted and (gfc_period or covid_period or 
                                   (market_regime and market_regime["primary_regime"] == "INCLUDES_SYSTEMIC_CRISIS")):
            crisis_name = "GFC 2008-09" if gfc_period else ("COVID 2020" if covid_period else "crisi sistemica")
            issues.append({
                "type": "DRAWDOWN_REGIME_CONTEXT",
                "severity": "ℹ️",
                "message": f"Max Drawdown {max_dd:.1%} durante {crisis_name}. "
                          f"Coerente con benchmark crisi sistemica (-50% per 100% equity). "
                          f"Capacità di sopravvivenza confermata."
            })
        elif portfolio_type in ["DEFENSIVE", "BALANCED", "INCOME_YIELD", "RISK_PARITY"]:
            issues.append({
                "type": "HIGH_DRAWDOWN",
                "severity": "🚨",
                "message": f"Max Drawdown {max_dd:.1%} > {max_dd_threshold:.0%} atteso per tipo {portfolio_type}."
            })
        else:
            context_note = " (include GFC 2008-09)" if gfc_period else (" (include COVID 2020)" if covid_period else "")
            issues.append({
                "type": "HIGH_DRAWDOWN",
                "severity": "⚠️",
                "message": f"Max Drawdown {max_dd:.1%} > {max_dd_threshold:.0%} atteso per tipo {portfolio_type}{context_note}."
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
