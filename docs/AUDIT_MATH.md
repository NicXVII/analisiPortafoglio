# AUDIT MATEMATICO - Portfolio Engine
Data: 2026-02-08
Scope: correttezza matematica/statistica e coerenza interna

## Executive summary
- Aree analizzate: 12/13 (Markowitz incluso, threshold config escluso)
- Esito sintetico:
  - Corrette: Returns, Volatilita, Sharpe, Sortino, Drawdown, Beta, Markowitz
  - Parziali: CAGR coerenza cross-modulo, VaR/CVaR annualizzazione, Shrinkage
  - Correzioni implementate in questo passaggio: coerenza CAGR/CI, guardrail CCR, doc VaR

## Data flow verificato
Prezzi -> Returns (simple) -> Simulazione portafoglio -> Metriche -> Output
- Simple returns usati per aggregazione portfolio.
- Log returns presenti ma non usati nella pipeline principale.

---

## 1. Returns
Status: OK
- Formula: R_t = P_t/P_{t-1} - 1
- Implementazione: `analytics/metrics/basic.py::calculate_simple_returns`, `data/loader.py::simulate_portfolio_correct`
- Note: log returns definiti solo per analisi singolo asset. Non usati per aggregazione.

## 2. CAGR
Status: PARTIAL -> FIXED
- Formula corretta: (V_final/V_initial)^(1/years) - 1
- Issue: alcuni moduli usavano periods_per_year=252 ignorando il calendario reale.
- Fix implementato:
  - `analytics/metrics_monolith.py::calculate_all_metrics` usa calendar-based CAGR
  - `decision/validation.py::_calc_period_metrics` usa calendar-based CAGR
  - `analytics/metrics/confidence.py` allinea CI CAGR con calendario quando possibile

## 3. Volatilita
Status: OK
- Formula: sigma_annual = std_daily * sqrt(252)
- Implementazione: `analytics/metrics/basic.py::calculate_annualized_volatility`
- Note: ddof=1 usato (stimatore campionario), corretto.

## 4. Sharpe Ratio
Status: OK
- Risk-free convertito a daily: (1 + Rf_annual)^(1/252) - 1
- Annualizzazione: *sqrt(252)
- Opzione di correzione autocorrelazione (Lo, 2002) presente.

## 5. Sortino Ratio
Status: OK
- TDD definito come sqrt(mean(min(R - T, 0)^2)).
- Numeratore usa excess daily e annualizza linearmente, coerente con TDD annualizzata.

## 6. VaR / CVaR
Status: PARTIAL
- Metodo storico di default OK; bootstrap opzionale.
- Segno: ora restituisce perdite come valori POSITIVI (corretto per report).
- Annualizzazione: var_annual = var_daily * sqrt(252) e cvar_annual idem.
  - Nota: questa scala e' valida solo sotto assunzione sqrt(T). Nel report e' indicata come "indicative".
  - Raccomandazione: esporre esplicitamente l'assunzione nel report (non blocca l'output).

## 7. Max Drawdown
Status: OK
- Peak = running max, DD = (equity - peak)/peak.
- MaxDD restituito negativo; coerente con calcoli e report.

## 8. Risk Contribution
Status: OK (con guardrail)
- Formula CCR/MCR corretta, cov annualizzata su returns.
- Fix: aggiunto guardrail per port_vol=0 (evita divisione per zero).

## 9. Correlazione / Covarianza
Status: PARTIAL
- Cov/corr calcolata su returns (corretto).
- Shrinkage Ledoit-Wolf: implementazione semplificata (non garantisce PSD rigorosa).
  - Rischio: con pochi dati, eigenvalues negative possibili.
  - Raccomandazione: usare shrinkage standard (sklearn) in versione production.

## 10. Beta
Status: OK
- Formula corretta (cov/var). Allineamento temporale tramite dropna.
- Fallback beta=1 con meno di 60 osservazioni; ragionevole ma dichiarare nel report.

## 11. Monte Carlo / Stress Test
Status: OK
- Student-t come default per fat tails (coerente con assunzioni).
- Correlation shift scenario implementato.
- Nota: stress test usa scenario ipotetico, distinto da bootstrap storico (documentato).

## 12. Markowitz
Status: OK
- MVP: minimizza w'Cov w con vincolo sum w = 1.
- Max Sharpe: obiettivo corretto.
- Risk parity: implementato correttamente, fallback equal weight.
- Shrinkage su cov riusa la funzione di progetto.

---

## Correzioni implementate (questa iterazione)
1) Coerenza CAGR (calendar-based) in:
   - `analytics/metrics_monolith.py`
   - `decision/validation.py`
   - `analytics/metrics/confidence.py`
2) Guardrail divisione per zero in risk contribution:
   - `analytics/metrics/contribution.py`
3) Docstring VaR coerente con segno positivo:
   - `analytics/metrics/risk.py`

## Raccomandazioni prioritarie
1) VaR/CVaR annualizzazione: rendere esplicita l'assunzione sqrt(T) nel report e/o parametric-only.
2) Shrinkage: migrare a implementazione Ledoit-Wolf standard (sklearn) per PSD garantita.
3) Rimozione duplicati (returns in loader.py vs metrics/basic.py) per ridurre divergenze future.

