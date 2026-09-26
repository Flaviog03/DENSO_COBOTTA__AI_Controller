from pybcapclient.bcapclient import BCAPClient
import time
from enum import IntEnum, StrEnum
import os
from dotenv import load_dotenv
from pybcapclient.orinexception import ORiNException

class ControllerError(Exception):
    def __init__(self, message):
            self.message = message
            super().__init__(self.message)

class DirectionMap(StrEnum):
    """
    Il primo elemento è un numero ed è l'indice dell'asse all'interno del vettore delle coordinate
    Il secondo elemento è il  che indica il verso del vettore individuato da uno dei tre assi
    """
    FORWARD  = "0,+1"
    BACKWARD = "0,-1"
    RIGHT    = "1,-1"
    LEFT     = "1,+1"
    UP       = "2,+1"
    DOWN     = "2,-1"
    ERROR    = "X,-X"
    NULL     = "NaN,NaN"

    @classmethod
    def get_allowed_directions(cls) -> list[str]:
        """Restituisce le direzioni consentite leggendole dinamicamente dall'Enum"""
        return [direction.name for direction in cls]
    
class RobotAction(IntEnum):
    TRANSLATE = 0
    ROTATE = 1
    GRAB = 2
    RELEASE = 3
    ERROR = 4
    EXIT = 5
    SAVE = 6
    ROLLBACK = 7

    @classmethod
    def get_allowed_actions(cls) -> list[str]:
        """Restituisce le azioni consentite leggendole dinamicamente dall'Enum"""
        return [action.name for action in cls]

