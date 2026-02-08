"""
Metrics Submodule
=================
Portfolio metrics calculations - split from metrics_monolith.py

Modules:
- basic: Simple/log returns, CAGR, volatility
- risk: Sharpe, Sortino, Calmar, Drawdown, VaR/CVaR
- confidence: Confidence intervals, FDR correction
- contribution: Risk contribution (MCR, CCR)

All functions re-exported for backward compatibility.
"""

# Basic metrics
from portfolio_engine.analytics.metrics.basic import (
    calculate_simple_returns,
    calculate_log_returns,
    calculate_cagr,
    calculate_cagr_correct,  # alias
    calculate_annualized_volatility,
)

# Risk metrics  
from portfolio_engine.analytics.metrics.risk import (
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_calmar_ratio,
    calculate_max_drawdown,
    calculate_drawdown_series,
    analyze_multi_trough_recovery,
    calculate_var_cvar,
)

# Confidence intervals
from portfolio_engine.analytics.metrics.confidence import (
    apply_fdr_correction,
    calculate_gate_p_values,
    calculate_sharpe_confidence_interval,
    calculate_cagr_confidence_interval,
    calculate_max_dd_confidence_interval,
)

# Risk contribution
from portfolio_engine.analytics.metrics.contribution import (
    calculate_risk_contribution,
    calculate_risk_contribution_correct,  # alias
    calculate_conditional_risk_contribution,
)

# Aggregate helpers (backward-compat shim)
from portfolio_engine.analytics.metrics.aggregate import (
    calculate_all_metrics,
    calculate_shrunk_correlation,
    calculate_benchmark_comparison,
    run_monte_carlo_stress_test,
    calculate_conditional_correlations,
)


__all__ = [
    # Basic
    'calculate_simple_returns',
    'calculate_log_returns',
    'calculate_cagr',
    'calculate_cagr_correct',
    'calculate_annualized_volatility',
    # Risk
    'calculate_sharpe_ratio',
    'calculate_sortino_ratio',
    'calculate_calmar_ratio',
    'calculate_max_drawdown',
    'calculate_drawdown_series',
    'analyze_multi_trough_recovery',
    'calculate_var_cvar',
    # Confidence
    'apply_fdr_correction',
    'calculate_gate_p_values',
    'calculate_sharpe_confidence_interval',
    'calculate_cagr_confidence_interval',
    'calculate_max_dd_confidence_interval',
    # Contribution
    'calculate_risk_contribution',
    'calculate_risk_contribution_correct',
    'calculate_conditional_risk_contribution',
    # Aggregate
    'calculate_all_metrics',
    'calculate_shrunk_correlation',
    'calculate_benchmark_comparison',
    'run_monte_carlo_stress_test',
    'calculate_conditional_correlations',
]
