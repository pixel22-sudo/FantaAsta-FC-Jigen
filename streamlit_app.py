# VERSIONE v3.8.2 SIDE MENU
# FC Jigen - file corretto per GitHub

import re
import time
import streamlit as st
import pandas as pd
import json, statistics, hashlib, time
from supabase import create_client

import unicodedata

def _norm_search(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())

# Alias d'uso -> nome presente nel listone ufficiale.
# Serve soprattutto per i giocatori che Fantacalcio abbrevia con cognome + iniziale.
PLAYER_ALIASES = {
    "lautaro": "Martinez L.",
    "lautaro martinez": "Martinez L.",
    "martinez lautaro": "Martinez L.",
    "nico paz": "Paz N.",
    "nicolas paz": "Paz N.",
    "paz nico": "Paz N.",
    "goncalo ramos": "Ramos G.",
    "gonzalo ramos": "Ramos G.",
    "francesco pio esposito": "Esposito F.P.",
    "pio esposito": "Esposito F.P.",
    "esposito pio": "Esposito F.P.",
    "scott mctominay": "McTominay",
    "mctominay scott": "McTominay",
    "hakan calhanoglu": "Calhanoglu",
    "federico dimarco": "Dimarco",
    "marcus thuram": "Thuram",
    "rasmus hojlund": "Hojlund",
    "christian pulisic": "Pulisic",
    "kenan yildiz": "Yildiz",
    "moise kean": "Kean",
    "riccardo orsolini": "Orsolini",
}

def smart_player_mask(df, query):
    """Ricerca su nome ufficiale + alias comuni, accent-insensitive e case-insensitive."""
    q = _norm_search(query)
    if not q:
        return pd.Series([True] * len(df), index=df.index)

    official = df["Nome"].astype(str).map(_norm_search)
    mask = official.str.contains(q, regex=False, na=False)

    # Alias: match sia esatto/parziale sull'alias, poi traduzione verso il nome ufficiale.
    alias_targets = []
    for alias, target in PLAYER_ALIASES.items():
        na = _norm_search(alias)
        if q in na or na in q:
            alias_targets.append(_norm_search(target))

    if alias_targets:
        mask = mask | official.isin(alias_targets)

    # Se l'utente scrive più parole, prova anche tutte le parole senza ordine.
    tokens = [t for t in q.split() if len(t) >= 2]
    if len(tokens) >= 2:
        token_mask = pd.Series([True] * len(df), index=df.index)
        for token in tokens:
            token_mask &= official.str.contains(token, regex=False, na=False)
        mask = mask | token_mask

    return mask
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="FantaAsta FC Jigen", page_icon="⚽", layout="wide",
                   initial_sidebar_state="collapsed")

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
        # Official Streamlit/Supabase examples use flat SUPABASE_URL/SUPABASE_KEY.
        # Keep compatibility with the previous [supabase] nested format too.
        url = str(st.secrets.get("SUPABASE_URL", "")).strip()
        key = str(st.secrets.get("SUPABASE_KEY", "")).strip()
        if not url or not key:
            cfg = st.secrets.get("supabase", {})
            url = str(cfg.get("url", "")).strip()
            key = str(cfg.get("key", "")).strip()
        if not url or not key:
            return None
        return create_client(url, key)
    except Exception as exc:
        st.session_state["_cloud_error"] = f"{type(exc).__name__}: {exc}"
        return None

def cloud_config_status():
    try:
        url = str(st.secrets.get("SUPABASE_URL", "")).strip()
        key = str(st.secrets.get("SUPABASE_KEY", "")).strip()
        if url and key:
            return True
        cfg = st.secrets.get("supabase", {})
        return bool(str(cfg.get("url", "")).strip() and str(cfg.get("key", "")).strip())
    except Exception:
        return False

def cloud_load():
    sb = cloud_client()
    if not sb:
        return None
    try:
        res = sb.table("fanta_auction_state").select("state").eq("id", CLOUD_ID).maybe_single().execute()
        data = getattr(res, "data", None)
        st.session_state["_cloud_read_ok"] = True
        st.session_state.pop("_cloud_error", None)
        if data and isinstance(data.get("state"), dict) and data["state"].get("roster") is not None:
            return data["state"]
    except Exception as exc:
        st.session_state["_cloud_read_ok"] = False
        st.session_state["_cloud_error"] = f"{type(exc).__name__}: {exc}"
    return None

def cloud_save(state):
    sb = cloud_client()
    if not sb:
        st.session_state["_cloud_error"] = "Client Supabase non disponibile"
        return False
    try:
        payload = {"id": CLOUD_ID, "state": state, "updated_at": datetime.now().isoformat()}
        # The row already exists: UPDATE is simpler and avoids INSERT/UPSERT ambiguity under RLS.
        res = sb.table("fanta_auction_state").update(payload).eq("id", CLOUD_ID).execute()
        data = getattr(res, "data", None)
        ok = isinstance(data, list) and len(data) > 0
        if ok:
            st.session_state.pop("_cloud_error", None)
            st.session_state["_cloud_last_save"] = datetime.now().strftime("%H:%M:%S")
        else:
            st.session_state["_cloud_error"] = "Nessuna riga aggiornata da Supabase"
        return ok
    except Exception as exc:
        st.session_state["_cloud_error"] = f"{type(exc).__name__}: {exc}"
        return False

def persist():
    ok = cloud_save(st.session_state.auction)
    st.session_state["_cloud_ok"] = ok
    return ok

def manual_cloud_save():
    ok = persist()
    st.session_state["_cloud_notice"] = (
        "✅ Cloud salvato correttamente" if ok
        else "❌ Salvataggio cloud fallito"
    )



