# GitCheck – Confronto ambienti Azure DevOps (no clone)

Web app **Streamlit** per confrontare due ambienti/ref (SOURCE vs TARGET) su più repository Git in un Project Azure DevOps **senza clonare** i repo, usando solo le **Azure DevOps REST API**.

Consente al team di rispondere in pochi secondi a:
- *"Sviluppo è allineato a Collaudo?"*
- *"Collaudo è allineato a Produzione?"*
- *"Quali repo sono divergenti e cosa cambia?"*

---

## Indice

- [Requisiti](#requisiti)
- [Installazione](#installazione)
- [Avvio dell'applicazione](#avvio-dellapplicazione)
- [Avvio rapido (Windows)](#avvio-rapido-windows)
- [Utilizzo passo-passo](#utilizzo-passo-passo)
- [Schermate e funzionalità](#schermate-e-funzionalità)
- [Progetti salvati (sidebar e projects.json)](#progetti-salvati-sidebar-e-projectsjson)
- [Esempi d'uso](#esempi-duso)
- [Configurazione persistente (config.json)](#configurazione-persistente-configjson)
- [File del progetto](#file-del-progetto)
- [Architettura del codice](#architettura-del-codice)
- [Eseguire in debug (Cursor / VS Code)](#eseguire-in-debug-cursor--vs-code)
- [Api-version](#api-version-quale-versione-usa-il-server)
- [Test API con Postman](#test-api-con-postman)
- [Build pacchetto (output)](#build-pacchetto-output)
- [Risoluzione problemi](#risoluzione-problemi)
- [Vincoli tecnici](#vincoli-tecnici)

---

## Requisiti

| Requisito | Dettaglio |
|-----------|-----------|
| **Python** | 3.10 o superiore |
| **Sistema operativo** | Windows, macOS o Linux |
| **Account Azure DevOps** | Organization e Project con repository Git |
| **PAT (Personal Access Token)** | Con scope **Code – Read** (lettura codice e metadati) |

### Come ottenere il PAT

1. In Azure DevOps: **User settings** (icona ingranaggio in alto a destra) → **Personal access tokens**.
2. **+ New Token**: scegli un nome (es. "GitCheck"), scadenza (es. 90 giorni).
3. **Scopes**: seleziona **Code** → **Read** (basta la lettura).
4. Crea e **copia il token** (viene mostrato una sola volta). Inseriscilo nell’app nel campo PAT.

---

## Installazione

### 1. Clona o scarica il progetto

Se hai già la cartella `gitcheck` sul PC, apri un terminale in quella cartella.

### 2. (Consigliato) Crea un ambiente virtuale

**Windows (PowerShell):**
```powershell
cd gitcheck
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
cd gitcheck
python -m venv .venv
.venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
cd gitcheck
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Installa le dipendenze

Con l’ambiente virtuale attivo (vedi il prefisso `(.venv)` nel prompt):

```bash
pip install -r requirements.txt
```

**Se `pip` non è nel PATH** (es. su Windows):

```bash
python -m pip install -r requirements.txt
```

Dipendenze installate:
- `requests` – chiamate HTTP alle Azure DevOps REST API
- `streamlit` – interfaccia web

---

## Avvio dell'applicazione

Dalla cartella `gitcheck` (con venv attivato se lo usi):

```bash
streamlit run app.py
```

**Se `streamlit` non è nel PATH:**

```bash
python -m streamlit run app.py
```

- L’app si apre nel browser su **http://localhost:8501**.
- Per usare un’altra porta: `streamlit run app.py --server.port 8502`.
- Per aprire senza browser automatico: `streamlit run app.py --server.headless true`.

### Avvio rapido (Windows)

Nella cartella del progetto è presente **`Avvia.bat`** che:
- si sposta nella cartella dello script;
- verifica la presenza del virtual environment (`.venv`);
- attiva `.venv` e avvia Streamlit sulla porta **8501** con `--server.headless true`;
- apre il browser su `http://localhost:8501`.

Esecuzione: doppio clic su `Avvia.bat` oppure da prompt `Avvia.bat`. Richiede che `.venv` sia già stato creato e che le dipendenze siano installate (`pip install -r requirements.txt`).

---

## Utilizzo passo-passo

1. **(Opzionale) Progetti salvati**  
   Apri la **sidebar** (freccia in alto a sinistra). Puoi **aggiungere** più progetti (Base URL, Organization, Project, Username, PAT opzionale) salvati in `projects.json`, **caricare** uno per precompilare i campi in pagina, o **eliminare** un progetto. La sidebar è nascosta di default (`initial_sidebar_state="collapsed"`).

2. **Configurazione connessione**  
   Inserisci **Base URL** (solo se usi Azure DevOps Server on‑prem), Organization, Project e PAT (e opzionalmente Username). I campi possono essere precompilati da config o da un progetto caricato dalla sidebar.  
   Clicca **"Test connessione"** per verificare, poi **"Carica repository"**.

3. **Selezione repository**  
   Nella lista con i checkbox seleziona i repo da confrontare. Usa **"Seleziona tutti"** o **"Deseleziona tutti"** per aggiornare tutti i flag in un colpo solo. Puoi ordinare per nome (A→Z o Z→A).

4. **Definizione ambienti**  
   - **SOURCE**: tipo (Branch / Tag pattern / Commit SHA) e valore (es. `develop` o `prod*`).  
   - **TARGET**: stesso schema (es. `master` o un tag pattern).

5. **Esecuzione confronto**  
   Clicca **"Esegui confronto"**. L’app risolve i ref per ogni repo e chiama l’API `diffs/commits`.

6. **Lettura risultati**  
   Nella dashboard vedi per ogni repo: stato (Allineato / Divergente / Errore), #commit e #file diff. In ogni expander: **SOURCE** e **TARGET** in due colonne con commit ID, autore, data e messaggio; lista **Commit (SOURCE non in TARGET)** con autore e data; **File modificati** in expander; link **"Apri Compare in Azure DevOps"**.

7. **Salvataggio configurazione (opzionale)**  
   Clicca **"Salva configurazione (senza PAT)"** per salvare org, project, repo selezionati e definizione SOURCE/TARGET in `config.json`. Il PAT **non** viene salvato in `config.json` (in `projects.json` può essere salvato opzionalmente dalla sidebar).

---

## Schermate e funzionalità

### 1. Configurazione connessione

| Campo | Obbligatorio | Descrizione |
|-------|--------------|-------------|
| **Base URL** | No | Per **Azure DevOps Server on‑prem** (TFS): URL base del server (es. `http://gswvwtfs1.ternaren.prv:8080/tfs`). Se vuoto si usa il cloud (`https://dev.azure.com`). |
| Organization | Sì | Nome dell’organizzazione/collection (es. `DefaultCollection` on‑prem, `myorg` su cloud) |
| Project | Sì | Nome o ID del progetto (es. `EACS`) |
| PAT | Sì | Personal Access Token (campo password) |
| Username | No | Opzionale; per auth Basic si può lasciare vuoto |

**Azure DevOps Server on‑premise (TFS):** se il tuo endpoint è tipo `http://server:8080/tfs/DefaultCollection/EACS/_git/Reportistica-BE`, in GitCheck imposta **Base URL** = `http://server:8080/tfs`, **Organization** = `DefaultCollection`, **Project** = `EACS`. Poi PAT (e opzionale Username) e “Carica repository del progetto”.

**Azioni:**
- **Test connessione**: verifica credenziali e accesso al progetto.
- **Carica repository**: chiama l’API [Git Repositories List](https://learn.microsoft.com/en-us/rest/api/azure/devops/git/repositories/list) e mostra l’elenco dei repo con checkbox. **"Seleziona tutti"** e **"Deseleziona tutti"** aggiornano correttamente tutti i flag (stato sincronizzato con la session state).

### 2. Definizione ambienti (SOURCE e TARGET)

Per SOURCE e TARGET puoi scegliere:

| Tipo | Esempio valore | Comportamento |
|------|----------------|---------------|
| **Branch** | `develop`, `master`, `release/prod` | Risolto nel commit puntato dal branch |
| **Tag pattern** | `prod*`, `qa*`, `v1.*` | Elenco tag → filtro per pattern → scelta del tag **più recente** (per data commit) → risolto nel commit del tag |
| **Commit SHA** | `a1b2c3d` (anche corto) | Usato direttamente come commit |

L’app mostra quale ref è stato risolto (es. quale tag è stato scelto per un pattern). Se un ref non esiste in un repo, quello repo viene segnato in stato **ERRORE** con messaggio esplicativo.

### 3. Confronto differenze (no clone)

Per ogni repo selezionato viene usata solo l’API:

- `GET .../_apis/git/repositories/{repoId}/diffs/commits`

Vengono determinati:
- presenza di differenze (0 changes ⇒ **Allineato**);
- numero commit di differenza (da `aheadCount` / risposta API);
- lista commit (top 20) e lista file modificati (top 100).

Gestiti: ref non trovato, permessi insufficienti, errori API (con messaggio in dashboard).

### 4. Dashboard risultati

Tabella riepilogativa:

| Colonna | Significato |
|--------|-------------|
| Repo | Nome del repository |
| Stato | ✅ ALLINEATO / ⚠️ DIVERGENTE / ❌ ERRORE |
| #Commit diff | Commit in SOURCE non presenti in TARGET |
| #File diff | File modificati nel diff |
| SourceRef | Ref effettivo usato per SOURCE |
| TargetRef | Ref effettivo usato per TARGET |
| Note | Messaggio (es. errore o “Nessuna differenza”) |

**Funzioni UI:**
- **Filtro "Mostra solo divergenti"**: nasconde repo allineati ed errori.
- **Expander per repo**: **SOURCE** e **TARGET** in due colonne (commit ID, autore, data gg/mm/aaaa HH:mm, messaggio); lista **Commit (SOURCE non in TARGET)** con autore e data; **File modificati** in expander; link **"Apri Compare in Azure DevOps"**.

### 5. Persistenza configurazione

- **Salva configurazione**: scrive in `config.json` (nella cartella del progetto):
  - base_url, organization, project, username (se usato);
  - ID dei repo selezionati;
  - definizione SOURCE e TARGET (tipo + valore).
- **Il PAT non viene mai salvato** in `config.json` (solo in memoria). Può essere salvato opzionalmente in `projects.json` dalla sidebar.
- All’avvio, se esiste `config.json`, l’app precompila i campi (base_url, org, project, username) e (se presenti) i repo selezionati e SOURCE/TARGET.

---

## Progetti salvati (sidebar e projects.json)

Il **pannello laterale** è nascosto di default; si apre con la freccia in alto a sinistra.

| Funzione | Descrizione |
|---------|-------------|
| **Progetto salvato** | Select + **"Carica progetto"**: carica Base URL, Organization, Project, Username e PAT (se presente) nei campi in pagina. Poi rieseguire "Carica repository". |
| **Aggiungi progetto** | Expander "Nuovo progetto": Nome, Base URL, Organization, Project, Username, PAT (opzionale). **Salva progetto** aggiunge la voce a `projects.json`. |
| **Elimina progetto** | Select + **Elimina** per rimuovere un progetto da `projects.json`. |

**File `projects.json`** (stessa cartella di `app.py`):

```json
{
  "projects": [
    {
      "id": "uuid-corto",
      "name": "Nome progetto",
      "base_url": "http://server:8080/tfs",
      "organization": "DefaultCollection",
      "project": "EACS",
      "username": "",
      "pat": ""
    }
  ]
}
```

- **pat**: opzionale; se compilato viene salvato in chiaro. Valuta di escludere `projects.json` dal repo (es. `.gitignore`) se contiene PAT.
- **id**: generato automaticamente all'aggiunta.

---

## Esempi d'uso

### Confronto Sviluppo → Collaudo (develop vs master)

- **SOURCE**: tipo **Branch**, valore `develop`.
- **TARGET**: tipo **Branch**, valore `master`.
- Risultato: repo **Allineato** = develop e master puntano allo stesso commit; **Divergente** = ci sono commit su develop non ancora in master (da promuovere).

### Confronto Collaudo → Produzione (master vs tag prod*)

- **SOURCE**: tipo **Branch**, valore `master`.
- **TARGET**: tipo **Tag pattern**, valore `prod*`.
- L’app sceglie il tag più recente che matcha `prod*` (es. `prod-2024-01`) e confronta master con quel commit.
- Risultato: vedi se master è allineato alla “produzione” (ultimo tag prod) o se ci sono differenze da rilasciare.

### Produzione da commit specifico

- **SOURCE**: tipo **Branch**, valore `master`.
- **TARGET**: tipo **Commit SHA**, valore `a1b2c3d4...` (il commit con cui è stata costruita la produzione).
- Utile quando la produzione non è un tag ma un commit noto.

---

## Configurazione persistente (config.json)

Il file `config.json` viene creato nella stessa cartella di `app.py` (es. `gitcheck/config.json`).

**Contenuto tipico (il PAT non c’è mai):**

```json
{
  "base_url": "",
  "organization": "myorg",
  "project": "MyProject",
  "username": "",
  "selected_repo_ids": ["repo-id-1", "repo-id-2"],
  "source": { "ref_type_index": 0, "value": "develop" },
  "target": { "ref_type_index": 0, "value": "master" }
}
```

Per on‑prem, `base_url` può essere ad es. `http://gswvwtfs1.ternaren.prv:8080/tfs`.

- **ref_type_index**: 0 = Branch, 1 = Tag pattern, 2 = Commit SHA.
- Puoi modificare il file a mano; l’app lo legge al prossimo avvio.

---

## File del progetto

| File / cartella | Descrizione |
|-----------------|-------------|
| **app.py** | UI Streamlit: configurazione, sidebar progetti, lista repo, SOURCE/TARGET, confronto, dashboard. |
| **azure_devops_client.py** | Client REST Azure DevOps: autenticazione, list repositories, refs, commits, get_commit_by_id, diffs/commits, discovery api-version. |
| **ref_resolver.py** | Risoluzione branch / tag pattern / commit SHA in commit ID per ogni repo. |
| **diff_service.py** | Chiamate diffs/commits, costruzione risultato con commit e dettaglio SOURCE/TARGET (messaggio, autore, data). |
| **config.json** | Configurazione persistente (base_url, org, project, username, selected_repo_ids, source/target). Non contiene PAT. |
| **projects.json** | Elenco progetti salvati (sidebar): base_url, organization, project, username, pat opzionale. |
| **requirements.txt** | Dipendenze: `requests`, `streamlit`. |
| **Avvia.bat** | Script Windows per avviare l'app con `.venv` attivo e browser su localhost:8501. |
| **.streamlit/config.toml** | Configurazione Streamlit (es. `gatherUsageStats = false`). |
| **.vscode/launch.json** | Configurazioni debug (Streamlit: debug app.py, con/senza headless). |
| **scripts/build_output.py** | Script per creare un pacchetto in `output/GitCheck` (copia app, moduli, config, projects, requirements, README, .streamlit, Avvia.bat, .venv). |
| **POSTMAN_REQUESTS.md** | Istruzioni e richieste Postman per testare le API Azure DevOps (connessione, api-version, refs, commits, diffs). |
| **GitCheck_Postman_Collection.json** | Collection Postman importabile (variabili BASE_URL, ORG, PROJECT, REPO_ID, PAT). |

---

## Architettura del codice

| File | Ruolo |
|------|--------|
| **azure_devops_client.py** | Autenticazione (PAT + opzionale username), session HTTP, retry con backoff, discovery api-version (5.0/6.0/7.1), list repositories, refs, commits, get_commit_by_id, get_commits_compare, diffs/commits. |
| **ref_resolver.py** | Risolve per ogni repo: branch → commit ID, tag pattern → tag più recente (per data) → commit ID, SHA → commit ID. Gestisce ref mancanti. |
| **diff_service.py** | Per ogni repo: chiama `diffs/commits` (base=TARGET, target=SOURCE), parsing changeCounts/changes/aheadCount; lista commit (Get Commits compare); dettaglio SOURCE/TARGET (get_commit_by_id per messaggio, autore, data). Restituisce stato (aligned/divergent/error), conteggi, liste. |
| **app.py** | UI Streamlit: sidebar progetti (carica/aggiungi/elimina), form connessione, lista repo con Seleziona tutti/Deseleziona tutti, form SOURCE/TARGET, confronto, dashboard (expander con SOURCE/TARGET a colonne, commit con autore/data, file modificati), salvataggio config e progetti. |

**Gestione errori e logging:** eccezioni `AzureDevOpsClientError`, messaggi in dashboard e log con modulo `logging`.

---

## Eseguire in debug (Cursor / VS Code)

1. **Avvio con debugger**  
   Apri il pannello **Run and Debug** (icona play con bug, o `Ctrl+Shift+D`), scegli la configurazione **"Streamlit: debug app.py"** e premi **F5** (o il pulsante play verde). L’app parte sotto il debugger: puoi mettere **breakpoint** in `app.py`, `ref_resolver.py`, `diff_service.py`, `azure_devops_client.py` e fermarti quando viene eseguito quel punto (es. quando clicchi "Esegui confronto").

2. **Breakpoint nel codice**  
   In qualsiasi file Python inserisci `breakpoint()` dove vuoi fermarti; quando il flusso arriva lì, l’esecuzione si interrompe e nel terminale puoi ispezionare variabili (es. `repo_id`, `ref_value`, `heads`).

3. **Log dettagliati**  
   In `app.py`, nella riga di `logging.basicConfig(...)`, imposta `level=logging.DEBUG` per vedere in console tutti i log (anche da `ref_resolver` e client).

---

## Api-version (quale versione usa il server?)

Non esiste un endpoint REST che restituisce la “versione API supportata”. GitCheck **rileva automaticamente** la versione usabile: prova in ordine 5.0, 6.0, 7.1 sulle API Git e usa la prima che risponde. Dopo **Test connessione** vedrai in verde: *"Connessione riuscita. Api-version Git rilevata: 5.0"* (o 6.0 / 7.1). In alternativa puoi aprire **Help → About** nel portale Azure DevOps per vedere la versione del prodotto (2019 → api fino a 5.0, 2020 → 6.0, 2022 → 7.x).

---

## Test API con Postman

Per testare a mano le API Azure DevOps (connessione, lista repo, refs, api-version, commits, diffs) senza usare l'app:

1. **Importa la collection**: in Postman, **Import** → scegli **`GitCheck_Postman_Collection.json`** (nella cartella del progetto). Imposta la variabile **PAT** (Current Value) con il tuo token.
2. **Leggi le istruzioni**: apri **`POSTMAN_REQUESTS.md`** per le URL, i parametri e gli esempi (BASE_URL, ORG, PROJECT, REPO_ID, Basic Auth con PAT).
3. Le richieste coprono: connessione + lista repository, scoperta api-version (5.0 / 6.0 / 7.1), ref (tutti o filtrati), commit su branch, diff tra due commit.

---

## Build pacchetto (output)

Lo script **`scripts/build_output.py`** crea un pacchetto pronto da copiare (es. su un altro PC) nella cartella **`output/GitCheck`**.

**Contenuto copiato:** `app.py`, `azure_devops_client.py`, `diff_service.py`, `ref_resolver.py`, `config.json`, `projects.json`, `requirements.txt`, `README.md`, `.streamlit`, `Avvia.bat`, `.venv`. Esclusi: `__pycache__`, `.vscode`, `.git`, `output`.

**Esecuzione:** dalla root del progetto:

```bash
python scripts/build_output.py
```

Pacchetto in `output/GitCheck`; da lì attivare `.venv`, installare dipendenze se necessario, e avviare con `Avvia.bat` o `streamlit run app.py`.

---

## Risoluzione problemi

| Problema | Cosa fare |
|----------|-----------|
| **"Authentication failed"** | PAT scaduto o senza scope Code (Read). Crea un nuovo PAT con scope Code → Read. |
| **"Resource not found" (404)** | Verifica organization e project; controlla che il repo esista e che il PAT abbia accesso al progetto. |
| **Branch / tag non trovato** | Controlla il nome (es. `refs/heads/develop` vs `develop`). Per i tag, il pattern è in stile glob (es. `prod*`). |
| **`pip` o `streamlit` non riconosciuti** | Usa `python -m pip install -r requirements.txt` e `python -m streamlit run app.py`. Assicurati che Python sia nel PATH o usa il path completo a `python.exe`. |
| **Porta 8501 già in uso** | Avvia con `streamlit run app.py --server.port 8502` (o un’altra porta libera). |

---

## Vincoli tecnici

- ❌ **Nessun clone** di repository Git (nessun `git clone` né operazioni locali sui repo).
- ✅ Solo **Azure DevOps REST API** per list repo, refs, commits, diffs.
- ✅ **Linguaggio**: Python.
- ✅ **UI**: Streamlit.
- ✅ **Autenticazione**: PAT (Personal Access Token), con username opzionale.

---

## Licenza e utilizzo

Progetto fornito “as is” per uso interno. Per l’uso del PAT e l’accesso ai dati in Azure DevOps valgono i termini del tuo account e dell’organizzazione.
