import shutil
from pathlib import Path

# ===== CONFIG =====
APP_NAME = "GitSnap"

# Root progetto = padre di /scripts
ROOT = Path(__file__).parent.parent.resolve()

OUTPUT_ROOT = ROOT / "output"
OUTPUT_APP = OUTPUT_ROOT / APP_NAME

INCLUDE = [
    "src",
    "data",
    "requirements.txt",
    "README.md",
    ".streamlit",
    ".venv",
    "Avvia.bat",
]

EXCLUDE = {
    "__pycache__",
    ".vscode",
    ".git",
    "output",
}

# ===== LOGIC =====
def clean_output():
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_APP.mkdir(parents=True)

def copy_item(item_name: str):
    src = ROOT / item_name
    dst = OUTPUT_APP / item_name

    if not src.exists():
        print(f"⚠️  Skippato (non trovato): {item_name}")
        return

    if src.is_dir():
        shutil.copytree(
            src,
            dst,
            ignore=shutil.ignore_patterns(*EXCLUDE)
        )
    else:
        shutil.copy2(src, dst)

def main():
    print("🧹 Pulizia output/")
    clean_output()

    print(f"📦 Creazione pacchetto: {APP_NAME}")
    for item in INCLUDE:
        copy_item(item)

    print("\n✅ Build completata")
    print(f"➡️  {OUTPUT_APP}")

if __name__ == "__main__":
    main()
