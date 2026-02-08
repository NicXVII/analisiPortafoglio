# Portfolio Engine - How To

## Descrizione
Tool Python per analizzare portafogli di ETF/fondi usando dati storici Yahoo Finance. Calcola metriche di performance e rischio, analisi strutturale e produce report (console/PDF/JSON).

## Installazione
```bash
pip install -r requirements.txt
```

Per usare lo script CLI registrato:
```bash
pip install -e .
```

## Configurazione
La configurazione vive in `src/portfolio_engine/config/user_config.py`.
Le sezioni principali sono:
- `PORTFOLIO`: tickers e pesi
- `ANALYSIS`: date, risk-free, rebalance, VaR
- `EXPORT`: formati e output
- `RISK_INTENT`: livello di rischio dichiarato

Esempio minimo:
```python
RISK_INTENT = "GROWTH"

PORTFOLIO = {
    "VWCE.DE": 0.70,
    "AGGH.L": 0.20,
    "SGLD.L": 0.10,
}

ANALYSIS = {
    "years_history": 5,
    "start_date": None,
    "end_date": None,
    "risk_free_annual": 0.02,
    "rebalance": "ME",
    "var_confidence": 0.95,
}
```

### Config da file (JSON/YAML)
Puoi caricare un file esterno con:
```bash
python -m scripts.analyze_portfolio --config path/to/config.json
```
Oppure via variabile d ambiente:
```bash
PORTFOLIO_CONFIG_PATH=path/to/config.yaml python -m scripts.analyze_portfolio
```

Formato accettato:
- JSON con chiavi `tickers`, `weights`, `analysis`, `export`, `risk_intent`
- Oppure `portfolio` come mapping ticker->peso (verra normalizzato)

## Esecuzione
Metodo consigliato (wrapper CLI):
```bash
python -m scripts.analyze_portfolio
```

Dopo `pip install -e .`:
```bash
analyze-portfolio
```

## Output
Gli output vengono salvati in `output/` se `EXPORT["enabled"] = True`.
Per default lo script salva un PDF in `output/portfolio_analysis.pdf`.

Metriche principali:
- CAGR, volatilita annualizzata
- Sharpe / Sortino / Calmar
- Max Drawdown
- VaR / CVaR
- Risk contribution

## Integration tests nel report
Se vuoi includere i risultati dei test di integrazione nel report finale (console/PDF),
imposta in `src/portfolio_engine/config/user_config.py`:
```python
RUN_INTEGRATION_TESTS = True
```
I risultati vengono anche salvati in `output/data/integration_test_results.json`.

## Storage portafogli
Ogni avvio salva automaticamente la configurazione del portafoglio in un archivio
persistente con deduplicazione via hash (SHA-256). Config in:
`src/portfolio_engine/config/user_config.py`:
```python
PORTFOLIO_STORAGE = {
    "enabled": True,
    "store_dir": "./output/portfolio_store",
}
```
File generati:
- `output/portfolio_store/portfolios.jsonl` (append-only)
- `output/portfolio_store/index.json` (hash index per lookup rapido)

## Limitazioni note
- Fonte dati unica: Yahoo Finance (nessun ETF delisted)
- Possibile survivorship bias sui dati storici
- Nessuna previsione o ottimizzazione automatica
- Top holdings limitati alla disponibilita Yahoo

## Struttura del progetto (attuale)
```
analisiPortafogli/
├── src/portfolio_engine/   # codice applicativo
├── scripts/                # entry points
├── tests/                  # test unit e integration
├── docs/howto/README.md    # questa guida
├── docs/PROJECT_STATUS.md  # stato e architettura
└── requirements.txt
```
