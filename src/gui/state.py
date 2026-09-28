from enum import Enum, auto

class AppState(Enum):
    DISCONNECTED = auto()
    IDLE = auto()
    LISTENING = auto()
    PROCESSING_AI = auto()
    AWAITING_CONFIRMATION = auto()
    MOVING = auto()
    ERROR = auto()

class AppStateManager:
    def __init__(self):
        self.current_state = AppState.DISCONNECTED

    def transition_to(self, new_state: AppState) -> bool:
        """
        Cambia lo stato dell'applicazione. Si potrebbero aggiungere qui controlli
        sulle transizioni valide, se necessario.
        Restituisce True se la transizione ha successo.
        """
        # Per ora accettiamo tutte le transizioni, ma potremmo aggiungere
        # regole rigorose se necessario in futuro.
        print(f"[StateManager] Transizione: {self.current_state.name} -> {new_state.name}")
        self.current_state = new_state
        return True

    def get_state(self) -> AppState:
        return self.current_state
