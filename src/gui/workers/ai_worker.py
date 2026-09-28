from PySide6.QtCore import QObject, Signal, Slot
import traceback

class AIWorker(QObject):
    elaborazioneIniziata = Signal()
    comandoPronto = Signal(dict)
    erroreAI = Signal(str)

    def __init__(self, processor_class, azioni, direzioni, schema_name, mock=False):
        super().__init__()
        self.processor_class = processor_class
        self.azioni = azioni
        self.direzioni = direzioni
        self.schema_name = schema_name
        self.mock = mock
        self.processor = None

    @Slot()
    def inizializza(self):
        try:
            if not self.mock:
                self.processor = self.processor_class(
                    actions=self.azioni,
                    directions=self.direzioni,
                    responseSchemaName=self.schema_name
                )
        except Exception as e:
            self.erroreAI.emit(f"Errore inizializzazione BrainProcessor: {str(e)}")

    @Slot(str)
    def elaboraComando(self, testo: str):
        self.elaborazioneIniziata.emit()
        try:
            if not self.mock:
                if not self.processor:
                    self.inizializza()
                risultato = self.processor.process_command(testo)
                # Il risultato è un dict del tipo: {"comando": "...", "direzione": "...", "moltiplicatore": ...}
                self.comandoPronto.emit(risultato)
            else:
                import time
                time.sleep(1) # Simula l'API Call
                self.comandoPronto.emit({
                    "comando": "ROTATE",
                    "direzione": "RIGHT",
                    "moltiplicatore": 3
                })
        except Exception as e:
            err_msg = f"Errore AI: {str(e)}\n{traceback.format_exc()}"
            self.erroreAI.emit(err_msg)
