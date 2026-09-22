import os
import json
from AI.ai_transformer import AITransformer, AITransformerError
from AI import ai_utilities
from dotenv import load_dotenv
from densoController import DirectionMap, RobotAction
from typing import Any

class BrainProcessorError(Exception):
    def __init__(self, message):
            self.message = message
            super().__init__(self.message)

class BrainProcessor:
    def __init__(self, actions, directions, responseSchemaName):
        # L'inizializzazione legge automaticamente le variabili d'ambiente
        try:
            self.ai = AITransformer()
        except AITransformerError as e:
            print(f"Inizializzazione fallita: {e}")
            raise
            
        # Carichiamo lo schema strutturato dalla cartella schemas/
        self.schema = ai_utilities.getSchema(responseSchemaName)

        # Inietto le azioni e le direzioni nello schema
        self.schema["properties"]["comando"]["enum"] = actions
        self.schema["properties"]["direzione"]["enum"] = directions

        # Il System Prompt che istruisce il modello sulle azioni consentite
        self.system_prompt = f"""
                Sei il traduttore logico di un braccio robotico DENSO.
                Il tuo unico scopo e' estrarre comandi operativi da frasi in italiano e convertirli IN UN FORMATO ESCLUSIVAMENTE JSON. 
                NON SCRIVERE NESSUNA PAROLA O SPIEGAZIONE FUORI DAL JSON.

                AZIONI CONSENTITE: {actions}.
                DIREZIONI CONSENTITE (solo per le azioni che implicano un movimento del braccio e non della pinza, es: TRANSLATE e ROTATE): {directions}.

                REGOLE FISSE:
                1. Se l'utente chiede di spostarsi, usa TRANSLATE e specifica una tra le seguenti direzioni [UP, DOWN, FORWARD, BACKWARD].
                2. Se l'utente chiede di ruotarsi, usa ROTATE e specifica una tra le seguenti direzioni [RIGHT, LEFT].
                3. Se non viene indicata una distanza esatta, usa sempre moltiplicatore: 1. Se specificata, inserisci un numero da 1 a 5 in base all'entita' dello spostamento richiesto, eventualmente anche frazionario.
                4. Se l'utente chiede di prendere, pinzare o afferrare, usa GRAB (senza direzione e moltiplicatore).
                5. Se l'utente chiede di mollare, lasciare o aprire, usa RELEASE.
                6. Se l'utente richiede più azioni contemporaneamente restituisci ERROR in tutti i campi stringa e -1 in tutti i campi number

                ESEMPI DI RISPOSTA:
                Input: vai in avanti di poco
                Output: azione: TRANSLATE, direzione: FORWARD, moltiplicatore: 1

                Input: spostati un po' a destra
                Output: azione: ROTATE, direzione: RIGHT, moltiplicatore: 3

                Input: spostati molto a sinistra
                Output: azione: ROTATE, direzione: LEFT, moltiplicatore: 5

                Input: spostati a sinistra di 2 unità
                Output: azione: ROTATE, direzione: LEFT, moltiplicatore: 2
                
                Input: spostati indietro di 1/2 di unità
                Output: azione: TRANSLATE, direzione: BACKWARD, moltiplicatore: 0.5

                Input: spostati avanti di 1/4 di unità
                Output: azione: TRANSLATE, direzione: FORWARD, moltiplicatore: 0.25

                Input: spostati avanti di 3/4 di unità
                Output: azione: TRANSLATE, direzione: FORWARD, moltiplicatore: 0.75

                Input: chiudi la pinza e prendi il peluche
                Output: azione: GRAB

                Input: lascia andare
                Output: azione: RELEASE

                Input: vai in avanti di 1 unità e ruota
                Output: azione: ERROR, direzione: ERROR, moltiplicatore: -1

                Input: ruota in avanti
                Output: azione: ERROR, direzione: ERROR, moltiplicatore: -1

                Input: ruota in alto
                Output: azione: ERROR, direzione: ERROR, moltiplicatore: -1

                Input: ruota a sinistra e vai avanti
                Output: azione: ERROR, direzione: ERROR, moltiplicatore: -1

                Input: vai indietro di molto e afferra
                Output: azione: ERROR, direzione: ERROR, moltiplicatore: -1
            """

    def process_command(self, user_text: str) -> dict[str, Any]:
        """Questa funzione permette di interagire con il cervello robotico facendogli processare un comando testuale in un comando di movimentazione come dizionario, il dizionario è costruito come specificato da schemas responseFormat.json """
        # print(f"Analisi del comando: '{user_text}'...")

        try:
            if self.ai.modello is None:
                raise AITransformerError("Il modello Ai non è stato caricato correttamente")
            
            # Generiamo il dizionario payload formattato con i ruoli system e user
            payload = ai_utilities.getPayload(
                prompt=self.system_prompt,
                responseSchema=self.schema,
                params=user_text,
                model=self.ai.modello,
                schemaName="conversioneTestuale"
            )
            
            # Inviamo la request HTTP a LM Studio
            risposta = self.ai.askAI(payload=payload)
            
            # Poiché LM Studio restituisce un JSON in formato OpenAI-compatibile,
            # il contenuto vero e proprio si trova dentro la lista 'choices'
            raw_content = risposta['choices'][0]['message']['content']
            
            # Il contenuto è una stringa in formato JSON, va convertito in dizionario Python
            json_data = json.loads(raw_content)
            return json_data
        
        except AITransformerError as e:
            raise BrainProcessorError(f"Errore di connessione o URL mancante: {e}")
        except (KeyError, json.JSONDecodeError) as e:
            raise BrainProcessorError(f"Errore nella decodifica della risposta di LM Studio: {e}")

if __name__ == "__main__":
    load_dotenv()
    cervello = BrainProcessor(actions=RobotAction.get_allowed_actions(), directions=DirectionMap.get_allowed_directions(), responseSchemaName="responseFormat")
    risultato = cervello.process_command("ruota il braccio a destra di 3/4 di unità")

    for key, value in risultato.items():
        print(f"Key: {key}\nValue: {value}")