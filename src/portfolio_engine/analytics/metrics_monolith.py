"""
Portfolio Metrics Module
========================
Re-exports basic metrics from metrics/ submodule.
Contains higher-level composite functions.

For individual metrics, use:
- portfolio_engine.analytics.metrics.basic: returns, CAGR, volatility
- portfolio_engine.analytics.metrics.risk: Sharpe, Sortino, drawdown, VaR
- portfolio_engine.analytics.metrics.confidence: bootstrap CI, FDR
- portfolio_engine.analytics.metrics.contribution: risk contribution
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any, List
from scipy import stats

# ================================================================================
# Re-export all metrics from submodule for backward compatibility
# ================================================================================
from portfolio_engine.analytics.metrics import (
    # Basic
    calculate_simple_returns,
    calculate_log_returns,
    calculate_cagr,
    calculate_cagr_correct,
    calculate_annualized_volatility,
    # Risk
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_calmar_ratio,
    calculate_max_drawdown,
    calculate_drawdown_series,
    analyze_multi_trough_recovery,
    calculate_var_cvar,
    # Confidence
    apply_fdr_correction,
    calculate_gate_p_values,
    calculate_sharpe_confidence_interval,
    calculate_cagr_confidence_interval,
    calculate_max_dd_confidence_interval,
    # Contribution
    calculate_risk_contribution,
    calculate_risk_contribution_correct,
    calculate_conditional_risk_contribution,
)


# =========================
# MONTE CARLO STRESS TEST
# =========================

def _multivariate_t(mean: np.ndarray, cov: np.ndarray, df: int, n_samples: int) -> np.ndarray:
    """
    Generate samples from multivariate Student-t distribution.
    
    Fix C3/C4: This addresses the inconsistency between fat-tail warnings
    and normal distribution assumptions in Monte Carlo.
    
    Student-t has heavier tails than normal, controlled by degrees of freedom:
    - df=3: very heavy tails (extreme events ~3x more likely)
    - df=5: moderately heavy tails 
    - df=10: approaching normal
    - df=∞: equivalent to normal
    
    Args:
        mean: Mean vector (n_assets,)
        cov: Covariance matrix (n_assets, n_assets)
        df: Degrees of freedom (lower = heavier tails)
        n_samples: Number of samples to generate
        
    Returns:
        Array of shape (n_samples, n_assets)
    """
    n_assets = len(mean)
    
    # Sample from standard normal
    z = np.random.multivariate_normal(np.zeros(n_assets), cov, n_samples)
    
    # Scale by chi-squared to get Student-t
    # X ~ t_df is equivalent to Z * sqrt(df / chi2_df) where Z ~ N(0, Sigma)
    chi2 = np.random.chisquare(df, n_samples)
    scaling = np.sqrt(df / chi2)
    
    # Apply scaling to each sample
    samples = mean + z * scaling[:, np.newaxis]
    
    return samples


def run_monte_carlo_stress_test(
    returns: pd.DataFrame,
    weights: np.ndarray,
    n_simulations: int = 500,
    horizon_days: int = 252,
    includes_crisis: bool = False,
    use_student_t: bool = True,  # Fix C3/C4: Default to Student-t
    student_t_df: int = 5        # Fix C3/C4: Degrees of freedom
) -> Dict[str, Any]:
    """
    Monte Carlo stress test per scenari IPOTETICI forward-looking.
    
    ⚠️ METODOLOGIA CRITICA (Fix C3/C4):
    Questo stress test genera scenari IPOTETICI usando distribuzione Student-t
    per catturare le fat tails tipiche dei returns finanziari.
    
    La normale sottostima la probabilità di eventi estremi di ~20-40%.
    Student-t con df=5 produce code più pesanti, coerenti con l'avviso
    "returns finanziari hanno fat tails (kurtosis > 3)".
    
    Scenari:
    1. Base: distribuzione Student-t (code più pesanti della normale)
    2. Structural Break: fat tails asimmetrici (downside amplificato)
    3. Correlation Regime Shift: correlazioni → 0.95 (decorrelazione sparisce)
    
    Args:
        returns: DataFrame returns storici
        weights: Array pesi portafoglio
        n_simulations: Numero simulazioni
        horizon_days: Orizzonte in giorni
        includes_crisis: Se True, i dati già includono crisi (no vol doubling)
        use_student_t: Se True, usa Student-t invece di normale (Fix C3/C4)
        student_t_df: Gradi di libertà per Student-t (5=moderato, 3=estremo)
    
    Returns:
        Dict con scenari e metriche
    """
    # Guardrail: se dati insufficienti o vuoti, salta MC
    if returns is None or returns.empty or returns.dropna().empty:
        return {
            "error": "Monte Carlo skipped: empty returns",
            "distribution": None,
            "base": {},
            "correlation_shift": {},
            "structural_break": {},
        }

    n_assets = len(weights)
    mean_returns = returns.mean().values
    cov_matrix = returns.cov().values
    # Se cov contiene NaN o non è PSD, fallback skip
    if not np.all(np.isfinite(cov_matrix)) or cov_matrix.shape[0] != cov_matrix.shape[1]:
        return {
            "error": "Monte Carlo skipped: invalid covariance",
            "distribution": None,
            "base": {},
            "correlation_shift": {},
            "structural_break": {},
        }
    
    # Calcola skewness e kurtosis storiche
    portfolio_hist_returns = (returns * weights).sum(axis=1)
    hist_skew = portfolio_hist_returns.skew()
    hist_kurt = portfolio_hist_returns.kurtosis()  # Excess kurtosis
    
    # Fix C3/C4: Document distribution choice
    distribution_used = f"Student-t(df={student_t_df})" if use_student_t else "Normal"
    
    results = {
        'methodology': 'HYPOTHETICAL_SCENARIOS',
        'distribution': distribution_used,
        'data_includes_crisis': includes_crisis,
        'historical_kurtosis': hist_kurt,
        'note': f'Scenari ipotetici con {distribution_used}. Fat tails modellate esplicitamente.' 
                if use_student_t else 'Scenari ipotetici con distribuzione normale (può sottostimare code).'
    }
    
    # Scenario 1: Base (distribuzione storica con fat tails)
    np.random.seed(42)
    portfolio_returns_base = []
    for _ in range(n_simulations):
        if use_student_t:
            # Fix C3/C4: Use Student-t for heavier tails
            sim_returns = _multivariate_t(mean_returns, cov_matrix, student_t_df, horizon_days)
        else:
            sim_returns = np.random.multivariate_normal(mean_returns, cov_matrix, horizon_days)
        portfolio_daily = sim_returns @ weights
        cumulative = (1 + portfolio_daily).prod() - 1
        portfolio_returns_base.append(cumulative)
    
    results['base'] = {
        'var_5': np.percentile(portfolio_returns_base, 5),
        'var_1': np.percentile(portfolio_returns_base, 1),
        'median': np.percentile(portfolio_returns_base, 50),
        'worst': min(portfolio_returns_base),
        'best': max(portfolio_returns_base),
        'description': f'Distribuzione {distribution_used} (include crisi se presenti)'
    }
    
    # Scenario 2: Structural Break (fat tails, NON vol doubling se già in crisi)
    # FIX INCONGRUENZA #7: Il fat tail deve peggiorare la coda SINISTRA, non renderla simmetrica
    if includes_crisis:
        # I dati già includono eventi estremi dalle crisi
        # Modella con distribuzione ASIMMETRICA (skew negativo) + fat tails
        # Student-t con skew applicato solo al downside
        df_t = 4  # gradi di libertà più bassi = code più pesanti
        
        portfolio_returns_structural = []
        for _ in range(n_simulations):
            # Simula con normale per il mean, poi aggiungi shock negativi
            z = np.random.multivariate_normal(np.zeros(n_assets), cov_matrix, horizon_days)
            
            # Chi-squared scaling per fat tails
            chi2 = np.random.chisquare(df_t, horizon_days) / df_t
            
            # Negative skew: eventi negativi sono amplificati
            skew_factor = np.where(z.sum(axis=1) < 0, 1.3, 1.0)  # 30% amplification on bad days
            
            sim_returns = mean_returns + z / np.sqrt(chi2[:, np.newaxis]) * skew_factor[:, np.newaxis]
            portfolio_daily = sim_returns @ weights
            cumulative = (1 + portfolio_daily).prod() - 1
            portfolio_returns_structural.append(cumulative)
        
        results['structural_break'] = {
            'var_5': np.percentile(portfolio_returns_structural, 5),
            'var_1': np.percentile(portfolio_returns_structural, 1),
            'median': np.percentile(portfolio_returns_structural, 50),
            'worst': min(portfolio_returns_structural),
            'description': 'Fat tails asimmetrici (downside amplificato), peggiora vs base'
        }
    else:
        # Dati "normali" → stress vol 2x è appropriato
        cov_highvol = cov_matrix * 4  # 2x vol = 4x variance
        portfolio_returns_highvol = []
        for _ in range(n_simulations):
            if use_student_t:
                sim_returns = _multivariate_t(mean_returns, cov_highvol, student_t_df, horizon_days)
            else:
                sim_returns = np.random.multivariate_normal(mean_returns, cov_highvol, horizon_days)
            portfolio_daily = sim_returns @ weights
            cumulative = (1 + portfolio_daily).prod() - 1
            portfolio_returns_highvol.append(cumulative)
        
        results['high_vol'] = {
            'var_5': np.percentile(portfolio_returns_highvol, 5),
            'var_1': np.percentile(portfolio_returns_highvol, 1),
            'median': np.percentile(portfolio_returns_highvol, 50),
            'worst': min(portfolio_returns_highvol),
            'description': f'Volatilità 2x con {distribution_used} (appropriato per dati senza crisi)'
        }
    
    # Scenario 3: Correlation Regime Shift (sempre valido)
    std_devs = np.sqrt(np.diag(cov_matrix))
    crisis_corr = np.full((n_assets, n_assets), 0.95)
    np.fill_diagonal(crisis_corr, 1.0)
    cov_crisis = np.outer(std_devs, std_devs) * crisis_corr
    
    portfolio_returns_crisis = []
    for _ in range(n_simulations):
        sim_returns = np.random.multivariate_normal(mean_returns, cov_crisis, horizon_days)
        portfolio_daily = sim_returns @ weights
        cumulative = (1 + portfolio_daily).prod() - 1
        portfolio_returns_crisis.append(cumulative)
    
    results['correlation_shift'] = {
        'var_5': np.percentile(portfolio_returns_crisis, 5),
        'var_1': np.percentile(portfolio_returns_crisis, 1),
        'median': np.percentile(portfolio_returns_crisis, 50),
        'worst': min(portfolio_returns_crisis),
        'description': 'Correlazioni → 0.95 (diversificazione sparisce)'
    }
    
    return results


# =========================
# CORRELATION SHRINKAGE
# =========================

def calculate_shrunk_correlation(returns: pd.DataFrame, shrinkage_target: str = 'identity') -> pd.DataFrame:
    """
    Applica Ledoit-Wolf shrinkage alla matrice di correlazione.
    
    La correlazione campionaria è rumorosa con poche osservazioni.
    Lo shrinkage verso un target riduce l'estimation error.
    
    Metodo: corr_shrunk = δ * Target + (1-δ) * Sample
    dove δ è stimato per minimizzare MSE.
    
    Args:
        returns: DataFrame dei returns
        shrinkage_target: 'identity' (correlazione 0) o 'constant' (correlazione media)
    
    Returns:
        DataFrame con correlazione shrunk
    """
    n = len(returns)
    sample_corr = returns.corr()
    p = sample_corr.shape[0]
    
    if shrinkage_target == 'identity':
        # Target: matrice identità (correlazioni = 0)
        target = np.eye(p)
    else:
        # Target: correlazione costante (media delle correlazioni)
        avg_corr = (sample_corr.values.sum() - p) / (p * (p - 1))
        target = np.full((p, p), avg_corr)
        np.fill_diagonal(target, 1.0)
    
    # Stima shrinkage intensity (semplificato Ledoit-Wolf)
    # Formula completa in Ledoit & Wolf (2004)
    sample = sample_corr.values
    
    # Frobenius norm della differenza
    diff = sample - target
    
    # Shrinkage intensity stimata
    # Approssimazione: basata su varianza delle correlazioni
    var_corr = np.var(sample[np.triu_indices(p, k=1)])
    
    # δ tra 0 e 1
    delta = min(1.0, max(0.0, var_corr * n / (var_corr * n + np.sum(diff**2) / (p * p))))
    
    # Se pochi dati (n < 100), aumenta shrinkage
    if n < 100:
        delta = min(1.0, delta + 0.2)
    
    # Applica shrinkage
    shrunk = delta * target + (1 - delta) * sample
    
    return pd.DataFrame(shrunk, index=sample_corr.index, columns=sample_corr.columns), delta


# =========================
# CONDITIONAL CORRELATIONS
# =========================

def calculate_conditional_correlations(
    returns: pd.DataFrame,
    portfolio_returns: pd.Series = None,
    crisis_threshold: float = -0.02,
    vol_multiplier: float = 2.0
) -> Dict[str, Any]:
    """
    Calcola correlazioni CONDIZIONATE al regime (normale vs crisi).
    
    ⚠️ METODOLOGIA CRITICA (FIX Incongruenza #3):
    Le correlazioni osservate in regime normale SOTTOSTIMANO le correlazioni
    che si realizzano in crisi. Durante stress, le correlazioni convergono
    verso 1 ("correlation breakdown of diversification").
    
    DEFINIZIONE CRISI: usa DOPPIO criterio (return negativo + alta volatilità)
    invece di solo return < threshold. Questo cattura vere giornate di stress
    sistemico (tutti giù insieme) vs singoli cali idiosincratici.
    
    Args:
        returns: DataFrame returns giornalieri
        portfolio_returns: Serie returns portafoglio (per split regime)
        crisis_threshold: Soglia return per definire "crisi" (default -2% daily)
        vol_multiplier: Soglia volatilità = vol_multiplier * rolling_std (default 2.0)
    
    Returns:
        Dict con correlation_normal, correlation_crisis, delta, interpretation
    """
    tickers = returns.columns.tolist()
    
    # Calcola portfolio returns se non fornito
    if portfolio_returns is None:
        portfolio_returns = returns.mean(axis=1)  # EW proxy
    
    # === FIX INCONGRUENZA #3 ===
    # Crisi = return negativo significativo AND alta dispersione/volatilità
    # Questo cattura giorni di vero stress sistemico, non singoli cali
    rolling_vol = portfolio_returns.rolling(window=21).std()
    vol_threshold = rolling_vol.median() * vol_multiplier
    
    # Crisi: return molto negativo OPPURE (negativo + vol anomala)
    crisis_by_return = portfolio_returns < crisis_threshold
    crisis_by_vol = (portfolio_returns < 0) & (portfolio_returns.abs() > vol_threshold)
    crisis_mask = crisis_by_return | crisis_by_vol
    
    # Normale: solo giorni genuinamente calmi
    normal_mask = ~crisis_mask
    
    returns_normal = returns[normal_mask]
    returns_crisis = returns[crisis_mask]
    
    # Correlazioni in regime normale
    corr_normal = returns_normal.corr()
    avg_corr_normal = (corr_normal.values.sum() - len(tickers)) / (len(tickers) * (len(tickers) - 1))
    
    # Correlazioni in regime crisi
    if len(returns_crisis) >= 30:
        corr_crisis = returns_crisis.corr()
        avg_corr_crisis = (corr_crisis.values.sum() - len(tickers)) / (len(tickers) * (len(tickers) - 1))
        simulated = False
    else:
        # Non abbastanza dati - stima conservativa
        # In crisi, correlazioni tipicamente convergono verso 0.7-0.9
        avg_corr_crisis = min(0.85, avg_corr_normal + 0.25)
        corr_crisis = np.full((len(tickers), len(tickers)), avg_corr_crisis)
        np.fill_diagonal(corr_crisis, 1.0)
        corr_crisis = pd.DataFrame(corr_crisis, index=tickers, columns=tickers)
        simulated = True
    
    # Calcola delta (quanto aumentano in crisi)
    delta_matrix = corr_crisis.values - corr_normal.values
    np.fill_diagonal(delta_matrix, 0)  # Ignora diagonale
    delta_avg = float(delta_matrix.mean())
    
    # Interpretazione
    if delta_avg > 0.20:
        interpretation = (
            f"⚠️ ALTO RISCHIO: Correlazioni aumentano di {delta_avg:.2f} in crisi. "
            f"La diversificazione apparente (corr normale {avg_corr_normal:.2f}) "
            f"sparisce quando serve (corr crisi {avg_corr_crisis:.2f})."
        )
        severity = 'HIGH'
    elif delta_avg > 0.10:
        interpretation = (
            f"⚡ MODERATO: Correlazioni aumentano di {delta_avg:.2f} in crisi. "
            f"Diversificazione parzialmente compromessa in stress."
        )
        severity = 'MODERATE'
    else:
        interpretation = (
            f"✓ STABILE: Correlazioni aumentano solo di {delta_avg:.2f} in crisi. "
            f"Diversificazione relativamente robusta."
        )
        severity = 'LOW'
    
    return {
        'correlation_normal': corr_normal,
        'correlation_crisis': corr_crisis,
        'avg_corr_normal': float(avg_corr_normal),
        'avg_corr_crisis': float(avg_corr_crisis),
        'delta_avg': delta_avg,
        'delta_matrix': pd.DataFrame(delta_matrix, index=tickers, columns=tickers),
        'interpretation': interpretation,
        'severity': severity,
        'crisis_simulated': simulated,
        'summary': {
            'normal_days': int(normal_mask.sum()),
            'crisis_days': int(crisis_mask.sum()),
            'crisis_threshold': crisis_threshold
        }
    }


# =========================
# COMPREHENSIVE METRICS
# =========================

def calculate_all_metrics(
    equity: pd.Series,
    returns: pd.Series,
    risk_free: float = 0.02,
    var_confidence: float = 0.95,
    var_method: str = "historical",
    var_bootstrap_samples: int = 0,
) -> dict:
    """Calcola tutte le metriche del portafoglio."""
    
    periods = 252
    
    # Performance
    total_roi = float(equity.iloc[-1] / equity.iloc[0] - 1)
    # Use real calendar span when available (consistent with calculate_cagr default)
    cagr = calculate_cagr(equity, periods_per_year=None)
    volatility = calculate_annualized_volatility(returns, periods)
    
    # Risk-adjusted
    sharpe = calculate_sharpe_ratio(returns, risk_free, periods)
    sortino = calculate_sortino_ratio(returns, risk_free, 0.0, periods)
    
    # Drawdown
    max_dd, peak_date, trough_date = calculate_max_drawdown(equity)
    calmar = calculate_calmar_ratio(cagr, max_dd)
    
    dd_series = calculate_drawdown_series(equity)
    avg_dd = float(dd_series.mean())
    current_dd = float(dd_series.iloc[-1])
    
    # VaR e CVaR
    var_daily, cvar_daily = calculate_var_cvar(
        returns,
        var_confidence,
        periods,
        method=var_method,
        bootstrap_samples=var_bootstrap_samples,
    )
    var_annual = var_daily * np.sqrt(periods)
    cvar_annual = cvar_daily * np.sqrt(periods)
    
    # Monthly stats
    monthly_ret = returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)
    months_up = int((monthly_ret > 0).sum())
    months_down = int((monthly_ret < 0).sum())
    months_total = len(monthly_ret)
    
    # Yearly stats
    yearly_ret = returns.resample('YE').apply(lambda x: (1 + x).prod() - 1)
    years_up = int((yearly_ret > 0).sum())
    years_down = int((yearly_ret < 0).sum())
    years_total = len(yearly_ret)
    
    # Daily stats
    days_up = int((returns > 0).sum())
    days_down = int((returns < 0).sum())
    days_total = len(returns)
    
    # Gain/Loss metrics
    gains = returns[returns > 0]
    losses = returns[returns < 0]
    
    avg_gain = float(gains.mean()) if len(gains) > 0 else 0
    avg_loss = float(abs(losses.mean())) if len(losses) > 0 else 0
    gain_loss_ratio = avg_gain / avg_loss if avg_loss > 0 else 0
    
    total_gains = gains.sum() if len(gains) > 0 else 0
    total_losses = abs(losses.sum()) if len(losses) > 0 else 0
    profit_factor = float(total_gains / total_losses) if total_losses > 0 else 0
    
    # === CONFIDENCE INTERVALS ===
    # Calcola CI per metriche principali (importante per interpretazione)
    sharpe_ci = calculate_sharpe_confidence_interval(returns, risk_free)
    cagr_ci = calculate_cagr_confidence_interval(equity)
    max_dd_ci = calculate_max_dd_confidence_interval(equity)
    
    return {
        # Performance
        "total_roi": total_roi,
        "cagr": cagr,
        "volatility": volatility,
        
        # Risk-adjusted
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        
        # Drawdown
        "max_drawdown": max_dd,
        "max_dd_peak": peak_date,
        "max_dd_trough": trough_date,
        "avg_drawdown": avg_dd,
        "current_drawdown": current_dd,
        
        # VaR/CVaR
        "var_95_daily": var_daily,
        "cvar_95_daily": cvar_daily,
        "var_95_annual": var_annual,
        "cvar_95_annual": cvar_annual,
        
        # Monthly
        "months_up": months_up,
        "months_down": months_down,
        "months_total": months_total,
        "win_rate_monthly": months_up / months_total if months_total > 0 else 0,
        "best_month": float(monthly_ret.max()) if len(monthly_ret) > 0 else 0,
        "worst_month": float(monthly_ret.min()) if len(monthly_ret) > 0 else 0,
        "avg_month": float(monthly_ret.mean()) if len(monthly_ret) > 0 else 0,
        
        # Yearly
        "years_up": years_up,
        "years_down": years_down,
        "years_total": years_total,
        "best_year": float(yearly_ret.max()) if len(yearly_ret) > 0 else 0,
        "worst_year": float(yearly_ret.min()) if len(yearly_ret) > 0 else 0,
        
        # Daily
        "days_up": days_up,
        "days_down": days_down,
        "days_total": days_total,
        "best_day": float(returns.max()),
        "worst_day": float(returns.min()),
        
        # Ratios
        "gain_loss_ratio": gain_loss_ratio,
        "profit_factor": profit_factor,
        
        # Confidence Intervals (95%)
        "sharpe_ci": sharpe_ci,
        "cagr_ci": cagr_ci,
        "max_dd_ci": max_dd_ci,
        
        # Time series (per decomposizione temporale)
        "equity_curve": equity,
        "returns": returns,
    }


# =========================
# BENCHMARK COMPARISON
# =========================

# Benchmark standard per confronto
# FIX INCONGRUENZA #6: Separazione benchmark per CATEGORIA vs OPPORTUNITY COST
STANDARD_BENCHMARKS = {
    # === SAME-CATEGORY BENCHMARKS (equity vs equity) ===
    'GLOBAL_EQUITY': {
        'ticker': 'VT',
        'name': 'Global Equity (VT)',
        'description': 'Vanguard Total World Stock ETF - benchmark globale',
        'category': 'EQUITY',  # Per equity portfolios
        'comparison_type': 'SAME_CATEGORY'
    },
    'SP500': {
        'ticker': 'SPY',
        'name': 'S&P 500 (SPY)',
        'description': 'US Large Cap - benchmark americano',
        'category': 'EQUITY',
        'comparison_type': 'SAME_CATEGORY'
    },
    # === OPPORTUNITY COST BENCHMARKS (different strategy) ===
    '60_40': {
        'tickers': ['SPY', 'BND'],  # or AGG
        'weights': [0.60, 0.40],
        'name': '60/40 Portfolio',
        'description': 'Balanced portfolio classico',
        'category': 'BALANCED',
        'comparison_type': 'OPPORTUNITY_COST'  # Non same-category per equity portfolios
    }
}


def calculate_benchmark_comparison(
    portfolio_returns: pd.Series,
    portfolio_metrics: Dict,
    benchmark_prices: pd.DataFrame,
    portfolio_type: str = None,
    start_date: str = None,
    end_date: str = None,
    total_defensive_pct: float = 0.0,  # Rule 8: REQUIRED - if > 5%, no SAME_CATEGORY for equity benchmarks
    has_sector_tilts: bool = False  # Rule 8: REQUIRED - if True, no SAME_CATEGORY
) -> Dict[str, Any]:
    """
    Confronta il portafoglio con benchmark standard.
    
    ⚠️ METODOLOGIA ISTITUZIONALE:
    Il confronto con benchmark è OBBLIGATORIO per valutare se:
    - Il portafoglio aggiunge valore rispetto a un'alternativa passiva
    - La complessità è giustificata dal rendimento extra
    - Il rischio aggiuntivo è compensato
    
    FIX INCONGRUENZA #6: Distinzione tra:
    - SAME_CATEGORY: benchmark della stessa categoria (equity vs VT, balanced vs 60/40)
    - OPPORTUNITY_COST: benchmark di categoria diversa (equity vs 60/40 = scelta strategica)
    
    Rule 8 v4.2: SAME_CATEGORY only allowed if:
    - Total equity >= 95% (no defensives)  
    - No sector tilts
    - Portfolio is pure broad-market equity
    
    Un portafoglio equity-growth NON deve "battere" il 60/40 per essere valido.
    Deve battere VT (same category). Il 60/40 è solo opportunity cost.
    
    Args:
        portfolio_returns: Returns del portafoglio
        portfolio_metrics: Metriche già calcolate
        benchmark_prices: DataFrame con prezzi dei benchmark (VT, SPY, BND)
        portfolio_type: Tipo di portafoglio per determinare same-category benchmark
        start_date, end_date: Range per allineamento
        total_defensive_pct: REQUIRED - Percentage of defensive assets (bonds/gold). If > 5%, no SAME_CATEGORY
        has_sector_tilts: REQUIRED - If True, portfolio has sector tilts → no SAME_CATEGORY
    
    Returns:
        Dict con confronto per ogni benchmark
    """
    # FIX PROBLEMA 4: Validate required parameters for Rule 8
    if total_defensive_pct is None:
        raise ValueError("total_defensive_pct must be provided for Rule 8 benchmark categorization")
    
    results = {
        'methodology': 'BENCHMARK_COMPARISON',
        'note': 'Confronto vs alternative passive. Distingue same-category vs opportunity-cost.',
        'benchmarks': {},
        'same_category_benchmarks': [],  # Per verdetto finale
        'opportunity_cost_benchmarks': [],
        'rule8_params': {  # Track what was used for Rule 8
            'total_defensive_pct': total_defensive_pct,
            'has_sector_tilts': has_sector_tilts
        }
    }
    
    # Determina categoria del portafoglio
    portfolio_category = 'EQUITY'  # Default
    if portfolio_type:
        if any(kw in portfolio_type.upper() for kw in ['BALANCED', 'RISK_PARITY', 'DEFENSIVE']):
            portfolio_category = 'BALANCED'
        elif any(kw in portfolio_type.upper() for kw in ['INCOME', 'YIELD', 'DIVIDEND']):
            portfolio_category = 'INCOME'
    
    # Portfolio metrics
    port_cagr = portfolio_metrics.get('cagr', 0)
    port_vol = portfolio_metrics.get('volatility', 0.20)
    port_sharpe = portfolio_metrics.get('sharpe', 0)
    port_max_dd = portfolio_metrics.get('max_drawdown', -0.50)
    
    # Per ogni benchmark disponibile
    for bench_key, bench_info in STANDARD_BENCHMARKS.items():
        if bench_key == '60_40':
            # Costruisci 60/40
            if 'SPY' in benchmark_prices.columns and 'BND' in benchmark_prices.columns:
                spy_ret = benchmark_prices['SPY'].pct_change().dropna()
                bnd_ret = benchmark_prices['BND'].pct_change().dropna()
                # Allinea
                common_idx = spy_ret.index.intersection(bnd_ret.index)
                if len(common_idx) > 252:
                    bench_ret = 0.60 * spy_ret[common_idx] + 0.40 * bnd_ret[common_idx]
                else:
                    continue
            else:
                continue
        else:
            ticker = bench_info['ticker']
            if ticker not in benchmark_prices.columns:
                continue
            bench_ret = benchmark_prices[ticker].pct_change().dropna()
        
        # Allinea con portfolio
        common_idx = portfolio_returns.index.intersection(bench_ret.index)
        if len(common_idx) < 252:  # Minimo 1 anno
            continue
        
        bench_ret_aligned = bench_ret[common_idx]
        
        # Calcola metriche benchmark
        bench_equity = (1 + bench_ret_aligned).cumprod()
        bench_cagr = calculate_cagr(bench_equity, 252)
        bench_vol = calculate_annualized_volatility(bench_ret_aligned, 252)
        bench_sharpe = calculate_sharpe_ratio(bench_ret_aligned, 0.02, 252)
        bench_max_dd, _, _ = calculate_max_drawdown(bench_equity)
        
        # Calcola differenziali
        excess_return = port_cagr - bench_cagr
        tracking_error = (portfolio_returns[common_idx] - bench_ret_aligned).std() * np.sqrt(252)
        information_ratio = excess_return / tracking_error if tracking_error > 0 else 0
        
        # Beta e Alpha (vs benchmark)
        cov = np.cov(portfolio_returns[common_idx], bench_ret_aligned)
        beta = cov[0, 1] / cov[1, 1] if cov[1, 1] > 0 else 1
        alpha = port_cagr - (0.02 + beta * (bench_cagr - 0.02))  # Jensen's alpha
        
        # FIX INCONGRUENZA #6: Determina tipo di confronto
        bench_category = bench_info.get('category', 'EQUITY')
        comparison_type = bench_info.get('comparison_type', 'SAME_CATEGORY')
        
        # Se portafoglio equity vs benchmark balanced → opportunity cost, non same category
        is_same_category = (portfolio_category == bench_category) or \
                           (portfolio_category == 'EQUITY' and bench_category == 'EQUITY')
        
        if not is_same_category:
            comparison_type = 'OPPORTUNITY_COST'
        
        # Rule 8 v4.2: Stricter SAME_CATEGORY criteria for equity benchmarks
        # If portfolio has defensives (>5%) or sector tilts → NOT same category as VT/SPY
        # FIX PROBLEMA 4: More explicit Rule 8 application with logging
        rule8_applied = False
        rule8_reason = None
        if comparison_type == 'SAME_CATEGORY' and bench_category == 'EQUITY':
            if total_defensive_pct > 0.05:
                comparison_type = 'OPPORTUNITY_COST'
                rule8_reason = f"Defensive allocation {total_defensive_pct:.1%} > 5% (Rule 8)"
                rule8_applied = True
            elif has_sector_tilts:
                comparison_type = 'OPPORTUNITY_COST'
                rule8_reason = "Portfolio has sector tilts (Rule 8)"
                rule8_applied = True
        
        # Interpretation - diversificata per tipo confronto
        if comparison_type == 'SAME_CATEGORY':
            if excess_return > 0 and port_sharpe > bench_sharpe:
                verdict = "SUPERIOR"
                interpretation = f"Portfolio batte {bench_info['name']} in rendimento E risk-adjusted."
            elif excess_return > 0:
                verdict = "HIGHER_RETURN_LOWER_EFFICIENCY"
                interpretation = f"Portfolio rende più di {bench_info['name']} ma con più rischio relativo."
            elif port_sharpe > bench_sharpe:
                verdict = "LOWER_RETURN_HIGHER_EFFICIENCY"
                interpretation = f"Portfolio rende meno ma è più efficiente (risk-adjusted)."
            else:
                verdict = "INFERIOR"
                interpretation = f"Portfolio sottoperforma {bench_info['name']} - giustificare la scelta."
        else:
            # OPPORTUNITY_COST - logica diversa, non è un "fallimento" non battere
            if port_sharpe > bench_sharpe:
                verdict = "HIGHER_RISK_ADJUSTED"
                interpretation = f"Portfolio ha Sharpe migliore di {bench_info['name']} (strategia diversa)."
            elif excess_return > 0:
                verdict = "HIGHER_ABSOLUTE_RETURN"
                interpretation = f"Portfolio rende di più ma con più volatilità (scelta growth)."
            else:
                verdict = "ALTERNATIVE_STRATEGY"
                interpretation = f"{bench_info['name']} ha dato rendimento maggiore - ma è strategia diversa, non errore."
        
        results['benchmarks'][bench_key] = {
            'name': bench_info['name'],
            'benchmark_cagr': bench_cagr,
            'benchmark_vol': bench_vol,
            'benchmark_sharpe': bench_sharpe,
            'benchmark_max_dd': bench_max_dd,
            'excess_return': excess_return,
            'tracking_error': tracking_error,
            'information_ratio': information_ratio,
            'beta': beta,
            'alpha': alpha,
            'verdict': verdict,
            'interpretation': interpretation,
            'comparison_type': comparison_type,  # FIX #6: Include tipo confronto
            'rule8_applied': rule8_applied,  # FIX PROBLEMA 4: Track if Rule 8 changed categorization
            'rule8_reason': rule8_reason  # FIX PROBLEMA 4: Explain why Rule 8 was applied
        }
        
        # Track per verdetto finale
        if comparison_type == 'SAME_CATEGORY':
            results['same_category_benchmarks'].append(bench_key)
        else:
            results['opportunity_cost_benchmarks'].append(bench_key)
    
    # Verdetto complessivo - SOLO basato su SAME_CATEGORY
    same_cat_verdicts = [results['benchmarks'][k]['verdict'] 
                         for k in results['same_category_benchmarks'] 
                         if k in results['benchmarks']]
    
    if not same_cat_verdicts:
        results['overall_verdict'] = 'NO_SAME_CATEGORY_BENCHMARK'
        results['overall_interpretation'] = 'Nessun benchmark same-category disponibile per confronto.'
    elif all(v == 'SUPERIOR' for v in same_cat_verdicts):
        results['overall_verdict'] = 'PORTFOLIO_JUSTIFIED'
        results['overall_interpretation'] = 'Portfolio aggiunge valore vs benchmark di categoria.'
    elif any(v in ['SUPERIOR', 'LOWER_RETURN_HIGHER_EFFICIENCY'] for v in same_cat_verdicts):
        results['overall_verdict'] = 'PARTIALLY_JUSTIFIED'
        results['overall_interpretation'] = 'Portfolio ha meriti vs benchmark di categoria.'
    else:
        results['overall_verdict'] = 'REVIEW_NEEDED'
        results['overall_interpretation'] = 'Portfolio sottoperforma benchmark di categoria - rivedere.'
    
    return results
