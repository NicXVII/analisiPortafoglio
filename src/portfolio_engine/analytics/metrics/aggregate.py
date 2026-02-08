"""
Aggregate portfolio metrics
---------------------------
Thin wrappers that defer import of metrics_monolith to avoid circular deps.
"""

__all__ = [
    "calculate_all_metrics",
    "calculate_shrunk_correlation",
    "calculate_benchmark_comparison",
    "run_monte_carlo_stress_test",
    "calculate_conditional_correlations",
]


def calculate_all_metrics(*args, **kwargs):
    from portfolio_engine.analytics import metrics_monolith as _m
    return _m.calculate_all_metrics(*args, **kwargs)


def calculate_shrunk_correlation(*args, **kwargs):
    from portfolio_engine.analytics import metrics_monolith as _m
    return _m.calculate_shrunk_correlation(*args, **kwargs)


def calculate_benchmark_comparison(*args, **kwargs):
    from portfolio_engine.analytics import metrics_monolith as _m
    return _m.calculate_benchmark_comparison(*args, **kwargs)


def run_monte_carlo_stress_test(*args, **kwargs):
    from portfolio_engine.analytics import metrics_monolith as _m
    return _m.run_monte_carlo_stress_test(*args, **kwargs)


def calculate_conditional_correlations(*args, **kwargs):
    from portfolio_engine.analytics import metrics_monolith as _m
    return _m.calculate_conditional_correlations(*args, **kwargs)
