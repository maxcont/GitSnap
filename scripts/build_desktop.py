import os
import shutil
import subprocess
import sys
from pathlib import Path

APP_NAME = "GitSnap"

ROOT = Path(__file__).parent.parent.resolve()
SCRIPTS = ROOT / "scripts"

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

    # 4) Assicura cargo nel PATH per la sessione del processo
    cargo_bin = str(Path.home() / ".cargo" / "bin")
    env = {"PATH": cargo_bin + os.pathsep + os.environ.get("PATH", "")}

    # Modalità: dev o build (default: dev)
    mode = "dev"
    if len(sys.argv) > 1:
        mode = sys.argv[1].strip().lower()

    if mode not in ("dev", "build"):
        raise ValueError("Uso: python scripts/build_desktop.py [dev|build]")

    if mode == "dev":
        run([npm, "run", "tauri", "dev"], cwd=TAURI_DIR, extra_env=env)
    else:
        run([npm, "run", "tauri", "build"], cwd=TAURI_DIR, extra_env=env)
        print("\n✅ Installer in:")
        print(TAURI_DIR / "src-tauri" / "target" / "release" / "bundle")

if __name__ == "__main__":
    main()
