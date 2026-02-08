# Project Overview & Architecture
Data: 2026-01-29

## 1) Scopo del progetto
Motore Python per analizzare portafogli di ETF/fondi usando dati storici Yahoo Finance. Calcola metriche rischio/rendimento, controlla coerenza strutturale tramite gate decisionali e produce output leggibile (console/PDF/JSON) per analisi ripetibili.

## 2) Cosa fa oggi (feature attuali)
- Download prezzi da Yahoo Finance con auto-start date e warning su survivorship bias e illiquidita.
- Calcolo metriche: simple/log returns, CAGR corretto, volatilita annualizzata, Sharpe/Sortino/Calmar, max drawdown, VaR/CVaR, risk contribution e conditional risk contribution, correlazioni shrinked.
- Classificazione portafoglio: type detection via tassonomia ETF, esposizione geografica/funzionale, detection di false diversificazioni, market regime detection.
- Gate system: data integrity, risk intent, structural coherence, benchmark comparison; eccezioni bloccanti con meccanismo di override; verdetto finale strutturato.
- Validation: walk-forward, rolling stability, out-of-sample stress test, Monte Carlo con distribuzione t-student, dual correlation matrix.
- Reporting: summary console, esport PDF/Excel/CSV/JSON/HTML, grafici opzionali, modelli strutturati (`AnalysisResult`, `MetricsSnapshot`).
- Configurazione: `config/user_config.py` fornisce portfolio di esempio, intent, parametri analisi, opzioni export, preset.
- Entry point: `scripts/analyze_portfolio.py` richiama `run_analysis_to_pdf` e salva in `output/`.
- Test: unit su modelli, integrazione su pipeline stage e structured output (dipendono da dati live Yahoo).

## 3) Cosa NON fa (limiti dichiarati)
- Nessuna previsione o ottimizzazione portafoglio; niente raccomandazioni di trading.
- Fonte dati unica (Yahoo Finance); niente caching locale, nessuna copertura ETF delisted, niente dati di flussi o fondamentali.
- Geo exposure e issuer exposure non affidabili; top holdings limitati alla disponibilita Yahoo.
- Nessuna API esterna; input legato al cod ice (config Python), non a file utente o CLI strutturata.
- Costi di transazione e tassazione solo abbozzati; ribilanciamento senza costi reali.
- Test dipendono da rete e da dati variabili; assenza di fixture deterministiche.
- Output e log persistono nella repo (no pulizia/ignore automatica).

## 4) Architettura attuale (descrizione)
- **core**: `core/main_legacy.py` gestisce l intero orchestratore (download, metriche, gate, stampa, export) con funzioni di stage estratte in `core/pipeline.py`; rimane logica duplicata e monolitica.
- **analytics**: `analytics/metrics_monolith.py` re-esporta moduli `analytics/metrics/*` e implementa stress test; `analysis_monolith.py` contiene detection tipo/regime e false diversificazioni; `analytics/portfolio_analysis/*` gestisce temporal/resilience/type detection; `regime.py` per market regime.
- **data**: `data/loader.py` per download yfinance, simulazioni e controlli data quality; `data/definitions/{taxonomy,crisis}.py` e `etf_taxonomy.json` per tassonomia.
- **decision**: `decision/gate_system.py`, `risk_intent.py`, `validation.py` applicano gate, soft labels, walk-forward e verifiche.
- **reporting**: `reporting/console.py` per stampa, `reporting/export.py` per PDF/CSV/XLSX/JSON/HTML.
- **models**: `models/portfolio.py` con dataclass e enum (AnalysisResult, MetricsSnapshot, ecc.).
- **config**: `config/user_config.py` (portfolio hard-coded, preset, soglie gate, parametri statistici), `config/thresholds.py` (documentazione soglie con fonti).
- **utils**: logging, eccezioni, costi; `update_imports.py` script di manutenzione import.
- **tests**: `tests/unit`, `tests/integration` (usano rete); cartella separata `test/` con script esplorativi e plot holdings.
- **altra documentazione**: `howTo.md` (riferisce a main.py non piu esistente), report storici in `reports/`, log/output tracciati.

