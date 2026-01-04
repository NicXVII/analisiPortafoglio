"""
ETF Taxonomy Module
===================
Classificazione ETF per categoria, esposizione geografica e funzione economica.

Include:
- Categorie ETF (Core, Settoriale, Tematico, Bond, etc.)
- Mapping esposizione geografica
- Classificazione per funzione economica
"""

from typing import Dict, List
import numpy as np


# ================================================================================
# ETF CATEGORIES (Tassonomia Granulare v2)
# ================================================================================
# 
# STRUTTURA CORRETTA:
# 1. Core Geografico: blocchi regionali strutturali
# 2. Fattoriale/Asset Class: small cap, REIT, value, momentum
# 3. Settoriale: biotech, healthcare, financials (non tematico)
# 4. Tematico Puro: trend specifici ad alto beta (uranio, AI, clean energy)
#

# === 1. CORE GEOGRAFICO ===
# Core Globale: All-World diversificati
CORE_GLOBAL_ETF = ['VWCE', 'IWDA', 'SWDA', 'VT', 'ACWI', 'URTH', 'MSCI', 'FTSE', 'ALLWORLD']

# Core Developed: USA, Europa, Japan, UK (blocchi geografici strutturali)
CORE_DEVELOPED_ETF = ['CSPX', 'SXR8', 'VOO', 'SPY', 'IVV', 'QQQ',   # USA Large
                      'EZU', 'VGK', 'IEUR', 'EXSA', 'MEUD',          # Europa
                      'EWJ', 'IJPN', 'SJPA',                          # Japan
                      'EWU', 'ISF', 'VUKE',                           # UK
                      'EWC', 'EWA', 'EWS',                            # Canada, Australia, Singapore
                      'EWT', 'EWY', 'EWH']                            # Taiwan, Korea, HK (DM Asia)

# Core Emerging Broad: EM diversificati (NON single-country)
EMERGING_BROAD_ETF = ['EIMI', 'EEM', 'VWO', 'IS3N', 'IEEM', 'AEEM', 'EMIM']

# === 2. FATTORIALE / ASSET CLASS (strutturali, NON satellite) ===
# Small Cap: fattore size, strutturale
SMALL_CAP_ETF = ['IUSN', 'VB', 'IJR', 'WSML', 'ZPRX', 'IWM', 'SCHA', 'VBR', 'VIOO']

# Real Estate / REIT: asset class distinta
REIT_ETF = ['VNQ', 'VNQI', 'IYR', 'SCHH', 'RWR', 'REET', 'XLRE', 'USRT', 'REM']

# Factor ETF: value, momentum, quality, min vol (strutturali)
FACTOR_ETF = ['VLUE', 'VTV', 'IWD', 'MTUM', 'QUAL', 'USMV', 'SPLV', 'EFAV',
              'ACWV', 'VFMF', 'GVAL', 'IVAL', 'FNDX', 'PRF']

# === 3. SETTORIALE (non tematico, cicli economici) ===
# Settori ciclici e difensivi tradizionali
SECTOR_ETF = ['XLF', 'XLV', 'XLI', 'XLP', 'XLU', 'XLC', 'XLB', 'XLY',  # SPDR Settori
              'IBB', 'XBI', 'IHI', 'IHF',                               # Healthcare/Biotech
              'ITA', 'PPA',                                              # Defense/Aerospace
              'XLE', 'XOP', 'OIH', 'VDE',                                # Energy tradizionale
              'KBE', 'KRE', 'IAI']                                       # Financials

# === 4. TEMATICO PURO (high beta, trend specifici) ===
# Questi sono i veri "satellite" speculativi
THEMATIC_PURE_ETF = ['URA', 'URNM', 'NUKL',                        # Uranio/Nucleare
                     'SRVR', 'SKYY', 'WCLD', 'CLOU',               # Cloud/Data Center
                     'ARKK', 'ARKG', 'ARKQ', 'ARKW', 'ARKF',       # ARK Innovation
                     'SOXX', 'SMH', 'SEMI', 'PSI',                 # Semiconduttori
                     'HACK', 'CIBR', 'CYBR', 'BUG',                # Cybersecurity
                     'ICLN', 'TAN', 'QCLN', 'PBW', 'FAN',          # Clean Energy
                     'BATT', 'LIT', 'DRIV', 'IDRV', 'KARS',        # EV/Batterie
                     'ROBO', 'BOTZ', 'IRBO', 'AIQ', 'CHAT',        # Robotics/AI
                     'MOON', 'HERO', 'ESPO', 'NERD', 'GAMR',       # Space/Gaming
                     'IBIT', 'BITO', 'GBTC', 'ETHE',               # Crypto
                     'MSTR', 'COIN', 'RING', 'GDXJ',               # Crypto-proxy/Gold miners
                     'ARKG', 'GNOM', 'XBI']                        # Genomics/Biotech speculativo

