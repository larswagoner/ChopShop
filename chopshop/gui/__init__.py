import sys


def main():
    from PySide6.QtWidgets import QApplication

    from .window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("ChopShop")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
