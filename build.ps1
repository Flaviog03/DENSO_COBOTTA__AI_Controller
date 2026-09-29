$ErrorActionPreference = "Stop"

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "   Avvio processo di build per Windows     " -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan

# 1. Ricerca ed impostazione di Python 3.11
$pythonCmd = $null

if (Get-Command "py" -ErrorAction SilentlyContinue) {
    $test = & py -3.11 --version 2>&1
    if ($LASTEXITCODE -eq 0) { $pythonCmd = "py -3.11" }
}

if (-not $pythonCmd -and (Get-Command "python3.11" -ErrorAction SilentlyContinue)) {
    $pythonCmd = "python3.11"
}

if (-not $pythonCmd) {
    $commonPaths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "C:\Python311\python.exe",
        "C:\Program Files\Python311\python.exe"
    )
    foreach ($p in $commonPaths) {
        if (Test-Path $p) {
            $pythonCmd = "& `"$p`""
            break
        }
    }
}

if (-not $pythonCmd -and (Get-Command "python" -ErrorAction SilentlyContinue)) {
    $v = & python --version 2>&1
    if ($v -like "*3.11*") { $pythonCmd = "python" }
}

if (-not $pythonCmd) {
    Write-Host "`n[ERRORE] Python 3.11 non e' stato trovato nel sistema." -ForegroundColor Red
    Write-Host "Il pacchetto 'av' (richiesto da faster-whisper) necessita di Python 3.11 su Windows." -ForegroundColor Red
    Write-Host "Installa Python 3.11 da python.org con 'Add to PATH' e 'py launcher'." -ForegroundColor Red
    Exit 1
}

Write-Host "[OK] Utilizzo Python 3.11:" -ForegroundColor Green
Invoke-Expression "$pythonCmd --version"

# 2. Aggiornamento pip e dipendenze
Write-Host "`nInstallazione e verifica delle dipendenze con Python 3.11..." -ForegroundColor Yellow
Invoke-Expression "$pythonCmd -m pip install --upgrade pip"
Invoke-Expression "$pythonCmd -m pip install -r requirements.txt"
Invoke-Expression "$pythonCmd -m pip install pyinstaller"

# 3. Pulizia cartelle di build precedenti
Write-Host "`nPulizia cartelle di compilazione..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

# 4. Compilazione eseguibile con PyInstaller
Write-Host "`nCreazione dell'eseguibile unico in corso (questa operazione puo' richiedere alcuni minuti)..." -ForegroundColor Yellow

$buildArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--name", "DENSO_Controller",
    "--onefile",
    "--windowed",
    "--paths", "src",
    "--add-data", "src/schemas/*.json;src/schemas",
    "--collect-all", "faster_whisper",
    "--collect-all", "ctranslate2",
    "run_gui.py"
)

if ($pythonCmd.StartsWith("& ")) {
    $exePath = $pythonCmd.Substring(2).Trim('"')
    & $exePath $buildArgs
} elseif ($pythonCmd -eq "py -3.11") {
    & py -3.11 $buildArgs
} else {
    & $pythonCmd $buildArgs
}

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
