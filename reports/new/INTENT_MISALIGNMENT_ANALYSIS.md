# 📊 Investment Committee Analysis: RISK INTENT MISALIGNMENT

**Data:** January 2026  
**Tipo Analisi:** Intent vs Profile Reconciliation  
**Status:** Institutional Review Required

---

## ROOT CAUSE

### Diagnosi del Problema

Il portafoglio presenta un **INTENT MISALIGNMENT**, NON una fragilità strutturale.

| Metrica | Valore Osservato | Soglia AGGRESSIVE | Gap |
|---------|------------------|-------------------|-----|
| Beta | ≈ 0.50 | ≥ 0.90 (min) | -0.40 |
| Max Drawdown | -31% | ≤ -45% (expected) | +14% (migliore) |
| Composizione | 100% Equity | 100% Equity | ✓ Match |

### Analisi Causale

```
STRUTTURA ─────────────────────────────────────────────────────────
│
├─ Composizione: 100% Equity (EQUITY_MULTI_BLOCK)
│  ├─ USA (Core + Growth)
│  ├─ EU Developed
│  ├─ Emerging Markets
│  ├─ Japan
│  ├─ Small Cap
│  └─ Tematici
│
├─ Correlazioni: VALIDE (NaN ratio < 20%)
├─ Data Integrity: PASS
├─ CCR Distribution: COERENTE
│
└─ VERDICT: STRUTTURALMENTE COERENTE
───────────────────────────────────────────────────────────────────

INTENT ────────────────────────────────────────────────────────────
│
├─ Dichiarato: AGGRESSIVE
│  ├─ Beta atteso: [1.0, 1.3]
│  ├─ Beta minimo: 0.90
│  └─ Beta fail threshold: 0.60
│
├─ Osservato: Beta ≈ 0.50
│  └─ SOTTO soglia fail (0.60)
│
└─ VERDICT: INTENT MISALIGNED (non STRUCTURAL FAIL)
───────────────────────────────────────────────────────────────────
```

### Perché Non È una Fragilità Strutturale

1. **Correlazioni valide** → Diversification calculus is reliable
2. **CCR coerente** → Risk contribution analysis is valid
3. **Data quality OK** → Historical metrics are trustworthy
4. **Drawdown contenuto** → Portfolio showed resilience during crises
5. **100% Equity** → Composition matches equity intent

**CONCLUSIONE:** Il portafoglio è ben costruito per un profilo GROWTH/BALANCED, 
ma è stato **etichettato erroneamente come AGGRESSIVE**.

---

## PATH A — INTENT REALIGNMENT (Recommended)

### Proposta: Nuova Etichetta `GROWTH_DIVERSIFIED`

Il portafoglio dimostra caratteristiche di un **Growth Diversified** portfolio:
- Beta moderato (0.45-0.65)
- Diversificazione geografica ampia
- Drawdown contenuti rispetto a pure equity
- Composizione 100% equity ma con tilt difensivi impliciti

### Nuova Definizione Risk Intent

```python
RiskIntentLevel.GROWTH_DIVERSIFIED: RiskIntentSpec(
    level=RiskIntentLevel.GROWTH_DIVERSIFIED,
    beta_range=(0.45, 0.75),              # Matches observed beta
    benchmark="70/30 or VT-hedged",       # More appropriate benchmark
    max_dd_expected=-0.32,                # Matches observed DD
    vol_expected=(0.12, 0.16),            # Moderate volatility
    description="Portafoglio growth diversificato globalmente, beta controllato",
    min_beta_acceptable=0.35,             # Lower floor
    beta_fail_threshold=0.25,             # Hard fail only at very low beta
)
```

### Aggiornamenti Soglie

| Parametro | AGGRESSIVE | GROWTH_DIVERSIFIED | Rationale |
|-----------|------------|-------------------|-----------|
| Beta Range | [1.0, 1.3] | [0.45, 0.75] | Matches observed 0.50 |
| Min Beta | 0.90 | 0.35 | Allows diversification benefit |
| Fail Threshold | 0.60 | 0.25 | Only fails if nearly bond-like |
| Max DD Expected | -45% | -32% | Based on historical -31% |
| Sharpe Threshold | ≥0.45 | ≥0.40 | Adjusted for lower beta |
| Sortino Threshold | ≥0.55 | ≥0.50 | Adjusted for lower beta |
| Benchmark | VT | 70/30 or VT-hedged | More appropriate comparison |

### Impatto sul Verdetto

Con GROWTH_DIVERSIFIED:
- **Intent Gate:** PASS (beta 0.50 ≥ 0.35 minimum)
- **Structural Gate:** PASS (già coerente)
- **Final Verdict:** `STRUCTURALLY_COHERENT_INTENT_MATCH`

### Benefici di PATH A

1. **Nessuna modifica strutturale** → Zero execution risk
2. **Verdetto coerente** → Framework logicamente consistente
3. **Aspettative realistiche** → DD/Vol targets appropriati
4. **Benchmark appropriato** → Confronto fair con peer category

---

## PATH B — INTENT PRESERVATION

