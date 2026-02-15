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

from portfolio_engine.data.definitions.taxonomy import (
    calculate_geographic_exposure,
    analyze_function_exposure,
    CORE_GLOBAL_ETF,
    CORE_REGIONAL_ETF,
    EMERGING_ETF,
    SATELLITE_KEYWORDS,
    REIT_ETF,
)
from portfolio_engine.data.definitions.etf_classifier import classify_ticker
from portfolio_engine.analytics.analysis import (
    detect_false_diversification,
    identify_structural_strengths,
    generate_verdict_bullets,
)

# Import centralized configuration (Fix C6)
from portfolio_engine.config.user_config import SAMPLE_SIZE_CONFIG, OUTPUT_MODE, SHOW_PLOTS


# ================================================================================
# RETAIL CLIENT REPORT (v3.1)
# ================================================================================

def print_retail_report(
    metrics: dict,
    risk_contrib: pd.DataFrame,
    verdict_info: dict = None,
    benchmark_comparison: dict = None
) -> None:
    """
    Report 1-pagina per cliente retail.
    
    Risponde alle domande chiave:
    - Questo portfolio è OK per me?
    - Performa bene?
    - Cosa devo fare?
    
    Target: 80-100 righe totali.
    """
    print("\n" + "=" * 70)
    print("                   📊 PORTFOLIO ANALYSIS REPORT")
    print("                        (Client View v3.1)")
    print("=" * 70)
    
    # === EXECUTIVE SUMMARY ===
    _print_executive_summary(metrics, risk_contrib, benchmark_comparison)
    
    # === METRICHE CHIAVE ===
    print("\n📈 PERFORMANCE SUMMARY")
    print("-" * 70)
    print(f"  CAGR (annualizzato):    {metrics['cagr']:>12.2%}")
    print(f"  Volatility:             {metrics['volatility']:>12.2%}")
    print(f"  Sharpe Ratio:           {metrics['sharpe']:>12.2f}   (risk-adjusted return)")
    print(f"  Max Drawdown:           {metrics['max_drawdown']:>12.2%}   (worst loss)")
    print(f"  Beta vs Global Market:  {metrics.get('beta', 0):>12.2f}")
    
    # === RISK ASSESSMENT ===
    print("\n⚠️  RISK PROFILE")
    print("-" * 70)
    
    # Top 3 risk contributors
    top3_risk = risk_contrib.nlargest(3, 'RC%')
    print("  Top 3 Risk Contributors:")
    for idx, (ticker, row) in enumerate(top3_risk.iterrows(), 1):
        risk_leverage = row['RC%'] / row['Weight'] if row['Weight'] > 0 else 1.0
        leverage_flag = " ⚠️" if risk_leverage > 2.0 else ""
        print(f"    {idx}. {ticker:<10} Weight: {row['Weight']:>5.1%}, Risk: {row['RC%']:>5.1%}{leverage_flag}")
    
    # VaR daily (solo quello utilizzabile)
    print(f"\n  VaR Daily (95%):        {metrics['var_95_daily']:>12.2%}")
    print(f"  CVaR Daily (95%):       {metrics['cvar_95_daily']:>12.2%}")
    print("  ℹ️ 5% probabilità di perdere più del VaR in un giorno")
    
    # === MONTE CARLO SEMPLIFICATO ===
    print("\n🎲 STRESS SCENARIOS (Monte Carlo)")
    print("-" * 70)
    
    # Calcola scenari (logica semplificata)
    current_cagr = metrics['cagr']
    current_dd = abs(metrics['max_drawdown'])
    
    # Scenario normale (observed)
    print(f"  📊 Scenario Base (osservato):")
    print(f"     CAGR: {current_cagr:>6.1%}  |  Max DD: {current_dd:>6.1%}")
    
    # Scenario stress (worst bootstrap se disponibile)
    stress_cagr = metrics.get('cagr_ci', {}).get('ci_lower', current_cagr * 0.7)
    stress_dd = metrics.get('max_dd_ci', {}).get('ci_upper', current_dd * 1.3)
    print(f"\n  ⚠️  Scenario Stress (plausibile):")
    print(f"     CAGR: {stress_cagr:>6.1%}  |  Max DD: {stress_dd:>6.1%}")
    
    # Takeaway
    if stress_dd > 0.45:
        print(f"\n  💡 TAKEAWAY: In scenari avversi, drawdown può superare 45%.")
        print(f"     Valuta se puoi sostenere psicologicamente questa volatilità.")
    else:
        print(f"\n  💡 TAKEAWAY: Drawdown contenuto anche in stress. Profilo difensivo.")
    
    # === VERDICT & ACTION ===
    if verdict_info:
        print("\n" + "=" * 70)
        print("🎯 VERDICT & RECOMMENDED ACTION")
        print("=" * 70)
        
        verdict_type = verdict_info.get('type', 'UNKNOWN')
        confidence = verdict_info.get('confidence', 0)
        
        # Verdict emoji
        if 'COHERENT' in verdict_type or 'APPROVED' in verdict_type:
            verdict_icon = "✅"
        elif 'MISALIGNED' in verdict_type or 'CRITICAL' in verdict_type:
            verdict_icon = "❌"
        else:
            verdict_icon = "⚠️"
        
        print(f"{verdict_icon} PORTFOLIO STATUS: {verdict_type}")
        print(f"   Confidence: {confidence}%")
        
        # Azione raccomandata
        if confidence >= 70 and 'COHERENT' in verdict_type:
            print("\n💡 AZIONE RACCOMANDATA:")
            print("   ✓ Portfolio allineato al tuo profilo di rischio")
            print("   → Mantieni allocazione, monitora rebalancing trimestrale")
        elif 'MISALIGNED' in verdict_type:
            print("\n💡 AZIONE RACCOMANDATA:")
            print("   ⚠️ Rischio non allineato alle intenzioni dichiarate")
            print("   → Rivedi allocazione o aggiorna il Risk Intent")
        else:
            print("\n💡 AZIONE RACCOMANDATA:")
            print("   → Valuta con consulente le aree di miglioramento sopra")
    
    print("\n" + "=" * 70)
    print("Fine Report - Per analisi completa usa OUTPUT_MODE='professional'")
    print("=" * 70)


# ================================================================================
# EXECUTIVE SUMMARY (Production v3.0)
# ================================================================================

def _print_executive_summary(
    metrics: dict, 
    risk_contrib: pd.DataFrame,
    benchmark_comparison: dict = None
) -> None:
    """
    Genera Executive Summary di 5 righe per decisori rapidi.
    
    Risponde a:
    1. Cos'è questo portfolio?
    2. Performa bene?
    3. Cosa funziona?
    4. Cosa migliorare?
    5. Azione raccomandata
    """
    # Line 1: Portfolio Identity
    cagr = metrics.get('cagr', 0)
    beta = metrics.get('beta', 0)
    sharpe = metrics.get('sharpe', 0)
    max_dd = metrics.get('max_drawdown', 0)
    
    if beta < 0.6:
        risk_profile = "difensivo (beta basso)"
    elif beta < 0.85:
        risk_profile = "bilanciato growth"
    elif beta < 1.15:
        risk_profile = "aggressivo"
    else:
        risk_profile = "molto aggressivo"
    
    print(f"📌 PORTFOLIO: Equity diversificato {risk_profile}, beta {beta:.2f} vs mercato globale")
    
    # Line 2: Performance Assessment
    if sharpe > 0.8:
        perf = "Eccellente"
    elif sharpe > 0.5:
        perf = "Buona"
    elif sharpe > 0.3:
        perf = "Accettabile"
    else:
        perf = "Debole"
    
    print(f"📊 PERFORMANCE: {perf} risk-adjusted return (CAGR {cagr:.1%}, Sharpe {sharpe:.2f})")
    
    # Line 3: What Works
    strengths = []
    if abs(max_dd) < 0.35:
        strengths.append("drawdown contenuto")
    if sharpe > 0.6:
        strengths.append("efficienza ottima")
    if cagr > 0.10:
        strengths.append("rendimento solido")
    
    if strengths:
        print(f"✅ PUNTI DI FORZA: {', '.join(strengths)}")
    else:
        print("✅ PUNTI DI FORZA: Struttura stabile nel lungo periodo")
    
    # Line 4: What to Improve
    issues = []
    top_risk = risk_contrib.nlargest(1, 'RC%')
    if not top_risk.empty:
        top_ticker = top_risk.index[0]
        top_ccr = top_risk.iloc[0]['RC%']
        top_weight = top_risk.iloc[0]['Weight']
        risk_leverage = top_ccr / top_weight if top_weight > 0 else 1.0
        
        if risk_leverage > 2.0:
            issues.append(f"{top_ticker} contribuisce {top_ccr:.0%} al rischio con solo {top_weight:.0%} peso")
    
    if abs(max_dd) > 0.40:
        issues.append(f"drawdown elevato ({max_dd:.0%})")
    
    if issues:
        print(f"⚠️  DA MIGLIORARE: {', '.join(issues)}")
    else:
        print("⚠️  DA MIGLIORARE: Nessuna criticità strutturale rilevata")
    
    # Line 5: Recommended Action
    if sharpe > 0.7 and abs(max_dd) < 0.35:
        action = "✓ Mantieni allocazione attuale, monitora rebalancing"
    elif sharpe < 0.4:
        action = "⚠️ Rivedi asset selection, considera riduzione posizioni a basso Sharpe"
    elif abs(max_dd) > 0.45:
        action = "⚠️ Riduci concentrazione, aggiungi difensivi per contenere drawdown"
    else:
        action = "→ Portfolio funzionale, valuta ottimizzazione posizioni risk leverage >2x"
    
    print(f"💡 AZIONE: {action}")
    print("=" * 70)


