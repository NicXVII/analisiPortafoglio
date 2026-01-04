# Work Report - Correzioni Progetto analisiPortafogli

**Data**: 3 Gennaio 2026

---

## VERSIONE 2.2 - Architettura Modulare

### Refactoring Struttura Codebase

Il progetto è stato completamente modularizzato per migliorare manutenibilità e leggibilità.

---

## Architettura dei Moduli

```
analisiPortafogli/
├── main.py           # Entry point (orchestrazione)
├── config.py         # Configurazione portafoglio
├── metrics.py        # Calcolo metriche
├── taxonomy.py       # Classificazione ETF
├── analysis.py       # Portfolio type detection
├── output.py         # Funzioni di output/stampa
├── export.py         # Export dati (CSV, Excel, JSON)
├── data.py           # Download e gestione dati
├── main_old.py       # Backup versione monolitica
├── requirements.txt  # Dipendenze
└── output/           # File generati
```

---

## Moduli e Responsabilità

### 1. `config.py` - Configurazione
Definisce il portafoglio da analizzare:
- Lista tickers
- Pesi percentuali
- Periodo di analisi
- Opzioni export

### 2. `metrics.py` - Calcolo Metriche (330+ righe)
**Funzioni principali**:
- `calculate_simple_returns()` - Simple returns per aggregazione
- `calculate_cagr()` / `calculate_cagr_correct()` - CAGR geometrico
- `calculate_sharpe_ratio()` - Risk-adjusted return
- `calculate_sortino_ratio()` - Downside risk-adjusted
- `calculate_var_cvar()` - Value at Risk e Expected Shortfall
- `calculate_max_drawdown()` - Drawdown con date
- `calculate_risk_contribution()` - MCR/CCR contribution
- `calculate_all_metrics()` - Calcolo completo

### 3. `taxonomy.py` - Classificazione ETF (400+ righe)
**Dati**:
- `CORE_GLOBAL_ETF` - VT, VWCE, IWDA...
- `CORE_REGIONAL_ETF` - IVV, VOO, EWJ, VGK...
- `EMERGING_ETF` - EEM, VWO, IEEM...
- `SMALL_CAP_ETF`, `REIT_ETF`, `FACTOR_ETF`, `SECTOR_ETF`
- `THEMATIC_PURE_ETF` - URA, ARKK, SRVR...
- `BOND_ETF`, `GOLD_COMMODITY_ETF`, `DIVIDEND_INCOME_ETF`
- `GEO_EXPOSURE` - Mapping esposizione geografica per ETF
- `ASSET_FUNCTION` - Funzione economica per ETF

**Funzioni**:
- `get_asset_function()` - Classifica ticker per funzione
- `calculate_geographic_exposure()` - Esposizione geografica effettiva
- `analyze_function_exposure()` - Esposizione per funzione economica
- `classify_ticker()` - Classificazione granulare ticker

### 4. `analysis.py` - Analisi Portafoglio (900+ righe)
**Funzioni principali**:
- `detect_portfolio_type()` - Identificazione 10 tipi portafoglio:
  1. INCOME_YIELD - Dividend ETF focus
  2. DEFENSIVE - Capital preservation
  3. BALANCED - Multi-asset 60/40
  4. RISK_PARITY - Risk contribution equilibrata
  5. EQUITY_MULTI_BLOCK - Pesi equilibrati
  6. EQUITY_CORE_DRIVEN - World index >50%
  7. BARBELL_THEMATIC - Core + satellite
  8. EQUITY_GROWTH_CORE - Singolo asset >45%
  9. EQUITY_GROWTH_DIVERSIFIED - Multi-core
  10. TACTICAL - Pattern non chiaro

- `get_type_thresholds()` - Soglie per tipo portafoglio
- `analyze_portfolio_issues()` - Analisi criticità type-aware
- `detect_false_diversification()` - Falsa diversificazione
- `identify_structural_strengths()` - Punti di forza
- `generate_verdict_bullets()` - Verdetto finale

### 5. `output.py` - Output/Stampa (530+ righe)
**Funzioni**:
- `print_summary()` - Report metriche completo
- `print_portfolio_critique()` - Analisi criticità
- `print_senior_architect_analysis()` - Analisi istituzionale
- `plot_results()` - Grafici (equity, drawdown, distribution, rolling Sharpe)

### 6. `export.py` - Export Dati (480+ righe)
**Funzioni**:
- `export_to_csv()` - Multiple file CSV
- `export_to_excel()` - File Excel multi-sheet
- `export_to_json()` - JSON strutturato
- `export_charts()` - PNG/PDF grafici
- `generate_html_report()` - Report HTML completo
- `export_all_data()` - Orchestrazione export
- `create_zip_archive()` - Archivio ZIP