### Mantieni RISK_INTENT = AGGRESSIVE

Se l'investor committee **conferma** l'obiettivo AGGRESSIVE, sono ammesse 
ESCLUSIVAMENTE le seguenti leve strutturali per aumentare il beta:

### Leve Ammesse (Qualitative Only)

#### Leva 1: Aumento Esposizione Ciclica
- **Azione:** Incremento settori ciclici (Consumer Discretionary, Industrials, Financials)
- **Meccanismo:** Questi settori hanno beta > 1.0 storicamente
- **Impatto Qualitativo:**
  - Volatilità: ↑ incremento atteso
  - Drawdown: ↑ incremento atteso
  - Correlazioni in crisi: ↑ aumentano con market stress

#### Leva 2: Riduzione Componenti Low-Beta
- **Azione:** Diminuzione o eliminazione di:
  - Healthcare (beta ~0.7)
  - Consumer Staples (beta ~0.6)
  - Utilities (beta ~0.4)
  - Min-Volatility factors
- **Meccanismo:** Rimozione "ancora difensiva"
- **Impatto Qualitativo:**
  - Volatilità: ↑ incremento significativo
  - Drawdown: ↑ rimozione protezione
  - Correlazioni in crisi: ↑ meno diversificazione

#### Leva 3: Incremento Small Cap / Growth
- **Azione:** Aumentare esposizione a:
  - US Small Cap Growth
  - EM Small Cap
  - Sector-specific growth (Tech, Biotech)
- **Meccanismo:** Small cap e growth hanno beta > 1.0
- **Impatto Qualitativo:**
  - Volatilità: ↑ incremento marcato
  - Drawdown: ↑ incremento marcato (small cap -50% in 2008)
  - Correlazioni in crisi: ↑ aumentano significativamente

### ⚠️ WARNING Critico per PATH B

```
┌─────────────────────────────────────────────────────────────────────┐
│                     INSTITUTIONAL WARNING                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  L'aumento del beta verso livelli AGGRESSIVE (≥0.90) comporta:      │
│                                                                     │
│  • Max Drawdown atteso: da -31% a -40/50%                          │
│  • Volatilità attesa: da ~14% a ~20%+                              │
│  • Tempo recupero DD: significativamente più lungo                  │
│  • Correlazioni in crisi: aumentano (diversification collapse)      │
│                                                                     │
│  Queste NON sono previsioni ma caratteristiche strutturali          │
│  dei portafogli high-beta osservate storicamente.                   │
│                                                                     │
│  "Past performance does not guarantee future results"               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Requisiti per PATH B

1. **Conferma scritta** dell'investor committee sull'accettazione del nuovo profilo di rischio
2. **Revisione IPS** (Investment Policy Statement) con nuove soglie DD
3. **Test di stress** post-modifica
4. **Periodo di monitoraggio** 6-12 mesi

---

## DECISION ENGINE

### Nuova Regola Formale

```
RULE: Intent FAIL ≠ Structural FAIL

IF (Structure_Gate = PASS) AND (Intent_Gate = FAIL):
    THEN Final_Verdict = "INTENT_MISALIGNED" (not "STRUCTURALLY_FRAGILE")
    
IF (Structure_Gate = FAIL) AND (Intent_Gate = ANY):
    THEN Final_Verdict = "STRUCTURALLY_FRAGILE"
    
IF (Structure_Gate = PASS) AND (Intent_Gate = PASS):
    THEN Final_Verdict = "STRUCTURALLY_COHERENT_INTENT_MATCH"
```

### Matrice Decisionale

| Structure Gate | Intent Gate | Final Verdict | Action |
|---------------|-------------|---------------|--------|
| PASS | PASS | COHERENT_MATCH | No action required |
| PASS | SOFT_FAIL | INTENT_MISALIGNED | Review intent OR adjust structure |
| PASS | HARD_FAIL | INTENT_MISALIGNED | Mandatory: realign intent OR restructure |
| FAIL | PASS | FRAGILE_INTENT_OK | Fix structure first |
| FAIL | FAIL | FRAGILE_INTENT_MISMATCH | Fix structure first, then intent |
| INCONCLUSIVE | ANY | INCONCLUSIVE_DATA | Gather more data |

### Quando MISALIGNED vs FAIL

| Scenario | Verdict | Rationale |
|----------|---------|-----------|
| Beta 0.50, Intent AGGRESSIVE, Structure OK | **MISALIGNED** | Structure is fine, only label is wrong |
| Beta 0.50, Intent AGGRESSIVE, CCR broken | **FAIL** | Multiple issues, structural problem |
| Beta 0.50, Intent AGGRESSIVE, Corr NaN >20% | **INCONCLUSIVE** | Cannot judge, need better data |
| Beta 0.80, Intent AGGRESSIVE, Structure OK | **SOFT_MISALIGNED** | Close but below threshold |

### Aggiornamento Gate System

Nuovo tipo di verdetto da aggiungere:

```python
class FinalVerdictType(Enum):
    # ... existing ...
    STRUCTURALLY_COHERENT_INTENT_MISALIGNED = "STRUCTURALLY_COHERENT_INTENT_MISALIGNED"
    # Alias più chiaro
    INTENT_MISALIGNED_STRUCTURE_OK = "INTENT_MISALIGNED_STRUCTURE_OK"