# === 5. SINGLE-COUNTRY EM (tilt geografico, rischio concentrato) ===
EM_SINGLE_COUNTRY_ETF = ['INDA', 'INDY', 'SMIN', 'NDIA',   # India
                         'EWZ', 'FLBR', 'BRF',              # Brasile
                         'MCHI', 'FXI', 'KWEB', 'ASHR',     # Cina
                         'EWW', 'FLMX',                     # Messico
                         'TUR', 'EZA', 'EPOL', 'ERUS']      # Altri single-country

# === 6. BOND, GOLD, DEFENSIVE ===
BOND_ETF = ['AGGH', 'BND', 'AGG', 'GOVT', 'TLT', 'IEF', 'LQD', 'HYG', 'IEAG', 'IBTA', 
            'VGOV', 'STHY', 'TIP', 'TIPS', 'IGLT', 'CORP', 'IBCI', 'VAGF', 'VAGS', 
            'VUTY', 'VGEA', 'VECP', 'VEMT', 'VGEB', 'VCSH', 'VCIT', 'VCLT',
            'STHE', 'DTLA', 'GOVE', 'IEGA', 'GIST', 'SEGA', 'XGLE', 'UEEF',
            'SHY', 'IEI', 'VGSH', 'VGIT', 'VGLT', 'EDV', 'ZROZ']

GOLD_COMMODITY_ETF = ['GLD', 'GOLD', 'IAU', 'SGOL', 'GLDM', 'PHAU', 'SGLD',
                      'DBC', 'PDBC', 'GSG', 'COMT', 'COPX', 'REMX', 'CMOD',
                      'SLV', 'PPLT', 'PALL', 'USO', 'UNG', 'WEAT', 'CORN']

DIVIDEND_INCOME_ETF = ['VIG', 'SCHD', 'VIGI', 'NOBL', 'SPHD', 'HDV', 'DVY', 'VHYL', 'IUKD',
                       'SPYD', 'JEPI', 'JEPQ', 'DIVO', 'IEDY', 'IDVY', 'VYMI', 'SDIV', 
                       'FDVV', 'VYM', 'DGRO', 'DIV', 'DIVD', 'QDIV', 'TDIV']

DEFENSIVE_ETF = ['USMV', 'SPLV', 'EFAV', 'ACWV', 'XMLV', 'XSLV', 'LVHD'] + GOLD_COMMODITY_ETF

# === ALIAS PER BACKWARD COMPATIBILITY ===
CORE_REGIONAL_ETF = CORE_DEVELOPED_ETF
EMERGING_ETF = EMERGING_BROAD_ETF
# SATELLITE ora include solo tematici puri + single-country EM
SATELLITE_KEYWORDS = THEMATIC_PURE_ETF + EM_SINGLE_COUNTRY_ETF
# NON-CORE STRUTTURALE (fattoriali + settoriali + REIT) - NON sono satellite
NON_CORE_STRUCTURAL_ETF = SMALL_CAP_ETF + REIT_ETF + FACTOR_ETF + SECTOR_ETF


# ================================================================================
# GEOGRAPHIC EXPOSURE MAPPING (esposizione geografica implicita)
# ================================================================================
# Ogni ETF ha un breakdown geografico approssimativo
# Fonte: factsheet ufficiali, dati medi storici

GEO_EXPOSURE = {
    # === GLOBAL ===
    "VT": {"USA": 0.60, "Europe": 0.15, "Japan": 0.06, "EM": 0.12, "Other_DM": 0.07},
    "VWCE": {"USA": 0.60, "Europe": 0.15, "Japan": 0.06, "EM": 0.12, "Other_DM": 0.07},
    "IWDA": {"USA": 0.68, "Europe": 0.18, "Japan": 0.07, "EM": 0.0, "Other_DM": 0.07},
    "ACWI": {"USA": 0.62, "Europe": 0.14, "Japan": 0.05, "EM": 0.12, "Other_DM": 0.07},
    
    # === USA ===
    "IVV": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "SPY": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "VOO": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "QQQ": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "IWM": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "VNQ": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "IBB": {"USA": 0.90, "Europe": 0.05, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.05},
    
    # === EUROPA ===
    "VGK": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "EXSA": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "EZU": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "EWU": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "IEUR": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    
    # === JAPAN / ASIA DM ===
    "EWJ": {"USA": 0.0, "Europe": 0.0, "Japan": 1.0, "EM": 0.0, "Other_DM": 0.0},
    "VPL": {"USA": 0.0, "Europe": 0.0, "Japan": 0.65, "EM": 0.0, "Other_DM": 0.35},
    "EPP": {"USA": 0.0, "Europe": 0.0, "Japan": 0.60, "EM": 0.0, "Other_DM": 0.40},
    "EWT": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 1.0},  # Taiwan = DM per MSCI
    "EWY": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 1.0},  # Korea
    
    # === EMERGING MARKETS ===
    "EEM": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},
    "VWO": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},
    "INDA": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},  # India
    "MCHI": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},  # Cina
    "EWZ": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},   # Brasile
    
    # === SMALL CAP ===
    "IUSN": {"USA": 0.60, "Europe": 0.20, "Japan": 0.10, "EM": 0.0, "Other_DM": 0.10},
    "IWM": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    
    # === TEMATICI (prevalentemente USA) ===
    "ARKK": {"USA": 0.85, "Europe": 0.05, "Japan": 0.0, "EM": 0.05, "Other_DM": 0.05},
    "ARKQ": {"USA": 0.80, "Europe": 0.05, "Japan": 0.05, "EM": 0.05, "Other_DM": 0.05},
    "URA": {"USA": 0.40, "Europe": 0.10, "Japan": 0.05, "EM": 0.0, "Other_DM": 0.45},  # Canada, Australia
    "SRVR": {"USA": 0.85, "Europe": 0.05, "Japan": 0.05, "EM": 0.0, "Other_DM": 0.05},
    "SOXX": {"USA": 0.85, "Europe": 0.05, "Japan": 0.0, "EM": 0.05, "Other_DM": 0.05},
    
    # === SETTORIALI USA ===
    "XLE": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "XLF": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "XLV": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "ITA": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
}

