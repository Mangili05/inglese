import streamlit as st
import sqlite3
from deep_translator import GoogleTranslator
from datetime import datetime
import pandas as pd

# Configurazione Pagina
st.set_page_config(page_title="Il Mio Diario Linguistico", page_icon="📝", layout="centered")

# --- FUNZIONI DATABASE ---
def init_db():
    conn = sqlite3.connect('diario_voci_v2.db', check_same_thread=False)
    c = conn.cursor()
    # Aggiungiamo 'id' come chiave primaria per poter eliminare le righe facilmente
    c.execute('''CREATE TABLE IF NOT EXISTS dizionario 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, inglese TEXT, italiano TEXT, data TEXT)''')
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- INTERFACCIA APP ---
st.title("📝 Diario Linguistico Personale")

# Sezione Inserimento
with st.expander("➕ Aggiungi una nuova parola", expanded=True):
    col1, col2 = st.columns([2, 1])
    
    with col2:
        direzione = st.radio("Direzione:", ("EN ➔ IT", "IT ➔ EN"))
    
    with col1:
        parola_input = st.text_input("Scrivi la parola:").strip()

    if st.button("Traduci e Salva"):
        if parola_input:
            try:
                # Imposta sorgente e destinazione in base alla scelta
                src, tgt = ('en', 'it') if direzione == "EN ➔ IT" else ('it', 'en')
                
                # Traduzione
                traduzione = GoogleTranslator(source=src, target=tgt).translate(parola_input)
                data_oggi = datetime.now().strftime("%d/%m/%Y %H:%M")
                
                # Salvataggio (Salviamo sempre 'inglese' nella prima colonna e 'italiano' nella seconda per coerenza)
                if src == 'en':
                    c.execute("INSERT INTO dizionario (inglese, italiano, data) VALUES (?, ?, ?)",
                              (parola_input, traduzione, data_oggi))
                else:
                    c.execute("INSERT INTO dizionario (inglese, italiano, data) VALUES (?, ?, ?)",
                              (traduzione, parola_input, data_oggi))
                
                conn.commit()
                st.success(f"Salvato: **{parola_input}** ➔ **{traduzione}**")
                st.rerun() # Ricarica l'app per aggiornare la tabella
            except Exception as e:
                st.error(f"Errore: {e}")
        else:
            st.warning("Inserisci una parola prima di cliccare!")

st.divider()

# --- VISUALIZZAZIONE E GESTIONE DIARIO ---
st.subheader("📚 Il tuo vocabolario")

# Recupero dati
df = pd.read_sql_query("SELECT * FROM dizionario ORDER BY id DESC", conn)

if not df.empty:
    # Mostriamo la tabella (nascondendo la colonna ID per pulizia visiva)
    st.dataframe(df.drop(columns=['id']), use_container_width=True, hide_index=True)
    
    st.divider()
    
    # Sezione Eliminazione
    st.subheader("🗑️ Gestione errori")
    col_del1, col_del2 = st.columns([3, 1])
    
    with col_del1:
        # Crea una lista di stringhe per il selettore (es: "apple - mela")
        opzioni_elimina = df.apply(lambda row: f"{row['inglese']} | {row['italiano']}", axis=1).tolist()
        parola_da_eliminare = st.selectbox("Seleziona la riga da rimuovere:", opzioni_elimina)
        
    with col_del2:
        st.write(" ") # Spaziatore
        if st.button("Elimina riga"):
            # Troviamo l'ID corrispondente alla selezione
            indice_sel = opzioni_elimina.index(parola_da_eliminare)
            id_da_eliminare = int(df.iloc[indice_sel]['id'])
            
            c.execute("DELETE FROM dizionario WHERE id = ?", (id_da_eliminare,))
            conn.commit()
            st.warning("Voce eliminata correttamente.")
            st.rerun()

else:
    st.info("Il tuo diario è vuoto. Comincia ad aggiungere qualche parola!")