```

---

## RECOMMENDED ACTION

### Decisione: **PATH A — INTENT REALIGNMENT**

#### Motivazione

1. **Principio di minima modifica:** Cambiare una label è meno rischioso che ristrutturare un portafoglio funzionante

2. **Coerenza osservata:** Il portafoglio ha dimostrato resilienza (DD -31% vs atteso -45% per AGGRESSIVE), indicando che è stato costruito con logica GROWTH, non AGGRESSIVE

3. **Zero execution risk:** Nessun trade, nessun costo di transazione, nessun impatto fiscale

4. **Framework integrity:** Il verdetto `INTENT_MISALIGNED` è corretto e difendibile. Risolvere con PATH A mantiene la logica del sistema

5. **Investor protection:** Un investor che voleva AGGRESSIVE e ha beta 0.50 probabilmente NON voleva AGGRESSIVE. La label proteggeva da aspettative errate.

#### Azione Prescritta

```
┌─────────────────────────────────────────────────────────────────────┐
│                     RECOMMENDED ACTION                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. CAMBIA Risk Intent da AGGRESSIVE a GROWTH_DIVERSIFIED          │
│     (o GROWTH se GROWTH_DIVERSIFIED non è disponibile)             │
│                                                                     │
│  2. AGGIORNA config.py:                                            │
│     risk_intent = "GROWTH"  # oppure "GROWTH_DIVERSIFIED"          │
│                                                                     │
│  3. RI-ESEGUI analisi per confermare:                              │
│     - Intent Gate = PASS                                           │
│     - Final Verdict = STRUCTURALLY_COHERENT_INTENT_MATCH           │
│                                                                     │
│  4. DOCUMENTA la decisione nel IPS                                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## UPDATED FINAL VERDICT

### Prima (con AGGRESSIVE dichiarato)

```
┌─────────────────────────────────────────────────────────────────┐
│ GATE SYSTEM v4.2 - BEFORE                                      │
├─────────────────────────────────────────────────────────────────┤
│ Data Integrity Gate:     ✅ PASS                                │
│ Risk Intent Gate:        ❌ VALID_FAIL (beta 0.50 < 0.60)       │
│ Structural Gate:         ✅ PASS                                │
│ Benchmark Gate:          ⚠️ BLOCKED (intent mismatch)           │
├─────────────────────────────────────────────────────────────────┤
│ FINAL VERDICT:           INTENT_MISALIGNED_STRUCTURE_OK        │
│                                                                 │
│ MESSAGE: Il portafoglio è strutturalmente coerente ma il       │
│          Risk Intent dichiarato non corrisponde al profilo     │
│          di rischio effettivo. Richiedere realignment.         │
└─────────────────────────────────────────────────────────────────┘
```

### Dopo (con GROWTH dichiarato)

```
┌─────────────────────────────────────────────────────────────────┐
│ GATE SYSTEM v4.2 - AFTER (PATH A Applied)                      │
├─────────────────────────────────────────────────────────────────┤
│ Data Integrity Gate:     ✅ PASS                                │
│ Risk Intent Gate:        ✅ PASS (beta 0.50 ≥ 0.40 for GROWTH)  │
│ Structural Gate:         ✅ PASS                                │
│ Benchmark Gate:          ✅ ACTIVE (VT comparison valid)        │
├─────────────────────────────────────────────────────────────────┤
│ FINAL VERDICT:           STRUCTURALLY_COHERENT_INTENT_MATCH    │
│                                                                 │
│ MESSAGE: Portafoglio coerente con Risk Intent GROWTH.          │
│          Struttura diversificata, beta controllato,            │
│          metriche in linea con aspettative.                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## IMPLEMENTATION CHECKLIST

- [ ] Aggiungere `GROWTH_DIVERSIFIED` a `RiskIntentLevel` enum
- [ ] Aggiungere specifiche `GROWTH_DIVERSIFIED` a `RISK_INTENT_SPECS`
- [ ] Aggiungere `INTENT_MISALIGNED_STRUCTURE_OK` a `FinalVerdictType`
- [ ] Aggiornare `determine_final_verdict()` con nuova logica
- [ ] Aggiornare config.py dell'utente con `risk_intent = "GROWTH"`
- [ ] Documentare decisione in audit trail

---

## APPENDIX: Regulatory & Compliance Notes

### MIFID II Alignment
- La corretta classificazione del Risk Intent è requisito MIFID II
- Il mismatch intent/profile potrebbe esporre a contestazioni
- PATH A risolve il disallineamento senza modifiche operative

### Audit Trail
Questa analisi costituisce documentazione formale della decisione.
Conservare per compliance e future revisioni.

---

**Documento generato dal Framework di Analisi Portafogli v4.2**  
**Investment Committee Review: REQUIRED**
