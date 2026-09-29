import os
import dotenv
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QTextEdit, QGroupBox, QGridLayout, QSlider,
    QTabWidget, QFormLayout, QLineEdit, QMessageBox, QCheckBox, QComboBox
)
from PySide6.QtCore import QThread, Qt, Slot, Signal

from gui.state import AppState, AppStateManager
from gui.workers.robot_worker import RobotWorker
from gui.workers.voice_worker import VoiceWorker
from gui.workers.ai_worker import AIWorker

from densoController import DensoController, RobotAction, DirectionMap
from brainProcessor import BrainProcessor
from voiceRecognition import VoiceProcessor
import requests

class ChatWorker(QThread):
    rispostaPronta = Signal(str)
    errore = Signal(str)

    def __init__(self, url, prompt, manual_context=""):
        super().__init__()
        self.url = url
        self.prompt = prompt
        self.manual_context = manual_context

    def run(self):
        try:
            payload = {
                "messages": [
                    {"role": "system", "content": self.manual_context},
                    {"role": "user", "content": self.prompt}
                ],
                "temperature": 0.7
            }
            res = requests.post(self.url, json=payload, timeout=60)
            res.raise_for_status()
            data = res.json()
            testo_risposta = data['choices'][0]['message']['content']
            self.rispostaPronta.emit(testo_risposta)
        except Exception as e:
            self.errore.emit(str(e))

