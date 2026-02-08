from .utils import compute_covariance_matrix, compute_expected_returns, portfolio_statistics
from .markowitz import (
    min_variance_portfolio,
    max_sharpe_portfolio,
    risk_parity_portfolio,
    _validate_inputs,
)
from .frontier import generate_efficient_frontier, analyze_current_vs_optimal
from .compat import (
    efficient_frontier,
    select_key_portfolios,
    simulate_portfolio_mc,
    simulate_portfolios_mc,
    run_frontier_with_mc,
)

__all__ = [
    "compute_covariance_matrix",
    "compute_expected_returns",
    "portfolio_statistics",
    "min_variance_portfolio",
    "max_sharpe_portfolio",
    "risk_parity_portfolio",
    "generate_efficient_frontier",
    "analyze_current_vs_optimal",
    "efficient_frontier",
    "select_key_portfolios",
    "simulate_portfolio_mc",
    "simulate_portfolios_mc",
    "run_frontier_with_mc",
]
