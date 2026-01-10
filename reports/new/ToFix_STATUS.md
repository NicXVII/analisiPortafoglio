# CRITICAL REVIEW - STATUS TRACKER
## Ultimo aggiornamento: 2026-01-07

---

## ✅ ISSUES RISOLTI

### Quantitative / Financial Issues
| Issue | Fix | File |
|-------|-----|------|
| VaR parametrico assume normalità | ✅ Usa VaR **storico** (quantile empirico) come default | metrics.py:321-358 |
| Zero confidence intervals | ✅ Bootstrap CI per Sharpe, CAGR, MaxDD | metrics.py:23-183 |
| No Monte Carlo stress test | ✅ Aggiunto stress test 3 scenari (base, high vol, crisis corr) | metrics.py:403-481 |
| Correlation matrix non regularizzata | ✅ **FIX #6**: Ora usa Ledoit-Wolf shrunk matrix per risk contribution | main.py:213-223 |
| Survivorship bias non gestito | ✅ Warning su tickers tematici/leveraged | data.py:36-66, main.py |
| Start date naive (years*365) | ✅ Usa `dateutil.relativedelta` per anni bisestili | data.py:120-138 |
| Risk contribution correlazioni costanti | ✅ **FIX #2**: `calculate_correlation_by_regime()` separa stress/normal | regime_detection.py |
| Rebalancing costs ignorati | ✅ **FIX #4**: Transaction cost model completo | transaction_costs.py |

### Methodological Issues
| Issue | Fix | File |
|-------|-----|------|
| "Regime detection quantitativo" falso | ✅ Trigger con prefisso "Osservato:" (non auto-detected) | analysis.py:38-95 |
| Crisis periods con boundaries arbitrarie | ✅ Date accurate S&P500 peak-to-trough | analysis.py:38-95 |
| Vol-mageddon come intero 2018 | ✅ Separato in Q4 2018 Selloff (Oct 3 - Dec 24) | analysis.py |
| Soglia 40 = ACCETTABILE | ✅ Cambiato a 50 minimum, <50 = DA_RIVEDERE | analysis.py:505-520 |
| Recovery tolerance 1% arbitraria | ✅ Cambiato a 0% (ATH effettivo) | analysis.py:353 |
| Soglie arbitrarie non documentate | ✅ **FIX #3**: `threshold_documentation.py` con fonti per ogni soglia | threshold_documentation.py |

### Interpretation Risks
| Issue | Fix | File |
|-------|-----|------|
| Correlation spike non actionable | ✅ Warning con suggerimento decorrelati | output.py (correlation stress) |
| "APPROVATO CON TRADE-OFF" maschera warnings | ✅ **FIX #7**: Verdetto con count warnings esplicito | output.py:649-735 |
| DEFAULT_GEO distorce analisi | ✅ Warning su ticker unmapped | taxonomy.py, output.py |
| "QUANT" misleading (euristiche, non ML) | ✅ **FIX #7**: Rinominato a "Rule-Based Classification" | output.py:339-341 |

### Scalability Issues
| Issue | Fix | File |
|-------|-----|------|
| No caching download data | ✅ Pickle cache con expiry 24h | data.py:73-115 |
| Assenza type safety | ✅ Dataclasses in models.py | models.py (nuovo) |
| Hardcoded ETF lists | ✅ **FIX #5**: Esternalizzato in `etf_taxonomy.json` | etf_taxonomy.json |

### Robustness / Statistical Issues
| Issue | Fix | File |
|-------|-----|------|
| No out-of-sample validation warning | ✅ **FIX #6**: Disclaimer overfitting nel verdetto | output.py:731-735 |
| Robustness score senza caveat | ✅ **FIX #6**: Docstring con overfitting warning | analysis.py:595-620 |

---

## ⏳ ISSUES IN PROGRESS / PARZIALI

### Type Safety
- ✅ Creato `models.py` con dataclasses
- ⏳ Non ancora integrato in tutto il codice (transizione graduale)
- Funzione helper `metrics_dict_to_dataclass()` per conversione

### Analysis.py Decomposition
- ✅ **FIX #1 (Phase 1)**: Estratto `regime_detection.py` (~400 righe)
- ✅ Estratto `transaction_costs.py` (~300 righe)
- ✅ Creato `threshold_documentation.py` (~450 righe)
- ⏳ Restano da estrarre: `portfolio_classifier.py`, `issue_analyzer.py`

---

## ❌ ISSUES NON ANCORA RISOLTI (Bassa priorità)

### Architectural Issues
| Issue | Priority | Note |
|-------|----------|------|
| Logica circolare taxonomy classification | LOW | Richiede redesign |
| Config mutation via global state | LOW | Anti-pattern ma funziona |
| Hardcoded data source senza astrazione | LOW | Vendor lock su Yahoo Finance |
| Output mixing print() e return | LOW | Refactoring per testabilità |

### Quantitative Issues Rimanenti
| Issue | Priority | Note |
|-------|----------|------|
| Forward fill nasconde illiquidità | LOW | Difficile da risolvere senza dati tick |
| Withholding tax non modellato | LOW | Modello base in transaction_costs.py |

### Statistical Risks Rimanenti
| Issue | Priority | Note |
|-------|----------|------|
| Rolling metrics window fisso 252 | LOW | Adaptive window complesso |
| Recovery analysis single peak | LOW | Multi-dip detection complesso |

---

## 📊 NUOVE FEATURES AGGIUNTE

### Monte Carlo Stress Test
```
📊 SCENARIO BASE (distribuzione storica)
⚠️ SCENARIO HIGH VOL (volatilità 2x)
🚨 SCENARIO CRISIS (correlazioni → 0.95)
```
- VaR 5%, VaR 1%, Median, Worst case per ogni scenario
- 500 simulazioni, 1Y horizon

### Confidence Intervals
- **CAGR**: Block bootstrap, preserva autocorrelazione
- **Sharpe**: SE analitico (Lo 2002) + bootstrap
- **MaxDD**: Block bootstrap per path-dependent

### Data Caching
- Cache locale `.data_cache/`
- Expiry 24 ore
- Riduce chiamate Yahoo Finance

### Type Safety (models.py)
- `PortfolioConfig`: validazione input
- `PortfolioMetrics`: output tipizzato
- `ConfidenceInterval`: CI strutturato
- `MarketRegime`, `Issue`, `RobustnessScore`: strutture analisi

---

## 📋 PRIORITY FIX RACCOMANDATI (prossimi step)

1. **Integrare dataclasses** nel flusso principale (main.py usa ancora dict)
2. **Split analyze_portfolio_issues()** in funzioni più piccole
3. **Aggiungere transaction cost model** per rebalancing
4. **Externalizzare ETF lists** in config JSON/YAML
5. **Refactor output.py** per return values testabili
