"""
ETF Taxonomy Module
===================
Classificazione ETF per categoria, esposizione geografica e funzione economica.

Include:
- Categorie ETF (Core, Settoriale, Tematico, Bond, etc.)
- Mapping esposizione geografica
- Classificazione per funzione economica
"""

from typing import Dict, List, Any
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
                      'EWT', 'EWY', 'EWH',                            # Taiwan, Korea, HK (DM Asia)
                      'VPL', 'EPP', 'IPAC']                           # Pacific (Asia-Pacific DM)

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
    "VNQ": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "IBB": {"USA": 0.90, "Europe": 0.05, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.05},
    
    # === USA SMALL CAP (100% USA) ===
    "IWM": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "IJR": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "VB": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    
    # === EUROPA BROAD ===
    "VGK": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "EXSA": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "EZU": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    "IEUR": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},
    
    # === COUNTRY ETF EUROPA (100% paese) - FIX DETERMINISTIC GEO ===
    "EWU": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},   # UK
    "EWUS": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},  # UK Small Cap
    "EWG": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},   # Germania
    "EWQ": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},   # Francia
    "EWL": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},   # Svizzera
    "EWI": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},   # Italia
    "EWP": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},   # Spagna
    "EWN": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},   # Olanda
    "EWK": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},   # Belgio
    "EWD": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},   # Svezia
    "ENOR": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},  # Norvegia
    "EDEN": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},  # Danimarca
    "EFNL": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},  # Finlandia
    "EIRL": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},  # Irlanda
    "EWO": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},   # Austria
    "EPOL": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},  # Polonia
    "GREK": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},  # Grecia
    "TUR": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},   # Turchia
    
    # === JAPAN / ASIA DM (100% paese) ===
    "EWJ": {"USA": 0.0, "Europe": 0.0, "Japan": 1.0, "EM": 0.0, "Other_DM": 0.0},
    "SCJ": {"USA": 0.0, "Europe": 0.0, "Japan": 1.0, "EM": 0.0, "Other_DM": 0.0},   # Japan Small Cap
    "DXJ": {"USA": 0.0, "Europe": 0.0, "Japan": 1.0, "EM": 0.0, "Other_DM": 0.0},   # Japan hedged
    "VPL": {"USA": 0.0, "Europe": 0.0, "Japan": 0.65, "EM": 0.0, "Other_DM": 0.35},
    "EPP": {"USA": 0.0, "Europe": 0.0, "Japan": 0.60, "EM": 0.0, "Other_DM": 0.40},
    "EWT": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},   # Taiwan (classificato EM per coerenza portafoglio)
    "EWY": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 1.0},   # Korea
    "EWA": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 1.0},   # Australia
    "EWC": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 1.0},   # Canada
    "EWS": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 1.0},   # Singapore
    "EWH": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 1.0},   # Hong Kong
    "ENZL": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 1.0},  # New Zealand
    "EIS": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 1.0},   # Israele
    
    # === EMERGING MARKETS BROAD ===
    "EEM": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},
    "VWO": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},
    "IEMG": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},
    "EIMI": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},
    
    # === EMERGING MARKETS SINGLE COUNTRY (100% EM) ===
    "INDA": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},  # India
    "INDY": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},  # India 50
    "SMIN": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},  # India Small Cap
    "MCHI": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},  # Cina
    "FXI": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},   # Cina Large Cap
    "ASHR": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},  # Cina A-Shares
    "KWEB": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},  # Cina Internet
    "CXSE": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},  # Cina ex State
    "CNXT": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},  # Cina Next Gen
    "EWZ": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},   # Brasile
    "FLBR": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},  # Brasile
    "BRF": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},   # Brasile Small Cap
    "EWZS": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},  # Brasile Small Cap
    "EWW": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},   # Messico
    "FLMX": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},  # Messico
    "ECH": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},   # Cile
    "EPU": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},   # Perù
    "ARGT": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},  # Argentina
    "THD": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},   # Thailandia
    "EIDO": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},  # Indonesia
    "EPHE": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},  # Filippine
    "VNM": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},   # Vietnam
    "EWM": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},   # Malaysia
    "EZA": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},   # Sud Africa
    "NGE": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},   # Nigeria
    "AFK": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},   # Africa
    "FM": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},    # Frontier Markets
    "FRN": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},   # Frontier Markets (alt)
    "GXG": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},   # Colombia
    "QAT": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},   # Qatar
    "UAE": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},   # UAE
    "KSA": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},   # Arabia Saudita
    "ERUS": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},  # Russia (may be delisted)
    "RSX": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},   # Russia (may be delisted)
    
    # === EM SMALL CAP (100% EM) ===
    "EWX": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},   # EM Small Cap
    "EEMS": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},  # EM Small Cap (iShares)
    "EMSC": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},  # EM Small Cap UCITS
    
    # === SMALL CAP NON-USA ===
    "IUSN": {"USA": 0.60, "Europe": 0.20, "Japan": 0.10, "EM": 0.0, "Other_DM": 0.10},  # Global Small Cap
    "VSS": {"USA": 0.0, "Europe": 0.35, "Japan": 0.20, "EM": 0.25, "Other_DM": 0.20},   # FTSE ex-US Small Cap
    
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
    
    # === UCITS ETF (European-listed) ===
    # Formato ticker: XXXX.L (London), XXXX.DE (Xetra), XXXX.AS (Amsterdam), XXXX.PA (Paris), XXXX.MI (Milano)
    
    # --- GLOBAL / WORLD UCITS ---
    "VWCE.DE": {"USA": 0.60, "Europe": 0.15, "Japan": 0.06, "EM": 0.12, "Other_DM": 0.07},  # Vanguard FTSE All-World
    "VWRL.L": {"USA": 0.60, "Europe": 0.15, "Japan": 0.06, "EM": 0.12, "Other_DM": 0.07},   # Vanguard FTSE All-World (Dist)
    "VWRA.L": {"USA": 0.60, "Europe": 0.15, "Japan": 0.06, "EM": 0.12, "Other_DM": 0.07},   # Vanguard FTSE All-World (Acc)
    "SWDA.L": {"USA": 0.68, "Europe": 0.18, "Japan": 0.07, "EM": 0.0, "Other_DM": 0.07},    # iShares Core MSCI World
    "IWDA.L": {"USA": 0.68, "Europe": 0.18, "Japan": 0.07, "EM": 0.0, "Other_DM": 0.07},    # iShares Core MSCI World (Amsterdam)
    "EUNL.DE": {"USA": 0.68, "Europe": 0.18, "Japan": 0.07, "EM": 0.0, "Other_DM": 0.07},   # iShares Core MSCI World (Xetra)
    "SSAC.L": {"USA": 0.62, "Europe": 0.14, "Japan": 0.05, "EM": 0.12, "Other_DM": 0.07},   # iShares MSCI ACWI
    "IMIE.L": {"USA": 0.62, "Europe": 0.14, "Japan": 0.05, "EM": 0.12, "Other_DM": 0.07},   # iShares Core MSCI World IMI
    "XDWD.DE": {"USA": 0.68, "Europe": 0.18, "Japan": 0.07, "EM": 0.0, "Other_DM": 0.07},   # Xtrackers MSCI World
    "LCWD.L": {"USA": 0.68, "Europe": 0.18, "Japan": 0.07, "EM": 0.0, "Other_DM": 0.07},    # Lyxor Core MSCI World
    
    # --- USA UCITS ---
    "CSPX.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Core S&P 500
    "IUSA.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares S&P 500
    "VUAA.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Vanguard S&P 500 (Acc)
    "VUSA.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Vanguard S&P 500 (Dist)
    "SXR8.DE": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares Core S&P 500 (Xetra)
    "EQQQ.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Invesco EQQQ Nasdaq-100
    "CNDX.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Nasdaq 100
    "IUSV.DE": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares MSCI USA Value
    "QDVE.DE": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares S&P 500 Info Tech
    
    # --- USA SMALL CAP UCITS ---
    "USSC.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # SPDR Russell 2000 US Small Cap
    "IUS3.DE": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares MSCI USA Small Cap
    "WSML.L": {"USA": 0.60, "Europe": 0.20, "Japan": 0.10, "EM": 0.0, "Other_DM": 0.10},    # iShares MSCI World Small Cap
    "IUSN.L": {"USA": 0.60, "Europe": 0.20, "Japan": 0.10, "EM": 0.0, "Other_DM": 0.10},    # iShares MSCI World Small Cap
    
    # --- EUROPE UCITS ---
    "IMEU.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Core MSCI Europe
    "SMEA.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares MSCI Europe
    "MEUD.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Lyxor Core STOXX Europe 600
    "VEUR.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Vanguard FTSE Developed Europe
    "VERX.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Vanguard FTSE Developed Europe ex UK
    "EXW1.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares STOXX Europe 600
    "EXSA.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares STOXX Europe 600 (Xetra)
    "DJSC.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares MSCI Europe Small Cap
    "EXI1.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares STOXX Europe 600 Industrials
    
    # --- JAPAN UCITS ---
    "SJPA.L": {"USA": 0.0, "Europe": 0.0, "Japan": 1.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Core MSCI Japan
    "IJPA.L": {"USA": 0.0, "Europe": 0.0, "Japan": 1.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Core MSCI Japan (alt)
    "VJPN.L": {"USA": 0.0, "Europe": 0.0, "Japan": 1.0, "EM": 0.0, "Other_DM": 0.0},        # Vanguard FTSE Japan
    "XMJP.DE": {"USA": 0.0, "Europe": 0.0, "Japan": 1.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers MSCI Japan
    "LCJP.L": {"USA": 0.0, "Europe": 0.0, "Japan": 1.0, "EM": 0.0, "Other_DM": 0.0},        # Lyxor Core MSCI Japan
    
    # --- ASIA-PACIFIC UCITS ---
    "VAPX.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.50, "EM": 0.0, "Other_DM": 0.50},      # Vanguard FTSE Developed Asia Pacific ex Japan
    "CPXJ.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 1.0},        # iShares Core MSCI Pacific ex Japan
    "IPXJ.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 1.0},        # iShares MSCI Pacific ex Japan
    
    # --- EMERGING MARKETS UCITS ---
    "EIMI.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # iShares Core MSCI EM IMI
    "VFEM.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # Vanguard FTSE Emerging Markets
    "EMIM.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # iShares Core MSCI EM
    "XMME.DE": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},       # Xtrackers MSCI EM
    "AUEM.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # Amundi MSCI EM
    
    # --- EM SINGLE COUNTRY UCITS ---
    "NDIA.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # iShares MSCI India
    "IIND.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # iShares MSCI India
    "CNYA.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # iShares MSCI China A
    "ICHN.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # iShares MSCI China
    "IBZL.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # iShares MSCI Brazil
    "XMEX.DE": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},       # Xtrackers MSCI Mexico
    
    # --- SECTOR UCITS (World/Global) ---
    "WHEA.L": {"USA": 0.70, "Europe": 0.12, "Japan": 0.08, "EM": 0.05, "Other_DM": 0.05},   # iShares MSCI World Health Care
    "XDWH.DE": {"USA": 0.70, "Europe": 0.12, "Japan": 0.08, "EM": 0.05, "Other_DM": 0.05},  # Xtrackers MSCI World Health Care
    "WIND.L": {"USA": 0.55, "Europe": 0.20, "Japan": 0.12, "EM": 0.05, "Other_DM": 0.08},   # iShares MSCI World Industrials (MSCI ex US focused)
    "WFIN.L": {"USA": 0.65, "Europe": 0.18, "Japan": 0.08, "EM": 0.04, "Other_DM": 0.05},   # iShares MSCI World Financials
    "WCSS.L": {"USA": 0.65, "Europe": 0.18, "Japan": 0.08, "EM": 0.04, "Other_DM": 0.05},   # iShares MSCI World Consumer Staples
    "WCOD.L": {"USA": 0.70, "Europe": 0.12, "Japan": 0.08, "EM": 0.05, "Other_DM": 0.05},   # iShares MSCI World Consumer Discretionary
    "WTCH.L": {"USA": 0.75, "Europe": 0.08, "Japan": 0.08, "EM": 0.05, "Other_DM": 0.04},   # iShares MSCI World Information Technology
    "WMAT.L": {"USA": 0.50, "Europe": 0.15, "Japan": 0.10, "EM": 0.10, "Other_DM": 0.15},   # iShares MSCI World Materials
    "WENS.L": {"USA": 0.55, "Europe": 0.12, "Japan": 0.02, "EM": 0.10, "Other_DM": 0.21},   # iShares MSCI World Energy
    "WUTI.L": {"USA": 0.60, "Europe": 0.20, "Japan": 0.08, "EM": 0.05, "Other_DM": 0.07},   # iShares MSCI World Utilities
    "WTEL.L": {"USA": 0.60, "Europe": 0.20, "Japan": 0.10, "EM": 0.05, "Other_DM": 0.05},   # iShares MSCI World Telecom
    
    # --- SEMICONDUCTOR UCITS ---
    "SEMI.L": {"USA": 0.65, "Europe": 0.08, "Japan": 0.08, "EM": 0.15, "Other_DM": 0.04},   # iShares Semiconductor (SOXX-like)
    "SMH": {"USA": 0.80, "Europe": 0.05, "Japan": 0.05, "EM": 0.08, "Other_DM": 0.02},      # VanEck Semiconductor ETF
    "VVSM.DE": {"USA": 0.65, "Europe": 0.08, "Japan": 0.08, "EM": 0.15, "Other_DM": 0.04},  # VanEck Semiconductor UCITS
    
    # --- THEMATIC UCITS ---
    "WCLD.L": {"USA": 0.85, "Europe": 0.08, "Japan": 0.02, "EM": 0.02, "Other_DM": 0.03},   # WisdomTree Cloud Computing
    "ISPY.L": {"USA": 0.80, "Europe": 0.10, "Japan": 0.02, "EM": 0.05, "Other_DM": 0.03},   # iShares Digital Security
    "RBOT.L": {"USA": 0.55, "Europe": 0.15, "Japan": 0.20, "EM": 0.05, "Other_DM": 0.05},   # iShares Automation & Robotics
    "HEAL.L": {"USA": 0.60, "Europe": 0.20, "Japan": 0.10, "EM": 0.05, "Other_DM": 0.05},   # iShares Healthcare Innovation
    "INRG.L": {"USA": 0.40, "Europe": 0.25, "Japan": 0.05, "EM": 0.15, "Other_DM": 0.15},   # iShares Global Clean Energy
    "CHRG.L": {"USA": 0.35, "Europe": 0.30, "Japan": 0.10, "EM": 0.15, "Other_DM": 0.10},   # iShares Electric Vehicles
    "BATG.L": {"USA": 0.30, "Europe": 0.10, "Japan": 0.15, "EM": 0.35, "Other_DM": 0.10},   # L&G Battery Value-Chain
    "URNG.L": {"USA": 0.40, "Europe": 0.10, "Japan": 0.05, "EM": 0.0, "Other_DM": 0.45},    # Global X Uranium
    
    # --- BOND UCITS ---
    "AGGH.L": {"USA": 0.40, "Europe": 0.30, "Japan": 0.10, "EM": 0.10, "Other_DM": 0.10},   # iShares Core Global Aggregate Bond
    "EUNA.DE": {"USA": 0.40, "Europe": 0.30, "Japan": 0.10, "EM": 0.10, "Other_DM": 0.10},  # iShares Core Global Agg Bond (Xetra)
    "IGLA.L": {"USA": 0.40, "Europe": 0.30, "Japan": 0.10, "EM": 0.10, "Other_DM": 0.10},   # iShares Global Govt Bond
    "IDTL.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares $ Treasury Bond 20+yr
    "IBTL.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares $ Treasury Bond 7-10yr
    "IEAG.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Core EUR Govt Bond
    "IBGS.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares EUR Govt Bond 1-3yr
    "IEAC.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Core EUR Corp Bond
    "LQDE.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares $ Corp Bond
    "IHYA.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares $ High Yield Corp Bond
    "SEMB.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # iShares JPM $ EM Bond
    "EMBE.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # iShares JPM EM Local Govt Bond
    "ITPS.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares $ TIPS
    "IBCI.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares EUR Inflation Linked Govt Bond
    
    # --- GOLD/COMMODITY UCITS ETC ---
    "SGLD.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Invesco Physical Gold (no geographic)
    "SGLN.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Invesco Physical Gold (alt ticker)
    "IGLN.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Physical Gold
    "PHAU.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # WisdomTree Physical Gold
    "VZLD.DE": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # WisdomTree Physical Gold (Xetra)
    "SLVR.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Invesco Physical Silver
    "PHAG.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # WisdomTree Physical Silver
    "PHPM.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # WisdomTree Physical Precious Metals
    
    # --- REIT UCITS ---
    "IWDP.L": {"USA": 0.60, "Europe": 0.15, "Japan": 0.10, "EM": 0.05, "Other_DM": 0.10},   # iShares Developed Markets Property Yield
    "IDWP.L": {"USA": 0.60, "Europe": 0.15, "Japan": 0.10, "EM": 0.05, "Other_DM": 0.10},   # iShares Developed Markets Property
    "IUKP.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares UK Property
    "IPRP.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares European Property Yield
    "IUSP.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares US Property Yield
    
    # --- DIVIDEND/INCOME UCITS ---
    "VHYL.L": {"USA": 0.45, "Europe": 0.25, "Japan": 0.08, "EM": 0.12, "Other_DM": 0.10},   # Vanguard FTSE All-World High Dividend
    "IDVY.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Euro Dividend
    "IUKD.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares UK Dividend
    "HDLV.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Invesco S&P 500 High Dividend Low Vol
    "QDIV.DE": {"USA": 0.68, "Europe": 0.18, "Japan": 0.07, "EM": 0.0, "Other_DM": 0.07},   # iShares MSCI World Quality Dividend
    
    # --- FACTOR UCITS ---
    "IWMO.L": {"USA": 0.68, "Europe": 0.18, "Japan": 0.07, "EM": 0.0, "Other_DM": 0.07},    # iShares Edge MSCI World Momentum
    "IWVL.L": {"USA": 0.60, "Europe": 0.22, "Japan": 0.10, "EM": 0.0, "Other_DM": 0.08},    # iShares Edge MSCI World Value
    "IWQU.L": {"USA": 0.72, "Europe": 0.16, "Japan": 0.06, "EM": 0.0, "Other_DM": 0.06},    # iShares Edge MSCI World Quality
    "MVOL.L": {"USA": 0.65, "Europe": 0.20, "Japan": 0.08, "EM": 0.0, "Other_DM": 0.07},    # iShares Edge MSCI World Min Vol
    "XDEM.DE": {"USA": 0.60, "Europe": 0.22, "Japan": 0.10, "EM": 0.0, "Other_DM": 0.08},   # Xtrackers MSCI World Value
    "XDEQ.DE": {"USA": 0.72, "Europe": 0.16, "Japan": 0.06, "EM": 0.0, "Other_DM": 0.06},   # Xtrackers MSCI World Quality
    "XDEV.DE": {"USA": 0.65, "Europe": 0.20, "Japan": 0.08, "EM": 0.0, "Other_DM": 0.07},   # Xtrackers MSCI World Min Vol
    
    # --- UK SPECIFIC UCITS ---
    "ISF.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},         # iShares Core FTSE 100
    "MIDD.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares FTSE 250
    "VMID.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Vanguard FTSE 250
    "VUKE.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Vanguard FTSE 100
    "CUKX.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares FTSE 100 (GBP)
    "CUKS.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares UK Equity All Cap
    "IUKP.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares UK Property
    
    # =========================================================================
    # SINGLE COUNTRY EQUITY ETF UCITS - EUROPE
    # =========================================================================
    
    # --- GERMANY (DAX / MDAX / TecDAX) ---
    "EXS1.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares Core DAX
    "DAXEX.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},      # iShares DAX (alt)
    "DBXD.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers DAX
    "EXS3.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares MDAX
    "EXSB.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares TecDAX
    "XMTC.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers MSCI Germany
    "EWG.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares MSCI Germany (Xetra)
    "SXRP.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares Core DAX (Acc)
    "GXF.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},         # WisdomTree Germany Equity
    
    # --- FRANCE (CAC 40) ---
    "CAC.PA": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Lyxor CAC 40
    "CACC.PA": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Amundi CAC 40 (Acc)
    "E40.PA": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # BNP Paribas Easy CAC 40
    "EEE.PA": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # BNP Paribas Easy CAC 40 ESG
    "CACX.PA": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Lyxor CAC 40 (Dist)
    "XMFR.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers MSCI France
    "IFRN.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares MSCI France
    
    # --- ITALY (FTSE MIB) ---
    "IMIB.MI": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares FTSE MIB
    "FTSEMIB.MI": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},    # Lyxor FTSE MIB
    "XMIT.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers MSCI Italy
    "EWI.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},         # iShares MSCI Italy (London)
    "IITA.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares MSCI Italy Capped
    "SMIB.MI": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Amundi FTSE MIB
    
    # --- SPAIN (IBEX 35) ---
    "IBEX.MC": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Lyxor IBEX 35
    "LYXIB.MC": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},      # Lyxor IBEX 35 (alt)
    "XMES.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers MSCI Spain
    "EWP.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},         # iShares MSCI Spain (London)
    "IESP.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares MSCI Spain Capped
    "BBVA.MC": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # BBVA Acción IBEX 35
    
    # --- SWITZERLAND (SMI / SPI) ---
    "EWL.SW": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares MSCI Switzerland
    "XMCH.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers MSCI Switzerland
    "CSSMI.SW": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},      # iShares SMI (CH)
    "SMIM.SW": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares SMIM (Swiss Mid Cap)
    "CHSPI.SW": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},      # iShares SPI (Swiss Performance Index)
    "SPICHA.SW": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},     # UBS ETF SPI
    "SRECHA.SW": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},     # UBS ETF MSCI Switzerland
    "CHDVD.SW": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},      # iShares Swiss Dividend
    
    # --- NETHERLANDS (AEX) ---
    "XMNL.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers MSCI Netherlands
    "EWN.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},         # iShares MSCI Netherlands
    "AEX.AS": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Lyxor AEX
    
    # --- BELGIUM (BEL 20) ---
    "XMBG.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers MSCI Belgium
    "EWK.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},         # iShares MSCI Belgium
    
    # --- AUSTRIA (ATX) ---
    "XMAT.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers MSCI Austria (hypothetical)
    "EWO.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},         # iShares MSCI Austria
    
    # --- PORTUGAL (PSI 20) ---
    "XMPT.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers MSCI Portugal (hypothetical)
    
    # --- IRELAND ---
    "EIRL.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares MSCI Ireland Capped
    
    # --- SWEDEN (OMX Stockholm 30) ---
    "XMSW.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers MSCI Sweden
    "EWD.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},         # iShares MSCI Sweden
    
    # --- NORWAY (OBX) ---
    "XMNO.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers MSCI Norway
    "ENOR.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares MSCI Norway Capped
    
    # --- DENMARK (OMX Copenhagen 25) ---
    "XMDK.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers MSCI Denmark
    "EDEN.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares MSCI Denmark Capped
    
    # --- FINLAND (OMX Helsinki 25) ---
    "XMFI.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers MSCI Finland
    "EFNL.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares MSCI Finland Capped
    
    # --- GREECE (ASE) ---
    "GREK.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Global X MSCI Greece
    "XMGR.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers MSCI Greece (hypothetical)
    
    # --- POLAND (WIG 20) ---
    "XMPL.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers MSCI Poland
    "EPOL.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares MSCI Poland
    
    # --- CZECH REPUBLIC ---
    "XMCZ.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers MSCI Czech Republic (hypothetical)
    
    # --- TURKEY (BIST) ---
    "TUR.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},         # iShares MSCI Turkey
    "XMTU.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers MSCI Turkey
    
    # --- EUROZONE AGGREGATE ---
    "CSEMU.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares Core MSCI EMU
    "SXRV.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares Euro STOXX 50
    "XESC.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers Euro STOXX 50
    "DBXE.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers Euro STOXX 50 (alt)
    "MSE.PA": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Lyxor Euro STOXX 50
    "FEZ.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},         # SPDR Euro STOXX 50
    
    # =========================================================================
    # BOND ETF UCITS - EXTENDED COVERAGE
    # =========================================================================
    
    # --- GOVERNMENT BONDS - USA (Treasury) ---
    "DTLE.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares $ Treasury Bond 20+yr (Dist)
    "IUSU.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares $ Treasury Bond 1-3yr
    "IUSM.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares $ Treasury Bond 3-7yr
    "SXRM.DE": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares $ Treasury Bond 7-10yr (Xetra)
    "DTLA.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares $ Treasury Bond 20+yr (Acc)
    "VUTY.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Vanguard USD Treasury Bond
    "VDTA.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Vanguard USD Treasury Bond (Acc)
    "TREX.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Xtrackers II US Treasuries
    "XUTD.DE": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers II US Treasuries 1-3
    "XUTY.DE": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers II US Treasuries (Xetra)
    
    # --- GOVERNMENT BONDS - EUROZONE ---
    "IBGX.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares EUR Govt Bond 15-30yr
    "IBGM.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares EUR Govt Bond 7-10yr
    "IEGA.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Core EUR Govt Bond (Acc)
    "SEGA.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares EUR Govt Bond 3-5yr
    "VGEA.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Vanguard EUR Eurozone Govt Bond
    "VETY.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Vanguard EUR Govt Bond (Dist)
    "XGLE.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers II Eurozone Govt Bond
    "DBXN.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers II Eurozone Govt Bond 1-3
    "DBXP.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers II Eurozone Govt Bond 3-5
    "DBXQ.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers II Eurozone Govt Bond 5-7
    "DBXR.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers II Eurozone Govt Bond 7-10
    "EUN5.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares EUR Govt Bond 0-1yr
    "EXHE.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares eb.rexx Govt Germany
    "EXHB.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares eb.rexx Govt Germany 1.5-2.5yr
    "EXHC.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares eb.rexx Govt Germany 2.5-5.5yr
    "EXHD.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares eb.rexx Govt Germany 5.5-10.5yr
    "EXHF.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares eb.rexx Govt Germany 10.5+yr
    
    # --- GOVERNMENT BONDS - UK (Gilts) ---
    "IGLT.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Core UK Gilts
    "IGLH.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares UK Gilts 0-5yr
    "IGLS.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares UK Gilts All Stocks
    "VGOV.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Vanguard UK Govt Bond
    "GILS.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Lyxor Core UK Govt Bond
    "INXG.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares UK Index-Linked Gilts
    
    # --- GOVERNMENT BONDS - GLOBAL ---
    "IGLG.L": {"USA": 0.35, "Europe": 0.30, "Japan": 0.15, "EM": 0.05, "Other_DM": 0.15},   # iShares Global Govt Bond
    "VGOV.L": {"USA": 0.35, "Europe": 0.30, "Japan": 0.15, "EM": 0.05, "Other_DM": 0.15},   # Vanguard Global Bond Index
    "XGSH.DE": {"USA": 0.40, "Europe": 0.30, "Japan": 0.12, "EM": 0.05, "Other_DM": 0.13},  # Xtrackers II Global Govt Bond
    
    # --- GOVERNMENT BONDS - JAPAN ---
    "IJPN.L": {"USA": 0.0, "Europe": 0.0, "Japan": 1.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Japan Govt Bond
    
    # --- GOVERNMENT BONDS - SINGLE COUNTRY (Europe) ---
    # ITALY (BTP)
    "IITB.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Italy Govt Bond
    "IBTI.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares Italy Govt Bond (Xetra)
    "XITG.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers II Italy Govt Bond
    "BTPI.MI": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Lyxor BTP Italy Govt Bond
    "BGBI.MI": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Amundi BTP Italy Govt Bond
    "EMI.MI": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Italy Govt Bond (Milano)
    "IITB.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares Italy Govt Bond (DE)
    "XBTI.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers II Italy Govt Bond 1-3
    
    # FRANCE (OAT)
    "IFRB.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares France Govt Bond
    "IFRB.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares France Govt Bond (Xetra)
    "XFRG.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers II France Govt Bond
    "MTF.PA": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Lyxor CAC 40 Daily (-2x) Inverse (proxy OAT)
    "GOAT.PA": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Amundi France Govt Bond
    
    # SPAIN (Bonos)
    "IESP.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Spain Govt Bond
    "IESP.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares Spain Govt Bond (Xetra)
    "XESP.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers II Spain Govt Bond
    
    # GERMANY (Bunds) - Additional
    "IS0L.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares Germany Govt Bond
    "XDEG.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers II Germany Govt Bond
    "BUND.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Lyxor Bund Daily
    "SDEU.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares Germany Govt Bond 0-1yr
    
    # NETHERLANDS
    "INLA.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Netherlands Govt Bond
    "INLA.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares Netherlands Govt Bond (Xetra)
    
    # BELGIUM
    "IBEB.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Belgium Govt Bond
    "IBEB.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares Belgium Govt Bond (Xetra)
    
    # AUSTRIA
    "IBAT.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Austria Govt Bond
    "IBAT.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares Austria Govt Bond (Xetra)
    
    # PORTUGAL
    "IPTE.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Portugal Govt Bond
    "IPTE.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares Portugal Govt Bond (Xetra)
    
    # IRELAND
    "IIRE.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Ireland Govt Bond
    "IIRE.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares Ireland Govt Bond (Xetra)
    
    # FINLAND
    "IFIN.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Finland Govt Bond
    "IFIN.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares Finland Govt Bond (Xetra)
    
    # SWITZERLAND
    "CSBGC7.SW": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},     # iShares Switzerland Govt Bond 7-15yr
    "CSBGC3.SW": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},     # iShares Switzerland Govt Bond 3-7yr
    "AGGS.SW": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # UBS Switzerland Govt Bond
    
    # SWEDEN
    "XSEK.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers II Sweden Govt Bond
    
    # NORWAY
    "XNOK.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers II Norway Govt Bond
    
    # DENMARK
    "XDKK.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers II Denmark Govt Bond
    
    # POLAND
    "XPOL.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers II Poland Govt Bond
    "IPOL.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Poland Govt Bond
    
    # CZECH REPUBLIC
    "XCZK.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers II Czech Republic Govt Bond
    
    # HUNGARY
    "XHUF.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers II Hungary Govt Bond
    
    # --- GOVERNMENT BONDS - SINGLE COUNTRY (Asia/Pacific) ---
    # AUSTRALIA
    "AGVT.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 1.0},        # iShares Australia Govt Bond
    "XAUD.DE": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 1.0},       # Xtrackers II Australia Govt Bond
    
    # CANADA
    "XCAD.DE": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 1.0},       # Xtrackers II Canada Govt Bond
    
    # SINGAPORE
    "XSGD.DE": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 1.0},       # Xtrackers II Singapore Govt Bond
    
    # --- GOVERNMENT BONDS - SINGLE COUNTRY (Emerging Markets) ---
    # CHINA
    "CNYB.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # iShares China CNY Bond
    "CYBA.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # iShares China CNY Bond (Acc)
    "CBON.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # VanEck China Bond
    
    # BRAZIL
    "XBRL.DE": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},       # Xtrackers II Brazil Govt Bond
    
    # MEXICO
    "XMXN.DE": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},       # Xtrackers II Mexico Govt Bond
    
    # SOUTH AFRICA
    "XZAR.DE": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},       # Xtrackers II South Africa Govt Bond
    
    # INDIA
    "IGNY.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # iShares India INR Govt Bond
    
    # INDONESIA
    "XIDR.DE": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},       # Xtrackers II Indonesia Govt Bond
    
    # TURKEY
    "XTRY.DE": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},       # Xtrackers II Turkey Govt Bond
    
    # SOUTH KOREA
    "XKRW.DE": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 1.0},       # Xtrackers II South Korea Govt Bond

    # --- CORPORATE BONDS - USD ---
    "LQDA.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares $ Corp Bond (Acc)
    "SUOA.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares $ Corp Bond 0-3yr
    "LQDH.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares $ Corp Bond (EUR Hedged)
    "VUCP.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Vanguard USD Corporate Bond
    "VCPA.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Vanguard USD Corp Bond (Acc)
    "XUSC.DE": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers II USD Corp Bond
    
    # --- CORPORATE BONDS - EUR ---
    "IEAA.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Core EUR Corp Bond (Acc)
    "IBCX.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares EUR Corp Bond Large Cap
    "IBCS.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares EUR Corp Bond 1-5yr
    "SE15.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares EUR Corp Bond ex-Financials
    "VECP.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Vanguard EUR Corporate Bond
    "VECA.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Vanguard EUR Corp Bond (Acc)
    "XBLC.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers II EUR Corp Bond
    
    # --- CORPORATE BONDS - GBP ---
    "SLXX.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares Core £ Corp Bond
    "IS15.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares £ Corp Bond 1-5yr
    "VUKC.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Vanguard UK Investment Grade Bond
    
    # --- HIGH YIELD BONDS ---
    "IHYG.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares $ High Yield Corp Bond
    "SHYU.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares $ Short Duration High Yield
    "HYLD.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares $ High Yield Corp Bond (EUR Hdg)
    "IHYG.DE": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares $ High Yield Corp (Xetra)
    "EUNW.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # iShares EUR High Yield Corp Bond
    "IHYG.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares EUR High Yield Corp Bond
    "GHYG.L": {"USA": 0.50, "Europe": 0.35, "Japan": 0.0, "EM": 0.10, "Other_DM": 0.05},    # iShares Global High Yield Corp Bond
    
    # --- EMERGING MARKET BONDS ---
    "IEMB.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # iShares JPM $ EM Bond (EUR Hdg)
    "EMBA.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # iShares JPM EM Bond (Acc)
    "SEML.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # iShares JPM EM Local Govt Bond
    "VEMT.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # Vanguard USD EM Govt Bond
    "VEMA.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # Vanguard EM Govt Bond (Acc)
    "XEMB.DE": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},       # Xtrackers II EM Govt Bond
    "EMCR.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # iShares EM Corporate Bond
    
    # --- AGGREGATE / TOTAL BOND ---
    "VAGF.L": {"USA": 0.40, "Europe": 0.30, "Japan": 0.10, "EM": 0.10, "Other_DM": 0.10},   # Vanguard Global Aggregate Bond (GBP Hdg)
    "VAGS.L": {"USA": 0.40, "Europe": 0.30, "Japan": 0.10, "EM": 0.10, "Other_DM": 0.10},   # Vanguard Global Aggregate Bond (EUR Hdg)
    "SAGG.L": {"USA": 0.40, "Europe": 0.30, "Japan": 0.10, "EM": 0.10, "Other_DM": 0.10},   # iShares Core Global Agg Bond (GBP Hdg)
    "AGGU.L": {"USA": 0.40, "Europe": 0.30, "Japan": 0.10, "EM": 0.10, "Other_DM": 0.10},   # iShares Core Global Agg Bond (USD)
    "XBAG.DE": {"USA": 0.40, "Europe": 0.30, "Japan": 0.10, "EM": 0.10, "Other_DM": 0.10},  # Xtrackers II Global Aggregate Bond
    "VDCP.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Vanguard USD Corp 1-3yr Bond
    "VDEA.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Vanguard EUR Corp 1-3yr Bond
    
    # --- INFLATION-LINKED BONDS ---
    "SGIL.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares £ Index-Linked Gilts
    "GILG.L": {"USA": 0.40, "Europe": 0.30, "Japan": 0.15, "EM": 0.05, "Other_DM": 0.10},   # iShares Global Inflation Linked Govt Bond
    "XGIU.DE": {"USA": 0.40, "Europe": 0.30, "Japan": 0.10, "EM": 0.05, "Other_DM": 0.15},  # Xtrackers II Global Infl-Linked Bond
    "ITPE.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares EUR Inflation Linked Govt Bond
    "VTIP.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Vanguard Short-Term Inflation-Protected
    
    # --- SHORT DURATION / MONEY MARKET ---
    "ERNS.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares EUR Ultrashort Bond
    "ERNE.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares EUR Ultrashort Bond (Acc)
    "XEOD.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers II EUR Overnight Rate Swap
    "CSH2.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Lyxor Smart Overnight Return EUR
    "XSTR.DE": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},       # Xtrackers EUR Cash Swap
    
    # =========================================================================
    # ACTIVE EQUITY FUNDS UCITS (Fondi Attivi Azionari)
    # =========================================================================
    
    # --- ACTIVE GLOBAL EQUITY ---
    "FCIT.L": {"USA": 0.55, "Europe": 0.15, "Japan": 0.08, "EM": 0.15, "Other_DM": 0.07},   # F&C Investment Trust
    "SMT.L": {"USA": 0.50, "Europe": 0.10, "Japan": 0.05, "EM": 0.25, "Other_DM": 0.10},    # Scottish Mortgage Investment Trust
    "JGGI.L": {"USA": 0.55, "Europe": 0.18, "Japan": 0.10, "EM": 0.10, "Other_DM": 0.07},   # JPMorgan Global Growth & Income
    "MWY.L": {"USA": 0.55, "Europe": 0.20, "Japan": 0.08, "EM": 0.10, "Other_DM": 0.07},    # Mid Wynd International
    "BNKR.L": {"USA": 0.50, "Europe": 0.20, "Japan": 0.10, "EM": 0.12, "Other_DM": 0.08},   # Bankers Investment Trust
    "CTY.L": {"USA": 0.40, "Europe": 0.30, "Japan": 0.08, "EM": 0.12, "Other_DM": 0.10},    # City of London Investment Trust
    "WTAN.L": {"USA": 0.50, "Europe": 0.20, "Japan": 0.10, "EM": 0.12, "Other_DM": 0.08},   # Witan Investment Trust
    "ATT.L": {"USA": 0.45, "Europe": 0.25, "Japan": 0.10, "EM": 0.12, "Other_DM": 0.08},    # Alliance Trust
    
    # --- ACTIVE USA EQUITY ---
    "JPEA.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # JPMorgan American IT
    "JAM.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},         # JPMorgan American IT
    "AGT.L": {"USA": 0.95, "Europe": 0.02, "Japan": 0.0, "EM": 0.02, "Other_DM": 0.01},     # AVI Global Trust (US focused)
    
    # --- ACTIVE EUROPE EQUITY ---
    "JEO.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},         # JPMorgan European IT
    "FEV.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},         # Fidelity European Trust
    "HEFT.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Henderson European Focus Trust
    "ESCT.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # European Smaller Companies Trust
    "BSEC.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # BlackRock Smaller Companies Trust
    
    # --- ACTIVE UK EQUITY ---
    "FRCL.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Fidelity Special Values
    "FGT.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},         # Finsbury Growth & Income Trust
    "LGEN.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Legal & General Group (proxy UK)
    "TMPL.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Temple Bar IT
    "MRC.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},         # Mercantile IT (UK Small/Mid)
    "SCIN.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Scottish Investment Trust
    "LWDB.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Law Debenture Corporation
    "JEMI.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # JPMorgan Elect Managed Income
    
    # --- ACTIVE ASIA / EM EQUITY ---
    "JMG.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},         # JPMorgan Emerging Markets IT
    "TEMIT.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},       # Templeton Emerging Markets IT
    "BGEM.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # Baillie Gifford Emerging Markets
    "PAC.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.30, "EM": 0.50, "Other_DM": 0.20},      # Pacific Assets Trust
    "JFJ.L": {"USA": 0.0, "Europe": 0.0, "Japan": 1.0, "EM": 0.0, "Other_DM": 0.0},         # JPMorgan Japanese IT
    "BRJP.L": {"USA": 0.0, "Europe": 0.0, "Japan": 1.0, "EM": 0.0, "Other_DM": 0.0},        # Baillie Gifford Japan Trust
    "SCAM.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.20, "EM": 0.60, "Other_DM": 0.20},     # Scottish Oriental Smaller Cos
    "AAIF.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.15, "EM": 0.65, "Other_DM": 0.20},     # abrdn Asian Income Fund
    "FAV.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.10, "EM": 0.70, "Other_DM": 0.20},      # Fidelity Asian Values
    "JII.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},         # JPMorgan Indian IT
    "FAS.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},         # Fidelity Asian Values (EM)
    "FCSS.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # Fidelity China Special Sits
    "JCGI.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # JPMorgan China Growth & Income
    
    # --- ACTIVE INCOME / DIVIDEND ---
    "MNKS.L": {"USA": 0.45, "Europe": 0.25, "Japan": 0.08, "EM": 0.12, "Other_DM": 0.10},   # Monks Investment Trust
    "MRCH.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Merchants Trust
    "HFEL.L": {"USA": 0.0, "Europe": 0.05, "Japan": 0.15, "EM": 0.60, "Other_DM": 0.20},    # Henderson Far East Income
    "EDGF.L": {"USA": 0.35, "Europe": 0.30, "Japan": 0.10, "EM": 0.15, "Other_DM": 0.10},   # Edinburgh IT (Glbl Income)
    
    # --- ACTIVE SMALL CAP ---
    "HSL.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},         # Henderson Smaller Companies IT
    "BGS.L": {"USA": 0.40, "Europe": 0.25, "Japan": 0.10, "EM": 0.15, "Other_DM": 0.10},    # Baillie Gifford Shin Nippon
    "ABSC.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # abrdn UK Smaller Companies
    "SLS.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},         # Standard Life UK Smaller Cos
    
    # --- ACTIVE THEMATIC / SECTOR ---
    "HHV.L": {"USA": 0.55, "Europe": 0.15, "Japan": 0.05, "EM": 0.15, "Other_DM": 0.10},    # Henderson High Income Trust
    "PCFT.L": {"USA": 0.45, "Europe": 0.20, "Japan": 0.10, "EM": 0.15, "Other_DM": 0.10},   # Polar Capital Technology Trust
    "BRWM.L": {"USA": 0.60, "Europe": 0.15, "Japan": 0.10, "EM": 0.10, "Other_DM": 0.05},   # BlackRock World Mining Trust
    "WWH.L": {"USA": 0.50, "Europe": 0.20, "Japan": 0.10, "EM": 0.10, "Other_DM": 0.10},    # Worldwide Healthcare Trust
    "HGT.L": {"USA": 0.75, "Europe": 0.10, "Japan": 0.0, "EM": 0.10, "Other_DM": 0.05},     # HgCapital Trust (Tech PE)
    "PHI.L": {"USA": 0.40, "Europe": 0.10, "Japan": 0.05, "EM": 0.0, "Other_DM": 0.45},     # Pantheon International (PE)
    "PNL.L": {"USA": 0.50, "Europe": 0.15, "Japan": 0.05, "EM": 0.10, "Other_DM": 0.20},    # Personal Assets Trust
    "RICA.L": {"USA": 0.40, "Europe": 0.25, "Japan": 0.05, "EM": 0.10, "Other_DM": 0.20},   # Ruffer Investment Company
    "CGT.L": {"USA": 0.55, "Europe": 0.20, "Japan": 0.08, "EM": 0.10, "Other_DM": 0.07},    # Capital Gearing Trust
    
    # =========================================================================
    # ACTIVE BOND FUNDS UCITS (Fondi Attivi Obbligazionari)
    # =========================================================================
    
    # --- ACTIVE GLOBAL BOND ---
    "TPIF.L": {"USA": 0.40, "Europe": 0.30, "Japan": 0.10, "EM": 0.10, "Other_DM": 0.10},   # TwentyFour Select Monthly Inc
    "TRIG.L": {"USA": 0.30, "Europe": 0.50, "Japan": 0.05, "EM": 0.05, "Other_DM": 0.10},   # Renewables Infrastructure Group
    "BIPS.L": {"USA": 0.40, "Europe": 0.35, "Japan": 0.08, "EM": 0.10, "Other_DM": 0.07},   # Baillie Gifford Strategic Bond
    "NCYF.L": {"USA": 0.35, "Europe": 0.35, "Japan": 0.05, "EM": 0.15, "Other_DM": 0.10},   # CQS New City High Yield
    
    # --- ACTIVE UK/EUROPE BOND ---
    "CCPE.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # CC Japan Income & Growth
    "CYN.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},         # City Merchants High Yield
    "HDIV.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # Henderson Diversified Income
    
    # --- INFRASTRUCTURE / REAL ASSETS ---
    "INPP.L": {"USA": 0.05, "Europe": 0.85, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.10},     # International Public Partnerships
    "HICL.L": {"USA": 0.05, "Europe": 0.85, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.10},     # HICL Infrastructure
    "BBGI.L": {"USA": 0.10, "Europe": 0.70, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.20},     # BBGI Global Infrastructure
    "GCP.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},         # GCP Infrastructure Investments
    "GRID.L": {"USA": 0.15, "Europe": 0.60, "Japan": 0.05, "EM": 0.10, "Other_DM": 0.10},   # Gresham House Energy Storage
    "NESF.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # NextEnergy Solar Fund
    "UKW.L": {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},         # Greencoat UK Wind
    "FSFL.L": {"USA": 0.05, "Europe": 0.80, "Japan": 0.0, "EM": 0.05, "Other_DM": 0.10},    # Foresight Solar Fund
    "JLEN.L": {"USA": 0.0, "Europe": 0.90, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.10},      # JLEN Environmental Assets
    "INFR.L": {"USA": 0.45, "Europe": 0.25, "Japan": 0.08, "EM": 0.12, "Other_DM": 0.10},   # iShares Global Infrastructure
    "IGF": {"USA": 0.45, "Europe": 0.25, "Japan": 0.08, "EM": 0.12, "Other_DM": 0.10},      # iShares Global Infrastructure (US)
    "PAVE": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},          # Global X US Infrastructure
    "IFRA": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},          # iShares US Infrastructure
    
    # --- DEFENSE & AEROSPACE ---
    "DFNS.L": {"USA": 0.70, "Europe": 0.25, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.05},     # VanEck Defense UCITS
    "XAR": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},           # SPDR S&P Aerospace & Defense
    "ITA": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},           # iShares US Aerospace & Defense
    "PPA": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},           # Invesco Aerospace & Defense
    "DFEN": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},          # Direxion Daily Aerospace & Defense Bull
    
    # --- TAIWAN (EM Asia - Semiconductor heavy) ---
    "ITWN.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # iShares MSCI Taiwan
    "EWT": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},           # iShares MSCI Taiwan (US)
    
    # --- SEMICONDUCTORS (Global exposure, heavy USA/Taiwan/Korea) ---
    "SEMI.L": {"USA": 0.65, "Europe": 0.05, "Japan": 0.05, "EM": 0.20, "Other_DM": 0.05},   # iShares Semiconductor UCITS
    "SOXX": {"USA": 0.85, "Europe": 0.02, "Japan": 0.03, "EM": 0.08, "Other_DM": 0.02},     # iShares PHLX Semiconductor (US heavy)
    "SMH": {"USA": 0.80, "Europe": 0.03, "Japan": 0.02, "EM": 0.12, "Other_DM": 0.03},      # VanEck Semiconductor
    "SOXQ": {"USA": 0.85, "Europe": 0.02, "Japan": 0.03, "EM": 0.08, "Other_DM": 0.02},     # Invesco PHLX Semiconductor
    
    # --- JAPAN SMALL CAP ---
    "ISJP.L": {"USA": 0.0, "Europe": 0.0, "Japan": 1.0, "EM": 0.0, "Other_DM": 0.0},        # iShares MSCI Japan Small Cap
    "SCJ": {"USA": 0.0, "Europe": 0.0, "Japan": 1.0, "EM": 0.0, "Other_DM": 0.0},           # iShares MSCI Japan Small Cap (US)
    "DXJS": {"USA": 0.0, "Europe": 0.0, "Japan": 1.0, "EM": 0.0, "Other_DM": 0.0},          # WisdomTree Japan SmallCap
    
    # --- WORLD SMALL CAP ---
    "WSML.L": {"USA": 0.58, "Europe": 0.18, "Japan": 0.10, "EM": 0.04, "Other_DM": 0.10},   # iShares MSCI World Small Cap
    "IUSN.L": {"USA": 0.58, "Europe": 0.18, "Japan": 0.10, "EM": 0.04, "Other_DM": 0.10},   # iShares MSCI World Small Cap (alt)
    
    # --- USA SMALL CAP UCITS ---
    "USSC.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # SPDR Russell 2000 US Small Cap
    "IUS3.L": {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0},        # iShares MSCI USA Small Cap
    
    # --- EMERGING MARKETS IMI (Broad) ---
    "EMIM.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # iShares Core MSCI EM IMI
    "EIMI.L": {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0},        # iShares Core MSCI EM IMI (alt)
    
    # --- PRIVATE CREDIT / ALTERNATIVE INCOME ---
    "BGLP.L": {"USA": 0.40, "Europe": 0.40, "Japan": 0.0, "EM": 0.10, "Other_DM": 0.10},    # BioPharma Credit
    "FAIR.L": {"USA": 0.30, "Europe": 0.50, "Japan": 0.0, "EM": 0.10, "Other_DM": 0.10},    # Fair Oaks Income Fund
    "SMIF.L": {"USA": 0.20, "Europe": 0.60, "Japan": 0.0, "EM": 0.10, "Other_DM": 0.10},    # TwentyFour Income Fund
    "RECI.L": {"USA": 0.05, "Europe": 0.85, "Japan": 0.0, "EM": 0.05, "Other_DM": 0.05},    # Real Estate Credit Investments
}