def recommended_targets():
    """Piano iniziale FC Jigen: modificabile dall'iPhone e salvato nel Cloud."""
    rows = [
        # POR
        ("Svilar","POR","A",28,38,"Carnesecchi / Butez","Top portiere, niente guerra di rilanci"),
        ("Carnesecchi","POR","B",20,30,"Svilar / Caprile","Alternativa premium"),
        ("Butez","POR","C",8,16,"Caprile / Falcone","Valore se i top salgono"),
        ("Caprile","POR","C",5,12,"Falcone","Low cost affidabile"),
        ("Falcone","POR","C",3,9,"Caprile","Ultimo piano portieri"),

        # DIF
        ("Dimarco","DIF","A",78,105,"Bremer / Bastoni","Top difesa e bonus; fermarsi allo STOP"),
        ("Bremer","DIF","A",28,42,"Mancini / Bastoni","Modificatore + affidabilità"),
        ("Mancini","DIF","B",18,28,"Bastoni / Rrahmani","Buona media + bonus"),
        ("Bastoni","DIF","B",14,24,"Rrahmani / Buongiorno","Profilo da modificatore"),
        ("Rrahmani","DIF","B",10,19,"Buongiorno / Pavlovic","Titolare affidabile"),
        ("Cambiaso","DIF","B",10,20,"Bellanova / Pavlovic","Bonus potenziali"),
        ("Bellanova","DIF","C",7,15,"Pavlovic / Scalvini","Esterno da bonus"),
        ("Buongiorno","DIF","C",6,14,"Pavlovic / Scalvini","Media voto"),
        ("Pavlovic","DIF","C",5,12,"Scalvini / Miranda J.","Qualità/prezzo"),
        ("Scalvini","DIF","C",4,10,"Miranda J. / Delprato","Scommessa controllata"),
        ("Delprato","DIF","C",2,7,"Valeri","Low cost"),
        ("Valeri","DIF","C",2,6,"Delprato","Low cost"),

        # CEN
        ("Paz N.","CEN","A",78,105,"McTominay / Calhanoglu","Top obiettivo centrocampo"),
        ("McTominay","CEN","A",65,92,"Paz N. / Calhanoglu","Top alternativo"),
        ("Calhanoglu","CEN","A",58,85,"Pulisic / Yildiz","Piazzati e bonus"),
        ("Pulisic","CEN","B",35,55,"Yildiz / Samardzic","Bonus, non strapagare"),
        ("Yildiz","ATT","B",28,48,"Pulisic / Samardzic","Upside"),
        ("Samardzic","CEN","B",16,31,"Baturina / Vlasic","Rapporto prezzo/potenziale"),
        ("Baturina","CEN","C",8,18,"Vlasic / Gaetano","Scommessa"),
        ("Vlasic","CEN","C",7,16,"Gaetano / Ferguson","Titolare con bonus"),
        ("Gaetano","CEN","C",5,13,"Ferguson / Mastantuono","Rotazione"),
        ("Ferguson","CEN","C",4,11,"Mastantuono / Alajbegovic","Valore"),
        ("Mastantuono","CEN","C",3,10,"Alajbegovic","Scommessa ad alto potenziale"),
        ("Alajbegovic","CEN","C",2,8,"Mastantuono","Scommessa low cost"),

        # ATT
        ("Martinez L.","ATT","A",270,325,"Malen / Hojlund","Lautaro: top assoluto, STOP rigido"),
        ("Malen","ATT","A",250,315,"Martinez L. / Hojlund","Alternativa top"),
        ("Hojlund","ATT","A",125,170,"Thuram / Ramos G.","Secondo slot premium"),
        ("Thuram","ATT","A",120,165,"Hojlund / Ramos G.","Secondo slot premium"),
        ("Ramos G.","ATT","A",105,155,"Hojlund / Kean","Alternativa forte"),
        ("Kean","ATT","B",75,115,"Douvikas / Scamacca","Buon secondo/terzo slot"),
        ("Orsolini","CEN","A",65,100,"Pulisic / Zaccagni","Bonus e piazzati"),
        ("Scamacca","ATT","B",35,60,"Krstovic / Douvikas","Terzo slot se prezzo giusto"),
        ("Douvikas","ATT","B",28,52,"Krstovic / Berardi","Valore"),
        ("Krstovic","ATT","C",22,45,"Douvikas / Berardi","Alternativa"),
        ("Berardi","ATT","C",20,42,"Zaccagni / De Ketelaere","Bonus se sottoprezzato"),
        ("De Ketelaere","ATT","C",18,38,"Zaccagni / Raspadori","Upside"),
        ("Zaccagni","CEN","B",17,36,"Orsolini / Pulisic","Bonus"),
        ("Dybala","ATT","C",14,32,"Raspadori","Talento con rischio"),
        ("Raspadori","ATT","C",10,26,"migliore occasione rimasta","Ultimi slot"),
    ]
    result = {}
    for name, role, prio, ideal, maxp, alt, note in rows:
        m = PLAYERS[(PLAYERS["Nome"] == name) & (PLAYERS["Ruolo"] == role)]
        if m.empty:
            continue
        r = m.iloc[0]
        result[r.key] = {
            "name": r.Nome, "role": r.Ruolo, "team": r.Squadra, "fvm": int(r.FVM),
            "priority": prio, "ideal": int(ideal), "max": int(maxp),
            "alternatives": alt, "notes": note, "status": "ATTIVO"
        }
    return result

def target_defaults(t):
    t.setdefault("team", "")
    t.setdefault("priority", "C")
    t.setdefault("ideal", 0)
    t.setdefault("max", 0)
    t.setdefault("alternatives", "")
    t.setdefault("notes", "")
    t.setdefault("status", "ATTIVO")
    return t

def _auto_priority(fvm):
    fvm=int(fvm or 0)
    if fvm >= 220: return "A"
    if fvm >= 110: return "B"
    return "C"

