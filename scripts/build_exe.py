"""
Build GitSnap con PyInstaller (onedir = cartella, avvio veloce).
Output: dist/GitSnap/ con GitSnap.exe e dipendenze. Nessuna estrazione in temp.

Eseguire dalla root: python scripts/build_exe.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "GitSnap.spec"
DIST_DIR = ROOT / "dist" / "GitSnap"

def main():
    if not SPEC.exists():
        print(f"ERRORE: {SPEC} non trovato.")
        sys.exit(1)
    if DIST_DIR.exists():
        print("  Rimozione dist/GitSnap/ esistente...")
        try:
            shutil.rmtree(DIST_DIR)
        except PermissionError as e:
            print(f"  Chiudi GitSnap se è in esecuzione, poi riprova. ({e})")
            sys.exit(1)
    subprocess.check_call(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", str(SPEC)],
        cwd=str(ROOT),
    )
    print("\n✅ Build completata (onedir).")
    print(f"   Cartella: {DIST_DIR}")
    print("   Distribuisci l'intera cartella (zip o copia); l'utente avvia GitSnap.exe dalla cartella.")
    print("   Avvio veloce: nessuna estrazione, un solo processo.")

if __name__ == "__main__":
    main()