class DensoController:
    def __init__(self, ip_address="192.168.0.1", port=5007, timeout=2000, baseUnit=50):
        self.ip = ip_address
        self.port = port
        self.baseUnit = baseUnit
        self.lastPosition = []
        self.savedPositions : dict[str, list[float]] = {}

        # Inizializza il client: l'apertura del socket avviene automaticamente qui (timeout 2000 ms)
        self.bcap = BCAPClient(self.ip, self.port, timeout) 
        print("Connessione aperta")

        self.bcap.service_start("")
        print("Servizio b-CAP avviato")

        self.h_ctrl = None
        self.h_rob = None
        self.CurPosHandl = None
        self.h_pinza = None

    def connect(self):
        # Connessione al controller virtuale o reale
        Name = ""
        Provider = "CaoProv.DENSO.VRC"   # usa "CaoProv.DENSO.VRC9" per un RC9
        Machine = "localhost"
        Option = ""
        self.h_ctrl = self.bcap.controller_connect(Name, Provider, Machine, Option)
        print("Connesso al controller, handle:", self.h_ctrl)

        # --- Handle dell'oggetto Robot ---
        self.h_rob = self.bcap.controller_getrobot(self.h_ctrl, "Arm", "")
        print("Handle Robot ottenuto:", self.h_rob)

        # Dopo aver ottenuto self.h_rob...
        self.CurPosHandl = self.bcap.robot_getvariable(self.h_rob, "@CURRENT_POSITION", "")

        # --- Handle della pinza ---
        # self.h_pinza = self.bcap.controller_getvariable(self.h_ctrl, "IO_PINZA", "")

        # --- Presa di controllo del braccio ---
        self.bcap.robot_execute(self.h_rob, "TakeArm", [0, 0])
        print("TakeArm eseguito")

        # --- Accensione motori ---
        self.bcap.robot_execute(self.h_rob, "Motor", [1, 0])
        print("Motori ON")

        # --- Velocità/accelerazione/decelerazione esterne (%) - bassa per sicurezza ---
        self.bcap.robot_execute(self.h_rob, "ExtSpeed", [40, 100, 100])
        print("Velocità impostata al 20%")

    def setSpeedAccDec(self, speed : int, acc=100, dec=100):
        """ Imposta la velocità/accelerazione/decelerazione del robot """
        self.bcap.robot_execute(self.h_rob, "ExtSpeed", [speed, acc, dec])
        print(f"Velocità impostata al {speed}%")

    def getActualPosition(self) -> list[float]:
        """ Restituisce le coordinate attuali del robot come elementi interi di una lista """
        pos_iniziale = self.bcap.variable_getvalue(self.CurPosHandl)
        return list(pos_iniziale)

    def execute(self, command:str, direction:str, moltiplicator:int) -> bool:

        # Se il comando è un salvataggio
        if command == RobotAction.SAVE.name:
            if ord(direction.capitalize()) < ord("A") or ord(direction.capitalize()) > ord("Z"):
                raise ControllerError("Nome del salvataggio non valido, deve essere una lettera")
            self.savedPositions[direction.capitalize()] = self.getActualPosition()
            return True
        
        # Controllo preliminare sulla pinza
        if command == RobotAction.GRAB.name:
            try:
                # HandMoveH: [Forza in Newton (6-15), Direzione (True = chiudi)]
                # Si ferma da sola contro l'oggetto solido mantenendo 10N di presa!
                self.bcap.controller_execute(self.h_ctrl, "HandMoveH", [10, True])
                print("Chiusura pinza con controllo di forza (10N).")

                preso = self.bcap.controller_execute(self.h_ctrl, "HandHoldState", None)
                if preso:
                    print("Presa confermata: c'è un oggetto tra le dita!")
                    return True
                else:
                    print("Pinza chiusa a vuoto: nessun oggetto rilevato.")
                    return False
            except ORiNException as e:
                raise ControllerError(f"Avviso Pinza (b-CAP {e}): verifica se sei in simulazione VRC.")
            finally:
                return False
        if command == RobotAction.RELEASE.name:
            self.bcap.controller_execute(self.h_ctrl, "HandMoveA", [30, 100])
            return True
        if command == RobotAction.ERROR.name:
            raise ControllerError(f"È stato generato un errore!")

        # Ottengo posizione attuale
        actualPosition = self.getActualPosition()
        print(f"Pos attuale: {actualPosition}")

        # Ottengo gli indici corrispondenti che ho precedentemente mappato
        indiceAsse = int(DirectionMap[direction].split(",")[0])
        verso = int(DirectionMap[direction].split(",")[1])

        # Prendo la posizione target
        posTarget:list[float] = list(actualPosition)

        # Calcolo la nuova posizione come
        # verso = +/- 1
        # self.baseUnit = unità base di movimentazione
        # moltiplicator = quanto vogliamo effettivamente spostarci 
        posTarget[indiceAsse] += float(verso) * float(self.baseUnit) * float(moltiplicator)

        try:
            if command == RobotAction.TRANSLATE.name:
                Pose = [posTarget, "P", "@E"]
                self.bcap.robot_move(self.h_rob, 1, Pose, "")
                return True
            if command == RobotAction.ROTATE.name:
                Pose = [posTarget, "P", "@E"]
                self.bcap.robot_move(self.h_rob, 1, Pose, "")
                return True
        except ORiNException as e:
            raise ControllerError(f"[ERRORE B-CAP] Posizione non raggiungibile dal braccio (codice {e.hresult}).")
        finally:
            self.bcap.controller_execute(self.h_ctrl, "ClearError")
            return False

    def esegui_presa(self, target_variable="P1"):
        """
        Comanda al robot di spostarsi sulla variabile calcolata dalla visione.
        """
        print(f"Inizio traiettoria verso {target_variable}...")
        
        movimento = f"@E {target_variable}"
        self.bcap.robot_execute(self.h_rob, "Move", [1, movimento])
        
        print("Posizione raggiunta! (Simulazione chiusura pinza in corso...)")
        time.sleep(1) 

    def disconnect(self):
        # --- Spegnimento motori ---
        self.bcap.robot_execute(self.h_rob, "Motor", [0, 0])
        print("Motori OFF")

        if self.CurPosHandl:
            self.bcap.variable_release(self.CurPosHandl)
        if self.h_rob:
            self.bcap.robot_execute(self.h_rob, "GiveArm", None)
            self.bcap.robot_release(self.h_rob)
            print("GiveArm eseguito e Robot rilasciato")
        if self.h_ctrl:
            self.bcap.controller_disconnect(self.h_ctrl)
            print("Controller disconnesso")
        self.bcap.service_stop()
        print("Servizio b-CAP fermato")

# ==========================================
# ESECUZIONE DEL TEST
# ==========================================
if __name__ == "__main__":
    load_dotenv()
    ipController = os.getenv("CONTROLLER_ADDRESS")

    if ipController is None:
        raise Exception("Non è stato possibile caricare ")
    
    robot = DensoController(ip_address=ipController) # L'IP della tua VM Windows
    
    try:
        robot.connect()
    
        # 2. Comando effettivo di spostamento alla variabile
        robot.esegui_presa("P1")
        
    except Exception as e:
        print(f"Errore b-CAP: {e}")
    finally:
        robot.disconnect()