# Default per ETF non mappati (assumption conservativa)
DEFAULT_GEO = {"USA": 0.60, "Europe": 0.15, "Japan": 0.05, "EM": 0.10, "Other_DM": 0.10}


# ================================================================================
# ASSET FUNCTION CLASSIFICATION (funzione economica)
# ================================================================================
ASSET_FUNCTION = {
    # Core Growth: driver principale di rendimento, diversificato
    "CORE_GROWTH": ["VT", "VWCE", "IWDA", "ACWI", "IVV", "SPY", "VOO", "QQQ"],
    
    # Regional Diversification: esposizione geografica specifica
    "REGIONAL_DIVERSIFICATION": ["VGK", "EZU", "EXSA", "EWJ", "EWU", "VPL", "EPP", "EWT", "EWY"],
    
    # EM Exposure: crescita EM, rischio geopolitico
    "EM_EXPOSURE": ["EEM", "VWO", "INDA", "MCHI", "EWZ", "EIMI"],
    
    # Factor Tilt: esposizione fattoriale (size, value, momentum)
    "FACTOR_TILT": ["IUSN", "IWM", "VB", "MTUM", "QUAL", "VLUE", "VTV"],
    
    # Real Assets: REIT, infrastrutture, commodity equity
    "REAL_ASSETS": ["VNQ", "VNQI", "XLRE", "SRVR"],
    
    # Cyclical Hedge: settori ciclici, energy, materials
    "CYCLICAL_HEDGE": ["XLE", "XLF", "XLB", "XLI", "ITA"],
    
    # Defensive: healthcare, utilities, consumer staples
    "DEFENSIVE_SECTOR": ["XLV", "XLU", "XLP", "IBB"],
    
    # Thematic Alpha: scommesse tematiche ad alto beta
    "THEMATIC_ALPHA": ["ARKK", "ARKQ", "ARKG", "URA", "SOXX", "ICLN", "TAN", "LIT"],
    
    # Income: dividend, covered call
    "INCOME": ["VIG", "SCHD", "JEPI", "JEPQ", "VYM", "HDV"],
    
    # Tail Hedge: oro, volatilità, bond lunghi
    "TAIL_HEDGE": ["GLD", "TLT", "GOVT", "BND"],
}


# ================================================================================
# HELPER FUNCTIONS
# ================================================================================

def get_asset_function(ticker: str) -> str:
    """Determina la funzione economica di un asset."""
    ticker_clean = ticker.upper().split('.')[0]
    for function, tickers_list in ASSET_FUNCTION.items():
        if ticker_clean in tickers_list:
            return function
    # Default basato su categorie
    if ticker_clean in THEMATIC_PURE_ETF or any(kw in ticker_clean for kw in THEMATIC_PURE_ETF):
        return "THEMATIC_ALPHA"
    if ticker_clean in REIT_ETF or any(kw in ticker_clean for kw in REIT_ETF):
        return "REAL_ASSETS"
    if ticker_clean in SECTOR_ETF or any(kw in ticker_clean for kw in SECTOR_ETF):
        return "CYCLICAL_HEDGE"
    if ticker_clean in SMALL_CAP_ETF or any(kw in ticker_clean for kw in SMALL_CAP_ETF):
        return "FACTOR_TILT"
    if ticker_clean in EMERGING_BROAD_ETF or any(kw in ticker_clean for kw in EMERGING_BROAD_ETF):
        return "EM_EXPOSURE"
    if ticker_clean in CORE_DEVELOPED_ETF or any(kw in ticker_clean for kw in CORE_DEVELOPED_ETF):
        return "REGIONAL_DIVERSIFICATION"
    return "CORE_GROWTH"  # Default


