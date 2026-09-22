# 1. Inizializzazione
        # 1.1 Connessione al robot
        # 1.2 Forza velocità del robot al 40%
        # 1.3 Inizializza "orecchio virtuale"

# 2. Corpo del programma (Ciclo)
    # 2.1 Acquisizione input
        # 2.1.1 Acquisizione posizione attuale -> lista [x,y,z,Rx,Ry,Rz]
        # 2.1.2 Impostazione del filtro silero-vad per voce chiara
        # 2.1.3 Acquisizione comando vocale (richiede una mappatura dei comandi) -> frasi in linguaggio naturale

    # 2.2 Comunicazione con l'AI
        # 2.2.1 Classificazione dei possibili comandi (traslazione/rotazione/afferra/rilascia)
        # 2.2.2 Breve check (se contiene afferra verifica che la pinza non sia già chiusa)
        # 2.2.3 Invio dei comandi in linguaggio naturale codificati all'interno di un file con formato JSON
        # 2.2.4 -!- Comunicazione con il modello (effettuerà la classificazione dell'input) 
            -> file JSON
        # 2.2.5 Validazione formato file JSON
        # 2.2.6 Calcolo nuova posizione
        # 2.2.7 Verifica fattibilità movimento tramite coordinate attuali (es. fuoriRange, fuoriBoxSicurezza)
        # Esecuzione

    # 2.3 Movimentazione del braccio 
        # -!- I movimenti avverranno secondo delle unità base, es (50 mm alla volta)

# 3. Operazioni finali e Rilascio connessione

### Funzionamento degli handle
    Nel contesto del protocollo b-CAP/ORiN, un handle è un identificativo numerico (una sorta di puntatore software) che rappresenta e permette di accedere a un oggetto specifico allocato all'interno della memoria del controller DENSO.
    L'interazione con il robot avviene attraverso una gerarchia di questi identificatori: è possibile acquisire handle per il controller principale (h_ctrl), per il braccio meccanico (h_rob) e per le singole variabili interne (h_var).
    Una volta generato un handle (ad esempio richiamando le funzioni controller_getrobot o controller_getvariable), questo numero deve essere passato come parametro alle funzioni successive per specificare su quale entità si desidera eseguire un'azione o leggere un dato.

Poiché la creazione di questi oggetti assegna delle risorse nella memoria hardware del controller, ogni handle deve essere obbligatoriamente liberato al termine del suo utilizzo tramite i metodi di rilascio dedicati

### MANUALE UTENTE ###
- Movimentazione del braccio robotico tramite comando vocale.
    La movimentazione avviene secondo delle "unità di spostamento".
    L'unità base vale 5 cm, l'IA è addestrata anche a riconoscere porzioni decimali di unità, ad esempio 1/2, 1/4 e 3/4.
    Se al robot vengono richieste più azioni contemporaneamente allora non prenderà in considerazione nessuna di esse

    Esempi di input corretti:
        #. Vai in avanti di poco
        #. spostati un po' a destra
        #. spostati molto a sinistra
        #. spostati a sinistra di 2 unità
        #. spostati indietro di 1/2 di unità
        #. spostati avanti di 1/4 di unità
        #. spostati a sinistra di 3/4 di unità
        #. chiudi la pinza
        #. lascia andare

    Esempi input scorretti:
        # vai in avanti di 1 unità e ruota
        # vai indietro di molto e afferra