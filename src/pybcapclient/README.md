# 1. Modulo `variant.py`

Il modulo definisce la classe **`VarType`**, che raggruppa le costanti numeriche usate dal protocollo b-CAP/ORiN per rappresentare i tipi di dato variant (di derivazione COM/OLE Automation) scambiati tra client e controller.

### Principali Tipi di Dato Supportati (`VarType`)

* **Tipi Base / Primitivi**:
* `VT_EMPTY` (0), `VT_NULL` (1)


* Interi con e senza segno: `VT_I1` (16), `VT_I2` (2), `VT_I4` (3), `VT_I8` (20), `VT_UI1` (17), `VT_UI2` (18), `VT_UI4` (19), `VT_UI8` (21)


* Numeri a virgola mobile: `VT_R4` (4 - float single precision), `VT_R8` (5 - double precision)


* Booleani e Stringhe: `VT_BOOL` (11), `VT_BSTR` (8 - stringhe OLE/Unicode)


* Data e Ora: `VT_DATE` (7)




* **Modificatori di Bit / Maschere**:
* `VT_ARRAY` (`0x2000`): Maschera logica OR applicata quando il valore trasmesso è un array (vettore) del tipo base corrispondente (es. array di float o interi).


* `VT_VARIANT` (12): Indica un tipo generico Variant o un array eterogeneo (`VT_VARIANT | VT_ARRAY`).





---

# 2. Modulo `orinexception.py`

Questo modulo gestisce la codifica degli errori di sistema e le eccezioni sollevate durante la comunicazione b-CAP.

### Classi Incluse

* **`HResult`**:
* Fornisce costanti esadecimali/intere per i codici di ritorno HRESULT (standard Windows/ORiN).


* Include errori noti come:
* `S_OK` (0): Operazione completata con successo.


* `S_EXECUTING` (2304): Operazione ancora in elaborazione.


* `E_ACCESSDENIED` (-2147024891): Accesso negato (es. semaforo braccio non concesso).


* `E_TIMEOUT` (-2147481344): Timeout della richiesta.


* `E_INVALIDPACKET` (-2147418112): Pacchetto b-CAP corrotto o delimitatori SOH/EOT errati.


* `E_CAO_VARIANT_TYPE_NOSUPPORT` (-2147483133): Tipo variant non supportato durante la serializzazione/deserializzazione.




* **Metodi di utilità**:
* `HResult.succeeded(hr)`: Restituisce `True` se `hr >= 0`.


* `HResult.failed(hr)`: Restituisce `True` se `hr < 0`.






* **`ORiNException(Exception)`**:
* Eccezione personalizzata sollevata dal client ogni volta che un comando b-CAP restituisce un HRESULT negativo.


* Attributo `hresult`: Contiene il codice HRESULT di fallimento.





---

# 3. Modulo `bcapclient.py`

Contiene la classe **`BCAPClient`**, che implementa il protocollo binario di comunicazione client TCP/IP b-CAP verso controller DENSO (reali o virtuali WINCAPS/VRC).

---

## 3.1 Connessione, Sessione e Configurazione Rete

* **`__init__(self, host, port, timeout)`**

Inizializza l'istanza, imposta timeout, contatore pacchetti seriale e apre la connessione socket TCP verso il server b-CAP specificato.


* **`__del__(self)`**

Distruttore: chiude e rilascia in sicurezza la connessione socket attiva.


* **`settimeout(self, timeout)`**

Imposta il valore di timeout per le operazioni socket.


* **`gettimeout(self)`**

Restituisce il timeout corrente impostato.


* **`service_start(self, option="")`**

Avvia il servizio b-CAP sul server (Function ID: 1).


* **`service_stop(self)`**

Arresta il servizio b-CAP sul server (Function ID: 2).


* **`controller_connect(self, name, provider, machine, option)`**

Stabilisce la connessione con il controller specificato (es. provider `"CaoProv.DENSO.VRC"` o `"CaoProv.DENSO.RC8"`) e restituisce l'handle (`h_ctrl`) del controller (Function ID: 3).


* **`controller_disconnect(self, handle)`**

Chiude la sessione e disconnette il controller identificato dall'handle (Function ID: 4).



---

## 3.2 Esecuzione Comandi (Execute)

Metodi utilizzati per inviare comandi di esecuzione generici a oggetti specifici:

* **`controller_execute(self, handle, command, param=None)`**

Invia un comando di esecuzione al controller (es. `"ClearError"`) (Function ID: 17).


* **`extension_execute(self, handle, command, param=None)`**

Esegue un comando sull'oggetto estensione (Function ID: 28).


* **`file_execute(self, handle, command, param=None)`**

Esegue un comando sull'oggetto file (Function ID: 41).


