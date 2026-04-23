import streamlit as st
import sqlite3
from deep_translator import GoogleTranslator
from gtts import gTTS
import io
import requests
from datetime import datetime
import pandas as pd

# 1. PERSONALIZZAZIONE APP (Nome e Logo)
st.set_page_config(
    page_title="MyDiary", 
    page_icon="📓", 
    layout="centered"
)

# --- FUNZIONI DATABASE ---
def init_db():
    conn = sqlite3.connect('diario_voci_v4.db', check_same_thread=False)
    c = conn.cursor()
    # Aggiunta colonna 'dettagli' per salvare sinonimi e tipi
    c.execute('''CREATE TABLE IF NOT EXISTS dizionario 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, inglese TEXT, italiano TEXT, dettagli TEXT, data TEXT)''')
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- FUNZIONI EXTRA (Dizionario e Sinonimi) ---
def get_word_details(word_en):
    """Recupera tipo di parola e sinonimi usando Free Dictionary API"""
    try:
        response = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word_en}")
        if response.status_code == 200:
            data = response.json()[0]
            info = []
            for meaning in data.get('meanings', []):
                part_of_speech = meaning.get('partOfSpeech', '')
                synonyms = meaning.get('synonyms', [])[:3] # Prende i primi 3
                syn_str = f" (Sinonimi: {', '.join(synonyms)})" if synonyms else ""
                info.append(f"[{part_of_speech}] {syn_str}")
            return " | ".join(info)
    except:
        pass
    return ""

def get_tts_audio(text, lang='en'):
    tts = gTTS(text=text, lang=lang)
    audio_stream = io.BytesIO()
    tts.write_to_fp(audio_stream)
    return audio_stream.getvalue()

# --- INTERFACCIA APP ---
st.title("📓 MyDiary")
st.caption("Il tuo compagno personale per lo studio dell'inglese")

# Sezione Inserimento
with st.expander("➕ Aggiungi nuova parola", expanded=True):
    col_in1, col_in2 = st.columns([2, 1])
    with col_in2:
        direzione = st.radio("Direzione:", ("EN ➔ IT", "IT ➔ EN"))
    with col_in1:
        parola_input = st.text_input("Inserisci termine:").strip()

    if st.button("Traduci e Salva", use_container_width=True):
        if parola_input:
            try:
                src, tgt = ('en', 'it') if direzione == "EN ➔ IT" else ('it', 'en')
                
                # 1. Traduzione principale
                traduzione = GoogleTranslator(source=src, target=tgt).translate(parola_input)
                
                # 2. Recupero dettagli (sempre basato sulla parola inglese)
                parola_en = parola_input if src == 'en' else traduzione
                dettagli = get_word_details(parola_en)
                
                # 3. Traduzione dei sinonimi se presenti
                if dettagli and src == 'it': # Se inserisco IT, i sinonimi trovati sono EN, li lasciamo così
                     pass 
                
                data_oggi = datetime.now().strftime("%d/%m/%Y")
                ing, ita = (parola_input, traduzione) if src == 'en' else (traduzione, parola_input)
                
                c.execute("INSERT INTO dizionario (inglese, italiano, dettagli, data) VALUES (?, ?, ?, ?)",
                          (ing.lower(), ita.lower(), dettagli, data_oggi))
                conn.commit()
                st.success(f"Salvato: {ing} = {ita}")
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")

st.divider()

# --- VISUALIZZAZIONE DIARIO ---
st.subheader("📚 Vocabolario Salvato")

audio_placeholder = st.empty()
df = pd.read_sql_query("SELECT * FROM dizionario ORDER BY id DESC", conn)

if not df.empty:
    for index, row in df.iterrows():
        # Layout: Audio | Testo | Elimina
        c1, c2, c3 = st.columns([1, 6, 1])
        
        with c1:
            if st.button("🔊", key=f"audio_{row['id']}"):
                audio_bytes = get_tts_audio(row['inglese'])
                audio_placeholder.audio(audio_bytes, format="audio/mp3", autoplay=True)
        
        with c2:
            st.markdown(f"**{row['inglese'].capitalize()}**")
            st.markdown(f"*{row['italiano'].capitalize()}*")
            if row['dettagli']:
                st.caption(f"ℹ️ {row['dettagli']}")
        
        with c3:
            # Tasto elimina accanto alla parola
            if st.button("🗑️", key=f"del_{row['id']}"):
                c.execute("DELETE FROM dizionario WHERE id = ?", (row['id'],))
                conn.commit()
                st.rerun()
        
        st.divider()
else:
    st.info("Inizia a scrivere per popolare il tuo diario!")
