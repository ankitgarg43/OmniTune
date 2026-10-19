"""Driver management module: hardware scan + driver updates via Windows Update.

Concept inspired by Snappy Driver Installer / SDI (GPL-3.0, gtumanyan):
https://github.com/gtumanyan/SDI
Clean-room reimplementation - no SDI code is used.

v0.4.0 scope: hardware inventory (Get-PnpDevice), problem-device flagging,
on-demand driver details, and driver updates through the Windows Update
Agent API (shared with the Updates module).
"""
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import drivers_engine as engine
from . import updates_engine

TITLE = "Drivers"
DESCRIPTION = (
    "Scan your hardware, spot devices with missing or broken drivers, and "
    "install driver updates from Windows Update."
)
ROADMAP = [
    "Offline driver-pack index support (torrent / 7z)",
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


class DriversPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._devices = []
        self._drv_updates = []

        layout = QVBoxLayout(self)
        split = QSplitter(Qt.Vertical)

        # -- hardware ------------------------------------------------------
        hw_box = QGroupBox("Hardware")
        hw_layout = QVBoxLayout(hw_box)
        hw_top = QHBoxLayout()
        self.scan_btn = QPushButton("Scan Hardware")
        self.scan_btn.setProperty("primary", "true")
        self.scan_btn.clicked.connect(self._on_scan)
        self.hw_status = QLabel("No scan performed yet.")
        self.hw_status.setWordWrap(True)
        hw_top.addWidget(self.scan_btn)
        hw_top.addWidget(self.hw_status, 1)
        hw_layout.addLayout(hw_top)

        self.dev_table = QTableWidget(0, 4)
        self.dev_table.setHorizontalHeaderLabels(
            ["Device", "Class", "Status", "Problem"])
        self.dev_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.dev_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.dev_table.verticalHeader().setVisible(False)
        self.dev_table.itemSelectionChanged.connect(self._on_device_selected)
        hw_layout.addWidget(self.dev_table)

        self.dev_detail = QLabel("Select a device to see driver details.")
        self.dev_detail.setWordWrap(True)
        self.dev_detail.setTextFormat(Qt.RichText)
        hw_layout.addWidget(self.dev_detail)
        split.addWidget(hw_box)

        # -- driver updates -------------------------------------------------
        upd_box = QGroupBox("Driver updates (Windows Update)")
        upd_layout = QVBoxLayout(upd_box)
        upd_top = QHBoxLayout()
        self.check_btn = QPushButton("Check Driver Updates")
        self.check_btn.clicked.connect(self._on_check_drivers)
        self.install_btn = QPushButton("Install Selected")
        self.install_btn.setProperty("primary", "true")
        self.install_btn.clicked.connect(self._on_install_drivers)
        self.inf_btn = QPushButton("Install from Folder...")
        self.inf_btn.clicked.connect(self._on_install_inf)
        self.export_btn = QPushButton("Export Drivers...")
        self.export_btn.clicked.connect(self._on_export_drivers)
        self.upd_status = QLabel("No check performed yet.")
        self.upd_status.setWordWrap(True)
        upd_top.addWidget(self.check_btn)
        upd_top.addWidget(self.install_btn)
        upd_top.addWidget(self.inf_btn)
        upd_top.addWidget(self.export_btn)
        upd_top.addWidget(self.upd_status, 1)
        upd_layout.addLayout(upd_top)

        self.upd_table = QTableWidget(0, 4)
        self.upd_table.setHorizontalHeaderLabels(
            ["", "Title", "KB", "Categories"])
        self.upd_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.upd_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.upd_table.verticalHeader().setVisible(False)
        upd_layout.addWidget(self.upd_table)
        split.addWidget(upd_box)

        split.setSizes([420, 300])
        layout.addWidget(split, 1)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(100)
        layout.addWidget(QLabel("Log"))
        layout.addWidget(self.log)

        self._log("Drivers module ready. Scan hardware, then check for "
                  "driver updates.")

    # -- helpers ---------------------------------------------------------
    def _log(self, msg):
        self.log.append(msg)

    def shutdown(self):
        """Stop the background worker (called on app close)."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.wait(3000)
        self._worker = None

    def _set_busy(self, busy):
        for w in (self.scan_btn, self.check_btn, self.install_btn,
                  self.inf_btn, self.export_btn):
            w.setEnabled(not busy)

    def _run_worker(self, fn, on_done):
        self._set_busy(True)
        self._worker = _Worker(fn, self)
        self._worker.progressed.connect(self._log)
        self._worker.done.connect(on_done)
        self._worker.done.connect(lambda _r: self._set_busy(False))
        self._worker.start()

    # -- hardware ------------------------------------------------------------
    def _on_scan(self):
        self.hw_status.setText("Scanning hardware...")
        self._log("Scanning PnP devices...")

        def job(log):
            devices = engine.scan_devices()
            problems = engine.problem_devices(devices)
            log(f"Found {len(devices)} device(s), "
                f"{len(problems)} with problems.")
            return devices

        def finished(result):
            status, payload = result
            if status != "ok":
                self.hw_status.setText("Scan failed - see log.")
                self._log(f"Scan failed: {payload}")
                return
            self._devices = payload
            problems = engine.problem_devices(payload)
            self.dev_table.setRowCount(len(payload))
            for row, dev in enumerate(payload):
                bad = dev in problems
                self.dev_table.setItem(
                    row, 0, QTableWidgetItem(dev["name"]))
                self.dev_table.setItem(
                    row, 1, QTableWidgetItem(dev["class"]))
                self.dev_table.setItem(
                    row, 2, QTableWidgetItem(dev["status"]))
                self.dev_table.setItem(
                    row, 3, QTableWidgetItem(
                        engine.problem_name(dev["problem"]) if bad else ""))
                if bad:
                    for col in range(4):
                        item = self.dev_table.item(row, col)
                        item.setBackground(Qt.darkRed)
            self.dev_table.resizeColumnsToContents()
            self.dev_table.horizontalHeader().setStretchLastSection(True)
            self.hw_status.setText(
                f"{len(payload)} device(s); {len(problems)} with problems "
                "(highlighted).")
        self._run_worker(job, finished)

    def _on_device_selected(self):
        rows = self.dev_table.selectionModel().selectedRows()
        if not rows:
            return
        dev = self._devices[rows[0].row()]
        iid = dev["instance_id"]
        if not iid:
            return
        self.dev_detail.setText("Reading driver details...")

        def job(log):
            return engine.device_details(iid)

        def finished(result):
            status, payload = result
            if status != "ok":
                self.dev_detail.setText("Could not read driver details.")
                return
            self.dev_detail.setText(
                f"<b>{dev['name']}</b><br>"
                f"Driver: {payload['driver_desc'] or 'n/a'}<br>"
                f"Version: {payload['driver_version'] or 'n/a'} &nbsp; "
                f"Date: {payload['driver_date'] or 'n/a'}<br>"
                f"Provider: {payload['driver_provider'] or 'n/a'} &nbsp; "
                f"Maker: {payload['manufacturer'] or 'n/a'}")
        self._run_worker(job, finished)

    # -- driver updates ---------------------------------------------------------
    def _on_check_drivers(self):
        if not updates_engine.com_available():
            QMessageBox.warning(self, "Drivers",
                                "Windows Update API is only available on "
                                "Windows.")
            return
        self.upd_status.setText("Searching for driver updates...")
        self._log("Searching Windows Update for drivers...")

        def job(log):
            infos = engine.check_driver_updates()
            log(f"Found {len(infos)} driver update(s).")
            return infos

        def finished(result):
            status, payload = result
            if status != "ok":
                self.upd_status.setText("Search failed - see log.")
                self._log(f"Search failed: {payload}")
                return
            self._drv_updates = payload
            self.upd_table.setRowCount(len(payload))
            for row, info in enumerate(payload):
                box = QCheckBox()
                box.setChecked(True)
                self.upd_table.setCellWidget(row, 0, box)
                self.upd_table.setItem(
                    row, 1, QTableWidgetItem(info["title"]))
                self.upd_table.setItem(
                    row, 2, QTableWidgetItem(info["kb"]))
                self.upd_table.setItem(
                    row, 3, QTableWidgetItem(", ".join(info["categories"])))
            self.upd_table.resizeColumnsToContents()
            self.upd_table.horizontalHeader().setStretchLastSection(True)
            self.upd_status.setText(f"{len(payload)} driver update(s) found.")
        self._run_worker(job, finished)

    def _on_install_drivers(self):
        ids = []
        for row in range(self.upd_table.rowCount()):
            box = self.upd_table.cellWidget(row, 0)
            if box is not None and box.isChecked():
                ids.append(self._drv_updates[row]["update_id"])
        if not ids:
            QMessageBox.information(self, "Drivers",
                                    "Tick at least one driver update first.")
            return
        confirm = QMessageBox.question(
            self, "Install Drivers",
            f"Download and install {len(ids)} driver update(s)?\n"
            "A reboot may be required afterwards.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if confirm != QMessageBox.Yes:
            return

        def job(log):
            return engine.install_driver_updates(ids, log=log)

        def finished(result):
            status, payload = result
            if status != "ok":
                self._log(f"Install failed: {payload}")
                return
            installed, reboot = payload
            self.upd_status.setText(
                f"Installed {installed} driver update(s)."
                + (" Reboot required." if reboot else ""))
            if reboot:
                QMessageBox.information(
                    self, "Drivers",
                    "Installation finished. Please reboot Windows to "
                    "complete it.")
            self._on_check_drivers()
        self._run_worker(job, finished)

    def _on_install_inf(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Driver Folder (recursive INF search)")
        if not folder:
            return
        confirm = QMessageBox.question(
            self, "Install Drivers",
            f"Install every driver INF found under:\n{folder}\n"
            "(including subfolders)?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if confirm != QMessageBox.Yes:
            return
        self._log(f"Installing drivers from {folder} ...")

        def job(log):
            ok, _summary = engine.install_inf_folder(folder, log=log)
            return ok

        def finished(result):
            status, payload = result
            if status == "ok" and payload:
                self._log("Driver installation from folder finished.")
                self._on_scan()  # refresh hardware view
        self._run_worker(job, finished)

    def _on_export_drivers(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Export Folder for Driver Backup")
        if not folder:
            return
        self._log(f"Exporting installed drivers to {folder} ...")

        def job(log):
            ok, _summary = engine.export_drivers(folder, log=log)
            return ok

        def finished(result):
            status, payload = result
            if status == "ok" and payload:
                self._log("Driver export finished.")
        self._run_worker(job, finished)


def create_panel() -> QWidget:
    return DriversPanel()
