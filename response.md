# Portfolio Analysis Engine v3.0 - Design Specification
## Documento di Specifica per Classificazione, Qualità Dati e Verdetto

---

# SEZIONE 0: RISK INTENT DECLARATION (Obbligatoria)

## 0.1 Definizione

**Risk Intent** = dichiarazione esplicita del livello di rischio che il portafoglio *intende* assumere.

**REGOLA FONDAMENTALE**: Ogni analisi DEVE iniziare con la dichiarazione del Risk Intent. Senza questa, il motore non può distinguere:
- Scelta consapevole di alto rischio → da valutare vs benchmark aggressivo
- Errore di design → da segnalare come fragilità strutturale

## 0.2 Livelli di Risk Intent

| Level | Beta Target | Benchmark Naturale | Max DD Atteso | Vol Attesa |
|-------|-------------|-------------------|---------------|------------|
| CONSERVATIVE | 0.3 - 0.5 | 40/60 (equity/bond) | -15% | 6-10% |
| MODERATE | 0.5 - 0.8 | 60/40 | -25% | 10-14% |
| GROWTH | 0.8 - 1.0 | 80/20 o VT | -35% | 14-18% |
| AGGRESSIVE | 1.0 - 1.3 | VT o ACWI | -45% | 18-22% |
| HIGH-BETA | > 1.3 | Small Value / EM | -55% | > 22% |

## 0.3 Regole di Coerenza

```
RULE: Se Risk Intent non dichiarato:
  → Default = GROWTH (beta ~1.0)
  → Warning: "Risk Intent non specificato - assunto GROWTH"

RULE: Se Risk Intent dichiarato:
  → Tutti i giudizi su DD/Vol normalizzati vs benchmark di categoria
  → "Fragilità" = SOLO se performance peggiore del benchmark coerente
```

## 0.4 Input Richiesto

```python
CONFIG = {
    'risk_intent': 'AGGRESSIVE',  # CONSERVATIVE | MODERATE | GROWTH | AGGRESSIVE | HIGH-BETA
    # ... resto config
}
```

---

# SEZIONE 1: TAXONOMY (Tassonomia Portafogli)

## 1.1 Definizioni Operative

### CORE
**Definizione**: Portafoglio passivo, buy-and-hold, con esposizione broad-market e complessità minima.

**Criteri TUTTI obbligatori**:
| Criterio | Soglia | Motivazione |
|----------|--------|-------------|
| Numero strumenti | N ≤ 3 | Semplicità operativa |
| HHI (Herfindahl) | HHI ≥ 0.33 | Concentrazione coerente con pochi strumenti |
| % in Global/World ETF | ≥ 80% | Core deve essere dominato da broad-market |
| Tracking Error vs VT/VWCE | ≤ 3% annualizzato | Replica fedele del mercato globale |
| Turnover implicito | ≤ 5% annuo | Buy-and-hold reale |
| Presence of thematic/sector | 0% | Nessun settoriale ammesso |

**Benchmark naturale**: VT, VWCE, IWDA, ACWI

---

### CORE + SATELLITE
**Definizione**: Core dominante con satelliti limitati, motivati strutturalmente (hedge, inflation protection, diversification).

**Criteri TUTTI obbligatori**:
| Criterio | Soglia | Motivazione |
|----------|--------|-------------|
| Numero strumenti | 3 < N ≤ 6 | Complessità controllata |
| % Core (global equity) | ≥ 60% | Core rimane dominante |
| % Satellite totale | ≤ 40% | Satelliti come complemento |
| % Satellite singolo | ≤ 8% | Nessun satellite dominante |
| Satellite ammessi | Solo: bonds, gold, REIT, EM tilt, inflation-linked | Lista chiusa |
| Tracking Error vs benchmark | ≤ 6% annualizzato | Deviazione controllata |
| Motivazione satellite | Deve essere: hedge OR diversifier OR inflation | No thematic puri |

**Satellite NON ammessi in questa categoria**:
- Settoriali (tech, healthcare, semiconductors)
- Factor aggressivi (pure small-cap, pure value)
- Thematic (clean energy, AI, crypto)
- Singoli paesi (escluso EM broad)

---

### TACTICAL / OPPORTUNISTIC
**Definizione**: Portafoglio con tilt attivi, settoriali, factor, o timing implicito. Richiede giustificazione e monitoraggio.

**Criteri (almeno 1 soddisfatto)**:
| Criterio | Soglia | Interpretazione |
|----------|--------|-----------------|
| Numero strumenti | N > 6 | Complessità elevata |
| % in settoriali/thematic | > 10% | Tilt attivo su settori |
| % in factor puri | > 15% | Factor tilt aggressivo |
| Tracking Error vs global | > 6% annualizzato | Deviazione significativa |
| HHI | < 0.15 | Frammentazione eccessiva |
| Presence of timing signals | Sì (es. pesi non market-cap) | Strategia implicita |

---

## 1.2 Sottotipi TACTICAL (Nuova Classificazione)

### TACTICAL-FACTOR
**Trigger**: % factor puri (SV, SC, momentum, quality, value) > 15%

| Caratteristica | Valore |
|----------------|--------|
| Benchmark naturale | Factor-specific (es. MSCI World Value, Russell 2000 Value) |
| Beta atteso | 1.0 - 1.3 (small/value tendono high-beta) |
| DD tollerato | Fino a +10% vs beta-adjusted benchmark |
| Giudizio chiave | Factor premium catturato? (confronto vs factor index) |

**Regola**: Se TACTICAL-FACTOR, confrontare con benchmark factor, NON con VT.

### TACTICAL-SECTOR
**Trigger**: % settoriali/thematic > 10%

| Caratteristica | Valore |
|----------------|--------|
| Benchmark naturale | Sector-weighted blend o MSCI World + sector index |
| Beta atteso | Variabile (tech ~1.2, utilities ~0.7) |
| DD tollerato | Coerente con beta settoriale |
| Giudizio chiave | Timing settoriale giustificato? (excess return vs sector risk) |

**Settori e Beta tipici**:
| Settore | Beta Tipico | Max DD Atteso |
|---------|-------------|---------------|
| Technology | 1.15 - 1.30 | -40% to -50% |
| Semiconductors | 1.30 - 1.50 | -45% to -55% |
| Healthcare | 0.80 - 1.00 | -30% to -40% |
| Utilities | 0.50 - 0.70 | -20% to -30% |
| Financials | 1.10 - 1.30 | -45% to -55% |
| Energy | 1.00 - 1.40 | -50% to -60% |

### TACTICAL-TIMING
**Trigger**: Pesi non giustificabili con market-cap logic + evidenza di ribilanciamento attivo

