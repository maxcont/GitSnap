# Richieste Postman per testare Azure DevOps REST API

Usa queste richieste in **Postman** (o simile) per verificare connessione, **scoprire quale api-version** supporta il tuo server e testare ref/branch.

---

## Import collection (opzionale)

- In Postman: **Import** → scegli il file **`GitCheck_Postman_Collection.json`** nella cartella del progetto.
- Nella collection importata, apri **Variables** e imposta **PAT** con il tuo token (Current Value).
- Le richieste 1–6 sono pronte; puoi cambiare **BASE_URL**, **ORG**, **PROJECT**, **REPO_ID** dalle variabili.

---

## 1. Autenticazione

- **Tipo:** Basic Auth  
- **Username:** lascia vuoto oppure `""` (alcuni server accettano solo PAT)  
- **Password:** il tuo **PAT** (Personal Access Token)

In Postman: tab **Authorization** → Type **Basic Auth** → compila solo **Password** con il PAT.

---

## 2. Variabili (da sostituire nelle URL)

| Variabile   | Esempio (tuo ambiente)                    |
|------------|-------------------------------------------|
| `BASE_URL` | `http://gswvwtfs1.ternaren.prv:8080/tfs`  |
| `ORG`      | `DefaultCollection`                       |
| `PROJECT`  | `EACS`                                    |
| `REPO_ID`  | *(lo ottieni dalla risposta della lista repo)* |

---

## 3. Test connessione + lista repository

**Metodo:** `GET`

**URL (copia-incolla, poi sostituisci BASE_URL, ORG, PROJECT):**

```
{{BASE_URL}}/{{ORG}}/{{PROJECT}}/_apis/git/repositories?api-version=5.0
```

**Esempio concreto:**

```
http://gswvwtfs1.ternaren.prv:8080/tfs/DefaultCollection/EACS/_apis/git/repositories?api-version=5.0
```

- **Headers:** nessuno obbligatorio (Postman aggiunge Basic Auth da solo).
- Dalla risposta JSON prendi `value[].id` (GUID, es. `01177660-1970-4169-9f98-fb8cba071e66`) o `value[].name` (es. `ProgConf-BE`) e usalo come `REPO_ID` nelle richieste sotto. Su alcuni TFS le chiamate **refs/commits/diffs** usano il **project GUID** (`value[].project.id`) nel path: GitCheck dopo «Carica repository» usa in automatico quel GUID.

---

## 3b. Get singolo repository (opzionale)

**Metodo:** `GET`

**URL:**

```
{{BASE_URL}}/{{ORG}}/{{PROJECT}}/_apis/git/repositories/{{REPO_ID}}?api-version=5.0
```

Restituisce un solo oggetto repo (con `defaultBranch`, `_links.refs`, `project.id`, ecc.). I link in `_links.refs` mostrano l’URL esatto che il server usa per i ref (incluso project GUID nel path).

---

## 4. Scoprire la versione API supportata – Lista ref (branch)

Il tuo server potrebbe supportare solo **5.0** o **6.0**, non **7.1**. Prova in ordine queste tre GET; la prima che restituisce **200** con una lista di ref è quella da usare.

### 4a. api-version = 5.0

**Metodo:** `GET`

**URL:**

```
{{BASE_URL}}/{{ORG}}/{{PROJECT}}/_apis/git/repositories/{{REPO_ID}}/refs?api-version=5.0&$top=100
```

**Esempio (sostituisci REPO_ID con l’id reale, es. nome o GUID del repo ProgConf-BE):**

```
http://gswvwtfs1.ternaren.prv:8080/tfs/DefaultCollection/EACS/_apis/git/repositories/ProgConf-BE/refs?api-version=5.0&$top=100
```

- Se **200** e nel JSON c’è `value` (array con elementi `name`, `objectId`) → il server supporta **5.0** e i ref sono disponibili.
- Se **404** o **400** → prova 4b o 4c.

---

### 4b. api-version = 6.0

**Metodo:** `GET`

**URL:**

```
{{BASE_URL}}/{{ORG}}/{{PROJECT}}/_apis/git/repositories/{{REPO_ID}}/refs?api-version=6.0&$top=100
```

**Esempio:**

```
http://gswvwtfs1.ternaren.prv:8080/tfs/DefaultCollection/EACS/_apis/git/repositories/ProgConf-BE/refs?api-version=6.0&$top=100
```

