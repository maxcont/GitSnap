# GitSnap Desktop (Tauri)

Wrapper Tauri per l'app Streamlit GitSnap: finestra nativa che carica `http://localhost:8501`.

## Dev (dalla root del repo)

```bash
# Con venv attivo
python scripts/build_desktop.py dev
```

Lo script avvia Streamlit, sincronizza le risorse in `src-tauri/resources/GitSnap` e lancia Tauri. La finestra apre direttamente l'app Streamlit.

## Build (installer)

```bash
python scripts/build_desktop.py build
```

Installer e .exe in: `desktop/gitsnap-desktop/src-tauri/target/release/bundle/`.

**Uso dell'app installata:** la finestra reindirizza a `http://localhost:8501`. Devi avviare Streamlit **prima** di aprire l'app, ad esempio:
- dalla cartella del repo (con venv attivo): `streamlit run app.py --server.port 8501`
- oppure dalla copia in `resources/GitSnap` dell’installer (se hai Python/venv lì): `python -m streamlit run app.py --server.port 8501`
