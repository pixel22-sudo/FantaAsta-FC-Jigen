import os
import tkinter as tk
from tkinter import ttk, messagebox

# 1. CARICAMENTO LISTA GIOCATORI DA FILE TXT ESTERNO
def carica_giocatori():
    percorso_file = os.path.expanduser("~/Desktop/giocatori.txt")
    if os.path.exists(percorso_file):
        with open(percorso_file, "r", encoding="utf-8") as f:
            linee = [riga.strip() for riga in f.readlines() if riga.strip()]
            return sorted(list(set(linee)))
    else:
        # Lista di riserva se il file non è presente
        return sorted([
            "Maignan", "Sommer", "Svilar", "Di Gregorio", "Meret", "Provedel",
            "Dimarco", "Bremer", "Bastoni", "Di Lorenzo", "Akanji", "Ndicka",
            "Calhanoglu", "Pulisic", "McTominay", "Barella", "Nico Paz", "Orsolini",
            "Lautaro Martinez", "Thuram M.", "Yildiz", "Hojlund", "Malen", "Dovbyk"
        ])

LISTA_GIOCATORI = carica_giocatori()

class FantaAstaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FantaAsta 2026/2027 - Live Manager Offline")
        self.root.geometry("620x680")

        self.budget_iniziale = 1000
        self.crediti_rimasti = 1000
        self.storico_acquisti = []

        # --- GRAPHICAL INTERFACE ---
        self.lbl_crediti = tk.Label(
            root, 
            text=f"Crediti Fc jigen: {self.crediti_rimasti} / {self.budget_iniziale}", 
            font=("Arial", 16, "bold"), 
            fg="#1e7e34"
        )
        self.lbl_crediti.pack(pady=10)

        # Frame Inserimento
        frame_input = tk.LabelFrame(root, text=" Registra Acquisto Completo ", font=("Arial", 11, "bold"), padx=10, pady=10)
        frame_input.pack(fill="x", padx=15, pady=5)

        # Autocompletamento Giocatore
        tk.Label(frame_input, text="Giocatore:").grid(row=0, column=0, sticky="w", pady=5)
        self.combo_giocatore = ttk.Combobox(frame_input, values=LISTA_GIOCATORI, font=("Arial", 11), width=28)
        self.combo_giocatore.grid(row=0, column=1, pady=5, padx=5)
        self.combo_giocatore.bind("<KeyRelease>", self.filtra_giocatori)

        # Prezzo d'acquisto
        tk.Label(frame_input, text="Prezzo (cr):").grid(row=1, column=0, sticky="w", pady=5)
        self.ent_prezzo = tk.Entry(frame_input, font=("Arial", 11), width=10)
        self.ent_prezzo.grid(row=1, column=1, sticky="w", pady=5, padx=5)

        # Pulsanti Azione
        btn_conferma = tk.Button(
            frame_input, text="📌 CONFERMA ACQUISTO", bg="#28a745", fg="white", 
            font=("Arial", 10, "bold"), command=self.registra_acquisto
        )
        btn_conferma.grid(row=2, column=0, columnspan=2, pady=10, sticky="we")

        # Indicatore Sbarramento / PMR
        self.lbl_sbarramento = tk.Label(root, text="Prezzo Medio Rimanente (25 slot): 40 cr/slot", font=("Arial", 11, "italic"), fg="#0056b3")
        self.lbl_sbarramento.pack(pady=5)

        # Storico Acquisti
        frame_storico = tk.LabelFrame(root, text=" Rosa Fc jigen (Acquistati) ", font=("Arial", 11, "bold"), padx=10, pady=10)
        frame_storico.pack(fill="both", expand=True, padx=15, pady=10)

        self.listbox_storico = tk.Listbox(frame_storico, font=("Courier", 10))
        self.listbox_storico.pack(fill="both", expand=True)

    def filtra_giocatori(self, event):
        testo = self.combo_giocatore.get().lower()
        if not testo:
            self.combo_giocatore['values'] = LISTA_GIOCATORI
        else:
            filtrati = [g for g in LISTA_GIOCATORI if testo in g.lower()]
            self.combo_giocatore['values'] = filtrati

    def registra_acquisto(self):
        nome = self.combo_giocatore.get().strip()
        prezzo_str = self.ent_prezzo.get().strip()

        if not nome or not prezzo_str.isdigit():
            messagebox.showerror("Errore Input", "Inserisci un nome valido e un prezzo numerico.")
            return

        prezzo = int(prezzo_str)

        if prezzo > self.crediti_rimasti:
            messagebox.showwarning("Budget Superato", "Non hai abbastanza crediti per completare l'operazione!")
            return

        self.crediti_rimasti -= prezzo
        self.storico_acquisti.append((nome, prezzo))

        # Aggiornamento UI
        self.lbl_crediti.config(text=f"Crediti Fc jigen: {self.crediti_rimasti} / {self.budget_iniziale}")
        self.listbox_storico.insert(tk.END, f"{nome:<28} - {prezzo} cr")

        # Calcolo dinamico slot e PMR
        slot_occupati = len(self.storico_acquisti)
        slot_rimanenti = max(1, 25 - slot_occupati)
        pmr = round(self.crediti_rimasti / slot_rimanenti, 1)
        self.lbl_sbarramento.config(text=f"PMR per i rimanenti {slot_rimanenti} slot: {pmr} cr/slot")

        # Reset campo di input
        self.combo_giocatore.set("")
        self.combo_giocatore['values'] = LISTA_GIOCATORI
        self.ent_prezzo.delete(0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = FantaAstaApp(root)
    root.mainloop()
