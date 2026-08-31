import streamlit as st
import pandas as pd

# 1. SETUP PAGINA
st.set_page_config(page_title="FantaBrain 5.0 - Copilota Asta", layout="wide", initial_sidebar_state="collapsed")

st.title("⚽ FantaBrain 5.0 - Copilota Automatizzato")
st.caption("Asta 10 Squadre | 1000 Crediti | Modificatore Difesa")

SQUADRE_LISTA = [
    "Fc jigen",
    "Red Demon",
    "CHIAVARIELLO FC",
    "La Seleção",
    "LAS Capocchias",
    "VERO TONY VERO SOSA",
    "Joga Benito",
    "vale lambo",
    "Los zuccherinhos",
    "ARIANAPOLI"
]

LIMITI_RUOLO = {"POR": 3, "DIF": 8, "CEN": 8, "ATT": 6}

# LISTA TARGET GIOCATORI MIGLIORI PER FANTACHILL
TARGET_GIOCATORI = {
    "🧤 PORTIERI": ["Maignan", "Martínez", "Meret", "Svilar", "Carnesecchi", "Vicario"],
    "🛡️ DIFENSORI": ["Dimarco", "Bremer", "Wesley", "Akanji", "Solet", "Mancini", "Di Lorenzo", "Ostigard"],
    "⚙️ CENTROCAMPISTI": ["Calhanoglu", "McTominay", "Nico Paz", "Orsolini", "Pulisic", "Frattesi", "Atta"],
    "⚽ ATTACCANTI": ["Lautaro", "Malen", "Ramos", "Hojlund", "Yildiz", "Dovbyk", "Davis", "Kolo Muani"]
}

# 2. INIZIALIZZAZIONE STATO AUTOMATICO
if "squadre" not in st.session_state:
    st.session_state.squadre = {
        sq: {
            "crediti": 1000,
            "POR": 0, "DIF": 0, "CEN": 0, "ATT": 0,
            "totale": 0
        } for sq in SQUADRE_LISTA
    }

if "storico" not in st.session_state:
    st.session_state.storico = []

# 3. PANNELLO REGISTRAZIONE RAPIDA
st.subheader("📝 Registra Acquisto in Tempo Reale")

col1, col2, col3, col4 = st.columns([2, 1, 2, 1])

with col1:
    squadra_acq = st.selectbox("Squadra Acquirente", list(st.session_state.squadre.keys()))
with col2:
    ruolo_acq = st.selectbox("Ruolo", ["ATT", "CEN", "DIF", "POR"])
with col3:
    nome_giocatore = st.text_input("Giocatore", placeholder="Es. Lautaro")
with col4:
    prezzo_acq = st.number_input("Prezzo (cr)", min_value=1, max_value=1000, value=1, step=1)

col_b1, col_b2 = st.columns(2)

with col_b1:
    if st.button("📌 CONFERMA ACQUISTO", use_container_width=True):
        if nome_giocatore:
            sq_data = st.session_state.squadre[squadra_acq]
            
            if sq_data[ruolo_acq] >= LIMITI_RUOLO[ruolo_acq]:
                st.error(f"⚠️ {squadra_acq} ha già completato il reparto {ruolo_acq}!")
            else:
                sq_data["crediti"] -= prezzo_acq
                sq_data[ruolo_acq] += 1
                sq_data["totale"] += 1
                
                st.session_state.storico.insert(0, {
                    "Giocatore": nome_giocatore.strip(),
                    "Ruolo": ruolo_acq,
                    "Squadra": squadra_acq,
                    "Prezzo": prezzo_acq
                })
                st.success(f"✅ Registrato: {nome_giocatore} ➔ {squadra_acq} per {prezzo_acq} cr")
        else:
            st.warning("Digita il nome del giocatore!")

with col_b2:
    if st.button("↩️ ANNULLA ULTIMO", use_container_width=True):
        if st.session_state.storico:
            ultimo = st.session_state.storico.pop(0)
            sq_data = st.session_state.squadre[ultimo["Squadra"]]
            sq_data["crediti"] += ultimo["Prezzo"]
            sq_data[ultimo["Ruolo"]] -= 1
            sq_data["totale"] -= 1
            st.info(f"Annullato: {ultimo['Giocatore']}")

st.divider()

# 4. MONITORAGGIO AUTOMATICO SBARRAMENTO E BUDGET
st.subheader("📊 Analisi Sbarramento & Crediti Fc jigen")

crediti_miei = st.session_state.squadre["Fc jigen"]["crediti"]
altri_crediti = [v["crediti"] for k, v in st.session_state.squadre.items() if k != "Fc jigen"]
max_avversario = max(altri_crediti) if altri_crediti else 0

m1, m2, m3 = st.columns(3)
m1.metric("Fc jigen Crediti Residui", f"{crediti_miei} cr")
m2.metric("Sbarramento Assoluto", f"{max_avversario + 1} cr", help="La cifra massima con cui ti aggiudichi chiunque superando tutti")
m3.metric("Slot Rimanenti Fc jigen", f"{25 - st.session_state.squadre['Fc jigen']['totale']} / 25")

# 5. TABELLA STATO LEGA E PMR
st.subheader("📋 Quadro Avversari & Prezzo Medio Rimanente (PMR)")

dati_tabella = []
for k, v in st.session_state.squadre.items():
    slot_rim = 25 - v["totale"]
    pmr = round(v["crediti"] / slot_rim, 1) if slot_rim > 0 else 0
    dati_tabella.append({
        "Squadra": k,
        "Crediti": v["crediti"],
        "PMR (cr/slot)": pmr,
        "Rosa": f"{v['totale']}/25",
        "POR": f"{v['POR']}/3",
        "DIF": f"{v['DIF']}/8",
        "CEN": f"{v['CEN']}/8",
        "ATT": f"{v['ATT']}/6"
    })

st.dataframe(pd.DataFrame(dati_tabella), use_container_width=True, hide_index=True)

# 6. CHEAT SHEET TARGET AUTOMATIZZATO (AUTO-SBARRAMENTO)
st.divider()
st.subheader("🎯 Target Migliori Rimanenti (Aggiornamento Automatico)")

presi_nomi = [item["Giocatore"].lower() for item in st.session_state.storico]

cols_t = st.columns(4)
for idx, (cat, lista_giocatori) in enumerate(TARGET_GIOCATORI.items()):
    with cols_t[idx % 4]:
        st.write(f"**{cat}**")
        for g in lista_giocatori:
            # Controllo automatico di corrispondenza parziale nel nome
            gia_acquistato = any(g.lower() in p or p in g.lower() for p in presi_nomi)
            if gia_acquistato:
                st.caption(f"~~{g}~~ ❌ *(Preso)*")
            else:
                st.write(f"🟢 **{g}**")

# 7. STORICO & EXPORT CSV
if st.session_state.storico:
    st.divider()
    st.subheader("📜 Storico Acquisti Completo")
    df_storico = pd.DataFrame(st.session_state.storico)
    st.dataframe(df_storico, use_container_width=True, hide_index=True)
    
    csv = df_storico.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Scarica Report Asta (CSV)", data=csv, file_name="fanta_asta_fantachill.csv", mime="text/csv")

# 8. RESET ASTA
with st.expander("⚙️ Gestione e Reset Sessione"):
    if st.button("⚠️ RESETTA TUTTI I DATI"):
        st.session_state.squadre = {
            sq: {"crediti": 1000, "POR": 0, "DIF": 0, "CEN": 0, "ATT": 0, "totale": 0} 
            for sq in SQUADRE_LISTA
        }
        st.session_state.storico = []
        st.rerun()