| Caratteristica | Valore |
|----------------|--------|
| Benchmark naturale | Risk-parity o target-vol benchmark |
| Beta atteso | Variabile (dipende da strategia) |
| DD tollerato | Deve essere INFERIORE a buy-and-hold equivalente |
| Giudizio chiave | Timing ha aggiunto valore? (confronto vs static allocation) |

**Indicatori di Timing**:
- Turnover > 20% annuo
- Pesi che cambiano > ±5% tra periodi
- Asset allocation non spiegabile da rebalancing calendar

---

## 1.3 Matrice Sottotipo → Benchmark → Giudizio

| Sottotipo | Benchmark Primario | Benchmark Secondario | Giudizio Fragilità |
|-----------|-------------------|---------------------|--------------------|
| TACTICAL-FACTOR | Factor Index | VT | Solo se underperform factor index |
| TACTICAL-SECTOR | Sector-weighted | VT | Solo se underperform sector blend |
| TACTICAL-TIMING | Static equivalent | VT | Solo se timing non aggiunge valore |

**REGOLA CHIAVE**: Fragilità strutturale ≠ underperformance vs VT se sottotipo giustifica deviazione.

---

## 1.2 Decision Tree per Classificazione

```
START
  │
  ├─► Numero strumenti > 6?
  │     ├─► SÌ → TACTICAL
  │     └─► NO → continua
  │
  ├─► % settoriali/thematic > 10%?
  │     ├─► SÌ → TACTICAL
  │     └─► NO → continua
  │
  ├─► % factor puri (SV, SC, momentum) > 15%?
  │     ├─► SÌ → TACTICAL
  │     └─► NO → continua
  │
  ├─► Tracking Error vs VT > 6%?
  │     ├─► SÌ → TACTICAL
  │     └─► NO → continua
  │
  ├─► Numero strumenti ≤ 3 AND % global ≥ 80%?
  │     ├─► SÌ → CORE
  │     └─► NO → continua
  │
  └─► CORE + SATELLITE (default se passa tutti i filtri)
```

---

# SEZIONE 2: RULE SET (Regole di Classificazione)

## 2.1 Hard Rules (Violazione = Flag Obbligatorio)

| ID | Regola | Soglia | Conseguenza |
|----|--------|--------|-------------|
| H1 | Single position max | > 35% (equity) | ⚠️ CONCENTRATION_RISK |
| H2 | Single position max | > 50% (bonds/gold) | ⚠️ CONCENTRATION_RISK |
| H3 | Satellite singolo in CORE+SAT | > 8% | ⚠️ SATELLITE_OVERWEIGHT → upgrade a TACTICAL |
| H4 | Satellite totale in CORE+SAT | > 40% | ⚠️ SATELLITE_EXCESS → upgrade a TACTICAL |
| H5 | Settoriale in CORE | > 0% | ⚠️ CORE_VIOLATION → downgrade a TACTICAL |
| H6 | HHI < 0.10 | (frammentazione) | ⚠️ EXCESSIVE_FRAGMENTATION |
| H7 | Correlazione media > 0.85 | (redundancy) | ⚠️ REDUNDANT_HOLDINGS |
| H8 | Max Drawdown > -55% | (storico) | ⚠️ EXTREME_TAIL_RISK |
| H9 | CCR/Weight ratio > 2.0 | per singolo asset | ⚠️ RISK_LEVERAGE_EXTREME |
| H10 | Data coverage < 50% | per asset | ⚠️ INSUFFICIENT_DATA |

## 2.2 Soft Rules (Violazione = Warning, non cambia classificazione)

| ID | Regola | Soglia | Warning |
|----|--------|--------|---------|
| S1 | Sharpe < 0.30 | (vs risk-free) | ⚡ SUBOPTIMAL_RISK_ADJUSTED |
| S2 | Sortino < 0.40 | (vs risk-free) | ⚡ DOWNSIDE_RISK_ELEVATED |
| S3 | Tracking Error > 4% | (CORE only) | ⚡ DEVIATION_FROM_BENCHMARK |
| S4 | Information Ratio < 0 | (se TE > 2%) | ⚡ ACTIVE_RISK_NOT_REWARDED |
| S5 | Expense Ratio totale > 0.50% | | ⚡ COST_DRAG_ELEVATED |
| S6 | Numero strumenti 4-6 | (CORE category) | ⚡ COMPLEXITY_CREEP |
| S7 | Gold/Commodity > 15% | | ⚡ ALTERNATIVE_OVERWEIGHT |
| S8 | EM > 25% total equity | | ⚡ EM_TILT_AGGRESSIVE |
| S9 | Recovery time > 5 anni | (storico) | ⚡ SLOW_RECOVERY |
| S10 | Volatility > 20% ann. | (all-equity) | ⚡ HIGH_VOLATILITY |

## 2.3 Tie-Break Rules

Quando la classificazione è ambigua:

| Situazione | Tie-Break | Risultato |
|------------|-----------|-----------|
| N=4, % global=75%, no thematic | % satellite totale ≤ 25%? | SÌ → CORE+SAT, NO → TACTICAL |
| TE = 5.5% (borderline) | IR ≥ 0.3? | SÌ → CORE+SAT, NO → TACTICAL |
| Satellite 9% (>8% ma singolo) | Motivazione hedge/inflation? | SÌ → CORE+SAT con warning, NO → TACTICAL |
| Factor 14% (borderline 15%) | Factor = quality/dividend? | SÌ → CORE+SAT, NO (SV/SC) → TACTICAL |

---

# SEZIONE 3: CONFIDENCE MODEL

## 3.1 Formula

```
CONFIDENCE = w1 × DataCoverage + w2 × PairwiseCoverage + w3 × StabilityScore + w4 × HistoryLength

Dove:
- w1 = 0.30 (peso data coverage)
- w2 = 0.30 (peso pairwise covariance coverage)
- w3 = 0.20 (peso stability checks)
- w4 = 0.20 (peso history length)
```

## 3.2 Componenti

### DataCoverage (0-100)
```
DataCoverage = 100 × (1 - NaN_ratio)

Dove NaN_ratio = giorni_con_almeno_un_NaN / giorni_totali_analisi
```

| Score | Interpretazione |
|-------|-----------------|
| 95-100 | Excellent |
| 80-94 | Good |
| 60-79 | Partial |
| < 60 | Insufficient |

### PairwiseCoverage (0-100)
```
PairwiseCoverage = 100 × (coppie_con_corr_valida / coppie_totali)

Coppia valida = almeno 252 giorni di overlap (1 anno trading)
```

| Score | Interpretazione |
|-------|-----------------|
| 100 | Full matrix |
| 80-99 | Minor gaps |
| 50-79 | Significant gaps |
| < 50 | Matrix unreliable |