def auto_target_prices(row):
    """Prezzi automatici per qualsiasi giocatore, ancorati ai target del Piano FC Jigen."""
    rec = recommended_targets()
    same = [v for v in rec.values() if v.get("role")==row.Ruolo and int(v.get("fvm",0) or 0)>0]
    fvm=max(1,int(row.FVM))
    if same:
        ref=min(same,key=lambda v: abs(int(v.get("fvm",0))-fvm))
        rf=max(1,int(ref.get("fvm",1)))
        ideal=max(1,round(fvm * int(ref.get("ideal",1)) / rf))
        stop=max(ideal,round(fvm * int(ref.get("max",ideal)) / rf))
    else:
        role_ratio={"POR":(.22,.42),"DIF":(.30,.48),"CEN":(.24,.40),"ATT":(.38,.58)}
        ri,rs=role_ratio.get(row.Ruolo,(.25,.45))
        ideal=max(1,round(fvm*ri))
        stop=max(ideal,round(fvm*rs))
    return {
        "name":row.Nome,"role":row.Ruolo,"team":row.Squadra,"fvm":fvm,
        "priority":_auto_priority(fvm),"ideal":ideal,"max":stop,
        "alternatives":"","notes":"Stima automatica","status":"ATTIVO","auto":True
    }

def effective_target_plan(row):
    """Usa il piano manuale se completo; altrimenti ripara/integra automaticamente."""
    k=row.key
    rec=recommended_targets()
    current=S.get("targets",{}).get(k)
    if current:
        current=target_defaults(current)
        # Se è un target del piano e i vecchi valori Cloud sono a zero, usa i valori ufficiali del piano.
        if k in rec:
            base=rec[k]
            if int(current.get("ideal",0) or 0)<=0:
                current["ideal"]=int(base["ideal"])
            if int(current.get("max",0) or 0)<=0:
                current["max"]=int(base["max"])
            if not current.get("alternatives"):
                current["alternatives"]=base.get("alternatives","")
            if not current.get("notes"):
                current["notes"]=base.get("notes","")
            if not current.get("team"):
                current["team"]=base.get("team","")
            current["fvm"]=int(base.get("fvm",row.FVM))
            return current
        # Target manuale generico: mai mostrare 0/0.
        auto=auto_target_prices(row)
        if int(current.get("ideal",0) or 0)<=0:
            current["ideal"]=auto["ideal"]
        if int(current.get("max",0) or 0)<=0:
            current["max"]=auto["max"]
        current["fvm"]=int(row.FVM)
        return current
    # Giocatore non target: mostra comunque valori automatici utili.
    return auto_target_prices(row)

def repair_saved_targets():
    """Migrazione una tantum dei target già presenti nel Cloud con prezzi mancanti/zero."""
    repaired=0
    rec=recommended_targets()
    for k,t in list(S.get("targets",{}).items()):
        if not isinstance(t,dict):
            continue
        target_defaults(t)
        if k in rec:
            base=rec[k]
            changed=False
            if int(t.get("ideal",0) or 0)<=0:
                t["ideal"]=int(base["ideal"]); changed=True
            if int(t.get("max",0) or 0)<=0:
                t["max"]=int(base["max"]); changed=True
            if not t.get("alternatives"):
                t["alternatives"]=base.get("alternatives",""); changed=True
            if not t.get("notes"):
                t["notes"]=base.get("notes",""); changed=True
            if changed: repaired+=1
        else:
            # Cerca la riga del listone per i target manuali.
            m=all_players()[all_players().key==k]
            if not m.empty and (int(t.get("ideal",0) or 0)<=0 or int(t.get("max",0) or 0)<=0):
                auto=auto_target_prices(m.iloc[0])
                if int(t.get("ideal",0) or 0)<=0: t["ideal"]=auto["ideal"]
                if int(t.get("max",0) or 0)<=0: t["max"]=auto["max"]
                repaired+=1
    return repaired


def default_state():
    return {
        "schema": 3, "team": "FC Jigen", "credits": BUDGET,
        "roster": [], "out": [], "moves": [], "targets": {},
        "custom_players": [],
        "plan_budget": {"POR": 40, "DIF": 170, "CEN": 250, "ATT": 540},
        "rivals": {n: {"credits": BUDGET, "slots": 25, "roles": dict(SLOTS)} for n in RIVALS}
    }

if "auction" not in st.session_state:
    cloud_state = cloud_load()
    st.session_state.auction = cloud_state if cloud_state else default_state()
    st.session_state["_cloud_ok"] = bool(cloud_state)
S = st.session_state.auction

def all_players():
    """Listone base + eventuali nuovi arrivi inseriti da iPhone."""
    if not S.get("custom_players"):
        return PLAYERS
    rows=[]
    for x in S.get("custom_players",[]):
        try:
            name=str(x.get("name","")).strip()
            role=str(x.get("role","")).strip()
            team=str(x.get("team","")).strip()
            if not name or role not in SLOTS:
                continue
            fvm=max(1,int(x.get("fvm",1) or 1))
            qta=max(1,int(x.get("qta",1) or 1))
            rows.append({
                "Id": f"CUSTOM-{_norm_search(role+'-'+name)}",
                "R": {"POR":"P","DIF":"D","CEN":"C","ATT":"A"}[role],
                "RM": role, "Nome": name, "Squadra": team,
                "QtA": qta, "FVM": fvm, "Ruolo": role, "key": f"{role}|{name}",
            })
        except Exception:
            continue
    if not rows:
        return PLAYERS
    custom=pd.DataFrame(rows)
    # Ensure every column used by the app exists.
    for c in PLAYERS.columns:
        if c not in custom.columns:
            custom[c]=0 if c in ("FVM","QtA") else ""
    custom=custom[PLAYERS.columns]
    base=PLAYERS[~PLAYERS["key"].isin(set(custom["key"]))].copy()
    return pd.concat([base,custom],ignore_index=True)

