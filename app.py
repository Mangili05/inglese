import streamlit as st
import sqlite3
from deep_translator import GoogleTranslator
from gtts import gTTS
import io
import requests
from datetime import datetime
import pandas as pd

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="MyDiary", page_icon="📓", layout="centered")

# --- FUNZIONI DATABASE ---
def init_db():
    conn = sqlite3.connect('diario_voci_v5.db', check_same_thread=False)
    c = conn.cursor()
    # Salviamo i dettagli già formattati come stringa nel DB
    c.execute('''CREATE TABLE IF NOT EXISTS dizionario 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, inglese TEXT, italiano TEXT, dettagli TEXT, data TEXT)''')
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- LOGICA DI TRADUZIONE E SINONIMI ---
def get_enhanced_details(word_en):
    """Recupera sinonimi in inglese e li traduce in italiano raggruppandoli per tipo"""
    try:
        response = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word_en}")
        if response.status_code != 200:
            return ""
        
        data = response.json()[0]
        translator_to_it = GoogleTranslator(source='en', target='it')
        all_info = []

        for meaning in data.get('meanings', []):
            part_of_speech = meaning.get('partOfSpeech', 'altro')
            synonyms_en = meaning.get('synonyms', [])[:3] # Prendiamo i primi 3
            
            if synonyms_en:
                pairs = []
                for syn in synonyms_en:
                    # Traduciamo il sinonimo inglese in italiano
                    syn_it = translator_to_it.translate(syn)
                    pairs.append(f"{syn} ➔ {syn_it}")
                
                # Formattazione: [verb] produce ➔ produrre, make ➔ fare
                info_line = f"**{part_of_speech}**: {', '.join(pairs)}"
                all_info.append(info_line)
        
        return "  \n".join(all_info) # Ritorna le righe separate da a capo
    except:
        return ""

def get_tts_audio(text, lang='en'):
    tts = gTTS(text=text, lang=lang)
    audio_stream = io.BytesIO()
    tts.write_to_fp(audio_stream)
    return audio_stream.getvalue()

# --- INTERFACCIA UTENTE ---
st.title("📓 MyDiary")
st.markdown("---")

# Input
with st.container():
    col_in1, col_in2 = st.columns([2, 1])
    with col_in2:
        direzione = st.radio("Direzione:", ("IT ➔ EN", "EN ➔ IT"))
    with col_in1:
        parola_input = st.text_input("Inserisci termine da imparare:").strip()

    if st.button("Traduci e Salva nel Diario", use_container_width=True):
        if parola_input:
            with st.spinner("Ricerca sinonimi e traduzione in corso..."):
                try:
                    # Direzione traduzione
                    if direzione == "IT ➔ EN":
                        word_it = parola_input
                        word_en = GoogleTranslator(source='it', target='en').translate(parola_input)
                    else:
                        word_en = parola_input
                        word_it = GoogleTranslator(source='en', target='it').translate(parola_input)
                    
                    # Recupero sinonimi accoppiati (sempre basandosi sulla parola inglese)
                    dettagli = get_enhanced_details(word_en.lower())
                    
                    data_oggi = datetime.now().strftime("%d/%m/%Y")
                    
                    c.execute("INSERT INTO dizionario (inglese, italiano, dettagli, data) VALUES (?, ?, ?, ?)",
                              (word_en.lower(), word_it.lower(), dettagli, data_oggi))
                    conn.commit()
                    st.success(f"Aggiunto: {word_it} = {word_en}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")

st.markdown("### 📚 Le tue parole")

# Visualizzazione
audio_placeholder = st.empty()
df = pd.read_sql_query("SELECT * FROM dizionario ORDER BY id DESC", conn)

if not df.empty:
    for index, row in df.iterrows():
        # Container per ogni parola per pulizia visiva
        with st.container():
            c1, c2, c3 = st.columns([1, 6, 1])
            
            with c1:
                if st.button("🔊", key=f"audio_{row['id']}"):
                    audio_bytes = get_tts_audio(row['inglese'])
                    audio_placeholder.audio(audio_bytes, format="audio/mp3", autoplay=True)
            
            with c2:
                st.markdown(f"**{row['inglese'].upper()}** ⟷ *{row['italiano'].capitalize()}*")
                if row['dettagli']:
                    st.info(row['dettagli'])
            
            with c3:
                if st.button("🗑️", key=f"del_{row['id']}"):
                    c.execute("DELETE FROM dizionario WHERE id = ?", (row['id'],))
                    conn.commit()
                    st.rerun()
            st.markdown("---")
else:
    st.info("Il diario è vuoto. Inserisci la prima parola qui sopra!")
