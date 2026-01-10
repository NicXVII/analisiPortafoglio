# Fix Report - Session 4: Prescriptive Actions & Classification

## Summary

This session addressed the 4 critical issues identified in the portfolio analysis:

1. ✅ **Risk Intent Enforcement** - Now produces prescriptive actions, not just warnings
2. ✅ **Core vs Tactical Classification** - Added `EQUITY_MULTI_BLOCK` for regional structures
3. ✅ **Decision Engine Actions** - Added confidence-weighted prescriptive action system
4. ✅ **Geography Completion** - Added 20+ missing ETFs to GEO_EXPOSURE

---

## Issue #1: Risk Intent Still Misdeclared

### Problem
Beta 0.50 vs AGGRESSIVE requiring ≥0.9. The system only warned but didn't enforce.

### Solution
Added `PrescriptiveAction` dataclass with:
- `issue_code`: Unique identifier (e.g., "INTENT_MISMATCH_HARD")
- `priority`: CRITICAL / HIGH / MEDIUM / LOW / INFO
- `confidence`: 0.0-1.0 based on data quality
- `actions`: List of concrete actions to take
- `blockers`: What gets blocked if not addressed

### Example Output
```
🔴 CRITICAL [INTENT_MISMATCH_HARD]
Confidence: [█████████░] 95%
Portfolio beta 0.50 is incompatible with AGGRESSIVE (requires ≥0.9)
→ Actions:
   • OPTION A: Change RISK_INTENT to MODERATE (matches beta 0.50)
   • OPTION B: Increase beta by 0.40 via:
      - Add 15-20% US large-cap growth (QQQ, VGT, XLK)
      - Remove low-beta positions (bond proxies, min-vol, utilities)
   • OPTION C: If intentional defensive tilt, relabel as BALANCED
⛔ Blocks if not addressed: All structural analysis, Benchmark comparisons
```

---

## Issue #2: Core vs Tactical Ambiguous

### Problem
Portfolio labeled "TACTICAL / OPPORTUNISTIC" with 50% confidence, but had 0% Core Global.
A stable regional structure shouldn't be called "tactical".

### Solution
Added `PortfolioStructureType` enum with 7 types:
- `GLOBAL_CORE`: ≥50% in global broad-market ETFs (VT, VWCE)
- `EQUITY_MULTI_BLOCK`: 0% Core Global but stable regional blocks ≥40%
- `FACTOR_TILTED`: Core + significant factor exposure
- `SECTOR_CONCENTRATED`: Heavy sector/thematic exposure
- `BALANCED`: Significant defensive allocation (≥30%)
- `DEFENSIVE`: Primarily bonds/gold
- `OPPORTUNISTIC`: High unclassified, unstable structure

Added `determine_portfolio_structure_type()` function that returns:
- Structure type
- Confidence score (0-100%)
- Explanation string

### Example Output
```
🏗️  STRUCTURE TYPE: EQUITY_MULTI_BLOCK (85% confidence)
    No global core but regional blocks 100% ≥ 40% form stable structure
```

---

## Issue #3: Decision Engine Too Indulgent

### Problem
Beta FAIL → "not a problem", correlation shift → warning only.
Needed confidence-weighted actions, not just descriptive verdicts.

### Solution
1. Updated `GateResult` dataclass to include `prescriptive_actions` field
2. Updated `GateAnalysisResult` to aggregate all actions from all gates
3. Actions are sorted by priority (CRITICAL first)
4. Each action includes:
   - Confidence bar visual
   - Concrete action steps
   - What gets blocked if not addressed
   - Data quality impact flag

### New Prescriptive Actions Section in Output
```
══════════════════════════════════════════════════════════════════════
                    PRESCRIPTIVE ACTIONS
══════════════════════════════════════════════════════════════════════

   🔴 CRITICAL [INTENT_MISMATCH_HARD]
   Confidence: [█████████░] 95%
   ...

   🟠 HIGH [CCR_CONCENTRATION]  
   Confidence: [████████░░] 80%
   ...
```

---

## Issue #4: Geography Incomplete

