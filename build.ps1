$ErrorActionPreference = "Stop"

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "   Avvio processo di build per Windows     " -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan

# 1. Verifica presenza di Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Rilevato: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERRORE] Python non e' raggiungibile da terminale." -ForegroundColor Red
    Write-Host "Verifica che Python sia installato e presente nel PATH." -ForegroundColor Red
    Exit 1
}

# 2. Aggiornamento pip e dipendenze
Write-Host "`nInstallazione e verifica delle dipendenze..." -ForegroundColor Yellow
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

# 3. Pulizia cartelle di build precedenti
Write-Host "`nPulizia cartelle di compilazione..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

# 4. Compilazione eseguibile con PyInstaller
Write-Host "`nCreazione dell'eseguibile unico in corso (questa operazione puo' richiedere alcuni minuti)..." -ForegroundColor Yellow

pyinstaller --noconfirm `
    --name "DENSO_Controller" `
    --onefile `
    --windowed `
    --paths src `
    --add-data "src/schemas/*.json;src/schemas" `
    --collect-all faster_whisper `
    --collect-all ctranslate2 `
    run_gui.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n=====================================================================" -ForegroundColor Green
    Write-Host " Build completata con successo!" -ForegroundColor Green
    Write-Host " Troverai l'eseguibile in: dist\DENSO_Controller.exe" -ForegroundColor Green
    Write-Host "`n Ricordati di copiare il file .env.example (rinominato in .env)" -ForegroundColor Cyan
    Write-Host " accanto al file .exe prima di avviarlo." -ForegroundColor Cyan
    Write-Host "=====================================================================" -ForegroundColor Green
} else {
    Write-Host "`n[ERRORE] La compilazione con PyInstaller e' fallita." -ForegroundColor Red
    Exit 1
}
