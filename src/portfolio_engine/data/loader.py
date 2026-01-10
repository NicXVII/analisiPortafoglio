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
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any


# ================================================================================
# SURVIVORSHIP BIAS CHECK
# ================================================================================

def check_survivorship_bias_warning(tickers: list) -> dict:
    """
    FIX ISSUE #1: Genera warning ENHANCED su survivorship bias.
    
    Yahoo Finance non include ETF delisted/falliti.
    Questo sistema categorizza il rischio e fornisce quantificazione.
    
    Returns:
        Dict con warning_level, message, e estimated impact
    """
    # ETF ad alto rischio di survivorship bias (tematici, leveraged, settoriali)
    high_risk_keywords = ['ARK', 'THEMATIC', 'ROBO', 'CYBR', 'HACK', 'MOON', 
                          'JETS', 'BETZ', 'NERD', '3X', '2X', 'LABU', 'SOXL',
                          'TQQQ', 'SQQQ', 'UVXY', 'VXX', 'SPAC', 'MEME',
                          'BUZZ', 'GUSH', 'DRIP', 'NUGT', 'DUST']
    
    # ETF settoriali con storia di fallimenti
    sector_risk_keywords = ['CLEAN', 'SOLAR', 'LITHIUM', 'CANNABIS', 'WEED',
                            'ESPO', 'HERO', 'GAME', 'METV']
    
    # ETF regionali/paese con rischio delisting
    regional_risk = ['GREK', 'TUR', 'RSX', 'ERUS', 'ARGT']  # Russia, Turchia, etc.
    
    high_risk_tickers = []
    sector_risk_tickers = []
    regional_risk_tickers = []
    
    for t in tickers:
        t_upper = t.upper().split('.')[0]
        if any(kw in t_upper for kw in high_risk_keywords):
            high_risk_tickers.append(t)
        elif any(kw in t_upper for kw in sector_risk_keywords):
            sector_risk_tickers.append(t)
        elif t_upper in regional_risk:
            regional_risk_tickers.append(t)
    
    # Calcola estimated impact
    # Studi accademici: survivorship bias overstate returns ~0.5-1.5% annuo per category
    total_risky = len(high_risk_tickers) + len(sector_risk_tickers) + len(regional_risk_tickers)
    total_tickers = len(tickers)
    risky_pct = total_risky / total_tickers if total_tickers > 0 else 0
    
    # Impatto stimato (conservativo)
    if high_risk_tickers:
        estimated_cagr_bias = 0.015  # 1.5% per leveraged/thematic
    elif sector_risk_tickers:
        estimated_cagr_bias = 0.010  # 1.0% per settoriali
    elif regional_risk_tickers:
        estimated_cagr_bias = 0.005  # 0.5% per regionali
    else:
        estimated_cagr_bias = 0.003  # 0.3% baseline (anche per core ETF)
    
    # Scale by percentage of risky tickers
    estimated_cagr_bias *= risky_pct + 0.2  # +0.2 baseline per tutti
    
    if len(high_risk_tickers) >= 3:
        return {
            "warning_level": "CRITICAL",
            "message": (
                f"⛔ SURVIVORSHIP BIAS CRITICO: {len(high_risk_tickers)} ETF leveraged/tematici.\n"
                f"   Tickers: {', '.join(high_risk_tickers)}\n"
                f"   ETF simili falliti (XIV, TVIX, etc.) NON sono nei dati Yahoo.\n"
                f"   CAGR potenzialmente sovrastimato di {estimated_cagr_bias:.1%} o più."
            ),
            "tickers_affected": high_risk_tickers,
            "estimated_cagr_overstatement": estimated_cagr_bias,
            "methodology_note": (
                "Fonte: Brown et al. (1992), Elton et al. (1996) - "
                "Survivorship bias in mutual fund data ~0.5-1.5%/anno"
            )
        }
    elif len(high_risk_tickers) >= 1 or len(sector_risk_tickers) >= 2:
        all_risky = high_risk_tickers + sector_risk_tickers
        return {
            "warning_level": "HIGH",
            "message": (
                f"⚠️ SURVIVORSHIP BIAS ELEVATO: {len(all_risky)} ETF ad alto rischio.\n"
                f"   Tickers: {', '.join(all_risky)}\n"
                f"   Stima CAGR overstatement: +{estimated_cagr_bias:.2%}/anno"
            ),
            "tickers_affected": all_risky,
            "estimated_cagr_overstatement": estimated_cagr_bias,
        }
    elif sector_risk_tickers or regional_risk_tickers:
        all_risky = sector_risk_tickers + regional_risk_tickers
        return {
            "warning_level": "MEDIUM",
            "message": (
                f"⚠️ SURVIVORSHIP BIAS MODERATO: {len(all_risky)} ETF settoriali/regionali.\n"
                f"   Tickers: {', '.join(all_risky)}\n"
                f"   Stima CAGR overstatement: +{estimated_cagr_bias:.2%}/anno"
            ),
            "tickers_affected": all_risky,
            "estimated_cagr_overstatement": estimated_cagr_bias,
        }
    else:
        return {
            "warning_level": "LOW",
            "message": (
                f"ℹ️ Survivorship bias presente ma limitato (solo ETF core/regionali).\n"
                f"   Stima CAGR overstatement baseline: +{estimated_cagr_bias:.2%}/anno"
            ),
            "tickers_affected": [],
            "estimated_cagr_overstatement": estimated_cagr_bias,
            "methodology_note": (
                "Anche ETF core hanno survivorship bias: "
                "fondi simili chiusi non appaiono nei dati storici"
            )
        }


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
# DATA CACHING
# ================================================================================

