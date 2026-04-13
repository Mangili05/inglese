import streamlit as st
import sqlite3
from deep_translator import GoogleTranslator
from datetime import datetime
import pandas as pd

# Configurazione Pagina per Mobile
st.set_page_config(page_title="Il Mio Diario Inglese", page_icon="🇬🇧")

# --- FUNZIONI DATABASE ---
def init_db():
    conn = sqlite3.connect('diario_voci.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS dizionario 
                 (inglese TEXT, italiano TEXT, data TEXT)''')
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- INTERFACCIA APP ---
st.title("🇬🇧 Diario di Inglese")
st.subheader("Traduci e salva nuove parole")

# Campo di inserimento
parola_input = st.text_input("Inserisci parola o frase in Inglese:").strip()

if st.button("Traduci e Salva"):
    if parola_input:
        try:
            # Traduzione
            traduzione = GoogleTranslator(source='en', target='it').translate(parola_input)
            data_oggi = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            # Salvataggio nel Database
            c.execute("INSERT INTO dizionario (inglese, italiano, data) VALUES (?, ?, ?)",
                      (parola_input, traduzione, data_oggi))
            conn.commit()
            
            st.success(f"Aggiunto: **{parola_input}** = **{traduzione}**")
        except Exception as e:
            st.error(f"Errore durante la traduzione: {e}")
    else:
        st.warning("Per favore, scrivi qualcosa!")

st.divider()

# --- VISUALIZZAZIONE DIARIO ---
st.subheader("📚 Le mie parole")

# Carichiamo i dati dal DB per mostrarli
data = pd.read_sql_query("SELECT inglese, italiano, data FROM dizionario ORDER BY rowid DESC", conn)

if not data.empty:
    # Mostra una tabella pulita
    st.dataframe(data, use_container_width=True, hide_index=True)
    
    # Pulsante per scaricare i dati (opzionale)
    st.download_button("Scarica Diario (CSV)", data.to_csv(index=False), "mio_diario.csv", "text/csv")
else:
    st.info("Il tuo diario è ancora vuoto. Inizia aggiungendo una parola!")
