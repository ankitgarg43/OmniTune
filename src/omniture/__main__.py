"""Entry point: `python -m omniture`."""
import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from . import version
from .app import MainWindow
from .theme import apply_theme


def resource_path(*parts):
    """Absolute path to a bundled resource (works in dev and PyInstaller)."""
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = os.path.dirname(__file__)
        return os.path.normpath(os.path.join(base, "resources", *parts))
    return os.path.join(base, "omniture", "resources", *parts)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("OmniTune")
    app.setApplicationVersion(version.__version__)
    app.setOrganizationName("OmniTune")
    apply_theme(app)
    icon = resource_path("icon", "omniture.ico")
    if os.path.exists(icon):
        app.setWindowIcon(QIcon(icon))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
