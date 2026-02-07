@echo off
setlocal

REM -------------------------------------------------
REM Avvio GitCheck - Streamlit App
REM -------------------------------------------------

REM Spostati nella cartella dove si trova questo file
cd /d %~dp0

REM Controllo presenza virtual environment
if not exist ".venv\Scripts\activate.bat" (
    echo ERRORE: virtual environment non trovato.
    echo Assicurati che la cartella ".venv" sia presente.
    pause
    exit /b 1
)

REM Attiva il virtual environment
call .venv\Scripts\activate

REM Porta Streamlit
set STREAMLIT_PORT=8501

REM Apri il browser
start "" http://localhost:%STREAMLIT_PORT%

REM Avvia Streamlit
streamlit run src/app.py ^
    --server.headless true ^
    --server.port %STREAMLIT_PORT%

endlocal
