# -*- coding: utf-8 -*-
"""
Test di movimento del robot DENSO via b-CAP.
Funziona sia con la simulazione VRC su Windows sia con un controller
REALE (RC8/RC8A/COBOTTA) connesso via LAN: l'unica cosa che cambia
davvero è l'IP in "host" qui sotto. Il Provider resta "CaoProv.DENSO.VRC"
in entrambi i casi.

Il robot legge la propria posizione attuale, ruota di qualche grado
attorno a un asse (Rx/Ry/Rz) e torna alla posizione di partenza.
Usa interpolazione PTP (joint) invece che lineare (CP): il controller
deve risolvere la cinematica solo per il punto di arrivo, non lungo
tutto il percorso, quindi tollera molto meglio le rotazioni ed evita
l'errore "OUT OF MOTION" che si ottiene spesso con CP + Fig fisso.

!!! SICUREZZA - SOLO SE ROBOT REALE !!!
- Area di lavoro del robot completamente libera da persone/oggetti
- Pulsante di emergenza fisico a portata di mano prima di lanciare lo script
- ExtSpeed tenuta bassa (vedi sotto) per il primo test
- Controller in modalità AUTO/EXT abilitata dal vero teach pendant

Prerequisiti:
- Simulazione: server b-CAP avviato (bCapConfig.exe -> Action -> Service Start)
- Robot reale: controller raggiungibile in rete (es. ping all'IP) e
  b-CAP/controllo esterno abilitato sul controller stesso
- Modalità AUTO attiva, nessun allarme presente
- Executable Token assegnato a "Ethernet" o "Any" (Setting -> Communication
  and Token -> Executable Token), altrimenti TakeArm/Motor falliscono

b-cap Lib: https://github.com/DENSORobot/orin_bcap
"""

import pybcapclient.bcapclient as bcapclient

# --- Parametri di connessione ---
# Simulazione VRC:  host = "127.0.0.1"
# Robot reale:      host = "<IP del controller>", es. "192.168.0.1"
host = "192.168.1.15"   # <-- sostituisci con l'IP reale del tuo controller
port = 5007              # porta di default del server b-CAP (NON quella OPC-UA)
timeout = 2000

# --- Parametri di rotazione ---
# Indice della posa da modificare: 3=Rx, 4=Ry, 5=Rz (0=X, 1=Y, 2=Z, 6=Fig)
ASSE_ROTAZIONE = 5       # Rz di default
GRADI_ROTAZIONE = -35.0  # negativo = rotazione nel verso opposto al test precedente

m_bcapclient = bcapclient.BCAPClient(host, port, timeout)
print("Connessione aperta")

m_bcapclient.service_start("")
print("Servizio b-CAP avviato")

Name = ""
Provider = "CaoProv.DENSO.VRC"   # usa "CaoProv.DENSO.VRC9" per un RC9
Machine = "localhost"
Option = ""

hCtrl = m_bcapclient.controller_connect(Name, Provider, Machine, Option)
print("Connesso al controller, handle:", hCtrl)

HRobot = None
CurPosHandl = None

try:
    # --- Handle dell'oggetto Robot ---
    HRobot = m_bcapclient.controller_getrobot(hCtrl, "Arm", "")
    print("Handle Robot ottenuto:", HRobot)

    # --- Presa di controllo del braccio ---
    m_bcapclient.robot_execute(HRobot, "TakeArm", [0, 0])
    print("TakeArm eseguito")

    # --- Accensione motori ---
    m_bcapclient.robot_execute(HRobot, "Motor", [1, 0])
    print("Motori ON")

    # --- Velocità/accelerazione/decelerazione esterne (%) - bassa per sicurezza ---
    # Su robot REALE, per il primissimo test valuta di abbassare ulteriormente
    # (es. 5-10%) finché non sei sicuro che la traiettoria sia quella attesa.
    m_bcapclient.robot_execute(HRobot, "ExtSpeed", [40, 100, 100])
    print("Velocità impostata al 40%")

    # --- Lettura posizione attuale [x, y, z, rx, ry, rz, fig] ---
    CurPosHandl = m_bcapclient.robot_getvariable(HRobot, "@CURRENT_POSITION", "")
    pos_iniziale = m_bcapclient.variable_getvalue(CurPosHandl)
    print("Posizione attuale:", pos_iniziale)

    # --- Calcolo posizione target: rotazione sull'asse scelto ---
    pos_target = list(pos_iniziale)
    pos_target[ASSE_ROTAZIONE] += GRADI_ROTAZIONE

    # --- Rotazione (Comp=1 -> PTP, joint interpolation) ---
    Pose = [pos_target, "P", "@E"]
    m_bcapclient.robot_move(HRobot, 1, Pose, "")
    print(f"Ruotato di {GRADI_ROTAZIONE} gradi sull'asse indice {ASSE_ROTAZIONE}")

    # --- Ritorno alla posizione di partenza (sempre PTP) ---
    Pose = [list(pos_iniziale), "P", "@E"]
    m_bcapclient.robot_move(HRobot, 1, Pose, "")
    print("Tornato alla posizione iniziale")

    # --- Spegnimento motori ---
    m_bcapclient.robot_execute(HRobot, "Motor", [0, 0])
    print("Motori OFF")

finally:
    # --- Rilascio risorse e disconnessione, sempre eseguito ---
    if CurPosHandl:
        m_bcapclient.variable_release(CurPosHandl)
    if HRobot:
        m_bcapclient.robot_execute(HRobot, "GiveArm", None)
        m_bcapclient.robot_release(HRobot)
        print("GiveArm eseguito e Robot rilasciato")
    if hCtrl:
        m_bcapclient.controller_disconnect(hCtrl)
        print("Controller disconnesso")
    m_bcapclient.service_stop()
    print("Servizio b-CAP fermato")