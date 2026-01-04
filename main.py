"""
Portfolio Analysis Tool v2.1
============================
Versione modulare con architettura a componenti.

Moduli:
- metrics.py: Calcolo metriche (returns, CAGR, Sharpe, Sortino, VaR, etc.)
- taxonomy.py: Classificazione ETF, esposizioni geografiche/funzionali
- analysis.py: Portfolio type detection, issue analysis
- output.py: Funzioni di output/stampa
- export.py: Export dati (CSV, Excel, JSON, HTML, grafici)
- data.py: Download e gestione dati
- config.py: Configurazione portafoglio

Metodologie:
- Simple returns per aggregazione portafoglio
- CAGR geometrico dall'equity curve
- Sortino con Target Downside Deviation corretta
- VaR/CVaR storico
- Risk contribution basata su matrice covarianza
"""

import numpy as np
import pandas as pd
import warnings
import os
warnings.filterwarnings('ignore', category=FutureWarning)

# === IMPORTS DAI MODULI ===
from config import get_config

from metrics import (
    calculate_simple_returns,
    calculate_cagr_correct,
    calculate_annualized_volatility,
    calculate_all_metrics,
    calculate_risk_contribution_correct
)

from data import (
    download_data,
    calculate_start_date,
    simulate_portfolio_correct
)

from analysis import (
    analyze_portfolio_issues
)

from output import (
    print_summary,
    print_portfolio_critique,
    print_senior_architect_analysis,
    plot_results
)

from export import (
    export_all_data
)


# =========================
# MAIN ANALYSIS FUNCTION
# =========================

def analyze_portfolio(config: dict) -> None:
    """
    Funzione principale di analisi portafoglio.
    
    Args:
        config: Dizionario configurazione con:
            - tickers: lista ticker
            - weights: lista pesi
            - years_history: anni di storico
            - end_date: data fine
            - start_date: data inizio (opzionale)
            - risk_free_annual: tasso risk-free
            - rebalance: frequenza ribilanciamento
            - var_confidence: confidenza VaR
            - export: config export
    """
    # === CONFIG ===
    tickers = config["tickers"]
    weights = np.array(config["weights"], dtype=float)
    years = config.get("years_history", 5)
    end = config["end_date"]
    start = config["start_date"] or calculate_start_date(years, end)
    risk_free = config["risk_free_annual"]
    rebalance = config.get("rebalance")
    var_conf = config.get("var_confidence", 0.95)
    
    # === VALIDAZIONE ===
    if len(tickers) != len(weights):
        raise ValueError("Tickers e weights devono avere stessa lunghezza")
    
    weights = weights / weights.sum()  # Normalizza a 100%
    
    # === DOWNLOAD DATI ===
    print(f"Downloading data for {len(tickers)} tickers...")
    prices = download_data(tickers, start, end)
    
    # === VALIDAZIONE DATI ===
    if prices.empty:
        raise RuntimeError("Nessun dato scaricato")
    
    missing = [t for t in tickers if t not in prices.columns]
    if missing:
        raise RuntimeError(f"Mancano dati per: {missing}")
    
    empty_cols = [c for c in prices.columns if prices[c].isna().all()]
    if empty_cols:
        raise RuntimeError(f"Ticker vuoti: {empty_cols}")
    
    prices = prices.dropna(how="all").ffill().dropna()
    
    print(f"Data range: {prices.index[0].date()} to {prices.index[-1].date()}")
    print(f"Trading days: {len(prices)}")
    
    # === SIMULAZIONE PORTAFOGLIO ===
    equity, port_ret = simulate_portfolio_correct(prices, weights, rebalance)
    
    # === CALCOLO METRICHE ===
    metrics = calculate_all_metrics(equity, port_ret, risk_free, var_conf)
    
    # === METRICHE PER ASSET ===
    simple_ret = calculate_simple_returns(prices)
    
    asset_cagr = {}
    asset_vol = {}
    for t in tickers:
        asset_eq = (1 + simple_ret[t]).cumprod()
        asset_cagr[t] = calculate_cagr_correct(asset_eq)
        asset_vol[t] = calculate_annualized_volatility(simple_ret[t])
    
    # === RISK CONTRIBUTION ===
    risk_contrib = calculate_risk_contribution_correct(simple_ret, weights, tickers)
    
    # === ASSET SUMMARY ===
    asset_df = pd.DataFrame({
        "Weight": weights,
        "CAGR": [asset_cagr[t] for t in tickers],
        "Vol": [asset_vol[t] for t in tickers],
    }, index=tickers)
    
    asset_df = asset_df.join(risk_contrib[['CCR%']].rename(columns={'CCR%': 'RiskContrib%'}))
    
    # === CORRELAZIONE ===
    corr = simple_ret.corr()
    
    # === OUTPUT PRINCIPALE ===
    print_summary(metrics, risk_contrib, corr, asset_df)
    
    # === ANALISI CRITICITÀ (TYPE-AWARE) ===
    issues, regime_info = analyze_portfolio_issues(
        weights=weights,
        tickers=tickers,
        corr=corr,
        risk_contrib=risk_contrib,
        asset_metrics=asset_df,
        metrics=metrics
    )
    print_portfolio_critique(issues, regime_info)
    
    # === SENIOR ARCHITECT ANALYSIS ===
    print_senior_architect_analysis(
        tickers=tickers,
        weights=weights,
        metrics=metrics,
        regime_info=regime_info,
        issues=issues,
        corr=corr
    )
    
    # === EXPORT ===
    export_config = config.get("export", {})
    if export_config.get("enabled", False):
        data_range = (str(prices.index[0].date()), str(prices.index[-1].date()))
        export_all_data(
            export_config=export_config,
            equity=equity,
            returns=port_ret,
            metrics=metrics,
            risk_contrib=risk_contrib,
            asset_metrics=asset_df,
            corr=corr,
            prices=prices,
            config=config,
            data_range=data_range
        )
    
    # === GRAFICI ===
    # Salva sempre il grafico base
    os.makedirs('output', exist_ok=True)
    plot_results(equity, port_ret, save_path='output/portfolio_analysis.png')


# =========================
# MAIN ENTRY POINT
# =========================

if __name__ == "__main__":
    CONFIG = get_config()
    analyze_portfolio(CONFIG)