# ================================================================================
# SUMMARY OUTPUT
# ================================================================================

def print_summary(
    metrics: dict,
    risk_contrib: pd.DataFrame,
    corr: pd.DataFrame,
    asset_metrics: pd.DataFrame,
    stress_test: dict = None,
    conditional_ccr: dict = None,
    conditional_corr: dict = None,
    benchmark_comparison: dict = None,
    corr_raw: pd.DataFrame = None,     # FIX BUG #1: Raw correlation matrix
    shrinkage_intensity: float = None,  # FIX BUG #1: Shrinkage intensity
    verdict_info: dict = None           # v3.1: Verdict for retail report
) -> None:
    """
    Stampa report - modalità dipende da OUTPUT_MODE config.
    
    - OUTPUT_MODE = 'retail': Report conciso 1-pagina per cliente finale
    - OUTPUT_MODE = 'professional': Report completo + JSON export
    """
    
    # Check output mode
    output_mode = OUTPUT_MODE.lower()
    
    if output_mode == 'retail':
        # Client-facing concise report
        print_retail_report(
            metrics=metrics,
            risk_contrib=risk_contrib,
            verdict_info=verdict_info,
            benchmark_comparison=benchmark_comparison
        )
        return
    
    # PROFESSIONAL MODE - Full diagnostic report
    print("\n" + "=" * 70)
    print("                      PORTFOLIO ANALYSIS REPORT")
    print("                   (Professional Diagnostic v3.1)")
    print("=" * 70)
    
    # NO Executive Summary in professional mode (redundant with detailed sections)
    # Professionals want data, not interpretation
    
    # === METHODOLOGY & ASSUMPTIONS (consolidated disclaimer) ===
    print("\n⚠️  METODOLOGIA E ASSUNZIONI")
    print("-" * 50)
    print("   • Metriche STORICHE: descrivono il passato, non predicono futuro")
    print("   • Returns finanziari: fat tails, volatility clustering")
    print("   • VaR/CVaR: storico (non parametrico), scaling annuale indicativo")
    print("   • Range plausibile*: variabilità campionaria (bootstrap)")
    print("   • Correlazioni: osservate, possono convergere in crisi")
    print("   • Monte Carlo: scenari ipotetici, non previsioni")
    
    # === PERFORMANCE ===
    print("\n📈 PERFORMANCE")
    print("-" * 50)
    print(f"  Total ROI:              {metrics['total_roi']:>12.2%}")
    
    # CAGR con bootstrap range (variabilità campionaria, non predittiva)
    cagr_ci = metrics.get('cagr_ci', {})
    if cagr_ci:
        print(f"  CAGR (geometric):       {metrics['cagr']:>12.2%}")
        print(f"    Range plausibile*:    [{cagr_ci['ci_lower']:.2%}, {cagr_ci['ci_upper']:.2%}]")
    else:
        print(f"  CAGR (geometric):       {metrics['cagr']:>12.2%}")
    print(f"  Volatility (ann.):      {metrics['volatility']:>12.2%}")
    
    # === RISK-ADJUSTED ===
    print("\n📊 RISK-ADJUSTED METRICS")
    print("-" * 50)
    
    # Sharpe con bootstrap range
    sharpe_ci = metrics.get('sharpe_ci', {})
    if sharpe_ci:
        print(f"  Sharpe Ratio:           {metrics['sharpe']:>12.2f}")
        print(f"    Range plausibile*:    [{sharpe_ci['ci_lower']:.2f}, {sharpe_ci['ci_upper']:.2f}]")
        print(f"    Precision:            ±{sharpe_ci['se']:.2f} ({sharpe_ci['n_years']:.1f} yrs)")
    else:
        print(f"  Sharpe Ratio:           {metrics['sharpe']:>12.2f}")
    
    print(f"  Sortino Ratio:          {metrics['sortino']:>12.2f}")
    print(f"  Calmar Ratio:           {metrics['calmar']:>12.2f}")
    print(f"  Profit Factor:          {metrics['profit_factor']:>12.2f}")
    print(f"  Gain/Loss Ratio:        {metrics['gain_loss_ratio']:>12.2f}")
    
    # === DRAWDOWN ===
    print("\n📉 DRAWDOWN ANALYSIS")
    print("-" * 50)
    
    # Max DD con bootstrap range
    max_dd_ci = metrics.get('max_dd_ci', {})
    if max_dd_ci:
        print(f"  Max Drawdown:           {metrics['max_drawdown']:>12.2%}")
        print(f"    Worst plausibile*:    [{max_dd_ci['ci_lower']:.1%}, {max_dd_ci['ci_upper']:.1%}]")
    else:
        print(f"  Max Drawdown:           {metrics['max_drawdown']:>12.2%}")
    
    print(f"    Peak Date:            {metrics['max_dd_peak'].strftime('%Y-%m-%d'):>12}")
    print(f"    Trough Date:          {metrics['max_dd_trough'].strftime('%Y-%m-%d'):>12}")
    print(f"  Avg Drawdown:           {metrics['avg_drawdown']:>12.2%}")
    print(f"  Current Drawdown:       {metrics['current_drawdown']:>12.2%}")
    
    # === VAR/CVAR (simplified, see methodology for assumptions) ===
    print("\n⚠️  TAIL RISK (VaR storico, 95% confidence)")
    print("-" * 50)
    print(f"  VaR (daily):            {metrics['var_95_daily']:>12.2%}")
    print(f"  CVaR (daily):           {metrics['cvar_95_daily']:>12.2%}")
    print(f"  VaR (annual, indicative): {metrics['var_95_annual']:>10.2%}")
    print(f"  CVaR (annual, indicative): {metrics['cvar_95_annual']:>9.2%}")
    print(f"  ℹ️  Scaling annuale: sqrt(T), può sottostimare rischio ~20-40%")
    
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
    print(f"{'Ticker':<12} {'Weight':>8} {'MCR':>10} {'CCR':>10} {'RC%':>10}")
    print("-" * 50)
    for ticker in risk_contrib.index:
        row = risk_contrib.loc[ticker]
        print(f"{ticker:<12} {row['Weight']:>8.2%} {row['MCR']:>10.4f} {row['CCR']:>10.4f} {row['RC%']:>10.2%}")
    print("-" * 50)
    print(f"{'TOTAL':<12} {risk_contrib['Weight'].sum():>8.2%} {'':<10} {risk_contrib['CCR'].sum():>10.4f} {risk_contrib['RC%'].sum():>10.2%}")
    
    # === CCR CONDIZIONALE (normale vs crisi) ===
    # FIX BUG #2: Block conclusions if crisis_days < minimum
    # Now imported from config.py (Fix C6)
    MIN_CRISIS_DAYS = SAMPLE_SIZE_CONFIG['crisis_min_days']
    
    if conditional_ccr:
        summary = conditional_ccr.get('summary', {})
        crisis_days = summary.get('crisis_days', 0)
        
        if crisis_days < MIN_CRISIS_DAYS:
            # FIX BUG #2: Gate - sample too small for inference
            print("\n" + "-" * 50)
            print("📊 RC% NORMALE vs CRISI (BLOCKED - SAMPLE TOO SMALL)")
            print("-" * 50)
            print(f"   ⛔ Crisis days: {crisis_days} (< {MIN_CRISIS_DAYS} minimum)")
            print(f"   Non è possibile fare inferenza statistica su normale vs crisi.")
            print(f"   I dati mostrati sotto sono SOLO ILLUSTRATIVI, non conclusivi.")
            print(f"   VIETATO usare per decisioni di portafoglio.")
            print("-" * 50)
        else:
            print("\n" + "-" * 50)
            print("📊 RC% NORMALE vs CRISI (come cambia in stress)")
            print("-" * 50)
        
        comparison = conditional_ccr.get('comparison')
        
        print(f"{'Ticker':<12} {'Normale':>10} {'Crisi':>10} {'Delta':>10} {'Note':>15}")
        print("-" * 50)
        for ticker in comparison.index:
            row = comparison.loc[ticker]
            normal = row['RC%_normal']
            crisis = row['RC%_crisis']
            delta = row['Delta']
            
            # Nota interpretativa
            if delta > 0.05:
                note = "⚠️ +rischio"
            elif delta < -0.05:
                note = "✓ -rischio"
            else:
                note = "≈ stabile"
            
            print(f"{ticker:<12} {normal:>10.1%} {crisis:>10.1%} {delta:>+10.1%} {note:>15}")
        
        print("-" * 50)
        sim_note = " (simulato)" if summary.get('simulated_crisis') else ""
        print(f"   Giorni normali: {summary.get('normal_days', 'N/A')}")
        print(f"   Giorni crisi: {summary.get('crisis_days', 'N/A')}{sim_note}")
    
    # === ASSET METRICS ===
    print("\n" + "=" * 70)
    print("INDIVIDUAL ASSET METRICS (annualized)")
    print("=" * 70)
    print(asset_metrics.to_string(float_format=lambda x: f"{x:.4f}"))
    
    # === CORRELATION ===
    # FIX BUG #1: Print both RAW and SHRUNK matrices when shrinkage is applied
    # IMPROVEMENT: Threshold abbassato a 1% - con 99% shrinkage la RAW è sempre necessaria
    # FIX PROBLEMA 3: When shrinkage > 50%, hide REG matrix (not informative)
    print("\n" + "=" * 70)
    
    if corr_raw is not None and shrinkage_intensity is not None and abs(shrinkage_intensity) > 0.01:
        # Shrinkage significativo
        if shrinkage_intensity >= 0.50:
            # HIGH SHRINKAGE (≥50%) - Show only RAW
            print("CORRELATION MATRIX (Observed, RAW)")
            print("=" * 70)
            print(f"\n⚠️ SHRINKAGE MOLTO ALTO ({shrinkage_intensity:.0%})")
            print("   La matrice REGULARIZED è quasi-identità (costruzione numerica).")
            print("   Usare SOLO la matrice RAW per interpretare relazioni tra asset.")
            print("   La REG serve esclusivamente per stabilizzare calcoli di rischio.")
            print(f"\n   ℹ️ Shrinkage intensity {shrinkage_intensity:.0%} → correlazioni regolarizzate")
            print("      non informative per diagnosi. Matrice RAW mostrata sotto.")
            print("      (REG usata internamente solo per calcoli numerici)")
            
            print("\n📊 CORRELAZIONI OSSERVATE (RAW, usate per diagnosi):")
            print("-" * 50)
            print(corr_raw.round(2).to_string())
        else:
            # MODERATE SHRINKAGE (1-50%) - Show both matrices
            print("CORRELATION MATRICES (RAW vs REGULARIZED)")
            print("=" * 70)
            print(f"\n⚠️ Shrinkage intensity: {shrinkage_intensity:.1%}")
            print("   RAW = osservata ma noisy con pochi dati/asset")
            print("   REGULARIZED = usata per risk calculations (Ledoit-Wolf)")
            
            print("\n📊 RAW CORRELATION (osservata, non usata per risk calc):")
            print("-" * 50)
            print(corr_raw.round(2).to_string())
            
            print("\n📊 REGULARIZED CORRELATION (usata per CCR, VaR, ecc.):")
            print("-" * 50)
            print(corr.round(2).to_string())
            
            print(f"\n   ⚠️ Con shrinkage {shrinkage_intensity:.0%} le correlazioni sono tirate verso identità.")
            print(f"   Le correlazioni RAW sono più informative per capire le relazioni reali.")
    else:
        # Shrinkage basso o assente - mostra solo una matrice
        print("CORRELATION MATRIX (osservata su tutto il periodo)")
        print("=" * 70)
        print(corr.round(2).to_string())
    
    # === CORRELATION SUMMARY (removed - already shown in CCR Condizionale) ===
    # Correlation behavior under stress is captured in CCR% normale vs crisi section above
    
    # === MONTE CARLO STRESS TEST (Simplified for Production v3.0) ===
    if stress_test:
        print("\n" + "=" * 70)
        print("🎲 MONTE CARLO STRESS TEST")
        print("=" * 70)
        
        base = stress_test.get('base', {})
        print("\n📊 SCENARIO NORMALE (distribuzione storica):")
        print("-" * 50)
        print(f"   Median return 1Y:     {base.get('median', 0):>12.1%}")
        print(f"   Worst case 5%:        {base.get('var_5', 0):>12.1%}")
        
        # Stress scenario: prioritize structural break if available, else high vol
        if 'structural_break' in stress_test:
            stress = stress_test['structural_break']
            scenario_name = "SCENARIO STRESS (crisi strutturale)"
        elif 'high_vol' in stress_test:
            stress = stress_test['high_vol']
            scenario_name = "SCENARIO STRESS (alta volatilità)"
        elif 'correlation_shift' in stress_test:
            stress = stress_test['correlation_shift']
            scenario_name = "SCENARIO STRESS (correlazioni elevate)"
        else:
            stress = None
            scenario_name = None
        
        if stress:
            print(f"\n⚠️  {scenario_name}:")
            print("-" * 50)
            print(f"   Median return 1Y:     {stress.get('median', base.get('median', 0)):>12.1%}")
            print(f"   Worst case 5%:        {stress.get('var_5', 0):>12.1%}")
        
        # Single takeaway
        base_var = base.get('var_5', 0)
        stress_var = stress.get('var_5', base_var) if stress else base_var
        delta = stress_var - base_var
        
        print("\n💡 TAKEAWAY:")
        if abs(delta) > 0.10:
            print(f"   Stress peggior caso: {stress_var:.0%} vs normale {base_var:.0%} (delta {abs(delta):.0%})")
        else:
            print(f"   Portfolio resiliente: stress vs normale <10% differenza")
    
    # === BENCHMARK COMPARISON ===
    if benchmark_comparison and benchmark_comparison.get('benchmarks'):
        print("\n" + "=" * 70)
        print("📊 BENCHMARK COMPARISON (vs alternative passive)")
        print("=" * 70)
        
        print(f"\n⚙️  METODOLOGIA: {benchmark_comparison.get('methodology', 'N/A')}")
        print(f"   {benchmark_comparison.get('note', '')}")
        
        # FIX PROBLEMA 4: Show Rule 8 parameters used
        if 'rule8_params' in benchmark_comparison:
            r8 = benchmark_comparison['rule8_params']
            print(f"\n   📋 Rule 8 Parameters:")
            print(f"      Defensive allocation: {r8['total_defensive_pct']:.1%}")
            print(f"      Has sector tilts: {r8['has_sector_tilts']}")
        
        # FIX INCONGRUENZA #6: Mostra tipo di confronto
        same_cat = benchmark_comparison.get('same_category_benchmarks', [])
        opp_cost = benchmark_comparison.get('opportunity_cost_benchmarks', [])
        
        for bench_key, bench_data in benchmark_comparison['benchmarks'].items():
            comp_type = bench_data.get('comparison_type', 'SAME_CATEGORY')
            type_tag = "🎯 SAME-CATEGORY" if comp_type == 'SAME_CATEGORY' else "📊 OPPORTUNITY-COST"
            
            print(f"\n   vs {bench_data['name']} [{type_tag}]:")
            print("-" * 50)
            
            # FIX PROBLEMA 4: Show Rule 8 application if relevant
            if bench_data.get('rule8_applied'):
                print(f"      ℹ️ Rule 8: {bench_data.get('rule8_reason', 'Applied')}")
            
            print(f"      Benchmark CAGR:    {bench_data['benchmark_cagr']:>8.2%}")
            print(f"      Benchmark Vol:     {bench_data['benchmark_vol']:>8.2%}")
            print(f"      Benchmark Sharpe:  {bench_data['benchmark_sharpe']:>8.2f}")
            print(f"      Benchmark MaxDD:   {bench_data['benchmark_max_dd']:>8.1%}")
            print(f"\n      Excess Return:     {bench_data['excess_return']:>+8.2%}")
            print(f"      Tracking Error:    {bench_data['tracking_error']:>8.2%}")
            print(f"      Information Ratio: {bench_data['information_ratio']:>8.2f}")
            print(f"      Beta:              {bench_data['beta']:>8.2f}")
            print(f"      Alpha (Jensen):    {bench_data['alpha']:>+8.2%}")
            print(f"\n      Verdict: {bench_data['verdict']}")
            print(f"      {bench_data['interpretation']}")
            
            # FIX PROBLEMA 4: Additional explanation for OPPORTUNITY_COST
            if comp_type == 'OPPORTUNITY_COST' and bench_data.get('rule8_applied'):
                print(f"\n      Nota: \"{bench_data['name']} rappresenta opportunity cost, non confronto diretto same-category.\"")
                print(f"            \"Portfolio ha caratteristiche che modificano il profilo di rischio.\"")
        
        print(f"\n   📋 VERDETTO COMPLESSIVO (solo same-category): {benchmark_comparison.get('overall_verdict', 'N/A')}")
        print(f"   {benchmark_comparison.get('overall_interpretation', '')}")
        
        # === PROXY BENCHMARK SUGGESTION (Production v3.0) ===
        overall_verdict = benchmark_comparison.get('overall_verdict', '')
        if overall_verdict == 'NO_SAME_CATEGORY_BENCHMARK':
            print("\n   💡 PROXY BENCHMARK SUGGESTION (non-official):")
            print("   Nessun benchmark same-category disponibile per questo portfolio.")
            print("   Considera come proxy di riferimento:")
            
            # Suggest based on portfolio characteristics
            benchmarks = benchmark_comparison.get('benchmarks', {})
            if benchmarks:
                # Find the most relevant benchmark
                for bench_key, bench_data in benchmarks.items():
                    comp_type = bench_data.get('comparison_type', 'OPPORTUNITY_COST')
                    if comp_type == 'OPPORTUNITY_COST':
                        bench_name = bench_data.get('name', 'N/A')
                        bench_beta = bench_data.get('beta', 0)
                        
                        if 'Global Equity' in bench_name or bench_name == 'VT':
                            print(f"      • {bench_name} (Global Equity) - opportunità costo base equity")
                        elif 'S&P 500' in bench_name or bench_name == 'SPY':
                            print(f"      • {bench_name} (US Large Cap) - beta {bench_beta:.2f} simile")
                        elif '60/40' in bench_name:
                            print(f"      • {bench_name} (Balanced) - bilanciato equity/bond")
                        break
            
            print("   Nota: Questi benchmark NON sono comparabili direttamente (strategie diverse),")
            print("         ma utili per valutare opportunity cost e posizionamento relativo.")


