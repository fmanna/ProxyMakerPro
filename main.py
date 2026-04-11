"""
ProxyMakerPro — entry point.

Run with:
    pip install -r requirements.txt
    python main.py
"""

import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("ProxyMakerPro")
    app.setApplicationDisplayName("ProxyMakerPro")
    app.setOrganizationName("ProxyMakerPro")
    # Use the native macOS style (native controls, dark-mode aware)
    app.setStyle("macos")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
