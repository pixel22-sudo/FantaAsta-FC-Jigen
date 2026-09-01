import streamlit as st
import pandas as pd
import json, statistics, hashlib, time
from supabase import create_client
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="FantaAsta FC Jigen", page_icon="⚽", layout="wide",
                   initial_sidebar_state="expanded")

EXCEL = Path(__file__).parent / "Quotazioni_Fantacalcio_Stagione_2026_27.xlsx"
BUDGET = 1000
SLOTS = {"POR": 3, "DIF": 8, "CEN": 8, "ATT": 6}
ROLE_BUDGET = {"POR": .04, "DIF": .16, "CEN": .25, "ATT": .55}
ROLE_MAP = {"P":"POR","D":"DIF","C":"CEN","A":"ATT"}
RIVALS = ["Red Demon","CHIAVARIELLO FC","La Seleção","LAS Capocchias",
          "VERO TONY VERO SOSA","Joga Benito","vale lambo","Los zuccherinhos","ARIANAPOLI"]

@st.cache_data
def load_players():
    df = pd.read_excel(EXCEL, header=1)
    df = df.rename(columns={"Qt.A":"QtA"})
    df = df[df["R"].isin(ROLE_MAP)].copy()
    df["Ruolo"] = df["R"].map(ROLE_MAP)
    for c in ("FVM","QtA"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    df["Nome"] = df["Nome"].astype(str).str.strip()
    df["Squadra"] = df["Squadra"].astype(str).str.strip()
    df["key"] = df["Ruolo"] + "|" + df["Nome"]
    return df

PLAYERS = load_players()

CLOUD_ID = "fc-jigen-main"

@st.cache_resource
def cloud_client():
    try:
        cfg = st.secrets.get("supabase", {})
        url = str(cfg.get("url", "")).strip()
        key = str(cfg.get("key", "")).strip()
        if not url or not key:
            return None
        return create_client(url, key)
    except Exception:
        return None

def cloud_config_status():
    try:
        cfg = st.secrets.get("supabase", {})
        has_url = bool(str(cfg.get("url", "")).strip())
        has_key = bool(str(cfg.get("key", "")).strip())
        return has_url and has_key
    except Exception:
        return False

def cloud_load():
    sb = cloud_client()
    if not sb:
        return None
    try:
        res = sb.table("fanta_auction_state").select("state").eq("id", CLOUD_ID).single().execute()
        data = getattr(res, "data", None)
        if data and isinstance(data.get("state"), dict) and data["state"].get("roster") is not None:
            return data["state"]
    except Exception:
        return None
    return None

def cloud_save(state):
    sb = cloud_client()
    if not sb:
        return False
    try:
        sb.table("fanta_auction_state").upsert(
            {"id": CLOUD_ID, "state": state, "updated_at": datetime.now().isoformat()},
            on_conflict="id"
        ).execute()
        return True
    except Exception:
        return False

def persist():
    st.session_state["_cloud_ok"] = cloud_save(st.session_state.auction)


def default_state():
    return {
        "schema": 2, "team": "FC Jigen", "credits": BUDGET,
        "roster": [], "out": [], "moves": [], "targets": {},
        "rivals": {n: {"credits": BUDGET, "slots": 25, "roles": dict(SLOTS)} for n in RIVALS}
    }

if "auction" not in st.session_state:
    cloud_state = cloud_load()
    st.session_state.auction = cloud_state if cloud_state else default_state()
    st.session_state["_cloud_ok"] = bool(cloud_state)
S = st.session_state.auction

def normalize():
    S.setdefault("schema",2); S.setdefault("team","FC Jigen")
    S.setdefault("roster",[]); S.setdefault("out",[]); S.setdefault("moves",[])
    S.setdefault("targets",{}); S.setdefault("rivals",{})
    for n in RIVALS:
        S["rivals"].setdefault(n, {"credits":BUDGET,"slots":25,"roles":dict(SLOTS)})
        d=S["rivals"][n]
        d.setdefault("credits",BUDGET); d.setdefault("slots",25); d.setdefault("roles",dict(SLOTS))
        for r,v in SLOTS.items(): d["roles"].setdefault(r,v)
    # derive own credits from roster: avoids silent inconsistency
    S["credits"] = max(0, BUDGET-sum(int(x.get("price",0) or 0) for x in S["roster"]))
    for x in S["roster"]:
        k=f'{x.get("role","")}|{x.get("name","")}'
        if k and k not in S["out"]: S["out"].append(k)
normalize()

def role_count(role): return sum(x.get("role")==role for x in S["roster"])
def remaining_slots(): return max(0, 25-len(S["roster"]))
def max_absolute(): return max(0, S["credits"]-max(0,remaining_slots()-1))
def tier(fvm):
    if fvm>=400:return "S"
    if fvm>=250:return "A"
    if fvm>=140:return "B"
    if fvm>=70:return "C"
    return "D"
def market_samples(role=None):
    out=[]
    for m in S["moves"]:
        if m.get("price",0)>0 and m.get("fvm",0)>0 and (role is None or m.get("role")==role):
            out.append(m["price"]/m["fvm"])
    return out
def market_index():
    vals=market_samples()
    return statistics.median(vals) if vals else 1.0
def role_market(role):
    vals=market_samples(role)
    return statistics.median(vals) if vals else market_index()
def competition(role):
    interested=0; power=[]
    for d in S["rivals"].values():
        if d["slots"]>0 and d["roles"].get(role,0)>0:
            interested+=1; power.append(d["credits"]/max(1,d["slots"]))
    score=min(100, round(interested/9*55 + min(1,(statistics.mean(power) if power else 0)/40)*45))
    return score, interested
def scarcity(role):
    top=PLAYERS[(PLAYERS.Ruolo==role)&(~PLAYERS.key.isin(set(S["out"])))&(PLAYERS.FVM>=140)]
    demand=max(0,SLOTS[role]-role_count(role))+sum(max(0,d["roles"].get(role,0)) for d in S["rivals"].values())
    ratio=demand/max(1,len(top))
    return min(100,round(ratio*45))
def urgency(role):
    missing=max(0,SLOTS[role]-role_count(role))
    if not missing:return 0
    comp,_=competition(role)
    return min(100,round((missing/SLOTS[role])*45+(scarcity(role)/100)*30+(comp/100)*25))
def prediction(row):
    factor={"S":1.10,"A":1.05,"B":1.0,"C":.95,"D":.90}[tier(row.FVM)]
    comp,_=competition(row.Ruolo)
    center=max(1,round(row.FVM*role_market(row.Ruolo)*factor*(1+min(.08,comp/1000))))
    return max(1,round(center*.88)),max(1,round(center*1.12))
def cap_for(row):
    mult={"S":1.10,"A":1.04,"B":.96,"C":.88,"D":.80}[tier(row.FVM)]
    comp,_=competition(row.Ruolo)
    if tier(row.FVM) in ("S","A"): mult*=1+min(.05,comp/1500)
    return min(max_absolute(),max(1,round(row.FVM*mult)))
def fit(row):
    t={"S":95,"A":85,"B":72,"C":57,"D":40}[tier(row.FVM)]
    return min(100,round(t*.45+urgency(row.Ruolo)*.25+scarcity(row.Ruolo)*.15+
                         min(100,(S["credits"]/max(1,remaining_slots()))/10*100)*.15))
def status_price(row,p):
    cap=cap_for(row)
    if p<=round(cap*.72):return "🟢 AFFARE"
    if p<=round(cap*.90):return "🔵 OK"
    if p<=cap:return "🟠 LIMITE"
    if p<=round(cap*1.12):return "🔴 OVERPAY"
    return "⛔ STOP"
def plan_b(row,n=3):
    df=PLAYERS[(PLAYERS.Ruolo==row.Ruolo)&(~PLAYERS.key.isin(set(S["out"])))&(PLAYERS.key!=row.key)].copy()
    df["delta"]=(df.FVM-row.FVM).abs()
    return df.sort_values(["delta","FVM"],ascending=[True,False]).head(n)
def snapshot():
    return json.loads(json.dumps(S,ensure_ascii=False))
def backup_bytes():
    return json.dumps(S,ensure_ascii=False,indent=2).encode("utf-8")
def integrity():
    issues=[]
    if len(S["roster"])>25:issues.append("Rosa oltre 25 giocatori")
    if S["credits"]<0:issues.append("Crediti negativi")
    keys=[f'{x.get("role")}|{x.get("name")}' for x in S["roster"]]
    if len(keys)!=len(set(keys)):issues.append("Duplicati nella rosa")
    for r in SLOTS:
        if role_count(r)>SLOTS[r]:issues.append(f"Troppi {r}")
    for n,d in S["rivals"].items():
        if d["credits"]<0 or d["slots"]<0:issues.append(f"Stato incoerente: {n}")
    return issues
def do_undo():
    if not S["moves"]:return
    m=S["moves"].pop()
    k=f'{m["role"]}|{m["name"]}'
    if k in S["out"]:S["out"].remove(k)
    if m["action"]=="MIO":
        for i in range(len(S["roster"])-1,-1,-1):
            x=S["roster"][i]
            if x["name"]==m["name"] and x["role"]==m["role"]:
                S["roster"].pop(i);break
    elif m["action"]=="ALTRI" and m.get("buyer") in S["rivals"]:
        d=S["rivals"][m["buyer"]];d["credits"]+=int(m["price"]);d["slots"]+=1;d["roles"][m["role"]]+=1
    normalize()

st.markdown("""<style>
.block-container{padding-top:1rem;padding-bottom:3rem}
div[data-testid="stMetric"]{border:1px solid rgba(128,128,128,.22);padding:12px;border-radius:14px}
[data-testid="stSidebar"]{min-width:285px}
.small{opacity:.72;font-size:.9rem}
</style>""",unsafe_allow_html=True)

st.title("⚽ FantaAsta FC Jigen • WEB v3.1 iPHONE")
st.caption("Ottimizzata per iPhone • Asta Live • ASTA MASTER • Radar • Cloud • Backup")

with st.sidebar:
    st.header("🎛️ Centrale")
    secrets_ready = cloud_config_status()
    sb_ready = cloud_client() is not None
    if secrets_ready and sb_ready:
        if st.session_state.get("_cloud_ok"):
            st.success("☁️ Cloud collegato")
        else:
            st.info("☁️ Secrets letti • premi SALVA ORA per testare")
        if st.button("☁️ SALVA ORA", use_container_width=True):
            st.session_state["_cloud_ok"] = cloud_save(S)
            if st.session_state["_cloud_ok"]:
                st.success("Salvataggio cloud riuscito")
            else:
                st.error("Secrets letti, ma Supabase ha rifiutato il salvataggio")
            st.rerun()
    elif not secrets_ready:
        st.warning("☁️ Secrets Supabase non letti da Streamlit")
    else:
        st.error("☁️ Configurazione cloud non valida")
    issues=integrity()
    if not issues:
        st.success("✅ Stato integro")
    else:
        st.error("⚠️ " + ", ".join(issues))
    up=st.file_uploader("Importa backup JSON",type=["json"])
    if up and st.button("Carica backup",use_container_width=True):
        try:
            data=json.load(up)
            if not isinstance(data,dict) or "roster" not in data or "moves" not in data:raise ValueError("Formato non valido")
            st.session_state.auction=data;normalize();persist();st.rerun()
        except Exception as e:st.error(f"Backup non valido: {e}")
    st.download_button("⬇️ BACKUP JSON",backup_bytes(),
        file_name=f"FC_Jigen_{datetime.now():%Y%m%d_%H%M}.json",mime="application/json",use_container_width=True)
    if S["moves"] and st.button("↩️ ANNULLA ULTIMA",use_container_width=True):
        do_undo();persist();st.rerun()
    with st.expander("⚠️ Reset"):
        st.warning("Cancella lo stato della sessione corrente.")
        if st.button("NUOVA ASTA",use_container_width=True):
            st.session_state.auction=default_state();persist();st.rerun()
    st.caption("Community Cloud: usa BACKUP JSON per conservare una copia indipendente dal server.")

m1,m2,m3,m4,m5=st.columns(5)
m1.metric("💰 Crediti",S["credits"])
m2.metric("💸 Spesi",BUDGET-S["credits"])
m3.metric("👕 Rosa",f'{len(S["roster"])}/25')
m4.metric("🔨 Max",max_absolute())
m5.metric("📊 Mercato",f"{market_index():.2f}x")

tabs=st.tabs(["🔥 ASTA LIVE","🧠 ASTA MASTER","📡 RADAR","👥 AVVERSARI","📋 ROSA","🎯 OBIETTIVI","📈 STORICO"])

with tabs[0]:
    left,right=st.columns([2.15,1])
    with left:
        q=st.text_input("🔎 Cerca",placeholder="Nome giocatore")
        role=st.segmented_control("Ruolo",["TUTTI","POR","DIF","CEN","ATT"],default="TUTTI")
        av=PLAYERS[~PLAYERS.key.isin(set(S["out"]))].copy()
        if role and role!="TUTTI":av=av[av.Ruolo==role]
        if q:av=av[av.Nome.str.contains(q,case=False,na=False)]
        av=av.sort_values(["FVM","Nome"],ascending=[False,True]).head(60)
        labels=[f"{r.Nome} • {r.Ruolo} • {r.Squadra} • FVM {r.FVM}" for _,r in av.iterrows()]
        choice=st.selectbox("Giocatore",labels,index=None,placeholder="Seleziona il giocatore...")
        row=None
        if choice:
            row=av.iloc[labels.index(choice)]
            lo,hi=prediction(row);cap=cap_for(row);comp,nint=competition(row.Ruolo)
            a,b,c,d,e=st.columns(5)
            a.metric("FVM",int(row.FVM));b.metric("Fascia",tier(row.FVM));c.metric("Previsione",f"{lo}-{hi}")
            d.metric("STOP",cap);e.metric("Fit",fit(row))
            st.caption(f"Concorrenza {row.Ruolo}: {comp}/100 • {nint} avversari con slot • Urgenza {urgency(row.Ruolo)}/100 • Scarsità {scarcity(row.Ruolo)}/100")
            pb=plan_b(row)
            if len(pb):
                st.write("**Piano B:** "+ " • ".join(f"{x.Nome} (FVM {x.FVM})" for _,x in pb.iterrows()))
    with right:
        st.subheader("🔨 Esito")
        price=st.number_input("Prezzo",min_value=0,step=1,value=0)
        buyer=st.selectbox("Acquirente",["FC Jigen","NON TRACCIATO"]+RIVALS)
        if row is not None:
            st.markdown(f"### {status_price(row,price)}" if price else "### ⏳ ATTESA")
            if st.button("✅ REGISTRA",type="primary",use_container_width=True):
                k=row.key
                if k in S["out"]:st.error("Giocatore già uscito.")
                elif buyer=="FC Jigen":
                    if role_count(row.Ruolo)>=SLOTS[row.Ruolo]:st.error(f"Slot {row.Ruolo} completi.")
                    elif len(S["roster"])>=25:st.error("Rosa completa.")
                    elif price>S["credits"] or price>max_absolute():st.error("Prezzo incompatibile con la chiusura della rosa.")
                    else:
                        item={"name":row.Nome,"role":row.Ruolo,"team":row.Squadra,"fvm":int(row.FVM),"price":int(price)}
                        S["roster"].append(item);S["out"].append(k)
                        S["moves"].append({**item,"action":"MIO","buyer":"FC Jigen","time":datetime.now().isoformat(timespec="seconds")})
                        normalize();persist();st.rerun()
                else:
                    if buyer!="NON TRACCIATO":
                        d=S["rivals"][buyer]
                        if d["slots"]<=0 or d["roles"][row.Ruolo]<=0:st.error("Avversario senza slot nel ruolo.");st.stop()
                        if price>d["credits"]:st.error("Prezzo superiore ai crediti dell'avversario.");st.stop()
                        d["credits"]-=int(price);d["slots"]-=1;d["roles"][row.Ruolo]-=1
                    S["out"].append(k)
                    S["moves"].append({"name":row.Nome,"role":row.Ruolo,"team":row.Squadra,"fvm":int(row.FVM),
                        "price":int(price),"action":"ALTRI","buyer":buyer,"time":datetime.now().isoformat(timespec="seconds")})
                    persist();st.rerun()
            if st.button("⛔ INVENDUTO",use_container_width=True):
                S["out"].append(row.key)
                S["moves"].append({"name":row.Nome,"role":row.Ruolo,"team":row.Squadra,"fvm":int(row.FVM),
                                   "price":0,"action":"INV","buyer":"-","time":datetime.now().isoformat(timespec="seconds")})
                persist();st.rerun()

with tabs[1]:
    st.subheader("🧠 ASTA MASTER")
    needed=[r for r in SLOTS if role_count(r)<SLOTS[r]]
    cand=PLAYERS[(~PLAYERS.key.isin(set(S["out"])))&PLAYERS.Ruolo.isin(needed)].copy()
    if len(cand):
        cand["Fascia"]=cand.FVM.map(tier);cand["STOP"]=cand.apply(cap_for,axis=1)
        cand["Previsione"]=cand.apply(lambda r:f"{prediction(r)[0]}-{prediction(r)[1]}",axis=1)
        cand["Fit"]=cand.apply(fit,axis=1)
        st.dataframe(cand.sort_values(["Fit","FVM"],ascending=False)[["Nome","Ruolo","Squadra","FVM","Fascia","Previsione","STOP","Fit"]].head(15),
                     hide_index=True,use_container_width=True)
    else:st.success("🏆 Rosa completa")
    st.subheader("Strategia di chiusura")
    rr=[]
    for r in SLOTS:
        missing=SLOTS[r]-role_count(r)
        rr.append({"Ruolo":r,"Presi":role_count(r),"Mancano":missing,"Urgenza":urgency(r),
                   "Scarsità":scarcity(r),"Concorrenza":competition(r)[0],
                   "Budget teorico residuo":round(S["credits"]*ROLE_BUDGET[r]) if remaining_slots() else 0})
    st.dataframe(pd.DataFrame(rr),hide_index=True,use_container_width=True)

with tabs[2]:
    st.subheader("📡 RADAR")
    rr=[]
    for r in SLOTS:
        sc,n=competition(r)
        label="CRITICA" if sc>=75 else "ALTA" if sc>=55 else "MEDIA" if sc>=32 else "BASSA"
        rr.append({"Ruolo":r,"Pressione":sc,"Livello":label,"Avversari interessati":n,
                   "Scarsità":scarcity(r),"Urgenza FC Jigen":urgency(r)})
    st.dataframe(pd.DataFrame(rr),hide_index=True,use_container_width=True)
    rivals=[]
    for n,d in S["rivals"].items():
        avg=d["credits"]/max(1,d["slots"])
        rivals.append({"Squadra":n,"Crediti":d["credits"],"Slot":d["slots"],"Crediti/slot":round(avg,1),
                       "Potenza":"ALTA" if avg>=45 else "MEDIA" if avg>=25 else "BASSA"})
    st.dataframe(pd.DataFrame(rivals).sort_values("Crediti/slot",ascending=False),hide_index=True,use_container_width=True)

with tabs[3]:
    st.subheader("👥 Avversari")
    selected=st.selectbox("Modifica squadra",RIVALS)
    d=S["rivals"][selected]
    c1,c2=st.columns(2)
    with c1:
        cred=st.number_input("Crediti",0,BUDGET,int(d["credits"]),key="rvcred")
        slots=st.number_input("Slot totali",0,25,int(d["slots"]),key="rvslots")
    with c2:
        vals={}
        for r in SLOTS:vals[r]=st.number_input(f"Slot {r}",0,SLOTS[r],int(d["roles"][r]),key=f"rv_{r}")
    if st.button("💾 Aggiorna avversario"):
        d["credits"]=int(cred);d["slots"]=int(slots);d["roles"]={r:int(vals[r]) for r in SLOTS};persist();st.rerun()
    rows=[{"Squadra":n,"Crediti":x["credits"],"Slot":x["slots"],**x["roles"],
           "Crediti/slot":round(x["credits"]/max(1,x["slots"]),1)} for n,x in S["rivals"].items()]
    st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)

