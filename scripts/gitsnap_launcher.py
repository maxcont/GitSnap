"""
Launcher per GitSnap (PyInstaller): avvio veloce per utenti senza Python.
- Build onedir: nessuna estrazione in temp, exe legge dalla cartella.
- Streamlit in subprocess (stesso exe con -m streamlit run): signal handler richiede main thread.
- Apre il browser su http://localhost:8501; console "Premi Invio per chiudere".
"""
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

PORT = 8501

if getattr(sys, "frozen", False):
    BUNDLE_ROOT = Path(sys._MEIPASS)
else:
    BUNDLE_ROOT = Path(__file__).resolve().parent.parent

APP_PY = BUNDLE_ROOT / "src" / "app.py"


def _is_streamlit_process() -> bool:
    return len(sys.argv) >= 4 and sys.argv[1] == "-m" and sys.argv[2] == "streamlit"


def _run_streamlit_subprocess() -> None:
    """Esegue Streamlit (siamo il processo figlio, invocato con -m streamlit run)."""
    os.chdir(BUNDLE_ROOT)
    sys.argv = ["streamlit"] + sys.argv[3:]
    import streamlit.web.cli as stcli
    stcli.main()


def _wait_for_port(timeout_sec: float = 90.0) -> bool:
    import socket
    deadline = time.monotonic() + timeout_sec
    last_msg = 0.0
    while time.monotonic() < deadline:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect(("127.0.0.1", PORT))
            return True
        except OSError:
            now = time.monotonic()
            if now - last_msg >= 5.0:
                print(f"  Attendo il server (porta {PORT})...", flush=True)
                last_msg = now
            time.sleep(0.3)
    return False


def main() -> None:
    # Sotto processo figlio (solo in dev con subprocess): esegui Streamlit e basta
    if _is_streamlit_process():
        _run_streamlit_subprocess()
        return

    # Modalità launcher
    print("  GitSnap - Avvio in corso...", flush=True)

    if not APP_PY.exists():
        print(f"ERRORE: app non trovata: {APP_PY}", file=sys.stderr)
        input("Premi Invio per uscire...")
        sys.exit(1)

    # Subprocess: stesso exe con -m streamlit run (Streamlit richiede main thread per signal)
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m", "streamlit", "run", str(APP_PY),
            "--server.headless", "true",
            "--server.port", str(PORT),
            "--global.developmentMode", "false",
        ],
        cwd=str(BUNDLE_ROOT),
        stdout=None,
        stderr=None,
    )

    if not _wait_for_port():
        proc.terminate()
        print("ERRORE: server non avviato in tempo. Verifica che la porta 8501 sia libera.", file=sys.stderr)
        input("Premi Invio per uscire...")
        sys.exit(1)

    webbrowser.open(f"http://localhost:{PORT}")
    print("\n  GitSnap in esecuzione. Apertura del browser...")
    print(f"  Se il browser non si apre, vai a: http://localhost:{PORT}")
    print("\n  Premi Invio in questa finestra per chiudere GitSnap.\n")
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass

    proc.terminate()
    proc.wait(timeout=10)
    sys.exit(0)


if __name__ == "__main__":
    main()
