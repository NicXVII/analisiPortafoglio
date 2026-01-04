"""
Output Module
=============
Funzioni per la stampa e visualizzazione dei risultati.

Include:
- print_summary: report metriche completo
- print_portfolio_critique: analisi criticità
- print_senior_architect_analysis: analisi istituzionale
- plot_results: grafici
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Any, List
import os

from taxonomy import (
    calculate_geographic_exposure, analyze_function_exposure,
    CORE_GLOBAL_ETF, CORE_REGIONAL_ETF, EMERGING_ETF, SATELLITE_KEYWORDS, REIT_ETF
)
from analysis import (
    detect_false_diversification, identify_structural_strengths,
    generate_verdict_bullets
)


# ================================================================================
# SUMMARY OUTPUT
# ================================================================================

def print_summary(
    metrics: dict,
    risk_contrib: pd.DataFrame,
    corr: pd.DataFrame,
    asset_metrics: pd.DataFrame
) -> None:
    """Stampa report completo."""
    
    print("\n" + "=" * 70)
    print("                      PORTFOLIO ANALYSIS REPORT")
    print("                          (Methodology v2.0)")
    print("=" * 70)
    
    # === PERFORMANCE ===
    print("\n📈 PERFORMANCE")
    print("-" * 50)
    print(f"  Total ROI:              {metrics['total_roi']:>12.2%}")
    print(f"  CAGR (geometric):       {metrics['cagr']:>12.2%}")
    print(f"  Volatility (ann.):      {metrics['volatility']:>12.2%}")
    
    # === RISK-ADJUSTED ===
    print("\n📊 RISK-ADJUSTED METRICS")
    print("-" * 50)
    print(f"  Sharpe Ratio:           {metrics['sharpe']:>12.2f}")
    print(f"  Sortino Ratio:          {metrics['sortino']:>12.2f}")
    print(f"  Calmar Ratio:           {metrics['calmar']:>12.2f}")
    print(f"  Profit Factor:          {metrics['profit_factor']:>12.2f}")
    print(f"  Gain/Loss Ratio:        {metrics['gain_loss_ratio']:>12.2f}")
    
    # === DRAWDOWN ===
    print("\n📉 DRAWDOWN ANALYSIS")
    print("-" * 50)
    print(f"  Max Drawdown:           {metrics['max_drawdown']:>12.2%}")
    print(f"    Peak Date:            {metrics['max_dd_peak'].strftime('%Y-%m-%d'):>12}")
    print(f"    Trough Date:          {metrics['max_dd_trough'].strftime('%Y-%m-%d'):>12}")
    print(f"  Avg Drawdown:           {metrics['avg_drawdown']:>12.2%}")
    print(f"  Current Drawdown:       {metrics['current_drawdown']:>12.2%}")
    
    # === VAR/CVAR ===
    print("\n⚠️  TAIL RISK (95% confidence)")
    print("-" * 50)
    print(f"  VaR (daily):            {metrics['var_95_daily']:>12.2%}")
    print(f"  CVaR (daily):           {metrics['cvar_95_daily']:>12.2%}")
    print(f"  VaR (annualized):       {metrics['var_95_annual']:>12.2%}")
    print(f"  CVaR (annualized):      {metrics['cvar_95_annual']:>12.2%}")
    
    # === MONTHLY ===
    print("\n📅 MONTHLY STATISTICS")
    print("-" * 50)
    print(f"  Months Up:              {metrics['months_up']:>8} / {metrics['months_total']} ({metrics['win_rate_monthly']:.1%})")
    print(f"  Months Down:            {metrics['months_down']:>8} / {metrics['months_total']}")
    print(f"  Best Month:             {metrics['best_month']:>12.2%}")
    print(f"  Worst Month:            {metrics['worst_month']:>12.2%}")
    print(f"  Avg Month:              {metrics['avg_month']:>12.2%}")
    
    # === YEARLY ===
    print("\n📆 YEARLY STATISTICS")
    print("-" * 50)
    print(f"  Years Up:               {metrics['years_up']:>8} / {metrics['years_total']}")
    print(f"  Years Down:             {metrics['years_down']:>8} / {metrics['years_total']}")
    print(f"  Best Year:              {metrics['best_year']:>12.2%}")
    print(f"  Worst Year:             {metrics['worst_year']:>12.2%}")
    
    # === DAILY ===
    print("\n📌 DAILY STATISTICS")
    print("-" * 50)
    win_rate = metrics['days_up'] / metrics['days_total'] if metrics['days_total'] > 0 else 0
    print(f"  Days Up:                {metrics['days_up']:>8} / {metrics['days_total']} ({win_rate:.1%})")
    print(f"  Days Down:              {metrics['days_down']:>8} / {metrics['days_total']}")
    print(f"  Best Day:               {metrics['best_day']:>12.2%}")
    print(f"  Worst Day:              {metrics['worst_day']:>12.2%}")
    
    # === RISK CONTRIBUTION ===
    print("\n" + "=" * 70)
    print("RISK CONTRIBUTION (Component Contribution to Risk)")
    print("=" * 70)
    print(f"{'Ticker':<12} {'Weight':>8} {'MCR':>10} {'CCR':>10} {'CCR%':>10}")
    print("-" * 50)
    for ticker in risk_contrib.index:
        row = risk_contrib.loc[ticker]
        print(f"{ticker:<12} {row['Weight']:>8.2%} {row['MCR']:>10.4f} {row['CCR']:>10.4f} {row['CCR%']:>10.2%}")
    print("-" * 50)
    print(f"{'TOTAL':<12} {risk_contrib['Weight'].sum():>8.2%} {'':<10} {risk_contrib['CCR'].sum():>10.4f} {risk_contrib['CCR%'].sum():>10.2%}")
    
    # === ASSET METRICS ===
    print("\n" + "=" * 70)
    print("INDIVIDUAL ASSET METRICS (annualized)")
    print("=" * 70)
    print(asset_metrics.to_string(float_format=lambda x: f"{x:.4f}"))
    
    # === CORRELATION ===
    print("\n" + "=" * 70)
    print("CORRELATION MATRIX")
    print("=" * 70)
    print(corr.round(2).to_string())


# ================================================================================
# PORTFOLIO CRITIQUE OUTPUT
# ================================================================================

def print_portfolio_critique(issues: list, regime_info: Dict[str, Any]) -> None:
    """
    Stampa analisi critica del portafoglio con identificazione tipo.
    """
    
    regime = regime_info["regime"]
    portfolio_type = regime_info.get("portfolio_type", regime)
    confidence = regime_info["confidence"]
    composition = regime_info["composition"]
    trade_offs = regime_info.get("trade_offs", [])
    thresholds = regime_info["thresholds"]
    type_reason = regime_info.get("type_reason", "")
    
    print("\n" + "=" * 70)
    print("🔍 QUANT PORTFOLIO TYPE ANALYSIS")
    print("=" * 70)
    
    # === TIPO IDENTIFICATO ===
    type_display = {
        "EQUITY_GROWTH_CORE": "📈 EQUITY GROWTH (Core-Driven)",
        "EQUITY_GROWTH_DIVERSIFIED": "🌍 EQUITY GROWTH (Diversified)",
        "EQUITY_GROWTH": "📈 EQUITY GROWTH",
        "EQUITY_MULTI_BLOCK": "🧱 EQUITY MULTI-BLOCK",
        "EQUITY_CORE_DRIVEN": "📊 EQUITY CORE-DRIVEN",
        "BALANCED": "⚖️ BALANCED (60/40)",
        "DEFENSIVE": "🛡️ DEFENSIVE / CAPITAL PRESERVATION",
        "INCOME_YIELD": "💰 INCOME / YIELD",
        "BARBELL_THEMATIC": "🎯 BARBELL THEMATIC",
        "RISK_PARITY": "📐 RISK PARITY (Multi-Asset)",
        "TACTICAL": "🎲 TACTICAL / OPPORTUNISTIC",
    }
    
    type_descriptions = {
        "EQUITY_GROWTH_CORE": "Beta concentrato su singolo driver, alta volatilità",
        "EQUITY_GROWTH_DIVERSIFIED": "Multi-core regionale, rischio distribuito ✓",
        "EQUITY_GROWTH": "Focus crescita, alta tolleranza rischio",
        "EQUITY_MULTI_BLOCK": "Pesi equilibrati, diversificazione intra-equity",
        "EQUITY_CORE_DRIVEN": "World index dominante + satellite",
        "BALANCED": "Multi-asset, drawdown contenuto",
        "DEFENSIVE": "Preservazione capitale, min drawdown",
        "INCOME_YIELD": "Dividendi/cedole, income stream",
        "BARBELL_THEMATIC": "Core + scommesse tematiche",
        "RISK_PARITY": "Multi-asset (bond+equity), risk contribution equilibrata",
        "TACTICAL": "Allocazione opportunistica",
    }
    
    print(f"\n🏷️  TIPO IDENTIFICATO: {type_display.get(portfolio_type, portfolio_type)}")
    print(f"   {type_descriptions.get(portfolio_type, '')}")
    print(f"   Confidence: {confidence:.0%}")
    if type_reason:
        print(f"   Motivazione: {type_reason}")
    
    # === COMPOSIZIONE DETTAGLIATA ===
    print("\n📊 COMPOSIZIONE PORTAFOGLIO:")
    print("-" * 50)
    print(f"   Core Globale:       {composition['core_global']:>6.1%}  (VT, VWCE, IWDA)")
    print(f"   Core Regionale:     {composition['core_regional']:>6.1%}  (IVV, EWJ, VGK...)")
    
    if composition.get('structural_noncore', 0) > 0:
        print(f"   --- Strutturale Non-Core ---")
        if composition.get('small_cap', 0) > 0:
            print(f"     Small Cap:        {composition['small_cap']:>6.1%}  (IUSN, IWM...)")
        if composition.get('reit', 0) > 0:
            print(f"     REIT:             {composition['reit']:>6.1%}  (VNQ, VNQI...)")
        if composition.get('factor', 0) > 0:
            print(f"     Fattoriale:       {composition['factor']:>6.1%}  (MTUM, QUAL...)")
        if composition.get('sector', 0) > 0:
            print(f"     Settoriale:       {composition['sector']:>6.1%}  (IBB, XLF...)")
    
    if composition.get('thematic_pure', 0) > 0 or composition.get('true_satellite', 0) > 0:
        thematic = composition.get('thematic_pure', 0) or composition.get('true_satellite', 0)
        print(f"   Tematico Puro:      {thematic:>6.1%}  (URA, ARKK, SRVR...)")
    
    # EM exposure
    total_em = composition.get('total_emerging', 0)
    if total_em > 0 or composition.get('emerging_broad', 0) > 0 or composition.get('em_single_country', 0) > 0:
        print(f"   --- Emerging Markets ---")
        if composition.get('emerging_broad', 0) > 0:
            print(f"     EM Broad:         {composition['emerging_broad']:>6.1%}  (EEM, VWO...)")
        if composition.get('em_single_country', 0) > 0:
            print(f"     EM Single:        {composition['em_single_country']:>6.1%}  (INDA, MCHI...)")
    
    # Other equity (non classificato)
    if composition.get('other_equity', 0) > 0:
        print(f"   Altro Equity:       {composition['other_equity']:>6.1%}  (non classificato)")
    
    print(f"   Bond:               {composition['bond']:>6.1%}")
    if composition.get('gold_commodity', 0) > 0:
        print(f"   Gold/Commodity:     {composition['gold_commodity']:>6.1%}")
    if composition.get('dividend_income', 0) > 0:
        print(f"   Dividend/Income:    {composition['dividend_income']:>6.1%}")
    print("-" * 50)
    
    # === SANITY CHECK ===
    total_allocated = composition.get('total_allocated', composition.get('total_equity', 0) + composition.get('bond', 0) + composition.get('gold_commodity', 0))
    if abs(total_allocated - 1.0) > 0.01:
        print(f"   ⚠️ WARNING: Totale allocato = {total_allocated:.1%} (atteso 100%)")
    
    print(f"   TOTALE EQUITY:      {composition['total_equity']:>6.1%}")
    if composition.get('total_defensive', 0) > 0:
        print(f"   TOTALE DEFENSIVE:   {composition['total_defensive']:>6.1%}")
    
    # === SOGLIE TYPE-SPECIFIC ===
    print(f"\n📏 SOGLIE PER TIPO '{portfolio_type}':")
    print("-" * 50)
    print(f"   Max singola posizione:  {thresholds['max_single_position']:>6.0%}")
    print(f"   Max top 3:              {thresholds['max_top3']:>6.0%}")
    print(f"   Max satellite singolo:  {thresholds['max_satellite_single']:>6.0%}")
    print(f"   Max satellite totale:   {thresholds['max_satellite_total']:>6.0%}")
    print(f"   Max drawdown accettato: {thresholds['max_drawdown']:>6.0%}")
    print(f"   Min Sharpe atteso:      {thresholds['min_sharpe']:>6.2f}")
    if 'description' in thresholds:
        print(f"   → {thresholds['description']}")
    
    if 'primary_metrics' in thresholds:
        print(f"\n📌 METRICHE PRIMARIE: {', '.join(thresholds['primary_metrics'])}")
        print(f"   (Queste metriche sono critiche per tipo {portfolio_type})")
    if 'secondary_metrics' in thresholds:
        print(f"   Secondarie: {', '.join(thresholds['secondary_metrics'])}")
    
    # === TRADE-OFF CONSAPEVOLI ===
    if trade_offs:
        print("\n✅ TRADE-OFF CONSAPEVOLI (coerenti con il tipo):")
        print("-" * 50)
        for to in trade_offs:
            print(f"   • {to['message']}")
    
    # === CRITICITÀ ===
    if not issues:
        print("\n" + "=" * 70)
        print("✅ NESSUNA CRITICITÀ RILEVATA")
        print(f"   Portafoglio pienamente coerente con tipo {portfolio_type}")
        print("=" * 70)
    else:
        severity_order = {"🚨": 0, "⚠️": 1, "ℹ️": 2}
        issues_sorted = sorted(issues, key=lambda x: severity_order.get(x["severity"], 3))
        
        critical = [i for i in issues_sorted if i["severity"] == "🚨"]
        warnings = [i for i in issues_sorted if i["severity"] == "⚠️"]
        info = [i for i in issues_sorted if i["severity"] == "ℹ️"]
        
        if critical:
            print("\n🚨 CRITICITÀ SEVERE:")
            print("-" * 50)
            for issue in critical:
                print(f"   • {issue['message']}")
        
        if warnings:
            print("\n⚠️  ATTENZIONE:")
            print("-" * 50)
            for issue in warnings:
                print(f"   • {issue['message']}")
        
        if info:
            print("\nℹ️  NOTE:")
            print("-" * 50)
            for issue in info:
                print(f"   • {issue['message']}")
    
    # === VERDETTO FINALE ===
    print("\n" + "=" * 70)
    
    real_critical = [i for i in issues if i["severity"] == "🚨" and i["type"] != "DATA_QUALITY"]
    real_warnings = [i for i in issues if i["severity"] == "⚠️"]
    
    if real_critical:
        print("📋 VERDETTO: ❌ DA RISTRUTTURARE")
        print(f"   Criticità severe non coerenti con tipo {portfolio_type}.")
        print("   Suggerimento: rivedi la composizione o considera un tipo diverso.")
    elif len(real_warnings) >= 3:
        print("📋 VERDETTO: ⚠️ APPROVATO CON RISERVE")
        print(f"   Diverse aree di miglioramento per tipo {portfolio_type}.")
        print("   Il portafoglio funziona ma può essere ottimizzato.")
    elif real_warnings:
        print("📋 VERDETTO: ✅ APPROVATO CON TRADE-OFF CONSAPEVOLI")
        print(f"   Portafoglio coerente con tipo {portfolio_type}.")
        print(f"   Trade-off identificati e accettabili per la strategia.")
    else:
        print("📋 VERDETTO: ✅ APPROVATO - STRUTTURALMENTE SOLIDO")
        print(f"   Portafoglio pienamente coerente con tipo {portfolio_type}.")
        print("   Nessuna criticità, costruzione solida.")
    
    print("=" * 70)


# ================================================================================
# SENIOR ARCHITECT OUTPUT
# ================================================================================

def print_senior_architect_analysis(
    tickers: list,
    weights: np.ndarray,
    metrics: dict,
    regime_info: Dict[str, Any],
    issues: list,
    corr: pd.DataFrame = None
) -> None:
    """
    SENIOR PORTFOLIO ARCHITECT ANALYSIS (Vanguard Style)
    """
    
    portfolio_type = regime_info.get("portfolio_type", "TACTICAL")
    composition = regime_info.get("composition", {})
    
    print("\n" + "=" * 70)
    print("🏛️  SENIOR PORTFOLIO ARCHITECT ANALYSIS")
    print("    Framework Istituzionale (Vanguard Style)")
    print("=" * 70)
    
    # === 1. ESPOSIZIONE GEOGRAFICA REALE ===
    geo_exposure = calculate_geographic_exposure(tickers, weights)
    
    print("\n🌍 ESPOSIZIONE GEOGRAFICA EFFETTIVA:")
    print("-" * 50)
    print("   (Calcolata considerando composizione interna ETF)")
    print()
    
    geo_sorted = sorted(geo_exposure.items(), key=lambda x: x[1], reverse=True)
    total_geo = sum(geo_exposure.values())
    
    for region, pct in geo_sorted:
        if pct > 0.01:
            bar_len = int(pct * 40)
            bar = "█" * bar_len
            region_names = {
                "USA": "🇺🇸 USA",
                "Europe": "🇪🇺 Europa",
                "Japan": "🇯🇵 Giappone",
                "EM": "🌏 Emergenti",
                "Other_DM": "🌐 Altri DM"
            }
            print(f"   {region_names.get(region, region):<18} {pct:>6.1%}  {bar}")
    
    print("-" * 50)
    print(f"   Totale:                     {total_geo:>6.1%}")
    
    usa_pct = geo_exposure.get("USA", 0)
    if usa_pct > 0.70:
        print(f"\n   ⚠️ CONCENTRAZIONE USA ELEVATA ({usa_pct:.0%})")
    elif usa_pct > 0.60:
        print(f"\n   ℹ️ Bias USA moderato ({usa_pct:.0%}) - comune per portafogli growth")
    elif usa_pct < 0.45:
        print(f"\n   ✓ Esposizione USA contenuta ({usa_pct:.0%}) - diversificazione effettiva")
    
    # === 2. ESPOSIZIONE PER FUNZIONE ECONOMICA ===
    function_exposure = analyze_function_exposure(tickers, weights)
    
    print("\n\n⚙️  ESPOSIZIONE PER FUNZIONE ECONOMICA:")
    print("-" * 50)
    
    function_names = {
        "CORE_GROWTH": "📈 Core Growth (rendimento principale)",
        "REGIONAL_DIVERSIFICATION": "🌍 Diversificazione Regionale",
        "EM_EXPOSURE": "🌏 Esposizione Emergenti",
        "FACTOR_TILT": "📊 Factor Tilt (size/value/momentum)",
        "REAL_ASSETS": "🏢 Real Assets (REIT/infrastrutture)",
        "CYCLICAL_HEDGE": "⚡ Settori Ciclici",
        "DEFENSIVE_SECTOR": "🛡️ Settori Difensivi",
        "THEMATIC_ALPHA": "🎯 Tematici Alpha (scommesse)",
        "INCOME": "💰 Income (dividendi/cedole)",
        "TAIL_HEDGE": "🔒 Tail Hedge (oro/bond lunghi)"
    }
    
    func_sorted = sorted(function_exposure.items(), key=lambda x: x[1], reverse=True)
    for func, pct in func_sorted:
        if pct > 0.01:
            bar_len = int(pct * 35)
            bar = "▓" * bar_len
            print(f"   {function_names.get(func, func):<40} {pct:>6.1%}  {bar}")
    
    # === 3. CONCENTRAZIONE E FALSE DIVERSIFICAZIONI ===
    print("\n\n🔬 ANALISI CONCENTRAZIONE E OVERLAP:")
    print("-" * 50)
    
    weights_sorted = sorted(weights, reverse=True)
    max_position = weights_sorted[0] if weights_sorted else 0
    top3 = sum(weights_sorted[:3]) if len(weights_sorted) >= 3 else sum(weights_sorted)
    top5 = sum(weights_sorted[:5]) if len(weights_sorted) >= 5 else sum(weights_sorted)
    hhi = sum(w**2 for w in weights)
    effective_n = 1 / hhi if hhi > 0 else len(weights)
    
    print(f"   Max posizione singola:    {max_position:>6.1%}")
    print(f"   Top 3 posizioni:          {top3:>6.1%}")
    print(f"   Top 5 posizioni:          {top5:>6.1%}")
    print(f"   HHI (concentrazione):     {hhi:>6.3f}  (più basso = più diversificato)")
    print(f"   N. effettivo posizioni:   {effective_n:>6.1f}  (vs {len(weights)} nominali)")
    
    false_div_warnings = detect_false_diversification(tickers, weights, geo_exposure, corr)
    
    if false_div_warnings:
        print("\n   🔎 FALSE DIVERSIFICAZIONI RILEVATE:")
        for w in false_div_warnings:
            severity_icon = "🚨" if w["severity"] == "structural" else "ℹ️"
            print(f"      {severity_icon} {w['message']}")
    else:
        print("\n   ✓ Nessuna falsa diversificazione significativa rilevata")
    
    # === 4. PUNTI DI FORZA STRUTTURALI ===
    strengths = identify_structural_strengths(composition, geo_exposure, function_exposure, metrics, weights)
    
    if strengths:
        print("\n\n💪 PUNTI DI FORZA STRUTTURALI:")
        print("-" * 50)
        for i, s in enumerate(strengths, 1):
            print(f"   {i}. {s}")
    
    # === 5. VERDETTO FINALE ===
    bullets = generate_verdict_bullets(portfolio_type, strengths, issues, metrics, composition)
    
    real_critical = [i for i in issues if i.get("severity") == "🚨" and i.get("type") != "DATA_QUALITY"]
    structural_issues = [i for i in issues if i.get("severity") == "⚠️"]
    false_div_structural = [w for w in false_div_warnings if w.get("severity") == "structural"]
    
    print("\n" + "=" * 70)
    
    if real_critical or len(false_div_structural) >= 2:
        print("📋 VERDETTO FINALE: ⛔ STRUTTURALMENTE INCOERENTE")
        print("   Richiede ristrutturazione prima di implementazione")
    elif structural_issues or false_div_structural:
        print("📋 VERDETTO FINALE: ✅ APPROVATO CON TRADE-OFF CONSAPEVOLI")
    elif len(strengths) >= 4:
        print("📋 VERDETTO FINALE: ✅ APPROVATO - COSTRUZIONE ISTITUZIONALE")
    else:
        print("📋 VERDETTO FINALE: ✅ APPROVATO - STRUTTURALMENTE SOLIDO")
    
    print("\n   Motivazioni:")
    for bullet in bullets:
        print(f"   • {bullet}")
    
    print("\n" + "-" * 70)
    print("   Analisi condotta secondo framework Senior Portfolio Architect")
    print("   Standard: Vanguard/BlackRock Institutional Guidelines")
    print("=" * 70)


# ================================================================================
# PLOTTING
# ================================================================================

def plot_results(equity: pd.Series, returns: pd.Series, save_path: str = None) -> None:
    """Genera grafici del portafoglio."""
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 1. Equity Curve
    axes[0, 0].plot(equity.index, equity.values, 'b-', linewidth=1.5)
    axes[0, 0].set_title('Portfolio Equity Curve', fontsize=12, fontweight='bold')
    axes[0, 0].set_xlabel('Date')
    axes[0, 0].set_ylabel('Portfolio Value ($)')
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].fill_between(equity.index, equity.values, alpha=0.3)
    
    # 2. Drawdown
    dd = equity / equity.cummax() - 1
    axes[0, 1].fill_between(dd.index, dd.values, 0, color='red', alpha=0.5)
    axes[0, 1].set_title('Drawdown', fontsize=12, fontweight='bold')
    axes[0, 1].set_xlabel('Date')
    axes[0, 1].set_ylabel('Drawdown (%)')
    axes[0, 1].grid(True, alpha=0.3)
    
    # 3. Returns Distribution
    axes[1, 0].hist(returns.values, bins=50, color='steelblue', alpha=0.7, edgecolor='black')
    axes[1, 0].axvline(returns.mean(), color='red', linestyle='--', label=f'Mean: {returns.mean():.2%}')
    axes[1, 0].axvline(0, color='black', linestyle='-', linewidth=0.5)
    axes[1, 0].set_title('Daily Returns Distribution', fontsize=12, fontweight='bold')
    axes[1, 0].set_xlabel('Daily Return')
    axes[1, 0].set_ylabel('Frequency')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # 4. Rolling Sharpe (252 days)
    rolling_ret = returns.rolling(252).mean() * 252
    rolling_vol = returns.rolling(252).std() * np.sqrt(252)
    rolling_sharpe = (rolling_ret - 0.02) / rolling_vol
    
    axes[1, 1].plot(rolling_sharpe.index, rolling_sharpe.values, 'g-', linewidth=1.5)
    axes[1, 1].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    axes[1, 1].axhline(y=1, color='green', linestyle='--', alpha=0.5, label='Sharpe = 1')
    axes[1, 1].set_title('Rolling Sharpe Ratio (252 days)', fontsize=12, fontweight='bold')
    axes[1, 1].set_xlabel('Date')
    axes[1, 1].set_ylabel('Sharpe Ratio')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save if path provided
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"\n📊 Grafico salvato in: {save_path}")
    
    # Show only if explicitly enabled via environment variable
    # Default: non mostrare (per evitare blocco in ambienti non interattivi)
    if os.environ.get('PORTFOLIO_SHOW_PLOT', 'false').lower() == 'true':
        plt.show()
    
    plt.close()
