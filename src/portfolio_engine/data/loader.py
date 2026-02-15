"""
Data Module
===========
Funzioni per download e gestione dati.

Include:
- download_data: download dati da Yahoo Finance
- calculate_start_date: calcolo data inizio
- simulate_portfolio_correct: simulazione portafoglio

⚠️ SURVIVORSHIP BIAS WARNING:
Yahoo Finance NON include ETF delisted/falliti. Se un ETF va a zero e viene
rimosso, sparisce dallo storico. Questo significa che l'analisi considera
SOLO i survivor, sovrastimando sistematicamente le metriche reali.

Esempio: Se nel 2021 avessi avuto ARKK + 3 ETF tematici falliti, Yahoo
mostra solo ARKK, ignorando i -100% degli altri. Le metriche osservate
(Sharpe, CAGR, MaxDD) sono TUTTE sovrastimate.

TODO: Implementare data source alternativo con dead ETFs o aggiungere
survivorship bias adjustment factor.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List

from portfolio_engine.data_providers.yahoo_client import download_prices
from portfolio_engine.utils.logger import get_logger

logger = get_logger(__name__)


# ================================================================================
# SURVIVORSHIP BIAS CHECK (enhanced)
# ================================================================================

def _confidence_to_label(score: float) -> str:
    if score >= 0.80:
        return "HIGH"
    if score >= 0.60:
        return "MEDIUM"
    if score >= 0.40:
        return "LOW"
    return "VERY_LOW"


def _generate_survivorship_recommendation(warnings: List[Dict[str, Any]], confidence: float) -> str:
    if confidence < 0.50:
        return ("ATTENZIONE: dati potenzialmente distorti da survivorship bias. "
                "Ridurre peso ETF tematici/leveraged, usare periodo più breve, "
                "interpretare le metriche con cautela.")
    if confidence < 0.70:
        return ("Bias moderato: metriche affidabili per core ETF, ma cautela su tematici. "
                "Backtest potrebbe essere ottimistico del 5-15%.")
    return ("Bias contenuto: risultati ragionevolmente affidabili per ETF core/large.")


def check_survivorship_bias_warning(
    tickers: list,
    returns: Optional[pd.DataFrame] = None,
    start_date: Optional[datetime] = None
) -> dict:
    """
    Analisi avanzata del survivorship bias (Fix M1).

    - Usa keyword risk buckets (leveraged/thematic/regional)
    - Misura copertura storica effettiva vs richiesta
    - Calcola un confidence_score 0-1 per l'attendibilità delle metriche
    """
    warnings: List[Dict[str, Any]] = []
    confidence_penalty = 0.0

    high_risk_keywords = ['ARK', 'TQQQ', 'SQQQ', 'UVXY', 'SPXU', 'TECL', 'LABU', 'SOXL']
    thematic_keywords = ['ROBOT', 'SEMI', 'CLEAN', 'CYBER', 'GENOME', 'ESPO', 'BOTZ', 'ROBO', 'METV']
    regional_risk = ['GREK', 'TUR', 'RSX', 'ERUS', 'ARGT']

    for ticker in tickers:
        t = ticker.upper()
        if any(kw in t for kw in high_risk_keywords):
            warnings.append({
                "ticker": ticker,
                "type": "LEVERAGED_INVERSE",
                "severity": "HIGH",
                "message": f"{ticker}: ETF leveraged/inverse → survivorship bias elevato."
            })
            confidence_penalty += 0.15
        elif any(kw in t for kw in thematic_keywords):
            warnings.append({
                "ticker": ticker,
                "type": "THEMATIC",
                "severity": "MEDIUM",
                "message": f"{ticker}: ETF tematico → bias moderato (alto turnover)."
            })
            confidence_penalty += 0.08
        elif t.split('.')[0] in regional_risk:
            warnings.append({
                "ticker": ticker,
                "type": "REGIONAL_HIGH_RISK",
                "severity": "MEDIUM",
                "message": f"{ticker}: Paese con storico delisting/sospensioni."
            })
            confidence_penalty += 0.05

    # Copertura storica effettiva
    coverage_ratio = None
    if returns is not None and not returns.empty and start_date:
        years_requested = (datetime.now() - start_date).days / 365.25
        coverage = []
        for ticker in tickers:
            if ticker in returns.columns:
                valid = returns[ticker].dropna()
                if len(valid) > 0:
                    first_date = valid.index[0]
                    years_actual = (valid.index[-1] - first_date).days / 365.25
                    coverage.append(years_actual / max(years_requested, 0.1))
                    if years_actual / max(years_requested, 0.1) < 0.5:
                        warnings.append({
                            "ticker": ticker,
                            "type": "SHORT_HISTORY",
                            "severity": "HIGH",
                            "message": f"{ticker}: solo {years_actual:.1f} anni di storia "
                                       f"su {years_requested:.1f} richiesti."
                        })
                        confidence_penalty += 0.10
        if coverage:
            coverage_ratio = float(np.mean(coverage))

    base_confidence = 0.85
    final_confidence = max(0.30, base_confidence - confidence_penalty)
    confidence_label = _confidence_to_label(final_confidence)

    warning_level = "LOW"
    if confidence_label == "MEDIUM":
        warning_level = "MEDIUM"
    elif confidence_label == "LOW":
        warning_level = "HIGH"
    elif confidence_label == "VERY_LOW":
        warning_level = "CRITICAL"

    recommendation = _generate_survivorship_recommendation(warnings, final_confidence)
    message = (f"Survivorship bias: confidenza {confidence_label} ({final_confidence:.0%}). "
               f"Red flags: {len(warnings)}. {recommendation}")

    result = {
        "warning_level": warning_level,
        "message": message,
        "warnings": warnings,
        "confidence_score": final_confidence,
        "confidence_label": confidence_label,
        "coverage_ratio": coverage_ratio,
        "recommendation": recommendation,
    }
    return result


def detect_illiquidity_issues(prices: pd.DataFrame) -> dict:
    """
    FIX ISSUE #2: Rileva problemi di illiquidità e forward-fill mascherato.
    
    Cerca:
    - Prezzi identici consecutivi (> 3 giorni = sospetto forward fill)
    - Zero returns ripetuti (segnale di halt trading)
    - Gap nei dati che indicano illiquidità
    
    Returns:
        Dict con dettaglio problemi per ticker
    """
    issues = {}
    returns = prices.pct_change()
    
    for ticker in prices.columns:
        ticker_issues = []
        
        # Check prezzi identici consecutivi
        prices_series = prices[ticker].dropna()
        if len(prices_series) > 5:
            # Conta sequenze di prezzi identici
            diff = prices_series.diff()
            zero_diff = (diff == 0)
            
            # Trova sequenze consecutive di zero diff
            consecutive_zeros = 0
            max_consecutive = 0
            total_zero_days = 0
            
            for is_zero in zero_diff:
                if is_zero:
                    consecutive_zeros += 1
                    total_zero_days += 1
                    max_consecutive = max(max_consecutive, consecutive_zeros)
                else:
                    consecutive_zeros = 0
            
            if max_consecutive >= 5:
                ticker_issues.append({
                    'type': 'FORWARD_FILL_SUSPECTED',
                    'severity': 'HIGH',
                    'detail': f"{max_consecutive} giorni consecutivi stesso prezzo (illiquido o halt)"
                })
            elif max_consecutive >= 3:
                ticker_issues.append({
                    'type': 'STALE_PRICES',
                    'severity': 'MEDIUM',
                    'detail': f"{max_consecutive} giorni consecutivi stesso prezzo"
                })
        
        # Check zero returns percentage
        zero_returns = (returns[ticker] == 0).sum()
        zero_pct = zero_returns / len(returns[ticker]) if len(returns[ticker]) > 0 else 0
        
        if zero_pct > 0.10:  # > 10% di giorni con zero return
            ticker_issues.append({
                'type': 'HIGH_ZERO_RETURN_RATIO',
                'severity': 'MEDIUM',
                'detail': f"{zero_pct:.1%} di giorni con rendimento zero (illiquidità)"
            })
        
        if ticker_issues:
            issues[ticker] = ticker_issues
    
    return {
        'has_issues': len(issues) > 0,
        'tickers_affected': list(issues.keys()),
        'details': issues,
        'warning': (
            f"⚠️ ILLIQUIDITY DETECTED: {len(issues)} ticker con problemi di liquidità. "
            "Correlazioni e volatilità potrebbero essere artificialmente ridotte."
        ) if issues else None
    }


# ================================================================================
# DATA DOWNLOAD (delegated to data_providers)
# ================================================================================

def download_data(tickers: list, start: str, end: Optional[str] = None, use_cache: bool = True) -> pd.DataFrame:
    """
    Scarica dati da Yahoo Finance con caching opzionale.
    
    ⚠️ NOTA: Yahoo Finance non include ETF delisted. Questo introduce
    survivorship bias sistematico. Vedi check_survivorship_bias_warning().
    
    Args:
        tickers: Lista di ticker
        start: Data inizio (YYYY-MM-DD)
        end: Data fine (YYYY-MM-DD), default oggi
        use_cache: Se True, usa cache locale (default True)
    
    Returns:
        DataFrame con prezzi di chiusura
    """
    return download_prices(tickers, start=start, end=end, use_cache=use_cache)


def get_currency_map(tickers: list) -> dict:
    """
    Recupera valuta di quotazione per ciascun ticker (best-effort via yfinance).
    """
    import yfinance as yf
    currencies = {}
    for t in tickers:
        cur = None
        try:
            info = yf.Ticker(t).fast_info
            cur = getattr(info, "currency", None) or (info.get("currency") if isinstance(info, dict) else None)
        except Exception:
            cur = None
        currencies[t] = cur
    return currencies


def convert_to_base_currency(
    prices: pd.DataFrame,
    currency_map: dict,
    base_currency: str,
    manual_rates: dict | None = None,
    warn_on_missing: bool = True,
    return_info: bool = False,
) -> pd.DataFrame | tuple:
    """
    Converte i prezzi nella valuta base usando tassi FX di Yahoo o manuali.
    - Se currency == base → nessuna conversione
    - Ticker FX usato: f"{cur}{base}=X" (es. EURUSD=X)
    - manual_rates può fornire override (es. {"EURUSD": 1.08})
    """
    manual_rates = manual_rates or {}
    info = {"missing": [], "converted": [], "skipped": []}

    if prices.empty or not currency_map:
        return (prices, info) if return_info else prices

    converted = prices.copy()
    unique_currencies = {c for c in currency_map.values() if c}
    if unique_currencies <= {None, base_currency}:
        return (converted, info) if return_info else converted

    import yfinance as yf
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Group tickers by currency to avoid redundant FX downloads
    currency_groups: dict[str, list[str]] = {}
    for t in prices.columns:
        cur = currency_map.get(t)
        if cur and cur != base_currency:
            currency_groups.setdefault(cur, []).append(t)

    if not currency_groups:
        return (converted, info) if return_info else converted

    start_dt = str(prices.index.min().date())
    end_dt = str(prices.index.max().date())

    def _fetch_fx(cur: str) -> tuple[str, pd.Series | None]:
        pair = f"{cur}{base_currency}=X"
        if pair in manual_rates:
            return cur, pd.Series(manual_rates[pair], index=prices.index)
        try:
            fx = yf.download(pair, start=start_dt, end=end_dt, progress=False)
            # Normalizza a Series
            if isinstance(fx, pd.DataFrame):
                if isinstance(fx.columns, pd.MultiIndex):
                    fx = fx["Close"]
                if "Close" in fx.columns:
                    fx = fx["Close"]
                elif fx.shape[1] == 1:
                    fx = fx.iloc[:, 0]
            fx = fx.squeeze()
            if fx.empty:
                return cur, None
            rate_series = fx.reindex(prices.index).ffill().bfill()
            return cur, rate_series
        except Exception:
            return cur, None

    max_workers = min(8, max(1, len(currency_groups)))
    fx_rates: dict[str, pd.Series | None] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_fetch_fx, cur): cur for cur in currency_groups}
        for fut in as_completed(futures):
            cur, rate_series = fut.result()
            fx_rates[cur] = rate_series

    # Apply FX rates to tickers
    for cur, tickers_for_cur in currency_groups.items():
        rate_series = fx_rates.get(cur)
        pair = f"{cur}{base_currency}=X"
        if rate_series is None:
            for t in tickers_for_cur:
                if warn_on_missing:
                    logger.warning(f"FX missing for {t} ({cur}->{base_currency}); leaving unconverted.")
                info["missing"].append(t)
            continue
        rate_on_prices = rate_series.reindex(prices.index).ffill().bfill()
        if len(rate_on_prices) != len(prices):
            for t in tickers_for_cur:
                logger.warning(f"FX series length mismatch for {t}; skipping conversion.")
                info["skipped"].append(t)
            continue
        for t in tickers_for_cur:
            converted[t] = prices[t] * rate_on_prices
            info["converted"].append(t)
            logger.info(f"Converted {t} from {cur} to {base_currency} using {pair}")

    return (converted, info) if return_info else converted


def calculate_start_date(years: int, end_date: Optional[str] = None) -> str:
    """
    Calcola data inizio da anni di storico.
    
    Usa relativedelta per gestione corretta degli anni bisestili.
    La formula years*365 introduce errore di ~5 giorni su 20 anni.
    
    Args:
        years: Numero di anni di storico
        end_date: Data fine (YYYY-MM-DD), default oggi
    
    Returns:
        Data inizio (YYYY-MM-DD)
    """
    from dateutil.relativedelta import relativedelta
    end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.now()
    start = end - relativedelta(years=years)
    return start.strftime("%Y-%m-%d")


def check_staleness(prices: pd.DataFrame, limit_days: int = 3) -> Optional[str]:
    """
    Warning se l'ultimo prezzo è più vecchio di limit_days di borsa.
    """
    if prices.empty:
        return "Dati vuoti"
    last_date = prices.index.max()
    delta = datetime.now().date() - last_date.date()
    if delta.days > limit_days:
        return f"Ultimo prezzo del {last_date.date()} (>{limit_days} giorni fa)"
    return None


# ================================================================================
# DATA INTEGRITY LAYER
# ================================================================================

# Policy per gestione inizio serie storiche
# Opzioni: "COMMON_START" | "STAGGERED_ENTRY" | "SYNTHETIC_PROXY"
# FIX: STAGGERED_ENTRY come default per preservare storia completa (es. 20 anni)
DATA_START_POLICY = "STAGGERED_ENTRY"

DATA_POLICY_DESCRIPTIONS = {
    "COMMON_START": "Backtest parte quando TUTTI gli asset hanno dati reali. Conservativo ma perde storia.",
    "STAGGERED_ENTRY": "Ogni asset entra quando nasce, pesi rinormalizzati. Preserva storia completa.",
    "SYNTHETIC_PROXY": "Usa proxy storici per asset mancanti. DEVE essere dichiarato nel report.",
}


def validate_data_integrity(
    prices: pd.DataFrame,
    tickers: list,
    policy: str = None
) -> Tuple[pd.DataFrame, dict]:
    """
    Valida integrità dati secondo policy dichiarata.
    
    ⚠️ METODOLOGIA:
    La gestione dell'inizio delle serie storiche è ESPLICITA, non implicita.
    Il survivorship bias e il backfill bias sono gestiti secondo policy dichiarata.
    
    Args:
        prices: DataFrame con prezzi
        tickers: Lista ticker originali
        policy: Policy da applicare (default: DATA_START_POLICY)
    
    Returns:
        Tuple (prices_validated, integrity_report)
    """
    policy = policy or DATA_START_POLICY
    
    report = {
        "policy": policy,
        "policy_description": DATA_POLICY_DESCRIPTIONS.get(policy, "Unknown"),
        "original_start": str(prices.index[0].date()),
        "original_end": str(prices.index[-1].date()),
        "ticker_starts": {},
        "common_start": None,
        "data_gaps": {},
        "warnings": [],
    }
    
    # Trova prima data valida per ogni ticker
    for ticker in prices.columns:
        first_valid = prices[ticker].first_valid_index()
        if first_valid:
            report["ticker_starts"][ticker] = str(first_valid.date())
    
    # Common start date (quando tutti hanno dati)
    common_start = prices.dropna().index[0] if not prices.dropna().empty else prices.index[0]
    report["common_start"] = str(common_start.date())
    
    # Trova gap nei dati (più di 5 giorni consecutivi di NaN)
    for ticker in prices.columns:
        series = prices[ticker]
        nan_mask = series.isna()
        if nan_mask.any():
            # Conta gap consecutivi
            gap_groups = (nan_mask != nan_mask.shift()).cumsum()
            gap_sizes = nan_mask.groupby(gap_groups).sum()
            large_gaps = gap_sizes[gap_sizes > 5]
            if len(large_gaps) > 0:
                report["data_gaps"][ticker] = int(large_gaps.max())
    
    # Applica policy
    if policy == "COMMON_START":
        # Taglia a common start - il più conservativo
        prices_out = prices.loc[common_start:].copy()
        
        # Warning se perdiamo molti dati
        days_lost = len(prices) - len(prices_out)
        if days_lost > 252:  # Più di 1 anno
            report["warnings"].append(
                f"⚠️ COMMON_START ha eliminato {days_lost} giorni ({days_lost/252:.1f} anni). "
                f"Considera STAGGERED_ENTRY per preservare storia completa."
            )
    
    elif policy == "STAGGERED_ENTRY":
        # Mantieni tutti i dati dalla prima data disponibile di qualsiasi ticker
        prices_out = prices.copy()
        
        # Identifica ticker con storia incompleta rispetto al più vecchio
        earliest_date = min(pd.Timestamp(d) for d in report["ticker_starts"].values())
        latest_inception = max(pd.Timestamp(d) for d in report["ticker_starts"].values())
        report["staggered_info"] = {
            "earliest_data": str(earliest_date.date()),
            "latest_inception": str(latest_inception.date()),
            "full_history_tickers": [],
            "partial_history_tickers": {},
        }
        
        for ticker, start_str in report["ticker_starts"].items():
            start_date = pd.Timestamp(start_str)
            if start_date <= earliest_date + pd.Timedelta(days=30):  # Tolleranza 30 giorni
                report["staggered_info"]["full_history_tickers"].append(ticker)
            else:
                years_missing = (start_date - earliest_date).days / 365.25
                report["staggered_info"]["partial_history_tickers"][ticker] = f"{years_missing:.1f} anni mancanti"
        
        partial = report["staggered_info"]["partial_history_tickers"]
        if partial:
            report["warnings"].append(
                f"ℹ️ STAGGERED_ENTRY: {len(partial)} ticker con storia parziale. "
                f"Pesi rinormalizzati dinamicamente prima delle loro inception dates."
            )
            # Segnala quali ticker mancano per quali periodi
            for ticker, missing in list(partial.items())[:3]:
                report["warnings"].append(f"   • {ticker}: {missing}")
        else:
            report["warnings"].append("✓ STAGGERED_ENTRY: tutti i ticker hanno storia completa.")
    
    elif policy == "SYNTHETIC_PROXY":
        prices_out = prices.copy()
        report["warnings"].append(
            "⚠️ SYNTHETIC_PROXY: backtest usa proxy storici. "
            "Risultati sono INDICATIVI, non replicabili esattamente."
        )
    
    else:
        prices_out = prices.copy()
        report["warnings"].append(f"⚠️ Policy '{policy}' non riconosciuta, dati non modificati.")
    
    # Verifica finale: ancora NaN?
    # La gestione dei NaN dipende dalla policy
    remaining_nan = prices_out.isna().sum().sum()
    if remaining_nan > 0:
        # Identifica dove sono i NaN
        nan_locations = []
        for col in prices_out.columns:
            nan_dates = prices_out[prices_out[col].isna()].index
            if len(nan_dates) > 0:
                nan_locations.append(f"{col}: {len(nan_dates)} NaN")
        
        if policy == "STAGGERED_ENTRY":
            # In STAGGERED_ENTRY, i NaN sono ATTESI (asset non ancora esistenti)
            # NON rimuoviamo righe - saranno gestiti dalla simulazione con pesi rinormalizzati
            report["data_quality_issue"] = False  # Non è un problema, è il design
            report["nan_expected"] = remaining_nan
            report["nan_removed"] = 0
            report["warnings"].append(
                f"ℹ️ STAGGERED_ENTRY: {remaining_nan} NaN = asset non ancora esistenti. "
                f"Gestiti con dynamic weight renormalization nella simulazione."
            )
        else:
            # Per COMMON_START o altri: NaN sono errore dati
            # NON facciamo forward-fill - è distorsione dei dati
            # Invece: rimuoviamo le righe con NaN (holiday mismatch, data issue)
            rows_before = len(prices_out)
            prices_out = prices_out.dropna()
            rows_removed = rows_before - len(prices_out)
            
            report["data_quality_issue"] = True
            report["nan_removed"] = rows_removed
            report["warnings"].append(
                f"⚠️ DATA QUALITY: {remaining_nan} NaN residui dopo common-start. "
                f"Rimossi {rows_removed} giorni con dati incompleti (NO forward-fill per coerenza metodologica). "
                f"Dettagli: {', '.join(nan_locations[:3])}"
            )
    else:
        report["data_quality_issue"] = False
        report["nan_removed"] = 0
    
    return prices_out, report


# ================================================================================
# PORTFOLIO SIMULATION
# ================================================================================

def simulate_portfolio_correct(
    prices: pd.DataFrame,
    weights: np.ndarray,
    rebalance: Optional[str] = None,
    staggered_entry: bool = False
) -> Tuple[pd.Series, pd.Series]:
    """
    Simula portafoglio con simple returns.
    
    FIX STAGGERED_ENTRY: Se staggered_entry=True, i pesi vengono rinormalizzati
    dinamicamente per escludere asset non ancora esistenti (NaN).
    
    Args:
        prices: DataFrame con prezzi
        weights: Array con pesi target
        rebalance: Frequenza ribilanciamento ('daily', 'monthly', 'quarterly', 'yearly', None)
        staggered_entry: Se True, rinormalizza pesi per asset mancanti
    
    Returns:
        Tuple (equity_curve, portfolio_returns)
    """
    # Simple returns
    returns = prices.pct_change()
    
    if staggered_entry:
        # STAGGERED_ENTRY: rinormalizza pesi dinamicamente
        # Per ogni giorno, usa solo asset con dati validi
        weights_series = pd.DataFrame(
            np.tile(weights, (len(returns), 1)),
            index=returns.index,
            columns=returns.columns
        )
        
        # Maschera: 0 dove NaN nei returns, 1 altrove
        valid_mask = (~returns.isna()).astype(float)
        
        # Pesi effettivi: peso * maschera, poi rinormalizza
        effective_weights = weights_series * valid_mask
        weight_sums = effective_weights.sum(axis=1)
        
        # Evita divisione per zero
        weight_sums = weight_sums.replace(0, np.nan)
        normalized_weights = effective_weights.div(weight_sums, axis=0)
        
        # Returns con NaN → 0 (asset non esistenti contribuiscono 0)
        returns_filled = returns.fillna(0)
        
        # Portfolio returns con pesi dinamici
        port_ret = (returns_filled * normalized_weights).sum(axis=1)
        port_ret = port_ret.dropna()
        
        equity = (1 + port_ret).cumprod()
        return equity, port_ret
    
    # Comportamento standard (no staggered)
    returns = returns.dropna()
    
    if rebalance:
        # Portfolio con ribilanciamento periodico
        equity = simulate_rebalanced_portfolio(returns, weights, rebalance)
        # Calcola returns dalla equity curve
        port_ret = equity.pct_change().dropna()
    else:
        # Buy & Hold: ogni asset si muove indipendentemente
        # Simula come se comprasse units proporzionali ai pesi iniziali
        initial_prices = prices.iloc[0]
        units = weights / initial_prices
        
        # Valore portafoglio = somma (units * prices)
        portfolio_value = (prices * units).sum(axis=1)
        equity = portfolio_value / portfolio_value.iloc[0]
        port_ret = equity.pct_change().dropna()
    
    return equity, port_ret


def simulate_rebalanced_portfolio(
    returns: pd.DataFrame,
    weights: np.ndarray,
    rebalance: str
) -> pd.Series:
    """
    Simula portafoglio con ribilanciamento periodico.
    
    Args:
        returns: DataFrame con returns giornalieri
        weights: Array con pesi target
        rebalance: Frequenza ('daily', 'monthly', 'quarterly', 'yearly')
    
    Returns:
        Serie equity curve
    """
    # Mappa frequenza a pandas resampler
    freq_map = {
        'daily': 'D',
        'monthly': 'ME',
        'quarterly': 'QE',
        'yearly': 'YE'
    }
    
    if rebalance == 'daily':
        # Ribilanciamento giornaliero = weighted average returns
        port_ret = (returns * weights).sum(axis=1)
        equity = (1 + port_ret).cumprod()
    else:
        # Ribilanciamento periodico
        freq = freq_map.get(rebalance, 'ME')
        
        # Identifica date di ribilanciamento
        rebal_dates = returns.resample(freq).last().index
        
        equity_values = [1.0]
        current_weights = weights.copy()
        
        for i in range(len(returns)):
            date = returns.index[i]
            day_ret = returns.iloc[i].values
            
            # Calcola return portafoglio con pesi correnti
            port_day_ret = np.dot(current_weights, day_ret)
            new_equity = equity_values[-1] * (1 + port_day_ret)
            equity_values.append(new_equity)
            
            # Aggiorna pesi per drift
            current_weights = current_weights * (1 + day_ret)
            current_weights = current_weights / current_weights.sum()
            
            # Ribilancia se è data di rebalance
            if date in rebal_dates:
                current_weights = weights.copy()
        
        equity = pd.Series(equity_values[1:], index=returns.index)
    
    return equity


# ================================================================================
# RETURNS CALCULATION
# ================================================================================

def calculate_simple_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola simple returns.
    
    Args:
        prices: DataFrame con prezzi
    
    Returns:
        DataFrame con simple returns
    """
    return prices.pct_change().dropna()


