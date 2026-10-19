"""Windows Update manager module: check, install, hide updates + history.

Feature set modeled on wumgr / WuMgr (GPL-3.0, DavidXanatos):
https://github.com/DavidXanatos/wumgr
Clean-room reimplementation - no wumgr code is used. Talks to the
Windows Update Agent API through updates_engine.
"""
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import updates_engine as engine

TITLE = "Updates"
DESCRIPTION = (
    "Take control of Windows Update: check for updates on demand, install "
    "only what you choose, hide the ones you never want, and browse the "
    "install history."
)
ROADMAP = [
    "Per-update download/install progress bars",
    "Automatic-update policy presets (notify / download / manual)",
    "Offline update catalog (.msu) installation",
]


class _Worker(QThread):
    progressed = Signal(str)
    done = Signal(object)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:  # noqa: BLE001 - non-Windows / already init'd
            pass
        try:
            self.done.emit(("ok", self._fn(self.progressed.emit)))
        except Exception as exc:  # noqa: BLE001 - reported to the UI
            self.done.emit(("error", str(exc)))
        finally:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:  # noqa: BLE001
                pass


class _HistoryDialog(QDialog):
    def __init__(self, entries, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Update History")
        self.resize(760, 420)
        layout = QVBoxLayout(self)
        table = QTableWidget(len(entries), 4)
        table.setHorizontalHeaderLabels(
            ["Title", "Date", "Operation", "Result"])
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        for row, entry in enumerate(entries):
            table.setItem(row, 0, QTableWidgetItem(entry["title"]))
            table.setItem(row, 1, QTableWidgetItem(entry["date"]))
            table.setItem(row, 2, QTableWidgetItem(entry["operation"]))
            table.setItem(row, 3, QTableWidgetItem(entry["result"]))
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close, alignment=Qt.AlignRight)


class UpdatesPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._updates = []  # parallel to table rows

        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self.check_btn = QPushButton("Check for Updates")
        self.check_btn.setProperty("primary", "true")
        self.check_btn.clicked.connect(self._on_check)
        self.history_btn = QPushButton("Show History")
        self.history_btn.clicked.connect(self._on_history)
        self.status = QLabel("No check performed yet.")
        self.status.setWordWrap(True)
        top.addWidget(self.check_btn)
        top.addWidget(self.history_btn)
        top.addWidget(self.status, 1)
        layout.addLayout(top)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["", "Title", "KB", "Categories", "Mandatory"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        self.install_btn = QPushButton("Download && Install Selected")
        self.install_btn.setProperty("primary", "true")
        self.install_btn.clicked.connect(self._on_install)
        self.hide_btn = QPushButton("Hide Selected")
        self.hide_btn.clicked.connect(lambda: self._on_hide(True))
        self.unhide_btn = QPushButton("Unhide Selected")
        self.unhide_btn.clicked.connect(lambda: self._on_hide(False))
        for btn in (self.install_btn, self.hide_btn, self.unhide_btn):
            actions.addWidget(btn)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(120)
        layout.addWidget(QLabel("Log"))
        layout.addWidget(self.log)

        self._log("Updates module ready. Uses the Windows Update Agent API.")

    # -- helpers ---------------------------------------------------------
    def _log(self, msg):
        self.log.append(msg)

    def _set_busy(self, busy):
        for w in (self.check_btn, self.history_btn, self.install_btn,
                  self.hide_btn, self.unhide_btn):
            w.setEnabled(not busy)

    def _run_worker(self, fn, on_done):
        self._set_busy(True)
        self._worker = _Worker(fn, self)
        self._worker.progressed.connect(self._log)
        self._worker.done.connect(on_done)
        self._worker.done.connect(lambda _r: self._set_busy(False))
        self._worker.start()

    def _selected_ids(self):
        ids = []
        for row in range(self.table.rowCount()):
            box = self.table.cellWidget(row, 0)
            if box is not None and box.isChecked():
                ids.append(self._updates[row]["update_id"])
        return ids

    # -- actions ------------------------------------------------------------
    def _on_check(self):
        if not engine.com_available():
            QMessageBox.warning(self, "Updates",
                                "Windows Update API is only available on "
                                "Windows.")
            return
        self.status.setText("Searching for updates (can take a few minutes)...")
        self._log("Searching Windows Update...")

        def job(log):
            infos = engine.check_updates()
            log(f"Found {len(infos)} update(s).")
            return infos

        def finished(result):
            status, payload = result
            if status != "ok":
                self.status.setText("Search failed - see log.")
                self._log(f"Search failed: {payload}")
                return
            self._updates = payload
            self.table.setRowCount(len(payload))
            for row, info in enumerate(payload):
                box = QCheckBox()
                box.setChecked(True)
                self.table.setCellWidget(row, 0, box)
                self.table.setItem(row, 1, QTableWidgetItem(info["title"]))
                self.table.setItem(row, 2, QTableWidgetItem(info["kb"]))
                self.table.setItem(
                    row, 3, QTableWidgetItem(", ".join(info["categories"])))
                self.table.setItem(
                    row, 4, QTableWidgetItem(
                        "Yes" if info["mandatory"] else ""))
            self.table.resizeColumnsToContents()
            self.table.horizontalHeader().setStretchLastSection(True)
            self.status.setText(f"{len(payload)} update(s) found.")
        self._run_worker(job, finished)

    def _on_install(self):
        ids = self._selected_ids()
        if not ids:
            QMessageBox.information(self, "Updates",
                                    "Tick at least one update first.")
            return
        confirm = QMessageBox.question(
            self, "Install Updates",
            f"Download and install {len(ids)} selected update(s)?\n"
            "This can take a long time. A reboot may be required afterwards.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if confirm != QMessageBox.Yes:
            return

        def job(log):
            engine.download_updates(ids, log=log)
            installed, reboot = engine.install_updates(ids, log=log)
            if reboot:
                log("A REBOOT is required to finish installation.")
            return installed, reboot

        def finished(result):
            status, payload = result
            if status != "ok":
                self._log(f"Install failed: {payload}")
                return
            installed, reboot = payload
            self.status.setText(
                f"Installed {installed} update(s)."
                + (" Reboot required." if reboot else ""))
            if reboot:
                QMessageBox.information(
                    self, "Updates",
                    "Installation finished. Please reboot Windows to "
                    "complete it.")
            self._on_check()  # refresh the list
        self._run_worker(job, finished)

    def _on_hide(self, hide):
        ids = self._selected_ids()
        if not ids:
            QMessageBox.information(self, "Updates",
                                    "Tick at least one update first.")
            return

        def job(log):
            return engine.set_hidden(ids, hide=hide, log=log)

        def finished(result):
            self._on_check()  # refresh (hidden ones drop out of the list)
        self._run_worker(job, finished)

    def _on_history(self):
        if not engine.com_available():
            QMessageBox.warning(self, "Updates",
                                "Windows Update API is only available on "
                                "Windows.")
            return
        self._log("Reading update history...")

        def job(log):
            return engine.get_history(100)

        def finished(result):
            status, payload = result
            if status != "ok":
                self._log(f"History failed: {payload}")
                return
            _HistoryDialog(payload, self).exec()
        self._run_worker(job, finished)


def create_panel() -> QWidget:
    return UpdatesPanel()
