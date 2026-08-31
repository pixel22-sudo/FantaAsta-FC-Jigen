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
    "Como": "https://a.espncdn.com/i/teamlogos/soccer/500/2157.png"
}

DATABASE_GIOCATORI = {
    "Maignan": "Milan", "Sommer": "Inter", "Svilar": "Roma", "Meret": "Napoli", "Di Gregorio": "Juventus", "Carnesecchi": "Atalanta",
    "Dimarco": "Inter", "Bremer": "Juventus", "Bastoni": "Inter", "Di Lorenzo": "Napoli", "Akanji": "Inter", "Solet": "Udinese",
    "Calhanoglu": "Inter", "Pulisic": "Milan", "McTominay": "Napoli", "Nico Paz": "Como", "Orsolini": "Bologna", "Frattesi": "Inter",
    "Lautaro Martinez": "Inter", "Yildiz": "Juventus", "Hojlund": "Napoli", "Malen": "Roma", "Ramos G.": "Milan", "Kolo Muani": "Juventus"
}

LISTA_GIOCATORI_COMPLETA = sorted(list(DATABASE_GIOCATORI.keys()))

TARGET_GIOCATORI = {
    "POR": ["Maignan", "Meret", "Svilar", "Sommer", "Carnesecchi", "Di Gregorio"],
    "DIF": ["Dimarco", "Bremer", "Akanji", "Bastoni", "Di Lorenzo", "Solet"],
    "CEN": ["Calhanoglu", "McTominay", "Pulisic", "Nico Paz", "Orsolini", "Frattesi"],
    "ATT": ["Lautaro Martinez", "Yildiz", "Hojlund", "Malen", "Ramos G.", "Kolo Muani"]
}

if "squadre" not in st.session_state:
    st.session_state.squadre = {
        sq: {"crediti": 1000, "POR": 0, "DIF": 0, "CEN": 0, "ATT": 0, "totale": 0} for sq in SQUADRE_LISTA
    }

if "storico" not in st.session_state:
    st.session_state.storico = []

st.subheader("📝 Registra Chiamata e Acquisto")

col1, col2, col3, col4 = st.columns([2, 1, 2, 1])
with col1:
    squadra_acq = st.selectbox("Squadra Acquirente", list(st.session_state.squadre.keys()))
with col2:
    ruolo_acq = st.selectbox("Ruolo Chiamato", ["ATT", "CEN", "DIF", "POR"])
with col3:
    nome_giocatore = st.selectbox("Giocatore Chiamato", options=[""] + LISTA_GIOCATORI_COMPLETA)
with col4:
    prezzo_acq = st.number_input("Prezzo Finale (cr)", min_value=1, max_value=1000, value=1, step=1)

# SUGGERITORE CON LOGHI E BUDGET REPARTO
presi_nomi = [item["Giocatore"].lower() for item in st.session_state.storico]
liberi_ruolo = [g for g in TARGET_GIOCATORI[ruolo_acq] if not any(g.lower() in p for p in presi_nomi)]
crediti_jigen = st.session_state.squadre["Fc jigen"]["crediti"]
max_spesa = int(crediti_jigen * PERCENTUALI_MAX[ruolo_acq])

if nome_giocatore and nome_giocatore in DATABASE_GIOCATORI:
    sq_club = DATABASE_GIOCATORI[nome_giocatore]
    logo_url = LOGHI_SQUADRE.get(sq_club, "")
    if logo_url:
        st.image(logo_url, width=40)

st.info(f"💡 **Copilota {ruolo_acq} (Budget Reparto: {int(1000*PERCENTUALI_MAX[ruolo_acq])} cr):** Max consigliato per un top slot: **{max_spesa} cr** | **Migliori liberi:** {', '.join(liberi_ruolo[:3]) if liberi_ruolo else 'Tutti i target presi'}")

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
                st.success(f"✅ Registrato: {nome_giocatore} ➔ {squadra_acq} per {prezzo_acq} cr")
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
            st.info(f"Annullato: {ultimo['Giocatore']}")

st.divider()

st.subheader("📊 Analisi Sbarramento & Crediti Fc jigen")
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
st.subheader("🎯 Target Rimanenti con Loghi")
cols_t = st.columns(4)
titoli_cat = {"POR": "🧤 PORTIERI", "DIF": "🛡️ DIFENSORI", "CEN": "⚙️ CENTROCAMPISTI", "ATT": "⚽ ATTACCANTI"}
for idx, (r_code, lista_giocatori) in enumerate(TARGET_GIOCATORI.items()):
    with cols_t[idx % 4]:
        st.write(f"**{titoli_cat[r_code]}**")
        for g in lista_giocatori:
            club = DATABASE_GIOCATORI.get(g, "")
            logo = LOGHI_SQUADRE.get(club, "")
            if any(g.lower() in p for p in presi_nomi):
                st.caption(f"~~{g}~~ ❌ *(Preso)*")
            else:
                st.markdown(f"🟢 **{g}** `[{club}]`")

if st.session_state.storico:
    st.divider()
    st.subheader("📜 Storico Acquisti Completo")
    df_storico = pd.DataFrame(st.session_state.storico)
    st.dataframe(df_storico, use_container_width=True, hide_index=True)
    csv = df_storico.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Scarica Report (CSV)", data=csv, file_name="asta_fantachill.csv", mime="text/csv")
