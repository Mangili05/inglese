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

# CSS personalizzato per rendere l'interfaccia ancora più simile a un'app
st.markdown("""
    <style>
    .pos-tag { color: #2e76d2; font-weight: bold; font-size: 0.8em; }
    .stButton>button { border-radius: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('diario_reverso_v1.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS dizionario 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, originale TEXT, traduzione_formattata TEXT, data TEXT, direzione TEXT)''')
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- LOGICA DI TRADUZIONE REVERSO-STYLE ---
def get_pos_and_alternatives(word_en, is_to_en=True):
    """
    Recupera categoria grammaticale e alternative.
    is_to_en=True significa che la traduzione è in inglese (usa adj., v.)
    is_to_en=False significa che la traduzione è in italiano (usa agg., v., s.)
    """
    pos_map = {
        "adjective": ("adj.", "agg."),
        "verb": ("v.", "v."),
        "noun": ("n.", "s."),
        "adverb": ("adv.", "avv.")
    }
    
    try:
        response = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word_en}")
        if response.status_code != 200: return ""
        
        data = response.json()[0]
        results = []
        
        # Estraiamo la parola principale e i sinonimi raggruppati per POS
        for meaning in data.get('meanings', []):
            pos_raw = meaning.get('partOfSpeech', '')
            # Scegliamo l'abbreviazione giusta (EN o IT)
            idx = 0 if is_to_en else 1
            tag = pos_map.get(pos_raw, (f"{pos_raw}.", f"{pos_raw}."))[idx]
            
            # Prendiamo la parola stessa + 2 sinonimi per quel POS
            syns = [word_en] + meaning.get('synonyms', [])[:2]
            
            # Se stiamo traducendo verso l'italiano, dobbiamo tradurre anche i sinonimi
            if not is_to_en:
                translator = GoogleTranslator(source='en', target='it')
                syns = [translator.translate(s) for s in syns]
            
            for s in list(dict.fromkeys(syns)): # Rimuove duplicati
                results.append(f"{s} :blue[{tag}]")
        
        return " / ".join(results[:4]) # Limitiamo a 4 risultati totali
    except:
        return ""

def get_tts_audio(text, lang='en'):
    tts = gTTS(text=text, lang=lang)
    audio_stream = io.BytesIO()
    tts.write_to_fp(audio_stream)
    return audio_stream.getvalue()

# --- INTERFACCIA ---
st.title("📓 MyDiary")

# Inserimento
with st.container():
    col_in1, col_in2 = st.columns([2, 1])
    with col_in2:
        direzione = st.radio("Direzione:", ("IT ➔ EN", "EN ➔ IT"))
    with col_in1:
        parola_input = st.text_input("Inserisci termine:").strip()

    if st.button("Traduci e Salva", use_container_width=True):
        if parola_input:
            with st.spinner("Elaborazione in corso..."):
                try:
                    if direzione == "IT ➔ EN":
                        # Traduciamo l'input in EN per interrogare il dizionario
                        main_trans = GoogleTranslator(source='it', target='en').translate(parola_input)
                        output_formattato = get_pos_and_alternatives(main_trans, is_to_en=True)
                        lingua_audio = main_trans
                    else:
                        # L'input è già EN
                        output_formattato = get_pos_and_alternatives(parola_input, is_to_en=False)
                        lingua_audio = parola_input
                    
                    # Se il dizionario non trova nulla, mettiamo almeno la traduzione base
                    if not output_formattato:
                        base = GoogleTranslator(source='it' if direzione=="IT ➔ EN" else 'en', 
                                                target='en' if direzione=="IT ➔ EN" else 'it').translate(parola_input)
                        output_formattato = base

                    data_oggi = datetime.now().strftime("%d/%m/%Y")
                    c.execute("INSERT INTO dizionario (originale, traduzione_formattata, data, direzione) VALUES (?, ?, ?, ?)",
                              (parola_input, output_formattato, data_oggi, direzione))
                    conn.commit()
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")

st.markdown("---")

# Visualizzazione Diario
audio_placeholder = st.empty()
df = pd.read_sql_query("SELECT * FROM dizionario ORDER BY id DESC", conn)

if not df.empty:
    for index, row in df.iterrows():
        with st.container():
            c1, c2, c3 = st.columns([1, 6, 1])
            
            with c1:
                # Per l'audio: se IT->EN la parola inglese è la traduzione, altrimenti è l'originale
                text_for_audio = row['traduzione_formattata'].split(' :')[0] if row['direzione'] == "IT ➔ EN" else row['originale']
                if st.button("🔊", key=f"audio_{row['id']}"):
                    audio_bytes = get_tts_audio(text_for_audio)
                    audio_placeholder.audio(audio_bytes, format="audio/mp3", autoplay=True)
            
            with c2:
                st.markdown(f"**{row['originale'].capitalize()}**")
                st.markdown(row['traduzione_formattata'])
            
            with c3:
                if st.button("🗑️", key=f"del_{row['id']}"):
                    c.execute("DELETE FROM dizionario WHERE id = ?", (row['id'],))
                    conn.commit()
                    st.rerun()
            st.markdown("---")
