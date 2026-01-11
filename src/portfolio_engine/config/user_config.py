"""
Portfolio Configuration
=======================
Configura qui il tuo portafoglio e le opzioni di analisi.
Modifica questo file senza toccare main.py.
"""

# =========================
# CENTRALIZED SAMPLE SIZE REQUIREMENTS (Fix C6)
# =========================
# Single source of truth for minimum sample sizes across all modules.
# Rationale: Ensures statistical validity and consistent behavior.

SAMPLE_SIZE_CONFIG = {
    # Correlation requirements
    'correlation_min_observations': 60,      # Minimum overlapping days for correlation
    
    # Beta calculation requirements
    'beta_min_trading_days': 60,             # Minimum trading days for beta estimation
    'beta_min_years': 3.0,                   # Minimum years of data for reliable beta
    
    # Crisis analysis requirements  
    'crisis_min_days': 30,                   # Minimum days to consider a crisis period valid
    
    # VaR/Risk metric requirements
    'var_min_observations': 252,             # Minimum trading days for VaR (1 year)
    
    # Regime detection requirements
    'regime_min_days': 252,                  # Minimum days for regime analysis
    
    # Monte Carlo simulation
    'monte_carlo_simulations': 500,          # Number of MC simulations (was hardcoded)
    'bootstrap_iterations': 200,             # Bootstrap iterations for SE estimation
}


# =========================
# GATE SYSTEM THRESHOLDS (Fix M1-M2)
# =========================
# Centralized thresholds for Gate System validation.
# Moving from hardcoded values in gate_system.py for maintainability.

GATE_THRESHOLDS = {
    # Data quality thresholds
    'nan_ratio_warning': 0.10,               # 10% NaN → YELLOW warning
    'nan_ratio_fail': 0.20,                  # 20% NaN → RED fail
    
    # Crisis Correlation Ratio (CCR) thresholds
    'ccr_normal_max': 1.5,                   # CCR ≤ 1.5 → Normal behavior
    'ccr_warning_max': 2.5,                  # CCR 1.5-2.5 → Elevated
    # CCR > 2.5 → High correlation spike (potential contagion)
    
    # Correlation confidence thresholds
    'confidence_high': 0.8,                  # Above this → high confidence
    'confidence_medium': 0.5,                # Between medium-high → medium confidence
    # Below confidence_medium → low confidence
    
    # Beta deviation thresholds (from intent)
    'beta_deviation_warning': 0.3,           # |beta - expected| > 0.3 → warning
    'beta_deviation_fail': 0.5,              # |beta - expected| > 0.5 → fail
}


# =========================
# STATISTICAL PARAMETERS (Fix C3-C4)
# =========================
# Parameters for risk metrics calculation.
# Documented assumptions and limitations.

STATISTICAL_PARAMS = {
    # VaR calculation
    'var_confidence_levels': [0.95, 0.99],   # Standard VaR confidence levels
    'var_time_horizons': [1, 5, 10, 21],     # Days: daily, weekly, bi-weekly, monthly
    
    # Note: sqrt(T) scaling assumes returns are IID and normally distributed.
    # This is known to underestimate tail risk during crises.
    # See LIMITATIONS_AND_ASSUMPTIONS in documentation.
    'var_scaling_assumption': 'sqrt_t',
    
    # Expected Shortfall (CVaR)
    'cvar_enabled': True,                    # Calculate ES alongside VaR
    
    # Return distribution warnings
    'normality_warning_threshold': 0.05,     # Jarque-Bera p-value threshold
}


# =========================
# OUTPUT CONFIGURATION (v3.1)
# =========================
# Configura il tipo di report da generare.
#
# Valori ammessi:
#   "retail"       - Report conciso per cliente finale (1 pagina)
#                    Solo metriche chiave + verdict + azione raccomandata
#                    Target: investitore retail che vuole decisione rapida
#   
#   "professional" - Report completo per quant analyst / risk manager
#                    Include metodologia, correlazioni raw, diagnostics
#                    + JSON strutturato per ML ingestion
#                    Target: professionisti finanziari, feeding IA
#
# DEFAULT: "retail" per uso ripetuto real-world
OUTPUT_MODE = "professional"  # Options: "retail" | "professional"

