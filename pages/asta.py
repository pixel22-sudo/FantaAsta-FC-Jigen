from fanta_core import *
from fanta_core import _quick_price, _reset_live_price, _quick_cloud_save, _quick_undo

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

    labels=[player_fast_label(r) for _,r in av.iterrows()]
    choice=st.selectbox(
        "🔎 Cerca / scegli giocatore",
        labels,
        index=None,
        placeholder="Scrivi Lautaro, Nico Paz, Dimarco...",
        key="asta_live_player"
    )

    row=None
    if choice:
        row=av.iloc[labels.index(choice)]
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


render_asta()
