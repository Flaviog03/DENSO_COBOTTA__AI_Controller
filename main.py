from voiceRecognition import VoiceProcessor
from densoController import RobotAction, DirectionMap
from pybcapclient.bcapclient import BCAPClient
from densoController import DensoController, ControllerError
from brainProcessor import BrainProcessor, BrainProcessorError
from speech_recognition.exceptions import WaitTimeoutError
from dotenv import load_dotenv
import time
import os

# Imposta l'IP del COBOTTA reale (di fabbrica è 192.168.0.1)
# Se stai testando su WINCAPS III, usa "172.20.10.2" o "127.0.0.1"[cite: 2, 4]
### PARAMETERS
ROBOT_PORT = 5007
TIMEOUT_MS = 2000
SPEED_LIMIT = 40
BASE_UNIT = 50          # Dimensione dell'unità base in mm
MOCK_EAR = True
MOCK_AI = True
MOCK_CONTROLLER = False

def provaMovimenti() -> list:
    azioni = RobotAction.get_allowed_actions()
    direzioni = DirectionMap.get_allowed_directions()

    print("Scegli un'azione (indice), una direzione (indice) e un moltiplicatore separati da spazi (es: 0 0 1 -> Translate Forward 1):")
    for azione in azioni:
        print(f"\tAzione : {azione} -> valore : {azioni.index(azione)}")
    for direzione in direzioni:
        print(f"\tDirezione : {direzione} -> valore : {direzioni.index(direzione)}")

    comando = input().split(" ")
              
    if int(comando[0]) == RobotAction.SAVE and len(comando[1]) == 1 and comando[1].isalpha():
        return [azioni[int(comando[0])], comando[1].upper(), int(comando[2])]

    if int(comando[0]) == RobotAction.ROLLBACK and len(comando[1]) == 1 and comando[1].isalpha():
        return [azioni[int(comando[0])], comando[1].upper(), int(comando[2])]

    return [azioni[int(comando[0])], direzioni[int(comando[1])], int(comando[2])]

if __name__ == "__main__":
    try:
        # 1.0 Caricamento delle variabili di ambiente
        load_dotenv()

        ROBOT_IP = os.getenv("CONTROLLER_ADDRESS")

        if not ROBOT_IP:
            raise ControllerError("Non è stato possibile trovare l'ip del robot")

        # 1.1 Connessione al controller
        controller = DensoController(ip_address=ROBOT_IP, port=ROBOT_PORT, timeout=TIMEOUT_MS)
        controller.connect()
        comandoUtente = ""

        # 1.2 Imposto la velocità al 40%
        controller.setSpeedAccDec(SPEED_LIMIT)

        # 1.3 Inizializzazione "orecchio virtuale"
        if not MOCK_EAR:
            orecchio = VoiceProcessor()

        # 1.4 Inizializzazione "cervello artificiale"
        azioniConsentite = RobotAction.get_allowed_actions()
        direzioniConsentite = DirectionMap.get_allowed_directions()
        cervello = BrainProcessor(actions=azioniConsentite, directions=direzioniConsentite, responseSchemaName="responseFormat")

        # 2 - Corpo principale del programma
        while comandoUtente != "Esci":
            try:
                    
                # Reset comandoUtente
                comandoUtente = ""

                # 2.0 Calcolo statistiche
                startingTime = time.time()

                # 2.1 Acquisizione input
                posizioneAttuale = controller.getActualPosition()

                if not MOCK_EAR:
                    comandoUtente = orecchio.listen_and_transcribe()
                    print(f"Comando audio : {comandoUtente}")
                else:
                    # Faccio un mock 
                    comandoUtente = "vai indietro"

                if not MOCK_AI:
                    risultato = cervello.process_command(comandoUtente)

                    azione = risultato["comando"]
                    direzione = risultato["direzione"]
                    moltiplicatore = risultato["moltiplicatore"]
                else:   # Mock dell'AI (fatto per problemi di ram)
                    listaAcquisita = provaMovimenti()
                    azione = listaAcquisita[0]
                    direzione = listaAcquisita[1]
                    moltiplicatore = listaAcquisita[2]

                print("Inizio movimentazione...")

                if azione == RobotAction.ERROR.name:
                    print("Qualcosa non è andato a buon fine, assicurati di menzionare un solo comando alla volta")
                    continue

                if azione == RobotAction.EXIT.name:
                    print("Arrivederci...")
                    break
                
                controller.execute(azione, direzione, moltiplicatore)

                endingTime = time.time()

                print(f"Tempo totale di esecuzione: {int(endingTime-startingTime)} secondi")
            except ControllerError as e:
                print(f"ControllerError : {e}")
                continue
            except BrainProcessorError as e:
                print(f"BrainProcessorError : {e}")
                continue
            except WaitTimeoutError as e:
                print(f"WaitTimeoutError : {e}")
                continue
    except Exception as e:
        print(e)
    finally:
        controller.disconnect()


"""
IDEE: 
    - Gestione delle eccezioni out of range

IMPLEMENTATE:
    - Salva la posizione del robot tramite comando vocale
    - Nuova istruzione ROLLBACK
"""

     



