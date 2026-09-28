#!/bin/bash
# Esci immediatamente se un comando fallisce
set -e

echo "=== Avvio del processo di build per Windows ==="

# 1. Aggiornamento e installazione dipendenze
# (Usando il requirements.txt che hai appena aggiornato)
echo "Installazione dipendenze in corso..."
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# 2. Pulizia di build precedenti
echo "Pulizia cartelle di build precedenti..."
rm -rf build dist

# 3. Build con PyInstaller
# --onefile: crea un unico eseguibile .exe
# --windowed: nasconde la console di Windows all'avvio (utile per app GUI)
# --add-data: include la cartella degli schemi JSON (usiamo ';' che è il separatore standard su Windows per PyInstaller)
# --collect-all: assicura che librerie complesse come faster_whisper e ctranslate2 includano tutti i loro file binari
echo "Creazione dell'eseguibile unico in corso..."
pyinstaller --noconfirm \
    --name "DENSO_Controller" \
    --onefile \
    --windowed \
    --add-data "src/schemas/*.json;src/schemas" \
    --collect-all faster_whisper \
    --collect-all ctranslate2 \
    run_gui.py

echo "=== Build Completato con Successo! ==="
echo "Troverai l'eseguibile all'interno della cartella 'dist'."
echo ""
echo "RICORDA: Distribuisci l'eseguibile (.exe) accompagnato dal file '.env' o '.env.example'."
echo "Senza il file .env nella stessa cartella dell'eseguibile, l'app non troverà gli IP e URL necessari."