# ================================================================================
# PORTFOLIO CRITIQUE OUTPUT
# ================================================================================

def print_portfolio_critique(issues: list, regime_info: Dict[str, Any]) -> None:
    """
    Stampa analisi critica del portafoglio con identificazione tipo.
    REGIME-CONDITIONED: mostra analisi condizionata al regime di mercato.
    """
    
    regime = regime_info["regime"]
    portfolio_type = regime_info.get("portfolio_type", regime)
    confidence = regime_info["confidence"]
    composition = regime_info["composition"]
    trade_offs = regime_info.get("trade_offs", [])
    thresholds = regime_info["thresholds"]
    type_reason = regime_info.get("type_reason", "")
    market_regime = regime_info.get("market_regime", None)
    
    print("\n" + "=" * 70)
    # FIX #7: Renamed from "QUANT PORTFOLIO TYPE ANALYSIS" - la classificazione
    # usa regole euristiche, NON ML/clustering/PCA. "Quant" era misleading.
    print("🔍 PORTFOLIO TYPE ANALYSIS (Rule-Based Classification)")
    print("=" * 70)
    
    # === MARKET REGIME DETECTION (FASE 1 OBBLIGATORIA) ===
    if market_regime:
        print("\n📅 REGIME DI MERCATO RILEVATO:")
        print("-" * 50)
        primary_regime = market_regime.get("primary_regime", "NORMAL")
        
        regime_icons = {
            "INCLUDES_SYSTEMIC_CRISIS": "🔴",
            "INCLUDES_TIGHTENING": "🟠",
            "INCLUDES_STRESS": "🟡",
            "FULL_CYCLE": "🔵",
            "NORMAL": "🟢",
        }
        
        regime_names = {
            "INCLUDES_SYSTEMIC_CRISIS": "Include Crisi Sistemica",
            "INCLUDES_TIGHTENING": "Include Ciclo Tightening",
            "INCLUDES_STRESS": "Include Stress Settoriale",
            "FULL_CYCLE": "Multi-Ciclico (>10 anni)",
            "NORMAL": "Prevalentemente Normale",
        }
        
        icon = regime_icons.get(primary_regime, "⚪")
        name = regime_names.get(primary_regime, primary_regime)
        print(f"   {icon} Regime: {name}")
        print(f"   Periodo: {market_regime.get('period_years', 0):.1f} anni")
        
        # === CRISI RILEVATE CON TRIGGER QUANTITATIVI ===
        crisis_periods = market_regime.get("crisis_periods", [])
        if crisis_periods:
            print(f"\n   📉 CRISI SISTEMICHE RILEVATE (con evidenza quantitativa):")
            for crisis in crisis_periods:
                # Mostra trigger oggettivi per ogni crisi
                name_crisis = crisis.get("name", "N/A")
                start = crisis.get("start", "N/A")
                end = crisis.get("end", "N/A")
                trigger = crisis.get("trigger", "drawdown <-20% + vol spike")
                print(f"      • {name_crisis} ({start} → {end})")
                print(f"        Trigger: {trigger}")
        
        # === SOGLIE DUALI (NORMALE vs CRISI) ===
        if thresholds.get("regime_adjusted", False):
            print(f"\n   ⚙️ SOGLIE APPLICATE (Normale vs Regime Attuale):")
            print(f"      {'Metrica':<20} {'Normale':>12} {'Regime':>12}")
            print(f"      {'-'*44}")
            print(f"      {'Min Sharpe':<20} {'0.55':>12} {thresholds['min_sharpe']:>12.2f}")
            # Min Sortino omesso (correlato a Sharpe, riduce ripetizioni)
            print(f"      {'Max Drawdown':<20} {'-30%':>12} {thresholds['max_drawdown']:>12.0%}")
        
        # Nota istituzionale obbligatoria
        context = market_regime.get("regime_context", {})
        if context.get("institutional_note"):
            print(f"\n   📋 {context['institutional_note']}")
    
    # === FASE 3: DECOMPOSIZIONE TEMPORALE (OBBLIGATORIA) ===
    temporal_decomposition = regime_info.get("temporal_decomposition")
    robustness_score = regime_info.get("robustness_score")
    
    if temporal_decomposition:
        print("\n📊 FASE 3: DECOMPOSIZIONE TEMPORALE")
        print("-" * 50)
        
        # Performance durante crisi
        crisis_perf = temporal_decomposition.get("crisis_performance", [])
        if crisis_perf:
            print("\n   🔴 PERFORMANCE DURANTE CRISI:")
            for crisis in crisis_perf:
                print(f"      {crisis['name']} ({crisis['start']} → {crisis['end']}):")
                print(f"         Return: {crisis['return']:>8.1%}  Vol: {crisis['volatility']:>6.1%}  MaxDD: {crisis['max_drawdown']:>8.1%}")
        
        # Performance in expansion
        expansion = temporal_decomposition.get("expansion_performance", {})
        if expansion:
            print("\n   🟢 PERFORMANCE IN EXPANSION:")
            print(f"      Periodo expansion: {expansion.get('years', 0):.1f} anni")
            print(f"      CAGR expansion: {expansion.get('cagr', 0):>8.1%}")
            print(f"      Volatility: {expansion.get('volatility', 0):>8.1%}")
            # Sharpe omesso per ridurre ripetizioni (già in RISK-ADJUSTED METRICS)
        
        # Recovery analysis
        recovery = temporal_decomposition.get("recovery_analysis", [])
        if recovery:
            print("\n   🔄 RECOVERY ANALYSIS (Time-to-Recover):")
            for rec in recovery:
                months = rec.get('months_to_recover', 0)
                print(f"      Post-{rec['crisis']}: {months:.0f} mesi per recuperare")
                print(f"         (Recovery CAGR: {rec.get('recovery_cagr', 0):>6.1%})")
        
        # Rolling metrics - Production v3.0: Simplified to reduce noise
        rolling = temporal_decomposition.get("rolling_metrics", {})
        if rolling and ("sharpe_3y" in rolling or "sharpe_5y" in rolling):
            # Only show if extreme instability (min < 0)
            s3_min = rolling.get("sharpe_3y", {}).get('min', 0)
            s5_min = rolling.get("sharpe_5y", {}).get('min', 0)
            if s3_min < 0 or s5_min < 0:
                print("\n   📈 ROLLING METRICS (only if unstable):")
                if s3_min < 0:
                    s3 = rolling["sharpe_3y"]
                    print(f"      Sharpe 3Y: min={s3.get('min', 0):.2f} (instability detected)")
                if s5_min < 0:
                    s5 = rolling["sharpe_5y"]
                    print(f"      Sharpe 5Y: min={s5.get('min', 0):.2f} (instability detected)")
        
        # Worst periods
        worst = temporal_decomposition.get("worst_periods", {})
        if worst:
            print("\n   📉 WORST PERIODS:")
            if "worst_12m" in worst:
                w12 = worst["worst_12m"]
                print(f"      Worst 12M: {w12.get('return', 0):>8.1%}  (ended {w12.get('end_date', 'N/A')})")
            if "worst_24m" in worst:
                w24 = worst["worst_24m"]
                print(f"      Worst 24M: {w24.get('return', 0):>8.1%}  (ended {w24.get('end_date', 'N/A')})")
    
    # === ROBUSTNESS SCORE (strumento di ranking relativo) ===
    if robustness_score:
        print("\n🎯 ROBUSTNESS SCORE (comparative ranking tool):")
        print("-" * 50)
        score = robustness_score.get('score', 0)
        max_score = robustness_score.get('max_score', 100)
        pct = robustness_score.get('percentage', 0)
        
        # Barra visuale
        filled = int(pct / 5)
        bar = "█" * filled + "░" * (20 - filled)
        print(f"   [{bar}] {score}/{max_score} ({pct:.0f}%)")
        print(f"   ⚠️ NOTA: Score per confronto RELATIVO tra portafogli, non giudizio assoluto.")
        
        print(f"\n   Breakdown (criteri storici retrospettivi):")
        for item in robustness_score.get('breakdown', []):
            print(f"      • {item}")
    
    # === RESILIENCE vs EFFICIENCY (TWO-AXIS EVALUATION) ===
    resilience_efficiency = regime_info.get("resilience_efficiency")
    if resilience_efficiency:
        print("\n📐 RESILIENCE vs EFFICIENCY (Two-Axis Evaluation):")
        print("-" * 50)
        
        eff = resilience_efficiency['efficiency']
        res = resilience_efficiency['resilience']
        quadrant = resilience_efficiency['quadrant']
        icon = resilience_efficiency['quadrant_icon']
        
        # Barre visuali
        eff_bar = "█" * (eff['score'] // 5) + "░" * (20 - eff['score'] // 5)
        res_bar = "█" * (res['score'] // 5) + "░" * (20 - res['score'] // 5)
        
        print(f"   EFFICIENZA:  [{eff_bar}] {eff['score']}/100 ({eff['level']})")
        print(f"   RESILIENZA:  [{res_bar}] {res['score']}/100 ({res['level']})")
        print(f"\n   Quadrante: {icon} {quadrant}")
        print(f"   {resilience_efficiency['quadrant_description']}")
        
        print(f"\n   Trade-off:")
        print(f"   {resilience_efficiency['trade_off_note']}")
    
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
        # === NUOVE CATEGORIE (Framework Istituzionale) ===
        "STRUCTURED_MULTI_ASSET": "📦 STRUCTURED MULTI-ASSET",
        "CORE_SATELLITES_STATIC": "🎯 CORE + SATELLITES (Static)",
        "LOW_BETA_DIVERSIFIED": "🔒 LOW-BETA DIVERSIFIED",
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
        "TACTICAL": "Allocazione opportunistica (≥2 criteri tactical)",
        # === NUOVE CATEGORIE ===
        "STRUCTURED_MULTI_ASSET": "Allocazione strategica stabile, multi-asset",
        "CORE_SATELLITES_STATIC": "Core stabile + satellites definiti, buy&hold",
        "LOW_BETA_DIVERSIFIED": "Profilo conservativo strutturale, beta basso intenzionale",
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
    # Separa issues reali da quelli regime-adjusted (informativi)
    regime_adjusted_types = ["LOW_SHARPE_REGIME_ADJUSTED", "LOW_SORTINO_REGIME_ADJUSTED", 
                            "DRAWDOWN_REGIME_CONTEXT", "CORRELATION_INFO"]
    
    structural_issues = [i for i in issues if i["type"] not in regime_adjusted_types]
    regime_context_issues = [i for i in issues if i["type"] in regime_adjusted_types]
    
    if not structural_issues and not regime_context_issues:
        print("\n" + "=" * 70)
        print("✅ NESSUNA CRITICITÀ RILEVATA")
        print(f"   Portafoglio pienamente coerente con tipo {portfolio_type}")
        print("=" * 70)
    else:
        severity_order = {"🚨": 0, "⚠️": 1, "ℹ️": 2}
        issues_sorted = sorted(structural_issues, key=lambda x: severity_order.get(x["severity"], 3))
        
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
        
        # Mostra contesto regime separatamente
        if regime_context_issues:
            print("\n📊 CONTESTO REGIME DI MERCATO:")
            print("-" * 50)
            for issue in regime_context_issues:
                print(f"   • {issue['message']}")
    
    # === VERDETTO FINALE (BASATO SU EVIDENZA QUANTITATIVA) ===
    print("\n" + "=" * 70)
    
    # Solo criticità strutturali contano per il verdetto
    real_critical = [i for i in structural_issues if i["severity"] == "🚨" and i["type"] != "DATA_QUALITY"]
    real_warnings = [i for i in structural_issues if i["severity"] == "⚠️"]
    n_warnings = len(real_warnings)
    
    # Check se le criticità sono dovute a metriche depresse in crisi
    is_regime_crisis = (market_regime and 
                       market_regime.get("primary_regime") in ["INCLUDES_SYSTEMIC_CRISIS", "INCLUDES_TIGHTENING"])
    
    # FIX #7: Mostra sempre il count warnings nel verdetto per trasparenza
    warning_note = f" ({n_warnings} warnings)" if n_warnings > 0 else ""
    
    # Usa robustness_score se disponibile per verdict evidence-based
    if robustness_score:
        score = robustness_score.get('score', 0)
        verdict = robustness_score.get('verdict', 'COERENTE')
        verdict_detail = robustness_score.get('verdict_detail', '')
        
        if real_critical:
            print("📋 VERDETTO: ❌ DA RISTRUTTURARE")
            print(f"   Criticità severe non coerenti con tipo {portfolio_type}.")
            print("   Suggerimento: rivedi la composizione o considera un tipo diverso.")
        elif verdict == "ROBUSTO":
            print(f"📋 VERDETTO: ✅ {verdict} (Score: {score}/100)")
            print(f"   {verdict_detail}")
            print(f"   Evidenza: recovery veloce, rolling metrics consistenti, CAGR solido.")
        elif verdict == "COERENTE":
            print(f"📋 VERDETTO: ✅ {verdict} CON REGIME (Score: {score}/100)")
            print(f"   {verdict_detail}")
            print(f"   Metriche coerenti con crisi sistemiche incluse nel periodo.")
        elif verdict == "ACCETTABILE":
            print(f"📋 VERDETTO: ⚠️ {verdict} CON RISERVE (Score: {score}/100)")
            print(f"   {verdict_detail}")
        else:  # FRAGILE
            print(f"📋 VERDETTO: ❌ {verdict} (Score: {score}/100)")
            print(f"   {verdict_detail}")
    else:
        # Fallback se non c'è robustness_score
        if real_critical:
            print("📋 VERDETTO: ❌ DA RISTRUTTURARE")
            print(f"   Criticità severe non coerenti con tipo {portfolio_type}.")
        elif len(real_warnings) >= 4:
            # 4+ warnings = problema serio anche senza critical
            print("📋 VERDETTO: ⚠️ DA RIVEDERE")
            print(f"   {len(real_warnings)} aree problematiche identificate.")
            print(f"   Suggerimento: rivedere struttura per tipo {portfolio_type}.")
        elif len(real_warnings) >= 3 and not is_regime_crisis:
            print("📋 VERDETTO: ⚠️ APPROVATO CON RISERVE")
            print(f"   {len(real_warnings)} aree di miglioramento per tipo {portfolio_type}.")
        elif real_warnings:
            if is_regime_crisis:
                # FIX #7: Distingui tra pochi e molti warning anche in regime crisi
                if n_warnings >= 4:
                    print(f"📋 VERDETTO: ⚠️ COERENTE MA CON RISERVE{warning_note}")
                    print(f"   Portafoglio tipo {portfolio_type}, metriche influenzate da crisi.")
                    print(f"   ⚠️ {n_warnings} aree problematiche richiedono attenzione.")
                else:
                    print(f"📋 VERDETTO: ✅ COERENTE CON REGIME{warning_note}")
                    print(f"   Portafoglio coerente con tipo {portfolio_type}.")
                    print(f"   {n_warnings} warning non critici, metriche influenzate da crisi.")
            else:
                # FIX #7: Non "APPROVATO" con 2+ warnings - usa "CON TRADE-OFF"
                if n_warnings >= 2:
                    print(f"📋 VERDETTO: ✅ APPROVATO CON TRADE-OFF{warning_note}")
                    print(f"   Portafoglio coerente con tipo {portfolio_type}.")
                    print(f"   {n_warnings} trade-off documentati sopra.")
                else:
                    print(f"📋 VERDETTO: ✅ APPROVATO{warning_note}")
                    print(f"   Portafoglio coerente con tipo {portfolio_type}.")
                    if n_warnings == 1:
                        print(f"   1 warning minore - vedi sopra.")
        else:
            if is_regime_crisis:
                print("📋 VERDETTO: ✅ COERENTE CON REGIME")
                print(f"   Portafoglio coerente con tipo {portfolio_type}.")
            else:
                print("📋 VERDETTO: ✅ APPROVATO")
                print(f"   Portafoglio coerente con tipo {portfolio_type}.")
    
    # Overfitting note (moved to methodology section at top)
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

    # === 0. CLASSIFICAZIONE DETERMINISTICA ===
    print("\n🏷️  CLASSIFICAZIONE ETF (deterministica, no metriche)")
    print("-" * 50)
    for t, w in zip(tickers, weights):
        cls = classify_ticker(t)
        cat = cls.get("category", "UNKNOWN")
        risk = cls.get("risk_profile", "UNKNOWN")
        method = cls.get("method", "")
        print(f"   {t:<12} {w:>5.1%}  {cat:<20} risk={risk:<10} ({method})")
    
    # === 1. ESPOSIZIONE GEOGRAFICA REALE ===
    geo_exposure = calculate_geographic_exposure(tickers, weights)
    
    # Estrai unmapped tickers se presenti
    unmapped_tickers = geo_exposure.pop("_unmapped", [])
    inferred_tickers = geo_exposure.pop("_inferred", [])
    
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
    
    # Warning per ticker unmapped
    if unmapped_tickers:
        total_unmapped_weight = sum(w for _, w in unmapped_tickers)
        print(f"\n   ⚠️ GEOGRAPHIC DATA MISSING:")
        print(f"      {len(unmapped_tickers)} ticker ({total_unmapped_weight:.1%} del portfolio) usano DEFAULT_GEO.")
        print(f"      Ticker: {', '.join(t for t, _ in unmapped_tickers)}")
        print(f"      L'esposizione geografica per questi assume 60% USA (può essere impreciso).")
    
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
    
    # === WARNING CORRELAZIONE IN STRESS ===
    # FIX INCONGRUENZA #4: Non mostrare "stress warning" se le correlazioni sono stabili
    # Il warning è GENERALE solo se avg_corr alta E nessun dato sui regimi
    avg_corr = corr.values[np.triu_indices_from(corr.values, k=1)].mean() if corr is not None else 0.5
    
    # Controlla se abbiamo risultati delle correlazioni condizionate
    cond_corr_severity = None
    if 'conditional_correlations' in regime_info and regime_info['conditional_correlations']:
        cond_corr_severity = regime_info['conditional_correlations'].get('severity', None)
    
    # Mostra warning solo se: alta correlazione media AND (non abbiamo dati condizionali OR severity è HIGH)
    show_stress_warning = (
        avg_corr > 0.75 and 
        (cond_corr_severity is None or cond_corr_severity == 'HIGH')
    )
    
    if show_stress_warning:
        print("\n   ⚠️ CORRELATION RISK:")
        print(f"      Avg correlation = {avg_corr:.2f} - in crisi → 1.0")
        print(f"      Considera asset decorrelati: bonds, gold, vol strategies")
    elif avg_corr > 0.75 and cond_corr_severity == 'LOW':
        # Alta correlazione ma STABILE in stress - informativo, non warning
        print("\n   ℹ️ CORRELAZIONE STRUTTURALE:")
        print(f"      Correlazione alta ({avg_corr:.2f}) ma STABILE in stress")
        print(f"      No correlation breakdown significativo")
    
    # === 4. PUNTI DI FORZA STRUTTURALI ===
    strengths = identify_structural_strengths(composition, geo_exposure, function_exposure, metrics, weights)
    
    if strengths:
        print("\n\n💪 PUNTI DI FORZA STRUTTURALI:")
        print("-" * 50)
        for i, s in enumerate(strengths, 1):
            print(f"   {i}. {s}")
    
    # === 5. VERDETTO FINALE ===
    # Rule 7: Pre-determine if verdict is INCONCLUSIVE to prohibit portfolio actions
    gate_analysis = regime_info.get('gate_analysis', {})
    final_verdict_early = gate_analysis.get('final_verdict', '') if gate_analysis else ''
    prohibit_portfolio_actions = 'INCONCLUSIVE' in final_verdict_early
    
    # Pass prohibit_portfolio_actions to filter out portfolio restructuring recommendations
    bullets = generate_verdict_bullets(portfolio_type, strengths, issues, metrics, composition, prohibit_portfolio_actions)
    
    real_critical = [i for i in issues if i.get("severity") == "🚨" and i.get("type") != "DATA_QUALITY"]
    structural_issues = [i for i in issues if i.get("severity") == "⚠️"]
    false_div_structural = [w for w in false_div_warnings if w.get("severity") == "structural"]
    
    # Check regime di mercato
    market_regime = regime_info.get("market_regime", None)
    is_regime_crisis = (market_regime and 
                       market_regime.get("primary_regime") in ["INCLUDES_SYSTEMIC_CRISIS", "INCLUDES_TIGHTENING", "FULL_CYCLE"])
    
    # Filtra issues regime-adjusted (non sono criticità strutturali)
    regime_adjusted_types = ["LOW_SHARPE_REGIME_ADJUSTED", "LOW_SORTINO_REGIME_ADJUSTED", 
                            "DRAWDOWN_REGIME_CONTEXT", "CORRELATION_INFO"]
    real_structural_issues = [i for i in structural_issues if i.get("type") not in regime_adjusted_types]
    
    # Ottieni robustness_score se disponibile
    robustness_score = regime_info.get("robustness_score", None)
    score = robustness_score.get("score", 50) if robustness_score else 50
    
    # FIX INCONGRUENZA #8: Check if PROVISIONAL
    analysis_status = regime_info.get('analysis_status', 'VALIDATED')
    is_provisional = (analysis_status == 'PROVISIONAL')
    
    print("\n" + "=" * 70)
    
    # === NUOVO FRAMEWORK v4.1: Usa verdetti dal gate_analysis se disponibile ===
    risk_intent_analysis = regime_info.get('risk_intent_analysis', {})
    aggregate_verdict = risk_intent_analysis.get('aggregate_verdict', {})
    
    # Se abbiamo il gate system v4.1, usalo PRIORITARIAMENTE
    if gate_analysis and 'final_verdict' in gate_analysis:
        final_verdict = gate_analysis.get('final_verdict', '')
        verdict_message = gate_analysis.get('verdict_message', '')
        why_not_contradictory = gate_analysis.get('why_not_contradictory', '')
        
        if is_provisional:
            print("📋 VERDETTO FINALE: ⚠️ PROVISIONAL (data quality issues)")
            print("   Risultati da validare - problemi di integrità dati rilevati")
        elif final_verdict == 'INCONCLUSIVE_DATA_FAIL':
            print("📋 VERDETTO FINALE: ⛔ INCONCLUSIVE - Data Integrity")
            print("   Dati insufficienti per verdetto definitivo (>20% correlazioni NaN)")
            print("   → Azione consentita: solo miglioramento dati/metodologia")
            print("   🚫 Ristrutturazione portafoglio: VIETATA")
        elif final_verdict == 'INCONCLUSIVE_INTENT_DATA':
            print("📋 VERDETTO FINALE: ⛔ INCONCLUSIVE - Beta Window")
            print("   Beta window insufficiente per giudicare intent")
            print("   → Azione consentita: raccogliere più storico")
            print("   🚫 Ristrutturazione portafoglio: VIETATA")
        elif final_verdict == 'INTENT_FAIL_STRUCTURE_INCONCLUSIVE':
            print("📋 VERDETTO FINALE: ⚠️ INTENT FAIL CERTO - Struttura Inconclusa")
            print("   Intent FAIL è CERTO (beta calcolato su finestra sufficiente)")
            print("   Struttura NON valutabile per dati correlazione incompleti")
            print("   → Azione consentita: correggere intent O migliorare dati")
            print("   🚫 Ristrutturazione strutturale: VIETATA (struttura non valutata)")
        elif final_verdict == 'STRUCTURALLY_COHERENT_INTENT_MISMATCH':
            # INTENT MISMATCH - NON è fragilità strutturale
            print("📋 VERDETTO FINALE: ⚠️ INTENT MISALIGNED")
            print("   Struttura coerente ma obiettivo (Risk Intent) non allineato")
            print("   → Questo NON è un problema strutturale, verifica il Risk Intent dichiarato")
        elif final_verdict == 'STRUCTURALLY_FRAGILE':
            print("📋 VERDETTO FINALE: ❌ STRUCTURALLY FRAGILE")
            print("   Fragilità strutturale indipendente dal Risk Intent")
        elif final_verdict == 'STRUCTURALLY_COHERENT_INTENT_MATCH':
            print(f"📋 VERDETTO FINALE: ✅ STRUCTURALLY COHERENT (Score: {score}/100)")
            print("   Struttura robusta e allineata al Risk Intent dichiarato")
        else:
            print(f"📋 VERDETTO FINALE: ⚠️ {final_verdict}")
            print(f"   {verdict_message}")
        
        # Aggiungi spiegazione anti-contraddizione se disponibile
        if why_not_contradictory:
            print(f"\n   📌 {why_not_contradictory[:80]}...")
        
        # Rule 7: Suppress portfolio action recommendations if INCONCLUSIVE
        is_inconclusive = 'INCONCLUSIVE' in final_verdict
    
    # Fallback: usa risk_intent_analysis se disponibile
    elif aggregate_verdict and 'final_verdict_type' in aggregate_verdict:
        final_verdict_type = aggregate_verdict.get('final_verdict_type', '')
        intent_coherence = aggregate_verdict.get('intent_coherence', 'N/A')
        structural_status = aggregate_verdict.get('structural_coherence_status', 'N/A')
        
        if is_provisional:
            print("📋 VERDETTO FINALE: ⚠️ PROVISIONAL (data quality issues)")
            print("   Risultati da validare - problemi di integrità dati rilevati")
        elif final_verdict_type == 'INTENT_MISALIGNED':
            # NUOVO: Intent mismatch NON è fragilità strutturale
            print("📋 VERDETTO FINALE: ⚠️ INTENT MISALIGNED")
            print("   Struttura coerente ma obiettivo (Risk Intent) non allineato")
            print("   → Questo NON è un problema strutturale, verifica il Risk Intent dichiarato")
        elif final_verdict_type == 'STRUCTURALLY_FRAGILE':
            print("📋 VERDETTO FINALE: ❌ STRUCTURALLY FRAGILE")
            print("   Fragilità strutturale indipendente dal Risk Intent")
        elif final_verdict_type == 'STRUCTURALLY_COHERENT':
            print(f"📋 VERDETTO FINALE: ✅ STRUCTURALLY COHERENT (Score: {score}/100)")
            if intent_coherence == 'OK' and structural_status == 'OK':
                print("   Struttura robusta e allineata al Risk Intent dichiarato")
        else:
            print(f"📋 VERDETTO FINALE: ⚠️ ANALYSIS INCOMPLETE")
            print("   Dati insufficienti per valutazione completa")
    else:
        # Fallback: logica precedente
        if is_provisional:
            print("📋 VERDETTO FINALE: ⚠️ PROVISIONAL (data quality issues)")
            print("   Risultati da validare - problemi di integrità dati rilevati")
            print("   Vedi DATA QUALITY GATE per dettagli")
        elif real_critical or len(false_div_structural) >= 2:
            print("📋 VERDETTO FINALE: ❌ STRUCTURALLY FRAGILE")
            print("   Fragilità indipendente dal regime di mercato")
        elif real_structural_issues or false_div_structural:
            if is_regime_crisis:
                print(f"📋 VERDETTO FINALE: ✅ COERENTE CON REGIME (Score: {score}/100)")
                print("   Trade-off osservati sono fisiologici per il contesto")
            else:
                print(f"📋 VERDETTO FINALE: ✅ APPROVATO CON TRADE-OFF (Score: {score}/100)")
        elif len(strengths) >= 4:
            if is_regime_crisis and score >= 70:
                print(f"📋 VERDETTO FINALE: ✅ RESILIENTE ATTRAVERSO I CICLI (Score: {score}/100)")
                print("   Evidenza quantitativa: recovery veloce, rolling metrics stabili")
            elif is_regime_crisis:
                print(f"📋 VERDETTO FINALE: ✅ COERENTE CON REGIME (Score: {score}/100)")
                print("   Ha attraversato crisi sistemiche mantenendo struttura")
            else:
                print(f"📋 VERDETTO FINALE: ✅ APPROVATO - COSTRUZIONE ISTITUZIONALE (Score: {score}/100)")
        else:
            print(f"📋 VERDETTO FINALE: ✅ APPROVATO (Score: {score}/100)")
    
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
    """
    Genera grafici del portafoglio.
    
    Production v3.0: Rimossi grafici standard ridondanti (equity curve, drawdown, 
    distribution, rolling Sharpe) per ridurre noise. Questi sono disponibili in 
    qualsiasi tool base - il valore aggiunto deve essere in insights unici.
    
    FUTURE: Aggiungere grafici insight-driven:
    - Crisis attribution (regime decomposition)
    - CCR normale vs crisi comparison
    - Geographic/functional exposure breakdown
    """
    
    # Production v3.0: Standard charts commented out to reduce output noise
    # Users can enable via environment variable if needed for debugging
    if os.environ.get('PORTFOLIO_LEGACY_CHARTS', 'false').lower() == 'true':
        _plot_legacy_charts(equity, returns, save_path)
        return
    
    # Placeholder: no charts generated by default in production mode
    # Focus on console insights rather than generic visualizations
    if save_path:
        # Create a minimal info placeholder
        fig, ax = plt.subplots(1, 1, figsize=(10, 2))
        ax.text(0.5, 0.5, 
                '📊 Production Mode: Standard charts disabled\n'
                'Set PORTFOLIO_LEGACY_CHARTS=true for equity/drawdown/distribution charts\n'
                'Focus on console text insights for decision making',
                ha='center', va='center', fontsize=11, wrap=True)
        ax.axis('off')
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"\n📊 Placeholder grafico salvato: {save_path} (legacy charts disabled)")
        plt.close()


def _plot_legacy_charts(equity: pd.Series, returns: pd.Series, save_path: str = None) -> None:
    """Legacy standard charts (equity, drawdown, distribution, rolling Sharpe)."""
    
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
        print(f"\n📊 Grafico legacy salvato in: {save_path}")
    
    # Show plots based on config (default True), can be disabled via env var.
    if SHOW_PLOTS and os.environ.get('PORTFOLIO_SHOW_PLOT', 'true').lower() == 'true':
        plt.show()
    
    plt.close()


# ================================================================================
# INTEGRATION TEST OUTPUT
# ================================================================================

def print_integration_test_results(test_results: dict) -> None:
    """
    Print integration test results in a concise, user-facing format.
    """
    if not test_results:
        return

    print("\n" + "=" * 70)
    print("                     INTEGRATION TEST RESULTS")
    print("=" * 70)

    status = "PASS" if test_results.get("passed") else "FAIL"
    summary = test_results.get("summary") or f"exit_code={test_results.get('exit_code')}"
    duration = test_results.get("duration_seconds")

    print(f"Status: {status}")
    print(f"Summary: {summary}")
    if duration is not None:
        print(f"Duration: {duration:.2f}s")

    stdout_tail = test_results.get("stdout_tail") or []
    stderr_tail = test_results.get("stderr_tail") or []

    if stdout_tail:
        print("\nstdout (tail):")
        for line in stdout_tail:
            print(f"  {line}")

    if stderr_tail:
        print("\nstderr (tail):")
        for line in stderr_tail:
            print(f"  {line}")


# ================================================================================
# OPTIMIZATION OUTPUT
# ================================================================================

def print_optimization_analysis(opt_result: dict | None) -> None:
    """
    Stampa sintesi analisi di ottimizzazione Markowitz.
    """
    if not opt_result:
        return
    if isinstance(opt_result, dict) and opt_result.get("error"):
        print(f"\n[Optimization] skipped: {opt_result['error']}")
        return

    analysis = opt_result.get("current_vs_optimal", {}) if isinstance(opt_result, dict) else {}
    curr = analysis.get("current", {})
    curr_hist = opt_result.get("current_historical_metrics", {}) if isinstance(opt_result, dict) else {}
    eff = analysis.get("efficiency_analysis", {})
    suggestions = analysis.get("suggestions", [])
    key_portfolios = opt_result.get("key_portfolios", {}) if isinstance(opt_result, dict) else {}
    key_metrics = opt_result.get("key_portfolio_metrics", {}) if isinstance(opt_result, dict) else {}
    frontier_obj = opt_result.get("frontier") if isinstance(opt_result, dict) else None

    tickers = list(curr.get("weights", {}).keys()) if curr.get("weights") else None

    def _fmt_weights_all(res) -> str:
        if not res:
            return "-"
        try:
            w = res.weights
            if tickers and len(tickers) == len(w):
                pairs = list(zip(tickers, w))
            else:
                pairs = list(enumerate(w))
            return ", ".join(f"{t}:{p*100:.1f}%" for t, p in pairs)
        except Exception:
            return "-"

    print("\n" + "=" * 70)
    print("                  OPTIMIZATION ANALYSIS (Markowitz)")
    print("=" * 70)

    if curr:
        print(f"Current Sharpe (expected):   {curr.get('sharpe_ratio', 0):.3f}")
        print(f"Current Volatility (exp):    {curr.get('volatility', 0):.2%}")
        print(f"Current Exp. Return:         {curr.get('expected_return', 0):.2%}")
    if curr_hist:
        print(f"Current Sharpe (historical): {curr_hist.get('sharpe', 0):.3f}")
        print(f"Current CAGR (historical):   {curr_hist.get('cagr', 0):.2%}")
        print(f"Current Vol (historical):    {curr_hist.get('volatility', 0):.2%}")
        print(f"Current MaxDD (historical):  {curr_hist.get('max_drawdown', 0):.2%}")
    if eff:
        score = eff.get("efficiency_score")
        if score is not None:
            print(f"Efficiency score vs. optimal: {score:.1%}")
        if eff.get("sharpe_gap") is not None:
            print(f"Sharpe gap: {eff['sharpe_gap']:.3f}")
        if eff.get("volatility_gap") is not None:
            print(f"Volatility gap: {eff['volatility_gap']:.2%}")

    if suggestions or curr_hist:
        print("\nSuggestions:")
        for s in suggestions:
            print(f"- [Expected] {s}")
        # Historical comparison vs key max_sharpe
        curr_sh = curr_hist.get("sharpe") if curr_hist else None
        max_sh = key_metrics.get("max_sharpe", {}).get("sharpe")
        if curr_sh is not None and max_sh is not None:
            gap = max_sh - curr_sh
            if gap > 0.01:
                print(f"- [Historical] Sharpe migliorabile: {curr_sh:.2f} vs {max_sh:.2f} (gap {gap:.2f})")
            else:
                print(f"- [Historical] Sharpe già vicino al migliore: {curr_sh:.2f} vs {max_sh:.2f} (gap {gap:.2f})")

    if key_portfolios:
        print("\nKey portfolios (CAGR/Vol/MaxDD/Sharpe | weights):")
        for name, res in key_portfolios.items():
            if not res:
                continue
            km = key_metrics.get(name, {})
            cagr = km.get("cagr")
            vol = km.get("volatility")
            max_dd = km.get("max_drawdown")
            sharpe = km.get("sharpe")
            if cagr is not None:
                print(f"  {name:12s} CAGR={cagr:.2%}")
                print(
                    f"    Vol={vol:.2%} MaxDD={max_dd:.2%} Sharpe={sharpe:.2f} | {_fmt_weights_all(res)}"
                )
            else:
                print(f"  {name:12s} "
                      f"R={getattr(res, 'expected_return', getattr(res, 'exp_return', 0)):.2%} "
                      f"V={res.volatility:.2%} "
                      f"S={res.sharpe_ratio if hasattr(res, 'sharpe_ratio') else res.sharpe:.2f} "
                      f"| {_fmt_weights_all(res)}")

    if frontier_obj:
        try:
            succ = len(frontier_obj.successful_points)
            print(f"\nFrontier points: {succ} successful")
        except Exception:
            pass


# ================================================================================
# DATA QUALITY OUTPUT
# ================================================================================

def print_data_quality(data_quality: dict | None) -> None:
    """Stampa sintesi qualità dati (FX, staleness, survivorship, shrinkage)."""
    if not data_quality:
        return
    print("\n" + "=" * 70)
    print("                        DATA QUALITY")
    print("=" * 70)

    staleness = data_quality.get("staleness")
    if staleness:
        print(f"Staleness: {staleness}")

    fx = data_quality.get("fx", {})
    if fx:
        if fx.get("converted"):
            print(f"FX converted: {fx.get('converted')}")
        missing_all = (fx.get("missing", []) + fx.get("skipped", []))
        if missing_all:
            print(f"FX missing/skipped: {missing_all}")

    surv = data_quality.get("survivorship", {})
    if surv:
        label = surv.get("confidence_label")
        score = surv.get("confidence_score", 0)
        print(f"Survivorship confidence: {label} ({score:.0%})")
        if surv.get("warning_level") and surv.get("warning_level") != "LOW":
            print(f"Survivorship warning: {surv.get('message')}")

    shrink = data_quality.get("shrinkage")
    if shrink is not None:
        print(f"Correlation shrinkage intensity: {shrink:.1%}")


# ================================================================================
# SECTOR & HOLDINGS OUTPUT
# ================================================================================

def print_sector_and_holdings_report(
    sector_report: dict,
    holdings_report: dict,
    top_n: int = 10
) -> None:
    """
    Print sector allocation and top holdings per ETF.
    """
    print("\n" + "=" * 70)
    print("                SECTOR ALLOCATION & TOP HOLDINGS")
    print("=" * 70)

    # --- Sector allocation ---
    sectors = (sector_report or {}).get("sectors", {})
    missing_sectors = (sector_report or {}).get("missing", [])

    print("\n📌 SETTORI (allocazione portafoglio)")
    print("-" * 50)
    if sectors:
        for sector, pct in sectors.items():
            print(f"  {sector:<20} {pct:>6.1f}%")
    else:
        print("  Nessun dato settoriale disponibile.")
    if missing_sectors:
        print(f"  Missing sector data: {', '.join(missing_sectors)}")

    # --- Top holdings per ETF ---
    print("\n📌 TOP HOLDINGS (Top 10 per ETF)")
    print("-" * 50)
    by_ticker = (holdings_report or {}).get("by_ticker", {})
    missing_holdings = (holdings_report or {}).get("missing", [])

    if by_ticker:
        for ticker, holdings in by_ticker.items():
            print(f"\n  {ticker}")
            for h in holdings[:top_n]:
                name = h.get("name", "N/A")
                symbol = h.get("symbol")
                weight = h.get("weight_pct") or h.get("weight") or h.get("holding_percent") or h.get("percent")
                if weight is None:
                    weight = h.get("Holding Percent")
                weight = (weight or 0.0) * (100.0 if (weight or 0.0) <= 1 else 1.0)
                label = f"{symbol} - {name}" if symbol else name
                print(f"    {weight:>6.2f}%  {label}")
    else:
        print("  Nessun dato holdings disponibile.")

    if missing_holdings:
        print(f"\n  Missing holdings data: {', '.join(missing_holdings)}")


# ================================================================================
# AGGREGATED TOP HOLDINGS (weighted by portfolio weights)
# ================================================================================

def print_aggregated_holdings_report(
    holdings_report: dict,
    tickers: list,
    weights: list,
    top_n: int = 10,
) -> None:
    """
    Aggrega le top holdings a livello di portafoglio pesando le holdings
    per il peso dell'ETF/fondo nel portafoglio.
    """
    if not holdings_report or not tickers or not weights:
        return

    by_ticker = holdings_report.get("by_ticker", {})
    agg = {}

    def _weight_from_h(h):
        pct = h.get("weight_pct") or h.get("weight") or h.get("holding_percent") or h.get("percent") or h.get("Holding Percent")
        if pct is None:
            return 0.0
        try:
            pct = float(pct)
        except Exception:
            return 0.0
        return pct / 100 if pct > 1 else pct

    for t, w in zip(tickers, weights):
        for h in by_ticker.get(t, []):
            sym = h.get("symbol") or h.get("Symbol") or h.get("name") or "UNKNOWN"
            name = h.get("name") or h.get("Name") or sym
            hp = _weight_from_h(h)
            agg_key = sym
            agg.setdefault(agg_key, {"name": name, "symbol": sym, "weight": 0.0})
            agg[agg_key]["weight"] += w * hp

    top = sorted(agg.values(), key=lambda x: x["weight"], reverse=True)[:top_n]

    if not top:
        return

    print("\n" + "=" * 70)
    print("         TOP HOLDINGS AGGREGATE (pesate per peso ETF)")
    print("=" * 70)
    for row in top:
        print(f"  {row['symbol']:<12} {row['weight']*100:>6.2f}%  {row['name']}")
