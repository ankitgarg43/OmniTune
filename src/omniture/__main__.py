"""Entry point: `python -m omniture`."""
import sys

from PySide6.QtWidgets import QApplication

from . import version
from .app import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("OmniTune")
    app.setApplicationVersion(version.__version__)
    app.setOrganizationName("OmniTune")

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
