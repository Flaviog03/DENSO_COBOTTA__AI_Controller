from PySide6.QtCore import QObject, Signal, Slot
import traceback

class RobotWorker(QObject):
    # Segnali in uscita
    connessioneRiuscita = Signal(str)
    disconnesso = Signal()
    posizioneAggiornata = Signal(list)
    movimentoIniziato = Signal()
    movimentoCompletato = Signal(bool, str)
    erroreRobot = Signal(str)

    memoriaAggiornata = Signal(dict)

    def __init__(self, controller_class, ip_address, port, timeout, base_unit, mock=False):
        super().__init__()
        self.controller_class = controller_class
        self.ip = ip_address
        self.port = port
        self.timeout = timeout
        self.base_unit = base_unit
        self.mock = mock
        self.controller = None
        
    @Slot()
    def connetti(self):
        try:
            if not self.mock:
                self.controller = self.controller_class(
                    ip_address=self.ip, port=self.port, timeout=self.timeout, baseUnit=self.base_unit
                )
                self.controller.connect()
                # Impostiamo una velocità di sicurezza standard al 40%
                self.controller.setSpeedAccDec(40)
            
            self.connessioneRiuscita.emit(f"Connesso al controller: {self.ip}:{self.port} (Mock={self.mock})")
        except Exception as e:
            err_msg = f"Errore di connessione: {str(e)}\n{traceback.format_exc()}"
            self.erroreRobot.emit(err_msg)

    @Slot()
    def disconnetti(self):
        try:
            if self.controller and not self.mock:
                pass
            self.controller = None
            self.disconnesso.emit()
        except Exception as e:
            self.erroreRobot.emit(f"Errore in disconnessione: {str(e)}")

    @Slot()
    def rimuoviLimiti(self):
        try:
            if not self.mock and self.controller:
                self.controller.clearSafetyBounds()
                self.movimentoCompletato.emit(True, "Limiti di sicurezza rimossi. Il robot è di nuovo libero.")
        except Exception as e:
            self.erroreRobot.emit(f"Errore rimozione limiti: {str(e)}")

    @Slot(str, str)
    def impostaLimiti(self, pos1_name: str, pos2_name: str):
        try:
            if not self.mock and self.controller:
                pos1 = self.controller.savedPositions.get(pos1_name)
                pos2 = self.controller.savedPositions.get(pos2_name)
                if pos1 and pos2:
                    bounds = self.controller.setSafetyBoundsFromPositions(pos1, pos2)
                    self.movimentoCompletato.emit(True, f"Limiti di sicurezza impostati: {bounds}")
                else:
                    self.erroreRobot.emit("Una o entrambe le posizioni non sono presenti in memoria.")
        except Exception as e:
            self.erroreRobot.emit(f"Errore impostazione limiti: {str(e)}")

    @Slot(str, str, float)
    def eseguiComando(self, comando: str, direzione: str, moltiplicatore: float):
        self.movimentoIniziato.emit()
        try:
            if not self.mock:
                successo = self.controller.execute(comando, direzione, moltiplicatore)
                if successo:
                    if comando == "SAVE" or comando == "ROLLBACK":
                        self.memoriaAggiornata.emit(self.controller.savedPositions)
                    self.movimentoCompletato.emit(True, f"Comando {comando} completato.")
                else:
                    self.movimentoCompletato.emit(False, f"Comando {comando} fallito senza eccezioni.")
            else:
                import time
                time.sleep(1) # Simula tempo di esecuzione
                self.movimentoCompletato.emit(True, f"[MOCK] Comando {comando} completato.")
        except Exception as e:
            self.erroreRobot.emit(f"Errore esecuzione comando: {str(e)}")

    @Slot()
    def richiediPosizione(self):
        try:
            if not self.mock:
                if self.controller:
                    pos = self.controller.getActualPosition()
                    self.posizioneAggiornata.emit(pos)
            else:
                self.posizioneAggiornata.emit([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]) # Posizione mock
        except Exception as e:
            self.erroreRobot.emit(f"Errore lettura posizione: {str(e)}")