### StabilityScore (0-100)
```
StabilityScore = 100 - (volatility_of_rolling_correlations × 200)

Rolling correlations = correlazioni 60-day rolling tra coppie principali
Volatility = std dev delle rolling correlations
```

| Score | Interpretazione |
|-------|-----------------|
| 80-100 | Stable relationships |
| 60-79 | Moderate regime shifts |
| < 60 | Unstable/regime-dependent |

### HistoryLength (0-100)
```
HistoryLength = min(100, (min_asset_history_days / 1260) × 100)

1260 = 5 anni di trading days (obiettivo ideale)
```

| Days | Score | Interpretazione |
|------|-------|-----------------|
| ≥ 1260 | 100 | Full cycle coverage |
| 756-1259 | 60-99 | 3-5 years |
| 252-755 | 20-59 | 1-3 years |
| < 252 | < 20 | Insufficient |

## 3.3 Confidence Levels e GATING RULES

| Score Aggregato | Level | Azione |
|-----------------|-------|--------|
| 80-100 | HIGH | Verdetto pieno |
| 60-79 | MEDIUM | Verdetto con qualifiche |
| 40-59 | LOW | Verdetto tentativo + "REVIEW_NEEDED" |
| < 40 | INSUFFICIENT | Nessun verdetto strutturale |

### GATING RULES (Vincolanti)

**Queste NON sono warning, sono BLOCCHI HARD.**

```
┌────────────────────────────────────────────────────────────────────────┐
│ CONFIDENCE LEVEL │ CCR        │ CORRELATIONS │ STRUCTURAL VERDICT     │
├──────────────────┼────────────┼──────────────┼────────────────────────┤
│ HIGH (≥80)       │ ✅ Full    │ ✅ Full      │ ✅ Full                │
│ MEDIUM (60-79)   │ ⚠️ Solo se │ ⚠️ Solo se   │ ⚠️ Con disclaimer      │
│                  │ coverage   │ NaN < 20%    │                        │
│                  │ ≥ 70%      │              │                        │
│ LOW (40-59)      │ ❌ N/A     │ ❌ N/A       │ ❌ "REVIEW_NEEDED"     │
│ INSUFFICIENT(<40)│ ❌ N/A     │ ❌ N/A       │ ❌ BLOCKED             │
└────────────────────────────────────────────────────────────────────────┘
```

### Regole di Gating Esplicite

```python
# REGOLA 1: CCR Gating
if confidence_level in ['LOW', 'INSUFFICIENT']:
    ccr_all_assets = "N/A"
    ccr_in_verdict = False  # VIETATO usare CCR nel verdetto
    
elif confidence_level == 'MEDIUM':
    if pairwise_coverage < 0.70:
        ccr_all_assets = "N/A"
    else:
        ccr_available = True
        ccr_disclaimer = "CCR calcolato su dati parziali - interpretare con cautela"

# REGOLA 2: Correlation Gating
if nan_ratio_correlation > 0.20:
    correlation_verdict_allowed = False
    diversification_claims = "BLOCKED"  # Non posso dire "ben diversificato"

# REGOLA 3: Structural Verdict Gating
if confidence_level == 'INSUFFICIENT':
    structural_verdict = "ANALYSIS_BLOCKED - Dati insufficienti"
    allowed_output = ['basic_metrics', 'position_list', 'data_quality_report']
    blocked_output = ['ccr', 'correlation_analysis', 'structural_assessment', 'final_verdict']
```

### Messaggi di Gating

| Situazione | Messaggio OBBLIGATORIO |
|------------|------------------------|
| CCR bloccato | "⛔ CCR NON DISPONIBILE: Confidence {X}% insufficiente per calcolo affidabile" |
| Correlazioni bloccate | "⛔ MATRICE CORRELAZIONI BLOCCATA: {X}% celle non calcolabili" |
| Verdetto bloccato | "⛔ VERDETTO STRUTTURALE SOSPESO: Confidence {X}% < soglia minima (60%)" |

## 3.4 Impatto sul Verdetto

```python
if confidence_level == "INSUFFICIENT":
    verdict = "ANALYSIS_INCOMPLETE - Insufficient data for structural assessment"
    disable: structural_verdict, efficiency_verdict, resilience_verdict
    allow: basic_metrics (CAGR, vol), position_summary

elif confidence_level == "LOW":
    verdict_prefix = "⚠️ LOW CONFIDENCE: "
    verdict_suffix = " (Review recommended - data quality issues detected)"

elif confidence_level == "MEDIUM":
    verdict_prefix = ""
    verdict_suffix = " (Based on available data; some metrics approximate)"

elif confidence_level == "HIGH":
    verdict_prefix = ""
    verdict_suffix = ""
```

---

# SEZIONE 4: DATA QUALITY GATES

## 4.1 Gate Definitions

### GATE 1: Minimum History per Asset
```
RULE: Ogni asset deve avere ≥ 252 trading days (1 anno)
ACTION se violato:
  - Asset con < 252 days → marcato [INSUFFICIENT_HISTORY]
  - Se peso asset > 10% → analisi declassata a "PARTIAL"
  - Se peso asset > 30% → analisi declassata a "UNRELIABLE"
```

### GATE 2: Overlap Period per Covariance
```
RULE: Ogni coppia di asset deve avere ≥ 126 trading days di overlap (6 mesi)
ACTION se violato:
  - Coppia senza overlap sufficiente → correlazione = "N/A"
  - Se > 30% coppie N/A → matrice correlazioni = "INCOMPLETE"
  - CCR per asset senza correlazioni valide → "N/A" (non 0.00%)
```

### GATE 3: Benchmark Availability
```
RULE: Benchmark (VT/SPY/BND) deve avere dati per intero periodo analisi
ACTION se violato:
  - Benchmark parziale → comparison limitata a periodo overlap
  - Se overlap < 50% periodo → benchmark comparison = "NOT_AVAILABLE"
```

### GATE 4: Price Data Quality
```
RULE: No più di 5 consecutive missing days per asset (esclusi weekend/holiday)
ACTION se violato:
  - Gap > 5 days → [DATA_GAP_DETECTED]
  - Se gap > 20 days → asset marcato [STALE_DATA]
  - Se gap durante crash (VIX > 30) → [CRISIS_DATA_MISSING] - critico
```

### GATE 5: Return Distribution Sanity
```
RULE: Daily returns devono essere in range [-25%, +25%] 
ACTION se violato:
  - Return > ±25% → [OUTLIER_DETECTED] - verificare stock split/dividend
  - Se > 3 outliers non spiegati → [DATA_QUALITY_SUSPECT]
```

## 4.2 Quality Assessment Output

