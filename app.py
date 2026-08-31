import streamlit as st
import pandas as pd

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="FantaBrain 5.0 - Copilota Asta", layout="wide", initial_sidebar_state="collapsed")

st.title("⚽ FantaBrain 5.0 - Copilota & Listone Serie A")
st.caption("Asta 10 Squadre | 1000 Crediti | Modificatore Difesa")

# 2. COSTANTI & CONFIGURAZIONI
SQUADRE_LISTA = [
    "Fc jigen", "Red Demon", "CHIAVARIELLO FC", "La Seleção", "LAS Capocchias",
    "VERO TONY VERO SOSA", "Joga Benito", "vale lambo", "Los zuccherinhos", "ARIANAPOLI"
]

LIMITI_RUOLO = {"POR": 3, "DIF": 8, "CEN": 8, "ATT": 6}
PERCENTUALI_MAX = {"POR": 0.04, "DIF": 0.16, "CEN": 0.25, "ATT": 0.55}

LOGHI_SQUADRE = {

    "Atalanta": "https://a.espncdn.com/i/teamlogos/soccer/500/105.png",
    "Bologna": "https://a.espncdn.com/i/teamlogos/soccer/500/107.png",
    "Cagliari": "https://a.espncdn.com/i/teamlogos/soccer/500/2873.png",
    "Como": "https://a.espncdn.com/i/teamlogos/soccer/500/2157.png",
    "Empoli": "https://a.espncdn.com/i/teamlogos/soccer/500/1243.png",
    "Fiorentina": "https://a.espncdn.com/i/teamlogos/soccer/500/109.png",
    "Genoa": "https://a.espncdn.com/i/teamlogos/soccer/500/3263.png",
    "Inter": "https://a.espncdn.com/i/teamlogos/soccer/500/110.png",
    "Juventus": "https://a.espncdn.com/i/teamlogos/soccer/500/111.png",
    "Lazio": "https://a.espncdn.com/i/teamlogos/soccer/500/112.png",
    "Lecce": "https://a.espncdn.com/i/teamlogos/soccer/500/3445.png",
    "Milan": "https://a.espncdn.com/i/teamlogos/soccer/500/103.png",
    "Monza": "https://a.espncdn.com/i/teamlogos/soccer/500/11041.png",
    "Napoli": "https://a.espncdn.com/i/teamlogos/soccer/500/114.png",
    "Parma": "https://a.espncdn.com/i/teamlogos/soccer/500/113.png",
    "Roma": "https://a.espncdn.com/i/teamlogos/soccer/500/104.png",
    "Torino": "https://a.espncdn.com/i/teamlogos/soccer/500/239.png",
    "Udinese": "https://a.espncdn.com/i/teamlogos/soccer/500/115.png",
    "Venezia": "https://a.espncdn.com/i/teamlogos/soccer/500/2653.png",
    "Verona": "https://a.espncdn.com/i/teamlogos/soccer/500/2602.png"
}

# 3. CARICAMENTO INTELLIGENTE LISTONE FANTACALCIO
st.sidebar.header("📥 Carica Listone Fantacalcio")
uploaded_file = st.sidebar.file_uploader("Carica File Quotazioni (.xlsx o .csv)", type=["xlsx", "xls", "csv"])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith(('.xlsx', '.xls')):
            try:
                df_raw = pd.read_excel(uploaded_file, header=1)
            except Exception:
                uploaded_file.seek(0)
                df_raw = pd.read_excel(uploaded_file)
        else:
            try:
                df_raw = pd.read_csv(uploaded_file, sep=None, engine='python')
            except Exception:
                df_raw = pd.read_csv(uploaded_file)

        df_raw.columns = df_raw.columns.astype(str).str.strip()

        col_map = {}
        for col in df_raw.columns:
            c_low = col.lower()
            if c_low in ['nome', 'calciatore', 'giocatore']:
                col_map[col] = 'Nome'
            elif c_low in ['ruolo', 'r', 'r.']:
                col_map[col] = 'Ruolo'
            elif c_low in ['squadra', 'club', 'sq']:
                col_map[col] = 'Squadra'

        df_listone = df_raw.rename(columns=col_map)

        if 'Ruolo' in df_listone.columns:
            m_ruoli = {'P': 'POR', 'D': 'DIF', 'C': 'CEN', 'A': 'ATT'}
            df_listone['Ruolo'] = df_listone['Ruolo'].astype(str).str.upper().str.strip()
            df_listone['Ruolo'] = df_listone['Ruolo'].replace(m_ruoli)

    except Exception as e:
        st.error(f"Errore lettura file: {e}")
        df_listone = pd.DataFrame()
