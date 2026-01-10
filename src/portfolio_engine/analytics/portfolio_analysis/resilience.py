"""
Resilience & Robustness Module
==============================
Calculates portfolio resilience and efficiency scores.

This module provides:
- Robustness score calculation (comparative ranking)
- Resilience vs Efficiency two-axis evaluation
- Quadrant classification (Optimal, Growth, Defensive, Needs Review)
"""

import numpy as np
from typing import Dict, Any


def calculate_robustness_score(
    temporal_decomposition: Dict,
    metrics: Dict,
    crisis_periods: list
) -> Dict[str, Any]:
    """
    Calcola un ROBUSTNESS SCORE per comparazione RELATIVA tra portafogli.
    
    ⚠️ DISCLAIMER METODOLOGICO (OVERFITTING RISK):
    Questo score è uno strumento di RANKING RELATIVO, NON un giudizio assoluto.
    - Utile per: confrontare portafogli alternativi con stessa metodologia
    - NON utile per: predire performance futura o dichiarare "buono/cattivo"
    
    Un score 70/100 non significa "buono al 70%", ma "70 punti relativi
    basati su criteri storici che potrebbero non ripetersi".
    
    ⚠️ OVERFITTING WARNING:
    Le soglie usate (es. recovery < 12 mesi = +25 punti) sono calibrate su dati
    storici IN-SAMPLE. NON c'è walk-forward validation. Performance future
    potrebbe essere significativamente peggiore del backtest.
    
    Criteri (tutti retrospettivi):
    1. Recovery speed: tempo medio di recupero post-crisi (25 pts)
    2. Rolling consistency: varianza delle rolling metrics (25 pts)
    3. Worst period survival: worst 12M/24M non catastrofici (25 pts)
    4. Crisis behavior: compounding through cycles (25 pts)
    
    Args:
        temporal_decomposition: Dict from calculate_temporal_decomposition
        metrics: Dict with calculated portfolio metrics
        crisis_periods: List of crisis period dictionaries
    
    Returns:
        Dict con score e breakdown (for comparative use only)
    """
    score = 0
    max_score = 100
    breakdown = []
    
    # 1. RECOVERY SPEED (25 punti)
    recovery_analysis = temporal_decomposition.get("recovery_analysis", [])
    if recovery_analysis:
        avg_recovery_months = np.mean([r["months_to_recover"] for r in recovery_analysis])
        if avg_recovery_months < 12:
            score += 25
            breakdown.append(f"Recovery veloce: media {avg_recovery_months:.0f} mesi (+25)")
        elif avg_recovery_months < 24:
            score += 15
            breakdown.append(f"Recovery moderato: media {avg_recovery_months:.0f} mesi (+15)")
        elif avg_recovery_months < 36:
            score += 8
            breakdown.append(f"Recovery lento: media {avg_recovery_months:.0f} mesi (+8)")
        else:
            breakdown.append(f"Recovery molto lento: media {avg_recovery_months:.0f} mesi (+0)")
    
    # 2. ROLLING CONSISTENCY (25 punti)
    rolling_metrics = temporal_decomposition.get("rolling_metrics", {})
    if "sharpe_3y" in rolling_metrics:
        sharpe_3y = rolling_metrics["sharpe_3y"]
        min_sharpe = sharpe_3y.get("min", -999)
        median_sharpe = sharpe_3y.get("median", 0)
        
        if min_sharpe > 0:
            score += 25
            breakdown.append(f"Rolling Sharpe 3Y sempre positivo (min {min_sharpe:.2f}) (+25)")
        elif min_sharpe > -0.5:
            score += 15
            breakdown.append(f"Rolling Sharpe 3Y modesto (min {min_sharpe:.2f}) (+15)")
        else:
            score += 5
            breakdown.append(f"Rolling Sharpe 3Y volatile (min {min_sharpe:.2f}) (+5)")
    
    # 3. WORST PERIOD SURVIVAL (25 punti)
    worst_periods = temporal_decomposition.get("worst_periods", {})
    if "worst_12m" in worst_periods:
        worst_12m = worst_periods["worst_12m"].get("return", -1)
        if worst_12m > -0.30:
            score += 25
            breakdown.append(f"Worst 12M contenuto ({worst_12m:.0%}) (+25)")
        elif worst_12m > -0.45:
            score += 15
            breakdown.append(f"Worst 12M moderato ({worst_12m:.0%}) (+15)")
        else:
            score += 5
            breakdown.append(f"Worst 12M severo ({worst_12m:.0%}) (+5)")
    
    # 4. COMPOUNDING LONG-TERM (25 punti)
    cagr = metrics.get("cagr", 0)
    if cagr > 0.08:
        score += 25
        breakdown.append(f"CAGR solido ({cagr:.1%}) attraverso i cicli (+25)")
    elif cagr > 0.05:
        score += 15
        breakdown.append(f"CAGR moderato ({cagr:.1%}) (+15)")
    elif cagr > 0.02:
        score += 8
        breakdown.append(f"CAGR basso ({cagr:.1%}) (+8)")
    else:
        breakdown.append(f"CAGR insufficiente ({cagr:.1%}) (+0)")
    
    # Determina verdict basato su score
    # Nota: 50/100 è threshold minimo per "accettabile" (equivalente a sufficienza)
    if score >= 80:
        verdict = "ROBUSTO"
        verdict_detail = "Strutturalmente robusto attraverso i cicli"
    elif score >= 65:
        verdict = "COERENTE"
        verdict_detail = "Coerente con il regime, trade-off accettabili"
    elif score >= 50:
        verdict = "ACCETTABILE"
        verdict_detail = "Accettabile con riserve - margine limitato"
    else:
        verdict = "DA_RIVEDERE"
        verdict_detail = "Score insufficiente (<50) - richiede revisione strutturale"
    
    return {
        "score": score,
        "max_score": max_score,
        "percentage": score / max_score * 100,
        "breakdown": breakdown,
        "verdict": verdict,
        "verdict_detail": verdict_detail,
    }


