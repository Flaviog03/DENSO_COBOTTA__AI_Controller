@echo off
setlocal enabledelayedexpansion

echo ===========================================
echo   Avvio processo di build per Windows
echo ===========================================

REM 1. Verifica presenza di Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERRORE] Python non e' installato o non e' presente nel PATH di sistema.
    echo Assicurati di installare Python (versione 3.10 o 3.11 consigliata)
    echo ricordandoti di spuntare "Add Python to PATH" durante l'installazione.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do echo [OK] Rilevato: %%i

REM 2. Installazione dipendenze
echo.
echo Installazione e verifica delle dipendenze...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

REM 3. Pulizia build precedenti
echo.
echo Pulizia cartelle di compilazione...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM 4. Generazione eseguibile standalone
echo.
echo Creazione dell'eseguibile unico in corso (questa operazione puo' richiedere alcuni minuti)...
pyinstaller --noconfirm ^
    --name "DENSO_Controller" ^
    --onefile ^
    --windowed ^
    --add-data "src/schemas/*.json;src/schemas" ^
    --collect-all faster_whisper ^
    --collect-all ctranslate2 ^
    run_gui.py

if %errorlevel% neq 0 (
    echo.
    echo [ERRORE] La compilazione con PyInstaller e' fallita.
    pause
    exit /b 1
)

echo.
echo =====================================================================
echo  Build completata con successo!
echo  Troverai l'eseguibile in: dist\DENSO_Controller.exe
echo.
echo  Ricordati di copiare il file .env.example (rinominato in .env)
echo  accanto al file .exe prima di avviarlo.
echo =====================================================================
pause
