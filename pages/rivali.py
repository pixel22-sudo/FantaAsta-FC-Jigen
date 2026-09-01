from fanta_core import *
from fanta_core import _quick_price, _reset_live_price, _quick_cloud_save, _quick_undo

def render_rivali():
    fm_page("👥 Rivali", "Controlla chi ha ancora più potere di spesa e aggiorna i dati solo quando serve.")
    rows=[{"Squadra":n,"Crediti":x["credits"],"Slot":x["slots"],**x["roles"],
           "Crediti/slot":round(x["credits"]/max(1,x["slots"]),1)} for n,x in S["rivals"].items()]
    rview=pd.DataFrame(rows).sort_values(["Crediti/slot","Crediti"],ascending=False)
    st.dataframe(rview,hide_index=True,width="stretch")

    with st.expander("✏️ Aggiorna un rivale", expanded=False):
        selected=st.selectbox("Squadra",RIVALS,key="rival_edit_team")
        d=S["rivals"][selected]
        rv1,rv2,rv3=st.columns(3)
        rv1.metric("Crediti",d["credits"]); rv2.metric("Slot",d["slots"]); rv3.metric("Crediti/slot",round(d["credits"]/max(1,d["slots"]),1))
        c1,c2=st.columns(2)
        with c1:
            cred=st.number_input("Crediti residui",0,BUDGET,int(d["credits"]),key="rvcred")
            slots=st.number_input("Slot totali residui",0,25,int(d["slots"]),key="rvslots")
        with c2:
            vals={}
            for r in SLOTS: vals[r]=st.number_input(f"Slot {r}",0,SLOTS[r],int(d["roles"][r]),key=f"rv_{r}")
        if st.button("💾 SALVA RIVALE",type="primary",width="stretch",key="save_rival_edit"):
            d["credits"]=int(cred);d["slots"]=int(slots);d["roles"]={r:int(vals[r]) for r in SLOTS};persist();st.rerun()


render_rivali()
