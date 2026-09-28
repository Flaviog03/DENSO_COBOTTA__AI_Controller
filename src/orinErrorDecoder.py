from pybcapclient.orinexception import ORiNException, HResult


class OrinErrorDecoder:
    """Decodifica i codici numerici di ORiNException in messaggi leggibili."""

    # 1. Mappatura diretta in italiano dei codici più frequenti sul COBOTTA / VRC
    CUSTOM_ERRORS: dict[int, str] = {
        -2095049471: "Out of Bounds: posizione fuori dal raggio d'azione o dai limiti dei giunti del robot.",
        -2125459419: "Controller bloccato da un errore precedente: necessario eseguire ClearError prima di TakeArm.",
        -2147024809: "Argomento non valido (E_INVALIDARG): controlla handle e parametri passati al comando.",
        -2147024891: "Accesso negato (E_ACCESSDENIED): imposta il Teach Pendant in AUTO e Exec. Provider su Ethernet.",
        -2147467263: "Funzione non implementata (E_NOTIMPL): comando non supportato dal controller o dal VRC.",
        -2147483131: "Collezione già registrata (E_CAO_COLLECTION_REGISTERED): handle non rilasciato correttamente.",
        -2147481344: "Timeout di comunicazione b-CAP (E_TIMEOUT).",
    }

    @classmethod
    def decode(cls, error: int | ORiNException, bcap=None, h_ctrl=None) -> str:
        """
        Restituisce una stringa formattata con:
        - Codice decimale ed esadecimale
        - Spiegazione in italiano (se presente in CUSTOM_ERRORS) o nome costante HResult
        - Descrizione ufficiale letta dal controller DENSO (se connesso)
        """
        hr = error.hresult if isinstance(error, ORiNException) else int(error)
        hex_code = f"0x{hr & 0xFFFFFFFF:08X}"

        # Livello 1: Cerca nel dizionario personalizzato
        messaggio_locale = cls.CUSTOM_ERRORS.get(hr)

        # Livello 2: Se non è nel dizionario, cerca tra le costanti di HResult in orinexception.py
        if not messaggio_locale:
            costante_orin = next(
                (k for k, v in HResult.__dict__.items() if v == hr and not k.startswith("_")),
                "ERRORE_ORIN_SCONOSCIUTO"
            )
            messaggio_locale = f"Costante ORiN: {costante_orin}"

        # Livello 3: Chiede al controller DENSO la descrizione interna del firmware
        dettaglio_controller = ""
        if bcap is not None and h_ctrl is not None:
            try:
                descr = bcap.controller_execute(h_ctrl, "GetErrorDescription", hr)
                if descr and str(descr).strip():
                    dettaglio_controller = f" | Firmware DENSO: '{str(descr).strip()}'"
            except Exception:
                pass

        return f"[{hr} / {hex_code}] {messaggio_locale}{dettaglio_controller}"