## 5) Problemi noti / debolezze
- Orchestratore monolitico: `main_legacy.py` mescola orchestration, IO, plotting, validation; pipeline estratta solo in parte.
- Doppioni di modelli e API: `PrescriptiveAction` definita sia in `models/portfolio.py` sia in `decision/gate_system.py`; moduli *monolith* re-esportano funzioni gia modulari.
- Config hard-coded: `user_config.py` contiene portafoglio reale, soglie e opzioni export; input utente non separato da codice, rende difficile esecuzioni multiple e testabili.
- Dipendenza forte da rete e dati live: tests di integrazione e pipeline richiedono download Yahoo; nessuna fixture o caching locale.
- Incoerenza requisiti: `pyproject.toml` e `requirements.txt` hanno versioni diverse; seaborn/python-dateutil presenti solo in pyproject; dev deps definite ma non documentate.
- Repository hygiene: `__pycache__`, log e file di output/versioning nella repo; cartella `test/` fuori da `tests/`; notebook `lecture.ipynb` e file markdown vari senza struttura.
- Documentazione obsoleta: `howTo.md` parla di `main.py`; `gateDefiniiton.md` isolato; report vecchi in `reports/` non collegati al codice attuale.
- Layering debole: `analytics` conosce tassonomie e soglie di config, `decision` usa funzioni analytics e definizioni dati direttamente, `reporting` ricalcola soglie e logica; import incrociato difficile da testare.
- Assenza di strategie di gestione output: grafici e PDF salvati in `output/` senza naming stabile o cleanup.

## 6) Proposta di architettura target (senza nuove fonti dati)
Obiettivo: separazione chiara tra acquisizione dati, calcolo, decisioni e presentazione, mantenendo yfinance come provider corrente.

```
src/
  portfolio_engine/
    core/              # orchestrator e CLI thin; pipeline step chiari
    config/            # default, preset, validazione input; nessun dato sensibile
    data_providers/    # adapter Yahoo + cache locale; definitions/ per tassonomie e crisi
      definitions/
    analytics/         # metrica, risk, regime, stress; nessun IO
      metrics/
      portfolio/       # type detection, resilience
      stress/
    decision/          # gate, risk intent, validation; usa solo analytics/models
    reporting/         # console, exporters, plotting; dipende da analytics output
    models/            # dataclass ed enum condivisi (uniche definizioni)
    utils/             # logging, eccezioni, helpers generali
scripts/               # CLI, manutenzione (update_imports, generate-fixtures)
tests/
  unit/
  integration/
  fixtures/            # dati scaricati offline anonimi o sintetici
docs/
  PROJECT_STATUS.md
  howto/               # guide operative aggiornate
examples/              # config campione, notebook; non importati in src
sandbox/               # esperimenti singoli (ex cartella test/)
output/                # ignorato da VCS; usato per report locali
logs/                  # ignorato da VCS
```

Regole di dipendenza proposte:
- `data_providers` non importa da `analytics/decision/reporting`.
- `analytics` importa solo da `models/utils/config` (parametri), mai da `reporting`.
- `decision` importa da `analytics`, `models`, `config`; non viceversa.
- `reporting` consuma solo output di `core/analytics/decision`, nessuna logica di calcolo.
- `core` orchestra e chiama `reporting`, non contiene logica di dominio.

## 7) Roadmap tecnica
- Breve termine (0-4 settimane)
  - Pulizia repo: rimuovere `__pycache__`, log/output, aggiungere `.gitignore` coerente; allineare `requirements.txt` a `pyproject.toml`.
  - Uniformare modelli: tenere `PrescriptiveAction` e tipi solo in `models/portfolio.py`; adeguare `gate_system.py`.
  - Estrarre config run-time: spostare portafogli di esempio in `examples/` o preset JSON/YAML; `get_config()` deve accettare input esterni.
  - Stabilire dati di test: creare fixture CSV sintetici o snapshot Yahoo e far puntare i test di integrazione a quelli, con flag per live test.
  - Aggiornare documentazione utente (`howto/`) e CLI (`scripts/analyze_portfolio.py`) alla nuova struttura.
- Medio termine (1-3 mesi)
  - Rifattorizzare orchestratore: `main_legacy.py` -> `core/pipeline.py` + `core/cli.py`; rendere gli stage pure (niente side-effect IO).
  - Separare provider: modulo `data_providers/yahoo_client.py` con cache locale e controlli di rate-limit; mantenere interfaccia per futuri provider senza implementarli ora.
  - Consolidare soglie: utilizzare `config/thresholds.py` come fonte unica e consumata via API interna; eliminare hardcode residui.
  - Migliorare reporting: spostare formattazione soglie/benchmarks fuori da console, usare template per PDF/HTML, controllare naming degli output.
  - Test coverage: aggiungere unit per analytics e decision usando dataset piccolo deterministico; integrazione end-to-end con fixture.
