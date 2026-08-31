import streamlit as st
import pandas as pd

st.set_page_config(page_title="FantaBrain - Fantachill 5.0", layout="centered")

st.title("⚽ FantaBrain - Fantachill 5.0")
st.caption("Asta a 10 squadre | 1000 Crediti | Modificatore Difesa")

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

# Inizializzazione Stato
if "squadre" not in st.session_state:
    st.session_state.squadre = {sq: {"crediti": 1000, "acquisti": 0} for sq in SQUADRE_LISTA}

if "storico" not in st.session_state:
    st.session_state.storico = []

TARGET = {"POR": 90, "DIF": 150, "CEN": 280, "ATT": 480}

# 1. SEZIONE REGISTRAZIONE ACQUISTI
st.subheader("📝 Registra Acquisto")

col1, col2 = st.columns(2)
with col1:
    squadra_acquirente = st.selectbox("Squadra", list(st.session_state.squadre.keys()))
    ruolo = st.selectbox("Ruolo", ["ATT", "CEN", "DIF", "POR"])
with col2:
    nome_giocatore = st.text_input("Giocatore", placeholder="Es. Lautaro")
    prezzo = st.number_input("Prezzo (cr)", min_value=1, max_value=1000, value=1, step=1)

col_btn1, col_btn2 = st.columns(2)

with col_btn1:
    if st.button("📌 CONFERMA ACQUISTO", use_container_width=True):
        if nome_giocatore:
            st.session_state.squadre[squadra_acquirente]["crediti"] -= prezzo
            st.session_state.squadre[squadra_acquirente]["acquisti"] += 1
            st.session_state.storico.insert(0, {
                "giocatore": nome_giocatore,
                "ruolo": ruolo,
                "squadra": squadra_acquirente,
                "prezzo": prezzo
            })
            st.success(f"{nome_giocatore} ➔ {squadra_acquirente} ({prezzo} cr)")
        else:
            st.warning("Inserisci il nome del giocatore!")

with col_btn2:
    if st.button("↩️ ANNULLA ULTIMO", use_container_width=True):
        if st.session_state.storico:
            ultimo = st.session_state.storico.pop(0)
            st.session_state.squadre[ultimo["squadra"]]["crediti"] += ultimo["prezzo"]
            st.session_state.squadre[ultimo["squadra"]]["acquisti"] -= 1
            st.info(f"Annullato: {ultimo['giocatore']}")

st.divider()

# 2. TABELLA STATO CREDITI E SBARRAMENTO
st.subheader("📊 Stato Crediti & Sbarramento")

crediti_miei = st.session_state.squadre["Fc jigen"]["crediti"]
altri_crediti = [v["crediti"] for k, v in st.session_state.squadre.items() if k != "Fc jigen"]
max_avversario = max(altri_crediti) if altri_crediti else 0

col_a, col_b = st.columns(2)
col_a.metric("Crediti Fc jigen", f"{crediti_miei} cr")
col_b.metric("Sbarramento Massimo", f"{max_avversario + 1} cr", help="Prezzo per staccare tutti")

# Tabella avanzata
dati_tabella = []
for k, v in st.session_state.squadre.items():
    slot_rimanenti = 25 - v["acquisti"]
    pmr = round(v["crediti"] / slot_rimanenti, 1) if slot_rimanenti > 0 else 0
    dati_tabella.append({
        "Squadra": k,
        "Crediti": v["crediti"],
        "Giocatori": f"{v['acquisti']}/25",
        "PMR (cr/slot)": pmr
    })

st.dataframe(pd.DataFrame(dati_tabella), use_container_width=True)

# 3. ULTIME CHIAMATE E EXPORT CSV
if st.session_state.storico:
    st.subheader("📜 Ultime Chiamate")
    df_storico = pd.DataFrame(st.session_state.storico)
    st.dataframe(df_storico, use_container_width=True)
    
    csv = df_storico.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Scarica Report Asta (CSV)", data=csv, file_name="asta_fantachill.csv", mime="text/csv")

# 4. RESET ASTA (IN ESPANDER)
with st.expander("⚙️ Gestione e Reset"):
    if st.button("⚠️ RESETTA TUTTA L'ASTA"):
        st.session_state.squadre = {sq: {"crediti": 1000, "acquisti": 0} for sq in SQUADRE_LISTA}
        st.session_state.storico = []
        st.rerun()