def calculate_log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola log returns.
    
    Args:
        prices: DataFrame con prezzi
    
    Returns:
        DataFrame con log returns
    """
    return np.log(prices / prices.shift(1)).dropna()


# ================================================================================
# CRISIS DETECTION
# ================================================================================

# Import from single source of truth
from portfolio_engine.data.definitions.crisis import get_crisis_periods

# Convert to tuple format for backward compatibility: (start_str, end_str, name)
KNOWN_CRISES = [
    (cp.start, cp.end, cp.name)
    for cp in get_crisis_periods()
]


def detect_crisis_in_data(prices: pd.DataFrame, returns: pd.DataFrame = None) -> Dict[str, Any]:
    """
    Rileva se i dati storici includono periodi di crisi sistemica.
    
    Usa due metodi:
    1. Date note delle crisi storiche
    2. Criteri quantitativi (drawdown > 20%, vol spike > 2x)
    
    ⚠️ IMPORTANTE: Se i dati includono crisi, il Monte Carlo NON deve
    raddoppiare la volatilità (sarebbe doppio conteggio del rischio).
    
    Args:
        prices: DataFrame prezzi storici
        returns: DataFrame returns (opzionale, calcolato se non fornito)
    
    Returns:
        Dict con:
        - includes_crisis: bool
        - crisis_periods: List dei periodi identificati
        - method: 'known_dates' o 'quantitative'
        - max_drawdown_observed: float
        - max_vol_spike: float
    """
    if returns is None:
        returns = prices.pct_change().dropna()
    
    data_start = prices.index[0]
    data_end = prices.index[-1]
    
    crisis_periods = []
    
    # 1. Check contro crisi note
    for start_str, end_str, name in KNOWN_CRISES:
        start_date = pd.to_datetime(start_str)
        end_date = pd.to_datetime(end_str)
        
        # Overlap con i dati?
        if data_start <= end_date and data_end >= start_date:
            # Calcola overlap
            overlap_start = max(data_start, start_date)
            overlap_end = min(data_end, end_date)
            overlap_days = (overlap_end - overlap_start).days
            
            if overlap_days > 20:  # Almeno 20 giorni di overlap
                crisis_periods.append({
                    'name': name,
                    'start': str(start_date.date()),
                    'end': str(end_date.date()),
                    'overlap_days': overlap_days,
                    'detection': 'known_dates'
                })
    
    # 2. Criteri quantitativi: cerco drawdown > 15% e/o vol spikes
    # Calcola portfolio equally weighted se multipli asset
    if isinstance(returns, pd.DataFrame) and len(returns.columns) > 1:
        port_ret = returns.mean(axis=1)
    else:
        port_ret = returns.squeeze() if isinstance(returns, pd.DataFrame) else returns
    
    # Rolling max e drawdown
    equity = (1 + port_ret).cumprod()
    rolling_max = equity.expanding().max()
    drawdown = (equity - rolling_max) / rolling_max
    
    # Rolling volatility (21 giorni)
    rolling_vol = port_ret.rolling(21).std() * np.sqrt(252)
    baseline_vol = port_ret.std() * np.sqrt(252)
    
    # Identifica periodi con drawdown severo
    crisis_threshold = -0.15  # -15% drawdown
    vol_spike_threshold = 1.8  # 80% sopra baseline
    
    # Trova cluster di giorni in crisi
    in_crisis = (drawdown < crisis_threshold) | (rolling_vol > baseline_vol * vol_spike_threshold)
    
    # Se troviamo periodi significativi non già nelle crisi note
    if in_crisis.sum() > 20:  # Almeno 20 giorni in condizioni di crisi
        quant_crisis = {
            'name': 'Quantitative Detection',
            'crisis_days': int(in_crisis.sum()),
            'max_drawdown': float(drawdown.min()),
            'max_rolling_vol': float(rolling_vol.max()) if rolling_vol.notna().any() else None,
            'detection': 'quantitative'
        }
        
        # Aggiungi solo se non già coperto dalle crisi note
        if not crisis_periods:
            crisis_periods.append(quant_crisis)
    
    return {
        'includes_crisis': len(crisis_periods) > 0,
        'crisis_periods': crisis_periods,
        'max_drawdown_observed': float(drawdown.min()),
        'max_vol_observed': float(rolling_vol.max()) if rolling_vol.notna().any() else baseline_vol,
        'baseline_vol': float(baseline_vol),
        'data_span_years': (data_end - data_start).days / 365.25
    }
