"""PC TuneUp tab: runs the bundled PC-TuneUp PowerShell script.

The script (PC-TuneUp-v1.ps1, kept verbatim under resources/tuneup/) performs
a full health pass: restore point, hardware/software inventory, safe cleanup,
winget upgrades, Windows Update, DISM/SFC repair, and an HTML report on the
Desktop. OmniTune runs it elevated (the app already elevates at launch) and
streams its output live. Native per-phase reimplementation is on the roadmap.
"""
import glob
import os
import sys

from PySide6.QtCore import QProcess, QUrl, Qt
from PySide6.QtGui import QDesktopServices, QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

TITLE = "TuneUp"
DESCRIPTION = (
    "One-click PC health pass: creates a system restore point first, then "
    "inventories your hardware, cleans temp files, updates apps via winget, "
    "runs Windows Update, repairs system files (DISM + SFC), and writes an "
    "HTML health report to your Desktop."
)
ROADMAP = [
    "Per-phase toggles (run only the phases you want) - next",
    "Native Python reimplementation, phase by phase - next",
    "In-app HTML report viewer - next",
]

PHASES = [
    "1. Safety net - system restore point before anything changes",
    "2. Inventory - CPU, RAM, disks, GPU, BIOS, installed software",
    "3. Safe cleanup - temp files, update cache, component store",
    "4. App updates - winget upgrade --all",
    "5. Windows Update - OS and driver updates",
    "6. Repair - DISM /RestoreHealth + SFC /scannow",
    "7. Report - battery, startup apps, HTML report on Desktop",
]

SCRIPT_REL = os.path.join("tuneup", "PC-TuneUp-v1.ps1")


def resource_path(*parts):
    """Locate a bundled resource, frozen (PyInstaller) or from source."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, "omniture", "resources", *parts)
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "resources", *parts))


def latest_report():
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    matches = sorted(glob.glob(os.path.join(desktop, "PC-Health-Report-*.html")))
    return matches[-1] if matches else None


class TuneUpPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc = None

        layout = QVBoxLayout(self)
        desc = QLabel("<h2>TuneUp</h2>" + DESCRIPTION)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self.phase_list = QListWidget()
        self.phase_list.addItems(PHASES)
        self.phase_list.setMaximumHeight(170)
        layout.addWidget(self.phase_list)

        btns = QHBoxLayout()
        self.run_btn = QPushButton("Run TuneUp")
        self.run_btn.clicked.connect(self._run)
        btns.addWidget(self.run_btn)
        self.view_btn = QPushButton("View Script")
        self.view_btn.setToolTip("Open the bundled PowerShell script to inspect exactly what it does.")
        self.view_btn.clicked.connect(self._view_script)
        btns.addWidget(self.view_btn)
        self.report_btn = QPushButton("Open Latest Report")
        self.report_btn.clicked.connect(self._open_report)
        btns.addWidget(self.report_btn)
        btns.addStretch(1)
        layout.addLayout(btns)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("TuneUp output will stream here while it runs.")
        layout.addWidget(self.log, 1)

        self._refresh_report_button()

    # -- actions ------------------------------------------------------
    def _script_path(self):
        return resource_path(SCRIPT_REL)

    def _view_script(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self._script_path()))

    def _open_report(self):
        report = latest_report()
        if report:
            QDesktopServices.openUrl(QUrl.fromLocalFile(report))
        else:
            QMessageBox.information(self, "Report", "No PC-Health-Report found on the Desktop yet.")

    def _refresh_report_button(self):
        self.report_btn.setEnabled(latest_report() is not None)

    def _run(self):
        script = self._script_path()
        if not os.path.isfile(script):
            QMessageBox.warning(self, "TuneUp", "Bundled script not found:\n%s" % script)
            return
        answer = QMessageBox.question(
            self, "Run PC TuneUp?",
            "This runs the full 7-phase tune-up:\n\n"
            "- Creates a system restore point first (safety net)\n"
            "- Updates apps (winget) and Windows (OS + drivers)\n"
            "- Repairs system files (DISM + SFC)\n"
            "- Writes an HTML health report to your Desktop\n\n"
            "It takes 30-60+ minutes and you should restart the PC "
            "afterwards. The script is bundled verbatim - use 'View Script' "
            "to inspect it first.\n\nRun it now?",
            QMessageBox.Yes | QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        self.log.clear()
        self._append_log("Starting PC-TuneUp v1 ...\n")
        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # busy: phases vary in length
        self._proc = QProcess(self)
        self._proc.readyReadStandardOutput.connect(self._on_output)
        self._proc.readyReadStandardError.connect(self._on_output)
        self._proc.finished.connect(self._on_finished)
        self._proc.start("powershell.exe",
                         ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script])
        if not self._proc.waitForStarted(10000):
            self._append_log("ERROR: could not start PowerShell.\n")
            self._run_ended()

    # -- process events -----------------------------------------------
    def _on_output(self):
        if self._proc is None:
            return
        data = bytes(self._proc.readAllStandardOutput()).decode("utf-8", errors="replace")
        err = bytes(self._proc.readAllStandardError()).decode("utf-8", errors="replace")
        if data:
            self._append_log(data)
        if err:
            self._append_log(err)

    def _on_finished(self, exit_code, _status):
        self._append_log("\nTuneUp finished with exit code %d.\n" % exit_code)
        self._run_ended()
        self._refresh_report_button()
        report = latest_report()
        msg = "TuneUp finished."
        if report:
            msg += "\n\nReport: %s" % os.path.basename(report)
        msg += "\n\nRestart your PC so pending updates finish installing."
        QMessageBox.information(self, "TuneUp finished", msg)

    def _run_ended(self):
        self.run_btn.setEnabled(True)
        self.progress.setVisible(False)
        self._proc = None

    def _append_log(self, text):
        self.log.moveCursor(QTextCursor.End)
        self.log.insertPlainText(text)
        self.log.moveCursor(QTextCursor.End)


def create_panel():
    return TuneUpPanel()
