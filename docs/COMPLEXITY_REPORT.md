# Portfolio Engine – Complexity Report
Data: 2026-01-31  
Scope: analisi big‑O (tempo/spazio) dell’intero percorso “main” **a partire da `analyze_portfolio`** (`scripts/analyze_portfolio.py` → `core/main_legacy.py` → `core/pipeline.py` → reporting), con assunzioni realistiche:  
- n = numero asset (tipico 5–20)  
- T = osservazioni giornaliere per asset (anni_history·252)  
- k = punti frontiera (solo se ottimizzazione Markowitz è attivata)  
- S = simulazioni Monte Carlo per portafoglio (solo se MC esplicitamente richiesta)  
- C = portafogli random nel cloud (se abilitato)  

## 1) Sintesi ad alto livello
- Tempo dominato da: download dati (I/O rete), covarianze/correlazioni `O(T·n²)`, eventuale ottimizzazione Markowitz `O(k·I·n²)` e Monte Carlo `O(S·H·n)`.
- Spazio dominato da: prezzi e rendimenti `O(T·n)`, matrici `O(n²)`, eventuali array MC/cloud (`O(S)` / `O(C)`).
- Con 32 GB RAM le configurazioni correnti (n≈7, T≈30y, C=20k, S=20k) restano ampiamente entro margine (<1 GB).

### 1.1 Percorso `analyze_portfolio` (sequenza e costi)
1. Carica config & auto-save (`user_config`, `storage_runner`) → `O(n)` tempo/spazio.
2. Download prezzi & validazione (`data/loader`) → I/O rete + `O(T·n)` tempo, `O(T·n)` spazio.
3. Calcolo rendimenti e metriche base (`pipeline` → `analytics/metrics`) → `O(T·n)` + cov `O(T·n²)`, spazio `O(T·n + n²)`.
4. Correlazioni shrunk & contributi rischio → `O(T·n²)` tempo, `O(n²)` spazio.
5. Diagnostics/regime & walk-forward intent (`diagnostics_runner`, `decision/*`) → `O(T·n)`–`O(T·n²)` tempo, `O(T·n + n²)` spazio.
6. Output & export (`output_runner`, `reporting/*`) → `O(T·n)` tempo, spazio proporzionale ai file scritti.
7. (Opzionale) Ottimizzazione Markowitz (`analytics/optimization/markowitz`) → vedi §3.

## 2) Percorso principale e complessità
### a. Config & storage
- File: `src/portfolio_engine/config/user_config.py`, `core/storage_runner.py` (auto-save JSONL).  
- Tempo: `O(n)`; Spazio: `O(n)` (solo config corrente).

### b. Download & prep dati
- File: `data/loader.py` (`download_data`, `calculate_start_date`, `validate_data_integrity`).  
- Tempo: rete-dominato + CPU `O(T·n)` per pct_change;  
- Spazio: prezzi `O(T·n)`; eventuale duplicazione per benchmark aggiunge `O(T·n_bmk)`.

### c. Returns & metriche base
- File: `analytics/metrics/basic.py`, `metrics/__init__.py` orchestrato da `core/pipeline.py`.  
- Operazioni: rendimenti semplici/log, CAGR, volatilità, drawdown, VaR/ES.  
- Tempo: `O(T·n)` (statistiche per asset) + `O(T·n²)` per cov/var;  
- Spazio: `O(T·n)` per returns, `O(n²)` per cov/corr.

### d. Correlazioni & shrinkage
- File: `analytics/metrics/correlation.py` / `metrics_monolith.py` (`calculate_shrunk_correlation`).  
- Tempo: `O(T·n²)`; Spazio: `O(n²)`. Shrinkage aggiunge costante moderata.

### e. Risk contribution
- File: `analytics/metrics/contribution.py`.  
- Tempo: `O(n²)` (matmul su cov), Spazio: `O(n²)` (riusa cov).

### f. Diagnostics & regime
- File: `core/diagnostics_runner.py`, `analytics/regime.py`.  
- Tempo: prevalente `O(T·n)` per rolling/regime; Spazio: `O(T·n)` per finestre.

### g. Risk intent & gate system
- File: `decision/risk_intent.py`, `decision/gate_system.py`, `decision/validation.py`.  
- Tempo: `O(T·n²)` per dual correlations / walk-forward windowed; Spazio: `O(n²)` + finestra rolling `O(W·n)`.

### h. Output & reporting
- File: `core/output_runner.py`, `reporting/console.py`, `reporting/export.py`.  
- Tempo: lineare nel numero di record stampati/esportati `O(T·n)`; PDF plotting `O(T·n)` tipicamente.  
- Spazio: file CSV/JSON/PDF su disco (proporzionale ai dati scritti).

## 3) Modulo Markowitz (se invocato)
- File: `analytics/optimization/markowitz.py`.  
- Preprocessing: `O(T·n²)` (cov).  
- Ottimizzazioni singole (min var, max Sharpe, risk parity): `O(I·n²)` tempo, `O(n²)` spazio.  
- Frontiera k punti: `O(k·I·n²)` tempo, `O(k·n)` spazio.  
- Cloud random C: `O(C·n²)` tempo (statistiche), `O(C)` spazio (ret/vol/sharpe).  
- Monte Carlo S con orizzonte H: `O(S·H·n)` tempo, `O(S)` spazio (o meno con batching).  

## 4) Bottleneck pratici
- Rete: download da yfinance è il vero fattore dominante per T lungo; CPU/GPU non saturata.
- Covarianza/correlazioni: unico step quadratic in n; per n ≤ 30 resta lieve (< qualche ms per T ~ 7k).
- MC/Cloud: costi lineari in S e C; controllare questi parametri nelle run “pesanti”.
- I/O disco: esport di cloud/frontier può essere grande; evitare scrivere pesi se non servono.

## 5) Suggerimenti di ottimizzazione (senza cambiare design)
- Reuse cov/µ calcolati una volta nel pipeline per evitare ricomputi in step diagnostici aggiuntivi.
- Usare `float32` per cloud/MC arrays mantenendo `float64` per cov/optimizer (dimezza RAM).  
- Batch Monte Carlo (chunk da 5k) aggregando statistiche online per S elevati.  
- Limitare `cloud_size` quando `n_sims` è alto; disattivare cloud se non necessario.  
- Chiudere figure Matplotlib dopo salvataggio (`plt.close()`), già previsto ma da mantenere.

## 6) Ordini di grandezza (caso reale attuale)
- Parametri: n=7, T≈30 anni (≈7 560), k=20, C=20 000, S=20 000, H=252.  
- Tempo CPU (senza rete): pochi secondi per pipeline + ~10–15 s per MC/cloud (dipende dalla macchina).  
- RAM: < ~300 MB (MC + cloud + matrici), ampiamente entro 32 GB.

## 7) Check rapido per modifiche future
- Se n cresce > 200: cov/corr `O(n²)` può diventare dominante; valutare sparsità o block-diagonal.  
- Se T cresce > 100k: calcolo returns/cov diventa `O(T·n²)` costoso; valutare downsampling o EWMA.  
- Per S o C >> 100k: applicare batching e salvataggio incrementale su disco.
