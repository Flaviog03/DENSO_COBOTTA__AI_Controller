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
| Thread Secondari (QObject + moveToThread / QThread)   |
|                                                       |
|  * VoiceWorker  --> faster-whisper (VAD + int8)       |
|  * AIWorker     --> REST API / LM Studio (Structured) |
|  * RobotWorker  --> DensoController (b-CAP / ORiN)    |
|  * ChatWorker   --> Assistente AI / Supporto Manuale  |
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

## Limiti Operativi e Spazio di Lavoro (Safety Bounds)

Per prevenire collisioni e uscite dallo spazio di lavoro ammesso, il controller applica una validazione preliminare (`isInRange`) su tutte le coordinate calcolate rispetto ai limiti del banco:

- **Unità Base di Movimentazione:** 50 mm per singolo passo (1 unità = 50 mm).
- **Gabbia Virtuale (Safety Bounds):**
  - Definibile interattivamente o partendo da due posizioni salvate nella GUI (`setSafetyBoundsFromPositions`).
  - **Quota Z di Sicurezza:** Quando la gabbia è attiva, la quota Z minima è forzata a `20.0 mm` dal piano per impedire urti sul banco di lavoro, con una quota massima di `500.0 mm`.
  - Tolleranza di soglia: 2.0 mm per assorbire approssimazioni di cinematica inversa.

---

## Interfaccia Grafica (GUI)

L'interfaccia utente (PySide6) è organizzata in 5 schede operative pensate per l'operatore:

1. **Controllo Principale:**
   - Gestione connessione al braccio (pulsanti *Connetti* / *Disconnetti* con indicatore di stato).
   - Acquisizione comandi vocali con spia di stato (LED rosso di ascolto attivo).
   - Area di anteprima con trascrizione del testo e comando AI strutturato, con opzione di conferma ed esecuzione manuale (*Conferma ed Esegui* / *Annulla*).
   - Pannello di log operativi e log dettagliati dei movimenti cartesiani.
2. **Configurazione:**
   - Impostazione parametri di rete: *Indirizzo IP Controller*, *IP Server AI* e *Modello LLM*, con salvataggio persistente.
   - Opzione **Invio Automatico Comandi**: scavalca la conferma visiva ed esegue immediatamente il comando vocale validato.
   - Pannello **Simulazione (Mock)**: permette di simulare indipendentemente il Robot, la Voce (con comandi manuali testuali e D-Pad direzionale) e l'AI.
3. **Memoria Posizioni:**
   - Visualizzazione dei punti salvati in memoria (`SAVE`).
   - Selezione di due posizioni per generare e attivare la *Gabbia di Sicurezza* operativa.
4. **Manuale:**
   - Manuale d'uso rapido e discorsivo integrato direttamente nell'interfaccia grafica.
5. **Aiuto (Chat AI):**
   - Assistente di supporto tecnico basato su LLM (`ChatWorker`). Utilizza il testo del manuale integrato per rispondere a domande operative e guidare l'utente nella risoluzione degli errori.

---

## Diagnostica e Risoluzione Errori (ORiN)

Il modulo `orinErrorDecoder.py` intercetta e decodifica i codici di errore HResult generati dal protocollo b-CAP. I codici più comuni e le relative azioni correttive sono:

| Codice Decimale | Esadecimale | Causa Tipica | Soluzione Operativa |
| :--- | :--- | :--- | :--- |
| **`-2095049471`** | `0x83201401` | *Out of Bounds*: posizione richiesta fuori dal raggio o dai limiti dei giunti | Ridurre l'ampiezza dello spostamento o allontanarsi dal limite operativo |
| **`-2125459419`** | `0x81501025` | *Controller Bloccato*: errore pregresso non resettato | Eseguire `ClearError` da Teach Pendant o simulatore prima di `TakeArm` |
| **`-2147024891`** | `0x80070005` | *Accesso Negato (`E_ACCESSDENIED`)*: controller non autorizzato | Impostare il selettore del Teach Pendant su **AUTO** ed Exec. Provider su **Ethernet** |
| **`-2147481344`** | `0x80000000` | *Timeout (`E_TIMEOUT`)*: nessuna risposta via b-CAP | Verificare il cavo Ethernet, l'IP del PC (`192.168.0.100`), disconnettere e riconnettere |
| **`-2147024809`** | `0x80070057` | *Argomento Non Valido (`E_INVALIDARG`)* | Verificare parametri del comando o consistenza degli handle |

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
├── build.sh                      # Script di compilazione per ambienti Bash / Git Bash
├── build.bat                     # Script di compilazione nativo Windows (cmd / PowerShell)
├── .env.example                  # Template delle variabili di configurazione
├── requirements.txt              # Dipendenze Python
└── LICENSE                       # Licenza MIT del progetto
```

---

## Configurazione dell'Ambiente

### 1. Configurazione Rete Ethernet (PC <-> DENSO COBOTTA)
Per consentire la comunicazione b-CAP diretta tra il PC operatore e il robot:
- **Collegamento Fisico:** Connettere la porta Ethernet del controller COBOTTA alla scheda di rete del PC tramite cavo RJ45.
- **IP Controller DENSO:** Di fabbrica è impostato a `192.168.0.1`.
- **Configurazione Scheda di Rete PC (IPv4 Statico):**
  - **Indirizzo IP:** `192.168.0.100`
  - **Subnet Mask:** `255.255.255.0`
  - **Gateway / DNS:** Lasciare non configurati (vuoti).

### 2. Setup Server AI Locale (LM Studio)
1. Scaricare e installare LM Studio dal sito ufficiale: [https://lmstudio.ai/](https://lmstudio.ai/).
2. Nella barra di ricerca modelli, individuare e scaricare un modello della famiglia **Nemotron** (consigliato: `nemotron-3-nano-4b`).
3. Accedere alla scheda **Developer / Local Server** (icona terminale/doppie frecce):
   - Selezionare in alto il modello Nemotron scaricato per caricarlo in memoria.
   - Avviare il server cliccando su **Start Server** sulla porta predefinita `1234` (endpoint base: `http://localhost:1234/v1`).

### 3. Installazione e Avvio Applicazione
1. Clonare il repository:
   ```bash
   git clone <URL_REPOSITORY>
   cd DENSO_controller
   ```

2. Creare il virtual environment e installare le dipendenze:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Su Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Creare il file di configurazione `.env` partendo dal template:
   ```bash
   cp .env.example .env
   ```

4. Configurare i parametri in `.env`:
   ```ini
   # Indirizzo IP del controller reale o del simulatore WINCAPS III
   CONTROLLER_ADDRESS=192.168.0.1

   # Endpoint del server LLM locale (LM Studio)
   LLM_URL=http://localhost:1234/v1/chat/completions
   LLM_MODEL=nemotron-3-nano-4b
   ```

5. Avviare l'interfaccia grafica:
   ```bash
   python run_gui.py
   ```

---

## Build e Distribuzione Eseguibile (Windows)

Per generare un pacchetto autonomo distribuibile su postazioni Windows senza necessita' di installare Python o librerie di sistema:

1. Eseguire lo script di build:
   - **Da Windows (Prompt dei comandi / PowerShell o doppio clic):**
     ```cmd
     .\build.bat
     ```
   - **Da ambiente Unix / Git Bash:**
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