from PySide6.QtCore import QObject, Signal, Slot
import traceback

class VoiceWorker(QObject):
    ascoltoIniziato = Signal()
    elaborazioneAudio = Signal()
    trascrizioneCompletata = Signal(str)
    erroreVoce = Signal(str)

    def __init__(self, processor_class, mock=False):
        super().__init__()
        self.processor_class = processor_class
        self.mock = mock
        self.processor = None

    @Slot()
    def inizializza(self):
        try:
            if not self.mock:
                self.processor = self.processor_class()
        except Exception as e:
            self.erroreVoce.emit(f"Errore inizializzazione VoiceProcessor: {str(e)}")

    @Slot()
    def avviaAscolto(self):
        self.ascoltoIniziato.emit()
        try:
            if not self.mock:
                if not self.processor:
                    self.inizializza()
                # listen_and_transcribe è bloccante, per questo serve un worker
                testo = self.processor.listen_and_transcribe()
                self.elaborazioneAudio.emit() # Potremmo emetterlo subito prima del ritorno di transcribe se potessimo iniettarci in mezzo, ma lo emettiamo concettualmente
                self.trascrizioneCompletata.emit(testo)
            else:
                import time
                time.sleep(2) # Simula registrazione
                self.elaborazioneAudio.emit()
                time.sleep(1) # Simula trascrizione
                self.trascrizioneCompletata.emit("spostati un po' a destra")
        except Exception as e:
            err_msg = f"Errore vocale: {str(e)}\n{traceback.format_exc()}"
            self.erroreVoce.emit(err_msg)
