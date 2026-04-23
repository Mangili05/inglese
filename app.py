import streamlit as st
import sqlite3
from deep_translator import GoogleTranslator
from gtts import gTTS
import io
import requests
from datetime import datetime
import pandas as pd

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="MyDiary", page_icon="📓", layout="centered")

# CSS per i colori dei Tag (Blu come Reverso)
st.markdown("""
    <style>
    .blue-tag { color: #2e76d2; font-weight: bold; font-size: 0.85em; }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('diario_v6.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS dizionario 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, originale TEXT, traduzione_formattata TEXT, data TEXT, direzione TEXT)''')
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- LOGICA DI TRADUZIONE ---
def get_clean_translation(word, direzione):
    """Ottiene la traduzione pulita e i sinonimi corretti"""
    try:
        is_to_en = (direzione == "IT ➔ EN")
        translator_main = GoogleTranslator(source='it' if is_to_en else 'en', target='en' if is_to_en else 'it')
        translator_reverse = GoogleTranslator(source='en' if is_to_en else 'it', target='it' if is_to_en else 'en')
        
        # 1. Traduzione Principale
        main_translation = translator_main.translate(word)
        
        # 2. Otteniamo i Tag e i Sinonimi dall'API Dizionario (usiamo sempre la parola inglese)
        word_en = main_translation if is_to_en else word
        response = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word_en.lower()}")
        
        results = []
        # Mapping etichette richiesto
        pos_map = {
            "adjective": ("adj.", "agg."),
            "noun": ("n.", "s."),
            "verb": ("v.", "v."),
            "adverb": ("adv.", "avv.")
        }
        idx = 0 if is_to_en else 1 # 0 per EN, 1 per IT

        if response.status_code == 200:
            data = response.json()[0]
            for meaning in data.get('meanings', []):
                pos_raw = meaning.get('partOfSpeech', '')
                tag = pos_map.get(pos_raw, (f"{pos_raw}.", f"{pos_raw}."))[idx]
                
                # Prendiamo la parola principale tradotta e i sinonimi
                syns_en = meaning.get('synonyms', [])[:2] # Prendiamo solo i primi 2 sinonimi per evitare errori
                
                # Creiamo la lista di parole da mostrare
                if is_to_en:
                    # Esempio: Beautiful adj. / Nice adj.
                    current_items = [main_translation] + syns_en
                else:
                    # Esempio: Bello agg. / Splendido agg.
                    # Dobbiamo tradurre i sinonimi inglesi in italiano
                    current_items = [main_translation]
                    for s in syns_en:
                        translated_syn = GoogleTranslator(source='en', target='it').translate(s)
                        current_items.append(translated_syn)
                
                for item in list(dict.fromkeys(current_items)): # Rimuove duplicati
                    results.append(f"{item.capitalize()} :blue[{tag}]")
        
        if not results:
            return main_translation.capitalize()
            
        return " / ".join(results[:4]) # Massimo 4 risultati
    except:
        # Fallback in caso di errore API
        return GoogleTranslator(source='it' if direzione=="IT ➔ EN" else 'en', 
                                target='en' if direzione=="IT ➔ EN" else 'it').translate(word).capitalize()

def get_tts_audio(text, lang='en'):
    tts = gTTS(text=text, lang=lang)
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
        parola_input = st.text_input("Inserisci termine:").strip()

    if st.button("Traduci e Salva", use_container_width=True):
        if parola_input:
            with st.spinner("Traduzione in corso..."):
                output = get_clean_translation(parola_input, direzione)
                data_oggi = datetime.now().strftime("%d/%m/%Y")
                c.execute("INSERT INTO dizionario (originale, traduzione_formattata, data, direzione) VALUES (?, ?, ?, ?)",
                          (parola_input, output, data_oggi, direzione))
                conn.commit()
                st.rerun()

st.divider()

# --- VISUALIZZAZIONE ---
audio_placeholder = st.empty()
df = pd.read_sql_query("SELECT * FROM dizionario ORDER BY id DESC", conn)

if not df.empty:
    for index, row in df.iterrows():
        with st.container():
            c1, c2, c3 = st.columns([1, 6, 1])
            with c1:
                # Audio: prende la prima parola della traduzione se IT->EN, o l'originale se EN->IT
                word_for_audio = row['traduzione_formattata'].split(' :')[0] if row['direzione'] == "IT ➔ EN" else row['originale']
                if st.button("🔊", key=f"audio_{row['id']}"):
                    audio_bytes = get_tts_audio(word_for_audio)
                    audio_placeholder.audio(audio_bytes, format="audio/mp3", autoplay=True)
            with c2:
                st.markdown(f"**{row['originale'].capitalize()}**")
                st.markdown(row['traduzione_formattata'])
            with c3:
                if st.button("🗑️", key=f"del_{row['id']}"):
                    c.execute("DELETE FROM dizionario WHERE id = ?", (row['id'],))
                    conn.commit()
                    st.rerun()
            st.divider()