```
═══════════════════════════════════════════════════════════════
                    DATA QUALITY ASSESSMENT
═══════════════════════════════════════════════════════════════

Overall Status: [RELIABLE | PARTIAL | UNRELIABLE]

┌─────────────────────────────────────────────────────────────┐
│ GATE                    │ STATUS   │ DETAILS               │
├─────────────────────────┼──────────┼───────────────────────┤
│ 1. History Length       │ ✅ PASS  │ Min: 1847 days (7.3y) │
│ 2. Pairwise Overlap     │ ⚠️ WARN  │ 2/15 pairs < 126 days │
│ 3. Benchmark Available  │ ✅ PASS  │ 100% overlap          │
│ 4. Price Continuity     │ ✅ PASS  │ No gaps detected      │
│ 5. Return Sanity        │ ✅ PASS  │ 0 unexplained outliers│
└─────────────────────────┴──────────┴───────────────────────┘

Confidence Score: 78/100 (MEDIUM)
Metrics Reliability: CCR partially available (12/15 pairs valid)

Note: Correlations for GOLD-SEMI pair marked N/A (insufficient overlap)
```

---

# SEZIONE 5: RISK METRICS ROBUSTNESS POLICY

## 5.1 CCR/MCR Handling

### Policy: Zero vs N/A
```
REGOLA FONDAMENTALE:
- CCR = 0.00% → SOLO se contributo matematico è genuinamente zero
- CCR = "N/A" → se covarianza non stimabile per dati insufficienti

MAI mostrare 0.00% per asset con peso > 0 e dati mancanti.
```

### Calcolo CCR con Dati Parziali
```
Scenario A: Tutti i dati disponibili
  → CCR standard: CCR_i = w_i × (Σ_j w_j × σ_i × σ_j × ρ_ij) / σ_portfolio

Scenario B: Alcune correlazioni mancanti
  → Opzione 1 (CONSERVATIVE): CCR_i = "N/A" per asset coinvolti
  → Opzione 2 (SHRINKAGE): Usa Ledoit-Wolf shrinkage per stimare ρ mancanti
     - Se shrinkage usato → nota: "CCR estimated via shrinkage (X pairs imputed)"

Scenario C: Troppi dati mancanti (> 50% coppie)
  → CCR per tutti = "N/A"
  → Nota: "Risk contribution analysis not available - insufficient covariance data"
```

## 5.2 Beta-Adjusted Metrics (Nuova Sezione)

### Metriche Normalizzate Obbligatorie

Per evitare bias anti-equity, TUTTE le metriche di rischio devono essere presentate in due forme:
1. **Assolute** - valore grezzo
2. **Beta-Adjusted** - normalizzate per esposizione di mercato

### Definizioni

```
Beta_portfolio = Cov(R_p, R_benchmark) / Var(R_benchmark)

# Metriche Beta-Adjusted
Relative_DD = DD_portfolio / DD_benchmark
Excess_DD = DD_portfolio - (DD_benchmark × Beta_portfolio)
Beta_Adjusted_Vol = Vol_portfolio / Beta_portfolio
Beta_Adjusted_Sharpe = Sharpe_portfolio / Beta_portfolio  # Sharpe per unità di beta
```

### Output Table Beta-Adjusted

```
┌─────────────────────────────────────────────────────────────────────────┐
│ RISK METRICS (Absolute vs Beta-Adjusted)                                │
├─────────────────────────────────────────────────────────────────────────┤
│ Metric              │ Absolute   │ Beta-Adj   │ vs Benchmark │ Verdict │
├─────────────────────┼────────────┼────────────┼──────────────┼─────────┤
│ Max Drawdown        │ -41.2%     │ -35.8%*    │ -34.0%       │ ✅ OK   │
│ Volatility          │ 18.5%      │ 16.1%*     │ 15.2%        │ ✅ OK   │
│ Sharpe              │ 0.52       │ 0.45*      │ 0.48         │ ✅ OK   │
│ Sortino             │ 0.68       │ 0.59*      │ 0.62         │ ✅ OK   │
└─────────────────────┴────────────┴────────────┴──────────────┴─────────┘
* Beta-adjusted (Portfolio Beta = 1.15)

Interpretazione: Metriche assolute sembrano peggiori ma beta-adjusted
confermano che il portfolio non ha fragilità strutturale - solo higher beta.
```

### Regole di Giudizio Beta-Adjusted

| Metrica | Soglia Assoluta | Soglia Beta-Adjusted | Quale Usare per Verdict |
|---------|-----------------|---------------------|------------------------|
| Max DD | -55% (hard limit) | Excess_DD > 15% | **Beta-Adjusted** |
| Volatility | 25% (hard limit) | Excess_Vol > 5% | **Beta-Adjusted** |
| Sharpe | 0.30 (minimum) | vs Sharpe_benchmark | **Relativo** |

**REGOLA FONDAMENTALE**:
```
SE metrica_assoluta è "cattiva" MA metrica_beta_adjusted è "OK":
  → NON è fragilità strutturale
  → È conseguenza di risk intent
  → Verdict deve riflettere questo
```

---

### Output Format per CCR
```
┌─────────────────────────────────────────────────────────────┐
│ RISK CONTRIBUTION (CCR)                                     │
├─────────────────────────────────────────────────────────────┤
│ Ticker   │ Weight │ CCR%     │ CCR/W Ratio │ Status        │
├──────────┼────────┼──────────┼─────────────┼───────────────┤
│ VWCE     │ 35.0%  │ 42.3%    │ 1.21        │ ✓ Valid       │
│ AVUV     │ 10.0%  │ 14.8%    │ 1.48        │ ✓ Valid       │
│ GOLD     │  5.0%  │ N/A      │ N/A         │ ⚠ Insufficient│
│ SEMI     │  8.0%  │ 12.1%*   │ 1.51        │ * Estimated   │
└──────────┴────────┴──────────┴─────────────┴───────────────┘

Notes:
* Estimated via Ledoit-Wolf shrinkage (3 pairs imputed)
⚠ GOLD: Correlation with 4/6 assets not computable (< 126 days overlap)

Total CCR Coverage: 85.0% of portfolio (GOLD excluded)
```

## 5.2 Correlation Matrix Handling

### NaN Policy
```
REGOLA:
- Correlazione = NaN → mostrare "---" nella matrice
- Se > 20% celle NaN → matrice marcata [INCOMPLETE]
- Se cella critica NaN (es. tra top-2 holdings) → [CRITICAL_GAP]
```

### Output con NaN
```
CORRELATION MATRIX (Normal Regime)
Status: PARTIAL (3/15 pairs unavailable)

         VWCE   AVUV   SEMI   GOLD   EMIM   VAGF
VWCE     1.00   0.82   0.71   -0.05  0.78   0.15
AVUV     0.82   1.00   0.68   ---    0.71   0.12
SEMI     0.71   0.68   1.00   ---    0.65   0.08
GOLD    -0.05   ---    ---    1.00   ---    0.35
EMIM     0.78   0.71   0.65   ---    1.00   0.18
VAGF     0.15   0.12   0.08   0.35   0.18   1.00

Legend: --- = insufficient data (< 126 days overlap)
⚠ GOLD correlations mostly unavailable - diversification benefit unverified
```

