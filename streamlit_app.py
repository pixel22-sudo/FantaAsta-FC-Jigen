# VERSIONE v3.35.3 FANTAMOSSA - AUTO LINEUP PERCENTAGES
# FC Jigen - file corretto per GitHub

import re
import html
import time
import streamlit as st
from io import BytesIO
import base64
import pandas as pd
import json, statistics, hashlib
import unicodedata
import xml.etree.ElementTree as ET
import html as html_lib
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

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
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError


# --- FantaMossa Beta branding ---
FANTAMOSSA_ICON_B64 = """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"""
FANTAMOSSA_ICON = BytesIO(base64.b64decode(FANTAMOSSA_ICON_B64))

st.set_page_config(page_title="FantaMossa", page_icon=FANTAMOSSA_ICON, layout="wide")

st.markdown(f"""
<link rel="apple-touch-icon" sizes="96x96" href="data:image/png;base64,{FANTAMOSSA_ICON_B64}">
<meta name="apple-mobile-web-app-title" content="FantaMossa">
<meta name="apple-mobile-web-app-capable" content="yes">
""", unsafe_allow_html=True)


EXCEL = Path(__file__).parent / "Quotazioni_Fantacalcio_Stagione_2026_27.xlsx"
BUDGET = 1000
SLOTS = {"POR": 3, "DIF": 8, "CEN": 8, "ATT": 6}
ROLE_BUDGET = {"POR": .04, "DIF": .16, "CEN": .25, "ATT": .55}
ROLE_MAP = {"P":"POR","D":"DIF","C":"CEN","A":"ATT"}
RIVALS = ["Red Demon","CHIAVARIELLO FC","La Seleção","LAS Capocchias",
          "VERO TONY VERO SOSA","Joga Benito","vale lambo","Los zuccherinhos","ARIANAPOLI"]
INTEL_SNAPSHOT = "02/09/2026 • post-asta verificato"

@st.cache_data(show_spinner=False)
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

    # Il file Excel aggiornato è la fonte autoritativa per squadra/ruolo/FVM.
    return df

PLAYERS = load_players()

CLOUD_ID = "fc-jigen-main"

def _cloud_config():
    try:
        url = str(st.secrets.get("SUPABASE_URL", "")).strip()
        key = str(st.secrets.get("SUPABASE_KEY", "")).strip()
        if not url or not key:
            cfg = st.secrets.get("supabase", {})
            url = str(cfg.get("url", "")).strip()
            key = str(cfg.get("key", "")).strip()
        return url, key
    except Exception:
        return "", ""

def cloud_config_status():
    url, key = _cloud_config()
    return bool(url and key)

def _cloud_request(method, query="", payload=None):
    """REST Supabase fail-fast: massimo 3.5s, nessun retry nascosto dell'SDK."""
    url, key = _cloud_config()
    if not url or not key:
        raise RuntimeError("Configurazione Supabase assente")
    endpoint = f"{url.rstrip('/')}/rest/v1/fanta_auction_state"
    if query:
        endpoint += "?" + query
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "FantaMossa/3.31",
    }
    if method == "PATCH":
        headers["Prefer"] = "return=representation"
    req = Request(endpoint, data=body, headers=headers, method=method)
    with urlopen(req, timeout=3.5) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else None

def cloud_load():
    try:
        query = urlencode({"select":"state", "id":f"eq.{CLOUD_ID}"})
        data = _cloud_request("GET", query=query)
        st.session_state["_cloud_read_ok"] = True
        st.session_state.pop("_cloud_error", None)
        if isinstance(data, list) and data:
            state = data[0].get("state")
            if isinstance(state, dict) and state.get("roster") is not None:
                return state
    except Exception as exc:
        st.session_state["_cloud_read_ok"] = False
        st.session_state["_cloud_error"] = f"{type(exc).__name__}: {exc}"
    return None

def cloud_save(state):
    try:
        payload = {"state": state, "updated_at": datetime.now().isoformat()}
        query = urlencode({"id":f"eq.{CLOUD_ID}"})
        data = _cloud_request("PATCH", query=query, payload=payload)
        ok = isinstance(data, list) and len(data) > 0
        if ok:
            st.session_state.pop("_cloud_error", None)
            st.session_state["_cloud_last_save"] = datetime.now().strftime("%H:%M:%S")
        else:
            st.session_state["_cloud_error"] = "Nessuna riga aggiornata dal Cloud"
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
    st.session_state["_cloud_notice"] = "✅ Cloud salvato correttamente" if ok else "❌ Salvataggio cloud fallito"

@st.cache_data(show_spinner=False)
def load_valuations():
    """Valutazioni post-asta dal foglio Valutazioni; fallback vuoto se manca."""
    try:
        vf = pd.read_excel(EXCEL, sheet_name="Valutazioni")
        vf["Nome"] = vf["Nome"].astype(str).str.strip()
        return vf
    except Exception:
        return pd.DataFrame()

VALUATIONS = load_valuations()
VALUATION_BY_NAME = (
    {str(r["Nome"]): r.to_dict() for _, r in VALUATIONS.iterrows()}
    if not VALUATIONS.empty and "Nome" in VALUATIONS.columns else {}
)


@st.cache_data(show_spinner=False)
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


PLAYER_INTEL = {
    "Lucca": {
        "verdict":"🔴 RISCHIOSO",
        "titolarita":"BASSA",
        "risk":"ALTO",
        "summary":"Parte nettamente dietro nelle gerarchie del Napoli. Højlund è il riferimento principale: Lucca va considerato soprattutto come arma a gara in corso.",
        "auction":"Solo a prezzo molto basso. Non pagarlo come titolare.",
        "ideal":2,"stop":5,"tag":"SCOMMESSA DA 1-5"
    },
    "Stankovic F.": {
        "verdict":"🟢 INTERESSANTE",
        "titolarita":"ALTA",
        "risk":"MEDIO",
        "summary":"Portiere titolare e low cost: può essere una buona alternativa, soprattutto se vuoi spendere poco e sfruttare il modificatore.",
        "auction":"Buona scommessa da alternare in base al calendario.",
        "ideal":4,"stop":8,"tag":"SCOMMESSA FORTE"
    },
    "Calvani": {
        "verdict":"🟢 INTERESSANTE",
        "titolarita":"ALTA",
        "risk":"MEDIO",
        "summary":"Profilo da copertura low cost con buone chance di andare spesso a voto.",
        "auction":"Ottimo ultimo slot se resta economico.",
        "ideal":2,"stop":5,"tag":"SCOMMESSA FORTE"
    },
    "Bracaglia": {
        "verdict":"🟡 SOLO AL PREZZO GIUSTO",
        "titolarita":"MEDIO-ALTA",
        "risk":"MEDIO",
        "summary":"Può portare molte presenze a voto, ma il contesto può esporlo a insufficienze e cartellini.",
        "auction":"Copertura economica, senza rilanci aggressivi.",
        "ideal":2,"stop":4,"tag":"SCOMMESSA MEDIA"
    },
    "Bella-Kotchap": {
        "verdict":"🟢 INTERESSANTE",
        "titolarita":"ALTA",
        "risk":"MEDIO",
        "summary":"Difensore low cost con minutaggio interessante e discreta affidabilità.",
        "auction":"Valido come slot di copertura, soprattutto per il modificatore.",
        "ideal":2,"stop":5,"tag":"SCOMMESSA FORTE"
    },
    "Leysen F.": {
        "verdict":"🟢 INTERESSANTE",
        "titolarita":"MEDIA",
        "risk":"MEDIO",
        "summary":"Giovane difensore che può trovare parecchio spazio. Profilo da prezzo basso con margine di crescita.",
        "auction":"Scommessa interessante se rimane sotto costo.",
        "ideal":2,"stop":5,"tag":"SCOMMESSA FORTE"
    },
    "Coulibaly L.": {
        "verdict":"🟢 INTERESSANTE",
        "titolarita":"ALTA",
        "risk":"MEDIO-BASSO",
        "summary":"Centrocampista affidabile per minutaggio e media voto, con qualche possibilità di bonus.",
        "auction":"Buon riempitivo low cost per completare il reparto.",
        "ideal":3,"stop":7,"tag":"SCOMMESSA FORTE"
    },
    "Ilic": {
        "verdict":"🟡 SOLO AL PREZZO GIUSTO",
        "titolarita":"MEDIA",
        "risk":"ALTO",
        "summary":"Può rientrare nelle rotazioni, ma concorrenza e continuità fisica/rendimento sono punti deboli.",
        "auction":"Prendilo solo se resta molto economico.",
        "ideal":1,"stop":3,"tag":"SCOMMESSA DA 1-3"
    },
    "Tourè I.": {
        "verdict":"🟢 INTERESSANTE",
        "titolarita":"MEDIA",
        "risk":"MEDIO",
        "summary":"Profilo economico che può andare spesso a voto, ma con pochi bonus attesi.",
        "auction":"Buona copertura, non da pagare per i bonus.",
        "ideal":2,"stop":5,"tag":"SCOMMESSA MEDIA"
    },
    "Piccoli": {
        "verdict":"🟡 SOLO AL PREZZO GIUSTO",
        "titolarita":"MEDIA",
        "risk":"MEDIO",
        "summary":"Attaccante low cost con senso del gol, ma non parte da inamovibile nelle gerarchie.",
        "auction":"Buon 5°/6° slot se il prezzo resta contenuto.",
        "ideal":5,"stop":10,"tag":"SCOMMESSA FORTE"
    },
    "Vitinha O.": {
        "verdict":"🟡 SOLO AL PREZZO GIUSTO",
        "titolarita":"MEDIA",
        "risk":"MEDIO",
        "summary":"Può incidere anche da subentrato e andare spesso a voto, ma non è un titolare garantito.",
        "auction":"Interessante come ultimo slot offensivo a basso prezzo.",
        "ideal":3,"stop":7,"tag":"SCOMMESSA MEDIA"
    },
}