# FIX: DEFAULT_GEO ora genera un WARNING esplicito invece di assumere silenziosamente
DEFAULT_GEO = {"USA": 0.50, "Europe": 0.20, "Japan": 0.10, "EM": 0.10, "Other_DM": 0.10}
DEFAULT_GEO_WARNING = True  # Flag per segnalare uso di default


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


def _infer_geo_from_classification(ticker: str) -> Dict[str, float]:
    """
    Infer geographic exposure from ticker classification when not found in GEO_EXPOSURE.
    
    Uses heuristics based on:
    - EM single country classification → 100% EM
    - Core Global classification → global diversified
    - Core Developed classification → DM markets
    - Small Cap → depends on other hints
    - Bond/Gold → typically 0 geographic exposure for commodities
    
    Returns:
        Inferred geographic exposure dict, or None if can't infer
    """
    ticker_clean = ticker.upper().split('.')[0]
    
    # 1. EM Single Country → 100% EM
    if ticker_clean in EM_SINGLE_COUNTRY_ETF or any(kw in ticker_clean for kw in EM_SINGLE_COUNTRY_ETF):
        return {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0}
    
    # 2. Emerging Broad → 100% EM
    if ticker_clean in EMERGING_BROAD_ETF or any(kw in ticker_clean for kw in EMERGING_BROAD_ETF):
        return {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0}
    
    # 3. Core Global → global diversified (60% USA typical MSCI ACWI)
    if ticker_clean in CORE_GLOBAL_ETF or any(kw in ticker_clean for kw in CORE_GLOBAL_ETF):
        return {"USA": 0.60, "Europe": 0.15, "Japan": 0.06, "EM": 0.12, "Other_DM": 0.07}
    
    # 4. Core Developed → MSCI World allocation (no EM)
    if ticker_clean in CORE_DEVELOPED_ETF or any(kw in ticker_clean for kw in CORE_DEVELOPED_ETF):
        return {"USA": 0.68, "Europe": 0.18, "Japan": 0.07, "EM": 0.0, "Other_DM": 0.07}
    
    # 5. Gold/Commodity → no geographic exposure (physical assets)
    if ticker_clean in GOLD_COMMODITY_ETF or any(kw in ticker_clean for kw in GOLD_COMMODITY_ETF):
        return {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0}
    
    # 6. Check ticker suffix patterns for UCITS ETFs
    full_ticker = ticker.upper()
    
    # London-listed (.L) - often UCITS, could be UK or global
    if full_ticker.endswith('.L'):
        # If ticker contains India/China/EM hints
        if any(hint in ticker_clean for hint in ['IND', 'CHN', 'EM', 'BRIC']):
            return {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 1.0, "Other_DM": 0.0}
        # UK specific hints
        if any(hint in ticker_clean for hint in ['UK', 'FTSE', 'GBP']):
            return {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0}
    
    # Xetra-listed (.DE) - often German or European focus
    if full_ticker.endswith('.DE'):
        if any(hint in ticker_clean for hint in ['DAX', 'GER', 'EUR']):
            return {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0}
    
    # Milan-listed (.MI) - typically Italian
    if full_ticker.endswith('.MI'):
        return {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0}
    
    # Paris-listed (.PA) - typically French or Eurozone
    if full_ticker.endswith('.PA'):
        return {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0}
    
    # 7. Sector ETFs - typically USA-focused if US-listed
    if ticker_clean in SECTOR_ETF or any(kw in ticker_clean for kw in SECTOR_ETF):
        if not any(full_ticker.endswith(suffix) for suffix in ['.L', '.DE', '.MI', '.PA', '.AS']):
            return {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0}
    
    # 8. Bond ETFs - check issuer hints
    if ticker_clean in BOND_ETF or any(kw in ticker_clean for kw in BOND_ETF):
        if any(hint in ticker_clean for hint in ['US', 'TLT', 'SHY', 'IEF', 'TIPS']):
            return {"USA": 1.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0}
        if any(hint in ticker_clean for hint in ['EUR', 'BTP', 'BUND']):
            return {"USA": 0.0, "Europe": 1.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0}
        # Global aggregate
        return {"USA": 0.40, "Europe": 0.30, "Japan": 0.10, "EM": 0.10, "Other_DM": 0.10}
    
    # Cannot infer - return None to use DEFAULT_GEO
    return None


