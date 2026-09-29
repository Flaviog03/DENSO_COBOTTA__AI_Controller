@echo off
setlocal

echo ===========================================
echo   Avvio processo di build per Windows
echo ===========================================

REM 1. Ricerca ed impostazione di Python 3.11
set "PYTHON_CMD="

REM Tentativo 1: Python Launcher di Windows (py -3.11)
py -3.11 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.11"
    goto :python_found
)

REM Tentativo 2: Comando python3.11
python3.11 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python3.11"
    goto :python_found
)

REM Tentativo 3: Percorsi standard di installazione su Windows
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python311\python.exe""
    goto :python_found
)
if exist "C:\Python311\python.exe" (
    set "PYTHON_CMD="C:\Python311\python.exe""
    goto :python_found
)
if exist "C:\Program Files\Python311\python.exe" (
    set "PYTHON_CMD="C:\Program Files\Python311\python.exe""
    goto :python_found
)

REM Tentativo 4: Comando python generico (se e' gia' versione 3.11)
python --version 2>&1 | findstr /R "3\.11" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :python_found
)

goto :no_python311

:python_found
echo [OK] Python 3.11 rilevato nel sistema:
%PYTHON_CMD% --version

REM 2. Installazione dipendenze
echo.
echo Installazione e verifica delle dipendenze con Python 3.11...
%PYTHON_CMD% -m pip install --upgrade pip
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 goto :pip_error
%PYTHON_CMD% -m pip install pyinstaller
if errorlevel 1 goto :pip_error

REM 3. Pulizia build precedenti
echo.
echo Pulizia cartelle di compilazione...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM 4. Generazione eseguibile standalone
echo.
echo Creazione dell'eseguibile unico in corso...
%PYTHON_CMD% -m PyInstaller --noconfirm ^
    --name "DENSO_Controller" ^
    --onefile ^
    --windowed ^
    --paths src ^
    --add-data "src/schemas/*.json;src/schemas" ^
    --add-data "src/schemas/*.json;schemas" ^
    --collect-all faster_whisper ^
    --collect-all ctranslate2 ^
    run_gui.py

if errorlevel 1 goto :build_error

echo.
echo =====================================================================
echo  Build completata con successo!
echo  Troverai l'eseguibile in: dist\DENSO_Controller.exe
echo.
echo  Ricordati di copiare il file .env.example (rinominato in .env)
echo  accanto al file .exe prima di avviarlo.
echo =====================================================================
pause
exit /b 0

:no_python311
echo.
echo [ERRORE] Python 3.11 non e' stato trovato nel sistema.
echo.
echo Il pacchetto 'av' (richiesto da faster-whisper) necessita di Python 3.11 su Windows
echo per evitare errori di compilazione binaria C/FFmpeg tipici di Python 3.12/3.13+.
echo.
echo Per risolvere:
echo  1. Installa Python 3.11 (es. 3.11.9) da python.org.
echo  2. Durante l'installazione seleziona "Add python.exe to PATH" e "py launcher".
echo.
pause
exit /b 1

:build_error
echo.
echo [ERRORE] La compilazione con PyInstaller e' fallita.
echo.
pause
exit /b 1

:pip_error
echo.
echo [ERRORE] L'installazione delle dipendenze con pip e' fallita.
echo.
pause
exit /b 1


