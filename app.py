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
    conn = sqlite3.connect('my_diary_simple.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS dizionario 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, originale TEXT, traduzione TEXT, data TEXT, direzione TEXT)''')
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- FUNZIONE AUDIO ---
def get_tts_audio(text):
    tts = gTTS(text=text, lang='en')
    audio_stream = io.BytesIO()
    tts.write_to_fp(audio_stream)
    return audio_stream.getvalue()

# --- INTERFACCIA ---
st.title("📓 MyDiary")

with st.container():
    col_in1, col_in2 = st.columns([2, 1])
    with col_in2:
        direzione = st.radio("Direzione:", ("IT ➔ EN", "EN ➔ IT"))
    with col_in1:
        parola_input = st.text_input("Inserisci parola:").strip()

    if st.button("Traduci e Salva", use_container_width=True):
        if parola_input:
            try:
                src = 'it' if direzione == "IT ➔ EN" else 'en'
                tgt = 'en' if direzione == "IT ➔ EN" else 'it'
                
                traduzione = GoogleTranslator(source=src, target=tgt).translate(parola_input)
                data_oggi = datetime.now().strftime("%d/%m/%Y")
                
                c.execute("INSERT INTO dizionario (originale, traduzione, data, direzione) VALUES (?, ?, ?, ?)",
                          (parola_input.capitalize(), traduzione.capitalize(), data_oggi, direzione))
                conn.commit()
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")

st.divider()

# --- VISUALIZZAZIONE DIARIO ---
audio_placeholder = st.empty()
df = pd.read_sql_query("SELECT * FROM dizionario ORDER BY id DESC", conn)

if not df.empty:
    for index, row in df.iterrows():
        with st.container():
            c1, c2, c3 = st.columns([1, 6, 1])
            
            with c1:
                # L'audio legge sempre la parte inglese
                testo_audio = row['traduzione'] if row['direzione'] == "IT ➔ EN" else row['originale']
                if st.button("🔊", key=f"aud_{row['id']}"):
                    audio_bytes = get_tts_audio(testo_audio)
                    audio_placeholder.audio(audio_bytes, format="audio/mp3", autoplay=True)
            
            with c2:
                st.markdown(f"**{row['originale']}** \n{row['traduzione']}")
                st.caption(f"🗓️ {row['data']}")
            
            with c3:
                # Tasto elimina accanto alla parola
                if st.button("🗑️", key=f"del_{row['id']}"):
                    c.execute("DELETE FROM dizionario WHERE id = ?", (row['id'],))
                    conn.commit()
                    st.rerun()
            st.divider()
else:
    st.info("Il tuo diario è vuoto. Inserisci una parola per iniziare!")
