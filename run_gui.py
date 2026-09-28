import sys
import os

if getattr(sys, 'frozen', False):
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

src_dir = os.path.join(base_dir, 'src')
for path in [base_dir, src_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow
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
