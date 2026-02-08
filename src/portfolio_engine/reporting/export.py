"""
Export Module
=============
Funzioni per l'export dei dati in vari formati.

Include:
- export_to_csv: esportazione file CSV
- export_to_excel: esportazione Excel
- export_to_json: esportazione JSON
- export_ml_structured: export strutturato per ML (v3.1)
- export_charts: esportazione grafici
- generate_html_report: report HTML
- export_all_data: orchestrazione export
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import json
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List


# ================================================================================
# ML-READY STRUCTURED EXPORT (v3.1)
# ================================================================================

def export_ml_structured(
    output_dir: Path,
    metrics: dict,
    risk_contrib: pd.DataFrame,
    asset_metrics: pd.DataFrame,
    corr: pd.DataFrame,
    corr_raw: pd.DataFrame = None,
    verdict_info: dict = None,
    regime_info: dict = None
) -> str:
    """
    Export strutturato per ML ingestion e analisi quantitativa.
    
    Returns flattened metrics + nested structures for feature engineering.
    Target: Pandas DataFrame ready, no nested objects difficult to parse.
    
    Returns:
        str: Path to saved JSON file
    """
    
    structured = {
        "metadata": {
            "export_timestamp": datetime.now().isoformat(),
            "version": "3.1",
            "purpose": "ML_INGESTION_QUANT_ANALYSIS"
        },
        
        # Flat metrics for direct consumption
        "metrics_flat": {
            "cagr": float(metrics.get('cagr', 0)),
            "volatility": float(metrics.get('volatility', 0)),
            "sharpe": float(metrics.get('sharpe', 0)),
            "sortino": float(metrics.get('sortino', 0)),
            "calmar": float(metrics.get('calmar', 0)),
            "max_drawdown": float(metrics.get('max_drawdown', 0)),
            "avg_drawdown": float(metrics.get('avg_drawdown', 0)),
            "current_drawdown": float(metrics.get('current_drawdown', 0)),
            "beta": float(metrics.get('beta', 0)),
            "var_95_daily": float(metrics.get('var_95_daily', 0)),
            "cvar_95_daily": float(metrics.get('cvar_95_daily', 0)),
            "profit_factor": float(metrics.get('profit_factor', 0)),
            "gain_loss_ratio": float(metrics.get('gain_loss_ratio', 0)),
            "win_rate_daily": float(metrics.get('win_rate_daily', 0)),
            "win_rate_monthly": float(metrics.get('win_rate_monthly', 0))
        },
        
        # Bootstrap confidence intervals (if available)
        "confidence_intervals": {
            "cagr": {
                "lower": float(metrics.get('cagr_ci', {}).get('ci_lower', 0)),
                "upper": float(metrics.get('cagr_ci', {}).get('ci_upper', 0)),
                "se": float(metrics.get('cagr_ci', {}).get('se', 0))
            },
            "sharpe": {
                "lower": float(metrics.get('sharpe_ci', {}).get('ci_lower', 0)),
                "upper": float(metrics.get('sharpe_ci', {}).get('ci_upper', 0)),
                "se": float(metrics.get('sharpe_ci', {}).get('se', 0))
            },
            "max_dd": {
                "lower": float(metrics.get('max_dd_ci', {}).get('ci_lower', 0)),
                "upper": float(metrics.get('max_dd_ci', {}).get('ci_upper', 0))
            }
        },
        
        # Risk contribution breakdown
        "risk_contribution": {
            ticker: {
                "weight": float(row['Weight']),
                "mcr": float(row['MCR']),
                "ccr": float(row['CCR']),
                "ccr_pct": float(row['CCR%']),
                "risk_leverage": float(row['CCR%'] / row['Weight']) if row['Weight'] > 0 else 1.0
            }
            for ticker, row in risk_contrib.iterrows()
        },
        
        # Correlation matrices
        "correlations": {
            "regularized": corr.to_dict(),
            "raw": corr_raw.to_dict() if corr_raw is not None else None,
            "avg_correlation_reg": float(corr.values[np.triu_indices_from(corr.values, k=1)].mean()),
            "avg_correlation_raw": float(corr_raw.values[np.triu_indices_from(corr_raw.values, k=1)].mean()) if corr_raw is not None else None
        },
        
        # Asset-level metrics
        "assets": asset_metrics.to_dict('index'),
        
        # Verdict & classification
        "verdict": verdict_info if verdict_info else {},
        
        # Regime analysis
        "regime": regime_info if regime_info else {}
    }
    
    # Save to file
    filename = f"ml_structured_export_{get_timestamp()}.json"
    filepath = output_dir / filename
    
    with open(filepath, 'w') as f:
        json.dump(structured, f, indent=2, default=str)
    
    return str(filepath)

# ================================================================================
# UTILITY FUNCTIONS
# ================================================================================

def create_output_dir(output_dir: str = "./output") -> Path:
    """Crea directory di output se non esiste."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_timestamp() -> str:
    """Genera timestamp per i nomi dei file."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ================================================================================
# CSV EXPORT
# ================================================================================

def export_to_csv(
    output_dir: Path,
    equity: pd.Series,
    returns: pd.Series,
    metrics: dict,
    risk_contrib: pd.DataFrame,
    asset_metrics: pd.DataFrame,
    corr: pd.DataFrame,
    prices: pd.DataFrame
) -> list:
    """Esporta tutti i dati in formato CSV."""
    timestamp = get_timestamp()
    exported_files = []
    
    # 1. Equity curve
    equity_df = pd.DataFrame({'date': equity.index, 'equity': equity.values})
    equity_file = output_dir / f"equity_curve_{timestamp}.csv"
    equity_df.to_csv(equity_file, index=False)
    exported_files.append(equity_file)
    
    # 2. Daily returns
    returns_df = pd.DataFrame({'date': returns.index, 'return': returns.values})
    returns_file = output_dir / f"daily_returns_{timestamp}.csv"
    returns_df.to_csv(returns_file, index=False)
    exported_files.append(returns_file)
    
    # 3. Monthly returns
    monthly_ret = returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)
    monthly_df = pd.DataFrame({'date': monthly_ret.index, 'return': monthly_ret.values})
    monthly_file = output_dir / f"monthly_returns_{timestamp}.csv"
    monthly_df.to_csv(monthly_file, index=False)
    exported_files.append(monthly_file)
    
    # 4. Portfolio metrics
    metrics_df = pd.DataFrame([metrics]).T
    metrics_df.columns = ['value']
    metrics_file = output_dir / f"portfolio_metrics_{timestamp}.csv"
    metrics_df.to_csv(metrics_file)
    exported_files.append(metrics_file)
    
    # 5. Risk contribution
    risk_file = output_dir / f"risk_contribution_{timestamp}.csv"
    risk_contrib.to_csv(risk_file)
    exported_files.append(risk_file)
    
    # 6. Asset metrics
    asset_file = output_dir / f"asset_metrics_{timestamp}.csv"
    asset_metrics.to_csv(asset_file)
    exported_files.append(asset_file)
    
    # 7. Correlation matrix
    corr_file = output_dir / f"correlation_matrix_{timestamp}.csv"
    corr.to_csv(corr_file)
    exported_files.append(corr_file)
    
    # 8. Raw prices
    prices_file = output_dir / f"prices_{timestamp}.csv"
    prices.to_csv(prices_file)
    exported_files.append(prices_file)
    
    return exported_files


# ================================================================================
# EXCEL EXPORT
# ================================================================================

def export_to_excel(
    output_dir: Path,
    equity: pd.Series,
    returns: pd.Series,
    metrics: dict,
    risk_contrib: pd.DataFrame,
    asset_metrics: pd.DataFrame,
    corr: pd.DataFrame,
    prices: pd.DataFrame
) -> Path:
    """Esporta tutti i dati in un unico file Excel con più fogli."""
    timestamp = get_timestamp()
    excel_file = output_dir / f"portfolio_analysis_{timestamp}.xlsx"
    
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        # Summary metrics
        metrics_clean = {k: v for k, v in metrics.items() 
                        if not isinstance(v, (pd.Timestamp, datetime))}
        # Converti timestamp separatamente
        for k, v in metrics.items():
            if isinstance(v, (pd.Timestamp, datetime)):
                metrics_clean[k] = str(v.date()) if hasattr(v, 'date') else str(v)
        
        pd.DataFrame([metrics_clean]).T.to_excel(writer, sheet_name='Summary')
        
        # Equity curve
        pd.DataFrame({'equity': equity}).to_excel(writer, sheet_name='Equity')
        
        # Daily returns
        pd.DataFrame({'return': returns}).to_excel(writer, sheet_name='Daily Returns')
        
        # Monthly returns
        monthly_ret = returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)
        pd.DataFrame({'return': monthly_ret}).to_excel(writer, sheet_name='Monthly Returns')
        
        # Risk contribution
        risk_contrib.to_excel(writer, sheet_name='Risk Contribution')
        
        # Asset metrics
        asset_metrics.to_excel(writer, sheet_name='Asset Metrics')
        
        # Correlation
        corr.to_excel(writer, sheet_name='Correlation')
        
        # Prices
        prices.to_excel(writer, sheet_name='Prices')
    
    return excel_file


# ================================================================================
# JSON EXPORT
# ================================================================================

def export_to_json(
    output_dir: Path,
    equity: pd.Series,
    returns: pd.Series,
    metrics: dict,
    risk_contrib: pd.DataFrame,
    asset_metrics: pd.DataFrame,
    corr: pd.DataFrame,
    config: dict
) -> Path:
    """Esporta i dati in formato JSON."""
    timestamp = get_timestamp()
    json_file = output_dir / f"portfolio_analysis_{timestamp}.json"
    
    # Prepara dati per JSON
    export_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "version": "2.1",
            "config": {
                "tickers": config["tickers"],
                "weights": config["weights"],
                "risk_free": config["risk_free_annual"],
                "rebalance": config.get("rebalance"),
            }
        },
        "metrics": {},
        "equity_curve": {
            "dates": [d.isoformat() for d in equity.index],
            "values": equity.values.tolist()
        },
        "monthly_returns": {},
        "risk_contribution": risk_contrib.to_dict(),
        "asset_metrics": asset_metrics.to_dict(),
        "correlation": corr.to_dict()
    }
    
    # Converti metrics con gestione timestamp
    for k, v in metrics.items():
        if isinstance(v, (pd.Timestamp, datetime)):
            export_data["metrics"][k] = v.isoformat()
        elif isinstance(v, (np.floating, np.integer)):
            export_data["metrics"][k] = float(v)
        else:
            export_data["metrics"][k] = v
    
    # Monthly returns
    monthly_ret = returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)
    export_data["monthly_returns"] = {
        "dates": [d.isoformat() for d in monthly_ret.index],
        "values": monthly_ret.values.tolist()
    }
    
    with open(json_file, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    return json_file


# ================================================================================
# CHARTS EXPORT
# ================================================================================

def export_charts(
    output_dir: Path,
    equity: pd.Series,
    returns: pd.Series,
    chart_format: str = "png"
) -> list:
    """Esporta grafici come immagini."""
    timestamp = get_timestamp()
    exported_files = []
    
    # Usa backend non interattivo per export
    plt.switch_backend('Agg')
    
    # 1. Equity Curve
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(equity.index, equity.values, color='blue', linewidth=1.5)
    ax.set_title("Portfolio Equity Curve", fontsize=14)
    ax.set_ylabel("Value (base 1)")
    ax.grid(True, alpha=0.3)
    ax.axhline(y=1, color='gray', linestyle='--', alpha=0.5)
    equity_chart = output_dir / f"chart_equity_{timestamp}.{chart_format}"
    plt.savefig(equity_chart, dpi=150, bbox_inches='tight')
    plt.close()
    exported_files.append(equity_chart)
    
    # 2. Drawdown
    fig, ax = plt.subplots(figsize=(12, 6))
    dd = equity / equity.cummax() - 1
    ax.fill_between(dd.index, dd.values, 0, color='red', alpha=0.3)
    ax.plot(dd.index, dd.values, color='red', linewidth=1)
    ax.set_title("Drawdown", fontsize=14)
    ax.set_ylabel("Drawdown %")
    ax.grid(True, alpha=0.3)
    dd_chart = output_dir / f"chart_drawdown_{timestamp}.{chart_format}"
    plt.savefig(dd_chart, dpi=150, bbox_inches='tight')
    plt.close()
    exported_files.append(dd_chart)
    
    # 3. Returns Distribution
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(returns, bins=50, color='steelblue', alpha=0.7, edgecolor='black')
    ax.axvline(returns.mean(), color='green', linestyle='--', label=f'Mean: {returns.mean():.4f}')
    ax.axvline(returns.quantile(0.05), color='red', linestyle='--', label=f'VaR 5%: {returns.quantile(0.05):.4f}')
    ax.set_title("Daily Returns Distribution", fontsize=14)
    ax.legend()
    ax.grid(True, alpha=0.3)
    dist_chart = output_dir / f"chart_distribution_{timestamp}.{chart_format}"
    plt.savefig(dist_chart, dpi=150, bbox_inches='tight')
    plt.close()
    exported_files.append(dist_chart)
    
    # 4. Monthly Returns
    fig, ax = plt.subplots(figsize=(14, 6))
    monthly = returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)
    colors = ['green' if x > 0 else 'red' for x in monthly]
    ax.bar(monthly.index, monthly.values, color=colors, alpha=0.7, width=20)
    ax.set_title("Monthly Returns", fontsize=14)
    ax.set_ylabel("Return %")
    ax.axhline(y=0, color='black', linewidth=0.5)
    ax.grid(True, alpha=0.3)
    monthly_chart = output_dir / f"chart_monthly_{timestamp}.{chart_format}"
    plt.savefig(monthly_chart, dpi=150, bbox_inches='tight')
    plt.close()
    exported_files.append(monthly_chart)
    
    # 5. Dashboard completa
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    axes[0, 0].plot(equity.index, equity.values, color='blue', linewidth=1.5)
    axes[0, 0].set_title("Equity Curve")
    axes[0, 0].grid(True, alpha=0.3)
    
    axes[0, 1].fill_between(dd.index, dd.values, 0, color='red', alpha=0.3)
    axes[0, 1].set_title("Drawdown")
    axes[0, 1].grid(True, alpha=0.3)
    
    axes[1, 0].hist(returns, bins=50, color='steelblue', alpha=0.7)
    axes[1, 0].set_title("Returns Distribution")
    axes[1, 0].grid(True, alpha=0.3)
    
    axes[1, 1].bar(monthly.index, monthly.values, color=colors, alpha=0.7, width=20)
    axes[1, 1].set_title("Monthly Returns")
    axes[1, 1].axhline(y=0, color='black', linewidth=0.5)
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    dashboard_chart = output_dir / f"chart_dashboard_{timestamp}.{chart_format}"
    plt.savefig(dashboard_chart, dpi=150, bbox_inches='tight')
    plt.close()
    exported_files.append(dashboard_chart)
    
    # Ripristina backend interattivo
    try:
        plt.switch_backend('TkAgg')
    except Exception:
        pass  # Backend non disponibile, ignora
    
    return exported_files


# ================================================================================
# HTML REPORT
# ================================================================================

def generate_html_report(
    output_dir: Path,
    metrics: dict,
    risk_contrib: pd.DataFrame,
    asset_metrics: pd.DataFrame,
    corr: pd.DataFrame,
    config: dict,
    data_range: tuple
) -> Path:
    """Genera un report HTML completo."""
    timestamp = get_timestamp()
    html_file = output_dir / f"portfolio_report_{timestamp}.html"
    
    # CSS styling
    css = """
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: right; }
        th { background: #3498db; color: white; }
        tr:nth-child(even) { background: #f9f9f9; }
        tr:hover { background: #f1f1f1; }
        .metric-card { display: inline-block; background: #ecf0f1; padding: 15px 25px; margin: 10px; border-radius: 8px; min-width: 150px; }
        .metric-card .value { font-size: 24px; font-weight: bold; color: #2c3e50; }
        .metric-card .label { font-size: 12px; color: #7f8c8d; text-transform: uppercase; }
        .positive { color: #27ae60; }
        .negative { color: #e74c3c; }
        .section { margin: 30px 0; padding: 20px; background: #fafafa; border-radius: 8px; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #7f8c8d; font-size: 12px; }
    </style>
    """
    
    # Calcola valori per classi CSS
    roi_class = 'positive' if metrics['total_roi'] > 0 else 'negative'
    cagr_class = 'positive' if metrics['cagr'] > 0 else 'negative'
    
    # Genera HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Portfolio Analysis Report</title>
        {css}
    </head>
    <body>
        <div class="container">
            <h1>📊 Portfolio Analysis Report</h1>
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Data Range:</strong> {data_range[0]} to {data_range[1]}</p>
            
            <h2>📈 Performance Summary</h2>
            <div class="section">
                <div class="metric-card">
                    <div class="value {roi_class}">{metrics['total_roi']:.2%}</div>
                    <div class="label">Total ROI</div>
                </div>
                <div class="metric-card">
                    <div class="value {cagr_class}">{metrics['cagr']:.2%}</div>
                    <div class="label">CAGR</div>
                </div>
                <div class="metric-card">
                    <div class="value">{metrics['volatility']:.2%}</div>
                    <div class="label">Volatility</div>
                </div>
                <div class="metric-card">
                    <div class="value">{metrics['sharpe']:.2f}</div>
                    <div class="label">Sharpe Ratio</div>
                </div>
                <div class="metric-card">
                    <div class="value">{metrics['sortino']:.2f}</div>
                    <div class="label">Sortino Ratio</div>
                </div>
                <div class="metric-card">
                    <div class="value negative">{metrics['max_drawdown']:.2%}</div>
                    <div class="label">Max Drawdown</div>
                </div>
            </div>
            
            <h2>⚠️ Risk Metrics</h2>
            <div class="section">
                <div class="metric-card">
                    <div class="value negative">{metrics['var_95_daily']:.2%}</div>
                    <div class="label">VaR 95% (daily)</div>
                </div>
                <div class="metric-card">
                    <div class="value negative">{metrics['cvar_95_daily']:.2%}</div>
                    <div class="label">CVaR 95% (daily)</div>
                </div>
                <div class="metric-card">
                    <div class="value">{metrics['calmar']:.2f}</div>
                    <div class="label">Calmar Ratio</div>
                </div>
            </div>
            
            <h2>📊 Asset Allocation</h2>
            {asset_metrics.to_html(classes='', float_format=lambda x: f'{x:.4f}')}
            
            <h2>🎯 Risk Contribution</h2>
            {risk_contrib.to_html(classes='', float_format=lambda x: f'{x:.4f}')}
            
            <h2>🔗 Correlation Matrix</h2>
            {corr.round(2).to_html(classes='')}
            
            <h2>📅 Time Statistics</h2>
            <div class="section">
                <table>
                    <tr><th>Period</th><th>Up</th><th>Down</th><th>Win Rate</th><th>Best</th><th>Worst</th></tr>
                    <tr>
                        <td>Daily</td>
                        <td>{metrics['days_up']}</td>
                        <td>{metrics['days_down']}</td>
                        <td>{metrics['days_up']/metrics['days_total']:.1%}</td>
                        <td class="positive">{metrics['best_day']:.2%}</td>
                        <td class="negative">{metrics['worst_day']:.2%}</td>
                    </tr>
                    <tr>
                        <td>Monthly</td>
                        <td>{metrics['months_up']}</td>
                        <td>{metrics['months_down']}</td>
                        <td>{metrics['win_rate_monthly']:.1%}</td>
                        <td class="positive">{metrics['best_month']:.2%}</td>
                        <td class="negative">{metrics['worst_month']:.2%}</td>
                    </tr>
                    <tr>
                        <td>Yearly</td>
                        <td>{metrics['years_up']}</td>
                        <td>{metrics['years_down']}</td>
                        <td>{metrics['years_up']/metrics['years_total']:.1%}</td>
                        <td class="positive">{metrics['best_year']:.2%}</td>
                        <td class="negative">{metrics['worst_year']:.2%}</td>
                    </tr>
                </table>
            </div>
            
            <div class="footer">
                <p>Generated by Portfolio Analysis Tool v2.1 | Methodology: Simple Returns, Geometric CAGR</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return html_file


# ================================================================================
# ZIP ARCHIVE
# ================================================================================

def create_zip_archive(output_dir: Path, files: list, timestamp: str) -> Path:
    """
    Crea un archivio ZIP con tutti i file esportati.
    
    Args:
        output_dir: Directory di output
        files: Lista di Path dei file da includere
        timestamp: Timestamp per il nome del file
    
    Returns:
        Path del file ZIP creato
    """
    zip_filename = output_dir / f"portfolio_analysis_{timestamp}.zip"
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in files:
            if file_path.exists():
                # Aggiungi il file con solo il nome (non il path completo)
                zipf.write(file_path, file_path.name)
    
    return zip_filename


# ================================================================================
# MASTER EXPORT FUNCTION
# ================================================================================

def export_all_data(
    export_config: dict,
    equity: pd.Series,
    returns: pd.Series,
    metrics: dict,
    risk_contrib: pd.DataFrame,
    asset_metrics: pd.DataFrame,
    corr: pd.DataFrame,
    prices: pd.DataFrame,
    config: dict,
    data_range: tuple
) -> Optional[Path]:
    """
    Esporta tutti i dati nei formati richiesti.
    
    Returns:
        Path del file ZIP se creato, None altrimenti
    """
    
    if not export_config.get("enabled", False):
        print("\n📌 Export disabilitato. Per salvare i dati, imposta export.enabled = True")
        return None
    
    # Use data/ subfolder for exports (keep PDFs/PNGs in root output/)
    base_output = export_config.get("output_dir", "./output")
    output_dir = create_output_dir(f"{base_output}/data")
    formats = export_config.get("formats", [])
    timestamp = get_timestamp()
    
    print(f"\n{'='*70}")
    print("EXPORTING DATA")
    print("="*70)
    
    exported_files = []
    
    # CSV
    if "csv" in formats:
        csv_files = export_to_csv(output_dir, equity, returns, metrics, 
                                   risk_contrib, asset_metrics, corr, prices)
        exported_files.extend(csv_files)
        print(f"  ✓ CSV files exported ({len(csv_files)} files)")
    
    # Excel
    if "xlsx" in formats:
        try:
            excel_file = export_to_excel(output_dir, equity, returns, metrics,
                                         risk_contrib, asset_metrics, corr, prices)
            exported_files.append(excel_file)
            print(f"  ✓ Excel file exported: {excel_file.name}")
        except ImportError:
            print("  ⚠ Excel export requires openpyxl: pip install openpyxl")
        except Exception as e:
            print(f"  ⚠ Excel export failed: {e}")
    
    # JSON
    if "json" in formats:
        json_file = export_to_json(output_dir, equity, returns, metrics,
                                   risk_contrib, asset_metrics, corr, config)
        exported_files.append(json_file)
        print(f"  ✓ JSON file exported: {json_file.name}")
    
    # Charts
    if export_config.get("export_charts", False):
        chart_format = export_config.get("chart_format", "png")
        chart_files = export_charts(output_dir, equity, returns, chart_format)
        exported_files.extend(chart_files)
        print(f"  ✓ Charts exported ({len(chart_files)} files, format: {chart_format})")
    
    # HTML Report
    if export_config.get("export_html_report", False):
        html_file = generate_html_report(output_dir, metrics, risk_contrib,
                                         asset_metrics, corr, config, data_range)
        exported_files.append(html_file)
        print(f"  ✓ HTML report exported: {html_file.name}")
    
    # Crea ZIP se richiesto
    zip_file = None
    if export_config.get("create_zip", True) and exported_files:
        zip_file = create_zip_archive(output_dir, exported_files, timestamp)
        print(f"\n  📦 ZIP archive created: {zip_file.name}")
        
        # Elimina file singoli se richiesto
        if export_config.get("delete_files_after_zip", True):
            for f in exported_files:
                try:
                    f.unlink()
                except Exception:
                    pass
            print(f"  🗑️  Individual files removed (kept only ZIP)")
    
    print(f"\n  📁 Output directory: {output_dir.absolute()}")
    if zip_file:
        print(f"  📦 Archive: {zip_file.name}")
        zip_size_mb = zip_file.stat().st_size / (1024 * 1024)
        print(f"  💾 Size: {zip_size_mb:.2f} MB")
    else:
        print(f"  📄 Total files exported: {len(exported_files)}")
    
    return zip_file


# ================================================================================
# PDF EXPORT
# ================================================================================

def generate_pdf_report(
    output_text: str,
    output_path: str = "output/analisi.pdf",
    chart_path: str = None
) -> Path:
    """
    Genera un report PDF dall'output testuale dell'analisi.
    
    Args:
        output_text: Testo completo dell'analisi (catturato da stdout)
        output_path: Percorso del file PDF di output
        chart_path: Percorso opzionale del grafico da includere
    
    Returns:
        Path del file PDF generato
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Preformatted
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib import colors
    
    # Crea directory output se non esiste
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Setup documento
    doc = SimpleDocTemplate(
        str(output_file),
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )
    
    # Stili
    styles = getSampleStyleSheet()
    
    # Stile per il codice/output monospace
    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=6.5,
        leading=8,
        leftIndent=0,
        rightIndent=0,
        spaceBefore=0,
        spaceAfter=0,
        textColor=colors.black,
        backColor=colors.Color(0.97, 0.97, 0.97),
    )
    
    # Stile titolo
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=20,
        textColor=colors.darkblue,
    )
    
    # Contenuto
    story = []
    
    # Titolo
    story.append(Paragraph("📊 Portfolio Analysis Report", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 0.5*cm))
    
    # Aggiungi grafico se disponibile
    if chart_path and Path(chart_path).exists():
        try:
            img = Image(chart_path, width=18*cm, height=12*cm)
            story.append(img)
            story.append(Spacer(1, 0.5*cm))
        except Exception as e:
            story.append(Paragraph(f"[Chart not available: {e}]", styles['Normal']))
    
    # Processa l'output testuale
    # Rimuovi caratteri emoji problematici per PDF e converti in testo semplice
    clean_text = output_text
    
    # Mapping emoji → testo
    emoji_map = {
        '📋': '[INFO]',
        '📊': '[CHART]',
        '📈': '[UP]',
        '📉': '[DOWN]',
        '⚠️': '[WARN]',
        '⛔': '[BLOCK]',
        '✅': '[OK]',
        '❌': '[FAIL]',
        '🚨': '[ALERT]',
        '💪': '[STRONG]',
        '🎯': '[TARGET]',
        '🔍': '[SEARCH]',
        '🏛️': '[INST]',
        '🌍': '[WORLD]',
        '🇺🇸': '[US]',
        '🇪🇺': '[EU]',
        '🇯🇵': '[JP]',
        '🇬🇧': '[UK]',
        '🌏': '[ASIA]',
        '🌐': '[GLOBAL]',
        '⚙️': '[CONF]',
        '🔴': '[RED]',
        '🟢': '[GREEN]',
        '🟠': '[ORANGE]',
        '🔄': '[CYCLE]',
        '🎲': '[RANDOM]',
        '🏷️': '[TAG]',
        '📌': '[PIN]',
        '📅': '[DATE]',
        '📐': '[MEASURE]',
        '🔬': '[RESEARCH]',
        '💾': '[SAVE]',
        '📁': '[FOLDER]',
        '📦': '[PACKAGE]',
        '🗑️': '[DELETE]',
        '🛡️': '[SHIELD]',
        '🤖': '[AI]',
        '🌟': '[STAR]',
        '═': '=',
        '─': '-',
        '▓': '#',
        '░': '.',
        '█': '#',
        'ℹ️': '[i]',
        '🚫': '[X]',
    }
    
    for emoji, text in emoji_map.items():
        clean_text = clean_text.replace(emoji, text)
    
    # Dividi in sezioni (per evitare pagine troppo lunghe)
    lines = clean_text.split('\n')
    
    # Raggruppa linee in blocchi
    current_block = []
    for line in lines:
        current_block.append(line)
        
        # Ogni ~60 linee, crea un nuovo paragrafo
        if len(current_block) >= 60:
            block_text = '\n'.join(current_block)
            # Usa Preformatted per mantenere il formato
            story.append(Preformatted(block_text, code_style))
            story.append(Spacer(1, 0.2*cm))
            current_block = []
    
    # Aggiungi blocco rimanente
    if current_block:
        block_text = '\n'.join(current_block)
        story.append(Preformatted(block_text, code_style))
    
    # Genera PDF
    doc.build(story)
    
    return output_file