- Lungo termine (3-6 mesi)
  - Introdurre configurazione dichiarativa (es. file YAML) validata contro schema, caricata da CLI/API; mantenere compatibilita code-based.
  - Introdurre caching/persistenza dei download (file parquet) e invalidazione basata su data end-date.
  - Rendere il gate system estendibile (registry di regole) e documentare chiaramente il flusso; misurare performance e ottimizzare path calcolo.
  - Stendere manuale architetturale e contributory guide; automazione CI con test offline e, opzionalmente, job giornaliero per live smoke test.

## 8) Analisi sintetica del repository (stato attuale)
- **Struttura**: `src/portfolio_engine` e `tests/` ben presenti, ma convive una cartella `test/` con script esplorativi; `logs/` e `output/` sono artefatti runtime dentro repo.
- **Scripts**: `scripts/analyze_portfolio.py` e `update_imports.py` sono utili, ma non separano ambiente dev da produzione.
- **Docs**: `howTo.md` e `gateDefiniiton.md` non sono allineati al codice attuale; report storici in `reports/` non collegati a README o docs.
- **Duplicazioni**: `metrics_monolith.py` e `analysis_monolith.py` re-esportano logica gia spezzata; `PrescriptiveAction` e soglie replicate in moduli diversi.
- **Dipendenze**: discrepanze fra `pyproject.toml` e `requirements.txt` (versioni e pacchetti mancanti).

## 9) Classificazione del codice (per responsabilita)
- **Core engine**: `src/portfolio_engine/core/main_legacy.py`, `src/portfolio_engine/core/pipeline.py`
- **Data providers**: `src/portfolio_engine/data/loader.py`, `src/portfolio_engine/data/definitions/*`
- **Analytics / aggregazioni**: `src/portfolio_engine/analytics/*`, `src/portfolio_engine/analytics/metrics/*`, `src/portfolio_engine/analytics/portfolio_analysis/*`
- **Decision / gating**: `src/portfolio_engine/decision/gate_system.py`, `src/portfolio_engine/decision/risk_intent.py`, `src/portfolio_engine/decision/validation.py`
- **Reporting / visualizzazione**: `src/portfolio_engine/reporting/console.py`, `src/portfolio_engine/reporting/export.py`
- **Config / input utente**: `src/portfolio_engine/config/user_config.py`, `src/portfolio_engine/config/thresholds.py`
- **Modelli**: `src/portfolio_engine/models/portfolio.py`
- **Script test/esperimenti**: `test/*.py`, `scripts/analyze_portfolio.py`, `lecture.ipynb`
- **Documentazione**: `howTo.md`, `gateDefiniiton.md`, `reports/`

File fuori posto o con responsabilita miste:
- `test/holder_allocation.py`: utile ma dovrebbe stare in `sandbox/` o `examples/`.
- `howTo.md`: fa riferimento a `main.py` (non esiste), va aggiornato o spostato in `docs/howto/`.
- `metrics_monolith.py` e `analysis_monolith.py`: mescolano re-export e logica; candidati a deprecazione dopo consolidamento.
- `decision/gate_system.py`: definisce dataclass che duplicano modelli globali.

## 10) Azioni pratiche (refactor steps)
1) Allineare dipendenze e aggiungere `.gitignore` per `output/`, `logs/`, `__pycache__/`.
2) Consolidare modelli: `PrescriptiveAction` e tipi solo in `models/portfolio.py`; adattare import in `decision/gate_system.py` e pipeline.
3) Spostare `test/` in `sandbox/` e `howTo.md` in `docs/howto/` con contenuti aggiornati.
4) Estrarre config runtime: file di input esterni (JSON/YAML) + loader in `config/`; mantenere preset in `examples/`.
5) Separare provider: introdurre `data_providers/yahoo_client.py` e spostare funzioni di download fuori da `data/loader.py`.
6) Rendere `core/pipeline.py` l unico orchestratore logico; ridurre `main_legacy.py` a wrapper legacy.
7) Preparare fixture per test; marcare i test live con flag o marker pytest.
