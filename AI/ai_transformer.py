import os
import requests
import json
from typing import Any

class AITransformerError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class AITransformer:
    def __init__(self):
        # L'indirizzo del tuo LM Studio locale
        self.llm_url = os.getenv("LLM_URL")
        self.modello = os.getenv("LLM_MODEL")

        if not self.llm_url:
            raise AITransformerError("Errore: url della AI locale non trovato o non attivo in modalità server")
        if not self.modello:
            raise AITransformerError("Errore: il modello per l'AI scelto è sbagliato")

    def askAI(self, payload:dict[str, Any]) -> dict[str, Any]:
        """Invia una request ad un'AI locale e ritorna il risultato in JSON"""

        if self.llm_url is None:
            raise AITransformerError("Nessun url impostato per l'oggetto locale")

        risposta = requests.post(self.llm_url, json=payload)
        risposta.raise_for_status()
        return risposta.json()