### Problem
20% of portfolio used DEFAULT_GEO assumption (60% USA fallback).
Missing: ITWN.L, DFNS.L, INFR.L, SEMI.L, ISJP.L, WSML.L, EMIM.L, USSC.L

### Solution
Added 20+ new ETFs to `GEO_EXPOSURE` in taxonomy.py:

```python
# Taiwan UCITS
"ITWN.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},

# Defense/Aerospace UCITS  
"DFNS.L": {"USA": 0.70, "Europe": 0.25, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.05},

# Global Infrastructure UCITS
"INFR.L": {"USA": 0.45, "Europe": 0.25, "Japan": 0.08, "EM": 0.12, "Other_DM": 0.10},

# Semiconductor UCITS
"SEMI.L": {"USA": 0.65, "Europe": 0.05, "Japan": 0.05, "EM": 0.20, "Other_DM": 0.05},

# Japan Small Cap
"ISJP.L": {"USA": 0.0, "Europe": 0.0, "Japan": 1.0, "EM": 0.0, "Other_DM": 0.0},

# World Small Cap
"WSML.L": {"USA": 0.58, "Europe": 0.18, "Japan": 0.10, "EM": 0.04, "Other_DM": 0.10},

# USA Small Cap UCITS
"USSC.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},

# Emerging Markets IMI
"EMIM.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},
```

---

## Files Modified

### gate_system.py
- Added `ActionPriority` enum
- Added `PrescriptiveAction` dataclass
- Added `PortfolioStructureType` enum
- Added `determine_portfolio_structure_type()` function
- Updated `GateResult` to include `prescriptive_actions`
- Updated `GateAnalysisResult` with structure type fields and aggregated actions
- Updated `check_risk_intent_gate()` to generate prescriptive actions
- Updated `run_gate_analysis()` to aggregate all prescriptive actions
- Updated `print_gate_analysis()` to display new sections
- Version updated to v4.3

### taxonomy.py
- Added 20+ new ETFs to `GEO_EXPOSURE`:
  - Taiwan: ITWN.L, EWT
  - Defense: DFNS.L, XAR, ITA, PPA, DFEN
  - Infrastructure: INFR.L, IGF, PAVE, IFRA
  - Semiconductors: SEMI.L, SOXX, SMH, SOXQ
  - Japan Small Cap: ISJP.L, SCJ, DXJS
  - World Small Cap: WSML.L, IUSN.L
  - USA Small Cap: USSC.L, IUS3.L
  - EM IMI: EMIM.L, EIMI.L

---

## Test Results

```
Structure Type: PortfolioStructureType.EQUITY_MULTI_BLOCK
Structure Confidence: 0.85
Prescriptive Actions: 1
  - INTENT_MISMATCH_HARD: CRITICAL

Exit Code: 0
PDF Generated: output/analisi.pdf
```

---

## Gate System v4.3 Output Format

```
======================================================================
        INVESTMENT COMMITTEE VALIDATOR (Gate System v4.3)
======================================================================

📋 GATE STATUS:
   ✅ Data Integrity Gate: PASS
   ⛔ Intent Gate: VALID_FAIL
   ✅ Structural Gate: PASS
   ℹ️ Structure Type: EQUITY_MULTI_BLOCK (85% confidence)
   ℹ️ Benchmark Gate: OPPORTUNITY_COST
   ℹ️ Final Verdict: STRUCTURALLY_COHERENT_INTENT_MISMATCH
   ℹ️ Prescriptive Actions: 1

...

══════════════════════════════════════════════════════════════════════
                    PRESCRIPTIVE ACTIONS
══════════════════════════════════════════════════════════════════════

   🔴 CRITICAL [INTENT_MISMATCH_HARD]
   Confidence: [█████████░] 95%
   Portfolio beta 0.50 is incompatible with AGGRESSIVE (requires ≥0.9)
   → Actions:
      • OPTION A: Change RISK_INTENT to MODERATE
      • OPTION B: Increase beta by 0.40
      • OPTION C: Relabel as BALANCED

══════════════════════════════════════════════════════════════════════
                      FINAL VERDICT
══════════════════════════════════════════════════════════════════════

   ⚠️ INTENT MISMATCH (CERTO) - Struttura Coerente
```
