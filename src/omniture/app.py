"""OmniTune main window: one tab per maintenance module."""
from PySide6.QtWidgets import QMainWindow, QMessageBox, QTabWidget

from . import version
from .modules import debloat, disk, drivers, tuneup, updates

MODULES = (drivers, updates, debloat, disk, tuneup)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"OmniTune v{version.__version__}")
        self.resize(1024, 720)

        self.tabs = QTabWidget()
        for mod in MODULES:
            self.tabs.addTab(mod.create_panel(), mod.TITLE)
        self.setCentralWidget(self.tabs)

        self._build_menus()
        self.statusBar().showMessage(
            "Tip: run as administrator — every module needs elevation."
        )

    def closeEvent(self, event):
        """Let panels stop their background workers before teardown."""
        for i in range(self.tabs.count()):
            panel = self.tabs.widget(i)
            shutdown = getattr(panel, "shutdown", None)
            if callable(shutdown):
                try:
                    shutdown()
                except Exception:  # noqa: BLE001 - best effort
                    pass
        super().closeEvent(event)

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        exit_action = file_menu.addAction("E&xit")
        exit_action.triggered.connect(self.close)

        help_menu = self.menuBar().addMenu("&Help")
        about_action = help_menu.addAction("&About OmniTune")
        about_action.triggered.connect(self._show_about)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About OmniTune",
            (
                f"<b>OmniTune v{version.__version__}</b><br><br>"
                "All-in-one open-source Windows maintenance toolkit.<br>"
                "Drivers · Updates · Debloat · Disk<br><br>"
                "Licensed under GPL-3.0.<br>"
                "Feature concepts inspired by Snappy Driver Installer, "
                "WuMgr, Win11Debloat and WinDirStat - every feature is "
                "reimplemented from scratch; no upstream code is bundled.<br>"
                "The TuneUp tab runs the bundled PC-TuneUp script verbatim."
            ),
        )
