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


PORTFOLIO = {
    # CORE GLOBALE (growth engine)
    "VT":   0.35,   # Vanguard Total World Stock ETF (dal 2008, proxy globale robusto)
    # se vuole più storico: sostituibile con mix IVV+VEU

    # USA – GROWTH LEADER
    "IVV":  0.20,   # S&P 500 (storico lunghissimo, crescita strutturale)

    # EUROPA
    "VGK":  0.10,   # MSCI Europe (storico >20 anni)

    # GIAPPONE
    "EWJ":  0.08,   # MSCI Japan (storico >25 anni)

    # EMERGING MARKETS
    "EEM":  0.10,   # MSCI Emerging Markets (dal 2003)

    # ASIA PACIFICO ex-Japan
    "VPL":  0.07,   # Asia-Pacifico sviluppato (Australia, HK, Singapore)

    # SMALL CAPS (growth + size premium)
    "IWM":  0.10    # Russell 2000 (dal 2000)
}

PORTFOLIO = {
    # USA
    "IVV": 0.50,         # S&P 500 – core USA (storico >20 anni)

    # SMALL CAPS GLOBALI (proxy World Small Cap)
    "IWM": 0.15,         # Russell 2000 – small caps (storico >20 anni)

    # EUROPA
    "VGK": 0.15,         # Europe ETF (storico >20 anni)

    # REGNO UNITO (FTSE 100)
    "EWU": 0.10,         # MSCI United Kingdom (proxy UK large-cap, storico >20 anni)

    # TAIWAN
    "EWT": 0.10          # MSCI Taiwan (storico >20 anni)
}

PORTFOLIO = {
    # 🇺🇸 STATI UNITI
    "IVV": 0.18,        # S&P 500 – USA Large Cap
    "IJR": 0.07,        # USA Small Cap (S&P SmallCap 600)

    # 🇯🇵 GIAPPONE
    "EWJ": 0.10,        # Japan Large Cap
    "SCJ": 0.05,        # Japan Small Cap

    # 🇬🇧 REGNO UNITO
    "EWU": 0.07,        # UK Large Cap (FTSE 100 heavy)
    "EWUS": 0.04,       # UK Small Cap

    # 🇩🇪 GERMANIA
    "EWG": 0.08,        # Germany Large Cap

    # 🇫🇷 FRANCIA
    "EWQ": 0.08,        # France Large Cap

    # 🇨🇭 SVIZZERA
    "EWL": 0.08,        # Switzerland Large Cap

    # 🇮🇹 ITALIA
    "EWI": 0.05,        # Italy Large Cap

    # 🇨🇳 CINA
    "MCHI": 0.08,       # China Large Cap

    # 🇮🇳 INDIA
    "INDA": 0.07,       # India Large Cap


    # 🇹🇼 TAIWAN
    "EWT": 0.05         # Taiwan Large Cap
}

PORTFOLIO = {
    # 🌍 CORE GLOBALE (efficienza / base)
    "VWCE.DE": 0.35,    # Vanguard FTSE All-World UCITS – core globale cap-weight

    # 🇺🇸 FACTOR TILT USA (value + size)
    "IUSV.DE": 0.10,    # iShares MSCI USA Value UCITS ETF
    # Nota: UCITS small-cap value puro non esiste → value USA è il proxy più corretto

    # 🏥 TILT DIFENSIVI / STRUTTURALI
    "IUHC.DE": 0.08,    # iShares MSCI World Health Care UCITS ETF
    "EXI1.DE": 0.07,    # iShares STOXX Europe 600 Industrials UCITS ETF
    "SOXX.L": 0.05,    # iShares Semiconductor UCITS ETF

    # 🌍 GEOGRAFIA EX-USA MIRATA
    "VGK.DE": 0.10,     # Vanguard FTSE Developed Europe UCITS ETF
    "IJPA.DE": 0.05,    # iShares MSCI Japan UCITS ETF
    "IIND.AS": 0.05,    # iShares MSCI India UCITS ETF

    # 🛡️ STABILIZZATORI (decorrelazione reale)
    "AGGH.DE": 0.10,    # iShares Core Global Aggregate Bond UCITS ETF (EUR hedged)
    "SGLD.DE": 0.05     # Invesco Physical Gold ETC (oro fisico)
}

PORTFOLIO = {
    # 🇺🇸 USA
    "CSPX.L": 0.22,   # USA Large Cap (S&P 500)
    "USSC.L": 0.08,   # USA Small Cap

    # 🌍 EUROPA
    "IMEU.L": 0.12,   # Europe Developed

    # 🌏 EMERGING MARKETS
    "EMIM.L": 0.12,   # Emerging Markets IMI

    # 🇯🇵 GIAPPONE
    "SJPA.L": 0.06,   # Japan Large Cap
    "SCJ.L":  0.03,   # Japan Small Cap

    # 🇬🇧 REGNO UNITO
    "CUKS.L": 0.04,   # UK Large Cap
    "UKSC.L": 0.02,   # UK Small Cap

    # 🌍 SMALL CAPS GLOBALI
    "IUSN.L": 0.10,   # World Small Cap

    # 🇹🇼 TAIWAN
    "ITWN.L": 0.05,   # Taiwan

    # 🛡️ DIFESA
    "DFNS.L": 0.08,   # Defense & Aerospace

    # 🤖 AI – INFRASTRUTTURA
    "SEMI.L": 0.04,   # Semiconductors
    "INFR.L": 0.04    # Global Infrastructure
}
portfolio = {
    # =========================
    # USA – LARGE CAP GROWTH
    # =========================
    "CSPX.L": 0.22,   # S&P 500 (growth core, beta driver)
    
    # =========================
    # USA – SMALL CAP
    # =========================
    "USSC.L": 0.08,   # USA Small Cap (beta + convexity)
    
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
    "WSML.L": 0.10,   # Global Small Cap (size premium)
    
    # =========================
    # TEMATICI – GROWTH / AI / DEFENCE
    # =========================
    "SEMI.L": 0.04,   # Semiconductors
    "DFNS.L": 0.08,   # Defence (geopolitical growth)
    "INFR.L": 0.04    # Infrastructure / AI backbone
}