def calculate_geographic_exposure(tickers: list, weights: np.ndarray) -> Dict[str, float]:
    """
    Calcola l'esposizione geografica REALE del portafoglio,
    considerando la composizione interna di ogni ETF.
    """
    geo_totals = {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0}
    
    for i, ticker in enumerate(tickers):
        ticker_clean = ticker.upper().split('.')[0]
        weight = weights[i]
        
        # Cerca mapping esatto o parziale
        geo_map = None
        if ticker_clean in GEO_EXPOSURE:
            geo_map = GEO_EXPOSURE[ticker_clean]
        else:
            # Cerca match parziale
            for key in GEO_EXPOSURE:
                if key in ticker_clean or ticker_clean in key:
                    geo_map = GEO_EXPOSURE[key]
                    break
        
        if geo_map is None:
            geo_map = DEFAULT_GEO
        
        for region, pct in geo_map.items():
            geo_totals[region] += weight * pct
    
    return geo_totals


def analyze_function_exposure(tickers: list, weights: np.ndarray) -> Dict[str, float]:
    """
    Analizza l'esposizione per FUNZIONE ECONOMICA.
    """
    function_totals = {}
    for i, ticker in enumerate(tickers):
        func = get_asset_function(ticker)
        function_totals[func] = function_totals.get(func, 0) + weights[i]
    return function_totals


def classify_ticker(ticker: str) -> Dict[str, bool]:
    """
    Classifica un ticker in tutte le categorie applicabili.
    
    Returns:
        Dict con flag per ogni categoria
    """
    ticker_clean = ticker.upper().split('.')[0]
    
    return {
        "is_core_global": ticker_clean in CORE_GLOBAL_ETF or any(kw in ticker_clean for kw in CORE_GLOBAL_ETF),
        "is_core_developed": ticker_clean in CORE_DEVELOPED_ETF or any(kw in ticker_clean for kw in CORE_DEVELOPED_ETF),
        "is_emerging_broad": ticker_clean in EMERGING_BROAD_ETF or any(kw in ticker_clean for kw in EMERGING_BROAD_ETF),
        "is_small_cap": ticker_clean in SMALL_CAP_ETF or any(kw in ticker_clean for kw in SMALL_CAP_ETF),
        "is_reit": ticker_clean in REIT_ETF or any(kw in ticker_clean for kw in REIT_ETF),
        "is_factor": ticker_clean in FACTOR_ETF or any(kw in ticker_clean for kw in FACTOR_ETF),
        "is_sector": ticker_clean in SECTOR_ETF or any(kw in ticker_clean for kw in SECTOR_ETF),
        "is_thematic": ticker_clean in THEMATIC_PURE_ETF or any(kw in ticker_clean for kw in THEMATIC_PURE_ETF),
        "is_em_single": ticker_clean in EM_SINGLE_COUNTRY_ETF or any(kw in ticker_clean for kw in EM_SINGLE_COUNTRY_ETF),
        "is_bond": ticker_clean in BOND_ETF or any(kw in ticker_clean for kw in BOND_ETF),
        "is_gold_commodity": ticker_clean in GOLD_COMMODITY_ETF or any(kw in ticker_clean for kw in GOLD_COMMODITY_ETF),
        "is_dividend": ticker_clean in DIVIDEND_INCOME_ETF or any(kw in ticker_clean for kw in DIVIDEND_INCOME_ETF),
        "is_defensive": ticker_clean in DEFENSIVE_ETF or any(kw in ticker_clean for kw in DEFENSIVE_ETF),
    }


def get_ticker_category(ticker: str) -> str:
    """
    Restituisce la categoria principale di un ticker.
    """
    classification = classify_ticker(ticker)
    
    # Priority order
    if classification["is_core_global"]:
        return "CORE_GLOBAL"
    if classification["is_bond"]:
        return "BOND"
    if classification["is_gold_commodity"]:
        return "GOLD_COMMODITY"
    if classification["is_thematic"]:
        return "THEMATIC_PURE"
    if classification["is_em_single"]:
        return "EM_SINGLE_COUNTRY"
    if classification["is_reit"]:
        return "REIT"
    if classification["is_small_cap"]:
        return "SMALL_CAP"
    if classification["is_factor"]:
        return "FACTOR"
    if classification["is_sector"]:
        return "SECTOR"
    if classification["is_dividend"]:
        return "DIVIDEND_INCOME"
    if classification["is_emerging_broad"]:
        return "EMERGING_BROAD"
    if classification["is_core_developed"]:
        return "CORE_DEVELOPED"
    
    return "OTHER"