---

### 4c. api-version = 7.1

**Metodo:** `GET`

**URL:**

```
{{BASE_URL}}/{{ORG}}/{{PROJECT}}/_apis/git/repositories/{{REPO_ID}}/refs?api-version=7.1&$top=100
```

**Esempio:**

```
http://gswvwtfs1.ternaren.prv:8080/tfs/DefaultCollection/EACS/_apis/git/repositories/ProgConf-BE/refs?api-version=7.1&$top=100
```

---

## 5. Ref filtrati (solo branch)

Stessa richiesta della sezione 4, con parametro **filter** (sostituisci `5.0` con la versione che ha funzionato):

**Metodo:** `GET`

**URL:**

```
{{BASE_URL}}/{{ORG}}/{{PROJECT}}/_apis/git/repositories/{{REPO_ID}}/refs?api-version=5.0&$top=100&filter=refs/heads/
```

**Senza filtro (tutti i ref, per vedere il formato dei nomi):**

```
{{BASE_URL}}/{{ORG}}/{{PROJECT}}/_apis/git/repositories/{{REPO_ID}}/refs?api-version=5.0&$top=100
```

Dalla risposta controlla come sono i `name`: ad es. `refs/heads/master`, `heads/master` o solo `master`.

---

## 6. Commit su un branch (opzionale)

**Metodo:** `GET`

**URL (sostituisci `master` con il nome del branch che hai):**

```
{{BASE_URL}}/{{ORG}}/{{PROJECT}}/_apis/git/repositories/{{REPO_ID}}/commits?api-version=5.0&$top=5&searchCriteria.itemVersion.version=master&searchCriteria.itemVersion.versionType=branch
```

**Esempio:**

```
http://gswvwtfs1.ternaren.prv:8080/tfs/DefaultCollection/EACS/_apis/git/repositories/ProgConf-BE/commits?api-version=5.0&$top=5&searchCriteria.itemVersion.version=master&searchCriteria.itemVersion.versionType=branch
```

---

## 7. Diff tra due ref (opzionale)

Dopo aver risolto due ref in commit SHA (objectId dai ref o dai commit), puoi testare i diff:

**Metodo:** `GET`

**URL (sostituisci BASE_COMMIT e TARGET_COMMIT con due SHA):**

```
{{BASE_URL}}/{{ORG}}/{{PROJECT}}/_apis/git/repositories/{{REPO_ID}}/diffs/commits?api-version=5.0&baseVersion=BASE_COMMIT&baseVersionType=commit&targetVersion=TARGET_COMMIT&targetVersionType=commit&$top=50
```

---

## Riepilogo rapido

| Cosa testare              | Metodo | Endpoint |
|---------------------------|--------|----------|
| Connessione + lista repo  | GET    | `.../git/repositories?api-version=5.0` |
| Quale api-version per ref | GET    | `.../repositories/{id}/refs?api-version=5.0` (poi 6.0, 7.1) |
| Ref (tutti)                | GET    | `.../refs?api-version=5.0&$top=100` |
| Ref (solo branch)         | GET    | `.../refs?api-version=5.0&filter=refs/heads/` |
| Commit su branch          | GET    | `.../commits?api-version=5.0&searchCriteria.itemVersion.version=master&searchCriteria.itemVersion.versionType=branch` |

Usa **sempre** Basic Auth con il PAT. Se una api-version dà 404/400, prova la successiva (5.0 → 6.0 → 7.1).

---

## C’è un endpoint per sapere quale api-version usa il server?

**No.** Microsoft non espone un endpoint REST che restituisce la “versione API supportata” o la versione del server.

- **Da interfaccia:** puoi aprire **Help → About** (o l’URL `https://<tuo-server>/DefaultCollection/_home/About`) e vedere la versione del prodotto (es. Azure DevOps Server 2020). Da lì risali alla tabella:
  - 2019 → api-version fino a **5.0**
  - 2020 → fino a **6.0**
  - 2022 → fino a **7.0**
- **In modo programmatico:** l’unica strada è **provare** le api-version (5.0, 6.0, 7.1) sulle chiamate che ti servono (es. refs, repositories) e usare la prima che risponde con **200** e dati validi. È quello che fa anche il client GitCheck (fallback 7.1 → 6.0 → 5.0).
