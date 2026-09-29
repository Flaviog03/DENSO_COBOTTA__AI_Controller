#!/bin/bash
set -e

echo "=== Configurazione Ambiente e Avvio (Windows Bash) ==="

# 1. Creazione ambiente virtuale se non esiste
if [ ! -d "venv" ]; then
    echo "Creazione virtual environment in corso..."
    python -m venv venv
fi

# 2. Attivazione venv
# In bash su windows l'attivazione si fa puntando a Scripts o bin a seconda di come è stato creato
echo "Attivazione virtual environment..."
if [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "[ERRORE] Impossibile trovare lo script di attivazione del venv."
    exit 1
fi

# 3. Installazione dipendenze
echo "Installazione/Verifica dipendenze da requirements.txt..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 4. Copia .env se manca
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "Copia del file .env.example in .env..."
        cp .env.example .env
    fi
fi

# 5. Esecuzione
echo "Avvio della GUI in corso..."
python run_gui.py