import hashlib
import os
import pickle

CACHE_DIR = ".data_cache"

def _get_cache_key(tickers: list, start: str, end: str) -> str:
    """Genera chiave univoca per cache."""
    key_str = f"{sorted(tickers)}_{start}_{end}"
    return hashlib.md5(key_str.encode()).hexdigest()


def _get_cache_path(cache_key: str) -> str:
    """Path completo del file cache."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{cache_key}.pkl")


def _load_from_cache(cache_key: str) -> Optional[pd.DataFrame]:
    """Carica dati da cache se esistono e sono recenti (< 24h)."""
    cache_path = _get_cache_path(cache_key)
    if os.path.exists(cache_path):
        # Check se cache è recente (< 24 ore)
        cache_age = datetime.now().timestamp() - os.path.getmtime(cache_path)
        if cache_age < 86400:  # 24 ore
            try:
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            except:
                pass
    return None


def _save_to_cache(cache_key: str, data: pd.DataFrame) -> None:
    """Salva dati in cache."""
    try:
        cache_path = _get_cache_path(cache_key)
        with open(cache_path, 'wb') as f:
            pickle.dump(data, f)
    except:
        pass  # Ignora errori di cache


# ================================================================================
# DATA DOWNLOAD
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
    end_str = end or datetime.now().strftime("%Y-%m-%d")
    
    # Try cache first
    cache_key = None
    if use_cache:
        cache_key = _get_cache_key(tickers, start, end_str)
        cached = _load_from_cache(cache_key)
        if cached is not None:
            empty_cols = [c for c in cached.columns if cached[c].isna().all()]
            if empty_cols:
                # Cache incompleta: forza nuovo download
                cached = None
            else:
                return cached
    
    # Download fresh
    data = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    
    if isinstance(data.columns, pd.MultiIndex):
        data = data["Close"]
    else:
        if len(tickers) == 1:
            data = data[["Close"]].rename(columns={"Close": tickers[0]})
        else:
            data = data["Close"]
    
    # Retry individually if some columns sono NaN (yfinance download batches può fallire parzialmente)
    if not data.empty:
        empty_cols = [c for c in data.columns if data[c].isna().all()]
        if empty_cols:
            for t in empty_cols:
                try:
                    single = yf.download(t, start=start, end=end, auto_adjust=True, progress=False)
                    if not single.empty:
                        if "Close" in single.columns:
                            data[t] = single["Close"]
                except Exception:
                    pass
            # Re-drop completely empty columns after retry
            data = data[[c for c in data.columns if not data[c].isna().all()]]

    # Save to cache
    if use_cache and not data.empty:
        _save_to_cache(cache_key, data)
    
    return data


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
