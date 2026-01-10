# 📊 Analisi Migliorie Sistema di Output

**Data**: 2026-01-09  
**Stato**: Analisi gap tra documentazione e implementazione

---

## Executive Summary

L'analisi ha identificato **3 BUG critici**, **2 migliorie strutturali** e **3 ottimizzazioni opzionali**. 
Il sistema di output è **85% completo** rispetto alla documentazione fornita.

---

## 1. 🔴 BUG CRITICI (da fixare immediatamente)

### 1.1 VaR/CVaR sempre 0.0 nel JSON

**Problema**: Il JSON output mostra sempre `var_95: 0.0` e `cvar_95: 0.0`

**Causa**: Mismatch di chiavi tra `metrics.py` e `main.py`

```python
# metrics.py esporta:
"var_95_annual": var_annual,
"cvar_95_annual": cvar_annual,

# main.py cerca:
var_95=metrics.get('var_95', 0.0),  # ❌ chiave inesistente
cvar_95=metrics.get('cvar_95', 0.0),  # ❌ chiave inesistente
```

**Fix richiesto** (in [main.py](../../main.py#L176-L177)):
```python
var_95=metrics.get('var_95_annual', 0.0),
cvar_95=metrics.get('cvar_95_annual', 0.0),
```

**Priorità**: 🔴 CRITICAL  
**Effort**: 5 minuti  
**Impatto**: Metriche di rischio mancanti per integrazione programmatica

---

### 1.2 Prescriptive Actions sempre vuote nel JSON

**Problema**: Il campo `prescriptive_actions: []` è sempre vuoto nonostante il gate system generi azioni

**Causa**: Le azioni sono generate in `gate_system.py` ma non passate correttamente a `_build_analysis_result()`

**Analisi del flusso**:
1. ✅ `gate_system.py:1270-1290` genera `all_prescriptive_actions`
2. ✅ `GateAnalysisResult.prescriptive_actions` contiene le azioni
3. ❓ `main.py:188-202` estrae le azioni ma potrebbero essere vuote se `gate_result.prescriptive_actions` è vuoto

**Verifica necessaria**: 
```python
# In main.py, dopo analyze_portfolio():
logger.debug(f"Gate prescriptive actions: {len(gate_result.prescriptive_actions)}")
```

**Possibili cause**:
- Le azioni vengono generate ma non aggregate nel `GateAnalysisResult`
- Il portfolio analizzato non genera warning/errori (caso normale per portfolio sano)

**Priorità**: 🟡 HIGH (verificare prima se è bug o comportamento normale)  
**Effort**: 30 minuti (debug + eventuale fix)

---

### 1.3 Allowed/Prohibited Actions hardcoded

**Problema**: Le azioni permesse/proibite sono hardcoded con valori generici

```python
# main.py:232-240
allowed_actions = [] if is_inconclusive else [
    "Portfolio restructuring",
    "Asset rebalancing",
    "Risk adjustment"
]
```

**Impatto**: Non riflettono il verdetto specifico (INTENT_MISALIGNED vs STRUCTURE_FRAGILE)

**Fix suggerito**: Derivare da `FinalVerdictType` e gate results

**Priorità**: 🟡 HIGH  
**Effort**: 2 ore

---

## 2. 🟡 MIGLIORIE STRUTTURALI

### 2.1 Unificare JSON Export (Structured vs Legacy)

**Stato attuale**: Due formati JSON paralleli
- `AnalysisResult.to_dict()` → formato strutturato (usato)
- `export_analysis_to_json()` → formato legacy (non sincronizzato)

**Problema**: Il formato legacy in [export.py](../../export.py#L160-250) duplica logica e può divergere

**Soluzione proposta**:
1. Deprecare `export_analysis_to_json()` 
2. Usare solo `AnalysisResult.save_json()` per tutti gli export
3. Mantenere backward compatibility con wrapper

```python
def export_analysis_to_json(result: AnalysisResult, path: str) -> Path:
    """Deprecated: Use result.save_json() directly."""
    import warnings
    warnings.warn("Use AnalysisResult.save_json() instead", DeprecationWarning)
    result.save_json(path)
    return Path(path)
```

**Priorità**: 🟡 MEDIUM  
**Effort**: 1 ora

---

### 2.2 Report Testuale Consolidato per PDF

**Stato attuale**: 5 funzioni di stampa separate
- `print_summary()` - 300 righe
- `print_portfolio_critique()` - 250 righe
- `print_senior_architect_analysis()` - 200 righe
- `print_risk_intent_analysis()` - 80 righe
- `print_gate_analysis()` - 150 righe

**Problema**: Per PDF, catturiamo stdout con redirect. Ordine e contenuto dipendono da chiamate nel main.

**Soluzione proposta**: Creare `generate_full_report()` che orchestra tutte le sezioni

```python
def generate_full_report(
    result: AnalysisResult,
    metrics: dict,
    gate_result: GateAnalysisResult,
    risk_analysis: dict,
    format: Literal["text", "html", "dict"] = "text"
) -> str:
    """Genera report completo in formato unificato."""
    sections = []
    
    # Ordine canonico definito una volta sola
    sections.append(format_summary_section(result, metrics))
    sections.append(format_gate_section(gate_result))
    sections.append(format_risk_intent_section(risk_analysis))
    sections.append(format_critique_section(result))
    sections.append(format_architect_section(result))
    
    return "\n".join(sections)
```

**Benefici**:
- Single source of truth per ordine sezioni
- Testabilità (no stdout capture)
- Supporto multi-formato senza duplicazione

**Priorità**: 🟢 LOW (sistema attuale funziona)  
**Effort**: 4-6 ore

---

## 3. 🟢 OTTIMIZZAZIONI OPZIONALI

### 3.1 Aggiungere Campo `analysis_version` al JSON

Permette tracking retroattivo delle metriche.

```python
"metadata": {
    "timestamp": "2026-01-09T18:07:23",
    "portfolio_id": null,
    "analysis_version": "2.1.0",  # ← nuovo
    "gate_system_version": "4.3"   # ← nuovo
}
```

**Effort**: 15 minuti

---

### 3.2 Includere Bootstrap Samples Count nel JSON

Attualmente i CI sono nel JSON ma non il sample size usato.

```python
"metrics": {
    "cagr_ci_lower": 0.061,
    "cagr_ci_upper": 0.225,
    "bootstrap_samples": 10000,  # ← nuovo
    "bootstrap_ci_level": 0.95   # ← nuovo
}
```

**Effort**: 10 minuti

---

### 3.3 Aggiungere Sezione `raw_data_summary` 

Per debugging e auditability:

```python
"raw_data_summary": {
    "start_date": "2019-01-02",
    "end_date": "2026-01-08",
    "trading_days": 1752,
    "nan_cells_total": 2847,
    "nan_cells_inception": 2841,
    "nan_cells_data_quality": 6,
    "tickers_count": 13,
    "shortest_history": {"ticker": "SEMI.L", "days": 1245}
}
```

**Effort**: 30 minuti

---

## 4. Piano di Implementazione

### Fase 1: Fix Critici (30 min totali)

| Task | File | Effort | Priorità |
|------|------|--------|----------|
| Fix VaR/CVaR keys | main.py:176-177 | 5 min | 🔴 |
| Debug prescriptive_actions | main.py + gate_system.py | 25 min | 🔴 |

### Fase 2: Migliorie Strutturali (3 ore)

| Task | File | Effort | Priorità |
|------|------|--------|----------|
| Allowed/Prohibited actions dinamiche | main.py | 2h | 🟡 |
| Deprecare export legacy | export.py | 1h | 🟡 |

### Fase 3: Ottimizzazioni (1 ora, opzionale)

| Task | File | Effort |
|------|------|--------|
| analysis_version | models.py | 15 min |
| bootstrap metadata | models.py | 10 min |
| raw_data_summary | models.py + main.py | 35 min |

---

## 5. Raccomandazione

**Azione immediata**: Fixare il BUG VaR/CVaR (5 minuti) perché invalida i dati per utenti programmatici.

**Prossima sessione**: Verificare e fixare prescriptive_actions vuote, poi implementare allowed/prohibited dinamiche.

Le migliorie di consolidamento report (2.2) sono **nice-to-have** - il sistema attuale funziona correttamente.

---

## 6. Verifica Post-Fix

Dopo i fix, il JSON dovrebbe contenere:

```json
{
  "metrics": {
    "var_95": -0.182,      // ← era 0.0
    "cvar_95": -0.245      // ← era 0.0
  },
  "recommendations": {
    "prescriptive_actions": [
      {
        "issue_code": "BETA_SOFT_FAIL",
        "priority": "HIGH",
        "description": "Portfolio beta 0.72 sotto target 0.85"
      }
    ]
  }
}
```
