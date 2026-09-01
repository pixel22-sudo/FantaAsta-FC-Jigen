# FantaAsta FC Jigen WEB v3 iPHONE

Versione pensata per usare l'asta direttamente da iPhone tramite Streamlit Community Cloud.

## Incluso
- Asta Live
- ASTA MASTER
- Radar
- 9 avversari
- Rosa
- Obiettivi
- Storico + undo
- mercato adattivo
- AFFARE / OK / LIMITE / OVERPAY / STOP
- backup JSON + CSV
- supporto salvataggio cloud Supabase

## Deploy Streamlit
Carica tutti i file nel repository GitHub e imposta `streamlit_app.py` come main file.

## Secrets Streamlit
In **Advanced settings / Secrets** configura:

[supabase]
url = "URL_DEL_PROGETTO"
key = "PUBLISHABLE_KEY"

Non inserire mai una service-role key nel repository.

## Nota sicurezza
Il progetto database deve avere RLS/policy coerenti con il metodo di accesso scelto.
Se il cloud non è configurato o non è autorizzato, l'app continua a funzionare e permette il backup JSON.