## 5.3 Drawdown Attribution: Structural vs Regime-Driven

### Definizioni

| Tipo | Definizione | Esempio |
|------|-------------|--------|
| **Regime-Driven DD** | Drawdown coerente con beta e asset class | Portfolio 100% equity con DD -35% durante crash -33% di VT |
| **Structural DD** | Drawdown PEGGIORE del benchmark coerente | Portfolio 100% equity con DD -50% quando VT fa -33% |

### Regola di Attribuzione

```
Excess_DD = DD_portfolio - DD_benchmark_coerente

SE Excess_DD ≤ +5%:
  → DD è REGIME-DRIVEN (accettabile per risk intent)
  → Non genera flag "FRAGILE"
  → Verdict: "Drawdown coerente con esposizione di mercato"

SE Excess_DD > +5% AND ≤ +15%:
  → DD è PARTIALLY STRUCTURAL
  → Warning: "Drawdown moderatamente peggiore del benchmark"
  → Investigare: concentrazione, leverage implicito, asset illiquidi

SE Excess_DD > +15%:
  → DD è STRUCTURAL FRAGILITY
  → Flag: ⚠️ STRUCTURAL_FRAGILITY
  → Verdict: "Drawdown significativamente peggiore del benchmark - errore di design"
```

### Benchmark Coerente per Risk Intent

| Risk Intent | Benchmark DD Reference | DD Soglia "Normale" |
|-------------|----------------------|---------------------|
| CONSERVATIVE | 40/60 Portfolio | -15% |
| MODERATE | 60/40 Portfolio | -25% |
| GROWTH | VT / ACWI | -35% |
| AGGRESSIVE | VT / ACWI | -45% |
| HIGH-BETA | Small Value Index | -55% |

### Calcolo Beta-Adjusted Metrics

```
Beta_portfolio = Cov(R_portfolio, R_benchmark) / Var(R_benchmark)

Expected_DD = DD_benchmark × Beta_portfolio
Expected_Vol = Vol_benchmark × Beta_portfolio

Excess_DD = DD_portfolio - Expected_DD
Excess_Vol = Vol_portfolio - Expected_Vol
```

### Output per Drawdown Attribution

```
┌─────────────────────────────────────────────────────────────┐
│ DRAWDOWN ATTRIBUTION                                        │
├─────────────────────────────────────────────────────────────┤
│ Risk Intent Declared:    AGGRESSIVE                         │
│ Benchmark Coerente:      VT (Global Equity)                 │
│ Portfolio Beta:          1.15                               │
├─────────────────────────────────────────────────────────────┤
│ Portfolio Max DD:        -41.2%                             │
│ Benchmark Max DD:        -34.0%                             │
│ Expected DD (β-adj):     -39.1%                             │
│ Excess DD:               -2.1%  ✅ REGIME-DRIVEN            │
├─────────────────────────────────────────────────────────────┤
│ VERDICT: Drawdown coerente con beta e risk intent.          │
│          Non evidenza di fragilità strutturale.             │
└─────────────────────────────────────────────────────────────┘
```

### Frasi Standard per DD Attribution

| Situazione | Frase |
|------------|-------|
| Excess DD ≤ 5% | "Drawdown coerente con esposizione: regime-driven, non strutturale" |
| Excess DD 5-15% | "Drawdown moderatamente elevato: verificare concentrazione/correlazioni" |
| Excess DD > 15% | "⚠️ FRAGILITÀ STRUTTURALE: drawdown significativamente peggiore del benchmark" |
| Beta > 1.2, DD alto | "Drawdown elevato ma coerente con beta {X} - scelta consapevole di risk intent" |

---

## 5.4 Verdetti con Dati Incompleti

### Frasi VIETATE se dati incompleti:
- ❌ "Diversificazione stabile"
- ❌ "Correlazioni sotto controllo"
- ❌ "Risk contribution bilanciata"
- ❌ "Strutturalmente robusto"

### Frasi AMMESSE:
- ✅ "Diversificazione non valutabile (dati insufficienti per X asset)"
- ✅ "Correlazioni parzialmente disponibili - conclusioni limitate"
- ✅ "Risk contribution calcolata su 85% del portfolio"
- ✅ "Struttura da verificare con dati completi"

---

# SEZIONE 6: REPORTING TEMPLATE

## 6.1 Struttura Report

```
════════════════════════════════════════════════════════════════
           PORTFOLIO ANALYSIS REPORT
           Generated: [DATE] | Engine v3.0
════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────┐
│ SECTION 0: DATA QUALITY ASSESSMENT                         │
│ (SEMPRE PRIMA DI TUTTO)                                    │
└─────────────────────────────────────────────────────────────┘
  - Quality Status: [RELIABLE / PARTIAL / UNRELIABLE]
  - Confidence Score: XX/100 ([HIGH/MEDIUM/LOW])
  - Data Gates: [tabella pass/warn/fail]
  - Limitations: [lista specifica]

┌─────────────────────────────────────────────────────────────┐
│ SECTION 1: PORTFOLIO CLASSIFICATION                        │
└─────────────────────────────────────────────────────────────┘
  - Type: [CORE / CORE+SATELLITE / TACTICAL]
  - Rules triggered: [lista regole H/S applicate]
  - Benchmark assigned: [VT / custom]

┌─────────────────────────────────────────────────────────────┐
│ SECTION 2: COMPOSITION & WEIGHTS                           │
└─────────────────────────────────────────────────────────────┘
  - Holdings table
  - Geographic exposure
  - Asset class breakdown
  - HHI / Effective positions

┌─────────────────────────────────────────────────────────────┐
│ SECTION 3: PERFORMANCE METRICS                             │
└─────────────────────────────────────────────────────────────┘
  - CAGR, Volatility
  - Sharpe, Sortino
  - Max DD, Recovery time
  - Comparison vs benchmark

┌─────────────────────────────────────────────────────────────┐
│ SECTION 4: RISK ANALYSIS                                   │
│ (Solo se Confidence ≥ MEDIUM)                              │
└─────────────────────────────────────────────────────────────┘
  - CCR/MCR table (con N/A dove necessario)
  - Correlation matrix (con --- dove necessario)
  - Correlation regime analysis (stress vs normal)
  - Risk concentration flags

┌─────────────────────────────────────────────────────────────┐
│ SECTION 5: STRUCTURAL ASSESSMENT                           │
│ (Solo se Confidence ≥ MEDIUM)                              │
└─────────────────────────────────────────────────────────────┘
  - Hard rule violations
  - Soft rule warnings
  - Efficiency assessment (TE, IR, alpha)

┌─────────────────────────────────────────────────────────────┐
│ SECTION 6: MODULAR VERDICT                                 │
└─────────────────────────────────────────────────────────────┘
  A) Data Integrity Score:      XX/100
  B) Structural Coherence:      XX/100
  C) Efficiency vs Benchmark:   XX/100
  D) Tail Risk Assessment:      XX/100
  ─────────────────────────────────────
  AGGREGATE VERDICT: [testo] (Confidence: [HIGH/MED/LOW])

┌─────────────────────────────────────────────────────────────┐
│ SECTION 7: ACTIONABLE INSIGHTS                             │
└─────────────────────────────────────────────────────────────┘
  - Issues identified (prioritized)
  - Suggested actions
  - Monitoring recommendations
```

