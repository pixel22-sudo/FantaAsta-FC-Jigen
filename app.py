import streamlit as st
import pandas as pd

st.set_page_config(page_title="FantaBrain 5.0 - Copilota Asta", layout="wide", initial_sidebar_state="collapsed")

st.title("⚽ FantaBrain 5.0 - Copilota Automatizzato")
st.caption("Asta 10 Squadre | 1000 Crediti | Modificatore Difesa")

SQUADRE_LISTA = [
    "Fc jigen", "Red Demon", "CHIAVARIELLO FC", "La Seleção", "LAS Capocchias",
    "VERO TONY VERO SOSA", "Joga Benito", "vale lambo", "Los zuccherinhos", "ARIANAPOLI"
]

LIMITI_RUOLO = {"POR": 3, "DIF": 8, "CEN": 8, "ATT": 6}

# PERCENTUALI SPESA MAX CONSIGLIATA
PERCENTUALI_MAX = {"POR": 0.04, "DIF": 0.16, "CEN": 0.25, "ATT": 0.55}

# LOGHI SQUADRE SERIE A (URL Diretti CDN)
LOGHI_SQUADRE = {
    "Inter": "https://a.espncdn.com/i/teamlogos/soccer/500/110.png",
    "Milan": "https://a.espncdn.com/i/teamlogos/soccer/500/103.png",
    "Juventus": "https://a.espncdn.com/i/teamlogos/soccer/500/111.png",
    "Napoli": "https://a.espncdn.com/i/teamlogos/soccer/500/114.png",
    "Roma": "https://a.espncdn.com/i/teamlogos/soccer/500/104.png",
    "Lazio": "https://a.espncdn.com/i/teamlogos/soccer/500/112.png",
    "Atalanta": "https://a.espncdn.com/i/teamlogos/soccer/500/105.png",
    "Fiorentina": "https://a.espncdn.com/i/teamlogos/soccer/500/109.png",
    "Torino": "https://a.espncdn.com/i/teamlogos/soccer/500/239.png",
    "Bologna": "https://a.espncdn.com/i/teamlogos/soccer/500/107.png",
    "Como": "https://a.espncdn.com/i/teamlogos/soccer/500/2157.png",
    "Udinese": "https://a.espncdn.com/i/teamlogos/soccer/500/115.png"
}

# DATABASE COMPLETO DIVISO PER RUOLO E SQUADRA
DATABASE = {
    "POR": {
        "Maignan": "Milan", "Sommer": "Inter", "Svilar": "Roma", 
        "Meret": "Napoli", "Di Gregorio": "Juventus", "Carnesecchi": "Atalanta"
    },
    "DIF": {
        "Dimarco": "Inter", "Bremer": "Juventus", "Bastoni": "Inter", 
        "Di Lorenzo": "Napoli", "Akanji": "Inter", "Solet": "Udinese"
    },
    "CEN": {
        "Calhanoglu": "Inter", "Pulisic": "Milan", "McTominay": "Napoli", 
        "Nico Paz": "Como", "Orsolini": "Bologna", "Frattesi": "Inter"
    },
    "ATT": {
        "Lautaro Martinez": "Inter", "Yildiz": "Juventus", "Hojlund": "Napoli", 
        "Malen": "Roma", "Ramos G.": "Milan", "Kolo Muani": "Juventus"
    }
}

if "squadre" not in st.session_state:
    st.session_state.squadre = {
        sq: {"crediti": 1000, "POR": 0, "DIF": 0, "CEN": 0, "ATT": 0, "totale": 0} for sq in SQUADRE_LISTA
    }

if "storico" not in st.session_state:
    st.session_state.storico = []

# Nomi di tutti i giocatori già acquistati
presi_nomi = [item["Giocatore"].lower() for item in st.session_state.storico]

st.subheader("📝 Registra Chiamata e Acquisto")

col1, col2 = st.columns([1, 1])
with col1:
    squadra_acq = st.selectbox("Squadra Acquirente", list(st.session_state.squadre.keys()))
with col2:
    ruolo_acq = st.selectbox("Ruolo Chiamato", ["POR", "DIF", "CEN", "ATT"])

# FILTRAGGIO DINAMICO GIOCATORI LIBERI PER IL RUOLO SELEZIONATO
diz_ruolo = DATABASE[ruolo_acq]
giocatori_disponibili = [g for g in diz_ruolo.keys() if g.lower() not in presi_nomi]

