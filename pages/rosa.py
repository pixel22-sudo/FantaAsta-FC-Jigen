from fanta_core import *
from fanta_core import _quick_price, _reset_live_price, _quick_cloud_save, _quick_undo

def render_rosa():
    fm_page("📋 Rosa FC Jigen", "Controlla composizione, spesa e slot ancora da riempire.")
    c1,c2,c3,c4=st.columns(4)
    for col,r in zip((c1,c2,c3,c4),SLOTS):
        col.metric(r,f"{role_count(r)}/{SLOTS[r]}")
    if S["roster"]:
        spent=sum(int(x.get("price",0) or 0) for x in S["roster"])
        st.caption(f"{len(S['roster'])}/25 giocatori • {spent} crediti spesi • {S['credits']} residui")
        rdf=pd.DataFrame(S["roster"]).rename(columns={"name":"Nome","role":"Ruolo","team":"Squadra","fvm":"FVM","price":"Prezzo"})
        rdf=rdf[[c for c in ["Nome","Ruolo","Squadra","FVM","Prezzo"] if c in rdf.columns]]
        st.dataframe(rdf,hide_index=True,width="stretch")
        st.download_button("⬇️ ESPORTA ROSA CSV",rdf.to_csv(index=False).encode(),file_name="rosa_fc_jigen.csv",mime="text/csv",width="stretch")
    else:
        st.markdown('<div class="fm-empty">👕 La rosa è ancora vuota. Gli acquisti registrati in Asta compariranno qui automaticamente.</div>',unsafe_allow_html=True)


render_rosa()