else:
    data_listone = [
        {"Nome": "Maignan", "Ruolo": "POR", "Squadra": "Milan"},
        {"Nome": "Sommer", "Ruolo": "POR", "Squadra": "Inter"},
        {"Nome": "Dimarco", "Ruolo": "DIF", "Squadra": "Inter"},
        {"Nome": "Calhanoglu", "Ruolo": "CEN", "Squadra": "Inter"},
        {"Nome": "Lautaro Martinez", "Ruolo": "ATT", "Squadra": "Inter"}
    ]
    df_listone = pd.DataFrame(data_listone)

# 4. INIZIALIZZAZIONE SESSIONE
if "squadre" not in st.session_state:
    st.session_state.squadre = {
        sq: {"crediti": 1000, "POR": 0, "DIF": 0, "CEN": 0, "ATT": 0, "totale": 0} for sq in SQUADRE_LISTA
    }

if "storico" not in st.session_state:
    st.session_state.storico = []

presi_nomi = [item["Giocatore"].lower() for item in st.session_state.storico]

# 5. REGISTRAZIONE CHIAMATA & ACQUISTO
st.subheader("📝 Registra Chiamata e Acquisto")

col1, col2 = st.columns([1, 1])
with col1:
    squadra_acq = st.selectbox("Squadra Acquirente", list(st.session_state.squadre.keys()))
with col2:
    ruolo_acq = st.selectbox("Ruolo Chiamato", ["POR", "DIF", "CEN", "ATT"])

if 'Ruolo' in df_listone.columns and 'Nome' in df_listone.columns:
    df_filtrato = df_listone[(df_listone["Ruolo"] == ruolo_acq) & (~df_listone["Nome"].astype(str).str.lower().isin(presi_nomi))]
    opzioni_giocatori = sorted(df_filtrato["Nome"].dropna().astype(str).unique().tolist())
else:
    opzioni_giocatori = []

col3, col4 = st.columns([2, 1])
with col3:
    nome_giocatore = st.selectbox(
        f"Giocatore {ruolo_acq} Disponibile ({len(opzioni_giocatori)} rimasti)", 
        options=[""] + opzioni_giocatori
    )
with col4:
    prezzo_acq = st.number_input("Prezzo Finale (cr)", min_value=1, max_value=1000, value=1, step=1)

crediti_jigen = st.session_state.squadre["Fc jigen"]["crediti"]
max_spesa = int(crediti_jigen * PERCENTUALI_MAX[ruolo_acq])

if nome_giocatore and 'Squadra' in df_listone.columns:
    match_sq = df_listone[df_listone["Nome"] == nome_giocatore]["Squadra"].values
    sq_club = match_sq[0] if len(match_sq) > 0 else ""
    logo_url = LOGHI_SQUADRE.get(sq_club, "")
    col_img, col_txt = st.columns([1, 10])
    with col_img:
        if logo_url:
            st.image(logo_url, width=40)
    with col_txt:
        st.markdown(f"**Club:** {sq_club}")

st.info(f"💡 **Copilota {ruolo_acq}:** Budget consigliato ~{int(1000*PERCENTUALI_MAX[ruolo_acq])} cr | Max consigliato slot top: **{max_spesa} cr**")

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
            st.warning("Seleziona un giocatore dal menu!")

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

# 6. TABELLA SQUADRE & METRICHE
st.subheader("📊 Quadro Avversari & Prezzo Medio Rimanente (PMR)")
dati_tabella = []
for k, v in st.session_state.squadre.items():
    slot_rim = 25 - v["totale"]
    pmr = round(v["crediti"] / slot_rim, 1) if slot_rim > 0 else 0
    dati_tabella.append({
        "Squadra": k, "Crediti": v["crediti"], "PMR": pmr, "Rosa": f"{v['totale']}/25",
        "POR": f"{v['POR']}/3", "DIF": f"{v['DIF']}/8", "CEN": f"{v['CEN']}/8", "ATT": f"{v['ATT']}/6"
    })

st.dataframe(pd.DataFrame(dati_tabella), use_container_width=True, hide_index=True)

# 7. STORICO CHIAMATE
if st.session_state.storico:
    st.divider()
    st.subheader("📜 Storico Acquisti Completo")
    st.dataframe(pd.DataFrame(st.session_state.storico), use_container_width=True, hide_index=True)