def normalize():
    S.setdefault("schema",2); S.setdefault("team","FC Jigen")
    S.setdefault("roster",[]); S.setdefault("out",[]); S.setdefault("moves",[])
    S.setdefault("targets",{}); S.setdefault("rivals",{})
    S.setdefault("custom_players",[])
    S.setdefault("plan_budget", {"POR":40,"DIF":170,"CEN":250,"ATT":540})
    for r,v in {"POR":40,"DIF":170,"CEN":250,"ATT":540}.items():
        S["plan_budget"].setdefault(r,v)
    for _, t in S["targets"].items():
        if isinstance(t, dict):
            target_defaults(t)
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
_repaired_targets = repair_saved_targets()
if _repaired_targets:
    st.session_state["_prices_repaired"] = _repaired_targets
    persist()

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
    ap=all_players(); top=ap[(ap.Ruolo==role)&(~ap.key.isin(set(S["out"])))&(ap.FVM>=140)]
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
    ap=all_players(); df=ap[(ap.Ruolo==row.Ruolo)&(~ap.key.isin(set(S["out"])))&(ap.key!=row.key)].copy()
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

/* v3.6 iPHONE EASY */
div.stButton > button {min-height:52px;font-weight:700;border-radius:14px}
div[data-testid="stNumberInput"] input {font-size:1.35rem;font-weight:800;text-align:center}
div[data-testid="stSelectbox"] > div {min-height:48px}
div[data-testid="stTextInput"] input {min-height:48px;font-size:1.05rem}
div[data-testid="stMetric"] {padding:9px;border-radius:14px}
div[data-testid="stMetricValue"] {font-size:1.35rem}
button[data-baseweb="tab"] {font-weight:700}
@media (max-width: 700px) {
  .block-container {padding-top:.75rem;padding-left:.65rem;padding-right:.65rem;padding-bottom:2rem}
  h1 {font-size:1.65rem !important;line-height:1.15}
  h2,h3 {line-height:1.2}
  div[data-testid="stMetric"] {padding:7px}
  div[data-testid="stMetricLabel"] {font-size:.77rem}
  div[data-testid="stMetricValue"] {font-size:1.15rem}
  div[data-testid="column"] {min-width:0 !important}
  button[data-baseweb="tab"] {padding-left:.65rem;padding-right:.65rem}
}

/* v3.7 compact mobile header */
.jigen-head {
  display:flex; align-items:center; justify-content:space-between; gap:8px;
  margin:0 0 7px 0; padding:0 2px;
}
.jigen-brand {
  font-size:1.03rem; font-weight:800; line-height:1.15; white-space:nowrap;
  overflow:hidden; text-overflow:ellipsis;
}
.jigen-cloud {
  font-size:.78rem; font-weight:700; white-space:nowrap;
}
.jigen-summary {
  display:grid; grid-template-columns:1fr 1fr 1fr; gap:6px;
  border:1px solid rgba(128,128,128,.24); border-radius:14px;
  padding:7px 7px; margin:2px 0 8px 0;
}
.jigen-stat {
  text-align:center; min-width:0; padding:2px 3px;
}
.jigen-stat-label {
  font-size:.66rem; opacity:.72; font-weight:700; white-space:nowrap;
}
.jigen-stat-value {
  font-size:1.28rem; line-height:1.15; font-weight:800; white-space:nowrap;
}
.jigen-mini-detail {
  font-size:.72rem; opacity:.70; text-align:center; margin-top:-2px; margin-bottom:4px;
}
@media (max-width:700px) {
  .jigen-brand {font-size:.94rem}
  .jigen-cloud {font-size:.70rem}
  .jigen-summary {gap:3px; padding:6px 4px}
  .jigen-stat-label {font-size:.60rem}
  .jigen-stat-value {font-size:1.18rem}
}


@media (max-width:700px) {
  div.stButton > button {min-height:45px !important; padding:.38rem .45rem !important}
  div[data-testid="stTextInput"] input {min-height:43px !important}
  div[data-testid="stSelectbox"] > div {min-height:43px !important}
}


@media (max-width:700px) {
  div[data-testid="stHorizontalBlock"]:has(button[kind="secondary"]) {
    gap:.45rem !important;
  }
}



/* v3.7.3 — iPhone: niente scroll orizzontale */
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
  max-width:100vw !important;
  overflow-x:hidden !important;
}
.block-container {
  max-width:100% !important;
  overflow-x:hidden !important;
}



/* v3.7.6 — barra azioni mobile senza overflow */
@media (max-width:700px) {
  .st-key-quick_action_bar {
    width:100% !important;
    max-width:100% !important;
    overflow:hidden !important;
  }
  .st-key-quick_action_bar div[role="radiogroup"] {
    width:100% !important;
    display:flex !important;
    flex-wrap:nowrap !important;
  }
  .st-key-quick_action_bar button {
    flex:1 1 50% !important;
    min-width:0 !important;
    max-width:50% !important;
    white-space:nowrap !important;
    font-size:.82rem !important;
  }
}


/* v3.8.2 SIDE MENU */
@media (max-width:700px) {
 .st-key-safe_actions {width:100%!important;max-width:100%!important;overflow:hidden!important;}
 .st-key-safe_actions [data-testid="stHorizontalBlock"] {display:flex!important;flex-direction:row!important;flex-wrap:nowrap!important;gap:.4rem!important;width:100%!important;}
 .st-key-safe_actions [data-testid="column"] {flex:1 1 0!important;width:0!important;min-width:0!important;}
 .st-key-safe_actions button {width:100%!important;min-width:0!important;white-space:nowrap!important;font-size:.82rem!important;}
}

