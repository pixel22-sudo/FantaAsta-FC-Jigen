import streamlit as st

# Setup della pagina per Smartphone
st.set_page_config(page_title="FantaBrain - Fantachill 5.0", layout="centered")

st.title("⚽ FantaBrain - Fantachill 5.0")
st.caption("Asta a 10 squadre | 1000 Crediti | Modificatore Difesa")

# Nomi ufficiali delle squadre della lega Fantachill 5.0
SQUADRE_LISTA = [
    "Fc jigen",  # La tua squadra
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

# Inizializzazione dello Stato (Session State)
if "squadre" not in st.session_state:
    st.session_state.squadre = {sq: 1000 for sq in SQUADRE_LISTA}

if "storico" not in st.session_state:
    st.session_state.storico = []

# Target consigliati su 1000 crediti per Fantachill
TARGET = {"POR": 90, "DIF": 150, "CEN": 280, "ATT": 480}

# 1. SEZIONE ASTA IN TEMPO REALE
st.subheader("📝 Registra Acquisto")

col1, col2 = st.columns(2)
with col1:
    squadra_acquirente = st.selectbox("Squadra", list(st.session_state.squadre.keys()))
    ruolo = st.selectbox("Ruolo", ["ATT", "CEN", "DIF", "POR"])
with col2:
    nome_giocatore = st.text_input("Giocatore", placeholder="Es. Lautaro")
    prezzo = st.number_input("Prezzo (cr)", min_value=1, max_value=1000, value=1, step=1)

if st.button("📌 CONFERMA ACQUISTO", use_container_width=True):
    if nome_giocatore:
        st.session_state.squadre[squadra_acquirente] -= prezzo
        st.session_state.storico.insert(0, f"{nome_giocatore} ({ruolo}) ➔ {squadra_acquirente} per {prezzo} cr")
        st.success(f"{nome_giocatore} registrato a {squadra_acquirente}!")
    else:
        st.warning("Inserisci il nome del giocatore!")

st.divider()

# 2. METRICHE SBARRAMENTO E BUDGET
st.subheader("📊 Stato Crediti Avversari")

crediti_miei = st.session_state.squadre["Fc jigen"]
altri_crediti = [v for k, v in st.session_state.squadre.items() if k != "Fc jigen"]
max_avversario = max(altri_crediti) if altri_crediti else 0

col_a, col_b = st.columns(2)
col_a.metric("Crediti Fc jigen", f"{crediti_miei} cr")
col_b.metric("Sbarramento Massimo", f"{max_avversario + 1} cr", help="Offerta massima per superare chiunque")

st.write("**Crediti Rimanenti per Squadra:**")
st.dataframe(
    [{"Squadra": k, "Crediti Residui": v} for k, v in st.session_state.squadre.items()],
    use_container_width=True
)

with st.expander("💡 Target Spesa Consigliati (Modificatore)"):
    for r, cr in TARGET.items():
        st.write(f"- **{r}**: ~{cr} crediti")

if st.session_state.storico:
    st.subheader("📜 Ultime Chiamate")
    for item in st.session_state.storico[:5]:
        st.caption(item)
