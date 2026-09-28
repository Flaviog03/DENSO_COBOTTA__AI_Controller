import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from PySide6.QtWidgets import QApplication
from src.gui.main_window import MainWindow

import os
from dotenv import load_dotenv

def main():
    load_dotenv()
    app = QApplication(sys.argv)
    
    # Per avviare senza il braccio/microfono veri, puoi settare questi flag a True.
    # Attualmente li prendiamo di default da una variabile d'ambiente o li forziamo a True se non sei in lab.
    # mock_robot = True significa che non contatterà b-CAP ma simulerà.
    window = MainWindow(mock_robot=False, mock_voice=False, mock_ai=False)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
