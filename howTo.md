# Portfolio Analysis Tool

## Descrizione

Questo script Python permette di analizzare un portafoglio di investimento (ETF, azioni, etc.) scaricando i dati storici da Yahoo Finance e calcolando diverse metriche di performance e rischio.

## Requisiti

```bash
pip install -r requirements.txt
```

Oppure installa manualmente:
```bash
pip install numpy pandas yfinance matplotlib
```

## Configurazione

Modifica il dizionario `CONFIG` in `main.py`:

```python
CONFIG = {
    "tickers": [
        "VWCE.DE",   # Vanguard FTSE All-World
        "AGGH.L",    # iShares Core Global Aggregate Bond
        "SGLD.L",    # Invesco Physical Gold
    ],
    "weights": [0.70, 0.20, 0.10],  # Pesi (verranno normalizzati)
    "start_date": "2019-01-01",
    "end_date": None,               # None = oggi
    "risk_free_annual": 0.02,       # Tasso risk-free (es. 2%)
    "rebalance": "M",               # Frequenza ribilanciamento
}
```

### Parametri

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `tickers` | list | Lista di ticker Yahoo Finance |
| `weights` | list | Pesi del portafoglio (vengono normalizzati) |
| `start_date` | str | Data inizio analisi (YYYY-MM-DD) |
| `end_date` | str/None | Data fine (None = oggi) |
| `risk_free_annual` | float | Tasso risk-free annuo per Sharpe |
| `rebalance` | str/None | "M" mensile, "Q" trimestrale, None = buy&hold |

### Trovare i Ticker Corretti

I ticker devono essere quelli di Yahoo Finance. Alcuni esempi:

| ETF | Ticker Yahoo |
|-----|--------------|
| Vanguard FTSE All-World (Xetra) | VWCE.DE |
| iShares MSCI World (Xetra) | EUNL.DE |
| iShares Core S&P 500 (London) | CSPX.L |
| Invesco Physical Gold (London) | SGLD.L |

Verifica i ticker su [finance.yahoo.com](https://finance.yahoo.com/).

## Esecuzione

```bash
python main.py
```

## Output

### Metriche Calcolate

- **CAGR**: Compound Annual Growth Rate (rendimento annualizzato)
- **Volatility**: Volatilità annualizzata (deviazione standard)
- **Sharpe Ratio**: Rendimento aggiustato per il rischio
- **Max Drawdown**: Massima perdita dal picco

### Risk Contribution

Mostra quanto ogni asset contribuisce al rischio totale del portafoglio (approccio varianza-covarianza).

### Grafici

1. **Equity Curve**: Andamento del valore del portafoglio (base 1)
2. **Drawdown Chart**: Perdite percentuali dai massimi

## Esempio di Output

```
==================================================
PORTFOLIO SUMMARY
==================================================
CAGR:            8.45%
Volatility:     12.30%
Sharpe:           0.52
Max DD:         -25.12%

==================================================
ETF METRICS (annualized)
==================================================
         Weight    CAGR     Vol  RiskContrib%
VWCE.DE  0.7000  0.0920  0.1580        0.8500
AGGH.L   0.2000  0.0120  0.0450        0.0800
SGLD.L   0.1000  0.0650  0.1200        0.0700
```

## Limitazioni

- I pesi negativi (short) non sono supportati
- Il ribilanciamento non considera costi di transazione
- I dati dipendono dalla disponibilità su Yahoo Finance

## Struttura del Progetto

```
analisiPortafogli/
├── main.py           # Script principale
├── howTo.md          # Questa documentazione
├── requirements.txt  # Dipendenze Python
└── workReport.md     # Report delle modifiche
```
