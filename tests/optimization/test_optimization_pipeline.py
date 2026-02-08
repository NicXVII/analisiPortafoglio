import numpy as np
import pandas as pd

from portfolio_engine.core.optimization_runner import run_optimization_analysis


def test_run_optimization_analysis_returns_dict():
    np.random.seed(0)
    returns = pd.DataFrame(np.random.randn(252, 3) * 0.01, columns=["A", "B", "C"])
    weights = np.array([0.4, 0.3, 0.3])

    result = run_optimization_analysis(
        returns=returns,
        current_weights=weights,
        tickers=["A", "B", "C"],
        risk_free_rate=0.02,
        max_weight=0.7,
        n_frontier_points=5,
        enabled=True,
    )

    assert isinstance(result, dict)
    assert "frontier" in result
    assert result["frontier"].min_variance.success
