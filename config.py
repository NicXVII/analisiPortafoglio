"""
Portfolio Configuration
=======================
Configura qui il tuo portafoglio e le opzioni di analisi.
Modifica questo file senza toccare main.py.
"""

# =========================
# PORTFOLIO ALLOCATION
# =========================
PORTFOLIO = {
    # USA
    "IVV": 0.18,        # S&P 500 – core USA

    # EUROPA
    "EXSA.DE": 0.12,    # STOXX Europe 600 – core Europa

    # GIAPPONE (Nikkei/Japan proxy)
    "EWJ": 0.08,        # Japan equity (proxy solido per Nikkei su Yahoo)

    # TAIWAN
    "EWT": 0.06,        # MSCI Taiwan

    # SMALL CAPS GLOBALI
    "IUSN.DE": 0.10,    # MSCI World Small Cap

    # REAL ESTATE (globale)
    "VNQ": 0.12,        # US REITs (storico lungo, testabile)
    # alternativa se vuole più globale: "REET": 0.12

    # BIOTECH
    "IBB": 0.10,        # Nasdaq Biotechnology (storico lungo, testabile)
    # alternativa più “sector ETF”: "XBI": 0.10

    # ARK ROBOTICS & AI (tema aggressivo)
    "ARKQ": 0.08,       # ARK Autonomous Tech & Robotics

    # URANIO / NUCLEARE
    "URA": 0.06,        # Global Uranium & Nuclear Energy

    # AI INFRASTRUCTURE / DATA CENTERS
    "SRVR": 0.10,       # Data centers + digital infrastructure
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
    
    return {
        "tickers": tickers,
        "weights": weights,
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


def use_preset(name: str) -> None:
    """
    Cambia PORTFOLIO usando un preset predefinito.
    Uso: from config import use_preset; use_preset("aggressive")
    """
    global PORTFOLIO
    if name in PRESETS:
        PORTFOLIO.clear()
        PORTFOLIO.update(PRESETS[name])
        print(f"✓ Preset '{name}' caricato: {PORTFOLIO}")
    else:
        print(f"❌ Preset '{name}' non trovato. Disponibili: {list(PRESETS.keys())}")


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
