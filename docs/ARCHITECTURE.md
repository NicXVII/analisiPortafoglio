# Portfolio Engine - Architettura

Data: 2026-01-30  
Branch: `Remediation`

## Obiettivo
Descrivere in modo conciso layering, flussi e regole di dipendenza del motore, per supportare il remediation plan e futuri refactor.

## Layer
- **core/**: orchestrazione pipeline (load → metrics → diagnostics → gate → output). Nessuna logica di calcolo di dominio.
- **data_providers/**: accesso dati esterni (Yahoo) con cache. Non importa da analytics/decision.
- **data/**: loader + definizioni (tassonomia, crisi, storage). Può importare data_providers e utils, non analytics.
- **analytics/**: calcolo metrica pura (returns, risk, contribution), regime detection, portfolio_analysis. No I/O.
- **decision/**: risk intent, gate system, validation. Importa analytics + models + config, non output.
- **reporting/**: formattazione e stampa (console, export). Consuma output di core/analytics/decision, nessuna logica di calcolo.
- **models/**: dataclass e enum condivisi (single source of truth).
- **config/**: configurazioni utente, soglie documentate, loader JSON/YAML.
- **utils/**: logging, eccezioni, helper generici.
- **tests/**: unit + integration; fixture sintetiche in `tests/fixtures/`. Marker `live` per test che richiedono rete.

## Flusso dati (happy path)
1. `core.main_legacy` → `core.pipeline_runner.run_pipeline`
2. `data.loader.download_data` (via data_providers/yahoo_client) + integrity checks
3. `analytics.metrics` + `analytics.metrics_monolith` (in refactor) calcolano metriche e contributi
4. `decision.risk_intent` + `decision.gate_system` validano intent/struttura
5. `core.output_runner.emit_outputs` → `reporting.console` / export
6. `core.storage_runner` salva configurazione portfolio (hash dedupe)

## Regole di dipendenza
- data_providers → (none)
- data → data_providers, utils
- analytics → models, utils, config (parametri), data.definitions (tassonomia), **mai** reporting/decision
- decision → analytics, models, config
- reporting → models, decision/analytics output
- core → orchestrazione sopra i layer, nessun calcolo di dominio

## Convenzioni
- Funzioni di calcolo: pure, senza I/O.  
- Config: immutabile o passato esplicitamente; niente mutation globale.  
- Metriche: usare varianti annualizzate coerenti (`var_95_annual`, `cvar_95_annual`).  
- Test: default offline con fixture; i test live marcati `@pytest.mark.live`.

## Roadmap tecnica (remediation)
- Completare migrazione da `metrics_monolith.py` e `analysis_monolith.py` verso i moduli split.
- Estendere tassonomia/etf_classifier per coprire tutti i ticker usati nei preset.
- Rafforzare type hints in `core` e `reporting`.
- Allineare CLI e howto alla nuova struttura (config file + storage hash).
