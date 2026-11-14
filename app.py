import os
import sys
import ctypes

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

from main_window import MainWindow

def setup_windows_appid():
    """
    Sets explicit Windows Application User Model ID so the taskbar
    and tray icon show the custom application icon properly.
    """
    if sys.platform == "win32":
        try:
            myappid = "usd.hrn.ratemonitor.sense.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception as e:
            print("Could not set Windows AppID:", e)

def main():
    setup_windows_appid()

    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("USD / UAH Монитор")
    app.setApplicationDisplayName("USD / UAH Монитор")

    # Important: do NOT quit application when main window is closed (hidden to tray)
    app.setQuitOnLastWindowClosed(False)

    icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "icon.png"))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