with tabs[4]:
    st.subheader("📋 Rosa FC Jigen")
    if S["roster"]:
        rdf=pd.DataFrame(S["roster"]).rename(columns={"name":"Nome","role":"Ruolo","team":"Squadra","fvm":"FVM","price":"Prezzo"})
        st.dataframe(rdf,hide_index=True,use_container_width=True)
        st.download_button("⬇️ Rosa CSV",rdf.to_csv(index=False).encode(),file_name="rosa_fc_jigen.csv",mime="text/csv")
        c1,c2,c3,c4=st.columns(4)
        for col,r in zip((c1,c2,c3,c4),SLOTS):
            col.metric(r,f"{role_count(r)}/{SLOTS[r]}")
    else:st.info("Nessun acquisto.")

with tabs[5]:
    st.subheader("🎯 Obiettivi")
    q2=st.text_input("Cerca obiettivo",key="targetsearch")
    pool=PLAYERS[~PLAYERS.key.isin(set(S["out"]))].copy()
    if q2:pool=pool[pool.Nome.str.contains(q2,case=False,na=False)]
    opts=[f"{r.Nome} • {r.Ruolo} • FVM {r.FVM}" for _,r in pool.sort_values("FVM",ascending=False).head(80).iterrows()]
    t=st.selectbox("Giocatore",opts,index=None,key="targetpick")
    fascia=st.selectbox("Priorità",["A","B","C"])
    if t and st.button("➕ Salva obiettivo"):
        name=t.split(" • ")[0]
        r=pool[pool.Nome==name].iloc[0]
        S["targets"][r.key]={"name":r.Nome,"role":r.Ruolo,"fvm":int(r.FVM),"priority":fascia};persist();st.rerun()
    if S["targets"]:
        td=pd.DataFrame(S["targets"].values()).rename(columns={"name":"Nome","role":"Ruolo","fvm":"FVM","priority":"Priorità"})
        st.dataframe(td.sort_values(["Priorità","FVM"],ascending=[True,False]),hide_index=True,use_container_width=True)

with tabs[6]:
    st.subheader("📈 Storico")
    if S["moves"]:
        h=pd.DataFrame(S["moves"])
        st.dataframe(h.iloc[::-1],hide_index=True,use_container_width=True)
        st.download_button("⬇️ Storico CSV",h.to_csv(index=False).encode(),file_name="storico_asta.csv",mime="text/csv")
        st.caption(f"{len(h)} operazioni • indice mercato {market_index():.2f}x")
    else:st.info("Storico vuoto.")
