# DENSO COBOTTA - Voice & AI Robot Controller

Sistema di controllo e teleoperazione per braccio robotico collaborativo DENSO COBOTTA, integrato con pipeline di riconoscimento vocale locale (faster-whisper), interpretazione semantica via Large Language Model (LM Studio / OpenAI-compatible API) con output strutturato (JSON Schema), ed interfaccia grafica multithread sviluppata in PySide6 (Qt).

---

## Architettura del Sistema

L'applicazione adotta un'architettura modulare a thread separati per disaccoppiare l'interfaccia utente dai carichi computazionali dell'inferenza vocale, delle chiamate di rete verso l'LLM e delle comunicazioni sincrone con il controller industriale.

```text
[ Thread Principale / GUI ]
       MainWindow (PySide6)
       |         ^
       | segnali | segnali
       v         |
+-------------------------------------------------------+
| Thread Secondari (QObject + moveToThread)             |
|                                                       |
|  * VoiceWorker  --> faster-whisper (VAD + int8)       |
|  * AIWorker     --> REST API / LM Studio (Structured) |
|  * RobotWorker  --> DensoController (b-CAP / ORiN)    |
+-------------------------------------------------------+
```

### Thread-Safety del Protocollo b-CAP
Il client socket b-CAP (`pybcapclient`) non e' thread-safe: accessi concorrenti al socket (ad esempio la lettura della posizione corrente mentre e' in corso una primitiva di movimento) corrompono lo stream o generano eccezioni irreversibili `ORiNException`. 
Di conseguenza, tutte le operazioni sul robot (connessione, polling coordinate, movimentazione, controllo pinza e rilascio handle) sono confinate nel singolo thread dedicato `RobotWorker` e serializzate attraverso la coda degli eventi di Qt.

---

## Pipeline Operativa

Il ciclo operativo dell'applicazione si articola nelle seguenti fasi:

1. **Inizializzazione e Connessione**
   - Apertura socket b-CAP verso l'indirizzo del controller reale o del simulatore (WINCAPS III).
   - Allocazione handle del controller (`h_ctrl`) e del robot (`h_rob`).
   - Acquisizione controllo (`TakeArm`), accensione motori e configurazione della velocita' limite (default: 40%).
   - Inizializzazione orecchio virtuale e calibrazione del rumore ambientale.

2. **Acquisizione e Riconoscimento Vocale**
   - Rilevamento attivita' vocale mediante Silero VAD (Voice Activity Detection).
   - Elaborazione audio direttamente in memoria RAM via `io.BytesIO` per minimizzare la latenza di I/O.
   - Trascrizione in lingua italiana tramite modello `faster-whisper` (inferenza quantizzata int8 su CPU).

3. **Interpretazione Semantica e Validazione (LLM)**
   - Invio del testo trascritto a un'istanza locale di LM Studio.
   - Forzatura di output strutturato conforme a `src/schemas/responseFormat.json`.
   - Validazione delle chiavi di risposta (`comando`, `direzione`, `moltiplicatore`).
   - Verifica di conformita' (rigetto di comandi multipli, incompleti o ambigui).

4. **Verifica Cinematica e Movimentazione**
   - Calcolo delle coordinate cartesiane target basato su unita' discretizzate (default: 50 mm).
   - Controllo di sicurezza: verifica che il punto target rispetti il bounding box operativo (`isInRange`).
   - Invio della traiettoria al robot tramite primitiva b-CAP `robot_move`.

5. **Terminazione e Rilascio Risorse**
   - Spegnimento motori, rilascio del braccio (`GiveArm`), deallocazione esplicita degli handle ORiN e chiusura del servizio socket.

---

## Gestione degli Handle (Protocollo b-CAP / ORiN)

Nel contesto di b-CAP/ORiN, un handle e' un identificatore univoco allocato nella memoria del controller DENSO per indirizzare entita' interne:
- `h_ctrl`: handle del controller di sistema.
- `h_rob`: handle dell'oggetto cinematica/braccio.
- `CurPosHandl`: puntatore alla variabile di sistema `@CURRENT_POSITION`.

Ogni handle instanzia risorse hardware sul controller. L'implementazione garantisce il rilascio deterministico (`variable_release`, `robot_release`, `controller_disconnect`, `service_stop`) tramite costrutti `finally` e distruttori controllati, prevenendo leak di memoria sul firmware del robot.

---

## Specifica Comandi Vocali

La cinematica si basa su incrementi discreti definiti da un'unita' base (50 mm). Il modello AI riconosce sia moltiplicatori interi sia frazionari (1/4, 1/2, 3/4).

### Azioni Supportate
- `TRANSLATE`: Spostamento cartesiano lungo gli assi [`FORWARD`, `BACKWARD`, `UP`, `DOWN`].
- `ROTATE`: Rotazione angolare [`RIGHT`, `LEFT`].
- `GRAB`: Chiusura pinza con controllo di forza a 10 N (`HandMoveH`) e verifica di presa (`HandHoldState`).
- `RELEASE`: Apertura della pinza a corsa prefissata (`HandMoveA`).
- `SAVE [lettera]`: Memorizzazione coordinate correnti associata a un identificatore alfabetico (es. "Salva posizione come A").
- `ROLLBACK [lettera]`: Ritorno a una posizione precedentemente salvata.
- `EXIT`: Chiusura programmata della sessione.