def calculate_geographic_exposure(tickers: list, weights: np.ndarray) -> Dict[str, Any]:
    """
    Calcola l'esposizione geografica REALE del portafoglio,
    considerando la composizione interna di ogni ETF.
    
    Returns:
        Dict con esposizioni geografiche + lista ticker unmapped + inferred list
        
    IMPROVEMENT (Issue #23): 
    - Now uses smart inference based on ticker classification when not in mapping
    - Tracks both completely unmapped tickers and inferred ones
    - Reduces false 60% USA assumptions for non-US ETFs
    """
    geo_totals = {"USA": 0.0, "Europe": 0.0, "Japan": 0.0, "EM": 0.0, "Other_DM": 0.0}
    unmapped_tickers = []  # Tickers using DEFAULT_GEO (truly unknown)
    inferred_tickers = []  # Tickers using inference (better than default)
    
    for i, ticker in enumerate(tickers):
        ticker_clean = ticker.upper().split('.')[0]
        full_ticker = ticker.upper()
        weight = weights[i]
        
        # 1. Try exact match first
        geo_map = None
        if ticker_clean in GEO_EXPOSURE:
            geo_map = GEO_EXPOSURE[ticker_clean]
        elif full_ticker in GEO_EXPOSURE:
            geo_map = GEO_EXPOSURE[full_ticker]
        else:
            # 2. Try partial match
            for key in GEO_EXPOSURE:
                key_base = key.split('.')[0]
                if key_base == ticker_clean:
                    geo_map = GEO_EXPOSURE[key]
                    break
        
        # 3. If not found in mapping, try smart inference
        if geo_map is None:
            geo_map = _infer_geo_from_classification(ticker)
            if geo_map is not None:
                inferred_tickers.append((ticker, weight, "inferred"))
        
        # 4. Final fallback to DEFAULT_GEO
        if geo_map is None:
            geo_map = DEFAULT_GEO
            unmapped_tickers.append((ticker, weight))
        
        for region, pct in geo_map.items():
            geo_totals[region] += weight * pct
    
    # Include metadata in return
    geo_totals["_unmapped"] = unmapped_tickers
    geo_totals["_inferred"] = inferred_tickers
    
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


def quick_composition_estimate(tickers: List[str], weights: np.ndarray) -> Dict[str, float]:
    """
    Quick estimate of portfolio composition for Rule 8 benchmark comparison.
    Returns defensive%, thematic%, unclassified%.
    
    This is a fast heuristic used BEFORE full portfolio analysis.
    """
    total_defensive = 0.0
    total_thematic = 0.0
    total_unclassified = 0.0
    
    for ticker, weight in zip(tickers, weights):
        classification = classify_ticker(ticker)
        
        if classification["is_bond"] or classification["is_gold_commodity"] or classification["is_defensive"]:
            total_defensive += weight
        elif classification["is_thematic"] or classification["is_em_single"]:
            total_thematic += weight
        elif not any([classification["is_core_global"], classification["is_core_developed"], 
                     classification["is_emerging_broad"], classification["is_factor"],
                     classification["is_small_cap"], classification["is_reit"]]):
            # Not recognized as any standard category
            total_unclassified += weight
    
    return {
        "total_defensive": total_defensive,
        "total_thematic": total_thematic,
        "total_unclassified": total_unclassified,
        "has_sector_tilts": total_thematic > 0.05 or total_unclassified > 0.15
    }