class MainWindow(QMainWindow):
    # Segnali di richiesta verso i Worker (Qt applica in automatico QueuedConnection tra thread)
    richiestaConnessione = Signal()
    richiestaAscolto = Signal()
    richiestaElaborazioneAI = Signal(str)
    richiestaMovimento = Signal(str, str, float)
    richiestaLimiti = Signal(str, str)
    richiestaRimozioneLimiti = Signal()

    def __init__(self, mock_robot=False, mock_voice=False, mock_ai=False):
        super().__init__()
        self.setWindowTitle("DENSO COBOTTA - Controllo AI")
        self.resize(800, 700)
        
        self.state_manager = AppStateManager()
        
        self.mock_robot = mock_robot
        self.mock_voice = mock_voice
        self.mock_ai = mock_ai
        
        self.setup_ui()
        self.setup_threads_and_workers()
        self.update_ui_for_state(AppState.DISCONNECTED)

    def closeEvent(self, event):
        # Disconnettiamo il robot in sicurezza se è ancora connesso
        if hasattr(self, 'worker_robot') and self.worker_robot.controller:
            try:
                self.worker_robot.controller.disconnect()
            except Exception:
                pass
                
        # Arrestiamo tutti i thread di Qt
        for thread_name in ['thread_robot', 'thread_voice', 'thread_ai', 'chat_worker']:
            if hasattr(self, thread_name):
                t = getattr(self, thread_name)
                if t and t.isRunning():
                    t.quit()
                    t.wait(1000)
        event.accept()

    def setup_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        self.tab_main = QWidget()
        self.setup_main_tab(self.tab_main)
        self.tabs.addTab(self.tab_main, "Controllo Principale")
        
        self.tab_config = QWidget()
        self.setup_config_tab(self.tab_config)
        self.tabs.addTab(self.tab_config, "Configurazione")
        
        self.tab_memory = QWidget()
        self.setup_memory_tab(self.tab_memory)
        self.tabs.addTab(self.tab_memory, "Memoria Posizioni")
        
        self.tab_manual = QWidget()
        self.setup_manual_tab(self.tab_manual)
        self.tabs.addTab(self.tab_manual, "Manuale")
        
        self.tab_chat = QWidget()
        self.setup_chat_tab(self.tab_chat)
        self.tabs.addTab(self.tab_chat, "Aiuto (Chat AI)")
        
        self.pending_command = None

    def setup_main_tab(self, parent_widget):
        main_layout = QVBoxLayout(parent_widget)

        # Pannello Superiore: Stato Connessione
        conn_group = QGroupBox("Connessione")
        conn_layout = QHBoxLayout(conn_group)
        self.lbl_status = QLabel("Stato: DISCONNESSO")
        self.btn_connect = QPushButton("Connetti")
        self.btn_disconnect = QPushButton("Disconnetti")
        
        self.btn_connect.clicked.connect(self.on_btn_connect_clicked)
        self.btn_disconnect.clicked.connect(self.on_btn_disconnect_clicked)
        
        conn_layout.addWidget(self.lbl_status)
        conn_layout.addWidget(self.btn_connect)
        conn_layout.addWidget(self.btn_disconnect)
        main_layout.addWidget(conn_group)

        # Pannello Voce/AI
        ai_group = QGroupBox("Comando Vocale / AI")
        ai_layout = QVBoxLayout(ai_group)
        # Spia Microfono
        mic_layout = QHBoxLayout()
        self.btn_mic = QPushButton("Ascolta Comando")
        self.btn_mic.clicked.connect(self.on_btn_mic_clicked)
        self.lbl_mic_led = QLabel()
        self.lbl_mic_led.setFixedSize(20, 20)
        self.lbl_mic_led.setStyleSheet("background-color: gray; border-radius: 10px; border: 1px solid black;")
        mic_layout.addWidget(self.btn_mic)
        mic_layout.addWidget(self.lbl_mic_led)
        
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
        
        ai_layout.addLayout(mic_layout)
        ai_layout.addWidget(self.lbl_transcript)
        ai_layout.addWidget(self.lbl_ai_result)
        ai_layout.addLayout(self.preview_layout)
        main_layout.addWidget(ai_group)
        
        # Pannello Simulazione (nascosto di default)
        self.mock_panel = QGroupBox("Comandi Manuali (Simulazione Vocale attiva)")
        mock_layout = QVBoxLayout(self.mock_panel)
        
        # Testo manuale
        text_layout = QHBoxLayout()
        self.le_manual_text = QLineEdit()
        self.le_manual_text.setPlaceholderText("Es: spostati su")
        self.btn_send_manual = QPushButton("Invia Testo")
        self.btn_send_manual.clicked.connect(lambda: self.on_manual_command(self.le_manual_text.text()))
        text_layout.addWidget(self.le_manual_text)
        text_layout.addWidget(self.btn_send_manual)
        mock_layout.addLayout(text_layout)
        
        # D-PAD
        dpad_layout = QGridLayout()
        
        btn_up = QPushButton("Su")
        btn_forward = QPushButton("Avanti")
        btn_open = QPushButton("Apri Pinza")
        
        btn_left = QPushButton("Sinistra")
        btn_down = QPushButton("Giù")
        btn_right = QPushButton("Destra")
        btn_backward = QPushButton("Indietro")
        btn_close = QPushButton("Chiudi Pinza")
        
        dpad_layout.addWidget(btn_up, 0, 1)
        dpad_layout.addWidget(btn_left, 1, 0)
        dpad_layout.addWidget(btn_down, 1, 1)
        dpad_layout.addWidget(btn_right, 1, 2)
        
        dpad_layout.addWidget(btn_forward, 0, 3)
        dpad_layout.addWidget(btn_backward, 1, 3)
        
        dpad_layout.addWidget(btn_open, 0, 4)
        dpad_layout.addWidget(btn_close, 1, 4)
        
        btn_up.clicked.connect(lambda: self.send_direct_command("TRANSLATE", "UP", 1))
        btn_down.clicked.connect(lambda: self.send_direct_command("TRANSLATE", "DOWN", 1))
        btn_left.clicked.connect(lambda: self.send_direct_command("TRANSLATE", "LEFT", 1))
        btn_right.clicked.connect(lambda: self.send_direct_command("TRANSLATE", "RIGHT", 1))
        btn_forward.clicked.connect(lambda: self.send_direct_command("TRANSLATE", "FORWARD", 1))
        btn_backward.clicked.connect(lambda: self.send_direct_command("TRANSLATE", "BACKWARD", 1))
        btn_open.clicked.connect(lambda: self.send_direct_command("RELEASE", "NULL", 0))
        btn_close.clicked.connect(lambda: self.send_direct_command("GRAB", "NULL", 0))
        
        mock_layout.addLayout(dpad_layout)
        self.mock_panel.setVisible(self.mock_voice)
        main_layout.addWidget(self.mock_panel)

        # Pannello Log
        logs_layout = QVBoxLayout()
        
        log_group = QGroupBox("Log Eventi")
        log_layout = QVBoxLayout(log_group)
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        log_layout.addWidget(self.txt_log)
        
        mov_log_group = QGroupBox("Log Spostamenti")
        mov_log_layout = QVBoxLayout(mov_log_group)
        self.txt_movement_log = QTextEdit()
        self.txt_movement_log.setReadOnly(True)
        self.txt_movement_log.setMaximumHeight(80)
        mov_log_layout.addWidget(self.txt_movement_log)
        
        logs_layout.addWidget(log_group)
        logs_layout.addWidget(mov_log_group)
        main_layout.addLayout(logs_layout)

    def setup_config_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        
        env_group = QGroupBox("Impostazioni di Rete")
        form_layout = QFormLayout(env_group)
        
        self.le_controller_ip = QLineEdit()
        self.le_controller_ip.setText(os.getenv("CONTROLLER_ADDRESS", "192.168.0.1"))
        form_layout.addRow("Indirizzo IP Controller:", self.le_controller_ip)
        
        self.le_llm_ip = QLineEdit()
        full_url = os.getenv("LLM_URL", "http://localhost:1234/v1/chat/completions")
        # Estrai IP dal formato "http://IP:PORT/..."
        ip_only = full_url.replace("http://", "").split(":")[0]
        self.le_llm_ip.setText(ip_only)
        form_layout.addRow("IP Server AI (LM Studio):", self.le_llm_ip)
        
        self.le_llm_model = QLineEdit()
        self.le_llm_model.setText(os.getenv("LLM_MODEL", "meta-llama-3.1-8b-instruct"))
        form_layout.addRow("Modello LLM:", self.le_llm_model)
        
        self.btn_save_config = QPushButton("Salva Configurazione Rete")
        self.btn_save_config.clicked.connect(self.on_save_config_clicked)
        form_layout.addRow(self.btn_save_config)
        
        layout.addWidget(env_group)

        # Configurazione Comandi
        cmd_group = QGroupBox("Impostazioni Comandi")
        cmd_layout = QVBoxLayout(cmd_group)
        self.cb_auto_send = QCheckBox("Invio Automatico Comandi (scavalca la conferma)")
        self.cb_auto_send.setChecked(os.getenv("AUTO_SEND", "False").lower() == "true")
        cmd_layout.addWidget(self.cb_auto_send)
        layout.addWidget(cmd_group)
        
        mock_group = QGroupBox("Simulazione (Mock) - Si resetta al riavvio")
        mock_layout = QVBoxLayout(mock_group)
        
        self.cb_mock_robot = QCheckBox("Simula Robot (Non muove il braccio vero)")
        self.cb_mock_robot.setChecked(self.mock_robot)
        self.cb_mock_robot.toggled.connect(self.on_mock_robot_toggled)
        mock_layout.addWidget(self.cb_mock_robot)
        
        self.cb_mock_voice = QCheckBox("Simula Voce (Mostra pannello comandi manuali, disabilita mic)")
        self.cb_mock_voice.setChecked(self.mock_voice)
        self.cb_mock_voice.toggled.connect(self.on_mock_voice_toggled)
        mock_layout.addWidget(self.cb_mock_voice)
        
        self.cb_mock_ai = QCheckBox("Simula AI (Evita connessioni al server LLM locale)")
        self.cb_mock_ai.setChecked(self.mock_ai)
        self.cb_mock_ai.toggled.connect(self.on_mock_ai_toggled)
        mock_layout.addWidget(self.cb_mock_ai)
        
        layout.addWidget(mock_group)
        layout.addStretch()

    def setup_memory_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        self.txt_memory = QTextEdit()
        self.txt_memory.setReadOnly(True)
        self.txt_memory.setText("Nessuna posizione in memoria.")
        layout.addWidget(QLabel("Posizioni salvate (SAVE):"))
        layout.addWidget(self.txt_memory)
        
        limits_group = QGroupBox("Imposta Limiti di Gioco")
        limits_layout = QHBoxLayout(limits_group)
        self.combo_lim_1 = QComboBox()
        self.combo_lim_2 = QComboBox()
        self.combo_lim_1.addItems([chr(i) for i in range(65, 91)]) # A-Z
        self.combo_lim_2.addItems([chr(i) for i in range(65, 91)])
        
        self.btn_set_limits = QPushButton("Applica Limiti Sicurezza")
        self.btn_set_limits.clicked.connect(self.on_btn_set_limits_clicked)
        
        self.btn_clear_limits = QPushButton("Rimuovi Limiti")
        self.btn_clear_limits.setStyleSheet("background-color: #ffcccc; color: darkred;")
        self.btn_clear_limits.clicked.connect(lambda: self.richiestaRimozioneLimiti.emit())
        
        limits_layout.addWidget(QLabel("Posizione 1:"))
        limits_layout.addWidget(self.combo_lim_1)
        limits_layout.addWidget(QLabel("Posizione 2:"))
        limits_layout.addWidget(self.combo_lim_2)
        limits_layout.addWidget(self.btn_set_limits)
        limits_layout.addWidget(self.btn_clear_limits)
        
        layout.addWidget(limits_group)

    def on_btn_set_limits_clicked(self):
        pos1 = self.combo_lim_1.currentText()
        pos2 = self.combo_lim_2.currentText()
        if hasattr(self, 'worker_robot'):
            self.richiestaLimiti.emit(pos1, pos2)
    def setup_manual_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        self.manual_text = QTextEdit()
        self.manual_text.setReadOnly(True)
        self.manual_text.setHtml('''
        <h2 style="color: #2c3e50;">Guida Operativa - DENSO COBOTTA</h2>
        <p>Benvenuto nell'interfaccia di controllo del robot DENSO COBOTTA. Questa guida rapida ti aiuterà a usare il sistema in modo semplice e sicuro.</p>

        <h3 style="color: #2980b9;">1. Preparazione e Connessione</h3>
        <p>Prima di poter controllare il robot, è necessario configurare la connessione fisica di rete e il server di intelligenza artificiale locale:</p>
        
        <p><b>A. Collegamento Rete Ethernet (PC &lt;-&gt; COBOTTA):</b></p>
        <ul>
          <li><b>IP del Robot:</b> L'indirizzo predefinito del controller DENSO COBOTTA è <code>192.168.0.1</code>.</li>
          <li><b>Configurazione Scheda di Rete del PC:</b> Collega il cavo Ethernet al robot e imposta un IP statico sulla scheda di rete del computer:
            <ul>
              <li>Indirizzo IP: <code>192.168.0.100</code></li>
              <li>Maschera di sottorete (Subnet Mask): <code>255.255.255.0</code></li>
              <li>Gateway / DNS: lasciare vuoti.</li>
            </ul>
          </li>
        </ul>

        <p><b>B. Server AI Locale (LM Studio):</b></p>
        <ul>
          <li><b>Download e Installazione:</b> Scarica LM Studio dal sito ufficiale <a href="https://lmstudio.ai/">lmstudio.ai</a>.</li>
          <li><b>Modello da Utilizzare:</b> Cerca e scarica un modello della famiglia <b>Nemotron</b> (consigliato: <code>nemotron-3-nano-4b</code>).</li>
          <li><b>Avvio del Server Locale:</b> Apri la scheda <i>Developer / Local Server</i> (icona a forma di terminale/doppie frecce), seleziona in alto il modello Nemotron per caricarlo in memoria e clicca su <b>Start Server</b>. La porta predefinita è <code>1234</code>.</li>
        </ul>

        <p><b>C. Connessione dall'Applicazione:</b></p>
        <ul>
          <li>Vai nella scheda <b>Configurazione</b> di questa applicazione:
            <ul>
              <li>Imposta <i>Indirizzo IP Controller</i> su <code>192.168.0.1</code>.</li>
              <li>Imposta <i>IP Server AI</i> su <code>127.0.0.1</code> (se LM Studio gira sullo stesso computer) oppure l'IP locale del computer su cui è in esecuzione.</li>
              <li>Verifica che <i>Modello LLM</i> sia impostato su <code>nemotron-3-nano-4b</code> (o il nome del modello caricato).</li>
              <li>Clicca su <b>Salva Configurazione Rete</b>.</li>
            </ul>
          </li>
          <li>Torna nella scheda <b>Controllo Principale</b> e premi il pulsante <b>Connetti</b>. Quando lo stato mostrerà <code>CONNESSO</code>, il robot sarà pronto all'uso.</li>
        </ul>

        <h3 style="color: #2980b9;">2. Come Inviare i Comandi Vocali</h3>
        <p>Nella scheda <b>Controllo Principale</b>, premi il pulsante <b>Ascolta Comando</b>. <br/>
        La spia diventerà <b>rossa</b> per indicare che il microfono è in ascolto. Parla normalmente: la registrazione si interromperà in automatico appena avrai finito la frase. Il sistema sfrutta l'Intelligenza Artificiale (AI) per capire le tue richieste espresse in linguaggio naturale.</p>

        <h3 style="color: #2980b9;">3. Cosa Puoi Chiedere al Robot</h3>
        <ul>
          <li><b>Spostamenti Base:</b> Puoi dire <i>"Vai in avanti"</i>, <i>"Spostati indietro"</i>, <i>"Sali su"</i>, <i>"Vai in basso"</i>.</li>
          <li><b>Rotazioni:</b> Prova con <i>"Ruota a destra"</i> o <i>"Girati a sinistra"</i>.</li>
          <li><b>Distanze su Misura:</b> Il passo base è di 5 centimetri, ma puoi modificarlo in modo discorsivo. Ad esempio: <i>"Vai in avanti di poco"</i>, <i>"Spostati in alto di mezza unità"</i>, o <i>"Ruota a destra di molto"</i>.</li>
          <li><b>Uso della Pinza:</b> Ordina <i>"Chiudi la pinza"</i> (il robot applicherà automaticamente una presa sicura) oppure <i>"Apri la pinza" / "Lascia andare"</i>.</li>
          <li><b>Memorizzazione Punti:</b> Salva posizioni strategiche per raggiungerle in futuro. Dì <i>"Salva la posizione attuale come A"</i> e, in un secondo momento, <i>"Torna alla posizione A"</i>.</li>
        </ul>
        <p><b>Attenzione:</b> Il robot è configurato per eseguire <b>una sola azione alla volta</b> per motivi di sicurezza. Non usare comandi composti come <i>"Vai in alto e chiudi la pinza"</i>.</p>

        <h3 style="color: #2980b9;">4. Limiti di Sicurezza (Gabbia Virtuale)</h3>
        <p>Per prevenire urti accidentali con gli ostacoli sul banco, puoi delimitare lo spazio operativo del braccio. Sposta il robot in due posizioni estreme e salvale. Dalla scheda <b>Memoria Posizioni</b>, impostale come "Posizione 1" e "Posizione 2" per creare un perimetro di sicurezza invalicabile.</p>

        <h3 style="color: #2980b9;">5. Trucchi per gli Operatori</h3>
        <ul>
          <li><b>Azioni Rapide (Automazione):</b> Se devi impartire molti comandi consecutivi, attiva la casella <b>Invio Automatico</b> nella scheda <i>Configurazione</i> per evitare di dover cliccare su "Conferma" ad ogni istruzione.</li>
          <li><b>Modalità Silenziosa (Simulazione Voce):</b> Se c'è troppo rumore nell'ambiente di lavoro, attiva la <b>Simulazione Voce</b> in <i>Configurazione</i>. Comparirà una comoda barra per digitare manualmente i comandi al posto di dettarli a voce, e potrai usare anche dei pulsanti direzionali (D-Pad).</li>
        </ul>

        <h3 style="color: #2980b9;">6. Serve Aiuto?</h3>
        <p>Consulta la scheda <b>Aiuto (Chat AI)</b>. Puoi digitare un problema o un dubbio e il sistema, consultando questo stesso manuale, ti darà istruzioni mirate per risolverlo!</p>

        <h3 style="color: #2980b9;">7. Risoluzione dei Problemi (Codici di Errore)</h3>
        <p>Se il robot restituisce un codice di errore, consulta questa lista per capire cosa fare:</p>
        <ul>
          <li><b>Errore -2095049471 (Out of Bounds):</b> Il robot sta cercando di raggiungere un punto fisicamente impossibile. <i>Soluzione:</i> Richiedi uno spostamento più piccolo o allontanati dal bordo dell'area di lavoro.</li>
          <li><b>Errore -2125459419 (Controller Bloccato):</b> Un errore precedente non è stato resettato. <i>Soluzione:</i> Intervieni fisicamente sul controller DENSO o sul simulatore per cancellare l'errore (ClearError) prima di riconnettere.</li>
          <li><b>Errore -2147024891 (Accesso Negato):</b> Il sistema non ha i permessi per muovere il braccio. <i>Soluzione:</i> Imposta la chiave sul "Teach Pendant" in modalità <b>AUTO</b> e assicurati che l'esecuzione sia concessa a <b>Ethernet</b>.</li>
          <li><b>Errore -2147481344 (Timeout):</b> Collegamento perso. <i>Soluzione:</i> Controlla il cavo di rete, verifica l'IP nella scheda Configurazione, poi "Disconnetti" e "Connetti" di nuovo.</li>
          <li><b>Errore di Limiti Impostati:</b> "La posizione desiderata è fuori dai limiti impostati". <i>Soluzione:</i> Il movimento richiesto ti farebbe uscire dalla "Gabbia" (vedi punto 4). Fai un movimento contrario.</li>
        </ul>

        <h3 style="color: #2980b9;">8. Dettagli Tecnici di Sicurezza</h3>
        <ul>
          <li><b>Unità Base:</b> Un'unità standard equivale esattamente a <b>50 millimetri</b>.</li>
          <li><b>Prevenzione Urti (Asse Z):</b> Quando la "Gabbia" (Limiti di sicurezza) è attiva, per precauzione il robot non scenderà mai sotto i <b>20 millimetri</b> di altezza rispetto al banco di lavoro, e non salirà oltre i 500 millimetri.</li>
        </ul>
        ''')
        layout.addWidget(self.manual_text)

    def setup_chat_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        self.txt_chat_history = QTextEdit()
        self.txt_chat_history.setReadOnly(True)
        layout.addWidget(self.txt_chat_history)
        
        chat_input_layout = QHBoxLayout()
        self.le_chat_input = QLineEdit()
        self.le_chat_input.setPlaceholderText("Chiedi all'AI (es: Come salvo una posizione?)...")
        self.le_chat_input.returnPressed.connect(self.on_btn_chat_send_clicked)
        self.btn_chat_send = QPushButton("Invia")
        self.btn_chat_send.clicked.connect(self.on_btn_chat_send_clicked)
        
        chat_input_layout.addWidget(self.le_chat_input)
        chat_input_layout.addWidget(self.btn_chat_send)
        layout.addLayout(chat_input_layout)
    def on_btn_chat_send_clicked(self):
        testo = self.le_chat_input.text().strip()
        if not testo:
            return
            
        self.txt_chat_history.append(f"<b>Tu:</b> {testo}")
        self.le_chat_input.clear()
        
        self.btn_chat_send.setEnabled(False)
        self.txt_chat_history.append("<i>AI sta scrivendo...</i>")
        
        url = os.getenv("LLM_URL", "http://localhost:1234/v1/chat/completions")
        manual_content = self.manual_text.toPlainText()

        prompt = f"""
            Sei un assistente di supporto tecnico rapido ed essenziale. Il tuo compito è risolvere il problema dell'utente basandoti ESCLUSIVAMENTE sulle informazioni contenute nel manuale fornito.
            REGOLE TASSATIVE:
            1. Sii estremamente conciso. Vai direttamente alla soluzione.
            2. Non usare saluti, convenevoli, o frasi introduttive (es. "Ecco la risposta", "Secondo il manuale").
            3. Usa il minor numero di parole possibile per soddisfare la richiesta. Preferisci elenchi puntati brevi se i passaggi sono multipli.
            4. Se l'informazione necessaria non è esplicitamente presente nel testo fornito, rispondi SOLO con: "Informazione non presente nel manuale."
            
            MANUALE D'USO:
            {manual_content}
            """
        
        # Nel worker, sys_prompt viene concatenato se usato manual_context, ma qui il prompt del worker
        # lo possiamo semplicemente usare come system prompt passando il testo dell'utente.
        # Ho riscritto il ChatWorker in modo che accetti (url, prompt, manual_context).
        # prompt = domanda dell'utente. manual_context = il system prompt!
        self.chat_worker = ChatWorker(url, prompt=testo, manual_context=prompt)
        self.chat_worker.rispostaPronta.connect(self.on_chat_response)
        self.chat_worker.errore.connect(self.on_chat_error)
        self.chat_worker.start()

    @Slot(str)
    def on_chat_response(self, text):
        self.txt_chat_history.append(f"<span style='color:green;'><b>AI:</b> {text}</span><hr>")
        self.btn_chat_send.setEnabled(True)

    @Slot(str)
    def on_chat_error(self, err):
        self.txt_chat_history.append(f"<span style='color:red;'><b>Errore API:</b> {err}</span><hr>")
        self.btn_chat_send.setEnabled(True)

    def on_save_config_clicked(self):
        env_file = ".env"
        if not os.path.exists(env_file):
            open(env_file, 'a').close()
            
        new_ip = self.le_controller_ip.text().strip()
        new_llm_ip = self.le_llm_ip.text().strip()
        new_url = f"http://{new_llm_ip}:1234/v1/chat/completions"
        new_model = self.le_llm_model.text().strip()
        auto_send_val = "True" if self.cb_auto_send.isChecked() else "False"
        
        dotenv.set_key(env_file, "CONTROLLER_ADDRESS", new_ip, quote_mode="never")
        dotenv.set_key(env_file, "LLM_URL", new_url, quote_mode="never")
        dotenv.set_key(env_file, "LLM_MODEL", new_model, quote_mode="never")
        dotenv.set_key(env_file, "AUTO_SEND", auto_send_val, quote_mode="never")
        
        os.environ["CONTROLLER_ADDRESS"] = new_ip
        os.environ["LLM_URL"] = new_url
        os.environ["LLM_MODEL"] = new_model
        os.environ["AUTO_SEND"] = auto_send_val
        
        if hasattr(self, 'worker_robot'):
            self.worker_robot.ip = new_ip
            
        if hasattr(self, 'worker_ai'):
            self.worker_ai.processor = None
            
        QMessageBox.information(self, "Successo", "Configurazione salvata!\nSe il robot era connesso, disconnettiti e riconnettiti.")

    def on_mock_robot_toggled(self, checked):
        self.mock_robot = checked
        if hasattr(self, 'worker_robot'):
            self.worker_robot.mock = checked
            self.log(f"Mock Robot {'attivato' if checked else 'disattivato'}.")
            
    def on_mock_voice_toggled(self, checked):
        self.mock_voice = checked
        if hasattr(self, 'worker_voice'):
            self.worker_voice.mock = checked
            self.log(f"Mock Vocale {'attivato' if checked else 'disattivato'}.")
        
        self.mock_panel.setVisible(checked)
        self.update_ui_for_state(self.state_manager.get_state())
        
    def on_mock_ai_toggled(self, checked):
        self.mock_ai = checked
        if hasattr(self, 'worker_ai'):
            self.worker_ai.mock = checked
            self.log(f"Mock AI {'attivato' if checked else 'disattivato'}.")

    def on_manual_command(self, text):
        if not text.strip():
            return
        self.log(f"Comando simulato: '{text}'")
        self.on_voice_transcribed(text)

    def send_direct_command(self, action, direction="FORWARD", multiplier=1):
        self.log(f"Comando manuale diretto: {action} {direction}")
        self.on_ai_command_ready({"comando": action, "direzione": direction, "moltiplicatore": multiplier})

    def setup_threads_and_workers(self):
        # 1. Thread e Worker per il Robot
        self.thread_robot = QThread()
        ip = os.getenv("CONTROLLER_ADDRESS", "192.168.0.1")
        self.worker_robot = RobotWorker(DensoController, ip, 5007, 3, 50, mock=self.mock_robot)
        self.worker_robot.moveToThread(self.thread_robot)
        
        self.richiestaConnessione.connect(self.worker_robot.connetti)
        self.richiestaMovimento.connect(self.worker_robot.eseguiComando)
        self.richiestaLimiti.connect(self.worker_robot.impostaLimiti)
        self.richiestaRimozioneLimiti.connect(self.worker_robot.rimuoviLimiti)
        self.worker_robot.connessioneRiuscita.connect(self.on_robot_connected)
        self.worker_robot.erroreRobot.connect(self.on_error)
        self.worker_robot.movimentoCompletato.connect(self.on_robot_motion_completed)
        self.worker_robot.disconnesso.connect(self.on_robot_disconnected)
        self.worker_robot.memoriaAggiornata.connect(self.on_memory_updated)
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
        self.txt_log.append(f"<span style='color:inherit;'>{message}</span>")

    def log_movement(self, message: str):
        self.txt_movement_log.append(f"<span style='color:inherit;'>{message}</span>")

    @Slot(dict)
    def on_memory_updated(self, pos_dict):
        if not pos_dict:
            self.txt_memory.setText("Nessuna posizione in memoria.")
            return
        testo = ""
        for key, coords in pos_dict.items():
            coords_str = ", ".join(f"{c:.2f}" for c in coords)
            testo += f"Posizione {key}: [{coords_str}]\n"
        self.txt_memory.setText(testo.strip())

    def update_ui_for_state(self, state: AppState):
        self.state_manager.transition_to(state)
        
        is_disconnected = (state == AppState.DISCONNECTED)
        is_idle = (state == AppState.IDLE)
        is_awaiting_conf = (state == AppState.AWAITING_CONFIRMATION)
        
        self.btn_connect.setEnabled(is_disconnected)
        self.btn_disconnect.setEnabled(not is_disconnected)
        self.btn_mic.setEnabled(is_idle and not self.mock_voice)
        
        if state == AppState.LISTENING:
            self.lbl_mic_led.setStyleSheet("background-color: red; border-radius: 10px; border: 1px solid black;")
        else:
            self.lbl_mic_led.setStyleSheet("background-color: gray; border-radius: 10px; border: 1px solid black;")
        
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

    def on_btn_disconnect_clicked(self):
        self.log("Disconnessione in corso...")
        self.btn_disconnect.setEnabled(False)
        if hasattr(self, 'worker_robot'):
            self.worker_robot.disconnetti()

    def on_btn_mic_clicked(self):
        self.update_ui_for_state(AppState.LISTENING)
        self.lbl_transcript.setText("Trascrizione: in ascolto...")
        self.richiestaAscolto.emit()

    def on_btn_confirm_clicked(self):
        if self.pending_command:
            self.update_ui_for_state(AppState.MOVING)
            self.log_movement(f"Esecuzione in corso: {self.pending_command}")
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

    @Slot()
    def on_robot_disconnected(self):
        self.log("Disconnesso dal controller.")
        self.update_ui_for_state(AppState.DISCONNECTED)

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
        
        if risultato.get("comando") == "ERROR":
            self.log("L'AI ha interpretato il comando come ERRORE. Ignorato.")
            self.update_ui_for_state(AppState.IDLE)
        elif risultato.get("comando") == "EXIT":
            self.log("L'AI ha richiesto la disconnessione (EXIT).")
            self.on_btn_disconnect_clicked()
        else:
            self.pending_command = risultato
            self.update_ui_for_state(AppState.AWAITING_CONFIRMATION)
            if hasattr(self, 'cb_auto_send') and self.cb_auto_send.isChecked():
                self.on_btn_confirm_clicked()

    @Slot(bool, str)
    def on_robot_motion_completed(self, successo: bool, messaggio: str):
        self.log_movement(f"Movimento completato. Successo={successo}, Messaggio={messaggio}")
        self.update_ui_for_state(AppState.IDLE)

    @Slot(str)
    def on_error(self, messaggio: str):
        self.txt_log.append(f"<span style='color:red;'><b>ERRORE:</b> {messaggio}</span>")
        self.update_ui_for_state(AppState.IDLE)