## 6.2 Linguaggio Standard

### Verdetti Positivi (usare solo se Confidence ≥ MEDIUM)

**REGOLA**: Ogni verdetto deve essere **rule-based**, non narrativo.
Formato: `SE [condizione verificabile] → [verdetto]`

| Condizione (Rule) | Verdetto |
|-------------------|----------|
| Sharpe ≥ Sharpe_benchmark AND TE ≤ 3% | "✅ EFFICIENTE: Risk-adjusted return ≥ benchmark con tracking error contenuto" |
| max(CCR/Weight) ≤ 1.5 | "✅ BILANCIATO: Nessun asset con risk leverage > 1.5x" |
| mean(Corr) < 0.70 AND NaN_ratio < 0.10 | "✅ DIVERSIFICATO: Correlazione media {X} < 0.70 (matrice completa)" |
| Excess_DD ≤ 5% (vs benchmark coerente) | "✅ DD COERENTE: Drawdown in linea con risk intent ({INTENT})" |
| Beta_portfolio ∈ [Beta_intent - 0.2, Beta_intent + 0.2] | "✅ BETA COERENTE: Esposizione {X} allineata a risk intent {INTENT}" |

### Verdetti Negativi

**REGOLA**: Distinguere SEMPRE tra:
- **Structural Issue** → Errore di design, da correggere
- **Regime Issue** → Conseguenza di risk intent, da accettare consapevolmente

| Condizione (Rule) | Tipo | Verdetto |
|-------------------|------|----------|
| CCR/W > 1.5 per asset X | STRUCTURAL | "⚠️ STRUCTURAL: {TICKER} risk leverage {X}x - peso {Y}% genera {Z}% rischio" |
| CCR/W > 1.5 MA asset è factor/sector coerente con intent | REGIME | "ℹ️ REGIME: {TICKER} risk leverage {X}x coerente con tilt {TACTICAL_TYPE}" |
| Corr > 0.85 tra asset | STRUCTURAL | "⚠️ STRUCTURAL: Ridondanza {TICKER1}-{TICKER2} (ρ={X}) - consolidare" |
| Excess_DD > 15% vs benchmark coerente | STRUCTURAL | "🔴 STRUCTURAL FRAGILITY: DD -{X}% vs expected -{Y}% (excess {Z}%)" |
| Excess_DD ≤ 15% MA DD assoluto alto | REGIME | "ℹ️ REGIME: DD -{X}% coerente con beta {Y} e risk intent {INTENT}" |
| IR < 0 con TE > 3% | STRUCTURAL | "⚠️ STRUCTURAL: Active risk non remunerato (IR={X}, TE={Y}%)" |
| Vol > 20% MA coerente con beta/intent | REGIME | "ℹ️ REGIME: Volatilità {X}% coerente con beta {Y} ({INTENT})" |
| Vol > Expected_Vol + 5% | STRUCTURAL | "⚠️ STRUCTURAL: Volatilità {X}% > attesa {Y}% - verificare concentrazione" |

### Verdetti con Qualifiche (Confidence = LOW)
| Frase Standard |
|----------------|
| "Analisi preliminare (LOW CONFIDENCE): [verdetto]. Raccomandato riesame con dati completi." |
| "Struttura non pienamente valutabile - [X]% del portfolio senza correlazioni calcolabili." |
| "Verdict tentativo - dati insufficienti per confermare [metrica]." |

---

# SEZIONE 7: ESEMPI APPLICATI

## Esempio 1: CORE Puro

**Composizione**:
| Ticker | Weight | Asset Class |
|--------|--------|-------------|
| VWCE | 100% | Global Equity |

**Regole applicate**:
- N = 1 → ≤ 3 ✅
- % Global = 100% → ≥ 80% ✅
- HHI = 1.0 → ≥ 0.33 ✅
- Settoriali = 0% → = 0% ✅
- TE vs VT = ~0.5% → ≤ 3% ✅

**Classificazione**: CORE
**Confidence**: HIGH (single asset, full history)

**Verdetto**:
```
CLASSIFICATION: CORE (Passive Buy-and-Hold)
Confidence: HIGH (95/100)

Data Integrity:       98/100 - Full history, no gaps
Structural Coherence: 100/100 - Single global equity ETF, maximum simplicity
Efficiency:           85/100 - Sharpe 0.42 (benchmark-like), no active risk
Tail Risk:            70/100 - Max DD -34% (market beta = 1.0)

AGGREGATE: Portafoglio CORE correttamente implementato. Semplicità massima,
costi minimi, replica fedele del mercato globale. Drawdown in linea con equity
market. Adatto a investitore che accetta volatilità di mercato per rendimento
di mercato.
```

---

## Esempio 2: CORE + SATELLITE

**Composizione**:
| Ticker | Weight | Asset Class | Role |
|--------|--------|-------------|------|
| VWCE | 80% | Global Equity | Core |
| VAGF | 10% | Global Agg Bonds | Satellite (hedge) |
| SGLD | 10% | Gold | Satellite (inflation) |

**Regole applicate**:
- N = 3 → ≤ 3 (borderline) ✅
- % Global equity = 80% → ≥ 60% ✅
- % Satellite totale = 20% → ≤ 40% ✅
- % Satellite singolo = 10% → ≤ 8% ⚠️ (soft warning)
- Satellite types = bonds + gold → ammessi ✅
- Settoriali = 0% ✅

**Classificazione**: CORE + SATELLITE (con warning S7: satellite singolo 10% > 8%)
**Confidence**: HIGH