def calculate_resilience_efficiency(
    metrics: Dict,
    temporal_decomposition: Dict = None,
    composition: Dict = None
) -> Dict[str, Any]:
    """
    Calcola RESILIENZA ed EFFICIENZA come due assi INDIPENDENTI.
    
    ⚠️ METODOLOGIA:
    Un portafoglio può essere:
    - Alta Efficienza, Bassa Resilienza: buon rendimento/rischio ma fragile in crisi
    - Bassa Efficienza, Alta Resilienza: sotto-performa ma resiste a stress
    - Alta/Alta: eccellente (raro)
    - Bassa/Bassa: problematico
    
    FIX INCONGRUENZA #5: "DEFENSIVE_ORIENTED" non può essere assegnato a 100% equity.
    Un portafoglio 100% equity non è mai "difensivo" per definizione.
    
    EFFICIENZA: rendimento per unità di rischio (Sharpe, Sortino, Calmar)
    RESILIENZA: capacità di resistere a stress (Max DD, Recovery, Worst periods)
    
    Args:
        metrics: Dict con metriche calcolate
        temporal_decomposition: Dict con analisi temporale
        composition: Dict con composizione asset (per controllare se 100% equity)
    
    Returns:
        Dict con efficiency_score, resilience_score, quadrant, trade_off_analysis
    """
    # === EFFICIENCY AXIS (0-100) ===
    # Basato su risk-adjusted metrics
    efficiency_score = 0
    efficiency_breakdown = []
    
    sharpe = metrics.get('sharpe', 0)
    sortino = metrics.get('sortino', 0)
    calmar = metrics.get('calmar', 0)
    
    # Sharpe (0-35 punti)
    if sharpe >= 1.0:
        efficiency_score += 35
        efficiency_breakdown.append(f"Sharpe {sharpe:.2f} ≥ 1.0 (+35)")
    elif sharpe >= 0.7:
        efficiency_score += 25
        efficiency_breakdown.append(f"Sharpe {sharpe:.2f} ≥ 0.7 (+25)")
    elif sharpe >= 0.5:
        efficiency_score += 15
        efficiency_breakdown.append(f"Sharpe {sharpe:.2f} ≥ 0.5 (+15)")
    elif sharpe > 0:
        efficiency_score += 5
        efficiency_breakdown.append(f"Sharpe {sharpe:.2f} positivo (+5)")
    else:
        efficiency_breakdown.append(f"Sharpe {sharpe:.2f} negativo (+0)")
    
    # Sortino (0-35 punti) - premia protezione downside
    if sortino >= 1.5:
        efficiency_score += 35
        efficiency_breakdown.append(f"Sortino {sortino:.2f} ≥ 1.5 (+35)")
    elif sortino >= 1.0:
        efficiency_score += 25
        efficiency_breakdown.append(f"Sortino {sortino:.2f} ≥ 1.0 (+25)")
    elif sortino >= 0.6:
        efficiency_score += 15
        efficiency_breakdown.append(f"Sortino {sortino:.2f} ≥ 0.6 (+15)")
    elif sortino > 0:
        efficiency_score += 5
        efficiency_breakdown.append(f"Sortino {sortino:.2f} positivo (+5)")
    
    # Calmar (0-30 punti) - return/maxDD
    if calmar >= 0.5:
        efficiency_score += 30
        efficiency_breakdown.append(f"Calmar {calmar:.2f} ≥ 0.5 (+30)")
    elif calmar >= 0.3:
        efficiency_score += 20
        efficiency_breakdown.append(f"Calmar {calmar:.2f} ≥ 0.3 (+20)")
    elif calmar >= 0.15:
        efficiency_score += 10
        efficiency_breakdown.append(f"Calmar {calmar:.2f} ≥ 0.15 (+10)")
    
    # === RESILIENCE AXIS (0-100) ===
    # Basato su comportamento in stress
    resilience_score = 0
    resilience_breakdown = []
    
    max_dd = metrics.get('max_drawdown', -0.50)
    
    # Max Drawdown (0-40 punti)
    if max_dd > -0.15:
        resilience_score += 40
        resilience_breakdown.append(f"Max DD {max_dd:.1%} > -15% (+40)")
    elif max_dd > -0.25:
        resilience_score += 30
        resilience_breakdown.append(f"Max DD {max_dd:.1%} > -25% (+30)")
    elif max_dd > -0.35:
        resilience_score += 20
        resilience_breakdown.append(f"Max DD {max_dd:.1%} > -35% (+20)")
    elif max_dd > -0.50:
        resilience_score += 10
        resilience_breakdown.append(f"Max DD {max_dd:.1%} > -50% (+10)")
    else:
        resilience_breakdown.append(f"Max DD {max_dd:.1%} severo (+0)")
    
    # Worst periods da temporal decomposition (0-30 punti)
    if temporal_decomposition:
        worst_periods = temporal_decomposition.get("worst_periods", {})
        worst_12m = worst_periods.get("worst_12m", {}).get("return", -1)
        
        if worst_12m > -0.20:
            resilience_score += 30
            resilience_breakdown.append(f"Worst 12M {worst_12m:.1%} > -20% (+30)")
        elif worst_12m > -0.35:
            resilience_score += 20
            resilience_breakdown.append(f"Worst 12M {worst_12m:.1%} > -35% (+20)")
        elif worst_12m > -0.50:
            resilience_score += 10
            resilience_breakdown.append(f"Worst 12M {worst_12m:.1%} > -50% (+10)")
        else:
            resilience_breakdown.append(f"Worst 12M {worst_12m:.1%} severo (+0)")
        
        # Recovery speed (0-30 punti)
        recovery = temporal_decomposition.get("recovery_analysis", [])
        if recovery:
            avg_months = np.mean([r["months_to_recover"] for r in recovery])
            if avg_months < 12:
                resilience_score += 30
                resilience_breakdown.append(f"Recovery medio {avg_months:.0f}M < 12M (+30)")
            elif avg_months < 24:
                resilience_score += 20
                resilience_breakdown.append(f"Recovery medio {avg_months:.0f}M < 24M (+20)")
            elif avg_months < 36:
                resilience_score += 10
                resilience_breakdown.append(f"Recovery medio {avg_months:.0f}M < 36M (+10)")
    else:
        # Stima resilienza da downside deviation
        dd_vol = metrics.get('sortino', 0) / metrics.get('sharpe', 1) if metrics.get('sharpe', 1) != 0 else 1
        if dd_vol > 1.5:
            resilience_score += 30
            resilience_breakdown.append(f"Buon controllo downside (+30)")
        elif dd_vol > 1.2:
            resilience_score += 15
            resilience_breakdown.append(f"Controllo downside moderato (+15)")
    
    # === DETERMINE QUADRANT ===
    efficiency_level = 'HIGH' if efficiency_score >= 50 else 'LOW'
    resilience_level = 'HIGH' if resilience_score >= 50 else 'LOW'
    
    # FIX INCONGRUENZA #5: Check se 100% equity
    is_all_equity = False
    if composition:
        equity_pct = composition.get('total_equity', 0)  # Usa total_equity, non equity_pct
        is_all_equity = equity_pct >= 0.95  # >95% è "all equity"
    
    quadrant_map = {
        ('HIGH', 'HIGH'): {
            'quadrant': 'OPTIMAL',
            'description': 'Efficiente e Resiliente - raro, controllare se sostenibile',
            'icon': '🌟'
        },
        ('HIGH', 'LOW'): {
            'quadrant': 'GROWTH_ORIENTED',
            'description': 'Efficiente ma fragile - ottimo in normali, vulnerabile in crisi',
            'icon': '📈'
        },
        ('LOW', 'HIGH'): {
            'quadrant': 'DEFENSIVE_ORIENTED',
            'description': 'Resiliente ma inefficiente - protegge capitale, sotto-performa',
            'icon': '🛡️'
        },
        ('LOW', 'LOW'): {
            'quadrant': 'NEEDS_REVIEW',
            'description': 'Né efficiente né resiliente - rivedere struttura',
            'icon': '⚠️'
        }
    }
    
    quadrant_info = quadrant_map[(efficiency_level, resilience_level)]
    
    # FIX INCONGRUENZA #5: Override per all-equity
    # Un portafoglio 100% equity NON può essere "DEFENSIVE_ORIENTED"
    if is_all_equity and quadrant_info['quadrant'] == 'DEFENSIVE_ORIENTED':
        quadrant_info = {
            'quadrant': 'EQUITY_RESILIENT',
            'description': 'All-equity con buona resilienza storica - attenzione: resta esposto a equity risk',
            'icon': '📊'
        }
    elif is_all_equity and quadrant_info['quadrant'] == 'NEEDS_REVIEW':
        quadrant_info = {
            'quadrant': 'EQUITY_UNDERPERFORMING',
            'description': 'All-equity con scarsa efficienza E resilienza - concentrazione su asset deboli?',
            'icon': '📉'
        }
    
    return {
        'efficiency': {
            'score': efficiency_score,
            'level': efficiency_level,
            'breakdown': efficiency_breakdown
        },
        'resilience': {
            'score': resilience_score,
            'level': resilience_level,
            'breakdown': resilience_breakdown
        },
        'quadrant': quadrant_info['quadrant'],
        'quadrant_description': quadrant_info['description'],
        'quadrant_icon': quadrant_info['icon'],
        'trade_off_note': (
            "Trade-off intrinseco: aumentare efficienza (più rischio) "
            "riduce tipicamente resilienza, e viceversa. "
            "La posizione ottimale dipende dagli obiettivi dell'investitore."
        )
    }
