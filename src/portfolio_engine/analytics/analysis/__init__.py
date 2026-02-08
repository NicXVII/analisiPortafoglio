"""
Analysis package
----------------
Thin wrappers for legacy analysis_monolith functions, to allow
backward-compatible imports while completing the split.
"""

from portfolio_engine.analytics.portfolio_analysis.type_detection import (
    detect_portfolio_type,
    get_type_thresholds,
    detect_portfolio_regime,
    get_regime_thresholds,
)
from portfolio_engine.analytics.analysis.issues import (
    detect_false_diversification,
    analyze_portfolio_issues,
    identify_structural_strengths,
    generate_verdict_bullets,
)
from portfolio_engine.analytics.portfolio_analysis.temporal import (
    calculate_temporal_decomposition,
)
from portfolio_engine.analytics.portfolio_analysis.resilience import (
    calculate_robustness_score,
    calculate_resilience_efficiency,
)

__all__ = [
    "detect_portfolio_type",
    "get_type_thresholds",
    "detect_portfolio_regime",
    "get_regime_thresholds",
    "detect_false_diversification",
    "analyze_portfolio_issues",
    "identify_structural_strengths",
    "generate_verdict_bullets",
    "calculate_temporal_decomposition",
    "calculate_robustness_score",
    "calculate_resilience_efficiency",
]