**Verdetto**:
```
CLASSIFICATION: CORE + SATELLITE
Confidence: HIGH (92/100)

Data Integrity:       95/100 - All assets with 5+ years history
Structural Coherence: 88/100 - Core dominant, satellites justified
                      ⚡ S3: Single satellite at 10% (threshold 8%)
Efficiency:           82/100 - Sharpe 0.48, slight improvement over pure equity
Tail Risk:            78/100 - Max DD -28% (bonds/gold reduced drawdown)

AGGREGATE: Portafoglio CORE+SATELLITE ben strutturato. Core (VWCE 80%) fornisce
esposizione di mercato, satellite bonds riduce volatilità, gold aggiunge
diversificazione non correlata. Singolo satellite leggermente sopra soglia (10%
vs 8%) ma motivazione strutturale valida (inflation hedge). Complessità
giustificata dal miglioramento risk-adjusted.
```

---

## Esempio 3: TACTICAL (caso utente)

**Composizione** (esempio semplificato):
| Ticker | Weight | Asset Class | Role |
|--------|--------|-------------|------|
| VWCE | 35% | Global Equity | Core |
| AVUV | 10% | US Small Value | Factor |
| AVDV | 5% | Intl Small Value | Factor |
| ZPRV | 5% | EU Small Value | Factor |
| SEMI | 8% | Semiconductors | Sector |
| HEAL | 5% | Healthcare | Sector |
| VAGF | 12% | Global Bonds | Defensive |
| SGLD | 5% | Gold | Hedge |
| EMIM | 10% | Emerging Markets | Tilt |
| REIT | 5% | Real Estate | Alternative |

**Regole applicate**:
- N = 10 → > 6 ⚠️ **H-RULE TRIGGERED → TACTICAL**
- % Global equity = 35% → < 60% ⚠️
- % Factor = 20% → > 15% ⚠️ **H-RULE TRIGGERED**
- % Settoriali = 13% → > 10% ⚠️ **H-RULE TRIGGERED**
- TE vs VT = ~8% → > 6% ⚠️
- HHI = 0.16 → < 0.33 (frammentato)

**Classificazione**: TACTICAL / OPPORTUNISTIC
**Confidence**: MEDIUM (alcune correlazioni N/A per SEMI < 2 anni dati)

**Verdetto**:
```
CLASSIFICATION: TACTICAL / OPPORTUNISTIC
Confidence: MEDIUM (71/100)

Data Integrity:       78/100 - SEMI with limited history (18 months)
                      ⚠ Correlation for SEMI-GOLD, SEMI-REIT = N/A
Structural Coherence: 55/100 - Multiple hard rules triggered
                      ⚠️ H1: N > 6 (10 positions)
                      ⚠️ H3: Factor allocation 20% > 15%
                      ⚠️ H4: Sector allocation 13% > 10%
                      ⚡ S4: HHI 0.16 suggests fragmentation
Efficiency:           65/100 - TE 8% with IR 0.15 (active risk marginally rewarded)
                      ⚡ S2: High tracking error for modest alpha
Tail Risk:            60/100 - Max DD -38% (small value amplified drawdown)
                      ⚠️ H9: AVUV CCR/Weight = 1.8 (risk leverage elevated)

AGGREGATE (MEDIUM CONFIDENCE): Portafoglio TACTICAL con complessità elevata.
Factor tilt (20% small value) e settoriali (13%) classificano come strategia
attiva, non passiva. Tracking error 8% non pienamente giustificato da alpha
generato (IR 0.15). Small value contribuisce rischio sproporzionato (CCR/W 1.8).

⚠️ STRUTTURALMENTE COMPLESSO: 10 posizioni creano costo di gestione e
monitoring senza chiaro beneficio di diversificazione (correlazioni medie 0.72).

RACCOMANDAZIONE: Verificare se complessità aggiunge valore vs CORE semplificato.
Considerare consolidamento posizioni factor in singolo veicolo.
```

---

# SEZIONE 8: FAILURE MODES E REGOLE PREVENTIVE

## 10 Failure Modes Tipici con Prevenzione

### FM-1: CCR = 0.00% per Asset con Peso > 0

**Sintomo**: Asset con peso 5% mostra CCR% = 0.00%
**Causa**: Covarianza non calcolabile, sistema imposta default 0
**Regola Preventiva**:
```python
if weight[i] > 0 and covariance[i] is NaN:
    ccr[i] = "N/A"
    flag = "COVARIANCE_UNAVAILABLE"
```
**Messaggio Output**:
```
⚠️ CCR NON DISPONIBILE: [TICKER] - correlazioni insufficienti per calcolo.
   Risk contribution esclusa dal totale. Verificare dati.
```

---

### FM-2: Correlazione NaN + Verdetto "Diversificazione Stabile"

**Sintomo**: Matrice con 30% NaN, ma verdict dice "correlazioni sotto controllo"
**Causa**: Logica verdetto non controlla completezza matrice
**Regola Preventiva**:
```python
if nan_ratio_correlation_matrix > 0.20:
    disable_verdict("diversification_stable")
    append_qualifier("PARTIAL_DATA")
```
**Messaggio Output**:
```
⚠️ MATRICE CORRELAZIONI INCOMPLETA: [X]% coppie non calcolabili.
   Giudizio su diversificazione sospeso - dati insufficienti.
```

---

### FM-3: "Resilienza Alta" + "Strutturalmente Fragile" Contemporanei

**Sintomo**: Verdetti contraddittori nello stesso report
**Causa**: Moduli verdetto indipendenti senza arbitraggio
**Regola Preventiva**:
```python
if verdict_resilience == "HIGH" and verdict_structure == "FRAGILE":
    final_verdict = "MIXED_SIGNALS"
    explanation = "Metriche storiche positive ma struttura subottimale"
```
**Messaggio Output**:
```
⚠️ SEGNALI MISTI: Performance storica positiva (resilienza) ma struttura
   presenta criticità (complessità/concentrazione). Raccomandato approfondimento.
```

---

### FM-4: Tracking Error Calcolato su Periodi Non Allineati

**Sintomo**: TE sembra basso ma benchmark e portfolio hanno periodi diversi
**Causa**: Mancato allineamento date tra portfolio e benchmark
**Regola Preventiva**:
```python
overlap_days = len(set(portfolio_dates) & set(benchmark_dates))
if overlap_days < 0.80 * len(portfolio_dates):
    te_status = "PARTIAL_OVERLAP"
    te_confidence = "LOW"
```
**Messaggio Output**:
```
⚠️ TRACKING ERROR PARZIALE: Calcolato su [X]% del periodo (overlap limitato
   con benchmark). Valore potrebbe non essere rappresentativo.
```

---

### FM-5: Sharpe Negativo Mostrato come "Accettabile"

**Sintomo**: Sharpe = -0.15 ma sistema non genera warning
**Causa**: Soglia warning troppo bassa o assente
**Regola Preventiva**:
```python
if sharpe < 0:
    flag = "NEGATIVE_RISK_ADJUSTED"
    severity = "CRITICAL" if sharpe < -0.20 else "WARNING"
```
**Messaggio Output**:
```
🔴 SHARPE NEGATIVO ([X]): Rendimento inferiore al risk-free per unità di
   rischio. Strategia ha distrutto valore risk-adjusted nel periodo.
```

