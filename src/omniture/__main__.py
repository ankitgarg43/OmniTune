"""Entry point: `python -m omniture`."""
import sys

from PySide6.QtWidgets import QApplication

from . import version
from .app import MainWindow
from .theme import apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("OmniTune")
    app.setApplicationVersion(version.__version__)
    app.setOrganizationName("OmniTune")
    apply_theme(app)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
