"""
Avvia Streamlit (app principale del repo) in background sulla porta 8501
e termina quando il server è pronto. Usato da Tauri come beforeDevCommand
per mostrare l'app Streamlit nella finestra desktop invece della splash Vite.
"""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
APP_PY = ROOT / "src" / "app.py"
PORT = 8501
WAIT_TIMEOUT = 60
POLL_INTERVAL = 0.5


def port_ready(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect(("127.0.0.1", port))
        return True
    except OSError:
        return False


def main():
    if not APP_PY.exists():
        print(f"ERRORE: {APP_PY} non trovato.", file=sys.stderr)
        sys.exit(1)

    env = os.environ.copy()
    env.setdefault("PATH", os.defpath)
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(APP_PY),
        "--server.port", str(PORT),
        "--server.headless", "true",
    ]

    if sys.platform == "win32":
        # Su Windows: avvio in background tramite cmd start /B. Il primo "" è il titolo (obbligatorio).
        # Passiamo ogni argomento a start separatamente così path con spazi funzionano.
        subprocess.Popen(
            ["cmd", "/c", "start", "/B", ""] + cmd,
            cwd=str(ROOT),
            env=env,
        )
    else:
        subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    # Attendi che la porta sia in ascolto
    deadline = time.monotonic() + WAIT_TIMEOUT
    while time.monotonic() < deadline:
        if port_ready(PORT):
            sys.exit(0)
        time.sleep(POLL_INTERVAL)

    print(f"Timeout: Streamlit non in ascolto su {PORT} dopo {WAIT_TIMEOUT}s", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