* **`robot_execute(self, handle, command, param=None)`**

Invia comandi diretti di attuazione e controllo al braccio (es. `"TakeArm"`, `"GiveArm"`, `"Motor"`, `"Move"`, `"CurPos"`) (Function ID: 64).


* **`task_execute(self, handle, command, param=None)`**

Invia un comando di esecuzione a un task del controller (Function ID: 87).


* **`command_execute(self, handle, mode)`**

Esegue un oggetto comando b-CAP/ORiN nella modalità indicata (Function ID: 112).


* **`command_cancel(self, handle)`**

Annulla l'esecuzione del comando in corso (Function ID: 113).

---

## 3.3 Movimento e Controllo Cinematica Robot

Metodi dedicati all'attuazione motoria del braccio:

* **`robot_move(self, handle, comp, pose, option="")`**

Comanda un movimento verso la posa target con interpolazione specificata (`comp`) (Function ID: 72).


* **`robot_speed(self, handle, axis, speed)`**

Imposta la percentuale di velocità per uno specifico asse o globale (Function ID: 74).


* **`robot_accelerate(self, handle, axis, accel, decel)`**

Configura accelerazione e decelerazione (Function ID: 65).


* **`robot_drive(self, handle, axis, mov, option="")`**

Movimenta un singolo asse di una quantità relativa (Function ID: 68).


* **`robot_rotate(self, handle, rotsuf, deg, pivot, option="")`**

Esegue una rotazione attorno a un punto pivot (Function ID: 73).


* **`robot_change(self, handle, name)`**

Cambia utensile (tool) o sistema di coordinate di lavoro (Function ID: 66).


* **`robot_gohome(self, handle)`**

Comanda il ritorno del robot alla posizione di riposo iniziale/Home (Function ID: 69).


* **`robot_halt(self, handle, option="")`**

Arresta immediatamente il robot (Function ID: 70).


* **`robot_hold(self, handle, option="")`**

Mette in pausa/sospensione la traiettoria corrente (Function ID: 71).


* **`robot_unhold(self, handle, option="")`**

Riprende la traiettoria precedentemente sospesa (Function ID: 76).


* **`robot_chuck(self, handle, option="")`**

Attiva la pinza / gripper di presa (Function ID: 67).


* **`robot_unchuck(self, handle, option="")`**

Rilascia la pinza / gripper (Function ID: 75).



---

## 3.4 Acquisizione Oggetti (Get Handle) ed Esplorazione Nomi

Metodi usati per ottenere gli handle dei sotto-oggetti del controller e visualizzarne le liste disponibili:

* **Controller**:
* `controller_getrobot(handle, name, option="")` / `controller_getrobotnames(handle, option="")` (ID: 7, 13)


* `controller_gettask(handle, name, option="")` / `controller_gettasknames(handle, option="")` (ID: 8, 14)


* `controller_getvariable(handle, name, option="")` / `controller_getvariablenames(handle, option="")` (ID: 9, 15)


* `controller_getfile(handle, name, option="")` / `controller_getfilenames(handle, option="")` (ID: 6, 12)


* `controller_getcommand(handle, name, option="")` / `controller_getcommandnames(handle, option="")` (ID: 10, 16)


* `controller_getextension(handle, name, option="")` / `controller_getextensionnames(handle, option="")` (ID: 5, 11)


* `controller_getmessage(handle)` (ID: 18)




* **Sotto-oggetti**:
* `extension_getvariable(handle, name, option="")` / `extension_getvariablenames(handle, option="")` (ID: 26, 27)


* `file_getfile(handle, name, option="")` / `file_getfilenames(handle, option="")` (ID: 37, 39)


* `file_getvariable(handle, name, option="")` / `file_getvariablenames(handle, option="")` (ID: 38, 40)


* `robot_getvariable(handle, name, option="")` / `robot_getvariablenames(handle, option="")` (ID: 62, 63)


* `task_getvariable(handle, name, option="")` / `task_getvariablenames(handle, option="")` (ID: 85, 86)





---

## 3.5 Gestione delle Variabili (I/O, Posizioni, Registri)

* **`variable_getvalue(self, handle)`**

Legge il valore corrente della variabile identificata da `handle` (Function ID: 101).


* **`variable_putvalue(self, handle, newval)`**

Scrive un nuovo valore (scalare, stringa, lista di coordinate o variant) nella variabile (Function ID: 102).


* **`variable_getdatetime(self, handle)`**

Legge il timestamp associato all'ultimo aggiornamento della variabile (Function ID: 100).


* **`variable_getmicrosecond(self, handle)`**

Restituisce i microsecondi relativi al timestamp della variabile (Function ID: 110).



---

## 3.6 Gestione dei Task (Processi PacScript)

