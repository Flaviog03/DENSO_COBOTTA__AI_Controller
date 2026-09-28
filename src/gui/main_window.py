import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QTextEdit, QGroupBox, QGridLayout, QSlider
)
from PySide6.QtCore import QThread, Qt, Slot, Signal

from gui.state import AppState, AppStateManager
from gui.workers.robot_worker import RobotWorker
from gui.workers.voice_worker import VoiceWorker
from gui.workers.ai_worker import AIWorker

from densoController import DensoController, RobotAction, DirectionMap
from brainProcessor import BrainProcessor
from voiceRecognition import VoiceProcessor

class MainWindow(QMainWindow):
    # Segnali di richiesta verso i Worker (Qt applica in automatico QueuedConnection tra thread)
    richiestaConnessione = Signal()
    richiestaAscolto = Signal()
    richiestaElaborazioneAI = Signal(str)
    richiestaMovimento = Signal(str, str, float)

    def __init__(self, mock_robot=False, mock_voice=False, mock_ai=False):
        super().__init__()
        self.setWindowTitle("DENSO COBOTTA - Controllo AI")
        self.resize(800, 600)
        
        self.state_manager = AppStateManager()
        
        self.mock_robot = mock_robot
        self.mock_voice = mock_voice
        self.mock_ai = mock_ai
        
        self.setup_ui()
        self.setup_threads_and_workers()
        self.update_ui_for_state(AppState.DISCONNECTED)

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Pannello Superiore: Stato Connessione
        conn_group = QGroupBox("Connessione")
        conn_layout = QHBoxLayout(conn_group)
        self.lbl_status = QLabel("Stato: DISCONNESSO")
        self.btn_connect = QPushButton("Connetti")
        self.btn_connect.clicked.connect(self.on_btn_connect_clicked)
        conn_layout.addWidget(self.lbl_status)
        conn_layout.addWidget(self.btn_connect)
        main_layout.addWidget(conn_group)

        # Pannello Voce/AI
        ai_group = QGroupBox("Comando Vocale / AI")
        ai_layout = QVBoxLayout(ai_group)
        self.btn_mic = QPushButton("Ascolta Comando")
        self.btn_mic.clicked.connect(self.on_btn_mic_clicked)
        self.lbl_transcript = QLabel("Trascrizione: ...")
        self.lbl_ai_result = QLabel("Comando AI: ...")
        
        # Pulsanti anteprima
        self.preview_layout = QHBoxLayout()
        self.btn_confirm = QPushButton("Conferma ed Esegui")
        self.btn_cancel = QPushButton("Annulla")
        self.btn_confirm.clicked.connect(self.on_btn_confirm_clicked)
        self.btn_cancel.clicked.connect(self.on_btn_cancel_clicked)
        self.preview_layout.addWidget(self.btn_confirm)
        self.preview_layout.addWidget(self.btn_cancel)
        
        ai_layout.addWidget(self.btn_mic)
        ai_layout.addWidget(self.lbl_transcript)
        ai_layout.addWidget(self.lbl_ai_result)
        ai_layout.addLayout(self.preview_layout)
        main_layout.addWidget(ai_group)

        # Pannello Log
        log_group = QGroupBox("Log Eventi")
        log_layout = QVBoxLayout(log_group)
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        log_layout.addWidget(self.txt_log)
        main_layout.addWidget(log_group)
        
        # Variabili temporanee per il comando AI elaborato
        self.pending_command = None

    def setup_threads_and_workers(self):
        # 1. Thread e Worker per il Robot
        self.thread_robot = QThread()
        ip = os.getenv("CONTROLLER_ADDRESS", "192.168.0.1")
        self.worker_robot = RobotWorker(DensoController, ip, 5007, 2000, 50, mock=self.mock_robot)
        self.worker_robot.moveToThread(self.thread_robot)
        
        self.richiestaConnessione.connect(self.worker_robot.connetti)
        self.richiestaMovimento.connect(self.worker_robot.eseguiComando)
        self.worker_robot.connessioneRiuscita.connect(self.on_robot_connected)
        self.worker_robot.erroreRobot.connect(self.on_error)
        self.worker_robot.movimentoCompletato.connect(self.on_robot_motion_completed)
        self.thread_robot.start()

        # 2. Thread e Worker per la Voce
        self.thread_voice = QThread()
        self.worker_voice = VoiceWorker(VoiceProcessor, mock=self.mock_voice)
        self.worker_voice.moveToThread(self.thread_voice)
        
        self.richiestaAscolto.connect(self.worker_voice.avviaAscolto)
        self.worker_voice.ascoltoIniziato.connect(lambda: self.log("In ascolto..."))
        self.worker_voice.trascrizioneCompletata.connect(self.on_voice_transcribed)
        self.worker_voice.erroreVoce.connect(self.on_error)
        self.thread_voice.start()

        # 3. Thread e Worker per l'AI
        self.thread_ai = QThread()
        azioni = RobotAction.get_allowed_actions()
        direzioni = DirectionMap.get_allowed_directions()
        self.worker_ai = AIWorker(BrainProcessor, azioni, direzioni, "responseFormat", mock=self.mock_ai)
        self.worker_ai.moveToThread(self.thread_ai)
        
        self.richiestaElaborazioneAI.connect(self.worker_ai.elaboraComando)
        self.worker_ai.comandoPronto.connect(self.on_ai_command_ready)
        self.worker_ai.erroreAI.connect(self.on_error)
        self.thread_ai.start()

    def log(self, message: str):
        self.txt_log.append(message)

    def update_ui_for_state(self, state: AppState):
        self.state_manager.transition_to(state)
        
        is_disconnected = (state == AppState.DISCONNECTED)
        is_idle = (state == AppState.IDLE)
        is_awaiting_conf = (state == AppState.AWAITING_CONFIRMATION)
        
        self.btn_connect.setEnabled(is_disconnected)
        self.btn_mic.setEnabled(is_idle)
        
        # Anteprima
        self.btn_confirm.setEnabled(is_awaiting_conf)
        self.btn_cancel.setEnabled(is_awaiting_conf)
        
        if is_idle:
            self.lbl_status.setText("Stato: INATTIVO (Pronto)")
        elif is_disconnected:
            self.lbl_status.setText("Stato: DISCONNESSO")
            self.lbl_transcript.setText("Trascrizione: ...")
            self.lbl_ai_result.setText("Comando AI: ...")

    # --- Slots GUI -> Workers ---
    
    def on_btn_connect_clicked(self):
        self.log("Tentativo di connessione in corso...")
        self.btn_connect.setEnabled(False)
        self.richiestaConnessione.emit()

    def on_btn_mic_clicked(self):
        self.update_ui_for_state(AppState.LISTENING)
        self.lbl_transcript.setText("Trascrizione: in ascolto...")
        self.richiestaAscolto.emit()

    def on_btn_confirm_clicked(self):
        if self.pending_command:
            self.update_ui_for_state(AppState.MOVING)
            self.log(f"Esecuzione in corso: {self.pending_command}")
            self.richiestaMovimento.emit(
                self.pending_command["comando"],
                self.pending_command["direzione"],
                float(self.pending_command["moltiplicatore"])
            )
            self.pending_command = None

    def on_btn_cancel_clicked(self):
        self.log("Comando annullato dall'utente.")
        self.pending_command = None
        self.update_ui_for_state(AppState.IDLE)

    # --- Slots Workers -> GUI ---

    @Slot(str)
    def on_robot_connected(self, info: str):
        self.log(info)
        self.update_ui_for_state(AppState.IDLE)

    @Slot(str)
    def on_voice_transcribed(self, testo: str):
        self.lbl_transcript.setText(f"Trascrizione: {testo}")
        self.log(f"Trascrizione completata: '{testo}'")
        self.update_ui_for_state(AppState.PROCESSING_AI)
        self.richiestaElaborazioneAI.emit(testo)

    @Slot(dict)
    def on_ai_command_ready(self, risultato: dict):
        self.lbl_ai_result.setText(f"Comando AI: {risultato}")
        self.log(f"AI Output: {risultato}")
        
        # Controlliamo se c'è un errore logico o una richiesta di uscita
        if risultato.get("comando") == "ERROR":
            self.log("L'AI ha interpretato il comando come ERRORE. Ignorato.")
            self.update_ui_for_state(AppState.IDLE)
        elif risultato.get("comando") == "EXIT":
            self.log("Ricevuto comando di chiusura (EXIT). Disconnessione in corso...")
            self.close()  # Chiude la finestra in modo pulito invocando la disconnessione
        else:
            self.pending_command = risultato
            self.update_ui_for_state(AppState.AWAITING_CONFIRMATION)

    @Slot(bool, str)
    def on_robot_motion_completed(self, success: bool, msg: str):
        self.log(f"Movimento completato: {success} - {msg}")
        self.update_ui_for_state(AppState.IDLE)

    @Slot(str)
    def on_error(self, err_msg: str):
        self.log(f"[ERRORE] {err_msg}")
        # Gestione rozza dell'errore: torniamo in idle, tranne se il robot si è disconnesso
        if self.state_manager.current_state != AppState.DISCONNECTED:
            self.update_ui_for_state(AppState.IDLE)

    def closeEvent(self, event):
        # Chiusura sicura dei thread
        self.thread_robot.quit()
        self.thread_voice.quit()
        self.thread_ai.quit()
        self.thread_robot.wait()
        self.thread_voice.wait()
        self.thread_ai.wait()
        event.accept()