### 7. `data.py` - Download e Dati (160+ righe)
**Funzioni**:
- `download_data()` - Download da Yahoo Finance
- `calculate_start_date()` - Calcolo data inizio
- `simulate_portfolio_correct()` - Simulazione portafoglio
- `simulate_rebalanced_portfolio()` - Con ribilanciamento
- `calculate_simple_returns()`, `calculate_log_returns()`

### 8. `main.py` - Entry Point (200 righe)
**Funzione**:
- `analyze_portfolio()` - Orchestrazione completa:
  1. Validazione config
  2. Download dati
  3. Simulazione portafoglio
  4. Calcolo metriche
  5. Analisi criticità
  6. Output stampa
  7. Export dati
  8. Generazione grafici

---

## Dipendenze tra Moduli

```
main.py
  ├── config.py
  ├── metrics.py
  ├── data.py
  ├── analysis.py ──────┬── taxonomy.py
  ├── output.py ────────┤
  └── export.py         │
                        └── metrics.py (funzioni comuni)
```

---

## Vantaggi Architettura Modulare

1. **Manutenibilità**: Ogni modulo ha responsabilità chiara
2. **Testabilità**: Funzioni isolate facili da testare
3. **Riusabilità**: Moduli importabili in altri progetti
4. **Leggibilità**: File di ~200-500 righe invece di ~3000
5. **Sviluppo parallelo**: Team può lavorare su moduli diversi

---

## VERSIONE 2.0 - Correzioni Metodologiche (Audit Quant)

### Nuovo file: `main_v2.py`

Ho creato una versione completamente rivista dello script con metodologie quantitative professionali.

---

## 1. ✅ CAGR Calcolato Correttamente

**Problema v1**: Il CAGR era calcolato come `exp(mean(log_returns) * 252) - 1`, che è un'approssimazione che assume rendimenti IID e sovrastima sistematicamente in periodi di alta volatilità.

**Soluzione v2**:
```python
def calculate_cagr_correct(equity: pd.Series, periods_per_year: int = 252) -> float:
    total_return = equity.iloc[-1] / equity.iloc[0]
    n_years = len(equity) / periods_per_year
    cagr = total_return ** (1 / n_years) - 1
    return float(cagr)
```

**Formula corretta**: $CAGR = \left(\frac{V_{final}}{V_{initial}}\right)^{\frac{1}{years}} - 1$

---

## 2. ✅ Aggregazione Portafoglio con SIMPLE Returns

**Problema v1**: I log-returns venivano moltiplicati per i pesi, ma i log-returns NON sono additivi per portfolio pesati.

$$R_{port}^{log} \neq \sum w_i \cdot r_i^{log}$$

**Soluzione v2**: Uso di SIMPLE returns (percentage returns) che sono correttamente additivi:

```python
def calculate_simple_returns(prices: pd.DataFrame) -> pd.DataFrame:
    return prices.pct_change().dropna()

# Portfolio return corretto
port_ret = (simple_ret * weights).sum(axis=1)
```

**Impatto**: Tutte le metriche ora riflettono la realtà matematica del portafoglio.

---

## 3. ✅ Sortino Ratio con Target Downside Deviation Corretta

**Problema v1**: Sortino calcolato come `std(negative_returns)` che è concettualmente errato.

**Soluzione v2**: Implementazione corretta con TDD (Target Downside Deviation):

```python
def calculate_sortino_ratio(returns, risk_free, target_return=0.0, periods=252):
    # Calcola downside deviation rispetto al target
    downside = np.minimum(returns - target_daily, 0)
    downside_var = (downside ** 2).mean()
    tdd = np.sqrt(downside_var) * np.sqrt(periods)
    
    return (ann_return - risk_free) / tdd
```

**Formula corretta**: $TDD = \sqrt{\frac{1}{n}\sum_{i=1}^{n} \min(0, R_i - T)^2}$

---

## 4. ✅ Aggiunta VaR e CVaR (Expected Shortfall)

**Problema v1**: Nessuna metrica di tail risk.

**Soluzione v2**: Implementato Value at Risk e Conditional VaR:

```python
def calculate_var_cvar(returns, confidence=0.95, periods=252):
    # VaR storico
    var_historical = returns.quantile(1 - confidence)
    
    # CVaR (Expected Shortfall) - media delle perdite oltre il VaR
    cvar = returns[returns <= var_historical].mean()
    
    return var_historical, cvar
```

**Output aggiunto**:
```
⚠️  TAIL RISK (95% confidence)
--------------------------------------------------
  VaR (daily):                  -1.23%
  CVaR (daily):                 -1.93%
  VaR (annualized):            -19.45%
  CVaR (annualized):           -30.67%
```

---

## 5. ✅ Risk Contribution che Somma a 100%

**Problema v1**: Le percentuali di risk contribution non sommavano correttamente.

