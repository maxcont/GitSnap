# -*- mode: python ; coding: utf-8 -*-
# PyInstaller: build "one-folder" (onedir) per avvio velocissimo.
# Nessuna estrazione in temp: l'exe legge dalla cartella dist/GitSnap/.
# Distribuisci la cartella dist/GitSnap/ (zip o copia); l'utente avvia GitSnap.exe.
# Build: dalla root del repo: pyinstaller --noconfirm GitSnap.spec

import sys
from pathlib import Path

ROOT = Path.cwd().resolve()
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"
DATA = ROOT / "data"
STREAMLIT_CFG = ROOT / ".streamlit"

datas = [
    (str(SRC), "src"),
    (str(STREAMLIT_CFG), ".streamlit"),
]
if DATA.exists():
    datas.append((str(DATA), "data"))

# Metadati e static di Streamlit (senza .dist-info → PackageNotFoundError; senza static → index.html 404)
try:
    import streamlit as _st
    _st_root = Path(_st.__file__).resolve().parent
    _sp = _st_root.parent
    for _d in _sp.glob("streamlit*.dist-info"):
        datas.append((str(_d), _d.name))
        break
    _static = _st_root / "static"
    if _static.is_dir():
        datas.append((str(_static), "streamlit/static"))
except Exception:
    pass

hiddenimports = [
    "streamlit",
    "streamlit.web.cli",
    "streamlit.runtime.scriptrunner.magic_funcs",
    "streamlit.web.server",
    "streamlit.web.server.server",
    "streamlit.runtime.state",
    "streamlit.runtime.uploaded_file_manager",
    "altair",
    "pandas",
    "numpy",
    "requests",
    "packaging",
    "typing_extensions",
]

a = Analysis(
    [str(SCRIPTS / "gitsnap_launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GitSnap",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_console=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="GitSnap",
)