# =========================
# RISK INTENT DECLARATION (v3.0)
# =========================
# OBBLIGATORIO: Dichiara il livello di rischio che il portafoglio INTENDE assumere.
# Questo determina il benchmark di confronto e le soglie per i verdetti.
#
# Valori ammessi:
#   CONSERVATIVE       - Beta 0.3-0.5,   benchmark 40/60, max DD -15%, vol  6-10%
#   MODERATE           - Beta 0.5-0.8,   benchmark 60/40, max DD -25%, vol 10-14%
#   GROWTH_DIVERSIFIED - Beta 0.45-0.75, benchmark 70/30, max DD -32%, vol 12-16%  ⭐ FITS THIS PORTFOLIO
#   GROWTH             - Beta 0.8-1.0,   benchmark VT,    max DD -35%, vol 14-18%
#   AGGRESSIVE         - Beta 1.0-1.3,   benchmark VT,    max DD -45%, vol 18-22%
#   HIGH_BETA          - Beta 1.3-2.0,   benchmark AVUV,  max DD -55%, vol 22-30%
#
# 👉 QUESTO PORTFOLIO: Beta ~0.50 → usa GROWTH_DIVERSIFIED (non AGGRESSIVE!)
# ⚠️ Senza questo, il motore assume GROWTH e potrebbe penalizzare scelte consapevoli.
RISK_INTENT = "GROWTH_DIVERSIFIED"  # Beta 0.45-0.75, diversified globally

# =========================
# PORTFOLIO ALLOCATION
# =========================
PORTFOLIO = {
    # =========================
    # USA – LARGE CAP GROWTH
    # =========================
    "CSPX.L": 0.22,   # S&P 500 (growth core, beta driver)
    
    # =========================
    # USA – SMALL CAP
    # =========================
    "USSC.L": 0.125,   # USA Small Cap (beta + convexity)
    
    # =========================
    # EUROPA
    # =========================
    "IMEU.L": 0.12,   # Europa large/mid cap
    "CUKS.L": 0.04,   # UK Small Cap
    "CUKX.L": 0.02,   # UK Large Cap
    
    # =========================
    # GIAPPONE
    # =========================
    "SJPA.L": 0.06,   # Japan Large Cap
    "ISJP.L": 0.03,   # Japan Small Cap
    
    # =========================
    # EMERGING MARKETS
    # =========================
    "EMIM.L": 0.12,   # EM Broad (growth + beta)
    "ITWN.L": 0.05,   # Taiwan (semiconductors, convexity)
    
    # =========================
    # GLOBAL SMALL CAP
    # =========================
    "WSML.L": 0.05,   # Global Small Cap (size premium)
    
    # =========================
    # TEMATICI – GROWTH / AI / DEFENCE
    # =========================
    "SEMI.L": 0.04,   # Semiconductors
    "DFNS.L": 0.08,   # Defence (geopolitical growth)
    "INFR.L": 0.04    # Infrastructure / AI backbone
}

                                                                                                                










# =========================
# ANALYSIS PARAMETERS
# =========================
ANALYSIS = {
    "years_history": 20,          # Anni di storico da scaricare
    "start_date": None,           # Data inizio (es. "2020-01-01"), None = auto
    "end_date": None,             # Data fine, None = oggi
    "risk_free_annual": 0.02,     # Tasso risk-free annuale (2%)
    "rebalance": "ME",            # Frequenza ribilanciamento: None, "ME" (mensile), "QE" (trimestrale)
    "var_confidence": 0.95,       # Livello di confidenza VaR (95%)
}

# =========================
# EXPORT OPTIONS
# =========================
EXPORT = {
    "enabled": False,                   # True = salva file, False = solo visualizzazione
    "output_dir": "./output",           # Directory di output
    "create_zip": True,                 # Crea archivio ZIP con tutti i file
    "delete_files_after_zip": True,     # Elimina file singoli dopo creazione ZIP
    "formats": ["csv", "xlsx", "json"], # Formati: csv, xlsx, json
    "export_charts": True,              # Esporta grafici
    "chart_format": "png",              # png o pdf
    "export_html_report": True,         # Report HTML completo
}