col3, col4 = st.columns([2, 1])
with col3:
    nome_giocatore = st.selectbox(
        f"Giocatore {ruolo_acq} Disponibile ({len(giocatori_disponibili)} rimasti)", 
        options=[""] + giocatori_disponibili
    )
with col4:
    prezzo_acq = st.number_input("Prezzo Finale (cr)", min_value=1, max_value=1000, value=1, step=1)

# VISUALIZZAZIONE LOGO SQUADRA E INFO COPILOTA
crediti_jigen = st.session_state.squadre["Fc jigen"]["crediti"]
max_spesa = int(crediti_jigen * PERCENTUALI_MAX[ruolo_acq])

if nome_giocatore:
    sq_club = diz_ruolo.get(nome_giocatore, "")
    logo_url = LOGHI_SQUADRE.get(sq_club, "")
    col_img, col_txt = st.columns([1, 10])
    with col_img:
        if logo_url:
            st.image(logo_url, width=45)
    with col_txt:
        st.markdown(f"**Squadra Serie A:** {sq_club}")

st.info(f"💡 **Copilota {ruolo_acq}:** Budget Reparto consigliato ~{int(1000*PERCENTUALI_MAX[ruolo_acq])} cr | Max consigliato per questo slot: **{max_spesa} cr**")

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
                    "Giocatore": nome_giocatore, "Ruolo": ruolo_acq, "Squadra": squadra_acq, "Prezzo": prezzo_acq
                })
                st.rerun()
        else:
            st.warning("Seleziona un giocatore!")

with col_b2:
    if st.button("↩️ ANNULLA ULTIMO", use_container_width=True):
        if st.session_state.storico:
            ultimo = st.session_state.storico.pop(0)
            sq_data = st.session_state.squadre[ultimo["Squadra"]]
            sq_data["crediti"] += ultimo["Prezzo"]
            sq_data[ultimo["Ruolo"]] -= 1
            sq_data["totale"] -= 1
            st.rerun()

st.divider()

st.subheader("📊 Analisi Crediti & Sbarramento Fc jigen")
altri_crediti = [v["crediti"] for k, v in st.session_state.squadre.items() if k != "Fc jigen"]
max_avversario = max(altri_crediti) if altri_crediti else 0

m1, m2, m3 = st.columns(3)
m1.metric("Fc jigen Crediti", f"{crediti_jigen} cr")
m2.metric("Sbarramento Assoluto", f"{max_avversario + 1} cr")
m3.metric("Slot Rimanenti Fc jigen", f"{25 - st.session_state.squadre['Fc jigen']['totale']} / 25")

st.subheader("📋 Quadro Avversari & Prezzo Medio Rimanente (PMR)")
dati_tabella = []
for k, v in st.session_state.squadre.items():
    slot_rim = 25 - v["totale"]
    pmr = round(v["crediti"] / slot_rim, 1) if slot_rim > 0 else 0
    dati_tabella.append({
        "Squadra": k, "Crediti": v["crediti"], "PMR": pmr, "Rosa": f"{v['totale']}/25",
        "POR": f"{v['POR']}/3", "DIF": f"{v['DIF']}/8", "CEN": f"{v['CEN']}/8", "ATT": f"{v['ATT']}/6"
    })

st.dataframe(pd.DataFrame(dati_tabella), use_container_width=True, hide_index=True)

st.divider()
st.subheader("🎯 Target Rimanenti per Reparto (con Loghi)")
cols_t = st.columns(4)
titoli_cat = {"POR": "🧤 PORTIERI", "DIF": "🛡️ DIFENSORI", "CEN": "⚙️ CENTROCAMPISTI", "ATT": "⚽ ATTACCANTI"}

for idx, (r_code, lista_g) in enumerate(DATABASE.items()):
    with cols_t[idx]:
        st.write(f"**{titoli_cat[r_code]}**")
        for g_nome, sq_club in lista_g.items():
            logo_url = LOGHI_SQUADRE.get(sq_club, "")
            if g_nome.lower() in presi_nomi:
                st.caption(f"~~{g_nome}~~ ❌ *(Preso)*")
            else:
                col_l, col_n = st.columns([1, 4])
                with col_l:
                    if logo_url:
                        st.image(logo_url, width=22)
                with col_n:
                    st.markdown(f"**{g_nome}**")

if st.session_state.storico:
    st.divider()
    st.subheader("📜 Storico Acquisti Completo")
    df_storico = pd.DataFrame(st.session_state.storico)
    st.dataframe(df_storico, use_container_width=True, hide_index=True)
