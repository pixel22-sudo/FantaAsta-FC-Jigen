import streamlit as st
import pandas as pd

# CARICAMENTO / PASTE DEL LISTONE CON NORMALIZZAZIONE AUTOMATICA
uploaded_file = st.sidebar.file_uploader("Carica File CSV (Nome, Ruolo, Squadra)", type=["csv"])

if uploaded_file is not None:
    # Legge il CSV provando i separatori più comuni (virgola o punto e virgola)
    try:
        df_raw = pd.read_csv(uploaded_file, sep=None, engine='python')
    except Exception:
        df_raw = pd.read_csv(uploaded_file)

    # Rimuove spazi vuoti dai nomi delle colonne
    df_raw.columns = df_raw.columns.str.strip()

    # Mappatura automatica delle intestazioni possibili
    col_map = {}
    for col in df_raw.columns:
        c_low = col.lower()
        if c_low in ['nome', 'calciatore', 'giocatore', 'giocatori']:
            col_map[col] = 'Nome'
        elif c_low in ['ruolo', 'r', 'r.']:
            col_map[col] = 'Ruolo'
        elif c_low in ['squadra', 'club', 'sq', 'squadre']:
            col_map[col] = 'Squadra'

    df_listone = df_raw.rename(columns=col_map)

    # Normalizza i valori dei ruoli (es. P -> POR, D -> DIF, ecc.)
    m_ruoli = {'P': 'POR', 'D': 'DIF', 'C': 'CEN', 'A': 'ATT'}
    if 'Ruolo' in df_listone.columns:
        df_listone['Ruolo'] = df_listone['Ruolo'].astype(str).str.upper().str.strip()
        df_listone['Ruolo'] = df_listone['Ruolo'].replace(m_ruoli)
else:
    # Listone di riserva se non viene caricato alcun file
    data_listone = [
        {"Nome": "Maignan", "Ruolo": "POR", "Squadra": "Milan"},
        {"Nome": "Lautaro Martinez", "Ruolo": "ATT", "Squadra": "Inter"}
    ]
    df_listone = pd.DataFrame(data_listone)