</style>""",unsafe_allow_html=True)


def _quick_price(delta):
    cur = int(st.session_state.get("live_price", 0) or 0)
    st.session_state["live_price"] = max(0, cur + int(delta))

def _reset_live_price():
    st.session_state["live_price"] = 0

def _quick_cloud_save():
    manual_cloud_save()

def _quick_undo():
    _guard_sig = repr(tuple(locals().get(k) for k in []))
    _guard_now = time.monotonic()
    _guard_last = st.session_state.get("_auction_last_action")
    if _guard_last and _guard_last[0] == _guard_sig and (_guard_now - _guard_last[1]) < 0.8:
        return
    st.session_state["_auction_last_action"] = (_guard_sig, _guard_now)

    if S.get("moves"):
        do_undo()
        persist()
        st.session_state["_quick_notice"] = "↩️ Ultima operazione annullata"
    else:
        st.session_state["_quick_notice"] = "ℹ️ Nessuna operazione da annullare"

cloud_badge = "☁️ Cloud OK" if st.session_state.get("_cloud_ok") else "☁️ Cloud"
st.markdown(
    f"""<div class="jigen-head">
      <div class="jigen-brand">⚽ FC Jigen • v3.8.2 SIDE MENU</div>
      <div class="jigen-cloud">{cloud_badge}</div>
    </div>""",
    unsafe_allow_html=True
)

with st.sidebar:
    st.header("⚡ MENU ASTA")
    st.caption("Azioni rapide • si richiude con la freccia")
    st.button("☁️ SALVA ORA", use_container_width=True, on_click=_quick_cloud_save, key="sidebar_quick_save")
    st.button("↩️ ANNULLA ULTIMA", use_container_width=True, on_click=_quick_undo, key="sidebar_quick_undo")
    quick_sidebar_notice=st.session_state.pop("_quick_notice",None)
    if quick_sidebar_notice:
        if quick_sidebar_notice.startswith("↩️"):
            st.success(quick_sidebar_notice)
        else:
            st.info(quick_sidebar_notice)
    st.divider()
    st.subheader("☁️ Cloud e sicurezza")
    secrets_ready = cloud_config_status()
    sb_ready = cloud_client() is not None
    if secrets_ready and sb_ready:
        if st.session_state.get("_cloud_ok"):
            last = st.session_state.get("_cloud_last_save", "")
            st.success("☁️ Cloud collegato" + (f" • {last}" if last else ""))
        else:
            st.info("☁️ Secrets letti • testa il Cloud")
        notice = st.session_state.get("_cloud_notice")
        if notice:
            if notice.startswith("✅"):
                st.success(notice)
            else:
                st.error(notice)
                err = st.session_state.get("_cloud_error")
                if err:
                    st.caption("Diagnostica: " + err)
    elif not secrets_ready:
        st.warning("☁️ Secrets Supabase non letti da Streamlit")
    else:
        st.error("☁️ Configurazione cloud non valida")
        err = st.session_state.get("_cloud_error")
        if err:
            st.caption("Diagnostica: " + err)
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
    with st.expander("⚠️ Reset"):
        st.warning("Cancella lo stato della sessione corrente.")
        if st.button("NUOVA ASTA",use_container_width=True):
            st.session_state.auction=default_state();persist();st.rerun()
    st.caption("Community Cloud: usa BACKUP JSON per conservare una copia indipendente dal server.")

st.markdown(
    f"""<div class="jigen-summary">
      <div class="jigen-stat">
        <div class="jigen-stat-label">💰 CREDITI</div>
        <div class="jigen-stat-value">{S["credits"]}</div>
      </div>
      <div class="jigen-stat">
        <div class="jigen-stat-label">👕 ROSA</div>
        <div class="jigen-stat-value">{len(S["roster"])}/25</div>
      </div>
      <div class="jigen-stat">
        <div class="jigen-stat-label">🔨 MAX</div>
        <div class="jigen-stat-value">{max_absolute()}</div>
      </div>
    </div>
    <div class="jigen-mini-detail">Spesi {BUDGET-S["credits"]} • Mercato {market_index():.2f}x</div>""",
    unsafe_allow_html=True
)

tabs=st.tabs(["🔥 LIVE","🧠 MASTER","📡 RADAR","👥 RIVALI","📋 ROSA","🎯 PIANO","📈 STORICO"])

with tabs[0]:
    st.markdown("### 🔥 ASTA LIVE")
    st.caption("☰ Menu laterale: SALVA • ANNULLA • BACKUP • stato Cloud")

    quick_notice=st.session_state.pop("_quick_notice",None)
    if quick_notice:
        st.info(quick_notice)
    repaired_notice=st.session_state.pop("_prices_repaired",None)
    if repaired_notice:
        st.success(f"✅ Prezzi Piano riparati: {repaired_notice} target aggiornati")
    cloud_notice=st.session_state.get("_cloud_notice")
    if cloud_notice and cloud_notice.startswith("✅"):
        st.caption(cloud_notice)

    q=st.text_input(
        "🔎 Cerca giocatore",
        placeholder="Lautaro, Nico Paz, Dimarco...",
        key="asta_live_search"
    )
    role=st.segmented_control("RUOLO",["TUTTI","POR","DIF","CEN","ATT"],default="TUTTI",key="live_role")
    ap=all_players(); av=ap[~ap.key.isin(set(S["out"]))].copy()
    if role and role!="TUTTI":
        av=av[av.Ruolo==role]
    termine=q.strip()
    if termine:
        av=av[smart_player_mask(av, termine)]
    av=av.sort_values(["FVM","Nome"],ascending=[False,True]).head(60)

    if termine and av.empty:
        st.warning(f"Nessun giocatore trovato per “{termine}”.")
    elif termine:
        alias_target=PLAYER_ALIASES.get(_norm_search(termine))
        if alias_target and alias_target in set(av["Nome"].astype(str)):
            st.success(f"✅ {termine} → {alias_target}")

    labels=[f"{r.Nome} • {r.Ruolo} • {r.Squadra} • FVM {r.FVM}" for _,r in av.iterrows()]
    choice=st.selectbox(
        "Giocatore",
        labels,
        index=None,
        placeholder=("Nessun risultato" if not labels else "Tocca per scegliere..."),
        key="asta_live_player"
    )

    row=None
    if choice:
        row=av.iloc[labels.index(choice)]
        lo,hi=prediction(row); cap=cap_for(row); comp,nint=competition(row.Ruolo)
        manual_plan=S["targets"].get(row.key)
        plan=effective_target_plan(row)

        st.markdown(f"## {row.Nome}")
        st.caption(f"{row.Ruolo} • {row.Squadra} • FVM {int(row.FVM)}")

        p1,p2,p3=st.columns(3)
        p1.metric("🎯",plan.get("priority","C") if manual_plan else f'{plan.get("priority","C")} AUTO')
        p2.metric("💚 IDEALE",int(plan.get("ideal",1) or 1))
        p3.metric("🛑 STOP",int(plan.get("max",1) or 1))

        st.markdown("### 💶 PREZZO")
        price=st.number_input(
            "Prezzo asta",
            min_value=0,
            step=1,
            value=0,
            key="live_price",
            label_visibility="collapsed"
        )

        b1,b2,b3,b4,b5=st.columns(5)
        b1.button("−1",use_container_width=True,on_click=_quick_price,args=(-1,))
        b2.button("+1",use_container_width=True,on_click=_quick_price,args=(1,))
        b3.button("+5",use_container_width=True,on_click=_quick_price,args=(5,))
        b4.button("+10",use_container_width=True,on_click=_quick_price,args=(10,))
        b5.button("0",use_container_width=True,on_click=_reset_live_price)

        live_status=status_price(row,price) if price else "⏳ ATTESA"
        manual=S["targets"].get(row.key)
        if price and manual:
            eff=effective_target_plan(row)
            if int(eff.get("max",0) or 0)>0 and price>int(eff.get("max",0) or 0):
                live_status="⛔ STOP PIANO"

        if "STOP" in live_status or "OVERPAY" in live_status:
            st.error(live_status)
        elif "AFFARE" in live_status:
            st.success(live_status)
        else:
            st.info(live_status)

        buyer=st.selectbox(
            "👤 Compratore",
            ["FC Jigen","NON TRACCIATO"]+RIVALS,
            key="live_buyer"
        )

        if st.button("✅ REGISTRA",type="primary",use_container_width=True):
            k=row.key
            if k in S["out"]:
                st.error("Giocatore già uscito.")
            elif buyer=="FC Jigen":
                if role_count(row.Ruolo)>=SLOTS[row.Ruolo]:
                    st.error(f"Slot {row.Ruolo} completi.")
                elif len(S["roster"])>=25:
                    st.error("Rosa completa.")
                elif price>S["credits"] or price>max_absolute():
                    st.error("Prezzo incompatibile con la chiusura della rosa.")
                else:
                    item={"name":row.Nome,"role":row.Ruolo,"team":row.Squadra,"fvm":int(row.FVM),"price":int(price)}
                    S["roster"].append(item); S["out"].append(k)
                    S["moves"].append({**item,"action":"MIO","buyer":"FC Jigen","time":datetime.now().isoformat(timespec="seconds")})
                    normalize(); persist()
                    st.session_state["live_price"]=0
                    st.rerun()
            else:
                if buyer!="NON TRACCIATO":
                    d=S["rivals"][buyer]
                    if d["slots"]<=0 or d["roles"][row.Ruolo]<=0:
                        st.error("Avversario senza slot nel ruolo."); st.stop()
                    if price>d["credits"]:
                        st.error("Prezzo superiore ai crediti dell'avversario."); st.stop()
                    d["credits"]-=int(price); d["slots"]-=1; d["roles"][row.Ruolo]-=1
                S["out"].append(k)
                S["moves"].append({"name":row.Nome,"role":row.Ruolo,"team":row.Squadra,"fvm":int(row.FVM),
                    "price":int(price),"action":"ALTRI","buyer":buyer,"time":datetime.now().isoformat(timespec="seconds")})
                persist()
                st.session_state["live_price"]=0
                st.rerun()

        if st.button("⛔ INVENDUTO",use_container_width=True):
            S["out"].append(row.key)
            S["moves"].append({"name":row.Nome,"role":row.Ruolo,"team":row.Squadra,"fvm":int(row.FVM),
                               "price":0,"action":"INV","buyer":"-","time":datetime.now().isoformat(timespec="seconds")})
            persist()
            st.session_state["live_price"]=0
            st.rerun()

        with st.expander("🧠 Dettagli e Piano B",expanded=False):
            a,b,c=st.columns(3)
            a.metric("Fascia",tier(row.FVM))
            b.metric("Fit",fit(row))
            c.metric("Stima",f"{lo}-{hi}")
            st.caption(f"Concorrenza {row.Ruolo}: {comp}/100 • {nint} rivali con slot • Urgenza {urgency(row.Ruolo)}/100 • Scarsità {scarcity(row.Ruolo)}/100")
            if plan:
                if plan.get("alternatives"):
                    st.write("**Alternative:** "+str(plan.get("alternatives")))
                if plan.get("notes"):
                    st.write("**Nota:** "+str(plan.get("notes")))
            pb=plan_b(row)
            if len(pb):
                st.write("**Piano B automatico:** "+ " • ".join(f"{x.Nome} (FVM {x.FVM})" for _,x in pb.iterrows()))
    else:
        st.info("Cerca e seleziona un giocatore: il resto della schermata comparirà qui.")

with tabs[1]:
    st.subheader("🧠 ASTA MASTER")
    needed=[r for r in SLOTS if role_count(r)<SLOTS[r]]
    ap=all_players(); cand=ap[(~ap.key.isin(set(S["out"])))&ap.Ruolo.isin(needed)].copy()
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
    st.subheader("🎯 Piano Asta FC Jigen")
    st.caption("Listone aggiornato 01/09/2026 sui valori ufficiali verificati • nuovi arrivi gestibili da iPhone • modifiche salvate nel Cloud.")

    st.markdown("#### 💰 Budget guida per reparto")
    bc1,bc2,bc3,bc4=st.columns(4)
    bp={}
    for col,r in zip((bc1,bc2,bc3,bc4),["POR","DIF","CEN","ATT"]):
        bp[r]=col.number_input(r,min_value=0,max_value=BUDGET,value=int(S["plan_budget"].get(r,0)),
                               step=5,key=f"plan_budget_{r}")
    total_plan=sum(int(x) for x in bp.values())
    if total_plan==BUDGET:
        st.success(f"✅ Budget piano: {total_plan}/1000")
    else:
        st.warning(f"⚠️ Budget piano: {total_plan}/1000 • differenza {BUDGET-total_plan:+d}")
    if st.button("💾 SALVA BUDGET",use_container_width=True):
        S["plan_budget"]={r:int(bp[r]) for r in bp}
        persist();st.success("Budget salvato nel Cloud")

    st.divider()
    cplan1,cplan2=st.columns(2)
    with cplan1:
        if st.button("⚡ CARICA PIANO FC JIGEN",type="primary",use_container_width=True):
            rec=recommended_targets()
            # Merge intelligente: aggiunge i mancanti e corregge solo i campi zero/vuoti.
            for k,v in rec.items():
                if k not in S["targets"]:
                    S["targets"][k]=v
                else:
                    cur=target_defaults(S["targets"][k])
                    if int(cur.get("ideal",0) or 0)<=0: cur["ideal"]=int(v["ideal"])
                    if int(cur.get("max",0) or 0)<=0: cur["max"]=int(v["max"])
                    if not cur.get("alternatives"): cur["alternatives"]=v.get("alternatives","")
                    if not cur.get("notes"): cur["notes"]=v.get("notes","")
                    if not cur.get("team"): cur["team"]=v.get("team","")
                    cur["fvm"]=int(v.get("fvm",cur.get("fvm",0)))
            persist();st.rerun()
    with cplan2:
        st.metric("Target attivi",sum(1 for x in S["targets"].values() if x.get("status","ATTIVO")=="ATTIVO"))

    st.caption("Il piano preimpostato è una base strategica: puoi cambiare prezzi e priorità in qualsiasi momento.")

    st.markdown("#### 🚨 Ultimo minuto mercato")
    st.caption("Se arriva un giocatore nuovo e non è ancora nel listone, aggiungilo qui dall’iPhone: entra subito in LIVE/MASTER/Piano e viene salvato nel Cloud.")
    with st.expander("➕ AGGIUNGI NUOVO ARRIVO", expanded=False):
        nm=st.text_input("Nome listone",placeholder="Es. Nuovo Cognome",key="new_player_name")
        cc1,cc2=st.columns(2)
        nr=cc1.selectbox("Ruolo",["POR","DIF","CEN","ATT"],key="new_player_role")
        nt=cc2.text_input("Squadra",placeholder="Es. Inter",key="new_player_team")
        cc3,cc4=st.columns(2)
        nq=cc3.number_input("Quotazione",min_value=1,max_value=60,value=1,step=1,key="new_player_qta")
        nf=cc4.number_input("FVM / 1000",min_value=1,max_value=600,value=25,step=1,key="new_player_fvm")
        if st.button("✅ AGGIUNGI AL LISTONE",use_container_width=True,key="add_deadline_player"):
            name=str(nm).strip()
            if not name:
                st.error("Inserisci il nome.")
            else:
                k=f"{nr}|{name}"
                if k in set(all_players()["key"]):
                    st.warning("Questo giocatore è già presente nel listone.")
                else:
                    S["custom_players"].append({
                        "name":name,"role":nr,"team":str(nt).strip(),
                        "qta":int(nq),"fvm":int(nf),"created_at":datetime.now().isoformat(timespec="seconds")
                    })
                    persist()
                    st.success(f"✅ {name} aggiunto e salvato nel Cloud")
                    st.rerun()

    if S.get("custom_players"):
        st.markdown("**Nuovi arrivi aggiunti manualmente**")
        cdf=pd.DataFrame(S["custom_players"]).rename(columns={
            "name":"Nome","role":"Ruolo","team":"Squadra","qta":"Qt.A","fvm":"FVM","created_at":"Inserito"
        })
        cdf["Elimina"]=False
        edited_custom=st.data_editor(
            cdf,hide_index=True,use_container_width=True,
            disabled=["Nome","Ruolo","Squadra","Qt.A","FVM","Inserito"],
            column_order=["Nome","Ruolo","Squadra","Qt.A","FVM","Elimina"],
            column_config={"Elimina":st.column_config.CheckboxColumn("Elimina")},
            key="deadline_editor"
        )
        if st.button("🗑️ SALVA ELIMINAZIONI",use_container_width=True,key="delete_deadline_players"):
            to_delete=set()
            for _,rr in edited_custom.iterrows():
                if bool(rr.get("Elimina",False)):
                    to_delete.add((str(rr["Ruolo"]),str(rr["Nome"])))
            if to_delete:
                S["custom_players"]=[
                    x for x in S["custom_players"]
                    if (str(x.get("role","")),str(x.get("name",""))) not in to_delete
                ]
                persist();st.rerun()

    st.markdown("#### ➕ Aggiungi / aggiorna target")
    q2=st.text_input("🔎 Cerca giocatore",placeholder="Es. Lautaro, Nico Paz, Dimarco",key="targetsearch")
    ap=all_players(); pool=ap[~ap.key.isin(set(S["out"]))].copy()
    if q2:
        pool=pool[smart_player_mask(pool,q2)]
    pool=pool.sort_values(["FVM","Nome"],ascending=[False,True]).head(100)
    opts=[f"{r.Nome} • {r.Ruolo} • {r.Squadra} • FVM {r.FVM}" for _,r in pool.iterrows()]
    t=st.selectbox("Giocatore",opts,index=None,placeholder="Tocca qui per scegliere...",key="targetpick")
    tc1,tc2,tc3=st.columns(3)
    fascia=tc1.selectbox("Priorità",["A","B","C"],key="targetprio")
    ideal=tc2.number_input("Prezzo ideale",min_value=0,max_value=BUDGET,value=0,step=1,key="targetideal")
    maxp=tc3.number_input("STOP massimo",min_value=0,max_value=BUDGET,value=0,step=1,key="targetmax")
    alternatives=st.text_input("Alternative immediate",placeholder="Es. McTominay / Calhanoglu",key="targetalt")
    notes=st.text_input("Nota",placeholder="Es. non superare lo STOP",key="targetnote")
    if t and st.button("➕ SALVA TARGET",use_container_width=True):
        name=t.split(" • ")[0]
        rr=pool[pool.Nome==name].iloc[0]
        auto=auto_target_prices(rr)
        S["targets"][rr.key]={
            "name":rr.Nome,"role":rr.Ruolo,"team":rr.Squadra,"fvm":int(rr.FVM),
            "priority":fascia,
            "ideal":int(ideal) if int(ideal)>0 else int(auto["ideal"]),
            "max":int(maxp) if int(maxp)>0 else int(auto["max"]),
            "alternatives":alternatives,"notes":notes,"status":"ATTIVO"
        }
        persist();st.rerun()

    if S["targets"]:
        st.markdown("#### ✏️ Modifica target")
        records=[]
        for k,v in S["targets"].items():
            v=target_defaults(v)
            if f'{v.get("role","")}|{v.get("name","")}' in set(S["out"]):
                stato="USCITO"
            else:
                stato=v.get("status","ATTIVO")
            records.append({
                "_key":k,
                "Nome":v.get("name",""),"Ruolo":v.get("role",""),"Squadra":v.get("team",""),
                "FVM":int(v.get("fvm",0) or 0),"Priorità":v.get("priority","C"),
                "Ideale":int(v.get("ideal",0) or 0),"STOP":int(v.get("max",0) or 0),
                "Alternative":v.get("alternatives",""),"Note":v.get("notes",""),
                "Stato":stato,"Elimina":False
            })
        tdf=pd.DataFrame(records)
        order={"A":0,"B":1,"C":2}
        tdf["_ord"]=tdf["Priorità"].map(order).fillna(9)
        tdf=tdf.sort_values(["Ruolo","_ord","FVM"],ascending=[True,True,False]).drop(columns=["_ord"]).reset_index(drop=True)

        edited=st.data_editor(
            tdf,
            hide_index=True,
            use_container_width=True,
            height=520,
            disabled=["_key","Nome","Ruolo","Squadra","FVM"],
            column_order=["Nome","Ruolo","Priorità","Ideale","STOP","Alternative","Note","Stato","Elimina"],
            column_config={
                "Priorità":st.column_config.SelectboxColumn("Priorità",options=["A","B","C"],required=True),
                "Ideale":st.column_config.NumberColumn("Ideale",min_value=0,max_value=BUDGET,step=1),
                "STOP":st.column_config.NumberColumn("STOP",min_value=0,max_value=BUDGET,step=1),
                "Stato":st.column_config.SelectboxColumn("Stato",options=["ATTIVO","PAUSA","USCITO"],required=True),
                "Elimina":st.column_config.CheckboxColumn("Elimina")
            },
            key="targets_editor"
        )
        if st.button("💾 SALVA MODIFICHE TARGET",type="primary",use_container_width=True):
            new_targets={}
            for _,rr in edited.iterrows():
                if bool(rr.get("Elimina",False)):
                    continue
                k=str(rr["_key"])
                old=S["targets"].get(k,{})
                new_targets[k]={
                    "name":old.get("name",rr["Nome"]),"role":old.get("role",rr["Ruolo"]),
                    "team":old.get("team",rr.get("Squadra","")),"fvm":int(old.get("fvm",rr.get("FVM",0)) or 0),
                    "priority":str(rr["Priorità"]),"ideal":int(rr["Ideale"] or 0),"max":int(rr["STOP"] or 0),
                    "alternatives":str(rr.get("Alternative","") or ""),"notes":str(rr.get("Note","") or ""),
                    "status":str(rr.get("Stato","ATTIVO"))
                }
            S["targets"]=new_targets
            persist();st.rerun()

        # Vista rapida da asta: solo target ancora disponibili e attivi
        active=[]
        out_set=set(S["out"])
        for v in S["targets"].values():
            if v.get("status","ATTIVO")!="ATTIVO":
                continue
            if f'{v.get("role","")}|{v.get("name","")}' in out_set:
                continue
            active.append({
                "Nome":v.get("name"),"R":v.get("role"),"P":v.get("priority","C"),
                "FVM":v.get("fvm",0),"Ideale":v.get("ideal",0),"STOP":v.get("max",0),
                "Alternative":v.get("alternatives","")
            })
        if active:
            adf=pd.DataFrame(active)
            adf["_ord"]=adf["P"].map({"A":0,"B":1,"C":2}).fillna(9)
            st.markdown("#### 🚦 Vista rapida asta")
            st.dataframe(adf.sort_values(["R","_ord","FVM"],ascending=[True,True,False]).drop(columns=["_ord"]),
                         hide_index=True,use_container_width=True)
    else:
        st.info("Nessun target. Premi “CARICA PIANO FC JIGEN” oppure aggiungili manualmente.")

with tabs[6]:
    st.subheader("📈 Storico")
    if S["moves"]:
        h=pd.DataFrame(S["moves"])
        st.dataframe(h.iloc[::-1],hide_index=True,use_container_width=True)
        st.download_button("⬇️ Storico CSV",h.to_csv(index=False).encode(),file_name="storico_asta.csv",mime="text/csv")
        st.caption(f"{len(h)} operazioni • indice mercato {market_index():.2f}x")
    else:st.info("Storico vuoto.")