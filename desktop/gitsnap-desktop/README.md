# GitSnap Desktop (Tauri)

Wrapper Tauri per l'app Streamlit GitSnap: una finestra nativa che in **dev** carica `http://localhost:8501` (Streamlit avviato da `build_desktop.py`).

**Non avviare da qui.** Dalla **root del repo**:

```bash
# Con venv attivo
python scripts/build_desktop.py dev
```

Lo script esegue `build_output.py`, sincronizza le risorse in `src-tauri/resources/GitSnap`, avvia Streamlit e lancia `npm run tauri dev`. La finestra apre direttamente l'app Streamlit.

- **build:** `python scripts/build_desktop.py build` → installer in `src-tauri/target/release/bundle/`