# =========================
# CONFIG BUILDER (non modificare)
# =========================
def get_config() -> dict:
    """
    Costruisce la configurazione completa per main.py.
    Non modificare questa funzione.
    """
    tickers = list(PORTFOLIO.keys())
    weights = list(PORTFOLIO.values())
    
    # Validazione
    total = sum(weights)
    if abs(total - 1.0) > 0.001:
        print(f"⚠️  ATTENZIONE: I pesi sommano a {total:.2%}, non 100%!")
        print(f"   I pesi verranno normalizzati automaticamente.")
    
    # Validazione Risk Intent
    valid_intents = ["CONSERVATIVE", "MODERATE", "BALANCED", "GROWTH", "GROWTH_DIVERSIFIED", "AGGRESSIVE", "HIGH_BETA"]
    risk_intent = RISK_INTENT.upper() if RISK_INTENT else "GROWTH"
    if risk_intent not in valid_intents:
        print(f"⚠️  Risk Intent '{RISK_INTENT}' non valido. Uso GROWTH come default.")
        risk_intent = "GROWTH"
    
    return {
        "tickers": tickers,
        "weights": weights,
        "risk_intent": risk_intent,  # v3.0: Risk Intent Declaration
        **ANALYSIS,
        "export": EXPORT,
    }


# =========================
# PORTFOLIO PRESETS (opzionale)
# =========================
# Puoi definire configurazioni alternative qui e cambiarle rapidamente

PRESETS = {
    "aggressive": {
        "VWCE.DE": 0.60,
        "EIMI.L": 0.15,
        "DFEN.DE": 0.10,
        "NUKL.DE": 0.10,
        "INFR.L": 0.05,
    },
    "conservative": {
        "VWCE.DE": 0.50,
        "EIMI.L": 0.10,
        "AGGH.L": 0.30,  # Bond aggregate
        "INFR.L": 0.10,
    },
    "all_world_only": {
        "VWCE.DE": 1.00,
    },
}


