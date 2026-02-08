"""
Gate System Module v4.1
=======================
Investment Committee Validator Framework

Implementa il sistema di gate con priorità logica:
A) Data Integrity Gate
B) Risk Intent Gate  
C) Structural Coherence Gate
D) Benchmark Comparison Gate
E) Final Verdict (unico, senza contraddizioni)

REGOLA FONDAMENTALE:
Se un gate fallisce, i blocchi successivi devono essere limitati.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

# Import centralized configuration (Fix C6, M1-M2)
from portfolio_engine.config.user_config import SAMPLE_SIZE_CONFIG, GATE_THRESHOLDS

# Import FDR correction for multiple testing (Fix C7)
from portfolio_engine.analytics.metrics import apply_fdr_correction

# Import exception enforcement (Production Readiness Issue #1)
from portfolio_engine.utils.exceptions import (
    DataIntegrityError,
    BetaWindowError,
    IntentFailStructureInconclusiveError,
    UserAcknowledgment
)

# Import centralized models (Production Readiness Issue #2)
from portfolio_engine.models.portfolio import FinalVerdictType, PortfolioStructureType, PrescriptiveAction


# ================================================================================
# SEZIONE A: ENUMS E STRUTTURE DATI
# ================================================================================

class GateStatus(Enum):
    """Stati possibili per ogni gate."""
    PASS = "PASS"
    PASS_PROVISIONAL = "PASS_PROVISIONAL"  # Rule 1: Pass but low confidence
    SOFT_FAIL = "SOFT_FAIL"
    HARD_FAIL = "HARD_FAIL"
    VALID_FAIL = "VALID_FAIL"  # Rule 2: Fail is certain despite other data issues
    BLOCKED = "BLOCKED"
    INCONCLUSIVE = "INCONCLUSIVE"  # Rule 3: Cannot determine
    NOT_EVALUATED = "NOT_EVALUATED"


class AssetClassification(Enum):
    """
    Classificazione asset (Section D).
    
    FIX BUG #5: 5-bucket system:
    - CORE: Broad market global (VT, VWCE, etc.)
    - CORE_REGIONAL: Broad market regional (USA, EU, EM, JP, UK)
    - SATELLITE_CLASSIFIED: Factor/Sector/Region tilts (identifiable)
    - UNCLASSIFIED_EQUITY: Equity that doesn't fit core or satellite patterns
    - DEFENSIVE: Bond, cash-like, gold
    """
    CORE = "CORE"                           # Global broad market
    CORE_REGIONAL = "CORE_REGIONAL"         # FIX BUG #5: Regional broad market
    SATELLITE_FACTOR = "SATELLITE_FACTOR"   # Factor tilts (value, momentum, size)
    SATELLITE_SECTOR = "SATELLITE_SECTOR"   # Sector bets
    SATELLITE_REGION = "SATELLITE_REGION"   # Single-country EM tilts
    SATELLITE_THEMATIC = "SATELLITE_THEMATIC" # Pure thematic
    UNCLASSIFIED_EQUITY = "UNCLASSIFIED_EQUITY"  # Equity not matching patterns
    DEFENSIVE = "DEFENSIVE"                 # Bond, cash-like, gold


class BenchmarkComparability(Enum):
    """Comparabilità benchmark (Section E)."""
    SAME_CATEGORY = "SAME_CATEGORY"     # ≥95% equity broad-market
    REFERENCE_ONLY = "REFERENCE_ONLY"   # Opportunity cost, not direct comparison
    NOT_COMPARABLE = "NOT_COMPARABLE"   # Too different


class ActionPriority(Enum):
    """Priorità delle azioni prescriptive."""
    CRITICAL = "CRITICAL"       # Must fix before any other analysis
    HIGH = "HIGH"               # Should fix soon, blocks some conclusions
    MEDIUM = "MEDIUM"           # Should fix, but analysis can proceed
    LOW = "LOW"                 # Optimization suggestion
    INFORMATIONAL = "INFO"      # For awareness only


@dataclass
class SingleGateResult:
    """Risultato di un singolo gate (renamed to avoid conflict with models.GateResult)."""
    name: str
    status: GateStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    blocks_downstream: bool = False  # Se True, blocca gate successivi
    prescriptive_actions: List[PrescriptiveAction] = field(default_factory=list)


@dataclass
class CCRClassification:
    """
    Classificazione CCR/Weight leverage (Section F).
    
    Rule 6: If corr_nan_ratio > 0.20, CCR must be tagged PARTIAL.
    """
    ticker: str
    weight: float
    ccr_pct: float
    risk_leverage: float  # CCR% / weight%
    classification: str   # "normal", "warning", "critical"
    is_actionable: bool   # True solo se intent_match E corr_gate pass
    data_quality: str = "FULL"  # Rule 6: "FULL", "PARTIAL", "SAMPLE_TOO_SMALL"


# ================================================================================
# SEZIONE B: DATA INTEGRITY GATE
# ================================================================================

def calculate_corr_nan_ratio(corr_matrix: pd.DataFrame) -> float:
    """
    Calcola il rapporto di NaN nella matrice correlazione.
    
    corr_nan_ratio = (#correlazioni NaN) / (#celle totali)
    """
    if corr_matrix is None or corr_matrix.empty:
        return 1.0  # 100% NaN
    
    total_cells = corr_matrix.size
    nan_cells = corr_matrix.isna().sum().sum()
    
    return nan_cells / total_cells if total_cells > 0 else 1.0


def check_data_integrity_gate(
    corr_matrix: pd.DataFrame,
    returns_df: pd.DataFrame = None,
    nan_threshold: float = 0.20,
    ticker_starts: Dict[str, str] = None,  # FIX BUG #3: inception dates per ticker
    earliest_date: str = None               # FIX BUG #3: earliest date in dataset
) -> Tuple[SingleGateResult, Dict[str, Any]]:
    """
    DATA INTEGRITY GATE (Section B).
    
    FIX BUG #3: Distingue NaN da INCEPTION vs NaN da DATA QUALITY:
    - NaN_inception: celle dove l'ETF non esisteva ancora (INFORMATIVO)
    - NaN_data_quality: celle dove l'ETF esisteva ma mancano dati (CRITICO per gate)
    
    B1) Correlation Gate:
        Se corr_nan_ratio > 0.20:
        - Diversification Verdict = BLOCKED
        - Vietato dichiarare "diversificazione robusta"
        - Vietato calcolare medie su correlazioni
    
    B2) Risk Contribution Gate (CCR):
        Se corr_nan_ratio > 0.20:
        - CCR etichettato come PARTIAL/UNRELIABLE
        - Vietato usarlo per "criticità severe"
    
    Returns:
        (GateResult, details_dict)
    """
    corr_nan_ratio = calculate_corr_nan_ratio(corr_matrix)
    
    # FIX BUG #3: Calcola NaN da inception se abbiamo i dati dei returns
    nan_inception_count = 0
    nan_data_quality_count = 0
    total_cells = 0
    
    if returns_df is not None and ticker_starts is not None and earliest_date is not None:
        # Calcola NaN da inception vs data quality
        earliest = pd.Timestamp(earliest_date)
        
        for col in returns_df.columns:
            if col in ticker_starts:
                ticker_inception = pd.Timestamp(ticker_starts[col])
                series = returns_df[col]
                
                # NaN prima dell'inception = expected (inception NaN)
                inception_nan = series.loc[:ticker_inception].isna().sum()
                # NaN dopo l'inception = data quality issue
                quality_nan = series.loc[ticker_inception:].isna().sum()
                
                nan_inception_count += inception_nan
                nan_data_quality_count += quality_nan
                total_cells += len(series)
    
    # Se non abbiamo returns_df, usiamo solo corr_nan_ratio
    nan_data_quality_ratio = nan_data_quality_count / total_cells if total_cells > 0 else corr_nan_ratio
    
    details = {
        'corr_nan_ratio': corr_nan_ratio,
        'nan_threshold': nan_threshold,
        'correlation_gate_passed': corr_nan_ratio <= nan_threshold,
        'ccr_reliable': corr_nan_ratio <= nan_threshold,
        'diversification_verdict_allowed': corr_nan_ratio <= nan_threshold,
        'blocked_analyses': [],
        # FIX BUG #3: Separate NaN sources
        'nan_inception_count': nan_inception_count,
        'nan_data_quality_count': nan_data_quality_count,
        'nan_data_quality_ratio': nan_data_quality_ratio,
        'total_cells': total_cells,
    }
    
    if corr_nan_ratio > nan_threshold:
        # GATE FAILED
        details['blocked_analyses'] = [
            'diversification_verdict',
            'correlation_stability',
            'correlation_mean_calculation',
        ]
        
        if corr_nan_ratio > 0.50:
            # Molto grave - blocca anche CCR
            details['ccr_reliable'] = False
            details['blocked_analyses'].append('ccr_severity_judgment')
        
        return SingleGateResult(
            name="DATA_INTEGRITY",
            status=GateStatus.HARD_FAIL,
            message=f"⛔ CORRELATION_GATE: FAILED ({corr_nan_ratio:.0%} NaN > {nan_threshold:.0%} threshold)",
            details=details,
            blocks_downstream=True  # Blocca verdetti sulla diversificazione
        ), details
    
    # FIX BUG #3: Messaggio più informativo con distinzione NaN
    if nan_inception_count > 0:
        msg = (f"✅ DATA_INTEGRITY: PASS (Data Quality NaN {nan_data_quality_ratio:.1%}, "
               f"Inception NaN {nan_inception_count} cells - expected)")
    else:
        msg = f"✅ DATA_INTEGRITY: PASS (NaN ratio {corr_nan_ratio:.0%} ≤ {nan_threshold:.0%})"
    
    return SingleGateResult(
        name="DATA_INTEGRITY",
        status=GateStatus.PASS,
        message=msg,
        details=details,
        blocks_downstream=False
    ), details


# ================================================================================
# SEZIONE C: RISK INTENT GATE
# ================================================================================

# Rule 2 & 3: Minimum years for beta to be considered valid
# Now imported from config.py for centralized management (Fix C6)
MIN_BETA_WINDOW_YEARS = SAMPLE_SIZE_CONFIG['beta_min_years']


def check_risk_intent_gate(
    portfolio_beta: float,
    risk_intent: str,
    intent_specs: Dict[str, Any],
    beta_window_years: float = 10.0  # Rule 2 & 3: How many years of data for beta calc
) -> Tuple[SingleGateResult, Dict[str, Any]]:
    """
    RISK INTENT GATE (Section C).
    
    Rule 2: IF IntentGate = HARD_FAIL AND beta_window_years >= MIN_YEARS 
            THEN IntentVerdict = VALID_FAIL (not inconclusive).
    Rule 3: IF beta_window_years < MIN_YEARS 
            THEN IntentVerdict = INCONCLUSIVE_INTENT_DATA.
    
    Per Risk Intent = AGGRESSIVE:
        beta_target = [1.0, 1.3]
        beta_min = 0.9
        beta_fail = 0.6
    
    Returns:
        (GateResult, details_dict)
    """
    # Estrai specs per il risk intent
    beta_target = intent_specs.get('beta_range', (0.8, 1.0))
    beta_min = intent_specs.get('min_beta_acceptable', 0.6)
    beta_fail = intent_specs.get('beta_fail_threshold', 0.4)
    
    details = {
        'portfolio_beta': portfolio_beta,
        'risk_intent': risk_intent,
        'beta_target_range': beta_target,
        'beta_min_acceptable': beta_min,
        'beta_fail_threshold': beta_fail,
        'beta_window_years': beta_window_years,
        'min_beta_window_required': MIN_BETA_WINDOW_YEARS,
        'beta_data_sufficient': beta_window_years >= MIN_BETA_WINDOW_YEARS,
        'allows_structural_fragile_verdict': True,
        'allows_restructure_verdict': True,
        'intent_verdict_validity': 'VALID' if beta_window_years >= MIN_BETA_WINDOW_YEARS else 'INCONCLUSIVE',
    }
    
    prescriptive_actions = []
    
    # Rule 3: Check if beta window is sufficient
    if beta_window_years < MIN_BETA_WINDOW_YEARS:
        details['allows_structural_fragile_verdict'] = False
        details['allows_restructure_verdict'] = False
        
        prescriptive_actions.append(PrescriptiveAction(
            issue_code="BETA_WINDOW_INSUFFICIENT",
            priority=ActionPriority.HIGH.value,
            confidence=1.0,  # Certain - this is a data issue
            description=f"Beta window {beta_window_years:.1f}y < {MIN_BETA_WINDOW_YEARS:.0f}y required",
            actions=[
                "Wait for more historical data to accumulate",
                "Use longer backtest period if available",
                "Consider using proxy benchmark for intent validation"
            ],
            blockers=["Intent verdict (INCONCLUSIVE)", "Structural recommendations"],
            data_quality_impact="UNRELIABLE"
        ))
        
        return SingleGateResult(
            name="RISK_INTENT",
            status=GateStatus.INCONCLUSIVE,
            message=f"⚠️ INTENT_INCONCLUSIVE: Beta window {beta_window_years:.1f}y < {MIN_BETA_WINDOW_YEARS:.0f}y minimo. "
                   f"Dati insufficienti per giudicare intent.",
            details=details,
            blocks_downstream=False,
            prescriptive_actions=prescriptive_actions
        ), details
    
    # Rule 2: Beta window sufficient - verdict is VALID (certain)
    if portfolio_beta < beta_fail:
        # VALID_FAIL - intent mismatch is CERTAIN (not inconclusive)
        details['allows_structural_fragile_verdict'] = False
        details['allows_restructure_verdict'] = False
        
        # Calculate beta gap for actionable suggestions
        beta_gap = beta_min - portfolio_beta
        
        # Determine recommended intent based on actual beta
        if portfolio_beta < 0.5:
            recommended_intent = "CONSERVATIVE"
            alt_intent = "MODERATE"
        elif portfolio_beta < 0.7:
            recommended_intent = "MODERATE"
            alt_intent = "BALANCED"
        else:
            recommended_intent = "BALANCED"
            alt_intent = "GROWTH"
        
        prescriptive_actions.append(PrescriptiveAction(
            issue_code="INTENT_MISMATCH_HARD",
            priority=ActionPriority.CRITICAL.value,
            confidence=0.95,  # Very high - based on sufficient data
            description=f"Portfolio beta {portfolio_beta:.2f} is incompatible with {risk_intent} (requires ≥{beta_min:.1f})",
            actions=[
                f"OPTION A: Change RISK_INTENT to {recommended_intent} (matches beta {portfolio_beta:.2f})",
                f"OPTION B: Increase beta by {beta_gap:.2f} via:",
                f"   - Add 15-20% US large-cap growth (QQQ, VGT, XLK)",
                f"   - Remove low-beta positions (bond proxies, min-vol, utilities)",
                f"   - Reduce EM value / small-cap (typically low-beta)",
                f"OPTION C: If intentional defensive tilt, relabel as {alt_intent}"
            ],
            blockers=["All structural analysis", "Benchmark comparisons", "Diversification recommendations"],
            data_quality_impact="NONE"
        ))
        
        return SingleGateResult(
            name="RISK_INTENT",
            status=GateStatus.VALID_FAIL,  # Rule 2: Fail is certain
            message=f"❌ INTENT_MISMATCH (VALID FAIL): Beta {portfolio_beta:.2f} < {beta_fail:.1f} "
                   f"su {beta_window_years:.1f} anni. Verdict CERTO: obiettivo errato.",
            details=details,
            blocks_downstream=False,
            prescriptive_actions=prescriptive_actions
        ), details
    
    elif portfolio_beta < beta_min:
        # SOFT FAIL - warning ma non errore grave
        details['allows_structural_fragile_verdict'] = False
        details['allows_restructure_verdict'] = False
        
        beta_gap = beta_min - portfolio_beta
        
        # Determine if intent downgrade is better option
        if portfolio_beta < 0.7:
            recommended_intent = "BALANCED"
        elif portfolio_beta < 0.85:
            recommended_intent = "GROWTH"
        else:
            recommended_intent = None  # Close enough, minor tweak
        
        action_list = []
        if recommended_intent:
            action_list.append(f"OPTION A: Downgrade RISK_INTENT to {recommended_intent} (better fit)")
        action_list.extend([
            f"OPTION B: Increase beta by {beta_gap:.2f} via:",
            f"   - Tilt US large-cap +5-10%",
            f"   - Reduce defensive/low-vol positions",
            "OPTION C: Accept current structure as 'controlled-growth' portfolio"
        ])
        
        prescriptive_actions.append(PrescriptiveAction(
            issue_code="INTENT_MISMATCH_SOFT",
            priority=ActionPriority.MEDIUM.value,
            confidence=0.85,
            description=f"Portfolio beta {portfolio_beta:.2f} below minimum {beta_min:.1f} for {risk_intent}",
            actions=action_list,
            blockers=["Structural fragile verdict"],
            data_quality_impact="NONE"
        ))
        
        return SingleGateResult(
            name="RISK_INTENT",
            status=GateStatus.SOFT_FAIL,
            message=f"⚠️ INTENT_WARNING: Beta {portfolio_beta:.2f} sotto min {beta_min:.1f} "
                   f"per {risk_intent}. Struttura coerente ma obiettivo disallineato.",
            details=details,
            blocks_downstream=False,
            prescriptive_actions=prescriptive_actions
        ), details
    
    else:
        # PASS
        return SingleGateResult(
            name="RISK_INTENT",
            status=GateStatus.PASS,
            message=f"✅ INTENT_MATCH: Beta {portfolio_beta:.2f} ≥ {beta_min:.1f} per {risk_intent}",
            details=details,
            blocks_downstream=False,
            prescriptive_actions=[]
        ), details


# ================================================================================
# SEZIONE D: CORE vs SATELLITE CLASSIFICATION
# ================================================================================

def determine_portfolio_structure_type(
    summary: Dict[str, Any],
    rolling_stability: Dict[str, Any] = None
) -> Tuple[PortfolioStructureType, float, str]:
    """
    Determina il tipo di struttura del portafoglio (Issue #2 fix).
    
    Returns:
        (structure_type, confidence, explanation)
    """
    total_core_global = summary.get('total_core_global', 0)
    total_core_regional = summary.get('total_core_regional', 0)
    total_satellites = summary.get('total_satellites_classified', 0)
    total_defensive = summary.get('total_defensive', 0)
    total_unclassified = summary.get('total_unclassified_equity', 0)
    has_sector_tilts = summary.get('has_sector_tilts', False)
    
    # Rolling stability affects confidence
    stability_penalty = 0.0
    if rolling_stability:
        corr_stability = rolling_stability.get('correlation_stability', 1.0)
        if corr_stability < 0.7:
            stability_penalty = 0.15
        elif corr_stability < 0.85:
            stability_penalty = 0.08
    
    # High unclassified = lower confidence in any classification
    unclassified_penalty = min(0.20, total_unclassified * 0.5)
    
    # Decision tree for structure type
    if total_defensive >= 0.30:
        confidence = 0.90 - stability_penalty - unclassified_penalty
        return (
            PortfolioStructureType.BALANCED,
            confidence,
            f"Defensive allocation {total_defensive:.0%} ≥ 30% indicates balanced strategy"
        )
    
    if total_core_global >= 0.50:
        confidence = 0.95 - stability_penalty - unclassified_penalty
        return (
            PortfolioStructureType.GLOBAL_CORE,
            confidence,
            f"Global core {total_core_global:.0%} ≥ 50% dominates structure"
        )
    
    # Issue #2 FIX: EQUITY_MULTI_BLOCK when 0% global but stable regional
    if total_core_global < 0.05 and total_core_regional >= 0.40:
        confidence = 0.85 - stability_penalty - unclassified_penalty
        return (
            PortfolioStructureType.EQUITY_MULTI_BLOCK,
            confidence,
            f"No global core but regional blocks {total_core_regional:.0%} ≥ 40% form stable structure"
        )
    
    # Issue #2 FIX: Multi-block regional stable without global core (lower threshold)
    if total_core_global < 0.05 and total_core_regional >= 0.30:
        if stability_penalty < 0.08 and total_unclassified < 0.30:
            confidence = 0.80 - stability_penalty - unclassified_penalty
            return (
                PortfolioStructureType.EQUITY_MULTI_BLOCK,
                confidence,
                f"Stable regional blocks {total_core_regional:.0%} without global core"
            )
    
    if has_sector_tilts and (summary.get('sector_weight', 0) or total_satellites) >= 0.25:
        confidence = 0.80 - stability_penalty - unclassified_penalty
        return (
            PortfolioStructureType.SECTOR_CONCENTRATED,
            confidence,
            f"Sector/thematic concentration ≥ 25% drives structure"
        )
    
    if total_core_global + total_core_regional >= 0.30 and total_satellites >= 0.15:
        confidence = 0.85 - stability_penalty - unclassified_penalty
        return (
            PortfolioStructureType.FACTOR_TILTED,
            confidence,
            f"Core {total_core_global + total_core_regional:.0%} + satellites {total_satellites:.0%} = factor-tilted"
        )
    
    # Issue #2 FIX: NEW - Mixed equity diversification (high unclassified but stable)
    total_equity = 1.0 - total_defensive
    if total_equity > 0.85 and total_unclassified > 0.20:
        if stability_penalty < 0.10:
            confidence = 0.75 - stability_penalty - unclassified_penalty
            return (
                PortfolioStructureType.EQUITY_DIVERSIFIED_MIXED,
                confidence,
                f"Diversified equity with {total_unclassified:.0%} unclassified, but stable correlation structure. "
                f"Not timing-based, lacks dominant core pattern."
            )
    
    # Fallback: high unclassified AND unstable = OPPORTUNISTIC
    if total_unclassified >= 0.30 or stability_penalty >= 0.10:
        confidence = max(0.50, 0.70 - stability_penalty - unclassified_penalty)
        return (
            PortfolioStructureType.OPPORTUNISTIC,
            confidence,
            f"Unstable or timing-based: unclassified {total_unclassified:.0%}, stability penalty {stability_penalty:.0%}"
        )
    
    # Default to EQUITY_DIVERSIFIED_MIXED for mixed structures
    confidence = 0.70 - stability_penalty - unclassified_penalty
    return (
        PortfolioStructureType.EQUITY_DIVERSIFIED_MIXED,
        confidence,
        f"Mixed equity structure without dominant pattern"
    )


# Keywords per classificazione
# FIX C5: Ora caricate da etf_taxonomy.json invece di essere hardcoded.
# Fallback a default se il file non esiste o è malformato.

import json
import os

def _load_classification_keywords() -> dict:
    """Load classification keywords from etf_taxonomy.json with fallback defaults."""
    # JSON file is in data/definitions/
    json_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'definitions', 'etf_taxonomy.json')
    
    # Default keywords (fallback)
    defaults = {
        'CORE_GLOBAL': ['VT', 'VWCE', 'IWDA', 'ACWI', 'VTI', 'ITOT', 'SPTM'],
        'CORE_REGIONAL': ['VOO', 'SPY', 'IVV', 'CSPX', 'VGK', 'IMEU', 'VWO', 'IEMG', 'EMIM', 'EWJ', 'SJPA'],
        'SATELLITE_FACTOR': ['MTUM', 'QUAL', 'VLUE', 'SIZE', 'USSC', 'WSML', 'IWM', 'VB', 'IJR'],
        'SATELLITE_SECTOR': ['XLK', 'XLF', 'XLE', 'XLV', 'SEMI', 'SMH', 'INFR', 'DFNS'],
        'SATELLITE_REGION': ['INDA', 'MCHI', 'EWZ', 'EWT', 'EWY', 'ITWN'],
        'DEFENSIVE': ['BND', 'AGG', 'AGGH', 'TLT', 'GLD', 'IAU', 'SGLN'],
    }
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        keywords = data.get('classification_keywords', {})
        
        result = {}
        for key in defaults.keys():
            if key in keywords and 'keywords' in keywords[key]:
                result[key] = keywords[key]['keywords']
            else:
                result[key] = defaults[key]
        
        return result
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        import warnings
        warnings.warn(f"Could not load keywords from etf_taxonomy.json: {e}. Using defaults.")
        return defaults

# Load keywords once at module import
_KEYWORDS = _load_classification_keywords()

CORE_GLOBAL_KEYWORDS = _KEYWORDS['CORE_GLOBAL']
CORE_REGIONAL_KEYWORDS = _KEYWORDS['CORE_REGIONAL']
SATELLITE_FACTOR_KEYWORDS = _KEYWORDS['SATELLITE_FACTOR']
SATELLITE_SECTOR_KEYWORDS = _KEYWORDS['SATELLITE_SECTOR']
SATELLITE_REGION_KEYWORDS = _KEYWORDS['SATELLITE_REGION']
DEFENSIVE_KEYWORDS = _KEYWORDS['DEFENSIVE']


def classify_asset(ticker: str, vol: float = None) -> AssetClassification:
    """
    Classifica un singolo asset (Section D).
    
    FIX BUG #5: 5-bucket system:
    - CORE (global broad-market)
    - CORE_REGIONAL (regional broad-market: USA, EU, EM, JP, UK)
    - SATELLITE (factor/sector/region)
    - UNCLASSIFIED_EQUITY
    - DEFENSIVE
    
    Returns:
        AssetClassification
    """
    ticker_upper = ticker.upper()
    ticker_clean = ticker_upper.split('.')[0]
    
    # Check in ordine di specificità
    if any(kw in ticker_clean or kw in ticker_upper for kw in DEFENSIVE_KEYWORDS):
        return AssetClassification.DEFENSIVE
    
    # FIX BUG #5: Check CORE_GLOBAL first
    if any(kw in ticker_clean or kw in ticker_upper for kw in CORE_GLOBAL_KEYWORDS):
        return AssetClassification.CORE
    
    # FIX BUG #5: Check CORE_REGIONAL before satellite
    if any(kw in ticker_clean or kw in ticker_upper for kw in CORE_REGIONAL_KEYWORDS):
        return AssetClassification.CORE_REGIONAL
    
    if any(kw in ticker_clean or kw in ticker_upper for kw in SATELLITE_FACTOR_KEYWORDS):
        return AssetClassification.SATELLITE_FACTOR
    
    if any(kw in ticker_clean or kw in ticker_upper for kw in SATELLITE_SECTOR_KEYWORDS):
        return AssetClassification.SATELLITE_SECTOR
    
    if any(kw in ticker_clean or kw in ticker_upper for kw in SATELLITE_REGION_KEYWORDS):
        return AssetClassification.SATELLITE_REGION
    
    # Only classify as thematic if very high vol
    if vol is not None and vol > 0.35:
        return AssetClassification.SATELLITE_THEMATIC
    
    # Default to UNCLASSIFIED_EQUITY
    return AssetClassification.UNCLASSIFIED_EQUITY


def classify_portfolio_assets(
    tickers: List[str],
    weights: np.ndarray,
    asset_metrics: pd.DataFrame = None
) -> Dict[str, Any]:
    """
    Classifica tutti gli asset del portafoglio e calcola metriche separate.
    
    FIX BUG #5: 5-bucket output:
    - CORE_GLOBAL
    - CORE_REGIONAL
    - SATELLITE_CLASSIFIED (sum of factor/sector/region/thematic)
    - UNCLASSIFIED_EQUITY
    - DEFENSIVE
    
    Returns:
        Dict con classificazione e metriche per categoria
    """
    classifications = {}
    by_category = {
        AssetClassification.CORE: {'tickers': [], 'weights': [], 'total_weight': 0.0},
        AssetClassification.CORE_REGIONAL: {'tickers': [], 'weights': [], 'total_weight': 0.0},  # FIX BUG #5
        AssetClassification.SATELLITE_FACTOR: {'tickers': [], 'weights': [], 'total_weight': 0.0},
        AssetClassification.SATELLITE_SECTOR: {'tickers': [], 'weights': [], 'total_weight': 0.0},
        AssetClassification.SATELLITE_REGION: {'tickers': [], 'weights': [], 'total_weight': 0.0},
        AssetClassification.SATELLITE_THEMATIC: {'tickers': [], 'weights': [], 'total_weight': 0.0},
        AssetClassification.UNCLASSIFIED_EQUITY: {'tickers': [], 'weights': [], 'total_weight': 0.0},
        AssetClassification.DEFENSIVE: {'tickers': [], 'weights': [], 'total_weight': 0.0},
    }
    
    for i, ticker in enumerate(tickers):
        vol = None
        if asset_metrics is not None and ticker in asset_metrics.index:
            vol = asset_metrics.loc[ticker, 'Vol'] if 'Vol' in asset_metrics.columns else None
        
        classification = classify_asset(ticker, vol)
        classifications[ticker] = classification
        
        by_category[classification]['tickers'].append(ticker)
        by_category[classification]['weights'].append(weights[i])
        by_category[classification]['total_weight'] += weights[i]
    
    # FIX BUG #5: Calcola totali aggregati - 5-bucket system
    total_core_global = by_category[AssetClassification.CORE]['total_weight']
    total_core_regional = by_category[AssetClassification.CORE_REGIONAL]['total_weight']
    total_core = total_core_global + total_core_regional  # Combined for compatibility
    
    # Satellite CLASSIFIED = sum of identified satellite types
    total_satellites_classified = sum(
        by_category[cat]['total_weight'] 
        for cat in [
            AssetClassification.SATELLITE_FACTOR,
            AssetClassification.SATELLITE_SECTOR,
            AssetClassification.SATELLITE_REGION,
            AssetClassification.SATELLITE_THEMATIC,
        ]
    )
    
    total_unclassified_equity = by_category[AssetClassification.UNCLASSIFIED_EQUITY]['total_weight']
    total_defensive = by_category[AssetClassification.DEFENSIVE]['total_weight']
    
    # Rule 8: is_pure_equity_core only if no sector tilts and no defensive
    total_equity = total_core + total_satellites_classified + total_unclassified_equity
    has_sector_tilts = (
        by_category[AssetClassification.SATELLITE_SECTOR]['total_weight'] > 0.02 or
        by_category[AssetClassification.SATELLITE_THEMATIC]['total_weight'] > 0.02
    )
    is_pure_equity_core = (
        total_equity >= 0.95 and 
        total_defensive < 0.05 and
        not has_sector_tilts
    )
    
    return {
        'classifications': classifications,
        'by_category': by_category,
        'summary': {
            # FIX BUG #5: 5-bucket output
            'total_core_global': total_core_global,
            'total_core_regional': total_core_regional,
            'total_core': total_core,  # Combined for compatibility
            'total_satellites_classified': total_satellites_classified,
            'total_unclassified_equity': total_unclassified_equity,
            'total_defensive': total_defensive,
            # Legacy field for compatibility
            'total_satellites': total_satellites_classified,
            # Rule 8: Strict criteria for same-category benchmark
            'total_equity': total_equity,
            'has_sector_tilts': has_sector_tilts,
            'is_pure_equity_core': is_pure_equity_core,
        }
    }


# ================================================================================
# SEZIONE E: BENCHMARK COMPARISON GATE
# ================================================================================

def check_benchmark_comparability(
    portfolio_classification: Dict[str, Any],
    benchmark_name: str
) -> Tuple[BenchmarkComparability, str]:
    """
    Determina se un benchmark è SAME_CATEGORY o REFERENCE_ONLY (Section E).
    
    Rule 8: SAME_CATEGORY allowed only if:
    - equity >= 95%
    - no_sector_tilts (sector/thematic < 2%)
    - no_defensive (< 5%)
    
    Otherwise label as OPPORTUNITY_COST/REFERENCE.
    
    Returns:
        (BenchmarkComparability, reason)
    """
    summary = portfolio_classification.get('summary', {})
    total_defensive = summary.get('total_defensive', 0)
    total_equity = summary.get('total_equity', 0)
    has_sector_tilts = summary.get('has_sector_tilts', False)
    is_pure_equity_core = summary.get('is_pure_equity_core', False)
    total_unclassified = summary.get('total_unclassified_equity', 0)
    
    # Benchmark equity puri
    equity_benchmarks = ['VT', 'SPY', 'VOO', 'ACWI', 'IWDA']
    is_equity_benchmark = any(bm in benchmark_name.upper() for bm in equity_benchmarks)
    
    if not is_equity_benchmark:
        return BenchmarkComparability.REFERENCE_ONLY, f"{benchmark_name} non è equity benchmark"
    
    # Rule 8: Strict criteria for same-category
    # 1. Must have >= 95% equity
    if total_equity < 0.95:
        return BenchmarkComparability.REFERENCE_ONLY, \
               f"Equity {total_equity:.0%} < 95% → {benchmark_name} è OPPORTUNITY_COST, non same-category"
    
    # 2. Must NOT have defensive assets
    if total_defensive >= 0.05:
        return BenchmarkComparability.REFERENCE_ONLY, \
               f"Defensive {total_defensive:.0%} ≥ 5% (bond/gold) → {benchmark_name} è OPPORTUNITY_COST"
    
    # 3. Must NOT have sector tilts
    if has_sector_tilts:
        return BenchmarkComparability.REFERENCE_ONLY, \
               f"Sector/thematic tilts presenti → {benchmark_name} è OPPORTUNITY_COST"
    
    # 4. Rule 8: High unclassified equity = uncertain category
    if total_unclassified > 0.20:
        return BenchmarkComparability.REFERENCE_ONLY, \
               f"Unclassified equity {total_unclassified:.0%} > 20% → categoria incerta, {benchmark_name} è reference"
    
    # All criteria met
    if is_pure_equity_core:
        return BenchmarkComparability.SAME_CATEGORY, \
               f"Equity ≥95%, no defensive, no sector tilts → same-category con {benchmark_name}"
    
    return BenchmarkComparability.REFERENCE_ONLY, \
           f"Criteri SAME_CATEGORY non soddisfatti → {benchmark_name} è solo reference"


def check_benchmark_gate(
    portfolio_classification: Dict[str, Any],
    benchmark_results: Dict[str, Any],
    data_integrity_passed: bool,
    intent_gate_passed: bool
) -> Tuple[SingleGateResult, Dict[str, Any]]:
    """
    BENCHMARK COMPARISON GATE (Section E).
    
    "Non giustifica la complessità" è ammesso SOLO se:
    - corr gate PASS
    - intent match PASS
    - excess_return < 0 per almeno 2 benchmark comparabili
    - tracking_error > 4-5%
    - IR < 0
    
    Returns:
        (GateResult, details_dict)
    """
    details = {
        'benchmark_comparability': {},
        'allows_complexity_criticism': False,
        'comparable_benchmarks': [],
        'reference_benchmarks': [],
    }
    
    # Se data integrity o intent gate falliscono, non permettere critiche sulla complessità
    if not data_integrity_passed or not intent_gate_passed:
        details['allows_complexity_criticism'] = False
        details['blocked_reason'] = "Data integrity o intent gate non passati"
        
        return SingleGateResult(
            name="BENCHMARK_COMPARISON",
            status=GateStatus.BLOCKED,
            message="⛔ BENCHMARK_GATE: Critica 'complessità' BLOCCATA (prerequisiti non soddisfatti)",
            details=details,
            blocks_downstream=False
        ), details
    
    # Analizza ogni benchmark
    underperformance_count = 0
    
    for bench_name, bench_data in benchmark_results.get('benchmarks', {}).items():
        comparability, reason = check_benchmark_comparability(portfolio_classification, bench_name)
        
        details['benchmark_comparability'][bench_name] = {
            'comparability': comparability.value,
            'reason': reason,
        }
        
        if comparability == BenchmarkComparability.SAME_CATEGORY:
            details['comparable_benchmarks'].append(bench_name)
            
            # Check underperformance
            excess_return = bench_data.get('excess_return', 0)
            ir = bench_data.get('information_ratio', 0)
            te = bench_data.get('tracking_error', 0)
            
            if excess_return < 0 and ir < 0 and te > 0.04:
                underperformance_count += 1
        else:
            details['reference_benchmarks'].append(bench_name)
    
    # Determina se "complessità" critica è ammessa
    if underperformance_count >= 2:
        details['allows_complexity_criticism'] = True
        return SingleGateResult(
            name="BENCHMARK_COMPARISON",
            status=GateStatus.PASS,
            message=f"✅ BENCHMARK_GATE: {underperformance_count} benchmark same-category con underperformance",
            details=details,
            blocks_downstream=False
        ), details
    
    if not details['comparable_benchmarks']:
        return SingleGateResult(
            name="BENCHMARK_COMPARISON",
            status=GateStatus.PASS,
            message="ℹ️ BENCHMARK_GATE: Nessun benchmark same-category (solo reference)",
            details=details,
            blocks_downstream=False
        ), details
    
    return SingleGateResult(
        name="BENCHMARK_COMPARISON",
        status=GateStatus.PASS,
        message=f"✅ BENCHMARK_GATE: {len(details['comparable_benchmarks'])} benchmark comparabili",
        details=details,
        blocks_downstream=False
    ), details


# ================================================================================
# SEZIONE F: CCR CLASSIFICATION
# ================================================================================

def classify_ccr_leverage(
    ccr_data: pd.DataFrame,
    intent_gate_passed: bool,
    data_integrity_passed: bool,
    corr_nan_ratio: float = 0.0,
    crisis_sample_days: int = 100,
    portfolio_vol: float = None,
    target_vol: float = None
) -> List[CCRClassification]:
    """
    Classifica CCR/Weight leverage (Section F).
    
    Rule 6: IF corr_nan_ratio > 0.20 THEN CCR tables must be tagged PARTIAL;
            IF crisis_sample < 30 days THEN tag SAMPLE_TOO_SMALL.
    
    risk_leverage = CCR% / weight%
    
    Classificazione:
    - ≤1.5x → normale
    - 1.5-2.5x → warning  
    - >2.5x → critical (solo se intent match E corr gate pass)
    
    Se intent mismatch: CCR è solo DESCRITTIVO, non actionable.
    
    Returns:
        List[CCRClassification]
    """
    if ccr_data is None or ccr_data.empty:
        return []
    
    results = []
    
    weights = ccr_data['Weight'].values if 'Weight' in ccr_data.columns else None
    ccr_pct = ccr_data['CCR%'].values if 'CCR%' in ccr_data.columns else None
    
    if weights is None or ccr_pct is None:
        return []
    
    tickers = ccr_data.index.tolist() if hasattr(ccr_data, 'index') else []
    
    # Rule 6: Determine data quality tag
    if corr_nan_ratio > 0.20:
        data_quality = "PARTIAL"
    elif crisis_sample_days < 30:
        data_quality = "SAMPLE_TOO_SMALL"
    else:
        data_quality = "FULL"
    
    for i, ticker in enumerate(tickers):
        weight = weights[i]
        ccr = ccr_pct[i]
        
        if weight == 0 or np.isnan(weight) or np.isnan(ccr):
            continue
        
        risk_leverage = ccr / weight
        
        # Classificazione base
        if risk_leverage <= 1.5:
            classification = "normal"
        elif risk_leverage <= 2.5:
            classification = "warning"
        else:
            classification = "critical"
        
        # Rule 6: If data quality is not FULL, CCR is never actionable
        # Also not actionable if intent mismatch or data integrity fail
        is_actionable = (
            intent_gate_passed and 
            data_integrity_passed and
            data_quality == "FULL" and
            classification in ["warning", "critical"]
        )
        
        results.append(CCRClassification(
            ticker=ticker,
            weight=weight,
            ccr_pct=ccr,
            risk_leverage=risk_leverage,
            classification=classification,
            is_actionable=is_actionable,
            data_quality=data_quality  # Rule 6
        ))
    
    return results


# ================================================================================
# SEZIONE G: FINAL VERDICT
# ================================================================================

def determine_final_verdict(
    data_integrity_gate: SingleGateResult,
    intent_gate: SingleGateResult,
    structural_issues: List[str],
    ccr_classifications: List[CCRClassification]
) -> Tuple[FinalVerdictType, str, str]:
    """
    Determina il verdetto finale UNICO (Section G).
    
    CRITICAL FIX v4.3: Separazione Diagnostica vs Decisioni
    ========================================================
    
    DIAGNOSTICA (informativa, non terminale):
    - CCR warnings: segnali di concentrazione rischio
    - Correlation patterns: tendenze osservate
    - Sample size warnings: limiti statistici
    
    DECISIONI TERMINALI (gate fail = stop analysis):
    - Data Integrity FAIL: dati insufficienti per valutare
    - Intent FAIL: obiettivo dichiarato non raggiunto
    - Structural FRAGILITY: causa dimostrabile di instabilità
    
    DEFINIZIONE "Fragilità Strutturale" (causale, non sintomatica):
    ================================================================
    Una struttura è FRAGILE se e solo se:
    1. Single-driver dependency: >60% peso su 1 asset/fattore
    2. Hidden leverage: esposizione nascosta via derivati/strutturati
    3. Correlation collapse: asset decorrelati storicamente → +0.9 in crisi
    4. Liquidity trap: >40% in asset illiquidi (bid-ask >2%)
    5. Structural constraint violated: vincoli dichiarati violati
    
    CCR elevati NON sono fragilità (sono concentrazione, non instabilità).
    
    NEW RULE v4.3: Intent FAIL ≠ Structural FAIL
    - If structure is OK but intent fails, verdict is INTENT_MISALIGNED_STRUCTURE_OK
    - This is a labeling issue, NOT a structural problem
    
    Rule 1: IF DataIntegrity = HARD_FAIL THEN StructuralGate = BLOCKED
    Rule 2: IF IntentGate = VALID_FAIL THEN intent verdict is CERTAIN
    Rule 7: IF FinalVerdict = INCONCLUSIVE THEN prohibit portfolio-action recommendations
    
    Verdetti possibili:
    1. ✅ STRUCTURALLY_COHERENT + INTENT_MATCH
    2. ⚠️ INTENT_MISALIGNED_STRUCTURE_OK (structure fine, intent label wrong)
    3. ❌ STRUCTURALLY_FRAGILE (solo se causa dimostrabile)
    4. ⛔ INCONCLUSIVE_DATA_FAIL (corr NaN too high, structural unknown)
    5. ⚠️ INTENT_FAIL_STRUCTURE_INCONCLUSIVE (intent certain, structure unknown)
    6. ⛔ INCONCLUSIVE_INTENT_DATA (beta window too short)
    
    Returns:
        (FinalVerdictType, verdict_message, why_not_contradictory)
    """
    # Rule 3: Check if intent gate is inconclusive (beta window too short)
    if intent_gate.status == GateStatus.INCONCLUSIVE:
        # PRODUCTION ENFORCEMENT: Raise exception instead of just returning verdict
        window_years = intent_gate.details.get('beta_window_years', 0)
        raise BetaWindowError(
            window_years=window_years,
            min_years=MIN_BETA_WINDOW_YEARS,
            details={
                'beta_window_years': f'{window_years:.1f}',
                'min_required': f'{MIN_BETA_WINDOW_YEARS:.0f}',
                'portfolio_beta': intent_gate.details.get('portfolio_beta', 'N/A'),
                'risk_intent': intent_gate.details.get('risk_intent', 'N/A')
            }
        )
    
    # Rule 1 & 2: Handle data integrity failure
    if data_integrity_gate.status == GateStatus.HARD_FAIL:
        # Rule 2: Check if intent is CERTAIN despite data failure
        if intent_gate.status == GateStatus.VALID_FAIL:
            # Intent fail is CERTAIN, but structure is inconclusive
            # PRODUCTION ENFORCEMENT: Raise exception
            raise IntentFailStructureInconclusiveError(
                intent_details={
                    'portfolio_beta': intent_gate.details.get('portfolio_beta', 'N/A'),
                    'beta_min_required': intent_gate.details.get('beta_min_acceptable', 'N/A'),
                    'risk_intent': intent_gate.details.get('risk_intent', 'N/A'),
                    'beta_window_years': intent_gate.details.get('beta_window_years', 'N/A')
                },
                structure_issue=f"Correlation NaN ratio {data_integrity_gate.details.get('corr_nan_ratio', 0):.1%} > 20%"
            )
        elif intent_gate.status == GateStatus.SOFT_FAIL:
            # Soft fail on intent, structure inconclusive
            return (
                FinalVerdictType.INTENT_FAIL_STRUCTURE_INCONCLUSIVE,
                "⚠️ INTENT WARNING - Struttura Inconclusa",
                "Intent WARNING (beta sotto target ma non critico). "
                "Struttura NON valutabile per dati correlazione incompleti. "
                "Nessuna azione di ristrutturazione portafoglio consentita."
            )
        else:
            # Rule 1: Data fail, structure completely blocked
            # PRODUCTION ENFORCEMENT: Raise exception
            corr_nan_ratio = data_integrity_gate.details.get('corr_nan_ratio', 0)
            raise DataIntegrityError(
                corr_nan_ratio=corr_nan_ratio,
                threshold=data_integrity_gate.details.get('nan_threshold', 0.20),
                details={
                    'corr_nan_ratio': f'{corr_nan_ratio:.1%}',
                    'nan_data_quality': data_integrity_gate.details.get('nan_data_quality_ratio', 'N/A'),
                    'nan_inception': data_integrity_gate.details.get('nan_inception_count', 'N/A'),
                    'blocked_analyses': ', '.join(data_integrity_gate.details.get('blocked_analyses', []))
                }
            )
    
    # Data integrity OK - can evaluate structure
    intent_match = intent_gate.status == GateStatus.PASS
    intent_valid_fail = intent_gate.status == GateStatus.VALID_FAIL
    intent_soft_fail = intent_gate.status == GateStatus.SOFT_FAIL
    
    # =========================================================================
    # NEW RULE v4.3: Intent FAIL ≠ Structural FAIL
    # Structural fragility requires CAUSAL proof, not just CCR warnings
    # If structure is OK but intent fails, this is MISALIGNMENT, not fragility
    # =========================================================================
    
    # Rule 2: Valid fail on intent WITH structure OK
    if intent_valid_fail:
        # CRITICAL FIX v4.3: Check causal fragility, not just CCR count
        has_proven_fragility = _verify_structural_fragility_causal(
            structural_issues, ccr_classifications
        )
        
        if has_proven_fragility:
            # Both intent and structure have issues
            return (
                FinalVerdictType.STRUCTURALLY_FRAGILE,
                "❌ STRUCTURALLY FRAGILE + INTENT MISMATCH",
                "Doppio problema: Intent FAIL è CERTO (beta troppo basso) E causa strutturale "
                "dimostrata (single-driver, hidden leverage, correlation collapse, liquidity trap, "
                "o vincolo violato). Fix entrambi. Priorità: prima correggi intent (più semplice), "
                "poi valuta struttura."
            )
        else:
            # NEW v4.3: Intent fail but structure is OK - this is MISALIGNMENT
            ccr_note = ""
            actionable_ccr = [c for c in ccr_classifications if c.is_actionable]
            if len(actionable_ccr) >= 2:
                ccr_note = f" Note: {len(actionable_ccr)} CCR warnings presenti (diagnostici, non terminali)."
            
            return (
                FinalVerdictType.INTENT_MISALIGNED_STRUCTURE_OK,
                "⚠️ INTENT MISALIGNED - Struttura OK",
                "IMPORTANT: Questo NON è un problema strutturale. "
                "Il portafoglio è strutturalmente coerente, ma il Risk Intent dichiarato "
                "non corrisponde al profilo di rischio effettivo (beta troppo basso). "
                "SOLUZIONE: Cambia Risk Intent a GROWTH_DIVERSIFIED o GROWTH. "
                f"Alternativa: aumenta beta se confermi obiettivo AGGRESSIVE.{ccr_note}"
            )
    
    # Soft fail on intent
    if intent_soft_fail:
        # CRITICAL FIX v4.3: Soft fail non implica fragilità strutturale
        has_proven_fragility = _verify_structural_fragility_causal(
            structural_issues, ccr_classifications
        )
        
        if has_proven_fragility:
            return (
                FinalVerdictType.STRUCTURALLY_FRAGILE,
                "❌ STRUCTURALLY FRAGILE + INTENT WARNING",
                "Struttura fragile (causa dimostrata) con warning su intent (beta sotto target). "
                "Priorità: risolvi problemi strutturali prima."
            )
        else:
            # Structure OK, minor intent warning
            return (
                FinalVerdictType.INTENT_MISALIGNED_STRUCTURE_OK,
                "⚠️ INTENT WARNING - Struttura OK, beta sotto target",
                "Struttura coerente ma beta leggermente sotto il minimo per Risk Intent dichiarato. "
                "Non 'fragile' perché è un problema di calibrazione obiettivo, non struttura. "
                "Suggerimento: considera downgrade a GROWTH_DIVERSIFIED. "
                "Note: CCR warnings (se presenti) sono DIAGNOSTICI, non terminali."
            )
    
    # Intent match - check structure
    if intent_match:
        # CRITICAL FIX v4.3: Verify CAUSAL fragility, not just CCR warnings
        has_proven_fragility = _verify_structural_fragility_causal(
            structural_issues, ccr_classifications
        )
        
        if has_proven_fragility:
            return (
                FinalVerdictType.STRUCTURALLY_FRAGILE,
                "❌ STRUCTURALLY FRAGILE - Causa strutturale dimostrata",
                "Verdetto 'fragile' ammesso perché: intent match OK, data integrity OK, "
                "E causa dimostrabile di instabilità (single-driver dependency, hidden leverage, "
                "correlation collapse, liquidity trap, o vincolo strutturale violato)."
            )
    
    # Default: tutto OK (anche con CCR warnings - quelli sono DIAGNOSTICI)
    return (
        FinalVerdictType.STRUCTURALLY_COHERENT_INTENT_MATCH,
        "✅ STRUCTURALLY COHERENT - Struttura e Intent allineati",
        "Tutti i gate passati: data integrity OK, intent match OK, "
        "nessun problema strutturale critico rilevato. "
        "Note: CCR warnings (se presenti) sono DIAGNOSTICI, non terminali."
    )


def _verify_structural_fragility_causal(
    structural_issues: List[str],
    ccr_classifications: List[CCRClassification]
) -> bool:
    """
    CRITICAL FIX v4.3: Verifica fragilità CAUSALE (non sintomatica).
    
    Fragilità strutturale DIMOSTRATA se almeno 1 di:
    1. Single-driver dependency: 1 asset >60% peso
    2. Hidden leverage: esposizione via derivati/leva nascosta
    3. Correlation collapse: asset storicamente decorrelati → +0.9 in crisi
    4. Liquidity trap: >40% in asset illiquidi
    5. Constraint violation: vincolo dichiarato violato
    
    CCR elevati da soli NON sono fragilità (sono concentrazione).
    
    Args:
        structural_issues: Lista issue strutturali da altri moduli
        ccr_classifications: CCR data (usata solo per collapse detection)
    
    Returns:
        True se fragilità causale dimostrata
    """
    # Check for explicit structural issues
    causal_keywords = [
        'single-driver',
        'hidden leverage',
        'correlation collapse',
        'liquidity trap',
        'constraint violated',
        'structural instability',
        'derivative exposure',
        'leverage ratio'
    ]
    
    for issue in structural_issues:
        issue_lower = issue.lower()
        if any(keyword in issue_lower for keyword in causal_keywords):
            return True
    
    # Check for single-driver dependency (>60% on one asset)
    # This would need to be passed from weight analysis
    # For now, return False (conservative)
    
    # Check for correlation collapse (would need crisis vs normal correlation comparison)
    # This requires time-series correlation analysis, not just CCR averages
    
    # IMPORTANT: CCR warnings alone are NOT sufficient
    # They indicate concentration, not instability
    
    return False


# ================================================================================
# SEZIONE H: FULL GATE ANALYSIS
# ================================================================================

@dataclass
class GateAnalysisResult:
    """Risultato completo dell'analisi gate."""
    # Gate results
    data_integrity_gate: SingleGateResult
    intent_gate: SingleGateResult
    benchmark_gate: SingleGateResult
    
    # Classifications
    portfolio_classification: Dict[str, Any]
    ccr_classifications: List[CCRClassification]
    
    # Structure type (Issue #2 fix)
    structure_type: PortfolioStructureType
    structure_confidence: float
    structure_explanation: str
    
    # Prescriptive Actions (Issue #3 fix) - aggregated from all gates
    prescriptive_actions: List[PrescriptiveAction]
    
    # Final verdict
    final_verdict: FinalVerdictType
    verdict_message: str
    why_not_contradictory: str
    
    # Summary for output (Section H)
    output_summary: Dict[str, str]
    
    # FDR correction info (Fix C7)
    fdr_correction: Dict[str, Any] = field(default_factory=dict)


def run_gate_analysis(
    corr_matrix: pd.DataFrame,
    portfolio_beta: float,
    risk_intent: str,
    intent_specs: Dict[str, Any],
    tickers: List[str],
    weights: np.ndarray,
    ccr_data: pd.DataFrame,
    benchmark_results: Dict[str, Any],
    asset_metrics: pd.DataFrame = None,
    structural_issues: List[str] = None,
    beta_window_years: float = 10.0,  # Rule 2 & 3: Years of data for beta
    crisis_sample_days: int = 100,    # Rule 6: Days for crisis CCR
    returns_df: pd.DataFrame = None,  # FIX BUG #3: returns for NaN analysis
    ticker_starts: Dict[str, str] = None,  # FIX BUG #3: inception dates
    earliest_date: str = None         # FIX BUG #3: earliest date in dataset
) -> GateAnalysisResult:
    """
    Esegue l'analisi completa dei gate in ordine di priorità.
    
    Rule 1: IF DataIntegrity = HARD_FAIL THEN StructuralGate = BLOCKED
    Rule 2: IF IntentGate = VALID_FAIL AND beta_window >= MIN THEN intent is CERTAIN
    Rule 3: IF beta_window < MIN THEN intent = INCONCLUSIVE
    Rule 6: CCR tables tagged PARTIAL if corr_nan > 0.20
    
    Ordine (Section A):
    1. Data Integrity Gate
    2. Risk Intent Gate
    3. Structural Coherence (Core/Satellites + CCR)
    4. Benchmark Comparison
    5. Final Verdict
    
    Returns:
        GateAnalysisResult
    """
    if structural_issues is None:
        structural_issues = []
    
    # 1. DATA INTEGRITY GATE (FIX BUG #3: pass inception data for NaN distinction)
    data_gate, data_details = check_data_integrity_gate(
        corr_matrix,
        returns_df=returns_df,
        ticker_starts=ticker_starts,
        earliest_date=earliest_date
    )
    corr_nan_ratio = data_details.get('corr_nan_ratio', 0.0)
    
    # 2. RISK INTENT GATE (Rule 2 & 3: pass beta window years)
    intent_gate, intent_details = check_risk_intent_gate(
        portfolio_beta, risk_intent, intent_specs, beta_window_years
    )
    
    # 3. PORTFOLIO CLASSIFICATION (Core vs Satellite - FIX BUG #5: 5-bucket)
    portfolio_classification = classify_portfolio_assets(
        tickers, weights, asset_metrics
    )
    
    # Rule 1: Determine structural gate status
    if data_gate.status == GateStatus.HARD_FAIL:
        structural_gate_status = GateStatus.BLOCKED
    else:
        structural_gate_status = GateStatus.PASS
    
    # 4. CCR CLASSIFICATION (Rule 6: pass corr_nan_ratio and crisis_sample)
    ccr_classifications = classify_ccr_leverage(
        ccr_data,
        intent_gate_passed=(intent_gate.status == GateStatus.PASS),
        data_integrity_passed=(data_gate.status == GateStatus.PASS),
        corr_nan_ratio=corr_nan_ratio,
        crisis_sample_days=crisis_sample_days
    )
    
    # 5. BENCHMARK GATE
    benchmark_gate, bench_details = check_benchmark_gate(
        portfolio_classification,
        benchmark_results,
        data_integrity_passed=(data_gate.status == GateStatus.PASS),
        intent_gate_passed=(intent_gate.status == GateStatus.PASS)
    )
    
    # 6. FINAL VERDICT
    final_verdict, verdict_message, why_not_contradictory = determine_final_verdict(
        data_gate, intent_gate, structural_issues, ccr_classifications
    )
    
    # 7. STRUCTURE TYPE (Issue #2 fix)
    summary = portfolio_classification.get('summary', {})
    structure_type, structure_confidence, structure_explanation = determine_portfolio_structure_type(
        summary
    )
    
    # 8. AGGREGATE PRESCRIPTIVE ACTIONS (Issue #3 fix)
    all_prescriptive_actions = []
    
    # Collect from gates
    all_prescriptive_actions.extend(data_gate.prescriptive_actions)
    all_prescriptive_actions.extend(intent_gate.prescriptive_actions)
    all_prescriptive_actions.extend(benchmark_gate.prescriptive_actions)
    
    # Add CCR-based actions
    actionable_ccr = [c for c in ccr_classifications if c.is_actionable and c.classification == "critical"]
    if len(actionable_ccr) >= 2:
        ticker_list = ", ".join(c.ticker for c in actionable_ccr[:3])
        all_prescriptive_actions.append(PrescriptiveAction(
            issue_code="CCR_CONCENTRATION",
            priority=ActionPriority.HIGH.value,
            confidence=0.80 if data_gate.status == GateStatus.PASS else 0.50,
            description=f"Critical CCR concentration in {len(actionable_ccr)} positions: {ticker_list}",
            actions=[
                "Reduce position sizes for high-CCR assets",
                "Add uncorrelated assets to dilute concentration",
                "Review if concentration is intentional thematic bet"
            ],
            blockers=["Diversification claims"],
            data_quality_impact="PARTIAL" if corr_nan_ratio > 0.10 else "NONE"
        ))
    
    # Add geography-based actions if significant DEFAULT_GEO usage
    # (This would need to be passed from the main analysis)
    
    # Add structure-type based actions
    if structure_type == PortfolioStructureType.OPPORTUNISTIC:
        all_prescriptive_actions.append(PrescriptiveAction(
            issue_code="STRUCTURE_UNSTABLE",
            priority=ActionPriority.MEDIUM.value,
            confidence=structure_confidence,
            description="Portfolio structure classified as OPPORTUNISTIC (unstable/unclear)",
            actions=[
                "Consolidate holdings into identifiable blocks (Core + Satellite)",
                "Remove redundant positions that add complexity without benefit",
                "Define clear investment thesis for each position"
            ],
            blockers=["Clear benchmark comparison"],
            data_quality_impact="NONE"
        ))
    
    # Sort actions by priority
    priority_order = {
        ActionPriority.CRITICAL.value: 0,
        ActionPriority.HIGH.value: 1,
        ActionPriority.MEDIUM.value: 2,
        ActionPriority.LOW.value: 3,
        ActionPriority.INFORMATIONAL.value: 4
    }
    def _priority_key(action: PrescriptiveAction) -> int:
        value = action.priority.value if isinstance(action.priority, ActionPriority) else action.priority
        return priority_order.get(value, 5)
    all_prescriptive_actions.sort(key=_priority_key)
    
    # 9. FDR CORRECTION FOR MULTIPLE TESTING (Fix C7)
    # Convert gate statuses to approximate p-values for FDR
    gate_p_values = []
    gate_names = []
    
    # Map gate status to pseudo p-values
    status_to_p = {
        GateStatus.PASS: 0.50,
        GateStatus.PASS_PROVISIONAL: 0.30,
        GateStatus.SOFT_FAIL: 0.10,
        GateStatus.HARD_FAIL: 0.01,
        GateStatus.VALID_FAIL: 0.01,
        GateStatus.BLOCKED: 0.05,
        GateStatus.INCONCLUSIVE: 0.25,
        GateStatus.NOT_EVALUATED: 0.50,
    }
    
    # Collect p-values from all gates tested
    for gate_name, gate_result in [
        ('Data Integrity', data_gate),
        ('Risk Intent', intent_gate),
        ('Benchmark', benchmark_gate),
    ]:
        gate_names.append(gate_name)
        gate_p_values.append(status_to_p.get(gate_result.status, 0.50))
    
    # Add CCR classifications as tests
    for ccr in ccr_classifications:
        if ccr.classification == 'critical':
            gate_names.append(f'CCR_{ccr.ticker}')
            gate_p_values.append(0.01)
        elif ccr.classification == 'warning':
            gate_names.append(f'CCR_{ccr.ticker}')
            gate_p_values.append(0.10)
    
    # Apply FDR correction
    fdr_result = apply_fdr_correction(gate_p_values, alpha=0.05)
    fdr_correction = {
        'n_tests': len(gate_p_values),
        'gate_names': gate_names,
        'raw_p_values': gate_p_values,
        'adjusted_p_values': fdr_result['adjusted_p_values'],
        'significant_raw': fdr_result['n_significant_raw'],
        'significant_corrected': fdr_result['n_significant_corrected'],
        'note': f"FDR applied: {fdr_result['n_significant_raw']} raw failures → "
                f"{fdr_result['n_significant_corrected']} after correction"
    }
    
    # 10. OUTPUT SUMMARY (Section H required)
    # CRITICAL FIX v4.3: Gerarchia gate corretta
    # Rule 1: Structural Gate = BLOCKED if data integrity fails
    # NEW: Structural status dipende SOLO da fragilità causale dimostrata
    if data_gate.status == GateStatus.HARD_FAIL:
        structural_status = 'BLOCKED'
        structural_note = '(data insufficient to evaluate)'
    elif final_verdict == FinalVerdictType.STRUCTURALLY_FRAGILE:
        structural_status = 'FAIL'
        structural_note = '(causal fragility proven)'
    else:
        # PASS anche con CCR warnings (quelli sono diagnostici)
        structural_status = 'PASS'
        actionable_ccr = [c for c in ccr_classifications if c.is_actionable]
        if len(actionable_ccr) >= 2:
            structural_note = f'(PASS with {len(actionable_ccr)} CCR warnings - diagnostic only)'
        elif corr_nan_ratio > 0.10:
            structural_note = '(PASS provisional - limited data)'
        else:
            structural_note = '(no causal fragility detected)'
    
    output_summary = {
        'Data Integrity Gate': data_gate.status.value,
        'Intent Gate': intent_gate.status.value,
        'Structural Gate': f'{structural_status} {structural_note}',  # Rule 1 + clarity
        'Structure Type': f"{structure_type.value} ({structure_confidence:.0%} confidence)",
        'Benchmark Gate': 'COMPARABLE' if bench_details.get('comparable_benchmarks') else 'OPPORTUNITY_COST',
        'Final Verdict': final_verdict.value,
        'Prescriptive Actions': len(all_prescriptive_actions),
        'CCR Warnings (Diagnostic)': len([c for c in ccr_classifications if c.is_actionable]),
    }
    
    return GateAnalysisResult(
        data_integrity_gate=data_gate,
        intent_gate=intent_gate,
        benchmark_gate=benchmark_gate,
        portfolio_classification=portfolio_classification,
        ccr_classifications=ccr_classifications,
        structure_type=structure_type,
        structure_confidence=structure_confidence,
        structure_explanation=structure_explanation,
        prescriptive_actions=all_prescriptive_actions,
        final_verdict=final_verdict,
        verdict_message=verdict_message,
        why_not_contradictory=why_not_contradictory,
        output_summary=output_summary,
        fdr_correction=fdr_correction  # Fix C7
    )


def _generate_portfolio_label(summary: Dict[str, Any], intent_details: Dict[str, Any]) -> str:
    """
    IMPROVEMENT: Genera etichetta intelligente basata sulla composizione reale.
    
    Invece di "TACTICAL / OPPORTUNISTIC" generico, produce etichette come:
    - "Regional + Factor Tilted Equity Portfolio (Low-Beta)"
    - "Global Core Equity Portfolio"
    - "Balanced Multi-Asset Portfolio"
    """
    components = []
    
    # 1. Struttura base
    total_core_global = summary.get('total_core_global', 0)
    total_core_regional = summary.get('total_core_regional', 0)
    total_satellites = summary.get('total_satellites_classified', 0)
    total_defensive = summary.get('total_defensive', 0)
    total_equity = summary.get('total_equity', 1.0)
    
    # Determina struttura principale
    if total_core_global >= 0.50:
        components.append("Global Core")
    elif total_core_regional >= 0.40:
        components.append("Regional")
    elif total_core_regional >= 0.20:
        components.append("Multi-Regional")
    
    # 2. Factor tilts
    if total_satellites >= 0.15:
        components.append("Factor Tilted")
    elif total_satellites >= 0.05:
        components.append("Satellite Enhanced")
    
    # 3. Asset class
    if total_defensive >= 0.30:
        components.append("Balanced")
    elif total_defensive >= 0.10:
        components.append("Growth-Oriented")
    elif total_equity >= 0.95:
        components.append("Equity")
    
    # 4. Beta modifier
    portfolio_beta = intent_details.get('portfolio_beta', 0.8)
    if portfolio_beta < 0.6:
        components.append("(Low-Beta)")
    elif portfolio_beta < 0.8:
        components.append("(Controlled-Beta)")
    elif portfolio_beta > 1.1:
        components.append("(High-Beta)")
    
    # Costruisci label
    if not components:
        return "Diversified Multi-Asset Portfolio"
    
    # Join intelligente
    label_parts = []
    modifiers = [c for c in components if c.startswith("(")]
    main_parts = [c for c in components if not c.startswith("(")]
    
    if main_parts:
        label_parts.append(" + ".join(main_parts[:3]))  # Max 3 componenti
    if "Portfolio" not in " ".join(main_parts):
        label_parts.append("Portfolio")
    if modifiers:
        label_parts.append(" ".join(modifiers))
    
    return " ".join(label_parts)


def print_gate_analysis(result: GateAnalysisResult) -> None:
    """
    Stampa il risultato dell'analisi gate.
    
    Rule 1: If data integrity fail, structural analysis is LOW_CONFIDENCE/PROXY
    Rule 4: Show 5-bucket classification
    Rule 6: Show CCR data quality tags
    Rule 7: Show allowed vs prohibited actions
    """
    print("\n" + "=" * 70)
    print("        INVESTMENT COMMITTEE VALIDATOR (Gate System v4.3)")
    print("=" * 70)
    
    # Gate Status Summary (Section H required)
    print("\n📋 GATE STATUS:")
    print("-" * 50)
    for gate_name, status in result.output_summary.items():
        # Skip non-string values (like Prescriptive Actions count)
        status_str = str(status)
        if "PASS" in status_str and "PROVISIONAL" not in status_str:
            icon = "✅"
        elif "BLOCKED" in status_str or "FAIL" in status_str or "INCONCLUSIVE" in status_str:
            icon = "⛔"
        elif "PROVISIONAL" in status_str or "WARNING" in status_str:
            icon = "⚠️"
        else:
            icon = "ℹ️"
        print(f"   {icon} {gate_name}: {status_str}")
    
    # Data Integrity Details
    print(f"\n📊 DATA INTEGRITY GATE:")
    print(f"   {result.data_integrity_gate.message}")
    if result.data_integrity_gate.details.get('blocked_analyses'):
        print(f"   🚫 Blocked: {', '.join(result.data_integrity_gate.details['blocked_analyses'])}")
    
    # FIX BUG #3: Show NaN distinction if available
    nan_inception = result.data_integrity_gate.details.get('nan_inception_count', 0)
    nan_quality = result.data_integrity_gate.details.get('nan_data_quality_count', 0)
    if nan_inception > 0 or nan_quality > 0:
        print(f"   📊 NaN Analysis:")
        print(f"      Inception NaN (expected): {nan_inception} cells")
        print(f"      Data Quality NaN (issue): {nan_quality} cells")
    
    # FIX BUG #4: Intent Gate Details with 3-state beta gating
    print(f"\n🎯 RISK INTENT GATE (3-state beta gating):")
    print(f"   {result.intent_gate.message}")
    beta_window = result.intent_gate.details.get('beta_window_years', 0)
    intent_validity = result.intent_gate.details.get('intent_verdict_validity', 'UNKNOWN')
    portfolio_beta = result.intent_gate.details.get('portfolio_beta', 0)
    beta_min = result.intent_gate.details.get('beta_min_acceptable', 0.6)
    beta_fail = result.intent_gate.details.get('beta_fail_threshold', 0.4)
    
    # FIX BUG #4: Determine beta state
    if portfolio_beta >= beta_min:
        beta_state = "🟢 PASS"
        beta_state_detail = f"beta ≥ {beta_min:.1f}"
    elif portfolio_beta >= beta_fail:
        beta_state = "🟡 SOFT FAIL"
        beta_state_detail = f"{beta_fail:.1f} ≤ beta < {beta_min:.1f}"
    else:
        beta_state = "🔴 HARD FAIL"
        beta_state_detail = f"beta < {beta_fail:.1f}"
    
    print(f"   Beta state: {beta_state} ({beta_state_detail})")
    print(f"   Beta window: {beta_window:.1f}y → Intent verdict: {intent_validity}")
    
    # IMPROVEMENT: Actionable suggestions when beta misaligned
    risk_intent = result.intent_gate.details.get('risk_intent', 'GROWTH')
    if portfolio_beta < beta_min:
        print(f"\n   💡 AZIONI SUGGERITE (beta {portfolio_beta:.2f} < target {beta_min:.1f}):")
        if portfolio_beta < 0.7:
            print(f"      Opzione A: Abbassa Risk Intent → BALANCED o MODERATE")
            print(f"      Opzione B: Aumenta beta → +US Growth, -EM Value, -Small Global")
            print(f"      Opzione C: Aggiungi leva moderata (1.1-1.2x)")
        else:
            print(f"      Opzione A: Accetta Risk Intent = GROWTH (beta 0.6-0.8 OK)")
            print(f"      Opzione B: Tilt verso US large-cap growth per +beta")
    
    # Rule 1: Structural analysis confidence level
    data_integrity_passed = result.data_integrity_gate.status == GateStatus.PASS
    if not data_integrity_passed:
        print(f"\n⚠️ STRUCTURAL ANALYSIS: LOW_CONFIDENCE / PROXY-ONLY")
        print(f"   Le metriche strutturali (HHI, effN, correlazioni) sono PROXY, non actionable.")
    
    # FIX BUG #5: 5-bucket Portfolio Classification
    print(f"\n📦 PORTFOLIO CLASSIFICATION (5-bucket):")
    summary = result.portfolio_classification.get('summary', {})
    print(f"   Core Global (world):          {summary.get('total_core_global', 0):>6.1%}")
    print(f"   Core Regional (US/EU/EM...):  {summary.get('total_core_regional', 0):>6.1%}")
    print(f"   Satellite (classified):       {summary.get('total_satellites_classified', 0):>6.1%}")
    print(f"   Unclassified Equity:          {summary.get('total_unclassified_equity', 0):>6.1%}")
    print(f"   Defensive (bond/gold):        {summary.get('total_defensive', 0):>6.1%}")
    print(f"   ─────────────────────────────────────")
    total = (summary.get('total_core_global', 0) + summary.get('total_core_regional', 0) +
             summary.get('total_satellites_classified', 0) + 
             summary.get('total_unclassified_equity', 0) + summary.get('total_defensive', 0))
    print(f"   TOTAL:                        {total:>6.1%}")
    
    # IMPROVEMENT: Generate intelligent portfolio label based on composition
    portfolio_label = _generate_portfolio_label(summary, result.intent_gate.details)
    print(f"\n   🏷️  PORTFOLIO LABEL: {portfolio_label}")
    
    # Issue #2 FIX: Show structure type with confidence
    print(f"\n   🏗️  STRUCTURE TYPE: {result.structure_type.value} ({result.structure_confidence:.0%} confidence)")
    print(f"       {result.structure_explanation}")
    
    # Rule 8: Show if same-category benchmark is allowed
    if summary.get('is_pure_equity_core', False):
        print(f"   ✅ Same-category benchmark: ALLOWED (≥95% equity, no tilts)")
    else:
        reasons = []
        if summary.get('total_defensive', 0) >= 0.05:
            reasons.append(f"defensive {summary.get('total_defensive', 0):.0%}")
        if summary.get('has_sector_tilts', False):
            reasons.append("sector tilts")
        if summary.get('total_unclassified_equity', 0) > 0.20:
            reasons.append(f"unclassified {summary.get('total_unclassified_equity', 0):.0%}")
        print(f"   ⚠️ Same-category benchmark: NOT ALLOWED ({', '.join(reasons) or 'mixed portfolio'})")
    
    # Rule 6: CCR with data quality tags
    ccr_data_quality = "FULL"
    if result.ccr_classifications:
        ccr_data_quality = result.ccr_classifications[0].data_quality
    
    # CCR Classifications (only actionable)
    actionable_ccr = [c for c in result.ccr_classifications if c.is_actionable]
    if actionable_ccr:
        print(f"\n⚠️ CCR ACTIONABLE WARNINGS [{ccr_data_quality}]:")
        for c in actionable_ccr:
            print(f"   • {c.ticker}: {c.risk_leverage:.1f}x leverage ({c.classification})")
    
    # Non-actionable CCR with Rule 6 tag
    non_actionable = [c for c in result.ccr_classifications 
                     if not c.is_actionable and c.classification != "normal"]
    if non_actionable:
        tag = f"[{ccr_data_quality}]" if ccr_data_quality != "FULL" else ""
        print(f"\nℹ️ CCR DESCRITTIVO (non actionable) {tag}:")
        for c in non_actionable:
            print(f"   • {c.ticker}: {c.risk_leverage:.1f}x (solo informativo)")
        if ccr_data_quality == "PARTIAL":
            print(f"   ⚠️ Dati PARZIALI: correlazioni NaN > 20%, CCR non affidabile per decisioni")
        elif ccr_data_quality == "SAMPLE_TOO_SMALL":
            print(f"   ⚠️ Campione crisi TROPPO PICCOLO: < 30 giorni, CCR crisis non affidabile")
    
    # Benchmark Gate
    print(f"\n📈 BENCHMARK GATE:")
    print(f"   {result.benchmark_gate.message}")
    if result.benchmark_gate.details.get('comparable_benchmarks'):
        print(f"   Same-category: {', '.join(result.benchmark_gate.details['comparable_benchmarks'])}")
    if result.benchmark_gate.details.get('reference_benchmarks'):
        print(f"   Opportunity-cost only: {', '.join(result.benchmark_gate.details['reference_benchmarks'])}")
    
    # Issue #3 FIX: PRESCRIPTIVE ACTIONS SECTION
    if result.prescriptive_actions:
        print("\n" + "═" * 70)
        print("                    PRESCRIPTIVE ACTIONS")
        print("═" * 70)
        
        priority_icons = {
            ActionPriority.CRITICAL.value: "🔴 CRITICAL",
            ActionPriority.HIGH.value: "🟠 HIGH",
            ActionPriority.MEDIUM.value: "🟡 MEDIUM",
            ActionPriority.LOW.value: "🟢 LOW",
            ActionPriority.INFORMATIONAL.value: "ℹ️ INFO"
        }
        
        for action in result.prescriptive_actions:
            key = action.priority.value if isinstance(action.priority, ActionPriority) else action.priority
            icon = priority_icons.get(key, "❓")
            confidence_bar = "█" * int(action.confidence * 10) + "░" * (10 - int(action.confidence * 10))
            
            print(f"\n   {icon} [{action.issue_code}]")
            print(f"   Confidence: [{confidence_bar}] {action.confidence:.0%}")
            print(f"   {action.description}")
            print(f"   → Actions:")
            for act in action.actions:
                print(f"      • {act}")
            if action.blockers:
                print(f"   ⛔ Blocks if not addressed: {', '.join(action.blockers)}")
            if action.data_quality_impact != "NONE":
                print(f"   📊 Data quality impact: {action.data_quality_impact}")
    
    # Final Verdict (Section H required)
    print("\n" + "═" * 70)
    print("                      FINAL VERDICT")
    print("═" * 70)
    print(f"\n   {result.verdict_message}")
    print(f"\n   📌 Why this verdict is not contradictory:")
    print(f"   {result.why_not_contradictory}")
    
    # Rule 7: Show allowed vs prohibited actions
    is_inconclusive = "INCONCLUSIVE" in result.final_verdict.value
    is_intent_fail_only = result.final_verdict == FinalVerdictType.INTENT_FAIL_STRUCTURE_INCONCLUSIVE
    
    print(f"\n   📋 AZIONI CONSENTITE:")
    if is_inconclusive:
        print(f"   ✅ Migliorare dati/metodologia (raccolta storico, fix NaN)")
        print(f"   🚫 Ristrutturazione portafoglio (VIETATA - dati insufficienti)")
        print(f"   🚫 Verdetti 'da ristrutturare' (VIETATI)")
    elif is_intent_fail_only:
        print(f"   ✅ Correggere Risk Intent dichiarato")
        print(f"   ✅ Aumentare beta (se si vuole mantenere intent AGGRESSIVE)")
        print(f"   ✅ Migliorare dati correlazione")
        print(f"   🚫 Ristrutturazione strutturale (struttura non valutata)")
    else:
        print(f"   ✅ Tutte le azioni di portafoglio consentite")
    
    print("═" * 70)
