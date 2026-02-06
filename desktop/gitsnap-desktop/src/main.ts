// In build: la finestra reindirizza a Streamlit su localhost:8501
// (in dev Tauri carica direttamente devUrl, questo file non viene usato)
const STREAMLIT_URL = "http://localhost:8501";
const app = document.getElementById("app")!;
app.textContent = "Reindirizzamento a GitSnap...";
window.location.href = STREAMLIT_URL;
