import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

APP_NAME = "GitSnap"
STREAMLIT_PORT = 8501
STREAMLIT_WAIT_TIMEOUT = 60

ROOT = Path(__file__).parent.parent.resolve()
SCRIPTS = ROOT / "scripts"
APP_PY = ROOT / "src" / "app.py"

OUTPUT_APP = ROOT / "output" / APP_NAME

TAURI_DIR = ROOT / "desktop" / "gitsnap-desktop"
TAURI_RES = TAURI_DIR / "src-tauri" / "resources" / APP_NAME


def resolve_npm_cmd():
    # Windows: npm va invocato come npm.cmd
    candidates = [
        Path(r"C:\Program Files\nodejs\npm.cmd"),
        Path(r"C:\Program Files (x86)\nodejs\npm.cmd"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    raise FileNotFoundError("npm.cmd non trovato. Verifica installazione Node.js.")


def run(cmd, cwd=None, extra_env=None):
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    print(f"\n▶ {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=str(cwd) if cwd else None, env=env)

def ensure(path: Path, label: str):
    if not path.exists():
        raise FileNotFoundError(f"{label} non trovato: {path}")

def sync_resources():
    # Pulisce e ricopia GitSnap dentro resources
    if TAURI_RES.exists():
        shutil.rmtree(TAURI_RES)
    TAURI_RES.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n📁 Sync resources:\n  da: {OUTPUT_APP}\n  a : {TAURI_RES}")
    shutil.copytree(OUTPUT_APP, TAURI_RES)


def _port_ready(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect(("127.0.0.1", port))
        return True
    except OSError:
        return False


def start_streamlit_for_dev():
    """Avvia Streamlit in background (stesso ambiente di build_desktop.py) e attende la porta."""
    if not APP_PY.exists():
        raise FileNotFoundError(f"app.py non trovato: {APP_PY}")
    cmd = [
        sys.executable,
        "-m", "streamlit", "run", str(APP_PY),
        "--server.port", str(STREAMLIT_PORT),
        "--server.headless", "true",
    ]
    print(f"\n▶ Avvio Streamlit su porta {STREAMLIT_PORT}...")
    subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=os.environ.copy(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + STREAMLIT_WAIT_TIMEOUT
    while time.monotonic() < deadline:
        if _port_ready(STREAMLIT_PORT):
            print(f"   Streamlit pronto su http://localhost:{STREAMLIT_PORT}")
            return
        time.sleep(0.5)
    raise RuntimeError(f"Streamlit non in ascolto su {STREAMLIT_PORT} dopo {STREAMLIT_WAIT_TIMEOUT}s")

def main():
    # 1) Build output
    run([sys.executable, str(SCRIPTS / "build_output.py")], cwd=ROOT)

    ensure(OUTPUT_APP, "Output app")
    ensure(TAURI_DIR, "Cartella Tauri desktop")
    ensure(TAURI_DIR / "package.json", "package.json Tauri")

    # 2) Sync resources
    sync_resources()

    # 3) npm install se manca node_modules
    npm = resolve_npm_cmd()


    if not (TAURI_DIR / "node_modules").exists():
        run([npm, "install"], cwd=TAURI_DIR)

    # 4) PATH per npm/tauri: Node.js (per "node") e Cargo (per "cargo") devono essere in PATH
    nodejs_dir = str(Path(npm).resolve().parent)
    cargo_bin = str(Path.home() / ".cargo" / "bin")
    env = os.environ.copy()
    path = env.get("PATH", "")
    prepend = []
    if nodejs_dir not in path:
        prepend.append(nodejs_dir)
    if Path(cargo_bin).exists() and cargo_bin not in path:
        prepend.append(cargo_bin)
    if prepend:
        env["PATH"] = os.pathsep.join(prepend) + os.pathsep + path

    mode = "dev"
    if len(sys.argv) > 1:
        mode = sys.argv[1].strip().lower()

    if mode not in ("dev", "build"):
        raise ValueError("Uso: python scripts/build_desktop.py [dev|build]")

    if mode == "dev":
        start_streamlit_for_dev()
        run([npm, "run", "tauri", "dev"], cwd=TAURI_DIR, extra_env=env)
    else:
        run([npm, "run", "tauri", "build"], cwd=TAURI_DIR, extra_env=env)
        print("\n✅ Installer in:")
        print(TAURI_DIR / "src-tauri" / "target" / "release" / "bundle")

if __name__ == "__main__":
    main()
