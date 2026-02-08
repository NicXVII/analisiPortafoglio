# Math & Stats Correction Plan – Portfolio Engine
Data: 2026-02-01  
Scope: portare il motore in linea con definizioni teoriche e coerenza statistica.

## Obiettivi
1) Verificare e correggere formule chiave (returns, CAGR, vol, Sharpe/Sortino, VaR/ES, CCR).  
2) Uniformare annualizzazione (252) e gestione risk-free.  
3) Ridurre bias di stima (survivorship haircut già inserito, VaR bootstrap).  
4) Integrare Monte Carlo opzionale per portafogli chiave Markowitz.  
5) Allineare segni/convenzioni (VaR/ES come perdita positiva).

## Azioni previste
- Returns: confermare simple returns per aggregazione, log solo per analisi asset.  
- VaR/ES: segno coerente (loss>0), opzioni historical/parametric/bootstrap configurabili.  
- Annualizzazione: centralizzare 252 per std/Sharpe/Sortino; rf convertito a daily prima dell’excess.  
- Risk contribution: verificare somma CCR% = 1, cov annualizzata.  
- FX: già convertito; assicurare reindex e lunghezze allineate.  
- Monte Carlo Markowitz: già abilitabile, nessun intervento.  
- Reporting: esposizione holdings aggregate (già fix import).

## Output atteso
- Codice aggiornato con convenzioni corrette.  
- Nessun errore di lunghezza in conversione FX.  
- VaR/ES restituiti come valori di perdita positivi.  
- Configurazioni già presenti (FX, FEES, RISK, BIAS, OPTIMIZATION) utilizzate nei calcoli.

