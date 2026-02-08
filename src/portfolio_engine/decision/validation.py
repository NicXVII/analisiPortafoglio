"""
Validation Module - Walk-Forward and Out-of-Sample Testing
===========================================================

Implements:
1. Dual-Correlation Framework (RAW for diagnosis, REG for calculations)
2. Walk-Forward Validation (expanding window)
3. Rolling Window Stability Analysis
4. Out-of-Sample Stress Testing

DESIGN PHILOSOPHY:
- RAW correlation: shows actual market relationships (noisy but honest)
- REG correlation: regularized for stable risk calculations
- Walk-forward: prevents overfitting by testing on unseen data
- Rolling windows: detect regime changes and parameter instability

References:
- Ledoit-Wolf (2004): Shrinkage estimation
- Bailey & López de Prado (2012): Walk-forward backtesting
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, List, Optional
from dataclasses import dataclass
from enum import Enum

from portfolio_engine.analytics.metrics.basic import calculate_cagr
from portfolio_engine.analytics.metrics.risk import calculate_max_drawdown, calculate_sharpe_ratio

# ================================================================================
# DUAL-CORRELATION FRAMEWORK
# ================================================================================

class CorrelationUseCase(Enum):
    """Defines when to use RAW vs REG correlation."""
    DIAGNOSIS = "RAW"      # Identifying actual relationships
    RISK_CALC = "REG"      # Portfolio variance, VaR
    DISPLAY = "RAW"        # Showing to user
    CCR = "REG"            # Contribution to risk (stability matters)
    DIVERSIFICATION = "RAW"  # Assessing real diversification


@dataclass
class DualCorrelationMatrix:
    """
    Container for both RAW and REG correlation matrices.
    
    Framework Rule:
    - corr_raw: Use for DIAGNOSIS (what's actually happening)
    - corr_reg: Use for CALCULATIONS (stable numbers)
    """
    corr_raw: pd.DataFrame
    corr_reg: pd.DataFrame
    shrinkage_intensity: float
    
    def get(self, use_case: CorrelationUseCase) -> pd.DataFrame:
        """Return appropriate matrix based on use case."""
        if use_case in [CorrelationUseCase.DIAGNOSIS, 
                        CorrelationUseCase.DISPLAY,
                        CorrelationUseCase.DIVERSIFICATION]:
            return self.corr_raw
        else:
            return self.corr_reg
    
    def get_diagnosis_summary(self) -> Dict[str, Any]:
        """
        Produce diagnosis using RAW correlations (honest view).
        
        Returns insights about:
        - High correlation pairs (false diversification)
        - Correlation clusters
        - Outlier relationships
        """
        raw = self.corr_raw.values
        n = len(self.corr_raw)
        
        # Find high correlation pairs (excluding diagonal)
        high_corr_pairs = []
        low_corr_pairs = []
        
        for i in range(n):
            for j in range(i+1, n):
                ticker_i = self.corr_raw.index[i]
                ticker_j = self.corr_raw.columns[j]
                rho = raw[i, j]
                
                if rho > 0.7:
                    high_corr_pairs.append((ticker_i, ticker_j, rho))
                elif rho < 0.2:
                    low_corr_pairs.append((ticker_i, ticker_j, rho))
        
        # Average correlation (off-diagonal)
        off_diag = raw[np.triu_indices(n, k=1)]
        avg_corr_raw = np.mean(off_diag)
        
        # Compare with REG
        reg = self.corr_reg.values
        off_diag_reg = reg[np.triu_indices(n, k=1)]
        avg_corr_reg = np.mean(off_diag_reg)
        
        return {
            "avg_corr_raw": avg_corr_raw,
            "avg_corr_reg": avg_corr_reg,
            "correlation_bias": avg_corr_reg - avg_corr_raw,
            "shrinkage_intensity": self.shrinkage_intensity,
            "high_corr_pairs": sorted(high_corr_pairs, key=lambda x: x[2], reverse=True)[:5],
            "low_corr_pairs": sorted(low_corr_pairs, key=lambda x: x[2])[:5],
            "n_high_corr": len(high_corr_pairs),
            "interpretation": self._interpret_shrinkage_impact()
        }
    
    def _interpret_shrinkage_impact(self) -> str:
        """Human-readable interpretation of shrinkage impact."""
        if self.shrinkage_intensity > 0.90:
            return ("CRITICAL: >90% shrinkage means RAW correlations are unreliable. "
                    "REG matrix is mostly identity-based. Diversification metrics "
                    "should be interpreted as THEORETICAL, not observed.")
        elif self.shrinkage_intensity > 0.50:
            return ("HIGH: 50-90% shrinkage indicates significant noise in RAW data. "
                    "Use REG for risk calculations, RAW for identifying outlier pairs.")
        elif self.shrinkage_intensity > 0.20:
            return ("MODERATE: 20-50% shrinkage is typical for small portfolios. "
                    "Both RAW and REG are usable, prefer REG for stability.")
        else:
            return ("LOW: <20% shrinkage means RAW correlations are reliable. "
                    "REG and RAW should produce similar results.")


def create_dual_correlation(returns: pd.DataFrame, 
                           corr_raw: pd.DataFrame, 
                           corr_shrunk: pd.DataFrame,
                           shrinkage_delta: float) -> DualCorrelationMatrix:
    """Factory function to create DualCorrelationMatrix."""
    return DualCorrelationMatrix(
        corr_raw=corr_raw,
        corr_reg=corr_shrunk,
        shrinkage_intensity=shrinkage_delta if shrinkage_delta else 0.0
    )


# ================================================================================
# WALK-FORWARD VALIDATION
# ================================================================================

@dataclass
class WalkForwardResult:
    """Results from walk-forward validation."""
    in_sample_metrics: Dict[str, float]
    out_of_sample_metrics: Dict[str, float]
    is_sharpe_stable: bool
    is_drawdown_stable: bool
    stability_score: float  # 0-100
    interpretation: str
    details: List[Dict[str, Any]]


def run_walk_forward_validation(
    prices: pd.DataFrame,
    weights: np.ndarray,
    tickers: List[str],
    n_splits: int = 3,
    train_ratio: float = 0.7,
    risk_free_annual: float = 0.0,
    sharpe_autocorr_lags: int | None = None
) -> WalkForwardResult:
    """
    Walk-forward validation with expanding window.
    
    Splits data into train/test periods and compares metrics.
    Detects if in-sample performance is unrealistically good.
    
    Args:
        prices: Price DataFrame
        weights: Portfolio weights
        tickers: List of ticker symbols
        n_splits: Number of walk-forward splits
        train_ratio: Initial train/test ratio
        risk_free_annual: Annual risk-free rate for Sharpe calculations
        sharpe_autocorr_lags: Optional autocorrelation lag adjustment for Sharpe
        
    Returns:
        WalkForwardResult with stability metrics
    """
    n_obs = len(prices)
    if n_obs < 252 * 2:  # Need at least 2 years
        return WalkForwardResult(
            in_sample_metrics={},
            out_of_sample_metrics={},
            is_sharpe_stable=True,  # Insufficient data to judge
            is_drawdown_stable=True,
            stability_score=50.0,
            interpretation="Insufficient data for walk-forward validation (need 2+ years)",
            details=[]
        )
    
    returns = prices.pct_change().dropna()
    portfolio_returns = (returns * weights).sum(axis=1)
    
    split_results = []
    
    for split_idx in range(n_splits):
        # Expanding window
        train_end_idx = int(n_obs * (train_ratio + split_idx * (1 - train_ratio) / n_splits))
        test_start_idx = train_end_idx
        test_end_idx = min(n_obs, test_start_idx + int(n_obs * (1 - train_ratio) / n_splits))
        
        if test_end_idx <= test_start_idx:
            continue
            
        # Split portfolio returns
        train_ret = portfolio_returns.iloc[:train_end_idx]
        test_ret = portfolio_returns.iloc[test_start_idx:test_end_idx]
        
        if len(train_ret) < 126 or len(test_ret) < 63:  # Min 6 months train, 3 months test
            continue
        
        # Calculate metrics for each period
        train_metrics = _calc_period_metrics(
            train_ret, risk_free_annual=risk_free_annual, sharpe_autocorr_lags=sharpe_autocorr_lags
        )
        test_metrics = _calc_period_metrics(
            test_ret, risk_free_annual=risk_free_annual, sharpe_autocorr_lags=sharpe_autocorr_lags
        )
        
        split_results.append({
            "split": split_idx + 1,
            "train_period": f"{train_ret.index[0].date()} to {train_ret.index[-1].date()}",
            "test_period": f"{test_ret.index[0].date()} to {test_ret.index[-1].date()}",
            "train_days": len(train_ret),
            "test_days": len(test_ret),
            "train_sharpe": train_metrics["sharpe"],
            "test_sharpe": test_metrics["sharpe"],
            "train_cagr": train_metrics["cagr"],
            "test_cagr": test_metrics["cagr"],
            "train_maxdd": train_metrics["max_dd"],
            "test_maxdd": test_metrics["max_dd"],
        })
    
    if not split_results:
        return WalkForwardResult(
            in_sample_metrics={},
            out_of_sample_metrics={},
            is_sharpe_stable=True,
            is_drawdown_stable=True,
            stability_score=50.0,
            interpretation="Could not create valid train/test splits",
            details=[]
        )
    
    # Aggregate results
    avg_train_sharpe = np.mean([r["train_sharpe"] for r in split_results])
    avg_test_sharpe = np.mean([r["test_sharpe"] for r in split_results])
    avg_train_maxdd = np.mean([r["train_maxdd"] for r in split_results])
    avg_test_maxdd = np.mean([r["test_maxdd"] for r in split_results])
    
    # Stability checks
    sharpe_ratio = avg_test_sharpe / avg_train_sharpe if avg_train_sharpe > 0 else 0
    is_sharpe_stable = sharpe_ratio >= 0.5  # Test Sharpe >= 50% of train
    
    dd_ratio = abs(avg_test_maxdd / avg_train_maxdd) if avg_train_maxdd != 0 else 1
    is_drawdown_stable = dd_ratio <= 2.0  # Test DD not more than 2x train
    
    # Overall stability score (0-100)
    stability_score = 0
    stability_score += 25 if sharpe_ratio >= 0.8 else (15 if sharpe_ratio >= 0.5 else 0)
    stability_score += 25 if dd_ratio <= 1.5 else (15 if dd_ratio <= 2.0 else 0)
    stability_score += 25 if avg_test_sharpe > 0 else 0
    stability_score += 25 if avg_test_maxdd > -0.30 else (15 if avg_test_maxdd > -0.50 else 0)
    
    interpretation = _interpret_walk_forward(
        sharpe_ratio, dd_ratio, avg_test_sharpe, stability_score
    )
    
    return WalkForwardResult(
        in_sample_metrics={
            "sharpe": avg_train_sharpe,
            "cagr": np.mean([r["train_cagr"] for r in split_results]),
            "max_dd": avg_train_maxdd
        },
        out_of_sample_metrics={
            "sharpe": avg_test_sharpe,
            "cagr": np.mean([r["test_cagr"] for r in split_results]),
            "max_dd": avg_test_maxdd
        },
        is_sharpe_stable=is_sharpe_stable,
        is_drawdown_stable=is_drawdown_stable,
        stability_score=stability_score,
        interpretation=interpretation,
        details=split_results
    )


def _calc_period_metrics(
    returns: pd.Series,
    risk_free_annual: float = 0.0,
    sharpe_autocorr_lags: int | None = None
) -> Dict[str, float]:
    """Calculate basic metrics for a return series."""
    if len(returns) < 20:
        return {"sharpe": 0, "cagr": 0, "max_dd": 0, "vol": 0}
    
    ann_vol = returns.std(ddof=1) * np.sqrt(252)
    sharpe = calculate_sharpe_ratio(
        returns,
        risk_free_annual=risk_free_annual,
        periods=252,
        autocorr_lags=sharpe_autocorr_lags
    )
    
    # CAGR
    cum_ret = (1 + returns).cumprod()
    # Use real calendar span when available for consistency
    cagr = calculate_cagr(cum_ret, periods_per_year=None)
    
    # Max drawdown
    max_dd, _, _ = calculate_max_drawdown(cum_ret)
    
    return {
        "sharpe": sharpe,
        "cagr": cagr,
        "max_dd": max_dd,
        "vol": ann_vol
    }


def _interpret_walk_forward(sharpe_ratio: float, dd_ratio: float, 
                           test_sharpe: float, stability_score: float) -> str:
    """Generate human-readable interpretation."""
    messages = []
    
    if stability_score >= 75:
        messages.append("✅ STABLE: Out-of-sample performance confirms in-sample results.")
    elif stability_score >= 50:
        messages.append("⚠️ MODERATE: Some performance degradation out-of-sample.")
    else:
        messages.append("❌ UNSTABLE: Significant overfitting detected.")
    
    if sharpe_ratio < 0.5:
        messages.append(f"  • Sharpe degradation: test={sharpe_ratio:.0%} of train (POOR)")
    elif sharpe_ratio < 0.8:
        messages.append(f"  • Sharpe degradation: test={sharpe_ratio:.0%} of train (ACCEPTABLE)")
    
    if dd_ratio > 2.0:
        messages.append(f"  • Drawdown amplified: test={dd_ratio:.1f}x train (CONCERN)")
    
    if test_sharpe < 0:
        messages.append("  • Test period Sharpe NEGATIVE - results may not persist")
    
    return "\n".join(messages)


# ================================================================================
# ROLLING WINDOW STABILITY ANALYSIS
# ================================================================================

@dataclass
class RollingStabilityResult:
    """Results from rolling window stability analysis."""
    sharpe_history: pd.Series
    vol_history: pd.Series
    correlation_stability: float  # 0-1, higher = more stable
    parameter_stability: Dict[str, float]
    regime_changes_detected: int
    interpretation: str


def analyze_rolling_stability(
    prices: pd.DataFrame,
    weights: np.ndarray,
    window_months: int = 12,
    risk_free_annual: float = 0.0
) -> RollingStabilityResult:
    """
    Analyze stability of portfolio parameters over rolling windows.
    
    Detects:
    - Sharpe ratio variability over time
    - Correlation structure changes
    - Regime shifts
    
    Args:
        prices: Price DataFrame
        weights: Portfolio weights
        window_months: Rolling window size in months
        risk_free_annual: Annual risk-free rate for rolling Sharpe
        
    Returns:
        RollingStabilityResult with stability metrics
    """
    window = window_months * 21  # Approximate trading days
    returns = prices.pct_change().dropna()
    
    if len(returns) < window * 2:
        return RollingStabilityResult(
            sharpe_history=pd.Series([]),
            vol_history=pd.Series([]),
            correlation_stability=0.5,
            parameter_stability={},
            regime_changes_detected=0,
            interpretation="Insufficient data for rolling analysis"
        )
    
    portfolio_returns = (returns * weights).sum(axis=1)
    
    # Rolling Sharpe
    rf_daily = (1 + risk_free_annual) ** (1/252) - 1
    rolling_mean = (portfolio_returns - rf_daily).rolling(window).mean() * 252
    rolling_vol = portfolio_returns.rolling(window).std() * np.sqrt(252)
    rolling_sharpe = rolling_mean / rolling_vol
    rolling_sharpe = rolling_sharpe.dropna()
    
    # Sharpe stability
    sharpe_cv = rolling_sharpe.std() / rolling_sharpe.mean() if rolling_sharpe.mean() != 0 else 999
    
    # Correlation stability (compare first and second half)
    mid_idx = len(returns) // 2
    corr_first = returns.iloc[:mid_idx].corr()
    corr_second = returns.iloc[mid_idx:].corr()
    
    # Average correlation change
    corr_diff = np.abs(corr_first.values - corr_second.values)
    avg_corr_change = np.mean(corr_diff[np.triu_indices(len(corr_diff), k=1)])
    correlation_stability = max(0, 1 - avg_corr_change * 2)  # Scale to 0-1
    
    # Detect regime changes (Sharpe sign flips or large jumps)
    sharpe_changes = rolling_sharpe.diff().abs()
    regime_threshold = rolling_sharpe.std() * 2
    regime_changes = (sharpe_changes > regime_threshold).sum()
    
    # Parameter stability summary
    param_stability = {
        "sharpe_cv": sharpe_cv,
        "vol_cv": rolling_vol.std() / rolling_vol.mean() if rolling_vol.mean() > 0 else 999,
        "correlation_stability": correlation_stability,
    }
    
    interpretation = _interpret_rolling_stability(
        sharpe_cv, correlation_stability, regime_changes
    )
    
    return RollingStabilityResult(
        sharpe_history=rolling_sharpe,
        vol_history=rolling_vol,
        correlation_stability=correlation_stability,
        parameter_stability=param_stability,
        regime_changes_detected=int(regime_changes),
        interpretation=interpretation
    )


def _interpret_rolling_stability(sharpe_cv: float, corr_stability: float, 
                                  regime_changes: int) -> str:
    """Generate interpretation of rolling stability."""
    messages = []
    
    if sharpe_cv < 0.5:
        messages.append("✅ Sharpe ratio STABLE over time (CV < 0.5)")
    elif sharpe_cv < 1.0:
        messages.append("⚠️ Sharpe ratio VARIABLE (CV 0.5-1.0)")
    else:
        messages.append("❌ Sharpe ratio UNSTABLE (CV > 1.0) - high regime dependency")
    
    if corr_stability > 0.8:
        messages.append("✅ Correlation structure STABLE")
    elif corr_stability > 0.5:
        messages.append("⚠️ Correlation structure MODERATE stability")
    else:
        messages.append("❌ Correlation structure UNSTABLE - diversification unreliable")
    
    if regime_changes > 5:
        messages.append(f"⚠️ {regime_changes} regime shifts detected - tactical adjustments may be needed")
    
    return "\n".join(messages)


# ================================================================================
# SOFT LABELS FOR PORTFOLIO CLASSIFICATION
# ================================================================================

@dataclass
class SoftClassification:
    """Soft-label classification with continuous Core/Tactical split."""
    primary_type: str
    confidence: float
    core_score: float       # 0-100: how "core" the portfolio is
    tactical_score: float   # 0-100: how "tactical" the portfolio is
    conviction_score: float # 0-100: strength of classification
    alternative_types: List[Tuple[str, float]]  # (type, confidence) pairs
    reasoning: str


def calculate_soft_classification(
    weights: np.ndarray,
    tickers: List[str],
    asset_metrics: pd.DataFrame,
    portfolio_beta: float = 0.8
) -> SoftClassification:
    """
    Calculate soft-label classification with continuous Core/Tactical scores.
    
    Instead of binary "TACTICAL / OPPORTUNISTIC" with 50% confidence,
    produces:
    - core_score: How much is stable/passive (0-100)
    - tactical_score: How much is active/timing-based (0-100)
    - conviction_score: How confident we are (0-100)
    
    Args:
        weights: Portfolio weights
        tickers: List of tickers
        asset_metrics: DataFrame with asset characteristics
        portfolio_beta: Estimated portfolio beta
        
    Returns:
        SoftClassification with continuous scores
    """
    n_positions = len([w for w in weights if w > 0.01])
    max_weight = max(weights)
    
    # === CORE SCORE (0-100) ===
    # High core_score = stable, diversified, passive-like
    core_score = 0
    
    # Factor 1: Diversification (many positions, low max weight)
    diversification_factor = min(100, (n_positions / 15) * 50 + (1 - max_weight) * 50)
    core_score += diversification_factor * 0.30
    
    # Factor 2: Core ETF exposure
    core_etf_weight = sum(
        w for t, w in zip(tickers, weights)
        if any(kw in t.upper() for kw in ['VWCE', 'VT', 'IWDA', 'ACWI', 'VTI', 'VOO', 'SPY'])
    )
    core_score += core_etf_weight * 100 * 0.25
    
    # Factor 3: Low beta (conservative = core-like)
    beta_factor = max(0, min(100, (1.2 - portfolio_beta) * 100))
    core_score += beta_factor * 0.20
    
    # Factor 4: Bond/defensive presence
    bond_keywords = ['AGGH', 'BND', 'AGG', 'TLT', 'IEAG', 'GLD', 'SGOL']
    defensive_weight = sum(
        w for t, w in zip(tickers, weights)
        if any(kw in t.upper() for kw in bond_keywords)
    )
    core_score += defensive_weight * 100 * 0.25
    
    core_score = min(100, max(0, core_score))
    
    # === TACTICAL SCORE (0-100) ===
    # High tactical_score = concentrated, thematic, timing-based
    tactical_score = 0
    
    # Factor 1: Concentration
    concentration_factor = max_weight * 100
    tactical_score += concentration_factor * 0.25
    
    # Factor 2: Thematic/sector exposure
    thematic_keywords = ['ARK', 'SEMI', 'CLOUD', 'CLEAN', 'KWEB', 'MCHI', 'INDA']
    thematic_weight = sum(
        w for t, w in zip(tickers, weights)
        if any(kw in t.upper() for kw in thematic_keywords)
    )
    tactical_score += thematic_weight * 100 * 0.30
    
    # Factor 3: EM single country exposure
    em_single_keywords = ['EWZ', 'INDA', 'MCHI', 'TUR', 'EZA', 'EPOL', 'ARGT']
    em_single_weight = sum(
        w for t, w in zip(tickers, weights)
        if any(kw in t.upper() for kw in em_single_keywords)
    )
    tactical_score += em_single_weight * 100 * 0.25
    
    # Factor 4: High beta
    beta_tactical = max(0, min(100, (portfolio_beta - 0.8) * 200))
    tactical_score += beta_tactical * 0.20
    
    tactical_score = min(100, max(0, tactical_score))
    
    # === CONVICTION SCORE (0-100) ===
    # How confident are we in the classification?
    # Low conviction when core_score ≈ tactical_score
    score_diff = abs(core_score - tactical_score)
    conviction_score = min(100, score_diff + 30)  # Base 30, increases with difference
    
    # Boost conviction for clear patterns
    if core_etf_weight > 0.50:
        conviction_score = min(100, conviction_score + 20)
    if thematic_weight > 0.30:
        conviction_score = min(100, conviction_score + 20)
    
    # === DETERMINE PRIMARY TYPE ===
    if core_score > tactical_score + 20:
        if defensive_weight > 0.20:
            primary_type = "BALANCED"
        elif core_etf_weight > 0.50:
            primary_type = "EQUITY_CORE_DRIVEN"
        else:
            primary_type = "EQUITY_MULTI_BLOCK"
    elif tactical_score > core_score + 20:
        if thematic_weight > 0.30:
            primary_type = "BARBELL_THEMATIC"
        elif concentration_factor > 50:
            primary_type = "CONCENTRATED_CONVICTION"
        else:
            primary_type = "TACTICAL"
    else:
        # Ambiguous - use soft label
        primary_type = "HYBRID_CORE_TACTICAL"
    
    # Generate alternatives
    alternatives = [
        ("EQUITY_MULTI_BLOCK", core_score / 100),
        ("TACTICAL", tactical_score / 100),
        ("STRUCTURED_MULTI_ASSET", (core_score + defensive_weight * 100) / 200),
    ]
    alternatives = sorted(alternatives, key=lambda x: x[1], reverse=True)[:3]
    
    # Reasoning
    reasoning = _generate_soft_reasoning(
        core_score, tactical_score, conviction_score, 
        core_etf_weight, thematic_weight, portfolio_beta
    )
    
    return SoftClassification(
        primary_type=primary_type,
        confidence=conviction_score / 100,
        core_score=core_score,
        tactical_score=tactical_score,
        conviction_score=conviction_score,
        alternative_types=alternatives,
        reasoning=reasoning
    )


def _generate_soft_reasoning(core_score: float, tactical_score: float,
                             conviction_score: float, core_weight: float,
                             thematic_weight: float, beta: float) -> str:
    """Generate detailed reasoning for soft classification."""
    parts = []
    
    parts.append(f"Core Score: {core_score:.0f}/100 | Tactical Score: {tactical_score:.0f}/100")
    parts.append(f"Conviction: {conviction_score:.0f}/100")
    parts.append("")
    
    if core_score > tactical_score:
        parts.append("Leans CORE because:")
        if core_weight > 0.30:
            parts.append(f"  • {core_weight:.0%} in core global ETFs")
        if beta < 0.8:
            parts.append(f"  • Low beta ({beta:.2f}) suggests defensive tilt")
    else:
        parts.append("Leans TACTICAL because:")
        if thematic_weight > 0.15:
            parts.append(f"  • {thematic_weight:.0%} in thematic/sector exposure")
        if beta > 1.0:
            parts.append(f"  • High beta ({beta:.2f}) suggests aggressive positioning")
    
    if conviction_score < 50:
        parts.append("")
        parts.append("⚠️ LOW CONVICTION: Portfolio has mixed characteristics.")
        parts.append("   Consider this a HYBRID structure, not purely one type.")
    
    return "\n".join(parts)


# ================================================================================
# OUT-OF-SAMPLE STRESS TESTING
# ================================================================================

def run_out_of_sample_stress(
    prices: pd.DataFrame,
    weights: np.ndarray,
    test_ratio: float = 0.2,
    risk_free_annual: float = 0.0,
    sharpe_autocorr_lags: int | None = None
) -> Dict[str, Any]:
    """
    Reserve last portion of data for pure out-of-sample testing.
    
    This is SEPARATE from walk-forward (which uses expanding windows).
    Here we simply hold out the last X% and never touch it until final evaluation.
    
    Args:
        prices: Full price history
        weights: Portfolio weights
        test_ratio: Portion to reserve (default 20%)
        risk_free_annual: Annual risk-free rate for Sharpe calculations
        sharpe_autocorr_lags: Optional autocorrelation lag adjustment for Sharpe
        
    Returns:
        Dict with out-of-sample metrics
    """
    n = len(prices)
    split_idx = int(n * (1 - test_ratio))
    
    returns = prices.pct_change().dropna()
    portfolio_returns = (returns * weights).sum(axis=1)
    
    train_returns = portfolio_returns.iloc[:split_idx]
    test_returns = portfolio_returns.iloc[split_idx:]
    
    if len(test_returns) < 63:  # Min 3 months
        return {
            "valid": False,
            "message": "Insufficient out-of-sample data (need 3+ months)"
        }
    
    train_metrics = _calc_period_metrics(
        train_returns, risk_free_annual=risk_free_annual, sharpe_autocorr_lags=sharpe_autocorr_lags
    )
    test_metrics = _calc_period_metrics(
        test_returns, risk_free_annual=risk_free_annual, sharpe_autocorr_lags=sharpe_autocorr_lags
    )
    
    # Performance degradation
    sharpe_degradation = (train_metrics["sharpe"] - test_metrics["sharpe"]) / train_metrics["sharpe"] \
        if train_metrics["sharpe"] > 0 else 0
    
    return {
        "valid": True,
        "train_period": f"{train_returns.index[0].date()} to {train_returns.index[-1].date()}",
        "test_period": f"{test_returns.index[0].date()} to {test_returns.index[-1].date()}",
        "train_sharpe": train_metrics["sharpe"],
        "test_sharpe": test_metrics["sharpe"],
        "train_cagr": train_metrics["cagr"],
        "test_cagr": test_metrics["cagr"],
        "train_maxdd": train_metrics["max_dd"],
        "test_maxdd": test_metrics["max_dd"],
        "sharpe_degradation": sharpe_degradation,
        "passed_validation": sharpe_degradation < 0.5 and test_metrics["sharpe"] > 0,
        "interpretation": _interpret_oos_stress(sharpe_degradation, test_metrics)
    }


def _interpret_oos_stress(degradation: float, test_metrics: Dict) -> str:
    """Interpret out-of-sample stress test results."""
    if degradation < 0:
        return "✅ EXCELLENT: Out-of-sample BETTER than in-sample (rare but positive)"
    elif degradation < 0.3:
        return "✅ GOOD: Modest degradation (<30%), results likely to persist"
    elif degradation < 0.5:
        return "⚠️ MODERATE: 30-50% degradation, some overfitting possible"
    else:
        return "❌ POOR: >50% degradation, significant overfitting detected"
