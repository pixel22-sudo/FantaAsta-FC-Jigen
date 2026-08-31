# 8. SEZIONE TARGET MIGLIORI GIOCATORI RIMANENTI (CHEAT SHEET)
st.divider()
st.subheader("🎯 Target Migliori Giocatori Rimanenti (Fantachill 5.0)")
st.caption("Spunta i giocatori man mano che vengono acquistati per tenere a vista i migliori ancora liberi.")

TARGET_GIOCATORI = {
    "🧤 PORTIERI (Focus Modificatore / Clean Sheet)": [
        "Maignan / Blocco Milan",
        "Josep Martínez / Blocco Inter",
        "Vicario / Blocco Juve",
        "Meret (Napoli - Ottimo qualità/prezzo)",
        "Svilar (Roma)",
        "Carnesecchi (Atalanta)"
    ],
    "🛡️ DIFENSORI (Focus Voto da Modificatore & Bonus)": [
        "Dimarco (Inter - Super Top)",
        "Bremer (Juventus)",
        "Wesley (Roma - Spinta)",
        "Akanji (Inter)",
        "Solet (Udinese - Media voto alta)",
        "Mancini (Roma)",
        "Ostigard (Genoa - Vizio del gol)",
        "Chalobah / Kempf (Como)",
        "Di Lorenzo (Napoli)"
    ],
    "⚙️ CENTROCAMPISTI (Rigoristi & Inserimenti)": [
        "Hakan Calhanoglu (Inter - Rigorista)",
        "Scott McTominay (Napoli)",
        "Nico Paz (Como)",
        "Riccardo Orsolini (Bologna)",
        "Christian Pulisic (Milan)",
        "Arthur Atta (Fiorentina)",
        "Davide Frattesi (Lazio)"
    ],
    "⚽ ATTACCANTI (Bomber & Titolari Doppia Cifra)": [
        "Lautaro Martinez (Inter - Top)",
        "Donyell Malen (Roma)",
        "Gonçalo Ramos (Milan)",
        "Rasmus Hojlund (Napoli)",
        "Kenan Yildiz (Juventus)",
        "Artem Dovbyk (Bologna)",
        "Randal Kolo Muani (Juventus)",
        "Keinan Davis (Udinese - Rigorista)"
    ]
}

# Griglia interattiva con Checkbox
col_t1, col_t2 = st.columns(2)

keys_target = list(TARGET_GIOCATORI.keys())

with col_t1:
    for cat in keys_target[:2]:
        st.write(f"**{cat}**")
        for g in TARGET_GIOCATORI[cat]:
            st.checkbox(g, key=f"target_{g}")

with col_t2:
    for cat in keys_target[2:]:
        st.write(f"**{cat}**")
        for g in TARGET_GIOCATORI[cat]:
            st.checkbox(g, key=f"target_{g}")
