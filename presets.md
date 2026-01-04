PORTFOLIO = {
    # Ticker Yahoo Finance: peso percentuale
    "VWCE.DE": 0.73,    # Vanguard FTSE All-World - CORE
    "EIMI.L": 0.10,     # iShares Core MSCI EM IMI - EM Tilt
    "INFR.L": 0.07,     # iShares Global Infrastructure - Satellite Difensivo
    "DFEN.DE": 0.05,    # VanEck Defense - Satellite Tematico
    "NUKL.DE": 0.05,    # VanEck Uranium and Nuclear - Satellite Tematico
}

PORTFOLIO = {
    # CORE 83%
    "VWCE.DE": 0.73,    # Core globale All-World
    "EIMI.L": 0.10,     # Emerging Markets (tilt EM)
    
    # SATELLITE 17%
    "INFR.L": 0.07,     # Infrastructure (decorrelante)
    "DFEN.DE": 0.05,    # Difesa (tematico)
    "NUKL.DE": 0.05,    # Nucleare / energia (tematico)
}

PORTFOLIO_EQUITY_BACKTEST_READY = {

    # CORE GLOBALE
    "VT": 0.40,        # Vanguard Total World Stock ETF (dal 2008)

    # USA
    "IVV": 0.15,       # iShares Core S&P 500 (dal 2000)

    # EUROPA
    "VGK": 0.10,       # Vanguard FTSE Europe ETF (dal 2005)

    # EMERGING MARKETS
    "EEM": 0.10,       # iShares MSCI Emerging Markets (dal 2003)

    # GIAPPONE
    "EWJ": 0.07,       # iShares MSCI Japan (dal 1996)

    # PACIFICO ex-Japan
    "EPP": 0.05,       # iShares MSCI Pacific ex-Japan (dal 2001)

    # SMALL CAPS USA
    "IWM": 0.05,       # iShares Russell 2000 (dal 2000)

    # DIFESA / AEROSPACE
    "ITA": 0.04,       # iShares U.S. Aerospace & Defense (dal 2006)

    # ENERGIA / INFRASTRUTTURE
    "XLE": 0.04        # Energy Select Sector SPDR (dal 1998)
}

PORTFOLIO_EQUITY_REGIONAL_THEMATIC = {

    # USA
    "IVV": 0.22,        # S&P 500 – core USA

    # EUROPA
    "EXSA.DE": 0.15,    # EURO STOXX 600 (proxy Euro 400/600)

    # GIAPPONE
    "EWJ": 0.10,        # MSCI Japan

    # REGNO UNITO
    "EWU": 0.08,        # MSCI United Kingdom

    # INDIA
    "INDA": 0.07,       # MSCI India

    # EMERGING MARKETS (broad)
    "EEM": 0.12,        # MSCI Emerging Markets

    # SMALL CAPS GLOBALI
    "IUSN.DE": 0.10,    # MSCI World Small Cap

    # URANIO / NUCLEARE
    "URA": 0.08,        # Global Uranium & Nuclear Energy

    # AI INFRASTRUCTURE / HARDWARE
    "SRVR": 0.08       # Data centers, networks, digital infrastructure
}


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
