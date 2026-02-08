📘 STRUCTURAL GATE — DEFINIZIONE NORMATIVA FINALE

Nota di allineamento (2026-01-29):
- Questo documento e una specifica normativa. L implementazione corrente vive in `src/portfolio_engine/decision/gate_system.py`.
- Eventuali differenze operative vanno risolte aggiornando codice e questa specifica insieme.

(Versione proposta per Framework Istituzionale)

1️⃣ SCOPO DELLO STRUCTURAL GATE

Lo Structural Gate ha lo scopo di determinare se la struttura del portafoglio, indipendentemente da performance, regime di mercato o risk intent, presenta fragilità causali tali da comprometterne il funzionamento in modo non lineare e non reversibile.

Lo Structural Gate non valuta:

rendimento

volatilità

drawdown

coerenza con il risk intent

metriche di rischio ex-post

2️⃣ DEFINIZIONE FORMALE DI FRAGILITÀ STRUTTURALE

Un portafoglio è strutturalmente fragile se il suo profilo di rischio/rendimento dipende in modo critico da una o più ipotesi strutturali che, se violate, generano un deterioramento rapido, non lineare e difficilmente reversibile del comportamento del portafoglio.

Caratteristiche necessarie:

dipendenza causale identificabile

non linearità della risposta

assenza di meccanismi interni di compensazione

Se anche una sola di queste manca, non può essere dichiarata fragilità strutturale.

3️⃣ CAUSE AMMISSIBILI DI FAIL STRUTTURALE

(Lista chiusa — esclusiva)

Un FAIL dello Structural Gate può essere dichiarato solo se è verificata almeno una delle seguenti condizioni.

🔴 A. SINGLE-DRIVER DEPENDENCY

Il portafoglio dipende in modo dominante da un singolo driver economico, fattoriale o strutturale, anche se mascherato da più strumenti.

Criteri operativi:

50% del contributo al rischio riconducibile a una singola funzione economica

rimozione del driver → collasso del profilo rischio/rendimento

diversificazione apparente ma funzionalmente ridondante

🔴 B. HIDDEN LEVERAGE O CONVEXITY RISK

Esiste leva implicita, convessità negativa o rischio asimmetrico non esplicitamente dichiarato.

Criteri operativi:

perdite crescono più che linearmente in stress

VaR/CVaR mostrano discontinuità

payoff strutturalmente asimmetrico non intenzionale

🔴 C. CORRELATION COLLAPSE DIMOSTRATO

La diversificazione fallisce sistematicamente nei regimi di stress, con convergenza delle correlazioni verso 1 dimostrata su campione sufficiente.

Criteri operativi:

evidenza storica multi-crisi

collasso ripetuto, non episodico

perdita simultanea delle funzioni economiche

🔴 D. VIOLAZIONE DI VINCOLI STRUTTURALI DICHIARATI

Il portafoglio viola vincoli strutturali dichiarati ex-ante.

Esempi:

concentrazione oltre limiti ammessi

esposizione ad asset non consentiti

utilizzo di strumenti non previsti dal mandato

4️⃣ COSA NON COSTITUISCE FRAGILITÀ STRUTTURALE

I seguenti elementi non sono mai sufficienti, singolarmente o congiuntamente, per un FAIL strutturale:

CCR elevati

drawdown elevati ma coerenti con l’intent

volatilità elevata

Sharpe / Sortino compressi

performance negativa in crisi

aumento delle correlazioni in stress non dimostrato sistemicamente

Questi elementi sono diagnostici, non causali.

5️⃣ RUOLO DEI WARNING (CCR, CORRELAZIONI, DD)

I warning:

non attivano lo Structural Gate

non producono FAIL

richiedono analisi, non decisione

I warning possono:

motivare uno stato di Structural Watchlist

contribuire a dimostrare una delle cause A–D solo se accompagnati da evidenza causale

6️⃣ OUTPUT DELLO STRUCTURAL GATE

Lo Structural Gate può produrre solo uno dei seguenti stati:

Stato	Significato
✅ PASS	Nessuna fragilità causale
⚠️ WATCHLIST	Segnali strutturali da monitorare
❌ FAIL	Fragilità causale dimostrata

Uno stato FAIL è terminale e blocca:

score

ranking

verdetti successivi

7️⃣ RELAZIONE CON GLI ALTRI GATE

Lo Structural Gate è indipendente dal Risk Intent Gate

Un portafoglio può:

passare l’intent gate

fallire lo structural gate

Lo Structural Gate ha precedenza sugli score quantitativi

8️⃣ PRINCIPIO DI GOVERNANCE (fondamentale)

In assenza di prova causale, lo Structural Gate deve PASSARE.
Il dubbio genera watchlist, non bocciatura.

9️⃣ FORMULA DECISIONALE RIASSUNTIVA
IF (A OR B OR C OR D)
AND (Evidenza causale dimostrata)
THEN Structural Gate = FAIL
ELSE IF (Warning significativi ma non causali)
THEN Structural Gate = WATCHLIST
ELSE Structural Gate = PASS