### Esempi di Input

**Comandi conformi:**
```text
"Vai in avanti di poco"            -> TRANSLATE, FORWARD, 1.0
"Spostati un po' a destra"         -> ROTATE, RIGHT, 3.0
"Spostati avanti di 1/2 unita'"    -> TRANSLATE, FORWARD, 0.5
"Spostati indietro di 1/4 unita'"  -> TRANSLATE, BACKWARD, 0.25
"Chiudi la pinza"                  -> GRAB
"Lascia andare"                    -> RELEASE
"Salva posizione attuale come A"   -> SAVE, direzione: A
"Torna alla posizione A"           -> ROLLBACK, direzione: A
```

**Comandi non ammessi (restituiscono errore):**
```text
"Vai avanti di 1 unita' e ruota"    (Violazione: comandi multipli non ammessi)
"Vai indietro di molto e afferra"  (Violazione: azione composita)
"Ruota in alto"                    (Violazione: direzione non valida per ROTATE)
```

---

## Limiti Operativi e Spazio di Lavoro

Per prevenire collisioni e uscite dallo spazio di lavoro ammesso, il controller applica una validazione preliminare sulle coordinate calcolate rispetto ai limiti del banco (configurabili tramite `setSafetyBounds`):

- **X Cartesiano:** `[132 mm, 338 mm]`
- **Z Cartesiano:** `[-10 mm, 365 mm]`
- Tolleranza di soglia: 2.0 mm

---

## Struttura del Repository

```text
.
├── src/
│   ├── AI/
│   │   ├── ai_transformer.py     # Client HTTP verso l'endpoint LM Studio
│   │   └── ai_utilities.py       # Helper per schema injection e payload format
│   ├── gui/
│   │   ├── main_window.py        # Finestra principale PySide6
│   │   ├── state.py              # Macchina a stati dell'interfaccia
│   │   └── workers/              # QObject worker (Robot, Voice, AI)
│   ├── pybcapclient/             # Driver client b-CAP (ORiN2 protocol)
│   ├── schemas/
│   │   └── responseFormat.json   # JSON Schema rigido per vincolare l'LLM
│   ├── brainProcessor.py         # Orchestratore semantico (prompt + schema)
│   ├── densoController.py        # Controller cinematica e interfaccia b-CAP
│   ├── orinErrorDecoder.py       # Decodifica esadecimale codici di errore ORiN
│   └── voiceRecognition.py       # Pipeline audio (PyAudio, VAD, faster-whisper)
├── run_gui.py                    # Entry point applicativo con GUI
├── main.py                       # Entry point CLI (modalita' headless / test)
├── build.sh                      # Script di compilazione per Windows (PyInstaller)
├── .env.example                  # Template delle variabili di configurazione
├── requirements.txt              # Dipendenze Python
└── LICENSE                       # Licenza MIT del progetto
```

---

## Configurazione dell'Ambiente

1. Clonare il repository:
   ```bash
   git clone <URL_REPOSITORY>
   cd DENSO_controller
   ```

2. Creare il file di configurazione locale partendo dal template:
   ```bash
   cp .env.example .env
   ```

3. Modificare `.env` con i parametri operativi della propria postazione:
   ```ini
   # Indirizzo IP del controller reale o del simulatore WINCAPS III
   CONTROLLER_ADDRESS=192.168.0.1

   # Endpoint del server LLM locale (LM Studio)
   LLM_URL=http://localhost:1234/v1/chat/completions
   LLM_MODEL=meta-llama-3-8b-instruct
   ```

---

## Build e Distribuzione Eseguibile (Windows)

Per generare un pacchetto autonomo distribuibile su postazioni Windows senza necessita' di installare Python o librerie di sistema:

1. Eseguire lo script `build.sh` (tramite Git Bash o ambiente compatibile):
   ```bash
   ./build.sh
   ```

Lo script esegue automaticamente:
- Installazione di tutte le dipendenze da `requirements.txt` e di `pyinstaller`.
- Inclusione degli asset statici (`src/schemas/*.json`).
- Tracciamento e inclusione dei binari C++ e runtime di `faster_whisper` e `ctranslate2`.
- Generazione di un unico file eseguibile standalone (`--onefile --windowed`) in `dist/DENSO_Controller.exe`.

### Distribuzione su PC Target
Copiare su qualsiasi PC Windows:
1. `DENSO_Controller.exe` (da cartella `dist/`)
2. Il file `.env` configurato per la rete di laboratorio.

Al primo avvio, il modulo vocale scarichera' automaticamente i pesi del modello Whisper nella cache locale utente (`%USERPROFILE%\.cache\huggingface\hub\`); tutti i successivi avvii opereranno al 100% offline.

---

## Licenza

Questo progetto e' rilasciato sotto licenza MIT. Per maggiori dettagli, consultare il file [LICENSE](LICENSE).

Il driver b-CAP (`src/pybcapclient/`) e' copyright (c) 2017 DENSO WAVE INCORPORATED e rilasciato anch'esso sotto licenza MIT.