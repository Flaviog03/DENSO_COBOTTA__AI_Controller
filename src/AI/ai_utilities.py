import json
import os

def getSchema(schema_name:str )-> dict:
    """Carica uno schema JSON da un file dalla cartella ./schemas | !!! Inserire il nome dello schema senza l'estensione .json"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, '..', 'schemas', f"{schema_name}.json")
    with open(path, 'r') as f:
        return json.load(f)

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