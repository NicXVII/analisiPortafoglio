"""
Confidence Intervals and Statistical Corrections
=================================================
FDR correction, confidence intervals via bootstrap.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple


# =========================
# MULTIPLE TESTING CORRECTION (Fix C7)
# =========================

def apply_fdr_correction(p_values: List[float], alpha: float = 0.05) -> Dict[str, Any]:
    """
    Apply Benjamini-Hochberg False Discovery Rate correction for multiple testing.
    
    When running multiple hypothesis tests (e.g., 7 gate checks), the probability
    of at least one false positive increases. FDR controls the expected proportion
    of false positives among rejected hypotheses.
    
    Args:
        p_values: List of p-values from multiple tests
        alpha: Desired FDR level (default 0.05 = 5% expected false discoveries)
        
    Returns:
        Dict with:
        - 'adjusted_p_values': BH-adjusted p-values
        - 'significant': Boolean array of which tests remain significant
        - 'n_significant_raw': Number significant before correction
        - 'n_significant_corrected': Number significant after correction
        - 'fdr_threshold': The BH critical threshold used
    """
    n = len(p_values)
    if n == 0:
        return {'adjusted_p_values': [], 'significant': [], 'n_significant_raw': 0, 
                'n_significant_corrected': 0, 'fdr_threshold': alpha}
    
    # Sort p-values and track original indices
    sorted_indices = np.argsort(p_values)
    sorted_p = np.array(p_values)[sorted_indices]
    
    # Benjamini-Hochberg procedure
    # Critical values: (i/n) * alpha for i = 1, ..., n
    critical_values = np.arange(1, n + 1) / n * alpha
    
    # Find largest i where p[i] <= (i/n) * alpha
    significant_sorted = sorted_p <= critical_values
    
    # Adjusted p-values (Benjamini-Hochberg)
    adjusted_p = np.zeros(n)
    for i in range(n - 1, -1, -1):
        if i == n - 1:
            adjusted_p[sorted_indices[i]] = min(sorted_p[i] * n / (i + 1), 1.0)
        else:
            adjusted_p[sorted_indices[i]] = min(
                sorted_p[i] * n / (i + 1),
                adjusted_p[sorted_indices[i + 1]]
            )
    
    # Determine which are significant after correction
    significant = adjusted_p <= alpha
    
    return {
        'adjusted_p_values': adjusted_p.tolist(),
        'significant': significant.tolist(),
        'n_significant_raw': sum(np.array(p_values) <= alpha),
        'n_significant_corrected': sum(significant),
        'fdr_threshold': alpha,
        'inflation_factor': n,  # How many tests were run
        'note': f"FDR correction applied for {n} simultaneous tests"
    }


def calculate_gate_p_values(gate_results: Dict[str, Any]) -> List[Tuple[str, float]]:
    """
    Convert gate test results to approximate p-values for FDR correction.
    
    This is a heuristic conversion since gates aren't formal hypothesis tests.
    Maps gate status to approximate p-values:
    - PASS: p = 0.5 (null hypothesis not rejected)
    - SOFT_FAIL/WARNING: p = 0.10 (marginal)
    - HARD_FAIL: p = 0.01 (strong rejection)
    - INCONCLUSIVE: p = 0.25 (uncertain)
    
    Args:
        gate_results: Dictionary with gate names as keys and results as values
        
    Returns:
        List of (gate_name, p_value) tuples
    """
    p_value_map = {
        'PASS': 0.50,
        'SOFT_FAIL': 0.10,
        'WARNING': 0.10,
        'HARD_FAIL': 0.01,
        'VALID_FAIL': 0.01,
        'INCONCLUSIVE': 0.25,
    }
    
    results = []
    for gate_name, gate_data in gate_results.items():
        if isinstance(gate_data, dict):
            status = gate_data.get('status', 'PASS')
        else:
            status = str(gate_data)
        
        p_value = p_value_map.get(status, 0.50)
        results.append((gate_name, p_value))
    
    return results


# =========================
# CONFIDENCE INTERVALS
# =========================

def calculate_sharpe_confidence_interval(
    returns: pd.Series,
    risk_free_annual: float = 0.02,
    confidence: float = 0.95,
    n_bootstrap: int = 200  # Ridotto per performance
) -> Dict[str, float]:
    """
    Calcola Sharpe Ratio con confidence interval via bootstrap.
    
    Il Sharpe Ratio è stimato con incertezza significativa:
    - SE(Sharpe) ≈ sqrt((1 + 0.5*SR²) / n) dove n = anni di dati
    - Con 5 anni di dati, Sharpe 0.60 ha 95% CI ≈ [0.35, 0.85]
    
    Returns:
        Dict con 'point_estimate', 'ci_lower', 'ci_upper', 'se'
    """
    periods = 252
    n = len(returns)
    n_years = n / periods
    
    rf_daily = (1 + risk_free_annual) ** (1/periods) - 1
    
    # Point estimate
    excess = returns - rf_daily
    sharpe = excess.mean() / returns.std(ddof=1) * np.sqrt(periods) if returns.std() > 0 else 0
    
    # Standard Error analitico (Lo, 2002)
    # SE(SR) ≈ sqrt((1 + 0.5*SR²) / n_years)
    se_analytical = np.sqrt((1 + 0.5 * sharpe**2) / n_years) if n_years > 0 else 0
    
    # Bootstrap per robustezza
    bootstrap_sharpes = []
    for _ in range(n_bootstrap):
        # Resample con replacement
        sample = returns.sample(n=n, replace=True)
        excess_sample = sample - rf_daily
        sr = excess_sample.mean() / sample.std(ddof=1) * np.sqrt(periods) if sample.std() > 0 else 0
        bootstrap_sharpes.append(sr)
    
    alpha = 1 - confidence
    ci_lower = np.percentile(bootstrap_sharpes, alpha/2 * 100)
    ci_upper = np.percentile(bootstrap_sharpes, (1 - alpha/2) * 100)
    se_bootstrap = np.std(bootstrap_sharpes)
    
    return {
        "point_estimate": sharpe,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "se": se_bootstrap,
        "se_analytical": se_analytical,
        "n_years": n_years,
        "confidence": confidence,
    }


def calculate_cagr_confidence_interval(
    equity: pd.Series,
    confidence: float = 0.95,
    n_bootstrap: int = 200  # Ridotto per performance
) -> Dict[str, float]:
    """
    Calcola CAGR con confidence interval via block bootstrap.
    
    Usa block bootstrap per preservare autocorrelazione nei returns.
    
    Returns:
        Dict con 'point_estimate', 'ci_lower', 'ci_upper'
    """
    periods = 252
    n = len(equity)
    n_years = n / periods
    
    # Point estimate
    total_return = equity.iloc[-1] / equity.iloc[0]
    cagr = total_return ** (1 / n_years) - 1 if n_years > 0 else 0
    
    # Converti in returns per bootstrap
    returns = equity.pct_change().dropna()
    
    # Block bootstrap (block size = ~20 giorni per catturare autocorrelazione)
    block_size = min(20, len(returns) // 10)
    bootstrap_cagrs = []
    
    for _ in range(n_bootstrap):
        # Resample blocks
        n_blocks = len(returns) // block_size + 1
        blocks = []
        for _ in range(n_blocks):
            start = np.random.randint(0, len(returns) - block_size + 1)
            blocks.append(returns.iloc[start:start+block_size].values)
        
        sample_returns = np.concatenate(blocks)[:len(returns)]
        
        # Ricostruisci equity
        sample_equity = (1 + sample_returns).cumprod()
        sample_total = sample_equity[-1]
        sample_cagr = sample_total ** (1 / n_years) - 1 if n_years > 0 else 0
        bootstrap_cagrs.append(sample_cagr)
    
    alpha = 1 - confidence
    ci_lower = np.percentile(bootstrap_cagrs, alpha/2 * 100)
    ci_upper = np.percentile(bootstrap_cagrs, (1 - alpha/2) * 100)
    
    return {
        "point_estimate": cagr,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "se": np.std(bootstrap_cagrs),
        "n_years": n_years,
        "confidence": confidence,
    }


def calculate_max_dd_confidence_interval(
    equity: pd.Series,
    confidence: float = 0.95,
    n_bootstrap: int = 200  # Ridotto per performance
) -> Dict[str, float]:
    """
    Calcola Max Drawdown con confidence interval.
    
    Nota: Max DD è path-dependent, il bootstrap potrebbe sottostimare
    la variabilità. Usare con cautela.
    """
    # Point estimate
    peak = equity.cummax()
    drawdown = (equity - peak) / peak
    max_dd = drawdown.min()
    
    # Bootstrap
    returns = equity.pct_change().dropna()
    bootstrap_dds = []
    
    block_size = min(20, len(returns) // 10)
    
    for _ in range(n_bootstrap):
        n_blocks = len(returns) // block_size + 1
        blocks = []
        for _ in range(n_blocks):
            start = np.random.randint(0, len(returns) - block_size + 1)
            blocks.append(returns.iloc[start:start+block_size].values)
        
        sample_returns = np.concatenate(blocks)[:len(returns)]
        sample_equity = pd.Series((1 + sample_returns).cumprod())
        sample_peak = sample_equity.cummax()
        sample_dd = ((sample_equity - sample_peak) / sample_peak).min()
        bootstrap_dds.append(sample_dd)
    
    alpha = 1 - confidence
    # Nota: per drawdown, ci_lower è il worst case (più negativo)
    ci_lower = np.percentile(bootstrap_dds, alpha/2 * 100)
    ci_upper = np.percentile(bootstrap_dds, (1 - alpha/2) * 100)
    
    return {
        "point_estimate": max_dd,
        "ci_lower": ci_lower,  # worst plausible
        "ci_upper": ci_upper,  # best plausible
        "se": np.std(bootstrap_dds),
        "confidence": confidence,
    }