**Soluzione v2**: Calcolo esplicito di MCR, CCR e CCR%:

```python
def calculate_risk_contribution_correct(returns, weights, tickers, periods=252):
    # Marginal Contribution to Risk
    mcr = (cov.values @ w).flatten() / port_vol
    
    # Component Contribution to Risk
    ccr = weights * mcr
    
    # Percentuale (somma a 1)
    ccr_pct = ccr / port_vol
```

**Output migliorato**:
```
RISK CONTRIBUTION (Component Contribution to Risk)
Ticker         Weight        MCR        CCR       CCR%
VWCE.DE        40.00%     0.1802     0.0721     54.70%
...
TOTAL         100.00%                0.1317    100.00%  ← Somma verificata
```

---

## 6. ✅ Fix Warning Deprecation

**Problema v1**: Warning pandas/numpy:
- `'M' is deprecated, use 'ME'`
- `array concatenation with empty entries`
- `Conversion of array with ndim > 0 to scalar`

**Soluzioni v2**:
```python
# 1. Frequenza pandas aggiornata
rebalance_freq = "ME"  # invece di "M"

# 2. Soppressione warning non critici
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

# 3. Estrazione scalare esplicita
port_var = float((w.T @ cov.values @ w).item())  # .item() invece di float()
```

---

## 7. ✅ Grafici Avanzati con Rolling Metrics

**Aggiunto**:
- Distribuzione rendimenti giornalieri con VaR
- Rendimenti mensili (bar chart)
- Rolling Sharpe Ratio (1 anno)
- Rolling Volatility (1 anno)

---

## 8. ✅ Date di Max Drawdown

**Aggiunto**: Identificazione delle date di picco e valle del max drawdown:

```python
def calculate_max_drawdown(equity):
    trough_idx = drawdown.idxmin()
    peak_idx = equity.loc[:trough_idx].idxmax()
    return max_dd, peak_idx, trough_idx
```

**Output**:
```
Max Drawdown:                -11.16%
  Peak Date:              2025-03-24
  Trough Date:            2025-04-07
```

---

## CONFRONTO v1 vs v2

| Metrica | v1 (errato) | v2 (corretto) | Differenza |
|---------|-------------|---------------|------------|
| CAGR | 26.26% | 25.84% | -0.42% |
| Sharpe | 1.61 | 1.67 | +0.06 |
| Sortino | 2.33 | 2.81 | +0.48 |
| Max DD | -11.22% | -11.16% | +0.06% |
| VaR 95% | N/A | -1.23% daily | ✅ Nuovo |
| CVaR 95% | N/A | -1.93% daily | ✅ Nuovo |
| Risk Contrib Sum | ~100% | 100.00% | ✅ Verificato |

---

## File Creati/Modificati

| File | Azione |
|------|--------|
| `main_v2.py` | **NUOVO** - Versione corretta |
| `main.py` | Invariato (per confronto) |
| `workReport.md` | Aggiornato con documentazione v2 |

---

## Raccomandazioni Residue

1. **Benchmark**: Aggiungere confronto vs MSCI World
2. **Currency Risk**: Modellare esposizione EUR/GBP
3. **Stress Test**: Aggiungere scenari 2008, 2020, 2022
4. **Transaction Costs**: Modellare costi di ribilanciamento

---

## Versione 1.0 - Correzioni Iniziali (archivio)

### Criticità Corrette

#### 1. ✅ Array TICKERS e WEIGHTS vuoti
**Problema**: Gli array erano vuoti, causando crash immediato con `ValueError: Somma pesi nulla`.

**Soluzione**: Aggiunto un portafoglio di esempio con 3 ETF:
- VWCE.DE (70%) - Vanguard FTSE All-World
- AGGH.L (20%) - iShares Core Global Aggregate Bond  
- SGLD.L (10%) - Invesco Physical Gold

---

#### 2. ✅ File howTo.md conteneva codice invece di documentazione
**Problema**: Il file era un duplicato di main.py invece di contenere istruzioni.

**Soluzione**: Riscritto completamente come documentazione.

---

#### 3. ✅ Bug critico nel ribilanciamento (righe 78-94)
**Problema**: La variabile `port_eq` era inizializzata vuota, quindi `port_eq.loc[last_date]` restituiva `NaN`.

**Soluzione**: Riscritta completamente la funzione di ribilanciamento.

---

#### 4. ✅ Gestione errata per singolo ticker
**Problema**: `yf.download()` restituisce strutture dati diverse per 1 vs N ticker.

**Soluzione**: Creata funzione `download_data()` che gestisce entrambi i casi.

---

#### 5. ✅ Mancava requirements.txt
**Soluzione**: Creato con:
```
numpy>=1.21.0
pandas>=1.3.0
yfinance>=0.2.0
matplotlib>=3.4.0
scipy>=1.7.0
```
