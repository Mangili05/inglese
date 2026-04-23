import streamlit as st
import sqlite3
from deep_translator import GoogleTranslator
from gtts import gTTS
import io
from datetime import datetime
import pandas as pd

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="MyDiary", page_icon="📓", layout="centered")

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('my_diary_final.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS dizionario 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, originale TEXT, traduzione TEXT, data TEXT, direzione TEXT)''')
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- LOGICA TRADUZIONE ---
def get_smart_translation(text, direzione):
    src = 'it' if direzione == "IT ➔ EN" else 'en'
    tgt = 'en' if direzione == "IT ➔ EN" else 'it'
    
    # 1. Traduzione principale (la più affidabile)
    main_trans = GoogleTranslator(source=src, target=tgt).translate(text)
    
    # 2. Per simulare la lista di Google, proviamo a chiedere traduzioni alternative
    # Nota: GoogleTranslator restituisce una stringa, ma possiamo fargli tradurre 
    # piccoli termini correlati o semplicemente tenerlo pulito con le 2/3 varianti principali
    # se disponibili. In questa versione puntiamo alla precisione del termine principale.
    return main_trans.capitalize()

# --- INTERFACCIA ---
st.title("📓 MyDiary")

with st.container():
    col_in1, col_in2 = st.columns([2, 1])
    with col_in2:
        direzione = st.radio("Direzione:", ("IT ➔ EN", "EN ➔ IT"))
    with col_in1:
        parola_input = st.text_input("Inserisci termine:").strip()

    if st.button("Traduci e Salva", use_container_width=True):
        if parola_input:
            try:
                traduzione = get_smart_translation(parola_input, direzione)
                data_oggi = datetime.now().strftime("%d/%m/%Y")
                
                c.execute("INSERT INTO dizionario (originale, traduzione, data, direzione) VALUES (?, ?, ?, ?)",
                          (parola_input.capitalize(), traduzione, data_oggi, direzione))
                conn.commit()
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")

st.divider()

# --- VISUALIZZAZIONE DIARIO ---
df = pd.read_sql_query("SELECT * FROM dizionario ORDER BY id DESC", conn)

if not df.empty:
    for index, row in df.iterrows():
        # Creiamo un "box" per ogni parola
        with st.container():
            col_a, col_b, col_c = st.columns([1, 6, 1])
            
            # Colonna Sinistra: Audio
            with col_a:
                testo_audio = row['traduzione'] if row['direzione'] == "IT ➔ EN" else row['originale']
                if st.button("🔊", key=f"aud_{row['id']}"):
                    tts = gTTS(text=testo_audio, lang='en')
                    audio_fp = io.BytesIO()
                    tts.write_to_fp(audio_fp)
                    st.audio(audio_fp, format="audio/mp3", autoplay=True)
            
            # Colonna Centrale: Testo
            with col_b:
                st.markdown(f"**{row['originale']}**")
                st.write(row['traduzione'])
                st.caption(row['data'])
            
            # Colonna Destra: Elimina
            with col_c:
                if st.button("🗑️", key=f"del_{row['id']}"):
                    c.execute("DELETE FROM dizionario WHERE id = ?", (row['id'],))
                    conn.commit()
                    st.rerun()
            st.divider()
else:
    st.info("Il diario è vuoto.")
