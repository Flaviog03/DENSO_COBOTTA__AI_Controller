import json
import os
import sys

def getSchema(schema_name: str) -> dict:
    """Carica uno schema JSON da un file dalla cartella ./schemas | !!! Inserire il nome dello schema senza l'estensione .json"""
    filename = f"{schema_name}.json"
    candidates = []

    # Supporto per bundle PyInstaller (--onefile)
    if hasattr(sys, '_MEIPASS'):
        candidates.append(os.path.join(sys._MEIPASS, 'schemas', filename))
        candidates.append(os.path.join(sys._MEIPASS, 'src', 'schemas', filename))

    # Percorsi relativi alla posizione di ai_utilities.py
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(base_dir, '..', 'schemas', filename))
    candidates.append(os.path.join(base_dir, '..', 'src', 'schemas', filename))
    candidates.append(os.path.join(base_dir, 'schemas', filename))

    # Percorsi relativi alla directory di lavoro corrente
    candidates.append(os.path.join(os.getcwd(), 'src', 'schemas', filename))
    candidates.append(os.path.join(os.getcwd(), 'schemas', filename))

    for path in candidates:
        norm_path = os.path.normpath(path)
        if os.path.isfile(norm_path):
            with open(norm_path, 'r', encoding='utf-8') as f:
                return json.load(f)

    tried = "\n - ".join([os.path.normpath(p) for p in candidates])
    raise FileNotFoundError(f"Impossibile trovare lo schema '{filename}'. Percorsi verificati:\n - {tried}")

def getPayload(prompt:str, responseSchema:dict, params:str, model:str, schemaName:str):
    return {
        "model": model, 
        "messages": [
            {
                "role": "system", 
                "content": prompt
            }, 
            {
                "role": "user", 
                "content": params
            }
        ], 
        "temperature": 0.0, 
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": schemaName,
                "schema": responseSchema
            }
        }
    }