* **`task_start(self, handle, mode, option="")`**

Avvia l'esecuzione del task selezionato (Function ID: 88).


* **`task_stop(self, handle, mode, option="")`**

Arresta l'esecuzione del task (Function ID: 89).


* **`task_delete(self, handle, option="")`**

Elimina il task dalla memoria del controller (Function ID: 90).


* **`task_getfilename(self, handle)`**

Restituisce il nome del file script associato al task (Function ID: 91).



---

## 3.7 Gestione dei File

* Operazioni sul filesystem del controller:
* `file_run(handle, option="")`: Esegue il file (ID: 45).


* `file_copy(handle, name, option="")`: Copia il file (ID: 42).


* `file_move(handle, name, option="")`: Sposta/rinomina il file (ID: 44).


* `file_delete(handle, option="")`: Cancella il file (ID: 43).




* Attributi e contenuto del file:
* `file_getvalue(handle)` / `file_putvalue(handle, newval)`: Legge o scrive il contenuto binario/testuale del file (ID: 52, 53).


* `file_getpath(handle)`: Restituisce il percorso completo (ID: 49).


* `file_getsize(handle)`: Restituisce la dimensione in byte (ID: 50).


* `file_gettype(handle)`: Restituisce il tipo di file (ID: 51).


* `file_getdatecreated(handle)` / `file_getdatelastaccessed(handle)` / `file_getdatelastmodified(handle)`: Date di creazione, accesso e modifica (ID: 46, 47, 48).





---

## 3.8 Gestione dei Messaggi

Metodi per interagire con le notifiche di sistema e i messaggi dell'operatore:

* `message_reply(handle, data)`: Invia una risposta al messaggio (ID: 128).


* `message_clear(handle)`: Cancella il messaggio (ID: 129).


* `message_getvalue(handle)`: Ottiene il valore del messaggio (ID: 136).


* `message_getdescription(handle)` / `message_getnumber(handle)`: Descrizione e codice d'errore (ID: 131, 133).


* `message_getsource(handle)` / `message_getdestination(handle)`: Mittente e destinatario (ID: 135, 132).


* `message_getdatetime(handle)` / `message_getserialnumber(handle)`: Data e seriale del messaggio (ID: 130, 134).



---

## 3.9 Configurazione Oggetto Command

Metodi per la gestione dei comandi asincroni complessi:

* `command_getstate(handle)`: Verifica lo stato di avanzamento del comando (ID: 116).


* `command_getresult(handle)`: Legge il risultato al termine dell'operazione (ID: 119).


* `command_gettimeout(handle)` / `command_puttimeout(handle, newval)`: Lettura/scrittura del timeout (ID: 114, 115).


* `command_getparameters(handle)` / `command_putparameters(handle, newval)`: Parametri in ingresso al comando (ID: 117, 118).



---

## 3.10 Proprietà Comuni degli Oggetti e Rilascio Risorse (Release)

Ogni entità creata sul controller assegna risorse in memoria che devono essere rilasciate terminato l'uso:

* **Rilascio Handle (`*_release`)**:
* `extension_release(handle)` (ID: 36)


* `file_release(handle)` (ID: 61)


* `robot_release(handle)` (ID: 84)


* `task_release(handle)` (ID: 99)


* `variable_release(handle)` (ID: 111)


* `command_release(handle)` (ID: 127)


* `message_release(handle)` (ID: 137)




* **Attributi e Metadati Generali (`*_getattribute`, `*_gethelp`, `*_getname`, `*_gettag`, `*_puttag`, `*_getid`, `*_putid`)**:
Disponibili per controller, estensioni, file, robot, task, variabili e comandi. Permettono di leggere descrizioni, ID identificativi, nomi simbolici o associare tag personalizzati a ciascun elemento.



---

## 3.11 Utilità Interne e Serializzazione del Protocollo

* **`datetime2vntdate(date)`** / **`vntdate2datetime(date)`**

Metodi di utilità per convertire oggetti `datetime.datetime` Python nello standard OLE Automation Date (e viceversa), basato su float in giorni dal 30/12/1899.


* **`_send_and_recv(self, funcid, args)`**

Metodo core thread-safe: acquisisce il lock, serializza il pacchetto b-CAP con il Function ID, trasmette via socket, attende la risposta, verifica l'HRESULT tramite `HResult.failed()` e solleva `ORiNException` in caso di errore.


* **`_serialize(self, serial, version, funcid, args)`** / **`_deserialize(self, buf)`**

Formattano e decodificano i frame b-CAP delimitati da `_BCAP_SOH` (`0x1`) e `_BCAP_EOT` (`0x4`), gestendo le conversioni di tipo secondo il dizionario `_DICT_TYPE2VT`.
