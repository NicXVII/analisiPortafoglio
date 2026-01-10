"""
Models Module
=============
Dataclasses per type safety e validazione strutturale.

Sostituisce i dict non tipizzati con strutture validate.

Part of Production Readiness Issue #2: Type Safety Migration
Part of Production Readiness Issue #3: Structured Output
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from enum import Enum
import numpy as np
import pandas as pd
import json


# ================================================================================
# ENUMS
# ================================================================================

class RiskIntentLevel(str, Enum):
    """Risk intent levels for portfolio classification."""
    CONSERVATIVE = "CONSERVATIVE"
    MODERATE = "MODERATE"
    BALANCED = "BALANCED"
    GROWTH = "GROWTH"
    GROWTH_DIVERSIFIED = "GROWTH_DIVERSIFIED"
    AGGRESSIVE = "AGGRESSIVE"
    HIGH_BETA = "HIGH_BETA"


class FinalVerdictType(str, Enum):
    """
    Verdetti finali MUTUAMENTE ESCLUSIVI (Section G).
    
    REGOLA: Solo UNO di questi può essere il verdetto finale.
    
    NEW RULE (v4.2): Intent FAIL ≠ Structural FAIL
    - INTENT_MISALIGNED_STRUCTURE_OK: Structure is fine, only intent label is wrong
    - This is NOT a failure, it's a labeling issue requiring realignment
    """
    STRUCTURALLY_COHERENT_INTENT_MATCH = "STRUCTURALLY_COHERENT_INTENT_MATCH"
    STRUCTURALLY_COHERENT_INTENT_MISMATCH = "STRUCTURALLY_COHERENT_INTENT_MISMATCH"
    STRUCTURALLY_FRAGILE = "STRUCTURALLY_FRAGILE"
    INTENT_MISALIGNED_STRUCTURE_OK = "INTENT_MISALIGNED_STRUCTURE_OK"
    INCONCLUSIVE_DATA_FAIL = "INCONCLUSIVE_DATA_FAIL"
    INCONCLUSIVE_INTENT_DATA = "INCONCLUSIVE_INTENT_DATA"
    INTENT_FAIL_STRUCTURE_INCONCLUSIVE = "INTENT_FAIL_STRUCTURE_INCONCLUSIVE"


class PortfolioStructureType(str, Enum):
    """
    Classificazione struttura portafoglio (Issue #2 fix).
    
    Invece di TACTICAL/OPPORTUNISTIC generico, usa etichette precise:
    - GLOBAL_CORE: ≥50% in global broad-market ETFs
    - EQUITY_MULTI_BLOCK: 0% Core Global ma struttura regionale stabile
    - EQUITY_DIVERSIFIED_MIXED: Mixed equity diversification, stable structure
    - FACTOR_TILTED: Core + significant factor exposure
    - SECTOR_CONCENTRATED: Heavy sector/thematic exposure
    - BALANCED: Significant defensive allocation
    - OPPORTUNISTIC: Unstable structure, high turnover implied
    """
    GLOBAL_CORE = "GLOBAL_CORE"                   # VT, VWCE dominant
    EQUITY_MULTI_BLOCK = "EQUITY_MULTI_BLOCK"     # Regional blocks without global core
    EQUITY_DIVERSIFIED_MIXED = "EQUITY_DIVERSIFIED_MIXED"  # Mixed equity without dominant pattern
    FACTOR_TILTED = "FACTOR_TILTED"               # Core + factor satellites
    SECTOR_CONCENTRATED = "SECTOR_CONCENTRATED"  # Heavy sector bets
    BALANCED = "BALANCED"                         # Equity + defensive mix
    DEFENSIVE = "DEFENSIVE"                       # Primarily bonds/gold
    OPPORTUNISTIC = "OPPORTUNISTIC"               # High unclassified, unstable


class BenchmarkCategory(str, Enum):
    """Benchmark comparison category."""
    SAME_CATEGORY = "SAME_CATEGORY"
    OPPORTUNITY_COST = "OPPORTUNITY_COST"


# ================================================================================
# PORTFOLIO CONFIGURATION
# ================================================================================

@dataclass
class PortfolioConfig:
    """
    Configurazione del portafoglio da analizzare.
    
    Validazione:
    - tickers e weights devono avere stessa lunghezza
    - weights vengono normalizzati a somma 1
    - years_history > 0
    """
    tickers: List[str]
    weights: List[float]
    years_history: int = 5
    end_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    start_date: Optional[str] = None
    risk_free_annual: float = 0.02
    rebalance: Optional[str] = None  # None, 'daily', 'monthly', 'quarterly', 'yearly'
    var_confidence: float = 0.95
    
    def __post_init__(self):
        # Validazione
        if len(self.tickers) != len(self.weights):
            raise ValueError(f"tickers ({len(self.tickers)}) e weights ({len(self.weights)}) devono avere stessa lunghezza")
        
        if len(self.tickers) == 0:
            raise ValueError("Portfolio deve avere almeno 1 ticker")
        
        if self.years_history <= 0:
            raise ValueError("years_history deve essere > 0")
        
        if not 0 < self.var_confidence < 1:
            raise ValueError("var_confidence deve essere tra 0 e 1")
        
        # Normalizza weights
        total = sum(self.weights)
        if total <= 0:
            raise ValueError("Somma weights deve essere > 0")
        self.weights = [w / total for w in self.weights]
    
    @property
    def weights_array(self) -> np.ndarray:
        """Restituisce weights come numpy array."""
        return np.array(self.weights, dtype=float)


# ================================================================================
# METRICS OUTPUT
# ================================================================================

@dataclass
class ConfidenceInterval:
    """Intervallo di confidenza per una metrica."""
    point_estimate: float
    ci_lower: float
    ci_upper: float
    confidence: float = 0.95
    se: Optional[float] = None
    n_observations: Optional[int] = None
    
    def __str__(self) -> str:
        return f"{self.point_estimate:.2%} [{self.ci_lower:.2%}, {self.ci_upper:.2%}]"


@dataclass
class DrawdownInfo:
    """Informazioni su un drawdown."""
    value: float  # Es: -0.50 per -50%
    peak_date: datetime
    trough_date: datetime
    recovery_date: Optional[datetime] = None
    duration_days: Optional[int] = None
    recovery_days: Optional[int] = None


@dataclass
class PortfolioMetrics:
    """
    Metriche complete del portafoglio.
    
    Tutte le metriche sono tipizzate e documentate.
    """
    # Performance
    total_roi: float
    cagr: float
    volatility: float
    
    # Risk-adjusted
    sharpe: float
    sortino: float
    calmar: float
    
    # Drawdown
    max_drawdown: float
    max_dd_peak: datetime
    max_dd_trough: datetime
    avg_drawdown: float
    current_drawdown: float
    
    # VaR/CVaR (daily)
    var_95_daily: float
    cvar_95_daily: float
    var_95_annual: float
    cvar_95_annual: float
    
    # Statistics
    months_up: int
    months_down: int
    months_total: int
    years_up: int
    years_down: int
    years_total: int
    days_up: int
    days_down: int
    days_total: int
    
    # Best/Worst
    best_month: float
    worst_month: float
    avg_month: float
    best_year: float
    worst_year: float
    best_day: float
    worst_day: float
    
    # Ratios
    gain_loss_ratio: float
    profit_factor: float
    win_rate_monthly: float
    
    # Confidence intervals (opzionali)
    cagr_ci: Optional[ConfidenceInterval] = None
    sharpe_ci: Optional[ConfidenceInterval] = None
    max_dd_ci: Optional[ConfidenceInterval] = None
    
    # Time series (opzionali, per analisi dettagliata)
    equity_curve: Optional[pd.Series] = None
    returns: Optional[pd.Series] = None


# ================================================================================
# REGIME INFO
# ================================================================================

@dataclass
class CrisisPeriod:
    """Periodo di crisi con metadati."""
    name: str
    start_date: str
    end_date: str
    trigger: str  # Descrizione osservata (non auto-detected)
    
    def overlaps(self, data_start: str, data_end: str) -> bool:
        """Verifica se la crisi overlap con il periodo dati."""
        return self.start_date <= data_end and self.end_date >= data_start


@dataclass
class MarketRegime:
    """Regime di mercato rilevato."""
    primary_regime: str  # "NORMAL", "INCLUDES_SYSTEMIC_CRISIS", etc.
    period_years: float
    detected_crises: List[CrisisPeriod]
    thresholds_applied: Dict[str, Tuple[float, float]]  # metrica -> (normal, crisis)
    
    @property
    def is_crisis_regime(self) -> bool:
        return self.primary_regime in ["INCLUDES_SYSTEMIC_CRISIS", "INCLUDES_TIGHTENING"]


# ================================================================================
# PORTFOLIO ANALYSIS RESULTS
# ================================================================================

@dataclass
class Issue:
    """Un singolo issue rilevato nell'analisi."""
    type: str  # "CONCENTRATION", "CORRELATION", "DRAWDOWN", etc.
    severity: str  # "🚨", "⚠️", "ℹ️"
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class RobustnessScore:
    """Score di robustezza del portafoglio."""
    score: int  # 0-100
    verdict: str  # "ROBUSTO", "COERENTE", "ACCETTABILE", "DA_RIVEDERE"
    verdict_detail: str
    breakdown: Dict[str, int]  # componente -> punti
    
    @property
    def is_acceptable(self) -> bool:
        return self.score >= 50


@dataclass
class PortfolioType:
    """Tipo di portafoglio identificato."""
    type_name: str  # "EQUITY_GROWTH_DIVERSIFIED", "BALANCED", etc.
    display_name: str  # "🌍 EQUITY GROWTH (Diversified)"
    confidence: float  # 0-1
    reason: str
    composition: Dict[str, float]  # categoria -> peso
    thresholds: Dict[str, float]  # metrica -> soglia


@dataclass 
class StressTestResults:
    """Risultati Monte Carlo stress test."""
    base_var_5: float
    base_var_1: float
    base_median: float
    base_worst: float
    
    highvol_var_5: float
    highvol_var_1: float
    highvol_worst: float
    
    crisis_corr_var_5: float
    crisis_corr_var_1: float
    crisis_corr_worst: float


@dataclass
class PortfolioAnalysisResult:
    """
    Risultato completo dell'analisi portafoglio.
    
    Raggruppa tutti i risultati in una struttura coerente.
    """
    config: PortfolioConfig
    metrics: PortfolioMetrics
    issues: List[Issue]
    portfolio_type: PortfolioType
    market_regime: Optional[MarketRegime]
    robustness_score: Optional[RobustnessScore]
    stress_test: Optional[StressTestResults]
    
    # Data metadata
    data_start: str
    data_end: str
    trading_days: int
    
    @property
    def final_verdict(self) -> str:
        """Restituisce il verdetto finale."""
        if self.robustness_score:
            return self.robustness_score.verdict
        return "UNKNOWN"


# ================================================================================
# HELPER FUNCTIONS
# ================================================================================

def metrics_dict_to_dataclass(metrics: dict) -> PortfolioMetrics:
    """
    Converte un dict di metriche in PortfolioMetrics dataclass.
    
    Utile per la transizione dal codice legacy.
    """
    # Estrai confidence intervals se presenti
    cagr_ci = None
    if 'cagr_ci' in metrics and metrics['cagr_ci']:
        ci = metrics['cagr_ci']
        cagr_ci = ConfidenceInterval(
            point_estimate=ci.get('point_estimate', metrics['cagr']),
            ci_lower=ci.get('ci_lower', 0),
            ci_upper=ci.get('ci_upper', 0),
            confidence=ci.get('confidence', 0.95)
        )
    
    sharpe_ci = None
    if 'sharpe_ci' in metrics and metrics['sharpe_ci']:
        ci = metrics['sharpe_ci']
        sharpe_ci = ConfidenceInterval(
            point_estimate=ci.get('point_estimate', metrics['sharpe']),
            ci_lower=ci.get('ci_lower', 0),
            ci_upper=ci.get('ci_upper', 0),
            confidence=ci.get('confidence', 0.95),
            se=ci.get('se'),
            n_observations=int(ci.get('n_years', 0) * 252) if ci.get('n_years') else None
        )
    
    max_dd_ci = None
    if 'max_dd_ci' in metrics and metrics['max_dd_ci']:
        ci = metrics['max_dd_ci']
        max_dd_ci = ConfidenceInterval(
            point_estimate=ci.get('point_estimate', metrics['max_drawdown']),
            ci_lower=ci.get('ci_lower', 0),
            ci_upper=ci.get('ci_upper', 0),
            confidence=ci.get('confidence', 0.95)
        )
    
    return PortfolioMetrics(
        total_roi=metrics['total_roi'],
        cagr=metrics['cagr'],
        volatility=metrics['volatility'],
        sharpe=metrics['sharpe'],
        sortino=metrics['sortino'],
        calmar=metrics['calmar'],
        max_drawdown=metrics['max_drawdown'],
        max_dd_peak=metrics['max_dd_peak'],
        max_dd_trough=metrics['max_dd_trough'],
        avg_drawdown=metrics['avg_drawdown'],
        current_drawdown=metrics['current_drawdown'],
        var_95_daily=metrics['var_95_daily'],
        cvar_95_daily=metrics['cvar_95_daily'],
        var_95_annual=metrics['var_95_annual'],
        cvar_95_annual=metrics['cvar_95_annual'],
        months_up=metrics['months_up'],
        months_down=metrics['months_down'],
        months_total=metrics['months_total'],
        years_up=metrics['years_up'],
        years_down=metrics['years_down'],
        years_total=metrics['years_total'],
        days_up=metrics['days_up'],
        days_down=metrics['days_down'],
        days_total=metrics['days_total'],
        best_month=metrics['best_month'],
        worst_month=metrics['worst_month'],
        avg_month=metrics['avg_month'],
        best_year=metrics['best_year'],
        worst_year=metrics['worst_year'],
        best_day=metrics['best_day'],
        worst_day=metrics['worst_day'],
        gain_loss_ratio=metrics['gain_loss_ratio'],
        profit_factor=metrics['profit_factor'],
        win_rate_monthly=metrics['win_rate_monthly'],
        cagr_ci=cagr_ci,
        sharpe_ci=sharpe_ci,
        max_dd_ci=max_dd_ci,
        equity_curve=metrics.get('equity_curve'),
        returns=metrics.get('returns')
    )


# ================================================================================
# GATE SYSTEM MODELS (Issue #2 - Type Safety Migration)
# ================================================================================

@dataclass(frozen=True)
class RiskIntentSpec:
    """
    Risk intent specification with beta ranges and thresholds.
    
    Replaces dict from get_risk_intent_spec().
    """
    level: RiskIntentLevel
    beta_range: Tuple[float, float]
    min_beta_acceptable: float
    beta_fail_threshold: float
    max_dd_expected: float
    benchmark: str
    description: str
    vol_expected: Optional[Tuple[float, float]] = None  # Optional volatility range
    
    def is_beta_in_range(self, beta: float) -> bool:
        """Check if beta is within expected range."""
        return self.beta_range[0] <= beta <= self.beta_range[1]
    
    def is_beta_acceptable(self, beta: float) -> bool:
        """Check if beta meets minimum acceptable threshold."""
        return beta >= self.min_beta_acceptable
    
    def is_beta_fail(self, beta: float) -> bool:
        """Check if beta is below fail threshold."""
        return beta < self.beta_fail_threshold


@dataclass
class DataQuality:
    """
    Data quality metrics for portfolio analysis.
    
    Replaces data_integrity dict in gate_system.py
    """
    nan_ratio: float
    earliest_date: datetime
    latest_date: datetime
    trading_days: int
    overlapping_days: int
    staggered_entry: bool
    partial_tickers: List[str] = field(default_factory=list)
    nan_count: int = 0
    
    @property
    def is_pass(self) -> bool:
        """Check if data quality passes 20% threshold."""
        return self.nan_ratio <= 0.20
    
    @property
    def is_warning(self) -> bool:
        """Check if data quality in warning zone (10-20%)."""
        return 0.10 < self.nan_ratio <= 0.20
    
    def __str__(self) -> str:
        status = "PASS" if self.is_pass else "FAIL"
        return f"DataQuality({status}, NaN={self.nan_ratio:.1%}, days={self.trading_days})"


@dataclass
class ComponentRisk:
    """Risk contribution for a single asset."""
    ticker: str
    weight: float
    mcr: float  # Marginal Contribution to Risk
    ccr: float  # Component Contribution to Risk
    ccr_percent: float  # CCR as percentage of total risk
    
    @property
    def risk_leverage(self) -> float:
        """Risk leverage = CCR% / Weight%."""
        return self.ccr_percent / self.weight if self.weight > 0 else 0.0
    
    def __str__(self) -> str:
        return f"{self.ticker}: {self.ccr_percent:.1%} risk from {self.weight:.1%} weight (leverage={self.risk_leverage:.1f}x)"


@dataclass
class IntentGateCheck:
    """Risk intent gate validation result."""
    portfolio_beta: float
    intent_spec: RiskIntentSpec
    beta_window_years: float
    verdict: str  # "PASS", "INTENT_MISMATCH", "INCONCLUSIVE"
    confidence_score: int
    beta_state: str  # "PASS", "SOFT_FAIL", "HARD_FAIL"
    is_valid: bool  # Whether verdict is conclusive (>= 3 years)
    
    @property
    def is_pass(self) -> bool:
        return self.verdict == "PASS"
    
    @property
    def is_fail(self) -> bool:
        return self.verdict == "INTENT_MISMATCH"
    
    @property
    def is_inconclusive(self) -> bool:
        return self.verdict == "INCONCLUSIVE"


@dataclass
class StructuralGateCheck:
    """Structural coherence validation result."""
    structure_type: PortfolioStructureType
    confidence: float
    max_position: float
    top3_concentration: float
    hhi: float
    effective_positions: float
    verdict: str  # "PASS", "WARNING", "FAIL"
    issues: List[str] = field(default_factory=list)
    
    @property
    def is_pass(self) -> bool:
        return self.verdict == "PASS"


@dataclass
class BenchmarkComparison:
    """Benchmark comparison result."""
    benchmark_name: str
    category: BenchmarkCategory
    portfolio_cagr: float
    benchmark_cagr: float
    excess_return: float
    portfolio_sharpe: float
    benchmark_sharpe: float
    tracking_error: float
    information_ratio: float
    beta: float
    alpha: float
    verdict: str
    
    def __str__(self) -> str:
        return (f"{self.benchmark_name}: {self.verdict} "
                f"(excess={self.excess_return:+.2%}, IR={self.information_ratio:.2f})")


@dataclass
class GateResult:
    """
    Complete Gate System validation result.
    
    Replaces the gate_result dict returned by run_gate_analysis().
    
    This is the CENTRAL model for Issue #2 migration.
    All gate_system.py output will gradually migrate to this structure.
    """
    # Core gates
    data_quality: DataQuality
    intent_check: IntentGateCheck
    structural_check: StructuralGateCheck
    
    # Final verdict
    final_verdict: FinalVerdictType
    verdict_confidence: int
    
    # Benchmark analysis
    benchmark_comparisons: List[BenchmarkComparison] = field(default_factory=list)
    
    # Risk contributions
    component_risks: List[ComponentRisk] = field(default_factory=list)
    
    # Prescriptive actions
    actions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Override information (if applied)
    override_applied: bool = False
    override_details: Optional[Dict[str, Any]] = None
    
    # Portfolio classification
    portfolio_classification: Optional[Dict[str, Any]] = None
    
    @property
    def is_intent_misaligned(self) -> bool:
        """Check if verdict is intent mismatch."""
        return self.final_verdict == FinalVerdictType.INTENT_MISALIGNED_STRUCTURE_OK
    
    @property
    def is_inconclusive(self) -> bool:
        """Check if verdict is any INCONCLUSIVE type."""
        return self.final_verdict.value.startswith('INCONCLUSIVE')
    
    def to_dict(self) -> dict:
        """
        Convert to dict for backward compatibility during migration.
        
        This allows gradual migration where some code still expects dicts.
        Returns a dict that matches the current gate_system.py output format.
        """
        return {
            'verdict': self.final_verdict.value,
            'confidence': self.verdict_confidence,
            'data_quality': {
                'nan_ratio': self.data_quality.nan_ratio,
                'trading_days': self.data_quality.trading_days,
                'earliest_date': self.data_quality.earliest_date,
                'latest_date': self.data_quality.latest_date,
                'overlapping_days': self.data_quality.overlapping_days,
                'staggered_entry': self.data_quality.staggered_entry,
            },
            'intent_check': {
                'portfolio_beta': self.intent_check.portfolio_beta,
                'verdict': self.intent_check.verdict,
                'confidence': self.intent_check.confidence_score,
                'beta_window_years': self.intent_check.beta_window_years,
            },
            'structural_check': {
                'structure_type': self.structural_check.structure_type.value,
                'confidence': self.structural_check.confidence,
                'verdict': self.structural_check.verdict,
            },
            'benchmark_comparisons': [
                {
                    'name': b.benchmark_name,
                    'category': b.category.value,
                    'excess_return': b.excess_return,
                    'verdict': b.verdict,
                }
                for b in self.benchmark_comparisons
            ],
            'actions': self.actions,
            'override_applied': self.override_applied,
            'override_details': self.override_details,
            'portfolio_classification': self.portfolio_classification,
        }
    
    def __str__(self) -> str:
        """Rich string representation for debugging."""
        return (f"GateResult(\n"
                f"  verdict={self.final_verdict.value},\n"
                f"  confidence={self.verdict_confidence}/100,\n"
                f"  data_quality={self.data_quality},\n"
                f"  intent={self.intent_check.verdict},\n"
                f"  structure={self.structural_check.verdict}\n"
                f")")

# ================================================================================
# STRUCTURED OUTPUT (Issue #3)
# ================================================================================

@dataclass
class MetricsSnapshot:
    """
    Machine-readable metrics snapshot.
    
    Part of Issue #3: Structured Output for programmatic validation.
    """
    # Core performance
    cagr: float
    sharpe: float
    sortino: float
    max_drawdown: float
    volatility: float
    
    # Risk metrics
    var_95: float
    cvar_95: float
    
    # Confidence intervals (optional)
    cagr_ci_lower: Optional[float] = None
    cagr_ci_upper: Optional[float] = None
    sharpe_ci_lower: Optional[float] = None
    sharpe_ci_upper: Optional[float] = None
    
    # Additional metrics
    calmar_ratio: Optional[float] = None
    profit_factor: Optional[float] = None
    win_rate_monthly: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass  
class PrescriptiveAction:
    """
    Actionable recommendation with priority and confidence.
    
    Part of Issue #3: Structured recommendations for programmatic processing.
    """
    issue_code: str  # "INTENT_MISMATCH", "GEO_UNKNOWN", "CONCENTRATION", etc.
    priority: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"
    confidence: float  # 0.0-1.0
    description: str
    actions: List[str]
    blockers: List[str] = field(default_factory=list)
    data_quality_impact: str = "NONE"  # "NONE", "PARTIAL", "UNRELIABLE"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class AnalysisResult:
    """
    Complete machine-readable analysis result.
    
    Part of Issue #3: Structured Output.
    
    This is the main output object for programmatic validation:
    - Used by automated systems to parse results
    - Contains quality flags for filtering unreliable analyses
    - JSON-serializable for API integration
    """
    # Core verdict
    verdict: FinalVerdictType
    verdict_message: str
    verdict_confidence: int  # 0-100
    
    # Portfolio identification
    risk_intent: str
    structure_type: PortfolioStructureType
    portfolio_composition: Dict[str, float]  # {ticker: weight}
    
    # Metrics
    metrics: MetricsSnapshot
    
    # Quality flags (Issue #1 integration)
    is_actionable: bool  # False if INCONCLUSIVE
    data_quality_issues: List[str]
    quality_score: int  # 0-100 overall quality
    
    # Recommendations
    prescriptive_actions: List[PrescriptiveAction]
    allowed_actions: List[str]
    prohibited_actions: List[str]
    
    # Metadata
    analysis_timestamp: datetime
    portfolio_id: Optional[str] = None
    
    def is_inconclusive(self) -> bool:
        """Check if verdict is INCONCLUSIVE (requires override)."""
        return "INCONCLUSIVE" in self.verdict.value
    
    def is_pass(self) -> bool:
        """Check if verdict is a passing verdict."""
        return self.verdict in [
            FinalVerdictType.STRUCTURALLY_COHERENT_INTENT_MATCH,
            FinalVerdictType.INTENT_MISALIGNED_STRUCTURE_OK,
        ]
    
    def is_fail(self) -> bool:
        """Check if verdict is a hard failure."""
        return self.verdict in [
            FinalVerdictType.STRUCTURALLY_FRAGILE,
            FinalVerdictType.INTENT_FAIL_STRUCTURE_INCONCLUSIVE,
        ]
    
    def validate_for_production(self) -> Tuple[bool, List[str]]:
        """
        Validate if result is safe for production deployment.
        
        Returns:
            Tuple[bool, List[str]]: (is_valid, issues)
        """
        issues = []
        
        # Check 1: INCONCLUSIVE blocks production
        if self.is_inconclusive():
            issues.append(
                f"INCONCLUSIVE verdict ({self.verdict.value}) - "
                "requires explicit override with UserAcknowledgment"
            )
        
        # Check 2: Too many data quality issues
        if len(self.data_quality_issues) >= 3:
            issues.append(
                f"{len(self.data_quality_issues)} data quality issues detected - "
                "analysis may be unreliable"
            )
        
        # Check 3: Low quality score
        if self.quality_score < 50:
            issues.append(
                f"Quality score {self.quality_score}/100 is too low for production use"
            )
        
        # Check 4: Critical actions without data
        critical_actions = [
            a for a in self.prescriptive_actions 
            if a.priority == "CRITICAL"
        ]
        if len(critical_actions) > 0 and not self.is_actionable:
            issues.append(
                f"{len(critical_actions)} CRITICAL actions flagged but analysis "
                "is marked as not actionable"
            )
        
        return len(issues) == 0, issues
    
    def to_json(self, indent: int = 2) -> str:
        """
        Export to JSON for programmatic use.
        
        Args:
            indent: JSON indentation level (None for compact)
        
        Returns:
            JSON string
        """
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary (JSON-serializable).
        
        Returns:
            Dictionary with all analysis results
        """
        return {
            "verdict": {
                "type": self.verdict.value,
                "message": self.verdict_message,
                "confidence": self.verdict_confidence,
            },
            "portfolio": {
                "risk_intent": self.risk_intent,
                "structure_type": self.structure_type.value,
                "composition": self.portfolio_composition,
            },
            "metrics": self.metrics.to_dict(),
            "quality": {
                "is_actionable": self.is_actionable,
                "issues": self.data_quality_issues,
                "score": self.quality_score,
            },
            "recommendations": {
                "prescriptive_actions": [a.to_dict() for a in self.prescriptive_actions],
                "allowed_actions": self.allowed_actions,
                "prohibited_actions": self.prohibited_actions,
            },
            "metadata": {
                "timestamp": self.analysis_timestamp.isoformat(),
                "portfolio_id": self.portfolio_id,
            },
        }
    
    def save_json(self, filepath: str) -> None:
        """
        Save analysis result to JSON file.
        
        Args:
            filepath: Path to output JSON file
        """
        with open(filepath, 'w') as f:
            f.write(self.to_json())
    
    def __str__(self) -> str:
        """Human-readable summary."""
        status = "✅ PASS" if self.is_pass() else "❌ FAIL" if self.is_fail() else "⚠️ INCONCLUSIVE"
        return (
            f"AnalysisResult(\n"
            f"  verdict={status} - {self.verdict.value}\n"
            f"  quality_score={self.quality_score}/100\n"
            f"  is_actionable={self.is_actionable}\n"
            f"  metrics=(CAGR={self.metrics.cagr:.1%}, Sharpe={self.metrics.sharpe:.2f})\n"
            f"  actions={len(self.prescriptive_actions)} prescriptive\n"
            f")"
        )
