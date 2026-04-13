import streamlit as st
import sqlite3
from deep_translator import GoogleTranslator
from gtts import gTTS
import io
from datetime import datetime
import pandas as pd

# Configurazione Pagina
st.set_page_config(page_title="Il Mio Diario Linguistico", page_icon="📝", layout="centered")

# --- FUNZIONI DATABASE ---
# (Assicurati di usare 'v2' o un nome nuovo come discusso prima)
def init_db():
    conn = sqlite3.connect('diario_voci_v2.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS dizionario 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, inglese TEXT, italiano TEXT, data TEXT)''')
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- FUNZIONI AUDIO ---
def get_tts_audio(text, lang='en'):
    """Genera l'audio gTTS in memoria e lo restituisce in bytes"""
    tts = gTTS(text=text, lang=lang)
    audio_stream = io.BytesIO()
    tts.write_to_fp(audio_stream)
    return audio_stream.getvalue()

def play_audio(audio_bytes):
    """Crea un widget audio nascosto che riproduce automaticamente l'audio"""
    st.audio(audio_bytes, format="audio/mp3", autoplay=True)

# --- INTERFACCIA APP ---
st.title("📝 Diario Linguistico 2.0")

# Sezione Inserimento
with st.expander("➕ Aggiungi una nuova parola", expanded=True):
    col1, col2 = st.columns([2, 1])
    
    with col2:
        direzione = st.radio("Direzione:", ("EN ➔ IT", "IT ➔ EN"))
    
    with col1:
        parola_input = st.text_input("Scrivi la parola:").strip()

    if st.button("Traduci e Salva", key="btn_save"):
        if parola_input:
            try:
                src, tgt = ('en', 'it') if direzione == "EN ➔ IT" else ('it', 'en')
                traduzione = GoogleTranslator(source=src, target=tgt).translate(parola_input)
                data_oggi = datetime.now().strftime("%d/%m/%Y %H:%M")
                
                # Coerenza nel DB
                ing, ita = (parola_input, traduzione) if src == 'en' else (traduzione, parola_input)
                
                c.execute("INSERT INTO dizionario (inglese, italiano, data) VALUES (?, ?, ?)",
                          (ing.lower(), ita.lower(), data_oggi))
                conn.commit()
                st.success(f"Salvato: **{parola_input}** ➔ **{traduzione}**")
                # Rimuovi st.rerun() qui se dà problemi di performance in inserimento rapido
            except Exception as e:
                st.error(f"Errore: {e}")
        else:
            st.warning("Inserisci una parola prima di cliccare!")

st.divider()

# --- VISUALIZZAZIONE E PRONUNCIA DIARIO ---
st.subheader("📚 Il tuo vocabolario")

# Recupero dati
df = pd.read_sql_query("SELECT * FROM dizionario ORDER BY id DESC", conn)

# --- Gestore Audio State (Per non rigenerare audio ad ogni click) ---
# Usiamo st.empty() per un widget audio che aggiorneremo
audio_placeholder = st.empty()

if not df.empty:
    # Mostriamo solo le ultime 20 voci per performance mobile
    recent_df = df.head(20)
    
    # Invece di st.dataframe, usiamo un loop per generare righe HTML/Streamlit
    # con icone audio cliccabili
    for index, row in recent_df.iterrows():
        # Creiamo un layout pulito per ogni riga
        riga_col1, riga_col2, riga_col3 = st.columns([1, 4, 1])
        
        # Colonna 1: Icona Audio
        # Usiamo un pulsante finto con un'icona per mobile
        key_audio = f"tts_{row['id']}"
        with riga_col1:
            if st.button("🔊", key=key_audio):
                with st.spinner("Gen..."):
                    audio_bytes = get_tts_audio(row['inglese'])
                    # Aggiorna il placeholder in alto per riprodurre l'audio
                    audio_placeholder.audio(audio_bytes, format="audio/mp3", autoplay=True)

        # Colonna 2: Testo (Grassetto l'inglese)
        with riga_col2:
            st.markdown(f"**{row['inglese']}** | *{row['italiano']}*")
            
        # Colonna 3: Data (piccola)
        with riga_col3:
            st.caption(row['data'].split(' ')[0]) # Solo data, no ora
            
        st.divider()

    # --- Sezione Eliminazione ---
    with st.expander("🗑️ Elimina una voce errata"):
        opzioni_elimina = df.apply(lambda r: f"{r['inglese']} | {r['italiano']}", axis=1).tolist()
        parola_da_eliminare = st.selectbox("Seleziona:", opzioni_elimina)
        
        if st.button("Elimina definitivamente"):
            indice_sel = opzioni_elimina.index(parola_da_eliminare)
            id_da_eliminare = int(df.iloc[indice_sel]['id'])
            
            c.execute("DELETE FROM dizionario WHERE id = ?", (id_da_eliminare,))
            conn.commit()
            st.warning("Voce eliminata correttamente.")
            st.rerun()

else:
    st.info("Il tuo diario è vuoto.")
