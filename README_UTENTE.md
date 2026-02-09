# GitSnap – Guida all’uso

Questa guida è per chi utilizza **GitSnap** tramite l’eseguibile (`.exe` su Windows). Spiega come avviare l’app, configurarla e confrontare due ambienti (SOURCE e TARGET) sui repository Azure DevOps.

---

## Cosa fa GitSnap

GitSnap confronta **due ambienti** (ad es. il branch *develop* e il branch *master*) su **più repository Git** in un progetto Azure DevOps, **senza clonare** i repository. In pochi secondi puoi vedere:

- quali repository sono **allineati** o **divergenti**;
- **quanti commit** e **quali file** differiscono tra SOURCE e TARGET.

Utile per rispondere a domande come: *“Sviluppo è allineato a Collaudo?”* o *“Cosa cambia tra Collaudo e Produzione?”*.

---

## Cosa ti serve

| Requisito | Descrizione |
|-----------|-------------|
| **Account Azure DevOps** | Accesso a un’**Organization** e un **Project** con repository Git. |
| **PAT (Personal Access Token)** | Token con permesso **Code – Read** (solo lettura). |

### Come creare il PAT

1. In Azure DevOps: **User settings** (icona ingranaggio in alto a destra) → **Personal access tokens**.
2. **+ New Token**: nome (es. “GitSnap”), scadenza (es. 90 giorni).
3. **Scopes**: **Code** → **Read**.
4. Crea e **copia il token** (viene mostrato una sola volta). Lo inserirai nell’app nel campo **PAT**.

Se usi **Azure DevOps Server** (on‑premise), oltre al PAT ti serve l’indirizzo del server (**Base URL**, es. `http://server:8080/tfs`).

---

## Avvio dell'applicazione

**Non serve installare nulla** (né Python né altro). Basta avere Windows e un browser.

**Doppio clic su GitSnap.exe**  
Se apri solo l’exe, vedrai l’errore **"Impossibile raggiungere questa pagina"** / **"localhost ha rifiutato la connessione"** (ERR_CONNECTION_REFUSED). L’exe è solo la finestra dell’app: deve essere attivo anche un **server** (Streamlit) sulla stessa macchina.

**Cosa fare:**

1. Assicurati di avere la **cartella completa** che ti è stata fornita (con i file `src`, `data`, eventuale `.venv`, e i file `.bat`).
2. **Avvia sempre** il file **`Avvia GitSnap (desktop).bat`** (doppio clic).  
   Quel file avvia il server in background e poi apre l’exe (o il browser).  
   **Usa sempre questo metodo** per aprire GitSnap.
3. Se ti è stato dato **solo** l’exe senza la cartella e il file `.bat`, chiedi a chi ti ha fornito il programma il **pacchetto completo** (cartella con app + **Avvia GitSnap (desktop).bat** + eventuale ambiente Python già configurato).

**Requisito:** sulla macchina deve essere installato **Python** (3.10 o superiore) con le dipendenze dell’app, oppure la cartella deve contenere già l’ambiente virtuale (`.venv`) pronto all’uso.

---

## Avvio dell’applicazione

1. **Doppio clic** su **`Avvia GitSnap (desktop).bat`** (nella stessa cartella in cui si trovano `src`, `data` e, se presente, `GitSnap.exe`).
2. Attendi qualche secondo: il server si avvia in background, poi si apre la finestra GitSnap (o il browser su http://localhost:8501).
3. Se la finestra è vuota o in caricamento, attendi ancora qualche secondo.

---

## Primo utilizzo – Configurazione

1. **Base URL**  
   - Se usi **Azure DevOps nel cloud** (dev.azure.com): lascia **vuoto**.  
   - Se usi **Azure DevOps Server** (on‑premise): inserisci l’indirizzo del server (es. `http://server:8080/tfs`).

2. **Organization** e **Project**  
   Inserisci i nomi esatti della tua organization e del progetto (es. `DefaultCollection`, `MioProgetto`).

3. **PAT**  
   Incolla il tuo Personal Access Token nel campo **PAT**.

4. Clicca **Testa connessione**. Se va a buon fine, comparirà un messaggio di conferma e potrai procedere.

---

## Confrontare SOURCE e TARGET

1. **Seleziona i repository**  
   Dopo il test connessione viene mostrata la lista dei repository. Seleziona quelli che ti interessano (oppure “Seleziona tutti”).

2. **Definisci SOURCE e TARGET**  
   - **Tipo**: Branch, Tag pattern oppure Commit SHA.  
   - **Valore**: ad es. il nome del branch (`develop`, `master`) o un pattern per i tag.

3. Clicca **Esegui confronto**.

4. **Risultati**  
   - Tabella riassuntiva: per ogni repository vedi se è **allineato** o **divergente**, il numero di commit e di file diversi.  
   - Aprendo ogni riga (expander) vedi i dettagli: commit SOURCE e TARGET, autore, data, e l’elenco dei file modificati.

---

## Salvare la configurazione e i progetti

- **Salva configurazione (senza PAT)**  
  Salva organization, project, repository selezionati e definizione di SOURCE/TARGET. Il **PAT non viene salvato** per sicurezza.

- **Sidebar (pannello laterale)**  
  Clicca sulla freccia in alto a sinistra per aprire il pannello. Puoi:
  - **Aggiungere progetti**: salvare più combinazioni (Base URL, Organization, Project, eventuale PAT) con un nome, per passare velocemente da un progetto all’altro.
  - **Caricare progetto**: scegli un progetto salvato per precompilare i campi.
  - **Eliminare progetto**: rimuovere un progetto dalla lista.

I dati vengono salvati in file nella cartella dell’applicazione (configurazione e progetti salvati).

---

## Risoluzione problemi

| Problema | Cosa fare |
|----------|-----------|
| **"localhost ha rifiutato la connessione" / ERR_CONNECTION_REFUSED** | Hai avviato solo l’exe. Chiudi la finestra e avvia invece **`Avvia GitSnap (desktop).bat`** dalla cartella dell’app (vedi sezione [Come avviare](#-importante-come-avviare-gitsnap)). |
| **Connessione fallita** (dopo aver avviato correttamente) | Controlla Base URL (se on‑prem), Organization, Project e PAT. Verifica che il PAT abbia scope **Code – Read** e non sia scaduto. |
| **Nessun repository in lista** | Controlla di avere accesso in lettura al progetto. Riprova il test connessione. |
| **Finestra bianca o che non carica** | Riavvia l’applicazione. Se usi un server on‑premise, verifica di essere sulla rete corretta (VPN se necessario). |
| **PAT non riconosciuto** | Crea un nuovo token in Azure DevOps e usa quello. Il PAT va incollato senza spazi davanti o dietro. |

---

## Supporto

Per domande sull’uso di GitSnap o sui risultati del confronto, contatta chi ti ha fornito l’eseguibile o il pacchetto di installazione.

**GitSnap** · made with ❤️ by Massimo Contursi
