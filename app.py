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
    conn = sqlite3.connect('diario_v8.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS dizionario 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, originale TEXT, traduzione_formattata TEXT, data TEXT, direzione TEXT)''')
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- LOGICA DI TRADUZIONE "REVERSO" ---
def get_reverso_style_translation(word, direzione):
    is_to_en = (direzione == "IT ➔ EN")
    
    # Traduttori
    translator_to_target = GoogleTranslator(source='it' if is_to_en else 'en', target='en' if is_to_en else 'it')
    translator_back_to_source = GoogleTranslator(source='en' if is_to_en else 'it', target='it' if is_to_en else 'en')

    # Mapping Etichette
    pos_map = {
        "adjective": ("adj.", "agg."),
        "noun": ("n.", "s."),
        "verb": ("v.", "v."),
        "adverb": ("adv.", "avv.")
    }
    idx = 0 if is_to_en else 1

    try:
        # 1. Traduzione principale
        main_trans = translator_to_target.translate(word).lower()
        
        # 2. Otteniamo dati dal dizionario sulla parola inglese
        word_en = main_trans if is_to_en else word.lower()
        response = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word_en}")
        
        final_entries = []
        
        if response.status_code == 200:
            data = response.json()[0]
            for meaning in data.get('meanings', []):
                pos_raw = meaning.get('partOfSpeech', '')
                if pos_raw not in pos_map: continue # Salta roba strana o arcaica
                
                tag = pos_map[pos_raw][idx]
                
                # Prendiamo la parola principale e i sinonimi
                candidates = [word_en] + meaning.get('synonyms', [])[:5]
                
                for cand in candidates:
                    cand = cand.lower()
                    if " " in cand or len(cand) > 12: continue # Salta frasi composte o parole lunghissime
                    
                    # --- FILTRO DI COERENZA (Back-Translation) ---
                    # Traduciamo il candidato verso la lingua originale per vedere se il senso coincide
                    back_trans = translator_back_to_source.translate(cand).lower()
                    
                    # Se il candidato tradotto non c'entra nulla con la parola originale, lo scartiamo
                    # (Esempio: se 'Hefty' tradotto non dà 'Bello', sparisce)
                    common_roots = [word[:4].lower(), "bell", "piac", "good", "nice", "fine"]
                    if any(root in back_trans for root in common_roots) or word.lower() in back_trans:
                        
                        # Formattazione finale
                        if is_to_en:
                            display_word = cand.capitalize()
                        else:
                            # Se la direzione è EN->IT, la traduzione è quella di ritorno
                            display_word = back_trans.capitalize()
                        
                        entry = f"{display_word} :blue[{tag}]"
                        if entry not in final_entries:
                            final_entries.append(entry)
                
                if len(final_entries) >= 4: break

        # Fallback se il dizionario è troppo vuoto
        if not final_entries:
            return f"{main_trans.capitalize()} :blue[{'adj.' if is_to_en else 'agg.'}]"

        return " / ".join(final_entries[:4])

    except:
        return translator_to_target.translate(word).capitalize()

# --- INTERFACCIA ---
st.title("📓 MyDiary")

with st.container():
    col_in1, col_in2 = st.columns([2, 1])
    with col_in2:
        direzione = st.radio("Direzione:", ("IT ➔ EN", "EN ➔ IT"))
    with col_in1:
        parola_input = st.text_input("Parola da tradurre:").strip()

    if st.button("Traduci e Salva", use_container_width=True):
        if parola_input:
            with st.spinner("Analisi sinonimi in corso..."):
                output = get_reverso_style_translation(parola_input, direzione)
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
                # Audio: legge la parte inglese
                text_to_read = row['traduzione_formattata'].split(' :')[0] if row['direzione'] == "IT ➔ EN" else row['originale']
                if st.button("🔊", key=f"aud_{row['id']}"):
                    audio_placeholder.audio(gTTS(text=text_to_read, lang='en').get_urls()[0], format="audio/mp3", autoplay=True)
            with c2:
                st.markdown(f"**{row['originale'].capitalize()}**")
                st.markdown(row['traduzione_formattata'])
            with c3:
                if st.button("🗑️", key=f"del_{row['id']}"):
                    c.execute("DELETE FROM dizionario WHERE id = ?", (row['id'],))
                    conn.commit()
                    st.rerun()
            st.divider()