# =========================
# EXCEPTION OVERRIDE SYSTEM (Production Readiness - Issue #1)
# =========================
"""
INCONCLUSIVE VERDICT OVERRIDE MECHANISM
========================================

Starting from v4.3, the Gate System enforces INCONCLUSIVE verdicts by raising exceptions
that block analysis execution. This ensures institutional compliance and explicit
acknowledgment of data quality or structural issues.

WHEN OVERRIDES ARE NEEDED:
---------------------------
The system may raise INCONCLUSIVEVerdictError in three scenarios:

1. INCONCLUSIVE_DATA_FAIL (DataIntegrityError)
   - Trigger: Correlation matrix NaN ratio > 20%
   - Cause: Insufficient overlapping data between assets
   - Override needed: When portfolio is in construction phase or using new assets

2. INCONCLUSIVE_INTENT_DATA (BetaWindowError)
   - Trigger: Beta calculation window < 3 years
   - Cause: Recent portfolio inception or asset changes
   - Override needed: When accepting preliminary beta estimates

3. INTENT_FAIL_STRUCTURE_INCONCLUSIVE (IntentFailStructureInconclusiveError)
   - Trigger: Intent misalignment detected but structural analysis inconclusive
   - Cause: Intent FAIL certain but high NaN ratio prevents structural verdict
   - Override needed: When intent fail is acknowledged but full analysis blocked


HOW TO APPLY OVERRIDES:
------------------------
Import UserAcknowledgment and create override object:

from datetime import datetime
from portfolio_engine.utils.exceptions import UserAcknowledgment

override = UserAcknowledgment(
    verdict_type='INCONCLUSIVE_DATA_FAIL',     # Must match exception type
    authorized_by='John Doe',                   # Person authorizing override
    reason='Portfolio under construction - accepting preliminary analysis',
    date=datetime.now(),
    expiry_date=None                            # Optional: auto-expire override
)

Then pass to analysis:

from portfolio_engine.core.main_legacy import run_analysis_to_pdf
run_analysis_to_pdf(CONFIG, override=override)


OVERRIDE VALIDATION:
--------------------
All overrides are validated for:
- Required fields (verdict_type, authorized_by, reason, date)
- Non-empty strings (no blank authorizations)
- Verdict type matching (must match raised exception)
- Expiry date (if set, must be in the future)

Invalid overrides will raise ValueError and block execution.


AUDIT TRAIL:
------------
All overrides are logged to 'gate_override_log.json' with:
- Timestamp and authorization details
- Verdict type and reason
- Portfolio snapshot (tickers, weights)
- Expiry date (if applicable)

Use get_override_history() to review past overrides.


EXAMPLE - Portfolio Under Construction:
----------------------------------------
CONFIG = {
    'portfolio': {
        'SPY': 0.40,    # 3 years of data
        'NEWETF': 0.60  # Only 6 months of data (NEW!)
    },
    'risk_intent': 'GROWTH',
    'benchmark': 'SPY'
}

# Analysis will fail with DataIntegrityError due to NEWETF short history
# Override required:

from datetime import datetime, timedelta
from portfolio_engine.utils.exceptions import UserAcknowledgment
from portfolio_engine.core.main_legacy import run_analysis_to_pdf

override = UserAcknowledgment(
    verdict_type='INCONCLUSIVE_DATA_FAIL',
    authorized_by='Portfolio Manager',
    reason='NEWETF recently added - accepting reduced correlation confidence',
    date=datetime.now(),
    expiry_date=datetime.now() + timedelta(days=90)  # Expires in 3 months
)

run_analysis_to_pdf(CONFIG, override=override)
# Analysis proceeds with override logged to audit trail


EXAMPLE - Intent Fail Acknowledged:
------------------------------------
CONFIG = {
    'portfolio': {'QQQ': 1.0},
    'risk_intent': 'CONSERVATIVE',  # Beta 0.3-0.5 expected
    'benchmark': 'SPY'
}

# QQQ has beta ~1.2 → massive intent deviation
# If data quality also poor, will raise IntentFailStructureInconclusiveError

override = UserAcknowledgment(
    verdict_type='INTENT_FAIL_STRUCTURE_INCONCLUSIVE',
    authorized_by='Risk Committee',
    reason='Intent mismatch acknowledged - portfolio rebalance scheduled Q1 2024',
    date=datetime.now()
)

run_analysis_to_pdf(CONFIG, override=override)


PRODUCTION BEST PRACTICES:
---------------------------
1. ❌ DO NOT create default overrides in production code
2. ✅ DO require explicit authorization for each override
3. ✅ DO document override reason in detail
4. ✅ DO set expiry dates for temporary overrides
5. ✅ DO review override audit trail regularly
6. ✅ DO address root causes (add data, rebalance portfolio)
7. ❌ DO NOT use overrides as permanent workaround

For production systems, integrate UserAcknowledgment into your workflow
management system and require sign-off from authorized personnel.
"""


def use_preset(name: str) -> dict:
    """
    Restituisce un preset predefinito senza mutare stato globale.
    
    Args:
        name: Nome del preset da caricare
        
    Returns:
        dict: Portfolio configuration del preset
        
    Raises:
        ValueError: Se il preset non esiste
        
    Usage:
        from portfolio_engine.config.user_config import use_preset
        portfolio = use_preset("aggressive")
    """
    if name in PRESETS:
        return dict(PRESETS[name])  # Return copy, not reference
    else:
        raise ValueError(f"Preset '{name}' non trovato. Disponibili: {list(PRESETS.keys())}")


# Quick display quando importato
if __name__ == "__main__":
    print("=" * 50)
    print("CONFIGURAZIONE PORTAFOGLIO ATTUALE")
    print("=" * 50)
    for ticker, weight in PORTFOLIO.items():
        print(f"  {ticker:<12} {weight:>6.1%}")
    print("-" * 50)
    print(f"  {'TOTALE':<12} {sum(PORTFOLIO.values()):>6.1%}")
    print("=" * 50)
    print(f"\nPreset disponibili: {list(PRESETS.keys())}")
