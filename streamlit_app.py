# VERSIONE v3.25.0 FANTAMOSSA - MULTIPAGE ROUTER
import streamlit as st
import fanta_core  # inizializza Cloud, stato, branding e controlli condivisi

pages = [
    st.Page("pages/asta.py", title="Asta", icon="🔥", url_path="asta", default=True),
    st.Page("pages/rosa.py", title="Rosa", icon="👕", url_path="rosa"),
    st.Page("pages/rivali.py", title="Rivali", icon="👥", url_path="rivali"),
    st.Page("pages/altro.py", title="Altro", icon="🧰", url_path="altro"),
]

pg = st.navigation(pages, position="top")
pg.run()
