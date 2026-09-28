@echo off
setlocal

echo ===========================================
echo   Avvio processo di build per Windows
echo ===========================================

REM 1. Verifica presenza di Python
python --version >nul 2>&1
if errorlevel 1 goto :no_python

echo [OK] Python trovato nel sistema:
python --version

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
echo Creazione dell'eseguibile unico in corso...
pyinstaller --noconfirm ^
    --name "DENSO_Controller" ^
    --onefile ^
    --windowed ^
    --add-data "src/schemas/*.json;src/schemas" ^
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

:no_python
echo.
echo [ERRORE] Python non e' raggiungibile da terminale.
echo Assicurati che Python sia installato e presente nel PATH.
echo.
pause
exit /b 1

:build_error
echo.
echo [ERRORE] La compilazione con PyInstaller e' fallita.
echo.
pause
exit /b 1
