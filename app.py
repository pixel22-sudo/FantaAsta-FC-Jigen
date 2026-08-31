import streamlit as st
import pandas as pd

# 1. SETUP PAGINA SPARTANA & REATTIVA
st.set_page_config(page_title="FantaBrain - Fantachill 5.0", layout="wide", initial_sidebar_state="collapsed")

st.title("⚽ FantaBrain - Fantachill 5.0")
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
TARGET_BUDGET = {"POR": 90, "DIF": 150, "CEN": 280, "ATT": 480}

# 2. INIZIALIZZAZIONE DATO E STATO AUTOMATIZZATO
if "squadre" not in st.session_state:
    st.session_state.squadre = {
        sq: {
            "crediti": 1000,
            "spesi": 0,
            "POR": 0, "DIF": 0, "CEN": 0, "ATT": 0,
            "totale_rosa": 0
        } for sq in SQUADRE_LISTA
    }

if "storico" not in st.session_state:
    st.session_state.storico = []

# 3. PANNELLO INSERIMENTO RAPIDO
st.subheader("📝 Registra Acquisto")

col1, col2, col3, col4 = st.columns([2, 1, 2, 1])

with col1:
    squadra_acq = st.selectbox("Squadra", list(st.session_state.squadre.keys()))
with col2:
    ruolo_acq = st.selectbox("Ruolo", ["ATT", "CEN", "DIF", "POR"])
with col3:
    nome_giocatore = st.text_input("Nome Giocatore", placeholder="Es. Lautaro")
with col4:
    prezzo_acq = st.number_input("Prezzo (cr)", min_value=1, max_value=1000, value=1, step=1)

col_btn1, col_btn2 = st.columns(2)

with col_btn1:
    if st.button("📌 CONFERMA ACQUISTO", use_container_width=True):
        if nome_giocatore:
            sq_data = st.session_state.squadre[squadra_acq]
            
            # Controllo limite slot ruolo
            if sq_data[ruolo_acq] >= LIMITI_RUOLO[ruolo_acq]:
                st.error(f"⚠️ {squadra_acq} ha già completato il reparto {ruolo_acq} ({LIMITI_RUOLO[ruolo_acq]}/{LIMITI_RUOLO[ruolo_acq]})!")
            else:
                sq_data["crediti"] -= prezzo_acq
                sq_data["spesi"] += prezzo_acq
                sq_data[ruolo_acq] += 1
                sq_data["totale_rosa"] += 1
                
                st.session_state.storico.insert(0, {
                    "Giocatore": nome_giocatore,
                    "Ruolo": ruolo_acq,
                    "Squadra": squadra_acq,
                    "Prezzo": prezzo_acq
                })
                st.success(f"✅ {nome_giocatore} ({ruolo_acq}) ➔ {squadra_acq} per {prezzo_acq} cr")
        else:
            st.warning("Inserisci il nome del giocatore!")

with col_btn2:
    if st.button("↩️ ANNULLA ULTIMA OPERAZIONE", use_container_width=True):
        if st.session_state.storico:
            ultimo = st.session_state.storico.pop(0)
            sq_data = st.session_state.squadre[ultimo["Squadra"]]
            sq_data["crediti"] += ultimo["Prezzo"]
            sq_data["spesi"] -= ultimo["Prezzo"]
            sq_data[ultimo["Ruolo"]] -= 1
            sq_data["totale_rosa"] -= 1
            st.info(f"Annullato: {ultimo['Giocatore']} da {ultimo['Squadra']}")
        else:
            st.warning("Nessuna operazione da annullare!")

st.divider()

# 4. METRICHE STRATEGICHE IN REAL TIME
st.subheader("📊 Calcolo Automatizzato Sbarramento & Crediti")

crediti_miei = st.session_state.squadre["Fc jigen"]["crediti"]
altri_crediti = [v["crediti"] for k, v in st.session_state.squadre.items() if k != "Fc jigen"]
max_avversario = max(altri_crediti) if altri_crediti else 0

m1, m2, m3 = st.columns(3)
m1.metric("Fc jigen Crediti", f"{crediti_miei} cr")
m2.metric("Sbarramento Assoluto", f"{max_avversario + 1} cr", help="Offerta per battere qualsiasi avversario")
m3.metric("Slot Rimanenti Fc jigen", f"{25 - st.session_state.squadre['Fc jigen']['totale_rosa']} / 25")

# 5. TABELLA AVANZATA MONITORAGGIO AVVERSARI
st.subheader("📋 Status Completo Lega (Reparti & PMR)")

dati_tabella = []
for k, v in st.session_state.squadre.items():
    slot_rim = 25 - v["totale_rosa"]
    pmr = round(v["crediti"] / slot_rim, 1) if slot_rim > 0 else 0
    dati_tabella.append({
        "Squadra": k,
        "Crediti Res.": v["crediti"],
        "PMR": pmr,
        "Rosa": f"{v['totale_rosa']}/25",
        "POR": f"{v['POR']}/3",
        "DIF": f"{v['DIF']}/8",
        "CEN": f"{v['CEN']}/8",
        "ATT": f"{v['ATT']}/6"
    })

df_status = pd.DataFrame(dati_tabella)
st.dataframe(df_status, use_container_width=True, hide_index=True)

# 6. STORICO CHIAMATE CON FILTRO & EXPORT AUTOMATICO
if st.session_state.storico:
    st.divider()
    st.subheader("📜 Storico Chiamate & Report")
    
    df_storico = pd.DataFrame(st.session_state.storico)
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtro_ruolo = st.multiselect("Filtra per Ruolo", options=["ATT", "CEN", "DIF", "POR"], default=["ATT", "CEN", "DIF", "POR"])
    
    df_filtrato = df_storico[df_storico["Ruolo"].isin(filtro_ruolo)]
    st.dataframe(df_filtrato, use_container_width=True, hide_index=True)
    
    csv = df_storico.to_csv(index=False).encode('utf-8')
    st.download_button("📥 SCARICA REPORT COMPLETO (CSV)", data=csv, file_name="fanta_asta_fantachill.csv", mime="text/csv")

# 7. EXPANDER RESET
with st.expander("⚙️ Reset Totale Sessione"):
    if st.button("⚠️ RESETTA TUTTA L'ASTA"):
        st.session_state.squadre = {
            sq: {"crediti": 1000, "spesi": 0, "POR": 0, "DIF": 0, "CEN": 0, "ATT": 0, "totale_rosa": 0} 
            for sq in SQUADRE_LISTA
        }
        st.session_state.storico = []
        st.rerun()
