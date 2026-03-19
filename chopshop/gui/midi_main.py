"""Entry point for the MIDI generator GUI."""

import sys


def main():
    from PySide6.QtWidgets import QApplication

    from .midi_window import MidiWindow

    app = QApplication(sys.argv)
    app.setApplicationName("ChopShop MIDI")
    win = MidiWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
