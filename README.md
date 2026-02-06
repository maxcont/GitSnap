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
- [Utilizzo passo-passo](#utilizzo-passo-passo)
- [Schermate e funzionalità](#schermate-e-funzionalità)
- [Esempi d'uso](#esempi-duso)
- [Configurazione persistente (config.json)](#configurazione-persistente-configjson)
- [Architettura del codice](#architettura-del-codice)
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

---

## Utilizzo passo-passo

1. **Configurazione connessione**  
   Inserisci **Base URL** (solo se usi Azure DevOps Server on‑prem, es. `http://gswvwtfs1.ternaren.prv:8080/tfs`), Organization, Project e PAT (e opzionalmente Username).  
   Clicca **"Test connessione"** per verificare, poi **"Carica repository del progetto"**.

2. **Selezione repository**  
   Nella lista con i checkbox seleziona i repo da confrontare (o **"Seleziona tutti"**).

3. **Definizione ambienti**  
   - **SOURCE**: tipo (Branch / Tag pattern / Commit SHA) e valore (es. `develop` o `prod*`).  
   - **TARGET**: stesso schema (es. `master` o un tag pattern).

4. **Esecuzione confronto**  
   Clicca **"Esegui confronto"**. L’app risolve i ref per ogni repo e chiama l’API `diffs/commits`.

5. **Lettura risultati**  
   Nella dashboard vedi per ogni repo: stato (Allineato / Divergente / Errore), #commit e #file diff. Apri gli expander per commit e file; usa il link per aprire la compare in Azure DevOps.

6. **Salvataggio configurazione (opzionale)**  
   Clicca **"Salva configurazione (senza PAT)"** per salvare org, project, repo selezionati e definizione SOURCE/TARGET in `config.json`. Il PAT **non** viene salvato.

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
- **Carica repository del progetto**: chiama l’API [Git Repositories List](https://learn.microsoft.com/en-us/rest/api/azure/devops/git/repositories/list) e mostra l’elenco dei repo con checkbox e **"Seleziona tutti"** / **"Deseleziona tutti"**.

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
- **Expander per repo**: dettaglio con lista commit e lista file + link **"Apri Compare in Azure DevOps"** (compare tra i due ref nel portale).

### 5. Persistenza configurazione

- **Salva configurazione**: scrive in `config.json` (nella cartella del progetto):
  - organization, project, username (se usato);
  - ID dei repo selezionati;
  - definizione SOURCE e TARGET (tipo + valore).
- **Il PAT non viene mai salvato** in `config.json` (solo in memoria nella sessione Streamlit).
- All’avvio, se esiste `config.json`, l’app precompila organization, project, username e (se presenti) i repo selezionati e SOURCE/TARGET.

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

## Architettura del codice

| File | Ruolo |
|------|--------|
| **azure_devops_client.py** | Autenticazione (PAT + opzionale username), session HTTP, retry con backoff, chiamate a: list repositories, refs, commits, get commits compare, diffs/commits. |
| **ref_resolver.py** | Risolve per ogni repo: branch → commit ID, tag pattern → tag più recente → commit ID, SHA → commit ID. Gestisce ref mancanti. |
| **diff_service.py** | Per ogni repo: chiama `diffs/commits` (base=TARGET, target=SOURCE), parsing di changeCounts/changes/aheadCount; opzionale lista commit (API Get Commits con compareVersion). Restituisce stato (aligned/divergent/error), conteggi, liste. |
| **app.py** | UI Streamlit: form connessione, lista repo con checkbox, form SOURCE/TARGET, pulsante confronto, dashboard con tabella, filtri, expander, salvataggio/caricamento config. |

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
