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

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('diario_v7.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS dizionario 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, originale TEXT, traduzione_formattata TEXT, data TEXT, direzione TEXT)''')
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- LOGICA DI TRADUZIONE MIGLIORATA ---
def get_clean_translation(word, direzione):
    is_to_en = (direzione == "IT ➔ EN")
    
    # Mapping etichette (EN, IT)
    pos_map = {
        "adjective": ("adj.", "agg."),
        "noun": ("n.", "s."),
        "verb": ("v.", "v."),
        "adverb": ("adv.", "avv.")
    }
    idx = 0 if is_to_en else 1

    try:
        # 1. TRADUZIONE PRINCIPALE
        translator_main = GoogleTranslator(source='it' if is_to_en else 'en', target='en' if is_to_en else 'it')
        main_translation = translator_main.translate(word).lower()
        
        # 2. RICERCA SINONIMI COMUNI
        # Usiamo sempre la parola inglese per il dizionario
        word_en = main_translation if is_to_en else word.lower()
        response = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word_en}")
        
        final_results = []
        
        if response.status_code == 200:
            data = response.json()[0]
            # Prendiamo solo il PRIMO significato (di solito il più comune) per ogni categoria
            for meaning in data.get('meanings', []):
                pos_raw = meaning.get('partOfSpeech', '')
                if pos_raw not in pos_map: continue # Salta categorie strane
                
                tag = pos_map[pos_raw][idx]
                
                # Lista di parole da processare (Parola principale + sinonimi del dizionario)
                potential_words = [word_en] + meaning.get('synonyms', [])[:3]
                
                # Pulizia: teniamo solo parole singole ed evitiamo termini troppo lunghi/rari
                potential_words = [w for w in potential_words if " " not in w and len(w) < 12]

                for p_word in potential_words:
                    if is_to_en:
                        # Se andiamo verso l'inglese, salviamo la parola così com'è + tag
                        display_word = p_word.capitalize()
                    else:
                        # Se andiamo verso l'italiano, dobbiamo tradurre i sinonimi inglesi
                        display_word = GoogleTranslator(source='en', target='it').translate(p_word).capitalize()
                    
                    entry = f"{display_word} :blue[{tag}]"
                    if entry not in final_results:
                        final_results.append(entry)
                
                if len(final_results) >= 4: break # Non affolliamo troppo
        
        # Se il dizionario fallisce, restituisci almeno la traduzione base
        if not final_results:
            tag_fallback = ":blue[agg.]" if "bello" in word.lower() or "beautiful" in word.lower() else ""
            return f"{main_translation.capitalize()} {tag_fallback}"
            
        return " / ".join(final_results[:4])
        
    except Exception as e:
        return f"Errore: {str(e)}"

def get_tts_audio(text, lang='en'):
    tts = gTTS(text=text, lang=lang)
    audio_stream = io.BytesIO()
    tts.write_to_fp(audio_stream)
    return audio_stream.getvalue()

# --- INTERFACCIA ---
st.title("📓 MyDiary")

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
                # Logica audio: legge la versione inglese
                audio_text = row['traduzione_formattata'].split(' :')[0] if row['direzione'] == "IT ➔ EN" else row['originale']
                if st.button("🔊", key=f"aud_{row['id']}"):
                    audio_placeholder.audio(get_tts_audio(audio_text), format="audio/mp3", autoplay=True)
            with c2:
                st.markdown(f"**{row['originale'].capitalize()}**")
                st.markdown(row['traduzione_formattata'])
            with c3:
                if st.button("🗑️", key=f"del_{row['id']}"):
                    c.execute("DELETE FROM dizionario WHERE id = ?", (row['id'],))
                    conn.commit()
                    st.rerun()
            st.divider()