---

### FM-6: Max Drawdown Sottostimato per Dati Mancanti Durante Crisi

**Sintomo**: Max DD = -15% ma periodo include 2020 COVID crash
**Causa**: Dati mancanti durante marzo 2020
**Regola Preventiva**:
```python
crisis_periods = [(2008-09, 2009-03), (2020-02, 2020-04), (2022-01, 2022-10)]
for start, end in crisis_periods:
    if data_coverage(start, end) < 0.90:
        flag = "CRISIS_DATA_GAP"
```
**Messaggio Output**:
```
⚠️ DRAWDOWN POTENZIALMENTE SOTTOSTIMATO: Dati incompleti durante periodo
   crisi [DATE]. Max DD reale potrebbe essere peggiore di quanto mostrato.
```

---

### FM-7: Classificazione CORE per Portfolio con 8 Posizioni

**Sintomo**: Sistema classifica come CORE ma ha N > 6
**Causa**: Bug in logica o hard rule non applicata
**Regola Preventiva**:
```python
# Hard rule MUST be first check
if n_positions > 6:
    classification = "TACTICAL"  # Immediate override
    rule_triggered = "H1_POSITION_COUNT"
```
**Messaggio Output**:
```
📊 CLASSIFICAZIONE: TACTICAL
   Regola H1 applicata: Numero posizioni ([N]) > 6 → classificazione automatica
   come TACTICAL indipendentemente da altri criteri.
```

---

### FM-8: IR Positivo Mostrato senza Verifica Significatività Statistica

**Sintomo**: IR = 0.12 presentato come "alpha positivo"
**Causa**: IR basso non è significativo, ma sistema non lo segnala
**Regola Preventiva**:
```python
# IR significance: need IR > 0.3 for 95% confidence with 3y data
if ir < 0.30 and ir > 0:
    significance = "NOT_SIGNIFICANT"
    note = "IR too low for statistical significance"
```
**Messaggio Output**:
```
📈 Information Ratio: [X] (NON STATISTICAMENTE SIGNIFICATIVO)
   IR < 0.30 non permette di escludere che alpha sia dovuto a caso.
   Non interpretare come evidenza di skill.
```

---

### FM-9: Portfolio 100% Equity Confrontato con Benchmark 60/40

**Sintomo**: Portfolio all-equity sembra "outperform" vs 60/40
**Causa**: Benchmark mismatch - confronto non omogeneo
**Regola Preventiva**:
```python
portfolio_equity_pct = sum(weights[equity_assets])
if portfolio_equity_pct > 0.90:
    benchmark = "VT"  # Force equity benchmark
    if user_benchmark == "60/40":
        warning = "BENCHMARK_MISMATCH"
```
**Messaggio Output**:
```
⚠️ BENCHMARK NON COMPARABILE: Portfolio [X]% equity confrontato con
   benchmark [Y]% equity. Usare benchmark omogeneo per fair comparison.
   Benchmark suggerito: [SUGGESTED]
```

---

### FM-10: Volatilità Annualizzata da Meno di 1 Anno di Dati

**Sintomo**: Volatility = 12% ma basata su 6 mesi di dati
**Causa**: Annualizzazione da periodo troppo breve
**Regola Preventiva**:
```python
if trading_days < 252:
    volatility_confidence = "LOW"
    note = f"Annualized from {trading_days} days - may not be representative"
```
**Messaggio Output**:
```
📉 Volatilità: [X]% (STIMA PRELIMINARE - solo [N] giorni di dati)
   Annualizzazione da periodo < 1 anno può non catturare regime completo.
   Considerare come indicativa, non definitiva.
```

---

## Tabella Riassuntiva Failure Modes

| ID | Failure Mode | Regola Preventiva | Codice Messaggio |
|----|--------------|-------------------|------------------|
| FM-1 | CCR=0 per asset non-zero | CCR = N/A se cov=NaN | `COVARIANCE_UNAVAILABLE` |
| FM-2 | Corr NaN + verdict stabile | Disable verdict se NaN>20% | `PARTIAL_CORRELATION_MATRIX` |
| FM-3 | Verdetti contraddittori | Arbitraggio con MIXED_SIGNALS | `MIXED_SIGNALS` |
| FM-4 | TE su periodi non allineati | Check overlap ≥ 80% | `PARTIAL_BENCHMARK_OVERLAP` |
| FM-5 | Sharpe negativo non flaggato | Hard flag se Sharpe < 0 | `NEGATIVE_RISK_ADJUSTED` |
| FM-6 | DD sottostimato per gap crisi | Check coverage durante crisi | `CRISIS_DATA_GAP` |
| FM-7 | CORE con N > 6 | Hard rule first | `POSITION_COUNT_OVERRIDE` |
| FM-8 | IR non significativo come alpha | IR < 0.3 = not significant | `IR_NOT_SIGNIFICANT` |
| FM-9 | Benchmark mismatch | Force matching equity % | `BENCHMARK_MISMATCH` |
| FM-10 | Vol annualizzata da < 1y | Flag se days < 252 | `INSUFFICIENT_HISTORY_VOL` |

---

## Implementazione: Funzione di Validazione

```python
def validate_report_integrity(report_data: dict) -> dict:
    """
    Esegue tutti i check failure mode prima di generare output.
    Returns dict con warnings e blocchi.
    """
    issues = []
    blocks = []
    
    # FM-1: CCR zero check
    for ticker, ccr in report_data['ccr'].items():
        weight = report_data['weights'][ticker]
        if weight > 0 and ccr == 0 and not report_data['ccr_valid'][ticker]:
            issues.append({
                'code': 'FM-1',
                'severity': 'ERROR',
                'message': f'CCR=0 per {ticker} con peso {weight:.1%} - covarianza non disponibile',
                'action': f'Impostare CCR[{ticker}] = "N/A"'
            })
    
    # FM-2: Correlation completeness
    nan_ratio = report_data['correlation_nan_ratio']
    if nan_ratio > 0.20 and 'diversification_stable' in report_data['verdicts']:
        issues.append({
            'code': 'FM-2',
            'severity': 'ERROR',
            'message': f'Matrice correlazioni {nan_ratio:.0%} NaN ma verdict include "diversificazione stabile"',
            'action': 'Rimuovere verdict diversificazione o qualificare con PARTIAL_DATA'
        })
    
    # ... (altri check)
    
    return {
        'valid': len(blocks) == 0,
        'issues': issues,
        'blocks': blocks
    }
```

---

*Documento generato: Gennaio 2026*
*Portfolio Analysis Engine v3.0 Specification*