# Gerarchie aggiornate da probabili formazioni Fantacalcio 2026/27.
# Il blocco integra/sovrascrive le schede base sopra.
PLAYER_INTEL.update({
    # PORTIERI
    "Svilar":{
        "verdict":"🟢 TITOLARE FORTE","titolarita":"ALTA","risk":"BASSO",
        "summary":"È il portiere titolare della Roma. Profilo da prima fascia per continuità e modificatore.",
        "competition":"Gerarchia chiara: parte titolare.",
        "auction":"Puoi investirci, ma senza trasformare il portiere in una guerra di rilanci.",
        "tag":"TITOLARE","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Carnesecchi":{
        "verdict":"🟢 TITOLARE","titolarita":"ALTA","risk":"BASSO",
        "summary":"Parte titolare nell'Atalanta di Sarri.",
        "competition":"Gerarchia favorevole: è indicato nell'undici base.",
        "auction":"Ottima alternativa ai portieri più costosi.",
        "tag":"TITOLARE","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Butez":{
        "verdict":"🟢 TITOLARE","titolarita":"ALTA","risk":"BASSO",
        "summary":"È indicato come portiere titolare del Como.",
        "competition":"Gerarchia chiara nell'undici base.",
        "auction":"Buon profilo qualità/prezzo se i top salgono troppo.",
        "tag":"TITOLARE LOW COST","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Caprile":{
        "verdict":"🟢 TITOLARE","titolarita":"ALTA","risk":"BASSO",
        "summary":"È il portiere indicato nell'undici titolare del Cagliari.",
        "competition":"Gerarchia da numero uno.",
        "auction":"Interessante come scelta economica o in coppia.",
        "tag":"TITOLARE LOW COST","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Falcone":{
        "verdict":"🟢 TITOLARE","titolarita":"ALTA","risk":"BASSO",
        "summary":"È il portiere titolare del Lecce.",
        "competition":"Gerarchia chiara.",
        "auction":"Da considerare soprattutto se vuoi spendere poco nel reparto.",
        "tag":"TITOLARE LOW COST","source":"Fantacalcio • gerarchie 2026/27"
    },

    # DIFENSORI
    "Dimarco":{
        "verdict":"🟢 TOP DIFESA","titolarita":"ALTA","risk":"BASSO",
        "summary":"Titolare sulla fascia sinistra dell'Inter e coinvolto anche sui calci da fermo.",
        "competition":"Parte nell'undici base; alto potenziale bonus.",
        "setpieces":"Calci da fermo Inter: Calhanoglu, Dimarco, Zielinski.",
        "auction":"È un top: segui lo STOP e non farti trascinare oltre.",
        "tag":"TOP + BONUS","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Bremer":{
        "verdict":"🟢 TITOLARE FORTE","titolarita":"ALTA","risk":"BASSO",
        "summary":"È indicato titolare al centro della difesa Juventus.",
        "competition":"Gerarchia molto favorevole.",
        "auction":"Profilo forte da modificatore; pagalo per affidabilità, non per hype.",
        "tag":"MODIFICATORE","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Mancini":{
        "verdict":"🟢 TITOLARE","titolarita":"ALTA","risk":"BASSO",
        "summary":"È titolare nella difesa a tre della Roma.",
        "competition":"Gerarchia stabile nell'undici base.",
        "auction":"Buon difensore da modificatore con possibilità di bonus.",
        "tag":"TITOLARE","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Bastoni":{
        "verdict":"🟢 TITOLARE","titolarita":"ALTA","risk":"BASSO",
        "summary":"È titolare nel terzetto difensivo dell'Inter.",
        "competition":"Gerarchia stabile; la rotazione riguarda maggiormente altri centrali.",
        "auction":"Profilo sicuro per media voto e costruzione.",
        "tag":"MODIFICATORE","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Rrahmani":{
        "verdict":"🟢 TITOLARE","titolarita":"ALTA","risk":"BASSO",
        "summary":"È indicato titolare al centro della difesa Napoli.",
        "competition":"Parte davanti nelle gerarchie.",
        "auction":"Buona base affidabile per completare il reparto.",
        "tag":"TITOLARE","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Cambiaso":{
        "verdict":"🟢 TITOLARE + BONUS","titolarita":"ALTA","risk":"MEDIO-BASSO",
        "summary":"È indicato titolare come terzino sinistro della Juventus e rientra anche tra i tiratori da fermo.",
        "competition":"Parte nell'undici base.",
        "setpieces":"Tra i tiratori da fermo Juventus con Yildiz e Locatelli.",
        "auction":"Interessante per bonus, ma non pagarlo come un centrocampista offensivo.",
        "tag":"BONUS","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Bellanova":{
        "verdict":"🟡 BALLOTTAGGIO","titolarita":"MEDIA","risk":"MEDIO",
        "summary":"Nell'Atalanta parte in concorrenza sulla fascia destra.",
        "competition":"Ballottaggio diretto Zappacosta/Bellanova.",
        "auction":"Buono se il prezzo incorpora il rischio rotazione; evita rilanci da titolare fisso.",
        "tag":"ROTAZIONE","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Buongiorno":{
        "verdict":"🟡 BALLOTTAGGIO","titolarita":"MEDIA","risk":"MEDIO",
        "summary":"Al Napoli non è indicato come titolare certo nella formazione base.",
        "competition":"Ballottaggio Beukema/Buongiorno.",
        "auction":"Valido per media voto, ma il prezzo deve considerare la concorrenza.",
        "tag":"ROTAZIONE","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Pavlovic":{
        "verdict":"🟢 TITOLARE","titolarita":"ALTA","risk":"BASSO",
        "summary":"È indicato titolare nella difesa a tre del Milan.",
        "competition":"Parte nell'undici base.",
        "auction":"Buon profilo da modificatore se rimane a prezzo medio-basso.",
        "tag":"TITOLARE","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Scalvini":{
        "verdict":"🟢 TITOLARE","titolarita":"ALTA","risk":"MEDIO",
        "summary":"È indicato titolare nell'Atalanta di Sarri.",
        "competition":"Parte nell'undici base.",
        "auction":"Scommessa controllata: upside alto, ma considera sempre la tenuta fisica.",
        "tag":"TITOLARE / UPSIDE","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Delprato":{
        "verdict":"🟢 TITOLARE","titolarita":"ALTA","risk":"BASSO",
        "summary":"È indicato titolare nel Parma.",
        "competition":"Parte nell'undici base.",
        "auction":"Ottimo slot low cost per avere voto.",
        "tag":"LOW COST","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Valeri":{
        "verdict":"🟢 TITOLARE + PIAZZATI","titolarita":"ALTA","risk":"BASSO",
        "summary":"È indicato titolare sulla fascia sinistra del Parma.",
        "competition":"Parte nell'undici base.",
        "setpieces":"Terzo rigorista indicato e tra i tiratori da fermo del Parma.",
        "auction":"Low cost interessante grazie anche ai piazzati.",
        "tag":"LOW COST + BONUS","source":"Fantacalcio • gerarchie 2026/27"
    },

    # CENTROCAMPISTI / TREQUARTISTI
    "Paz N.":{
        "verdict":"🟢 TOP CENTROCAMPO","titolarita":"ALTA","risk":"BASSO",
        "summary":"È il trequartista centrale del Como e uno dei principali riferimenti tecnici.",
        "competition":"Titolare nell'undici base.",
        "setpieces":"Tra rigoristi e calci da fermo del Como.",
        "auction":"Top obiettivo: puoi spingere, ma rispettando lo STOP.",
        "tag":"TOP + BONUS","source":"Fantacalcio • gerarchie 2026/27"
    },
    "McTominay":{
        "verdict":"🟢 TOP / TITOLARE","titolarita":"ALTA","risk":"BASSO",
        "summary":"È indicato titolare nella mezzala sinistra del Napoli.",
        "competition":"Gerarchia solida nell'undici base.",
        "auction":"Profilo premium per inserimenti e bonus; non serve inseguirlo oltre lo STOP.",
        "tag":"TOP","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Calhanoglu":{
        "verdict":"🟢 TOP + RIGORI","titolarita":"ALTA","risk":"BASSO",
        "summary":"Titolare nel centrocampo Inter e primo riferimento sui rigori.",
        "competition":"Parte nell'undici base.",
        "setpieces":"Primo rigorista Inter; anche sui calci da fermo.",
        "auction":"Valore elevato per bonus pesanti: puoi investire, ma con limite rigido.",
        "tag":"TOP + RIGORISTA","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Pulisic":{
        "verdict":"🟢 TITOLARE OFFENSIVO","titolarita":"ALTA","risk":"MEDIO-BASSO",
        "summary":"È indicato titolare alle spalle della punta nel Milan.",
        "competition":"Parte nell'undici base.",
        "setpieces":"Tra i rigoristi e i tiratori da fermo del Milan.",
        "auction":"Ottimo se listato centrocampista: occhio solo a non pagarlo come un top assoluto d'attacco.",
        "tag":"BONUS","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Yildiz":{
        "verdict":"🟢 TITOLARE + RIGORI","titolarita":"ALTA","risk":"BASSO",
        "summary":"È indicato titolare sulla trequarti sinistra della Juventus.",
        "competition":"Gerarchia forte nell'undici base.",
        "setpieces":"Secondo rigorista indicato dopo Kolo Muani e tra i tiratori da fermo.",
        "auction":"Upside alto: va pagato da giocatore offensivo importante, non oltre lo STOP.",
        "tag":"BONUS","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Samardzic":{
        "verdict":"🟡 BALLOTTAGGIO CON BONUS","titolarita":"MEDIO-ALTA","risk":"MEDIO",
        "summary":"È nell'undici base Atalanta, ma con concorrenza diretta.",
        "competition":"Ballottaggio Samardzic/Pasalic.",
        "setpieces":"Terzo rigorista indicato e tra i tiratori da fermo.",
        "auction":"Interessante se il prezzo resta sotto quello di un titolare inamovibile.",
        "tag":"BALLOTTAGGIO + BONUS","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Baturina":{
        "verdict":"🟡 BALLOTTAGGIO / UPSIDE","titolarita":"MEDIO-ALTA","risk":"MEDIO",
        "summary":"È nell'undici base del Como sulla trequarti, ma non senza concorrenza.",
        "competition":"Ballottaggio Baturina/Caqueret.",
        "setpieces":"Tra i tiratori da fermo del Como.",
        "auction":"Scommessa interessante se non viene pagato come titolare certo.",
        "tag":"SCOMMESSA FORTE","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Vlasic":{
        "verdict":"🟢 TITOLARE + RIGORI","titolarita":"ALTA","risk":"BASSO",
        "summary":"È titolare sulla trequarti del Torino.",
        "competition":"Parte nell'undici base.",
        "setpieces":"Primo rigorista Torino e tra i tiratori da fermo.",
        "auction":"Profilo molto interessante se resta in fascia media.",
        "tag":"TITOLARE + RIGORISTA","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Gaetano":{
        "verdict":"🟢 TITOLARE","titolarita":"ALTA","risk":"MEDIO-BASSO",
        "summary":"È indicato titolare nel centrocampo dell'Atalanta.",
        "competition":"Parte nell'undici base.",
        "setpieces":"Tra i tiratori da fermo Atalanta.",
        "auction":"Buon rapporto prezzo/potenziale se resta economico.",
        "tag":"VALUE","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Ferguson":{
        "verdict":"🟢 TITOLARE","titolarita":"ALTA","risk":"BASSO",
        "summary":"È indicato titolare nel centrocampo del Bologna.",
        "competition":"Gerarchia favorevole nell'undici base.",
        "auction":"Valore affidabile, soprattutto se il prezzo resta contenuto.",
        "tag":"VALUE","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Mastantuono":{
        "verdict":"🟢 TITOLARE / UPSIDE","titolarita":"ALTA","risk":"MEDIO",
        "summary":"È indicato titolare nel tridente della Fiorentina.",
        "competition":"Parte nell'undici base.",
        "setpieces":"Tra i tiratori da fermo della Fiorentina.",
        "auction":"Scommessa ad alto potenziale: meglio prenderlo prima che il prezzo salga troppo.",
        "tag":"SCOMMESSA FORTE","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Alajbegovic":{
        "verdict":"🟡 BALLOTTAGGIO / UPSIDE","titolarita":"MEDIA","risk":"MEDIO",
        "summary":"È indicato sulla trequarti Juventus, ma la struttura può cambiare con Thuram/McKennie.",
        "competition":"Ballottaggio tattico Alajbegovic/Thuram con possibile avanzamento di McKennie.",
        "auction":"Scommessa pura: bene a prezzo basso, non da pagare come titolare fisso.",
        "tag":"SCOMMESSA","source":"Fantacalcio • gerarchie 2026/27"
    },

    # ATTACCANTI
    "Martinez L.":{
        "verdict":"🟢 TOP ASSOLUTO","titolarita":"ALTISSIMA","risk":"BASSO",
        "summary":"Lautaro è inamovibile nell'attacco Inter e resta un primo slot assoluto.",
        "competition":"Gerarchia chiarissima: titolare accanto a Thuram.",
        "setpieces":"Tra i rigoristi Inter, dietro Calhanoglu e Zielinski nelle gerarchie indicate.",
        "auction":"Puoi costruire l'attacco su di lui, ma STOP rigido per non bruciare il budget.",
        "tag":"TOP ASSOLUTO","source":"Fantacalcio • profilo + gerarchie 2026/27"
    },
    "Malen":{
        "verdict":"🟢 TOP / TITOLARE","titolarita":"ALTA","risk":"BASSO",
        "summary":"È indicato come riferimento offensivo della Roma.",
        "competition":"Titolare al centro dell'attacco; Castro può modificare l'assetto ma Malen resta centrale.",
        "setpieces":"Primo rigorista Roma e tra i tiratori da fermo.",
        "auction":"Profilo da top: forte, ma va rispettato lo STOP.",
        "tag":"TOP + RIGORISTA","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Hojlund":{
        "verdict":"🟢 TITOLARISSIMO","titolarita":"ALTISSIMA","risk":"BASSO",
        "summary":"È il centravanti titolare del Napoli; Fantacalcio lo indica come titolarissimo.",
        "competition":"Parte nettamente davanti nelle gerarchie per il ruolo di centravanti.",
        "setpieces":"Secondo rigorista indicato dopo De Bruyne.",
        "auction":"Secondo slot premium: puoi spingere, ma senza arrivare a prezzo da Lautaro/Malen.",
        "tag":"TITOLARE + RIGORI","source":"Fantacalcio • profilo + gerarchie 2026/27"
    },
    "Thuram":{
        "verdict":"🟢 TITOLARE MA CON CONCORRENZA","titolarita":"MEDIO-ALTA","risk":"MEDIO",
        "summary":"Parte nell'undici base dell'Inter, ma Pio Esposito gli mette pressione.",
        "competition":"Ballottaggio Thuram/Pio Esposito; Lautaro resta il riferimento più stabile.",
        "auction":"Forte secondo slot, ma considera una rotazione superiore rispetto a Lautaro.",
        "tag":"PREMIUM / ROTAZIONE","source":"Fantacalcio • profilo + gerarchie 2026/27"
    },
    "Esposito F.P.":{
        "verdict":"🟡 GRANDE SCOMMESSA","titolarita":"MEDIA","risk":"MEDIO",
        "summary":"Può essere incisivo e avere molto minutaggio, ma parte dietro a Lautaro e Thuram.",
        "competition":"Fantacalcio lo indica dietro Lautaro e Thuram; è però in ballottaggio diretto con Thuram nelle gerarchie.",
        "auction":"Ottimo rapporto qualità/prezzo se non viene pagato come titolare inamovibile.",
        "tag":"SCOMMESSA FORTE","source":"Fantacalcio • profilo + gerarchie 2026/27"
    },
    "Ramos G.":{
        "verdict":"🟢 TITOLARE + RIGORI","titolarita":"ALTA","risk":"BASSO",
        "summary":"È il centravanti indicato nell'undici base del Milan.",
        "competition":"Parte titolare come punta centrale.",
        "setpieces":"Secondo rigorista indicato dopo Nkunku.",
        "auction":"Alternativa forte ai top più costosi.",
        "tag":"PREMIUM + RIGORI","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Kean":{
        "verdict":"🟡 PREMIUM IN BALLOTTAGGIO","titolarita":"MEDIO-ALTA","risk":"MEDIO",
        "summary":"Trasferimento al Como in chiusura dopo visite mediche completate. Il cambio squadra aumenta la concorrenza diretta con Douvikas.",
        "competition":"Kean e Douvikas si giocano molto minutaggio: Fantacalcio segnala un ballottaggio serrato e continuo.",
        "auction":"Resta un attaccante importante, ma non pagarlo come un titolare inamovibile: il prezzo deve incorporare la concorrenza con Douvikas.",
        "tag":"PREMIUM / BALLOTTAGGIO","source":"Deadline Day 01/09 • Fantacalcio + ANSA"
    },
    "Orsolini":{
        "verdict":"🟢 TITOLARE + PRIMO RIGORISTA","titolarita":"ALTA","risk":"BASSO",
        "summary":"È titolare sulla trequarti destra del Bologna.",
        "competition":"Gerarchia forte nell'undici base.",
        "setpieces":"Primo rigorista Bologna e tra i principali tiratori da fermo.",
        "auction":"Se è centrocampista nel tuo listone è un profilo premium per bonus.",
        "tag":"TOP CEN + RIGORISTA","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Scamacca":{
        "verdict":"🟡 TITOLARE IN BALLOTTAGGIO","titolarita":"MEDIO-ALTA","risk":"MEDIO",
        "summary":"Parte come centravanti nell'undici base Atalanta, ma Krstovic è concorrente diretto.",
        "competition":"Ballottaggio Scamacca/Krstovic.",
        "setpieces":"Primo rigorista indicato Atalanta.",
        "auction":"Ottimo se il prezzo resta da terzo slot; evita prezzo da titolare inamovibile.",
        "tag":"BALLOTTAGGIO + RIGORI","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Douvikas":{
        "verdict":"🟡 TITOLARE IN BALLOTTAGGIO","titolarita":"MEDIO-ALTA","risk":"MEDIO",
        "summary":"Ha iniziato forte ed è centrale nel Como, ma l'arrivo di Kean cambia la gerarchia offensiva.",
        "competition":"Ballottaggio serrato e continuo con Kean; possibile alternanza anche per gli impegni europei.",
        "setpieces":"Resta un profilo interessante anche in area di rigore.",
        "auction":"Non pagarlo più come titolare fisso: resta appetibile, ma con STOP più prudente.",
        "tag":"VALUE / BALLOTTAGGIO","source":"Deadline Day 01/09 • Fantacalcio"
    },
    "Krstovic":{
        "verdict":"🟡 BALLOTTAGGIO","titolarita":"MEDIA","risk":"MEDIO",
        "summary":"È in concorrenza diretta con Scamacca per il posto da centravanti Atalanta.",
        "competition":"Ballottaggio Scamacca/Krstovic.",
        "setpieces":"Secondo rigorista indicato Atalanta.",
        "auction":"Prendilo solo se il prezzo compensa il rischio di rotazione.",
        "tag":"SCOMMESSA + RIGORI","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Berardi":{
        "verdict":"🟢 TITOLARE + RIGORI","titolarita":"ALTA","risk":"BASSO",
        "summary":"È titolare sulla fascia destra del Sassuolo e resta il riferimento tecnico.",
        "competition":"Gerarchia forte nell'undici base.",
        "setpieces":"Primo rigorista e primo riferimento sui calci da fermo.",
        "auction":"Molto interessante se sottoprezzato rispetto al suo potenziale bonus.",
        "tag":"BONUS + RIGORISTA","source":"Fantacalcio • gerarchie 2026/27"
    },
    "De Ketelaere":{
        "verdict":"🟢 TITOLARE OFFENSIVO","titolarita":"ALTA","risk":"BASSO",
        "summary":"È indicato titolare nel tridente dell'Atalanta.",
        "competition":"Parte nell'undici base.",
        "setpieces":"Tra i tiratori da fermo Atalanta.",
        "auction":"Upside importante: molto buono se il prezzo resta da terzo slot.",
        "tag":"BONUS","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Zaccagni":{
        "verdict":"🟢 TITOLARE + RIGORI","titolarita":"ALTA","risk":"BASSO",
        "summary":"È titolare sulla sinistra della Lazio.",
        "competition":"Gerarchia forte nell'undici base.",
        "setpieces":"Primo rigorista Lazio e tra i tiratori da fermo.",
        "auction":"Se listato centrocampista è un profilo molto prezioso per bonus.",
        "tag":"BONUS + RIGORISTA","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Dybala":{
        "verdict":"🟡 TALENTO CON RISCHIO","titolarita":"ALTA","risk":"MEDIO-ALTO",
        "summary":"È indicato titolare sulla trequarti Roma. Il talento resta enorme, ma va considerata la gestione fisica.",
        "competition":"Parte nell'undici base alle spalle di Malen.",
        "setpieces":"Secondo rigorista indicato dopo Malen e tra i tiratori da fermo.",
        "auction":"Prendilo solo se il prezzo incorpora il rischio: non inseguirlo come un top inamovibile.",
        "tag":"BONUS / RISCHIO","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Raspadori":{
        "verdict":"🟢 TITOLARE OFFENSIVO","titolarita":"ALTA","risk":"MEDIO-BASSO",
        "summary":"È indicato titolare nel tridente dell'Atalanta.",
        "competition":"Parte nell'undici base.",
        "auction":"Interessante come ultimo slot di qualità se resta a prezzo contenuto.",
        "tag":"VALUE","source":"Fantacalcio • gerarchie 2026/27"
    },

    # SCOMMESSE / GERARCHIE DELICATE
    "Lucca":{
        "verdict":"🔴 GERARCHIA SFAVOREVOLE","titolarita":"BASSA","risk":"ALTO",
        "summary":"Non è indicato nell'undici base del Napoli: Højlund è il centravanti titolare e Fantacalcio lo definisce titolarissimo.",
        "competition":"Davanti nelle gerarchie c'è Højlund; Lucca va considerato soprattutto come alternativa.",
        "auction":"Solo a prezzo molto basso. Non pagarlo come titolare.",
        "ideal":2,"stop":5,"tag":"SCOMMESSA DA 1-5","source":"Fantacalcio • profilo Højlund + gerarchie 2026/27"
    },
    "Stankovic F.":{
        "verdict":"🟢 TITOLARE LOW COST","titolarita":"ALTA","risk":"MEDIO",
        "summary":"È indicato titolare del Venezia.",
        "competition":"Gerarchia da numero uno.",
        "auction":"Buona scommessa economica, soprattutto in una strategia portieri low cost.",
        "ideal":4,"stop":8,"tag":"SCOMMESSA FORTE","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Calvani":{
        "verdict":"🟡 BALLOTTAGGIO LOW COST","titolarita":"MEDIO-ALTA","risk":"MEDIO",
        "summary":"È nell'undici base del Frosinone, ma con concorrenza.",
        "competition":"Ballottaggio Calvani/Akpoguma.",
        "auction":"Va bene come ultimo slot, purché resti molto economico.",
        "ideal":2,"stop":5,"tag":"SCOMMESSA FORTE","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Bracaglia":{
        "verdict":"🟢 TITOLARE LOW COST","titolarita":"ALTA","risk":"MEDIO",
        "summary":"È indicato titolare nella difesa del Frosinone.",
        "competition":"Parte nell'undici base.",
        "auction":"Copertura economica: niente rilanci aggressivi.",
        "ideal":2,"stop":4,"tag":"SCOMMESSA MEDIA","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Bella-Kotchap":{
        "verdict":"🟢 TITOLARE LOW COST","titolarita":"ALTA","risk":"MEDIO",
        "summary":"È indicato titolare al centro della difesa del Venezia.",
        "competition":"Parte nell'undici base.",
        "auction":"Valido come slot di copertura a basso costo.",
        "ideal":2,"stop":5,"tag":"SCOMMESSA FORTE","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Coulibaly L.":{
        "verdict":"🟢 TITOLARE LOW COST","titolarita":"ALTA","risk":"MEDIO-BASSO",
        "summary":"È indicato titolare nel centrocampo del Lecce.",
        "competition":"Parte nell'undici base.",
        "auction":"Buon riempitivo per avere voto spendendo poco.",
        "ideal":3,"stop":7,"tag":"SCOMMESSA FORTE","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Tourè I.":{
        "verdict":"🟢 TITOLARE + RIGORI","titolarita":"ALTA","risk":"MEDIO",
        "summary":"È indicato titolare nel tridente del Parma.",
        "competition":"Parte nell'undici base.",
        "setpieces":"Secondo rigorista indicato dopo Pellegrino.",
        "auction":"Scommessa molto interessante se resta sotto costo.",
        "ideal":2,"stop":5,"tag":"SCOMMESSA FORTE","source":"Fantacalcio • gerarchie 2026/27"
    },
    "Vitinha O.":{
        "verdict":"🟡 TITOLARE IN BALLOTTAGGIO","titolarita":"MEDIO-ALTA","risk":"MEDIO",
        "summary":"È nell'undici base del Genoa sulla trequarti.",
        "competition":"Ballottaggio Vitinha/Meichtry.",
        "setpieces":"Tra rigoristi e tiratori da fermo del Genoa.",
        "auction":"Interessante a prezzo contenuto grazie anche ai piazzati.",
        "ideal":3,"stop":7,"tag":"SCOMMESSA FORTE","source":"Fantacalcio • gerarchie 2026/27"
    },


    "Hutchinson":{
        "verdict":"🎲 SCOMMESSA INTERESSANTE","titolarita":"MEDIA","risk":"MEDIO",
        "summary":"Nuovo arrivo ufficiale al Milan. Esterno offensivo mancino, listato centrocampista al Classic.",
        "competition":"Avrà concorrenza sulla trequarti, ma è stato richiesto espressamente e avrà occasioni.",
        "auction":"Interessante a pochi crediti: il valore è soprattutto nel ruolo CEN e nel potenziale offensivo.",
        "ideal":3,"stop":7,"tag":"SCOMMESSA CEN","source":"Fantacalcio • ufficiale Milan 31/08"
    },

    "Meret":{
        "verdict":"🟡 TITOLARE CON CONCORRENZA",
        "titolarita":"MEDIO-ALTA",
        "risk":"MEDIO",
        "summary":"È in vantaggio nelle gerarchie del Napoli, ma la concorrenza di Milinkovic-Savic resta concreta.",
        "competition":"Meret parte avanti, ma Milinkovic-Savic può trovare spazio e rende meno sicura la gestione rispetto a un portiere inamovibile.",
        "auction":"Buon portiere se non viene pagato come un top assoluto. Meglio considerare anche la copertura della porta Napoli.",
        "tag":"TITOLARE / CONCORRENZA",
        "source":"Fantacalcio • profilo Meret 2026/27"
    },
})

def player_intel(row):
    """Giudizio serio: slot/rank quantitativi; titolarità separata e mai inventata."""
    name = str(row.Nome)
    val = VALUATION_BY_NAME.get(name, {})
    tit = str(val.get("Titolarita", "DA VERIFICARE") or "DA VERIFICARE").upper()
    ger = str(val.get("Gerarchia", "NON INFERITA") or "NON INFERITA")
    aff = str(val.get("Affidabilita", "ALGORITMICA") or "ALGORITMICA").upper()
    note = str(val.get("Giudizio", "") or "")
    slot = str(val.get("SlotLega10", "") or "")
    rank = val.get("RankRuolo", "")
    total = val.get("TotRuolo", "")
    if aff == "VERIFICATA":
        if tit == "ALTA":
            verdict, risk = "🟢 GERARCHIA FORTE", "BASSO"
        elif "MEDIO" in tit or tit == "MEDIA":
            verdict, risk = "🟡 GERARCHIA DA GESTIRE", "MEDIO"
        elif tit == "BASSA":
            verdict, risk = "🟠 ROTAZIONE / RISERVA", "MEDIO-ALTO"
        else:
            verdict, risk = "⚪ GERARCHIA VERIFICATA", "MEDIO"
        return {
            "verdict": verdict, "titolarita": tit, "risk": risk, "summary": note,
            "competition": ger if ger and ger != "NON INFERITA" else "",
            "auction": "Valuta il giocatore in base a slot reale, gerarchia e prezzo.",
            "ideal": None, "stop": None, "tag": f"{slot} • DATI VERIFICATI" if slot else "DATI VERIFICATI",
            "source": str(val.get("Fonte", "") or ""), "rank": rank, "total_role": total,
            "slot": slot, "confidence": "VERIFICATA",
        }
    if slot.startswith("1°"):
        verdict = "🟢 FASCIA ALTA DEL RUOLO"
    elif slot.startswith("2°") or slot.startswith("3°"):
        verdict = "🟡 FASCIA MEDIO-ALTA"
    else:
        verdict = "⚪ FASCIA DI COMPLETAMENTO"
    return {
        "verdict": verdict, "titolarita": "DA VERIFICARE", "risk": "MEDIO",
        "summary": note or "Valutazione quantitativa sul listone: la titolarità non viene dedotta dal solo FVM.",
        "auction": "Non confondere lo slot fantacalcistico con la titolarità reale.",
        "ideal": None, "stop": None, "tag": f"{slot} • ALGORITMICO" if slot else "ALGORITMICO",
        "source": "", "rank": rank, "total_role": total, "slot": slot, "confidence": "ALGORITMICA",
    }


def auction_signal(row, current_price, plan, info):
    try:
        price = int(current_price or 0)
    except Exception:
        price = 0

    ideal = int(plan.get("ideal", 1) or 1)
    stop = int(plan.get("max", ideal) or ideal)

    if info.get("ideal") not in (None, ""):
        ideal = int(info.get("ideal"))
    if info.get("stop") not in (None, ""):
        stop = int(info.get("stop"))

    remaining = int(S.get("credits", 1000) or 0)
    role = str(row.Ruolo)
    role_max = {"POR":3, "DIF":8, "CEN":8, "ATT":6}.get(role, 0)
    owned_role = sum(1 for x in S.get("roster", []) if x.get("role") == role)
    role_left = max(0, role_max - owned_role)

    total_left = max(0, 25 - len(S.get("roster", [])))
    min_reserve = max(0, total_left - 1)
    max_affordable = max(0, remaining - min_reserve)

    risk = str(info.get("risk","MEDIO")).upper()
    title = str(info.get("titolarita","DA VALUTARE")).upper()

    effective_stop = stop
    if "ALTO" in risk or "BASSA" in title:
        effective_stop = min(stop, max(1, int(round(stop * 0.85))))

    if role_left <= 0:
        return {"label":"🔴 LASCIA","reason":f"Reparto {role} già completo.",
                "ideal":ideal,"stop":stop,"effective_stop":effective_stop,"max_affordable":max_affordable}

    if price > max_affordable:
        return {"label":"🔴 LASCIA",
                "reason":f"A questo prezzo rischi di non completare la rosa. Massimo sostenibile ora: {max_affordable}.",
                "ideal":ideal,"stop":stop,"effective_stop":effective_stop,"max_affordable":max_affordable}

    if price <= ideal:
        return {"label":"🟢 PRENDI","reason":f"Prezzo dentro l'IDEALE ({ideal}).",
                "ideal":ideal,"stop":stop,"effective_stop":effective_stop,"max_affordable":max_affordable}

    if price <= effective_stop:
        extra = f" STOP operativo ridotto da {stop} a {effective_stop} per rischio/titolarità." if effective_stop < stop else ""
        return {"label":"🟡 VALUTA",
                "reason":f"Sopra l'IDEALE ({ideal}) ma ancora dentro il limite operativo ({effective_stop}).{extra}",
                "ideal":ideal,"stop":stop,"effective_stop":effective_stop,"max_affordable":max_affordable}

    return {"label":"🔴 LASCIA","reason":f"Prezzo oltre lo STOP operativo ({effective_stop}). Non inseguire.",
            "ideal":ideal,"stop":stop,"effective_stop":effective_stop,"max_affordable":max_affordable}



def slot_priority_advice(row, info):
    role = str(row.Ruolo)
    name = str(row.Nome)
    val = VALUATION_BY_NAME.get(name, {})
    slot = str(val.get("SlotLega10", "") or info.get("slot", "") or "")
    rank = val.get("RankRuolo", info.get("rank", ""))
    total = val.get("TotRuolo", info.get("total_role", ""))
    if not slot:
        ap = all_players()
        same = ap[ap.Ruolo.eq(role)].sort_values(["FVM","QtA","Nome"], ascending=[False,False,True])
        names = same["Nome"].astype(str).tolist()
        try: rank = names.index(name) + 1
        except ValueError: rank = len(names)
        slot_num = min(SLOTS.get(role, 1), max(1, (int(rank)-1)//10 + 1))
        slot = f"{slot_num}° PORTIERE" if role == "POR" else f"{slot_num}° SLOT"
        total = len(names)
    title = str(info.get("titolarita","DA VERIFICARE")).upper()
    risk = str(info.get("risk","MEDIO")).upper()
    mm = re.match(r"(\d+)", slot)
    slot_num = int(mm.group(1)) if mm else SLOTS.get(role, 1)
    if slot_num <= 2 and "BASSA" not in title: priority = "🔥 ALTA"
    elif slot_num <= 4: priority = "🟡 MEDIA"
    else: priority = "⚪ BASSA"
    if "ALTO" in risk or title == "BASSA": priority = "⚪ BASSA"
    role_max = SLOTS.get(role, 0)
    owned_role = sum(1 for x in S.get("roster", []) if x.get("role") == role)
    role_left = max(0, role_max - owned_role)
    return {"slot": slot, "priority": priority, "role_left": role_left, "rank": rank, "total": total}


def render_player_intel(row):
    info=player_intel(row)
    verdict=info.get("verdict","")
    if verdict.startswith("🔴"):
        st.error(verdict)
    elif verdict.startswith("🟢"):
        st.success(verdict)
    else:
        st.warning(verdict)
    st.markdown(
        f"**Titolarità:** {info.get('titolarita','—')}  •  "
        f"**Rischio:** {info.get('risk','—')}  •  "
        f"**Tipo:** {info.get('tag','—')}"
    )
    slot_info = slot_priority_advice(row, info)
    st.markdown(
        f"**🎟️ Slot:** {slot_info['slot']}  •  "
        f"**📊 Rank ruolo:** #{slot_info.get('rank','—')}/{slot_info.get('total','—')}  •  "
        f"**⚡ Priorità:** {slot_info['priority']}"
    )
    st.caption(
        f"Affidabilità giudizio: {info.get('confidence','ALGORITMICA')} • "
        "Slot = posizione nel listone della lega a 10; titolarità = dato separato."
    )
    st.caption(info.get("summary",""))
    if info.get("competition"):
        st.markdown("**⚔️ Concorrenza:** "+info.get("competition",""))
    if info.get("setpieces"):
        st.markdown("**🎯 Rigori / piazzati:** "+info.get("setpieces",""))
    st.info("🎯 Asta: "+info.get("auction",""))
    if info.get("source"):
        st.caption("📌 "+info.get("source",""))
    st.caption("🕒 Dati/gerarchie: "+INTEL_SNAPSHOT)

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


_DISPLAY_ALIAS_BY_OFFICIAL = {
    "Martinez L.": "Lautaro",
    "Paz N.": "Nico Paz",
    "Ramos G.": "Gonçalo Ramos",
    "Esposito F.P.": "Pio Esposito",
}

def player_fast_label(row):
    """Etichetta veloce O(1): niente scansione di tutti gli alias a ogni rerun."""
    official = str(row.Nome)
    pretty = _DISPLAY_ALIAS_BY_OFFICIAL.get(official, "")
    alias_txt = f" / {pretty}" if pretty and pretty.lower() not in official.lower() else ""
    return f"{official}{alias_txt} • {row.Ruolo} • {row.Squadra} • FVM {int(row.FVM)}"

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



# v3.21.3 — Branding iPhone / Aggiungi a Home
# Safari usa il titolo pagina per il nome proposto. L'icona FM resta incorporata e leggera.
st.markdown(f"""
<link rel="apple-touch-icon" href="data:image/png;base64,{FANTAMOSSA_ICON_B64}">
<link rel="apple-touch-icon-precomposed" href="data:image/png;base64,{FANTAMOSSA_ICON_B64}">
<meta name="apple-mobile-web-app-title" content="FantaMossa">
<meta name="application-name" content="FantaMossa">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
""", unsafe_allow_html=True)

normalize()
if not st.session_state.get("_targets_repair_done", False):
    _repaired_targets = repair_saved_targets()
    st.session_state["_targets_repair_done"] = True
    if _repaired_targets:
        st.session_state["_prices_repaired"] = _repaired_targets

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

def prediction_confidence(role):
    """Affidabilità della stima: cresce con i prezzi realmente osservati nell'asta."""
    role_n = len(market_samples(role))
    all_n = len(market_samples())
    if role_n >= 8 or (role_n >= 5 and all_n >= 18):
        return "🟢 ALTA", role_n
    if role_n >= 3 or all_n >= 8:
        return "🟡 MEDIA", role_n
    return "⚪ BASSA", role_n
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
    """Compatibilità legacy: usa lo stesso unico Semaforo mostrato in LIVE."""
    plan = effective_target_plan(row)
    return auction_signal(row, p, plan, player_intel(row))["label"]
def plan_b(row,n=3):
    ap=all_players(); df=ap[(ap.Ruolo==row.Ruolo)&(~ap.key.isin(set(S["out"])))&(ap.key!=row.key)].copy()
    df["delta"]=(df.FVM-row.FVM).abs()
    return df.sort_values(["delta","FVM"],ascending=[True,False]).head(n)

# --- v3.15 FantaMossa: decision support -------------------------------------------------

def mossa_decision_score(row, offered_price=0):
    """Punteggio 0-100 personalizzato sullo stato reale dell'asta. Non modifica lo stato."""
    role = str(row.Ruolo)
    if role not in SLOTS or role_count(role) >= SLOTS[role]:
        return 0

    info = player_intel(row)
    plan = effective_target_plan(row)

    base_fit = fit(row)
    urg = urgency(role)
    scarce = scarcity(role)

    priority = str(plan.get("priority", "C")).upper()
    priority_bonus = {"A": 14, "B": 9, "C": 4}.get(priority, 3)

    title = str(info.get("titolarita", "")).upper()
    risk = str(info.get("risk", "MEDIO")).upper()
    profile_adj = 0
    if "ALT" in title or "TITOLARISSIMO" in title:
        profile_adj += 8
    elif "MEDIA" in title:
        profile_adj += 3
    if "ALTO" in risk:
        profile_adj -= 10
    elif "BASSO" in risk:
        profile_adj += 4

    score = (
        base_fit * 0.48
        + urg * 0.20
        + scarce * 0.10
        + priority_bonus
        + profile_adj
    )

    try:
        price = int(offered_price or 0)
    except Exception:
        price = 0

    if price > 0:
        sig = auction_signal(row, price, plan, info)
        if sig["label"].startswith("🟢"):
            score += 12
        elif sig["label"].startswith("🟡"):
            score += 3
        else:
            score -= 22
        stop_op = max(1, int(sig.get("effective_stop", 1) or 1))
        value_delta = max(-1.0, min(1.0, (stop_op - price) / stop_op))
        score += value_delta * 8

    return max(0, min(100, int(round(score))))


def mossa_recommendations(role_filter="TUTTI", n=5):
    """Classifica i giocatori ancora disponibili in base a rosa, budget, piano e asta reale."""
    ap = all_players()
    available = ap[~ap.key.isin(set(S["out"]))].copy()

    needed_roles = [r for r in SLOTS if role_count(r) < SLOTS[r]]
    available = available[available.Ruolo.isin(needed_roles)]

    if role_filter and role_filter != "TUTTI":
        available = available[available.Ruolo == role_filter]

    rows = []
    for _, row in available.iterrows():
        plan = effective_target_plan(row)
        info = player_intel(row)
        score = mossa_decision_score(row)
        low, high = prediction(row)
        sig0 = auction_signal(row, max(1, int(plan.get("ideal", 1) or 1)), plan, info)

        reason_bits = [
            f"urgenza {urgency(row.Ruolo)}/100",
            f"priorità {plan.get('priority','C')}",
        ]
        if "ALTO" in str(info.get("risk","")).upper():
            reason_bits.append("rischio alto")
        elif "ALT" in str(info.get("titolarita","")).upper():
            reason_bits.append("titolarità alta")

        rows.append({
            "Nome": str(row.Nome),
            "R": str(row.Ruolo),
            "Squadra": str(row.Squadra),
            "FVM": int(row.FVM),
            "Score": int(score),
            "Ideale": int(plan.get("ideal", 1) or 1),
            "STOP": int(sig0.get("effective_stop", plan.get("max", 1)) or 1),
            "Stima": f"{low}-{high}",
            "Perché": " • ".join(reason_bits),
        })

    if not rows:
        return pd.DataFrame(columns=["Nome","R","Squadra","FVM","Score","Ideale","STOP","Stima","Perché"])

    out = pd.DataFrame(rows)
    return out.sort_values(["Score", "FVM"], ascending=[False, False]).head(int(n)).reset_index(drop=True)


def mossa_compare(row_a, row_b, price_a=0, price_b=0):
    """Confronto personalizzato, anche tra ruoli diversi."""
    def pack(row, price):
        plan = effective_target_plan(row)
        info = player_intel(row)
        lo, hi = prediction(row)
        score = mossa_decision_score(row, price)
        sig = auction_signal(row, price, plan, info) if int(price or 0) > 0 else None
        slot = slot_priority_advice(row, info)
        return {
            "Nome": str(row.Nome),
            "Ruolo": str(row.Ruolo),
            "Squadra": str(row.Squadra),
            "FVM": int(row.FVM),
            "Score": score,
            "Fit": fit(row),
            "Urgenza": urgency(row.Ruolo),
            "Ideale": int(plan.get("ideal", 1) or 1),
            "STOP": int(plan.get("max", 1) or 1),
            "Stima": f"{lo}-{hi}",
            "Slot": slot["slot"],
            "Priorità": slot["priority"],
            "Titolarità": info.get("titolarita", "—"),
            "Rischio": info.get("risk", "—"),
            "Prezzo": int(price or 0),
            "Semaforo": sig["label"] if sig else "—",
        }

    a = pack(row_a, price_a)
    b = pack(row_b, price_b)
    if a["Score"] > b["Score"]:
        winner = a["Nome"]
    elif b["Score"] > a["Score"]:
        winner = b["Nome"]
    else:
        winner = "PARI"
    return a, b, winner


def mossa_scenario(row, price):
    """Simula il budget dopo un acquisto senza toccare lo stato Cloud."""
    try:
        price = int(price or 0)
    except Exception:
        price = 0

    role = str(row.Ruolo)
    role_open = role in SLOTS and role_count(role) < SLOTS[role]
    feasible = price >= 1 and role_open and price <= max_absolute() and price <= int(S["credits"])

    credits_after = int(S["credits"]) - price
    missing_after = {}
    for r in SLOTS:
        bought_here = 1 if r == role and role_open and price >= 1 else 0
        missing_after[r] = max(0, SLOTS[r] - role_count(r) - bought_here)

    total_missing = sum(missing_after.values())
    minimum_reserve = total_missing
    free_credits = credits_after - minimum_reserve
    avg_per_slot = round(credits_after / max(1, total_missing), 1) if total_missing else credits_after

    spent_by_role = {
        r: sum(int(x.get("price", 0) or 0) for x in S.get("roster", []) if x.get("role") == r)
        for r in SLOTS
    }
    if role in spent_by_role and price >= 1:
        spent_by_role[role] += price

    plan_budget = S.get("plan_budget", {}) or {}
    role_rows = []
    planned_remaining_total = 0
    for r in SLOTS:
        target = int(plan_budget.get(r, round(BUDGET * ROLE_BUDGET[r])) or 0)
        planned_left = max(missing_after[r], target - spent_by_role[r])
        planned_remaining_total += planned_left
        role_rows.append({
            "Ruolo": r,
            "Mancano": missing_after[r],
            "Spesi": spent_by_role[r],
            "Budget piano": target,
            "Budget piano residuo": planned_left,
            "Media piano/slot": round(planned_left / max(1, missing_after[r]), 1) if missing_after[r] else 0,
        })

    if not feasible:
        status = "🔴 NON FATTIBILE"
    elif total_missing == 0:
        status = "🟢 ROSA COMPLETA"
    else:
        coverage = credits_after / max(1, planned_remaining_total)
        if coverage >= 0.90:
            status = "🟢 SOLIDO"
        elif coverage >= 0.70:
            status = "🟡 TIRATO"
        else:
            status = "🔴 RISCHIOSO"

    return {
        "status": status,
        "feasible": feasible,
        "credits_after": credits_after,
        "missing_after": total_missing,
        "minimum_reserve": minimum_reserve,
        "free_credits": free_credits,
        "avg_per_slot": avg_per_slot,
        "planned_remaining_total": planned_remaining_total,
        "roles": pd.DataFrame(role_rows),
    }


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

def rebuild_from_moves(moves):
    """Valida e ricostruisce lo stato asta in modo atomico: se c'è un errore non cambia nulla."""
    new_credits = BUDGET
    new_roster = []
    new_out = []
    new_moves = []
    new_rivals = {n: {"credits": BUDGET, "slots": 25, "roles": dict(SLOTS)} for n in RIVALS}
    errors = []

    for mv0 in moves:
        mv = dict(mv0)
        try:
            name = str(mv.get("name","")).strip()
            role = str(mv.get("role","")).strip()
            team = str(mv.get("team","")).strip()
            price = int(mv.get("price",0) or 0)
            buyer = str(mv.get("buyer","-")).strip()
            action = str(mv.get("action","")).strip()
            key = f"{role}|{name}"

            if not name or role not in SLOTS:
                errors.append(f"{name or '?'}: dati giocatore non validi")
                continue
            if key in new_out:
                errors.append(f"{name}: movimento duplicato")
                continue

            if action == "INV":
                new_out.append(key)
                mv["price"] = 0
                mv["buyer"] = "-"
                mv["action"] = "INV"
                new_moves.append(mv)
                continue

            if buyer == "FC Jigen":
                action = "MIO"
                if price <= 0:
                    errors.append(f"{name}: prezzo non valido")
                    continue
                if price > new_credits:
                    errors.append(f"{name}: crediti FC Jigen insufficienti")
                    continue
                if len(new_roster) >= 25:
                    errors.append(f"{name}: rosa FC Jigen già completa")
                    continue
                if sum(1 for x in new_roster if x.get("role")==role) >= SLOTS[role]:
                    errors.append(f"{name}: slot {role} pieno")
                    continue
                # Conserva almeno 1 credito per ogni slot ancora da riempire.
                remaining_after = 25 - (len(new_roster) + 1)
                if price > max(0, new_credits - remaining_after):
                    errors.append(f"{name}: prezzo incompatibile con la chiusura della rosa")
                    continue
                new_credits -= price
                new_roster.append({
                    "name": name, "role": role, "team": team,
                    "fvm": int(mv.get("fvm",0) or 0), "price": price
                })
            else:
                action = "ALTRI"
                if price <= 0:
                    errors.append(f"{name}: prezzo non valido")
                    continue
                if buyer in new_rivals:
                    d = new_rivals[buyer]
                    if d["slots"] <= 0:
                        errors.append(f"{name}: {buyer} senza slot")
                        continue
                    if d["roles"].get(role,0) <= 0:
                        errors.append(f"{name}: {buyer} senza slot {role}")
                        continue
                    if price > d["credits"]:
                        errors.append(f"{name}: crediti {buyer} insufficienti")
                        continue
                    d["credits"] -= price
                    d["slots"] -= 1
                    d["roles"][role] -= 1

            new_out.append(key)
            mv["action"] = action
            mv["buyer"] = buyer
            mv["price"] = price
            new_moves.append(mv)
        except Exception as e:
            errors.append(str(e))

    # ATOMICO: in presenza di qualsiasi errore lo stato corrente resta intatto.
    if errors:
        return errors

    S["credits"] = new_credits
    S["roster"] = new_roster
    S["out"] = new_out
    S["moves"] = new_moves
    S["rivals"] = new_rivals
    normalize()
    return []


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
:root{
  --fm-bg:#041a14; --fm-bg2:#07251d; --fm-card:#0e3329; --fm-card2:#123d31;
  --fm-input:#123a30; --fm-green:#1da878; --fm-green-dark:#0a5e44;
  --fm-gold:#d9b85f; --fm-gold-hi:#ffe4a0; --fm-text:#fffaf0;
  --fm-muted:#d4ddd8; --fm-muted2:#b7c5be; --fm-line:rgba(217,184,95,.34);
  --fm-ok:#57d58f; --fm-warn:#ffd36d; --fm-bad:#ff8c8c;
}
html{color-scheme:dark}
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"]{max-width:100vw!important;overflow-x:hidden!important}
[data-testid="stAppViewContainer"]{background:linear-gradient(180deg,#08251d 0%,#041a14 72%);color:var(--fm-text)}
[data-testid="stHeader"]{background:#08251d;border-bottom:1px solid rgba(217,184,95,.13)}
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer{display:none!important}
[data-testid="stSidebar"]{background:#08231c!important;border-right:1px solid var(--fm-line)}
.block-container{max-width:100%!important;padding-top:.55rem;padding-bottom:8.5rem!important;overflow-x:hidden!important}

/* Global readability */
[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li{color:var(--fm-text)!important}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p{color:var(--fm-muted)!important}
[data-testid="stWidgetLabel"] p,[data-testid="stWidgetLabel"] label{color:var(--fm-gold-hi)!important;font-weight:850!important}
h1,h2,h3,h4{color:var(--fm-gold-hi)!important;letter-spacing:-.01em}
hr{border-color:rgba(217,184,95,.20)!important}

/* Brand bar */
.fm-head{display:flex;align-items:center;gap:10px;padding:9px 10px;border:1px solid var(--fm-line);border-radius:18px;background:#0e3329;margin-bottom:8px}
.fm-logo{width:43px;height:43px;border-radius:12px;flex:0 0 auto}
.fm-brandbox{min-width:0;flex:1}.fm-brand{color:var(--fm-gold-hi);font-size:1.10rem;font-weight:950;line-height:1.05}.fm-sub{color:var(--fm-muted);font-size:.74rem;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fm-cloud{font-size:.70rem;font-weight:900;color:var(--fm-gold-hi);padding:6px 8px;border:1px solid rgba(217,184,95,.46);border-radius:999px;white-space:nowrap;background:rgba(217,184,95,.09)}

/* Main status */
.fm-summary{display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px;margin:5px 0 3px}
.fm-stat{background:#0e3329;border:1px solid rgba(217,184,95,.28);border-radius:15px;text-align:center;padding:9px 4px}
.fm-stat-label{font-size:.60rem;color:var(--fm-muted);font-weight:900;letter-spacing:.03em}.fm-stat-value{font-size:1.25rem;color:var(--fm-gold-hi);font-weight:950;line-height:1.1;margin-top:2px}
.fm-mini{font-size:.72rem;color:var(--fm-muted);text-align:center;margin:3px 0 8px}

/* Page hero */
.fm-page{border:1px solid rgba(217,184,95,.25);background:#0b2d24;border-radius:18px;padding:13px 14px;margin:8px 0 12px}
.fm-page-title{font-size:1.48rem;font-weight:950;color:var(--fm-gold-hi);line-height:1.05}.fm-page-sub{font-size:.82rem;color:var(--fm-muted);line-height:1.35;margin-top:6px}
.fm-step{color:var(--fm-gold-hi);font-size:.79rem;font-weight:950;letter-spacing:.035em;text-transform:uppercase;margin:.62rem 0 .20rem}
.fm-help{color:var(--fm-muted);font-size:.76rem;line-height:1.3;margin:0 0 .50rem}

/* 3-step strip */
.fm-guide{display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin:.2rem 0 .65rem}
.fm-guide-card{background:#0e3329;border:1px solid rgba(217,184,95,.24);border-radius:14px;padding:8px 5px;text-align:center}
.fm-guide-n{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:999px;background:var(--fm-gold);color:#062019;font-weight:950;font-size:.82rem;margin-bottom:5px}
.fm-guide-title{display:block;color:var(--fm-text);font-size:.76rem;font-weight:900;line-height:1.1}.fm-guide-sub{display:block;color:var(--fm-muted2);font-size:.61rem;margin-top:2px;line-height:1.15}

/* Player / recommendation cards */
.fm-player-card{background:#10382d;border:1px solid rgba(217,184,95,.42);border-radius:17px;padding:12px;margin:.35rem 0 .55rem}
.fm-player-name{color:var(--fm-gold-hi);font-size:1.48rem;font-weight:950;line-height:1.05}.fm-player-meta{color:var(--fm-muted);font-size:.82rem;margin-top:5px}
.fm-pick{background:#10382d;border:1px solid rgba(217,184,95,.42);border-radius:17px;padding:12px 13px;margin:.35rem 0 .65rem}
.fm-pick-kicker{color:var(--fm-muted);font-size:.67rem;font-weight:900;letter-spacing:.05em;text-transform:uppercase}.fm-pick-name{color:var(--fm-gold-hi);font-size:1.38rem;font-weight:950;margin-top:3px}.fm-pick-data{color:var(--fm-text);font-size:.82rem;margin-top:5px}.fm-pick-reason{color:var(--fm-muted);font-size:.73rem;margin-top:5px;line-height:1.3}
.fm-empty{border:1px dashed rgba(217,184,95,.35);border-radius:15px;padding:13px;color:var(--fm-muted);font-size:.82rem;text-align:center;background:rgba(14,51,41,.45)}

/* Inputs */
div[data-baseweb="select"]>div,div[data-testid="stTextInput"] input,div[data-testid="stNumberInput"] input{background:var(--fm-input)!important;color:var(--fm-text)!important;-webkit-text-fill-color:var(--fm-text)!important;border:1px solid rgba(217,184,95,.55)!important;border-radius:14px!important}
div[data-baseweb="select"] *,div[data-baseweb="popover"] *{color:var(--fm-text)!important;-webkit-text-fill-color:var(--fm-text)!important}
div[data-baseweb="select"] svg{fill:var(--fm-gold-hi)!important}
input::placeholder{color:#c8d3cd!important;-webkit-text-fill-color:#c8d3cd!important;opacity:.82!important}
div[data-testid="stTextInput"] input{min-height:48px;font-size:1.02rem}div[data-testid="stNumberInput"] input{font-size:1.42rem;font-weight:950;text-align:center}div[data-testid="stSelectbox"]>div{min-height:48px}
ul[role="listbox"],div[role="listbox"]{background:#10382d!important;border:1px solid var(--fm-line)!important}

/* Metrics */
div[data-testid="stMetric"]{background:#0e3329;border:1px solid rgba(217,184,95,.25);padding:8px;border-radius:14px}
div[data-testid="stMetricLabel"],div[data-testid="stMetricLabel"] *{color:var(--fm-muted)!important}div[data-testid="stMetricValue"],div[data-testid="stMetricValue"] *{color:var(--fm-gold-hi)!important;font-weight:950!important}

/* Buttons */
div.stButton>button{min-height:47px;font-weight:900;border-radius:14px;border:1px solid rgba(217,184,95,.50);background:#123a30;color:var(--fm-text)}
div.stButton>button p{color:inherit!important;font-weight:900!important}div.stButton>button:hover{background:#17493b;border-color:var(--fm-gold-hi);color:#fff}
div.stButton>button[kind="primary"]{background:var(--fm-gold)!important;color:#062019!important;border-color:var(--fm-gold-hi)!important;font-weight:950!important}div.stButton>button[kind="primary"] p{color:#062019!important}

/* Navigation: sticky, app-like — iPhone high contrast */
.st-key-fm_main_nav{position:sticky;top:.2rem;z-index:999;background:#07251d;padding:4px 0 7px;margin:0 0 4px}
.st-key-fm_main_nav div[role="radiogroup"]{display:flex!important;width:100%!important;gap:5px!important;background:#07251d!important}
.st-key-fm_main_nav button{
 flex:1 1 0!important;min-width:0!important;padding:.42rem .12rem!important;
 font-size:.73rem!important;font-weight:900!important;border-radius:12px!important;
 border:1px solid rgba(217,184,95,.45)!important;
 background:#10382d!important;
 color:#fff5d1!important;-webkit-text-fill-color:#fff5d1!important;
 opacity:1!important
}
.st-key-fm_main_nav button *{
 color:#fff5d1!important;-webkit-text-fill-color:#fff5d1!important;
 fill:#fff5d1!important;opacity:1!important;font-weight:900!important
}
.st-key-fm_main_nav button p,.st-key-fm_main_nav button span,.st-key-fm_main_nav button div{
 color:#fff5d1!important;-webkit-text-fill-color:#fff5d1!important
}
.st-key-fm_main_nav button svg{fill:#fff5d1!important;color:#fff5d1!important}
.st-key-fm_main_nav button[aria-checked="true"]{
 background:#d9b85f!important;color:#062019!important;-webkit-text-fill-color:#062019!important;
 border:2px solid #f0d982!important;box-shadow:0 0 0 1px rgba(240,217,130,.12)!important
}
.st-key-fm_main_nav button[aria-checked="true"] *{
 color:#062019!important;-webkit-text-fill-color:#062019!important;fill:#062019!important
}

.st-key-fm_centrale_nav div[role="radiogroup"]{display:flex!important;width:100%!important;gap:4px!important}
.st-key-fm_centrale_nav button{flex:1 1 0!important;min-width:0!important;padding:.40rem .08rem!important;font-size:.70rem!important;font-weight:900!important;border-radius:11px!important;border:1px solid rgba(217,184,95,.34)!important;background:#10382d!important;color:#fff5d1!important;-webkit-text-fill-color:#fff5d1!important}
.st-key-fm_centrale_nav button,.st-key-fm_centrale_nav button *{color:#fff5d1!important;-webkit-text-fill-color:#fff5d1!important;fill:#fff5d1!important;opacity:1!important}
.st-key-fm_centrale_nav button[aria-checked="true"]{background:#d9b85f!important;color:#062019!important;-webkit-text-fill-color:#062019!important;border:2px solid #f0d982!important}
.st-key-fm_centrale_nav button[aria-checked="true"],.st-key-fm_centrale_nav button[aria-checked="true"] *{color:#062019!important;-webkit-text-fill-color:#062019!important;fill:#062019!important}
.st-key-live_role button,.st-key-mossa_role_filter button,.st-key-mossa_tool button,.st-key-fm_extra_tool button{background:#10382d!important;color:var(--fm-text)!important;border-color:rgba(217,184,95,.30)!important;font-weight:850!important}
.st-key-live_role button[aria-checked="true"],.st-key-mossa_role_filter button[aria-checked="true"],.st-key-mossa_tool button[aria-checked="true"],.st-key-fm_extra_tool button[aria-checked="true"]{background:var(--fm-gold)!important;color:#062019!important}

/* Secondary components */
[data-testid="stExpander"]{border-color:rgba(217,184,95,.25)!important;border-radius:14px!important;background:rgba(14,51,41,.55)}
[data-testid="stDataFrame"]{border:1px solid rgba(217,184,95,.22);border-radius:12px;overflow:hidden}
[data-testid="stInfo"],[data-testid="stSuccess"],[data-testid="stWarning"],[data-testid="stError"]{border-radius:14px!important}

@media(max-width:700px){
 .block-container{padding:.48rem .58rem 2.6rem}.fm-head{padding:7px 8px;border-radius:15px}.fm-logo{width:38px;height:38px}.fm-brand{font-size:1rem}.fm-cloud{font-size:.63rem;padding:5px 6px}.fm-summary{gap:5px}.fm-stat{padding:7px 3px}.fm-stat-label{font-size:.56rem}.fm-stat-value{font-size:1.13rem}.fm-page{padding:11px 12px}.fm-page-title{font-size:1.34rem}.fm-guide{gap:5px}.fm-guide-card{padding:7px 4px}.fm-guide-title{font-size:.72rem}.fm-guide-sub{font-size:.58rem}.fm-player-name{font-size:1.34rem}.fm-pick-name{font-size:1.25rem}
 div.stButton>button{min-height:44px!important;padding:.34rem .38rem!important}.st-key-fm_main_nav button{font-size:.66rem!important;padding:.37rem .05rem!important;white-space:nowrap!important}div[data-testid="column"]{min-width:0!important}
}
</style>""",unsafe_allow_html=True)


st.markdown("""
<style>
/* v3.20.1 — FIX DROPDOWN GIOCATORI iPhone/Safari */

/* Campo selezione: chiaro e leggibile */
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    background:#F7F8FA !important;
    border:2px solid #D8B75F !important;
    color:#17211D !important;
    -webkit-text-fill-color:#17211D !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"] input,
div[data-testid="stSelectbox"] div[data-baseweb="select"] span {
    color:#17211D !important;
    -webkit-text-fill-color:#17211D !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"] input::placeholder {
    color:#66736D !important;
    -webkit-text-fill-color:#66736D !important;
    opacity:1 !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"] svg {
    fill:#17211D !important;
    color:#17211D !important;
}

/* Menu aperto: sfondo bianco, testo scuro */
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
ul[role="listbox"],
div[role="listbox"] {
    background:#FFFFFF !important;
    color:#17211D !important;
}

/* Ogni giocatore nel menu */
div[role="option"],
li[role="option"],
ul[role="listbox"] li,
div[data-baseweb="popover"] li {
    background:#FFFFFF !important;
    color:#17211D !important;
    -webkit-text-fill-color:#17211D !important;
    font-weight:700 !important;
}

/* Forza anche tutti i figli testuali delle opzioni */
div[role="option"] *,
li[role="option"] *,
ul[role="listbox"] li *,
div[data-baseweb="popover"] li * {
    color:#17211D !important;
    -webkit-text-fill-color:#17211D !important;
}

/* Riga evidenziata/selezionata */
div[role="option"]:hover,
div[role="option"][aria-selected="true"],
li[role="option"]:hover,
li[role="option"][aria-selected="true"] {
    background:#E8F2ED !important;
    color:#0B3A2B !important;
}
div[role="option"][aria-selected="true"] *,
li[role="option"][aria-selected="true"] * {
    color:#0B3A2B !important;
    -webkit-text-fill-color:#0B3A2B !important;
}
</style>
""", unsafe_allow_html=True)



def fm_page(title, subtitle):
    st.markdown(
        f'<div class="fm-page"><div class="fm-page-title">{title}</div><div class="fm-page-sub">{subtitle}</div></div>',
        unsafe_allow_html=True
    )

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

cloud_badge = "☁️ OK" if st.session_state.get("_cloud_ok") else "☁️ Cloud"
st.markdown(
    f"""<div class="fm-head">
      <img class="fm-logo" src="data:image/png;base64,{FANTAMOSSA_ICON_B64}">
      <div class="fm-brandbox"><div class="fm-brand">FantaMossa</div><div class="fm-sub">FC Jigen • Asta 2026/27</div></div>
      <div class="fm-cloud">{cloud_badge}</div>
    </div>""",
    unsafe_allow_html=True
)

with st.sidebar:
    st.header("⚙️ FantaMossa")
    st.caption("Controlli rapidi • v3.35.3")
    st.button("☁️ SALVA ORA", width="stretch", on_click=_quick_cloud_save, key="sidebar_quick_save")
    st.button("↩️ ANNULLA ULTIMA", width="stretch", on_click=_quick_undo, key="sidebar_quick_undo")
    quick_sidebar_notice=st.session_state.pop("_quick_notice",None)
    if quick_sidebar_notice:
        st.info(quick_sidebar_notice)

    issues=integrity()
    if not issues:
        st.success("✅ Stato integro")
    else:
        st.error("⚠️ " + ", ".join(issues))

    with st.expander("☁️ Cloud, backup e sicurezza", expanded=False):
        secrets_ready = cloud_config_status()
        sb_ready = cloud_config_status()
        if secrets_ready and sb_ready:
            if st.session_state.get("_cloud_ok"):
                last = st.session_state.get("_cloud_last_save", "")
                st.success("Cloud collegato" + (f" • {last}" if last else ""))
            else:
                st.info("Cloud configurato")
            notice = st.session_state.get("_cloud_notice")
            if notice:
                st.success(notice) if notice.startswith("✅") else st.error(notice)
        elif not secrets_ready:
            st.warning("Secrets Supabase non letti")
        else:
            st.error("Configurazione Cloud non valida")

        up=st.file_uploader("Importa backup JSON",type=["json"])
        if up and st.button("Carica backup",width="stretch",key="sidebar_load_backup"):
            try:
                data=json.load(up)
                if not isinstance(data,dict) or "roster" not in data or "moves" not in data: raise ValueError("Formato non valido")
                st.session_state.auction=data;normalize();persist();st.rerun()
            except Exception as e: st.error(f"Backup non valido: {e}")
        st.download_button("⬇️ BACKUP JSON",backup_bytes(),file_name=f"FC_Jigen_{datetime.now():%Y%m%d_%H%M}.json",mime="application/json",width="stretch")

    with st.expander("⚠️ Nuova asta", expanded=False):
        st.warning("Azzera lo stato corrente. Usa prima BACKUP JSON se vuoi conservarlo.")
        if st.button("RESET ASTA",width="stretch",key="sidebar_reset_auction"):
            st.session_state.auction=default_state();persist();st.rerun()

st.markdown(
    f"""<div class="fm-summary">
      <div class="fm-stat"><div class="fm-stat-label">💰 CREDITI</div><div class="fm-stat-value">{S["credits"]}</div></div>
      <div class="fm-stat"><div class="fm-stat-label">👕 PRESI</div><div class="fm-stat-value">{len(S["roster"])}/25</div></div>
      <div class="fm-stat"><div class="fm-stat-label">🔨 MAX</div><div class="fm-stat-value">{max_absolute()}</div></div>
    </div><div class="fm-mini">Spesi {BUDGET-S["credits"]} • Mercato {market_index():.2f}x</div>""",
    unsafe_allow_html=True
)


# --- v3.16: pagine isolate. I widget rerenderizzano solo la pagina attiva. ---
def render_asta():
    fm_page("🔥 Asta Live", "Tre tocchi: scegli il giocatore, valuta il prezzo, registra l’esito.")
    st.markdown("""
    <div class="fm-guide">
      <div class="fm-guide-card"><span class="fm-guide-n">1</span><span class="fm-guide-title">Scegli</span><span class="fm-guide-sub">trova il giocatore</span></div>
      <div class="fm-guide-card"><span class="fm-guide-n">2</span><span class="fm-guide-title">Prezzo</span><span class="fm-guide-sub">usa i tap veloci</span></div>
      <div class="fm-guide-card"><span class="fm-guide-n">3</span><span class="fm-guide-title">Registra</span><span class="fm-guide-sub">FC Jigen o rivale</span></div>
    </div>
    """, unsafe_allow_html=True)


    quick_notice=st.session_state.pop("_quick_notice",None)
    if quick_notice:
        st.info(quick_notice)
    repaired_notice=st.session_state.pop("_prices_repaired",None)
    if repaired_notice:
        st.success(f"✅ Prezzi Piano riparati: {repaired_notice} target aggiornati")
    cloud_notice=st.session_state.get("_cloud_notice")
    if cloud_notice and cloud_notice.startswith("✅"):
        st.caption(cloud_notice)

    st.markdown('<div class="fm-step">1 • Trova il giocatore</div>', unsafe_allow_html=True)
    st.markdown('<div class="fm-help">Cerca per nome o filtra prima il ruolo.</div>', unsafe_allow_html=True)

    # PERFORMANCE: il selectbox fa la ricerca nel browser.
    # Non eseguiamo più il Python ad ogni lettera digitata su iPhone.
    role=st.segmented_control(
        "RUOLO",
        ["TUTTI","POR","DIF","CEN","ATT"],
        default="TUTTI",
        key="live_role"
    )
    ap=all_players()
    av=ap[~ap.key.isin(set(S["out"]))].copy()
    if role and role!="TUTTI":
        av=av[av.Ruolo==role]
    av=av.sort_values(["FVM","Nome"],ascending=[False,True])

    av_map={str(r.key): r for _,r in av.iterrows()}
    av_keys=list(av_map.keys())
    choice=st.selectbox(
        "🔎 Cerca / scegli giocatore",
        av_keys,
        index=None,
        placeholder="Scrivi Lautaro, Nico Paz, Dimarco...",
        key="asta_live_player_v331",
        format_func=lambda k: player_fast_label(av_map[str(k)])
    )

    row=None
    if choice:
        row=av_map[str(choice)]
        lo,hi=prediction(row); cap=cap_for(row); comp,nint=competition(row.Ruolo)
        manual_plan=S["targets"].get(row.key)
        plan=effective_target_plan(row)

        st.markdown(f"<div class=\"fm-player-card\"><div class=\"fm-player-name\">{row.Nome}</div><div class=\"fm-player-meta\">{row.Ruolo} • {row.Squadra} • FVM {int(row.FVM)}</div></div>", unsafe_allow_html=True)

        p1,p2,p3=st.columns(3)
        p1.metric("🎯 PRIORITÀ",plan.get("priority","C") if manual_plan else f'{plan.get("priority","C")} AUTO')
        p2.metric("💚 IDEALE",int(plan.get("ideal",1) or 1))
        p3.metric("🛑 STOP",int(plan.get("max",1) or 1))

        with st.expander("🧠 Perché FantaMossa lo valuta così", expanded=False):
            render_player_intel(row)

        st.markdown('<div class="fm-step">2 • Prezzo e semaforo</div>', unsafe_allow_html=True)
        st.markdown('<div class="fm-help">Inserisci il rilancio corrente. Il semaforo reagisce subito.</div>', unsafe_allow_html=True)
        if st.session_state.pop("_reset_live_price_next", False):
            st.session_state["live_price"] = 0
        price=st.number_input(
            "Prezzo asta",
            min_value=0,
            step=1,
            value=0,
            key="live_price",
            label_visibility="collapsed"
        )

        live_sig=auction_signal(row,price,plan,player_intel(row))
        if price:
            if live_sig["label"].startswith("🟢"):
                st.success("🚦 "+live_sig["label"]+" — "+live_sig["reason"])
            elif live_sig["label"].startswith("🟡"):
                st.warning("🚦 "+live_sig["label"]+" — "+live_sig["reason"])
            else:
                st.error("🚦 "+live_sig["label"]+" — "+live_sig["reason"])
            st.caption(
                f"IDEALE {live_sig['ideal']} • STOP {live_sig['stop']} • "
                f"STOP operativo {live_sig['effective_stop']} • Max sostenibile {live_sig['max_affordable']}"
            )

        b1,b2,b3,b4,b5=st.columns(5)
        b1.button("− 1",width="stretch",on_click=_quick_price,args=(-1,))
        b2.button("+ 1",width="stretch",on_click=_quick_price,args=(1,))
        b3.button("+ 5",width="stretch",on_click=_quick_price,args=(5,))
        b4.button("+ 10",width="stretch",on_click=_quick_price,args=(10,))
        b5.button("↺",width="stretch",on_click=_reset_live_price)

        st.markdown('<div class="fm-step">3 • Registra l’esito</div>', unsafe_allow_html=True)
        st.markdown('<div class="fm-help">Scegli il vincitore: crediti, slot e storico si aggiornano automaticamente.</div>', unsafe_allow_html=True)
        buyer=st.selectbox(
            "👤 Destinazione del giocatore",
            ["FC Jigen","NON TRACCIATO"]+RIVALS,
            key="live_buyer"
        )

        register_label = "✅ PRENDI PER FC JIGEN" if buyer=="FC Jigen" else f"✅ REGISTRA • {buyer}"
        if st.button(register_label,type="primary",width="stretch",key="live_register_main"):
            k=row.key
            if price <= 0:
                st.error("⛔ Inserisci un prezzo di almeno 1 credito.")
            elif k in S["out"]:
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
                    st.session_state["_reset_live_price_next"]=True
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
                st.session_state["_reset_live_price_next"]=True
                st.rerun()

        if st.button("⛔ SEGNALA INVENDUTO",width="stretch",key="live_unsold_main"):
            S["out"].append(row.key)
            S["moves"].append({"name":row.Nome,"role":row.Ruolo,"team":row.Squadra,"fvm":int(row.FVM),
                               "price":0,"action":"INV","buyer":"-","time":datetime.now().isoformat(timespec="seconds")})
            persist()
            st.session_state["_reset_live_price_next"]=True
            st.rerun()

        with st.expander("🧠 Dettagli e Piano B",expanded=False):
            conf_label, conf_n = prediction_confidence(row.Ruolo)
            a,b,c=st.columns(3)
            a.metric("Fascia",tier(row.FVM))
            b.metric("Fit",fit(row))
            c.metric("Stima",f"{lo}-{hi}")
            st.caption(
                f"Affidabilità stima: {conf_label} ({conf_n} prezzi {row.Ruolo} osservati) • "
                f"Concorrenza {row.Ruolo}: {comp}/100 • {nint} rivali con slot • "
                f"Urgenza {urgency(row.Ruolo)}/100 • Scarsità {scarcity(row.Ruolo)}/100"
            )
            if plan:
                if plan.get("alternatives"):
                    st.write("**Alternative:** "+str(plan.get("alternatives")))
                if plan.get("notes"):
                    st.write("**Nota:** "+str(plan.get("notes")))
            pb=plan_b(row)
            if len(pb):
                st.write("**Piano B automatico:** "+ " • ".join(f"{x.Nome} (FVM {x.FVM})" for _,x in pb.iterrows()))
    else:
        st.markdown('<div class="fm-empty">🔎 Scegli un giocatore per vedere priorità, prezzo ideale, STOP e consiglio live.</div>', unsafe_allow_html=True)

def render_radar():
    fm_page("📡 Radar", "Pressione d’asta, scarsità per ruolo e potenza residua degli avversari.")
    rr=[]
    for r in SLOTS:
        sc,n=competition(r)
        label="CRITICA" if sc>=75 else "ALTA" if sc>=55 else "MEDIA" if sc>=32 else "BASSA"
        rr.append({"Ruolo":r,"Pressione":sc,"Livello":label,"Avversari interessati":n,
                   "Scarsità":scarcity(r),"Urgenza FC Jigen":urgency(r)})
    st.dataframe(pd.DataFrame(rr),hide_index=True,width="stretch")
    rivals=[]
    for n,d in S["rivals"].items():
        avg=d["credits"]/max(1,d["slots"])
        rivals.append({"Squadra":n,"Crediti":d["credits"],"Slot":d["slots"],"Crediti/slot":round(avg,1),
                       "Potenza":"ALTA" if avg>=45 else "MEDIA" if avg>=25 else "BASSA"})
    st.dataframe(pd.DataFrame(rivals).sort_values("Crediti/slot",ascending=False),hide_index=True,width="stretch")

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

def render_dashboard():
    """Dashboard centrale post-asta: solo calcoli locali, nessuna chiamata Cloud aggiuntiva."""
    fm_page("📊 Dashboard FC Jigen", "Quadro centrale post-asta: valore rosa, forza reparti, affari e punti da monitorare.")

    roster = list(S.get("roster", []))
    if not roster:
        st.markdown('<div class="fm-empty">👕 La rosa è ancora vuota. Gli acquisti registrati in Asta compariranno qui automaticamente.</div>', unsafe_allow_html=True)
        return

    # DataFrame locale: costruito una sola volta per render.
    rdf = pd.DataFrame(roster).rename(columns={
        "name":"Nome", "role":"Ruolo", "team":"Squadra", "fvm":"FVM", "price":"Prezzo"
    })
    for col in ["FVM", "Prezzo"]:
        if col not in rdf.columns:
            rdf[col] = 0
        rdf[col] = pd.to_numeric(rdf[col], errors="coerce").fillna(0).astype(int)

    # Arricchimento con ranking/slot già calcolati nel foglio Valutazioni.
    def _v(name, field, default=""):
        return VALUATION_BY_NAME.get(str(name), {}).get(field, default)

    rdf["RankRuolo"] = rdf["Nome"].map(lambda n: _v(n, "RankRuolo", 999))
    rdf["TotRuolo"] = rdf["Nome"].map(lambda n: _v(n, "TotRuolo", 1))
    rdf["Slot"] = rdf["Nome"].map(lambda n: _v(n, "SlotLega10", ""))
    rdf["Titolarità"] = rdf["Nome"].map(lambda n: _v(n, "Titolarita", "DA VERIFICARE"))
    rdf["Affidabilità"] = rdf["Nome"].map(lambda n: _v(n, "Affidabilita", "DA VERIFICARE"))
    rdf["RankRuolo"] = pd.to_numeric(rdf["RankRuolo"], errors="coerce").fillna(999).astype(int)
    rdf["TotRuolo"] = pd.to_numeric(rdf["TotRuolo"], errors="coerce").fillna(1).clip(lower=1).astype(int)

    # Forza 0-100: percentile inverso nel proprio ruolo. Non inventa titolarità.
    rdf["Forza"] = ((1 - ((rdf["RankRuolo"] - 1) / rdf["TotRuolo"])) * 100).clip(0,100).round().astype(int)
    rdf["ValorePrezzo"] = (rdf["FVM"] / rdf["Prezzo"].clip(lower=1)).round(2)
    rdf["DeltaMercato"] = rdf["FVM"] - rdf["Prezzo"]

    spent = int(rdf["Prezzo"].sum())
    total_fvm = int(rdf["FVM"].sum())
    credits = int(S.get("credits", 0) or 0)
    avg_strength = int(round(rdf["Forza"].mean())) if len(rdf) else 0

    # KPI principali.
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("💎 Valore FVM rosa", total_fvm)
    k2.metric("💰 Spesa asta", spent)
    k3.metric("🏦 Crediti residui", credits)
    k4.metric("⚡ Forza media", f"{avg_strength}/100")

    # Stato reparto: media forza + migliore giocatore + costo.
    st.markdown("### 🧩 Forza reparti")
    role_rows=[]
    role_cards=st.columns(4)
    for col, role in zip(role_cards, ["POR","DIF","CEN","ATT"]):
        sub=rdf[rdf["Ruolo"].eq(role)].copy()
        strength=int(round(sub["Forza"].mean())) if not sub.empty else 0
        best=sub.sort_values(["Forza","FVM"], ascending=False).iloc[0]["Nome"] if not sub.empty else "—"
        role_spent=int(sub["Prezzo"].sum()) if not sub.empty else 0
        col.metric(role, f"{strength}/100", f"{len(sub)}/{SLOTS[role]} • {role_spent} cr")
        role_rows.append({"Ruolo":role,"Forza":strength,"Migliore":best,"Spesa":role_spent})

    strongest=max(role_rows, key=lambda x:x["Forza"])
    weakest=min(role_rows, key=lambda x:x["Forza"])
    st.caption(f"🏆 Reparto più forte: {strongest['Ruolo']} ({strongest['Forza']}/100) • ⚠️ Da monitorare: {weakest['Ruolo']} ({weakest['Forza']}/100)")

    st.markdown("### ⭐ Pilastri della rosa")
    top = rdf.sort_values(["Forza","FVM"], ascending=False).head(5)
    st.dataframe(
        top[["Nome","Ruolo","Squadra","FVM","Prezzo","Slot","Forza"]],
        hide_index=True,
        width="stretch"
    )

    # Affari: evita che il semplice acquisto a 1 domini tutto; combina FVM, forza e prezzo.
    rdf["AffareScore"] = (rdf["Forza"] * 0.55 + rdf["FVM"].clip(upper=150) * 0.25 + (100 / rdf["Prezzo"].clip(lower=1)).clip(upper=40) * 0.20).round(1)
    bargains = rdf.sort_values(["AffareScore","ValorePrezzo"], ascending=False).head(5)
    st.markdown("### 💚 Migliori affari")
    st.dataframe(
        bargains[["Nome","Ruolo","Prezzo","FVM","Slot","Forza","ValorePrezzo"]].rename(columns={"ValorePrezzo":"FVM/credito"}),
        hide_index=True,
        width="stretch"
    )

    # Acquisti da rivedere: prezzo alto rispetto al valore/ranking; non etichetta come errore assoluto.
    watch = rdf.copy()
    watch["PressionePrezzo"] = (watch["Prezzo"] / watch["FVM"].clip(lower=1)).round(2)
    watch = watch.sort_values(["PressionePrezzo","Prezzo"], ascending=False).head(5)
    st.markdown("### 👀 Acquisti da monitorare")
    st.caption("Non significa 'acquisto sbagliato': evidenzia solo chi è stato pagato molto rispetto al FVM corrente.")
    st.dataframe(
        watch[["Nome","Ruolo","Prezzo","FVM","Slot","Forza","PressionePrezzo"]].rename(columns={"PressionePrezzo":"Prezzo/FVM"}),
        hide_index=True,
        width="stretch"
    )

    # Alert qualitativi locali.
    st.markdown("### 🚦 Check rosa")
    alerts=[]
    low = rdf[rdf["Forza"] < 35].sort_values("Forza")
    if not low.empty:
        alerts.append("⚠️ Profili con ranking basso nel ruolo: " + ", ".join(low["Nome"].head(6).tolist()))
    unverified = rdf[rdf["Titolarità"].astype(str).str.upper().eq("DA VERIFICARE")]
    if not unverified.empty:
        alerts.append(f"🔎 Titolarità ancora da verificare per {len(unverified)} giocatori: il sistema non la inventa.")
    if credits > 0:
        alerts.append(f"🏦 Hai {credits} crediti residui: utili per mercato di riparazione/scambi secondo regolamento.")
    if not alerts:
        st.success("✅ Nessun alert strutturale rilevante sulla rosa.")
    else:
        for a in alerts:
            st.info(a)

    # Dettaglio rosa completo, ma chiuso di default per tenere la dashboard leggera su iPhone.
    with st.expander("👕 ROSA COMPLETA E VALUTAZIONI", expanded=False):
        detail = rdf[["Nome","Ruolo","Squadra","Prezzo","FVM","Slot","Forza","Titolarità","Affidabilità"]].copy()
        detail = detail.sort_values(["Ruolo","Forza"], ascending=[True,False])
        st.dataframe(detail, hide_index=True, width="stretch")
        st.download_button(
            "⬇️ ESPORTA ROSA CSV",
            detail.to_csv(index=False).encode(),
            file_name="rosa_fc_jigen_post_asta.csv",
            mime="text/csv",
            width="stretch"
        )


@st.cache_data(ttl=600, show_spinner=False)
def _fetch_public_page_text(url):
    """Scarica una pagina pubblica con timeout breve e restituisce solo testo normalizzato."""
    try:
        req = Request(url, headers={"User-Agent":"Mozilla/5.0 FantaMossa/3.34.3"})
        with urlopen(req, timeout=3.0) as resp:
            raw = resp.read(900000).decode("utf-8", "ignore")
        raw = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", raw)
        raw = re.sub(r"(?s)<[^>]+>", " ", raw)
        raw = html_lib.unescape(raw)
        raw = re.sub(r"\\s+", " ", raw).strip()
        return raw, ""
    except Exception as exc:
        return "", f"{type(exc).__name__}: {exc}"


def _player_search_terms(player_name):
    """Termini conservativi per riconoscere il giocatore senza confonderlo con omonimi."""
    norm = _norm_search(player_name)
    toks = [t for t in norm.split() if len(t) >= 3]
    if not toks:
        return []
    # Il nome Fantacalcio è spesso cognome + iniziale: il primo token è in genere il più discriminante.
    return toks


def _operational_norm(s):
    """Normalizzazione per fonti operative: preserva % per leggere le probabilità."""
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9%]+", " ", s)
    return " ".join(s.split())


def _find_player_windows(page_text, player_name, radius=220):
    if not page_text:
        return []
    low = _operational_norm(page_text)
    terms = _player_search_terms(player_name)
    if not terms:
        return []
    primary = terms[0]
    windows = []
    start = 0
    while True:
        i = low.find(primary, start)
        if i < 0:
            break
        w = low[max(0, i-radius):min(len(low), i+radius)]
        if all(t in w for t in terms[1:]):
            windows.append(w)
        start = i + len(primary)
        if len(windows) >= 6:
            break
    return windows


@st.cache_data(ttl=600, show_spinner=False)
def fetch_fantacalcio_operational_status(player_name, team_name):
    """Stato rigoroso: infortuni + probabili formazioni Fantacalcio. Le news NON decidono lo stato."""
    injuries_url = "https://www.fantacalcio.it/serie-a/infortunati"
    probable_url = "https://www.fantacalcio.it/probabili-formazioni-serie-a"

    injuries_text, err_i = _fetch_public_page_text(injuries_url)
    probable_text, err_p = _fetch_public_page_text(probable_url)

    iw = _find_player_windows(injuries_text, player_name)
    pw = _find_player_windows(probable_text, player_name)

    result = {
        "status": "⚪ Da verificare",
        "confidence": "NON CONFERMATO",
        "reason": "Nessuna evidenza abbastanza forte nelle fonti operative.",
        "titolarita_live": "DA VERIFICARE",
        "percentage": None,
        "sources": [],
        "errors": [x for x in (err_i, err_p) if x],
    }

    # 1) Infortunati/indisponibili ha priorità assoluta.
    if iw:
        joined = " ".join(iw)
        hard_out = (
            " out ", "indisponibile", "lesione", "frattura", "operato", "operazione",
            "rottura", "ai box", "fuori causa", "non disponibile", "squalificato",
            "rientro da", "rientro dalla", "rientro inizio", "rientro metà", "rientro fine"
        )
        doubt = (
            "da valutare", "a rischio", "in dubbio", "affaticamento", "risentimento",
            "problema", "noie", "monitorato", "monitorate", "recupero"
        )
        if any(k in joined for k in hard_out):
            # Se nello stesso contesto si parla esplicitamente di valutazione per il prossimo turno,
            # classifica dubbio invece di OUT definitivo.
            if any(k in joined for k in ("da valutare", "a rischio", "in dubbio")) and not any(k in joined for k in ("out contro", "assente", "non disponibile")):
                result.update(status="⚠️ Dubbio", confidence="ALTA", reason="Presente nell'elenco infortunati/indisponibili con condizioni da valutare.")
            else:
                result.update(status="⛔ OUT", confidence="ALTA", reason="Presente nell'elenco Fantacalcio infortunati/indisponibili.")
        elif any(k in joined for k in doubt):
            result.update(status="⚠️ Dubbio", confidence="ALTA", reason="Fantacalcio segnala condizioni da valutare.")
        else:
            result.update(status="⚠️ Dubbio", confidence="MEDIA", reason="Il giocatore compare nell'elenco infortunati/indisponibili.")
        result["sources"].append(("Fantacalcio — Infortunati", injuries_url))

    # 2) Probabili: ricava percentuale/titolarità e conferma disponibilità solo se il giocatore compare davvero.
    if pw:
        joined_p = " ".join(pw)
        percentages = [int(x) for x in re.findall(r"(?:^|\\s)(\\d{1,3})\\s*%", joined_p) if 0 <= int(x) <= 100]
        pct = max(percentages) if percentages else None
        if pct is not None:
            result["percentage"] = pct
            if pct >= 70:
                result["titolarita_live"] = f"PROBABILE TITOLARE {pct}%"
            elif pct >= 40:
                result["titolarita_live"] = f"BALLOTTAGGIO {pct}%"
            else:
                result["titolarita_live"] = f"PANCHINA / CHANCE {pct}%"
        elif "panchina" in joined_p:
            result["titolarita_live"] = "PANCHINA PROBABILE"
        elif "ballottaggio" in joined_p:
            result["titolarita_live"] = "BALLOTTAGGIO"
        else:
            result["titolarita_live"] = "PRESENTE NELLE PROBABILI"

        result["sources"].append(("Fantacalcio — Probabili formazioni", probable_url))

        # Se non c'è nessun segnale medico negativo e compare nelle probabili, è disponibile.
        if not iw:
            result.update(
                status="✅ Disponibile",
                confidence="ALTA",
                reason="Presente nelle probabili formazioni Fantacalcio e non presente tra gli indisponibili."
            )

    # Nessuna classificazione positiva solo per assenza dall'elenco infortuni.
    return result


@st.cache_data(ttl=600, show_spinner=False)
def fetch_roster_lineup_live(roster_signature):
    """Una sola lettura delle probabili per tutta la rosa: % immediate in Formazione."""
    probable_url = "https://www.fantacalcio.it/probabili-formazioni-serie-a"
    probable_text, err = _fetch_public_page_text(probable_url)
    results = {}
    if err or not probable_text:
        return results, err or "Fonte probabili non disponibile"

    for player_name, team_name in roster_signature:
        windows = _find_player_windows(probable_text, player_name, radius=180)
        if not windows:
            results[player_name] = {
                "percentage": None,
                "titolarita_live": "N/D",
                "source": probable_url,
            }
            continue

        # Cerca percentuali solo molto vicino al nome. Se ce ne sono più di una,
        # prende la prima finestra che contiene un valore plausibile e il valore massimo
        # della stessa finestra (tipico ballottaggio espresso con più percentuali).
        pct = None
        for w in windows:
            vals = [int(x) for x in re.findall(r"(?:^|\\s)(\\d{1,3})\\s*%", w) if 0 <= int(x) <= 100]
            if vals:
                pct = max(vals)
                break

        joined = " ".join(windows)
        if pct is not None:
            if pct >= 70:
                label = f"PROBABILE TITOLARE {pct}%"
            elif pct >= 40:
                label = f"BALLOTTAGGIO {pct}%"
            else:
                label = f"PANCHINA / CHANCE {pct}%"
        elif "titolare" in joined and "panchina" not in joined:
            label = "PROBABILE TITOLARE"
        elif "ballottaggio" in joined:
            label = "BALLOTTAGGIO"
        elif "panchina" in joined:
            label = "PANCHINA PROBABILE"
        else:
            label = "PRESENTE NELLE PROBABILI"

        results[player_name] = {
            "percentage": pct,
            "titolarita_live": label,
            "source": probable_url,
        }

    return results, ""


def preload_roster_lineup_live():
    """Aggiorna Session State con le % live in un unico batch."""
    roster = [dict(x) for x in S.get("roster", [])]
    signature = tuple((str(p.get("name", "")), str(p.get("team", ""))) for p in roster)
    if not signature:
        return ""
    live_map, err = fetch_roster_lineup_live(signature)
    auto_detail = st.session_state.setdefault("auto_player_status_detail", {})
    for p in roster:
        name = str(p.get("name", ""))
        live = live_map.get(name, {})
        existing = dict(auto_detail.get(name, {}))
        # Non sovrascrive lo stato medico; aggiorna solo la titolarità live.
        existing["percentage"] = live.get("percentage")
        existing["titolarita_live"] = live.get("titolarita_live", "N/D")
        existing["lineup_source"] = live.get("source", "")
        auto_detail[name] = existing
    return err


@st.cache_data(ttl=900, show_spinner=False)
def fetch_player_news(player_name, team_name, limit=5, max_age_days=14):
    """News rigorose: solo giocatore selezionato, solo articoli recenti, timeout breve."""
    player_name = str(player_name or "").strip()
    team_name = str(team_name or "").strip()

    # Cerca il giocatore esatto + squadra. Il filtro locale sotto è comunque obbligatorio.
    query = f'"{player_name}" "{team_name}"'
    url = "https://news.google.com/rss/search?q=" + quote_plus(query) + "&hl=it&gl=IT&ceid=IT:it"

    # Token utili del nome. Ignora iniziali singole / punteggiatura.
    name_tokens = [
        t for t in _norm_search(player_name).split()
        if len(t) >= 3
    ]
    team_tokens = [
        t for t in _norm_search(team_name).split()
        if len(t) >= 3
    ]

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max_age_days)

    try:
        req = Request(url, headers={"User-Agent":"Mozilla/5.0 FantaMossa/3.35.3"})
        with urlopen(req, timeout=2.8) as resp:
            data = resp.read()

        root = ET.fromstring(data)
        out = []

        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_raw = (item.findtext("pubDate") or "").strip()
            if not title:
                continue

            title_norm = _norm_search(title)

            # Deve parlare davvero del giocatore selezionato.
            # Per nomi abbreviati basta il cognome significativo, ma la squadra
            # aiuta a scartare omonimi/risultati generici.
            if name_tokens and not all(tok in title_norm for tok in name_tokens):
                continue

            if len(name_tokens) == 1 and team_tokens:
                # Se il nome nel listone è solo il cognome, accetta comunque
                # articoli senza squadra solo se il cognome è molto specifico.
                surname = name_tokens[0]
                if surname not in title_norm:
                    continue

            try:
                pub_dt = parsedate_to_datetime(pub_raw)
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                pub_dt = pub_dt.astimezone(timezone.utc)
            except Exception:
                continue

            # Niente articoli vecchi.
            if pub_dt < cutoff or pub_dt > now + timedelta(hours=2):
                continue

            # Google News mette spesso la fonte dopo " - ".
            source = ""
            clean_title = title
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                if len(parts) == 2:
                    clean_title, source = parts[0].strip(), parts[1].strip()

            out.append({
                "title": clean_title,
                "source": source or "Google News",
                "link": link,
                "pubDate": pub_dt,
                "pubLabel": pub_dt.astimezone().strftime("%d/%m/%Y %H:%M"),
            })

        # Più recenti prima e senza duplicati di titolo.
        out.sort(key=lambda x: x["pubDate"], reverse=True)
        seen = set()
        deduped = []
        for n in out:
            k = _norm_search(n["title"])
            if not k or k in seen:
                continue
            seen.add(k)
            deduped.append(n)
            if len(deduped) >= limit:
                break

        return deduped, ""

    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"


def infer_player_status(news_items):
    """Stato automatico basato SOLO su segnali espliciti nelle news recenti."""
    if not news_items:
        return {
            "status": "⚪ Da verificare",
            "confidence": "NESSUNA EVIDENZA RECENTE",
            "reason": "Nessuna notizia recente sufficientemente specifica.",
        }

    out_kw = (
        "lesione", "frattura", "operato", "operazione", "infortunio",
        "indisponibile", "non convocato", "squalificato", "salta ",
        "fuori ", " ko ", "stop ", "rottura"
    )
    doubt_kw = (
        "dubbio", "ballottaggio", "affaticamento", "problema",
        "da valutare", "in forse", "a parte", "personalizzato",
        "non al meglio", "recupero"
    )
    available_kw = (
        "recuperato", "convocato", "in gruppo", "disponibile",
        "titolare", "dal 1", "rientra", "rientrato"
    )

    # Le news sono già ordinate dalla più recente.
    for n in news_items:
        t = " " + _norm_search(n.get("title", "")) + " "

        # Segnali di recupero più recenti prevalgono su vecchi infortuni.
        if any(_norm_search(k) in t for k in available_kw):
            return {
                "status": "✅ Disponibile",
                "confidence": "ALTA",
                "reason": f"Segnale recente: {n.get('title','')}",
            }
        if any(_norm_search(k) in t for k in out_kw):
            return {
                "status": "⛔ OUT",
                "confidence": "ALTA",
                "reason": f"Segnale recente: {n.get('title','')}",
            }
        if any(_norm_search(k) in t for k in doubt_kw):
            return {
                "status": "⚠️ Dubbio",
                "confidence": "MEDIA",
                "reason": f"Segnale recente: {n.get('title','')}",
            }

    return {
        "status": "⚪ Da verificare",
        "confidence": "NESSUN SEGNALE ESPLICITO",
        "reason": "Le notizie recenti non contengono indicazioni chiare su disponibilità o infortunio.",
    }


def _title_weight(info):
    t = str(info.get("titolarita","DA VERIFICARE")).upper()
    if "ALTISSIMA" in t: return 26
    if t == "ALTA" or "TITOLARISS" in str(info.get("verdict","")).upper(): return 22
    if "MEDIO-ALTA" in t: return 15
    if t == "MEDIA": return 8
    if "BASSA" in t: return -8
    return 3


def _roster_row(player):
    ap = all_players()
    m = ap[(ap.Nome.astype(str)==str(player.get("name",""))) & (ap.Squadra.astype(str)==str(player.get("team","")))]
    if m.empty:
        m = ap[ap.Nome.astype(str)==str(player.get("name",""))]
    return None if m.empty else m.iloc[0]


def _lineup_score(player):
    row = _roster_row(player)
    fvm = float(player.get("fvm",0) or 0)
    if row is not None:
        info = player_intel(row)
        slot_data = slot_priority_advice(row, info)
        slot_txt = str(slot_data.get("slot", ""))
        mm = re.match(r"(\d+)", slot_txt)
        slot = int(mm.group(1)) if mm else SLOTS.get(str(row.Ruolo), 1)
        rank = int(slot_data.get("rank", 999) or 999)
        total = int(slot_data.get("total", 999) or 999)
        rank_bonus = 0 if total <= 1 else max(0, 35 * (1 - (rank-1)/(total-1)))
    else:
        info = {"titolarita":"DA VERIFICARE"}
        slot, rank, total, rank_bonus = 8, 999, 999, 0
    state = st.session_state.get("auto_player_status", {}).get(str(player.get("name","")), "⚪ Da verificare")
    status_penalty = -10000 if state == "⛔ OUT" else (-18 if state == "⚠️ Dubbio" else 0)
    return fvm + rank_bonus + _title_weight(info) + status_penalty, info, slot, rank, total, state


def recommended_lineups():
    # PRIORITÀ REGOLAMENTO FC JIGEN: il modificatore difesa richiede 4 difensori.
    # Per questo i moduli consigliati standard sono esclusivamente a linea difensiva a 4.
    formations = {
        "4-3-3": (4,3,3),
        "4-4-2": (4,4,2),
        "4-5-1": (4,5,1),
    }
    roster=[dict(x) for x in S.get("roster",[])]
    grouped={r:[] for r in ["POR","DIF","CEN","ATT"]}
    for p in roster:
        score, info, slot, rank, total, state = _lineup_score(p)
        grouped.setdefault(p.get("role"),[]).append((score,p,info,slot,rank,total,state))
    for r in grouped:
        grouped[r].sort(key=lambda x:x[0], reverse=True)
    results=[]
    for form,(nd,nc,na) in formations.items():
        need={"POR":1,"DIF":nd,"CEN":nc,"ATT":na}
        if any(len([x for x in grouped[r] if x[6] != "⛔ OUT"]) < n for r,n in need.items()):
            continue
        starters=[]; total_score=0
        for r,n in need.items():
            picks=[x for x in grouped[r] if x[6] != "⛔ OUT"][:n]
            starters.extend(picks); total_score += sum(x[0] for x in picks)
        doubts=sum(1 for x in starters if x[6]=="⚠️ Dubbio")
        unverified=sum(1 for x in starters if "VERIFIC" not in str(x[2].get("confidence","")).upper())
        results.append({
            "formation": form,
            "score": round(total_score, 1),
            "starters": starters,
            "doubts": doubts,
            "unverified": unverified,
            "modifier_active": nd == 4,
        })
    return sorted(results,key=lambda x:x["score"],reverse=True)[:3]


def render_rosa_status():
    fm_page(
        "🩺 Stato giocatori",
        "Stato operativo rigoroso, titolarità e notizie recenti dei tuoi 25 giocatori."
    )
    roster = [dict(x) for x in S.get("roster", [])]
    if not roster:
        st.info("Rosa vuota.")
        return

    names = [p["name"] for p in roster]
    pick = st.selectbox("Giocatore", names, key="rosa_status_player")
    p = next(x for x in roster if x["name"] == pick)
    row = _roster_row(p)

    info = player_intel(row) if row is not None else {
        "titolarita":"DA VERIFICARE", "confidence":"DA VERIFICARE", "summary":"Dati non disponibili."
    }
    score, _, slot, rank, total, _ = _lineup_score(p)

    c1, c2, c3 = st.columns(3)
    c1.metric("Slot", f"{slot}°")
    c2.metric("Rank ruolo", f"#{rank}/{total}")
    c3.metric("Gerarchia base", str(info.get("titolarita", "DA VERIFICARE")))
    st.caption(f"Affidabilità gerarchia base: {info.get('confidence','DA VERIFICARE')} • {info.get('summary','')}")

    st.markdown("### 🩺 Stato operativo")
    st.caption(
        "Lo stato NON viene dedotto dalle news. Usa Fantacalcio Infortunati/Indisponibili e Probabili formazioni. "
        "Se non c'è conferma sufficiente resta Da verificare."
    )

    if st.button("🔎 VERIFICA STATO OPERATIVO", width="stretch", key=f"op_{_norm_search(pick)}"):
        with st.spinner("Controllo fonti operative…"):
            op = fetch_fantacalcio_operational_status(pick, p.get("team", ""))
        st.session_state.setdefault("auto_player_status", {})[pick] = op["status"]
        st.session_state.setdefault("auto_player_status_detail", {})[pick] = op

    op = st.session_state.setdefault("auto_player_status_detail", {}).get(pick)
    if op is None:
        st.info("⚪ Da verificare • premi “Verifica stato operativo”.")
    else:
        status = op.get("status", "⚪ Da verificare")
        conf = op.get("confidence", "")
        if status == "✅ Disponibile":
            st.success(f"{status} • affidabilità {conf}")
        elif status == "⚠️ Dubbio":
            st.warning(f"{status} • affidabilità {conf}")
        elif status == "⛔ OUT":
            st.error(f"{status} • affidabilità {conf}")
        else:
            st.info(f"{status} • {conf}")
        st.caption(op.get("reason", ""))
        st.markdown(f"**Titolarità giornata:** {op.get('titolarita_live','DA VERIFICARE')}")
        if op.get("percentage") is not None:
            st.caption(f"Percentuale rilevata nelle probabili: {op['percentage']}%")
        for label, url in op.get("sources", []):
            st.markdown(f"[{label}]({url})")
        if op.get("errors"):
            st.caption("Una fonte non ha risposto: classificazione mantenuta conservativa.")

    st.markdown("### 📰 Ultime notizie sul giocatore")
    st.caption("Solo articoli degli ultimi 14 giorni. Le news sono informative e NON modificano lo stato operativo.")

    if st.button("🔄 AGGIORNA NOTIZIE", width="stretch", key=f"news_{_norm_search(pick)}"):
        with st.spinner("Cerco solo notizie recenti sul giocatore…"):
            news, err = fetch_player_news(pick, p.get("team", ""), 5, 14)
        st.session_state["news_result"] = {"player": pick, "items": news, "err": err}

    nr = st.session_state.get("news_result", {})
    if nr.get("player") == pick:
        if nr.get("err"):
            st.warning("Le notizie non sono disponibili in questo momento.")
        elif not nr.get("items"):
            st.info("Nessuna notizia recente specifica sul giocatore negli ultimi 14 giorni.")
        else:
            for n in nr["items"]:
                title = str(n.get("title", "")).replace("[", "［").replace("]", "］")
                link = n.get("link", "")
                source = n.get("source", "Fonte")
                date_label = n.get("pubLabel", "")
                if link:
                    st.markdown(f"**[{title}]({link})**")
                else:
                    st.markdown(f"**{title}**")
                st.caption(f"{source} • {date_label}")


def _pitch_player_name(name):
    """Nome compatto per la lavagnetta mobile."""
    name = str(name or "").strip()
    if len(name) <= 14:
        return name
    parts = name.split()
    if len(parts) > 1:
        compact = f"{parts[0]} {parts[-1][0]}."
        if len(compact) <= 14:
            return compact
    return name[:13] + "…"


def _pitch_status_class(state):
    state = str(state or "")
    if "OUT" in state:
        return "out"
    if "Dubbio" in state:
        return "doubt"
    if "Disponibile" in state:
        return "ok"
    return "unknown"


def _starter_probability(player, info=None):
    """Percentuale titolarità: live se disponibile, altrimenti stima marcata ~ solo da gerarchia verificata."""
    name = str(player.get("name", ""))
    detail = st.session_state.get("auto_player_status_detail", {}).get(name, {})
    pct = detail.get("percentage")
    try:
        if pct is not None:
            pct = max(0, min(100, int(pct)))
            return pct, False, "LIVE"
    except Exception:
        pass

    if info is None:
        row = _roster_row(player)
        info = player_intel(row) if row is not None else {}

    confidence = str(info.get("confidence", "")).upper()
    tit = str(info.get("titolarita", "")).upper()
    # Solo gerarchie esplicitamente verificate: la tilde indica che NON è una percentuale live.
    if "VERIFIC" in confidence:
        mapping = {
            "ALTISSIMA": 95,
            "ALTA": 85,
            "MEDIO-ALTA": 70,
            "MEDIA": 55,
            "BASSA": 30,
        }
        for key, value in mapping.items():
            if key in tit:
                return value, True, "GERARCHIA"
    return None, False, "N/D"


def _probability_label(player, info=None):
    pct, estimated, source = _starter_probability(player, info)
    if pct is None:
        return "Tit. N/D", "nd"
    prefix = "~" if estimated else ""
    cls = "high" if pct >= 75 else ("mid" if pct >= 50 else "low")
    return f"Tit. {prefix}{pct}%", cls


def _render_pitch_line(players, css_class):
    chips = []
    for score, p, info, slot, rank, total, state in players:
        safe_name = html.escape(_pitch_player_name(p.get("name", "")))
        safe_team = html.escape(str(p.get("team", "")))
        state_class = _pitch_status_class(state)
        prob_label, prob_class = _probability_label(p, info)
        chips.append(
            f'<div class="fm-pitch-player {state_class}">'
            f'<div class="fm-shirt">●</div>'
            f'<div class="fm-pitch-name">{safe_name}</div>'
            f'<div class="fm-pitch-prob {prob_class}">{html.escape(prob_label)}</div>'
            f'<div class="fm-pitch-team">{safe_team}</div>'
            f'</div>'
        )
    return f'<div class="fm-pitch-line {css_class}">' + "".join(chips) + '</div>'


def render_lineup_advisor():
    fm_page(
        "🧩 Formazione giornata",
        "I 3 moduli consigliati mantengono sempre 4 difensori per attivare il modificatore."
    )

    # Appena entri: una sola lettura delle probabili aggiorna le % di tutti i 25 giocatori.
    with st.spinner("Aggiorno le titolarità della giornata…"):
        lineup_err = preload_roster_lineup_live()
    if lineup_err:
        st.caption("⚠️ Probabili momentaneamente non raggiungibili: mostro solo dati già verificati / N/D.")
    else:
        st.caption("✅ Titolarità giornata aggiornata automaticamente • cache 10 min")

    results = recommended_lineups()
    if not results:
        st.warning("Non ci sono abbastanza giocatori disponibili per costruire una formazione con 4 difensori e modificatore attivo. Controlla gli OUT/dubbi in difesa.")
        return

    result_map = {r["formation"]: r for r in results}
    options = list(result_map.keys())
    selected = st.segmented_control(
        "Modulo consigliato",
        options,
        default=options[0],
        key="lineup_formation_pick",
        label_visibility="collapsed",
    )
    if selected not in result_map:
        selected = options[0]
    res = result_map[selected]

    # Riepilogo rapido del modulo selezionato.
    m1, m2, m3 = st.columns(3)
    m1.metric("Modulo", res["formation"])
    m2.metric("Indice XI", f'{res["score"]:.0f}')
    m3.metric("Dubbi", res["doubts"])
    if res.get("modifier_active"):
        st.success("🛡️ Modificatore difesa ATTIVO — linea a 4")
    else:
        st.warning("⚠️ Modificatore difesa NON attivo")

    starters = res["starters"]
    by_role = {"POR": [], "DIF": [], "CEN": [], "ATT": []}
    for item in starters:
        by_role.setdefault(item[1].get("role"), []).append(item)

    # CSS lavagnetta: responsive e senza immagini esterne.
    st.markdown("""
    <style>
    .fm-pitch-wrap{
        margin:.55rem 0 .8rem;
        border:2px solid rgba(245,226,164,.75);
        border-radius:22px;
        overflow:hidden;
        box-shadow:0 8px 24px rgba(0,0,0,.18);
        background:#176b45;
    }
    .fm-pitch{
        position:relative;
        min-height:640px;
        padding:24px 10px 20px;
        display:flex;
        flex-direction:column;
        justify-content:space-between;
        background:
          linear-gradient(rgba(255,255,255,.08),rgba(255,255,255,.08)),
          repeating-linear-gradient(0deg,#176b45 0,#176b45 78px,#1b744b 78px,#1b744b 156px);
    }
    .fm-pitch:before{
        content:"";position:absolute;inset:12px;border:2px solid rgba(255,255,255,.78);border-radius:4px;pointer-events:none
    }
    .fm-pitch:after{
        content:"";position:absolute;left:50%;top:50%;width:92px;height:92px;
        border:2px solid rgba(255,255,255,.78);border-radius:50%;transform:translate(-50%,-50%);pointer-events:none
    }
    .fm-halfway{position:absolute;left:12px;right:12px;top:50%;border-top:2px solid rgba(255,255,255,.78)}
    .fm-box-top,.fm-box-bottom{position:absolute;left:25%;right:25%;height:74px;border:2px solid rgba(255,255,255,.78)}
    .fm-box-top{top:12px;border-top:0}.fm-box-bottom{bottom:12px;border-bottom:0}
    .fm-pitch-line{position:relative;z-index:3;display:flex;justify-content:space-evenly;align-items:center;gap:4px;width:100%;min-height:112px}
    .fm-pitch-player{width:78px;text-align:center;color:#fff;text-shadow:0 1px 2px rgba(0,0,0,.75)}
    .fm-shirt{width:42px;height:42px;display:flex;align-items:center;justify-content:center;margin:0 auto 4px;border-radius:50%;
        background:#f5e2a4;color:#0b2d24;border:2px solid #fff;font-size:1.1rem;box-shadow:0 3px 8px rgba(0,0,0,.28)}
    .fm-pitch-player.doubt .fm-shirt{background:#f3b64b}.fm-pitch-player.out .fm-shirt{background:#e75c55}.fm-pitch-player.unknown .fm-shirt{background:#d8ddd9}
    .fm-pitch-name{font-size:.72rem;font-weight:950;line-height:1.05;white-space:normal;word-break:break-word}
    .fm-pitch-team{font-size:.54rem;opacity:.86;margin-top:2px}
.fm-pitch-prob{display:inline-block;margin-top:3px;padding:2px 5px;border-radius:999px;font-size:.54rem;font-weight:950;background:rgba(0,0,0,.28);color:#fff}.fm-pitch-prob.high{background:#176d47}.fm-pitch-prob.mid{background:#9a6b10}.fm-pitch-prob.low{background:#9b342f}.fm-pitch-prob.nd{background:#59625d}
    .fm-pitch-legend{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;padding:8px 10px;background:#0d3f30;color:#e8eee9;font-size:.68rem}
    @media(max-width:700px){
      .fm-pitch{min-height:565px;padding:18px 4px 16px}.fm-pitch-line{min-height:96px;gap:1px}
      .fm-pitch-player{width:62px}.fm-shirt{width:35px;height:35px;font-size:.95rem}
      .fm-pitch-name{font-size:.63rem}.fm-pitch-prob{font-size:.48rem;padding:2px 4px}.fm-pitch-team{font-size:.48rem}
      .fm-pitch:after{width:76px;height:76px}.fm-box-top,.fm-box-bottom{height:62px}
    }
    </style>
    """, unsafe_allow_html=True)

    pitch_html = (
        '<div class="fm-pitch-wrap"><div class="fm-pitch">'
        '<div class="fm-halfway"></div><div class="fm-box-top"></div><div class="fm-box-bottom"></div>'
        + _render_pitch_line(by_role["ATT"], "attack")
        + _render_pitch_line(by_role["CEN"], "midfield")
        + _render_pitch_line(by_role["DIF"], "defence")
        + _render_pitch_line(by_role["POR"], "goalkeeper")
        + '</div><div class="fm-pitch-legend">'
          '<span>🟡 Disponibile</span><span>🟠 Dubbio</span><span>⚪ Da verificare</span>'
          '</div></div>'
    )
    st.markdown(pitch_html, unsafe_allow_html=True)

    if res["doubts"]:
        st.warning(f"⚠️ {res['doubts']} giocatore/i in dubbio nell’XI selezionato.")
    if res["unverified"]:
        st.caption(f"⚪ {res['unverified']} gerarchie/titolarità ancora da verificare.")

    # Panchina: tutti i non titolari, divisi per reparto e con titolarità %.
    starter_names = {str(x[1].get("name", "")) for x in starters}
    bench_by_role = {"POR": [], "DIF": [], "CEN": [], "ATT": []}
    for p in [dict(x) for x in S.get("roster", [])]:
        if str(p.get("name", "")) in starter_names:
            continue
        score, info, slot, rank, total, state = _lineup_score(p)
        if state != "⛔ OUT":
            bench_by_role.setdefault(str(p.get("role", "")), []).append((score, p, info, slot, state))
    for role in bench_by_role:
        bench_by_role[role].sort(key=lambda x: x[0], reverse=True)

    with st.expander("🪑 Panchina per reparto", expanded=True):
        role_labels = {"POR":"🧤 Portieri", "DIF":"🛡️ Difensori", "CEN":"⚙️ Centrocampisti", "ATT":"🎯 Attaccanti"}
        any_bench = False
        for role in ["POR", "DIF", "CEN", "ATT"]:
            players = bench_by_role.get(role, [])
            if not players:
                continue
            any_bench = True
            st.markdown(f"#### {role_labels[role]}")
            for _, p, info, slot, state in players:
                pct, estimated, src = _starter_probability(p, info)
                pct_txt = "N/D" if pct is None else (("~" if estimated else "") + f"{pct}%")
                status_txt = state if state else "⚪ Da verificare"
                st.markdown(
                    f"**{p.get('name','')}** · {p.get('team','')}  \n"
                    f"Titolarità **{pct_txt}** · {status_txt} · {slot}° slot"
                )
        if not any_bench:
            st.caption("Nessun altro giocatore disponibile.")

    st.caption("% senza ~ = rilevata dalle probabili. % con ~ = stima da gerarchia verificata. N/D = dato non sufficientemente verificato.")


def render_rosa():
    """Rosa separata dalla Dashboard: elenco completo e riepilogo per ruolo."""
    fm_page("👕 Rosa FC Jigen", "La squadra completa, separata dalla Dashboard centrale.")
    roster=list(S.get("roster", []))
    if not roster:
        st.markdown('<div class="fm-empty">👕 La rosa è ancora vuota.</div>', unsafe_allow_html=True)
        return
    rdf=pd.DataFrame(roster).rename(columns={"name":"Nome","role":"Ruolo","team":"Squadra","fvm":"FVM","price":"Prezzo"})
    for col in ["FVM","Prezzo"]:
        if col not in rdf.columns: rdf[col]=0
        rdf[col]=pd.to_numeric(rdf[col],errors="coerce").fillna(0).astype(int)
    def _v(name,field,default=""):
        return VALUATION_BY_NAME.get(str(name),{}).get(field,default)
    rdf["Slot"]=rdf["Nome"].map(lambda n:_v(n,"SlotLega10",""))
    rdf["Titolarità"]=rdf["Nome"].map(lambda n:_v(n,"Titolarita","DA VERIFICARE"))
    rdf["Affidabilità"]=rdf["Nome"].map(lambda n:_v(n,"Affidabilita","DA VERIFICARE"))
    rdf["RankRuolo"]=rdf["Nome"].map(lambda n:_v(n,"RankRuolo",999))
    rdf["TotRuolo"]=rdf["Nome"].map(lambda n:_v(n,"TotRuolo",1))
    rdf["RankRuolo"]=pd.to_numeric(rdf["RankRuolo"],errors="coerce").fillna(999).astype(int)
    rdf["TotRuolo"]=pd.to_numeric(rdf["TotRuolo"],errors="coerce").fillna(1).clip(lower=1).astype(int)
    rdf["Forza"]=((1-((rdf["RankRuolo"]-1)/rdf["TotRuolo"]))*100).clip(0,100).round().astype(int)
    c1,c2,c3,c4=st.columns(4)
    for col,role in zip((c1,c2,c3,c4),("POR","DIF","CEN","ATT")):
        sub=rdf[rdf["Ruolo"].eq(role)]
        col.metric(role,f"{len(sub)}/{SLOTS[role]}",f"{int(sub['Prezzo'].sum()) if not sub.empty else 0} cr")
    role_order={"POR":0,"DIF":1,"CEN":2,"ATT":3}
    rdf["_ord"]=rdf["Ruolo"].map(role_order).fillna(9)
    rdf=rdf.sort_values(["_ord","Forza"],ascending=[True,False]).drop(columns=["_ord"])
    st.dataframe(rdf[["Nome","Ruolo","Squadra","Prezzo","FVM","Slot","Forza","Titolarità","Affidabilità"]],hide_index=True,width="stretch")
    st.download_button("⬇️ ESPORTA ROSA CSV",rdf.to_csv(index=False).encode(),file_name="rosa_fc_jigen_post_asta.csv",mime="text/csv",width="stretch")

def render_piano():
    fm_page("🎯 Piano Asta", "Budget per ruolo, target, alternative e gestione degli arrivi dell’ultimo minuto.")
    st.caption("Snapshot 01/09/2026 • modifiche salvate nel Cloud")

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
    if st.button("💾 SALVA BUDGET",width="stretch"):
        S["plan_budget"]={r:int(bp[r]) for r in bp}
        persist();st.success("Budget salvato nel Cloud")

    st.divider()
    cplan1,cplan2=st.columns(2)
    with cplan1:
        if st.button("⚡ CARICA PIANO FC JIGEN",type="primary",width="stretch"):
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
        if st.button("✅ AGGIUNGI AL LISTONE",width="stretch",key="add_deadline_player"):
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
            cdf,hide_index=True,width="stretch",
            disabled=["Nome","Ruolo","Squadra","Qt.A","FVM","Inserito"],
            column_order=["Nome","Ruolo","Squadra","Qt.A","FVM","Elimina"],
            column_config={"Elimina":st.column_config.CheckboxColumn("Elimina")},
            key="deadline_editor"
        )
        if st.button("🗑️ SALVA ELIMINAZIONI",width="stretch",key="delete_deadline_players"):
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
    if t and st.button("➕ SALVA TARGET",width="stretch"):
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
            width="stretch",
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
        if st.button("💾 SALVA MODIFICHE TARGET",type="primary",width="stretch"):
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
                         hide_index=True,width="stretch")
    else:
        st.info("Nessun target. Premi “CARICA PIANO FC JIGEN” oppure aggiungili manualmente.")

def render_scommesse():
    fm_page("🎲 Scommesse", "Profili low cost e upside da prendere soltanto quando il prezzo crea valore.")
    st.caption("IDEALE e STOP qui sono dedicati alla scommessa e non sostituiscono il Piano principale.")
    role_bet=st.segmented_control("Ruolo scommesse",["TUTTI","POR","DIF","CEN","ATT"],default="TUTTI",key="bet_role")
    ap=all_players()
    bets=[]
    bet_keywords = ("SCOMMESS", "LOW COST", "UPSIDE")
    for name,info in PLAYER_INTEL.items():
        bet_text = " ".join([
            str(info.get("tag","")),
            str(info.get("verdict","")),
            str(info.get("summary",""))
        ]).upper()
        if not any(k in bet_text for k in bet_keywords):
            continue
        mm=ap[ap["Nome"].astype(str)==name]
        if mm.empty:
            continue
        rr=mm.iloc[0]
        if role_bet!="TUTTI" and rr.Ruolo!=role_bet:
            continue
        bets.append({
            "Nome":rr.Nome,"R":rr.Ruolo,"Squadra":rr.Squadra,"FVM":int(rr.FVM),
            "Tipo":info.get("tag",""),"Titolarità":info.get("titolarita",""),
            "Rischio":info.get("risk",""),"Ideale":info.get("ideal",""),
            "STOP":info.get("stop",""),"Giudizio":info.get("verdict","")
        })
    if bets:
        bdf=pd.DataFrame(bets)
        st.dataframe(bdf,hide_index=True,width="stretch")
        pick=st.selectbox("Analizza scommessa",["—"]+[x["Nome"] for x in bets],key="bet_pick")
        if pick!="—":
            rr=ap[ap["Nome"].astype(str)==pick].iloc[0]
            st.markdown(f"### {rr.Nome}")
            st.caption(f"{rr.Ruolo} • {rr.Squadra} • FVM {int(rr.FVM)}")
            render_player_intel(rr)
    else:
        st.info("Nessuna scommessa in questo filtro.")

def render_storico():
    fm_page("📈 Storico", "Tutte le operazioni dell’asta. Puoi correggere errori senza perdere la coerenza dello stato.")

    st.caption("Gestione movimenti: correggi o elimina una voce per errori, scambi o rettifiche post-asta.")

    moves_hist = list(S.get("moves", []))
    if moves_hist:
        hist_labels = []
        for i, m in enumerate(moves_hist):
            hist_labels.append(
                f"{i+1}. {m.get('name','?')} • {m.get('buyer','-')} • "
                f"{int(m.get('price',0) or 0)} cr • {m.get('action','?')}"
            )

        edit_idx = st.selectbox(
            "✏️ Movimento da modificare",
            range(len(hist_labels)),
            format_func=lambda i: hist_labels[i],
            key="history_edit_idx"
        )
        selected_move = dict(moves_hist[edit_idx])
        is_unsold = selected_move.get("action") == "INV"

        if is_unsold:
            st.info("Questo movimento è INVENDUTO: puoi eliminarlo per rimettere il giocatore sul mercato.")
        else:
            teams_hist = ["FC Jigen"] + RIVALS + ["NON TRACCIATO"]
            current_buyer = selected_move.get("buyer","NON TRACCIATO")
            if current_buyer not in teams_hist:
                current_buyer = "NON TRACCIATO"

            h1,h2 = st.columns(2)
            with h1:
                new_buyer_hist = st.selectbox(
                    "Nuova squadra",
                    teams_hist,
                    index=teams_hist.index(current_buyer),
                    key="history_new_buyer"
                )
            with h2:
                new_price_hist = st.number_input(
                    "Nuovo prezzo",
                    min_value=1,
                    step=1,
                    value=max(1,int(selected_move.get("price",1) or 1)),
                    key="history_new_price"
                )

        st.warning("⚠️ La modifica ricalcola automaticamente crediti, rosa, rivali e giocatori usciti.")

        hc1,hc2 = st.columns(2)
        with hc1:
            if not is_unsold and st.button("💾 SALVA MODIFICA",width="stretch",key="history_save_edit"):
                edited_moves = [dict(x) for x in moves_hist]
                edited_moves[edit_idx]["buyer"] = new_buyer_hist
                edited_moves[edit_idx]["price"] = int(new_price_hist)
                edited_moves[edit_idx]["action"] = "MIO" if new_buyer_hist=="FC Jigen" else "ALTRI"
                errs = rebuild_from_moves(edited_moves)
                if errs:
                    st.error("⛔ Modifica annullata: "+" | ".join(errs[:3]))
                else:
                    persist()
                    st.success("✅ Movimento modificato e stato ricalcolato.")
                    st.rerun()

        with hc2:
            if st.button("🗑️ ELIMINA MOVIMENTO",width="stretch",key="history_delete_move"):
                kept = [dict(x) for j,x in enumerate(moves_hist) if j != edit_idx]
                errs = rebuild_from_moves(kept)
                if errs:
                    st.error("⛔ Eliminazione annullata: "+" | ".join(errs[:3]))
                else:
                    persist()
                    st.success("✅ Movimento eliminato. Giocatore di nuovo disponibile se necessario.")
                    st.rerun()
    else:
        st.info("Storico vuoto: nessun movimento da modificare.")


    if S["moves"]:
        h=pd.DataFrame(S["moves"])
        st.dataframe(h.iloc[::-1],hide_index=True,width="stretch")
        st.download_button("⬇️ Storico CSV",h.to_csv(index=False).encode(),file_name="storico_asta.csv",mime="text/csv")
        st.caption(f"{len(h)} operazioni • indice mercato {market_index():.2f}x")
    else:st.info("Storico vuoto.")




# v3.35.3 — Tre mondi principali separati: Dashboard, Rosa, Asta.
main_area = st.segmented_control(
    "Mondo principale", ["📊 Dashboard", "👕 Rosa", "🔥 Asta"],
    default="📊 Dashboard", key="fm_main_nav", label_visibility="collapsed"
)
if main_area not in ["📊 Dashboard", "👕 Rosa", "🔥 Asta"]:
    main_area = "📊 Dashboard"

if main_area == "🔥 Asta":
    render_asta()
elif main_area == "👕 Rosa":
    rosa_nav = st.segmented_control(
        "Rosa", ["👕 Panoramica", "🩺 Stato", "🧩 Formazione"],
        default="👕 Panoramica", key="fm_rosa_nav", label_visibility="collapsed"
    )
    if rosa_nav == "🩺 Stato": render_rosa_status()
    elif rosa_nav == "🧩 Formazione": render_lineup_advisor()
    else: render_rosa()
else:
    dash_nav = st.segmented_control(
        "Dashboard", ["📊 Centrale", "👥 Rivali", "••• Altro"],
        default="📊 Centrale", key="fm_dashboard_nav", label_visibility="collapsed"
    )
    if dash_nav == "👥 Rivali":
        render_rivali()
    elif dash_nav == "••• Altro":
        fm_page("＋ Altri strumenti", "Approfondimenti e gestione avanzata.")
        extra = st.segmented_control(
            "Strumento", ["📡 Radar","🎯 Piano","🎲 Scommesse","📈 Storico"],
            default="📡 Radar", key="fm_extra_tool_v334", label_visibility="collapsed"
        )
        if extra == "📡 Radar": render_radar()
        elif extra == "🎯 Piano": render_piano()
        elif extra == "🎲 Scommesse": render_scommesse()
        else: render_storico()
    else:
        render_dashboard()
