from fanta_core import *
from fanta_core import _quick_price, _reset_live_price, _quick_cloud_save, _quick_undo

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



fm_page("＋ Altri strumenti", "Approfondimenti e gestione avanzata.")
extra = st.segmented_control(
    "Strumento",
    ["📡 Radar", "🎯 Piano", "🎲 Scommesse", "📈 Storico"],
    default="📡 Radar",
    key="fm_extra_tool_mp",
    label_visibility="collapsed",
)
if extra == "📡 Radar":
    render_radar()
elif extra == "🎯 Piano":
    render_piano()
elif extra == "🎲 Scommesse":
    render_scommesse()
else:
    render_storico()
