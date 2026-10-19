"""Debloat & tweaks module: full Windows cleanup with safety net.

Feature set modeled on Win11Debloat (MIT):
https://github.com/Raphire/Win11Debloat
Clean-room reimplementation - no Win11Debloat code is used.

The tab offers:
  * 26 registry tweaks in 6 categories (privacy, AI, taskbar/search,
    Explorer, gaming, lock screen) with live applied/not-applied state
  * Pre-installed AppX removal with a curated default list + custom entries
  * System restore point before changes, and one-click revert of tweaks
    (original registry values are snapshotted to a JSON backup file)
"""
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import debloat_engine as engine
from .debloat_catalog import BLOATWARE_APPS, get_tweak, tweaks_by_category

TITLE = "Debloat"
DESCRIPTION = (
    "Remove pre-installed apps, disable telemetry and ads, and apply "
    "curated Windows tweaks - always with a restore point and a full "
    "undo path before anything changes."
)
ROADMAP = [
    "Per-user vs all-users AppX scope options",
]


class _Worker(QThread):
    progressed = Signal(str)
    done = Signal(object)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        try:
            self.done.emit(("ok", self._fn(self.progressed.emit)))
        except Exception as exc:  # noqa: BLE001 - reported to the UI
            self.done.emit(("error", str(exc)))


class DebloatPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._restored_this_session = False
        self._refreshing_tree = False

        layout = QVBoxLayout(self)

        # -- safety row -------------------------------------------------
        safety = QHBoxLayout()
        self.restore_btn = QPushButton("Create Restore Point")
        self.restore_btn.clicked.connect(self._on_restore_point)
        self.restore_status = QLabel("No restore point created yet this session.")
        self.restore_status.setWordWrap(True)
        safety.addWidget(self.restore_btn)
        safety.addWidget(self.restore_status, 1)
        layout.addLayout(safety)

        # -- main split: tweaks | bloatware ------------------------------
        split = QSplitter(Qt.Horizontal)

        tweaks_box = QGroupBox("Windows tweaks")
        tweaks_layout = QVBoxLayout(tweaks_box)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Tweak", "State"])
        self.tree.setColumnWidth(0, 260)
        self.tree.itemChanged.connect(self._on_tree_item_changed)
        tweaks_layout.addWidget(self.tree)

        tweak_btns = QHBoxLayout()
        self.apply_btn = QPushButton("Apply Selected")
        self.apply_btn.clicked.connect(self._on_apply)
        self.revert_btn = QPushButton("Revert Selected")
        self.revert_btn.clicked.connect(self._on_revert)
        self.refresh_btn = QPushButton("Refresh States")
        self.refresh_btn.clicked.connect(self._refresh_tweak_states)
        for btn in (self.apply_btn, self.revert_btn, self.refresh_btn):
            tweak_btns.addWidget(btn)
        tweaks_layout.addLayout(tweak_btns)

        profile_btns = QHBoxLayout()
        self.export_btn = QPushButton("Export Profile...")
        self.export_btn.clicked.connect(self._on_export_profile)
        self.import_btn = QPushButton("Import Profile...")
        self.import_btn.clicked.connect(self._on_import_profile)
        profile_btns.addWidget(self.export_btn)
        profile_btns.addWidget(self.import_btn)
        profile_btns.addStretch(1)
        tweaks_layout.addLayout(profile_btns)
        split.addWidget(tweaks_box)

        apps_box = QGroupBox("Pre-installed apps (AppX)")
        apps_layout = QVBoxLayout(apps_box)
        self.app_filter = QLineEdit()
        self.app_filter.setPlaceholderText("Filter apps...")
        self.app_filter.textChanged.connect(self._on_app_filter)
        apps_layout.addWidget(self.app_filter)
        self.app_list = QListWidget()
        apps_layout.addWidget(self.app_list)
        add_row = QHBoxLayout()
        self.custom_pkg = QLineEdit()
        self.custom_pkg.setPlaceholderText("Custom package name fragment...")
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._on_add_custom_app)
        add_row.addWidget(self.custom_pkg, 1)
        add_row.addWidget(add_btn)
        apps_layout.addLayout(add_row)
        self.remove_btn = QPushButton("Remove Selected Apps")
        self.remove_btn.setProperty("primary", "true")
        self.remove_btn.clicked.connect(self._on_remove_apps)
        apps_layout.addWidget(self.remove_btn)
        self.rereg_btn = QPushButton("Re-register Selected Apps")
        self.rereg_btn.clicked.connect(self._on_reregister_apps)
        apps_layout.addWidget(self.rereg_btn)
        split.addWidget(apps_box)

        split.setSizes([560, 420])
        layout.addWidget(split, 1)

        # -- log ---------------------------------------------------------
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(140)
        layout.addWidget(QLabel("Log"))
        layout.addWidget(self.log)

        self._build_tree()
        self._build_app_list()
        self._refresh_tweak_states()
        self._log("Debloat module ready. States reflect the live registry.")

    # -- helpers ---------------------------------------------------------
    def _log(self, msg):
        self.log.append(msg)

    def _set_busy(self, busy):
        for widget in (self.restore_btn, self.apply_btn, self.revert_btn,
                       self.refresh_btn, self.remove_btn, self.rereg_btn,
                       self.export_btn, self.import_btn):
            widget.setEnabled(not busy)

    def shutdown(self):
        """Stop the background worker (called on app close)."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.wait(3000)
        self._worker = None

    # -- tweak tree -------------------------------------------------------
    def _build_tree(self):
        self.tree.clear()
        for category, tweaks in tweaks_by_category():
            cat_item = QTreeWidgetItem(self.tree, [category, ""])
            cat_item.setFlags(cat_item.flags() | Qt.ItemIsUserCheckable
                              | Qt.ItemIsAutoTristate)
            cat_item.setCheckState(0, Qt.Unchecked)
            cat_item.setExpanded(True)
            for tweak in tweaks:
                child = QTreeWidgetItem(cat_item, [tweak["name"], "…"])
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                child.setCheckState(0, Qt.Unchecked)
                child.setData(0, Qt.UserRole, tweak["key"])
                child.setToolTip(0, tweak["desc"])

    def _on_tree_item_changed(self, _item, _column):
        # Tristate parents are handled by Qt; nothing to do here.
        pass

    def _checked_tweak_keys(self):
        keys = []
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            cat = root.child(i)
            for j in range(cat.childCount()):
                child = cat.child(j)
                if child.checkState(0) == Qt.Checked:
                    keys.append(child.data(0, Qt.UserRole))
        return keys

    def _refresh_tweak_states(self):
        self._refreshing_tree = True
        try:
            root = self.tree.invisibleRootItem()
            for i in range(root.childCount()):
                cat = root.child(i)
                for j in range(cat.childCount()):
                    child = cat.child(j)
                    tweak = get_tweak(child.data(0, Qt.UserRole))
                    state = engine.tweak_state(tweak)
                    child.setText(1, {
                        "applied": "Applied",
                        "not-applied": "Not applied",
                        "mixed": "Partially applied",
                        "unknown": "Unknown (non-Windows)",
                    }[state])
        finally:
            self._refreshing_tree = False

    # -- bloatware list -----------------------------------------------------
    def _build_app_list(self):
        self.app_list.clear()
        for app in BLOATWARE_APPS:
            self._add_app_row(app["pkg"], app["label"], app["default"])
        for pkg in engine.load_custom_apps():
            if not any(self.app_list.item(i).data(Qt.UserRole) == pkg
                       for i in range(self.app_list.count())):
                self._add_app_row(pkg, pkg, True)

    def _add_app_row(self, pkg, label, checked):
        item = QListWidgetItem(f"{label}  ({pkg})")
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        item.setData(Qt.UserRole, pkg)
        self.app_list.addItem(item)

    def _on_app_filter(self, text):
        needle = text.strip().lower()
        for i in range(self.app_list.count()):
            item = self.app_list.item(i)
            item.setHidden(bool(needle) and needle not in item.text().lower())

    def _on_add_custom_app(self):
        pkg = self.custom_pkg.text().strip()
        if not pkg:
            return
        for i in range(self.app_list.count()):
            if self.app_list.item(i).data(Qt.UserRole).lower() == pkg.lower():
                QMessageBox.information(self, "Debloat",
                                        "That package is already listed.")
                return
        self._add_app_row(pkg, pkg, True)
        customs = [self.app_list.item(i).data(Qt.UserRole)
                   for i in range(self.app_list.count())]
        builtin = {app["pkg"] for app in BLOATWARE_APPS}
        engine.save_custom_apps([p for p in customs if p not in builtin])
        self.custom_pkg.clear()
        self._log(f"Added custom package '{pkg}' to the removal list.")

    def _checked_app_pkgs(self):
        pkgs = []
        for i in range(self.app_list.count()):
            item = self.app_list.item(i)
            if item.checkState() == Qt.Checked and not item.isHidden():
                pkgs.append(item.data(Qt.UserRole))
        return pkgs

    # -- actions ------------------------------------------------------------
    def _run_worker(self, fn, on_done):
        self._set_busy(True)
        self._worker = _Worker(fn, self)
        self._worker.progressed.connect(self._log)
        self._worker.done.connect(on_done)
        self._worker.done.connect(lambda _r: self._set_busy(False))
        self._worker.start()

    def _on_restore_point(self):
        confirm = QMessageBox.question(
            self, "Restore Point",
            "Create a system restore point now?\n"
            "This lets Windows roll back if anything misbehaves.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if confirm != QMessageBox.Yes:
            return
        self._log("Creating system restore point (can take a minute)...")

        def job(log):
            ok, msg = engine.create_restore_point()
            log(f"Restore point: {msg}")
            return ok

        def finished(result):
            status, ok = result
            if status == "ok" and ok:
                self._restored_this_session = True
                self.restore_status.setText(
                    "Restore point created this session.")
            else:
                self.restore_status.setText(
                    "Restore point FAILED - see log. Proceed with caution.")
        self._run_worker(job, finished)

    def _ensure_restore_point(self, log):
        if self._restored_this_session:
            return True
        log("Creating automatic restore point before applying changes...")
        ok, msg = engine.create_restore_point("OmniTune debloat (auto)")
        log(f"Restore point: {msg}")
        self._restored_this_session = ok
        return ok

    def _on_apply(self):
        keys = self._checked_tweak_keys()
        if not keys:
            QMessageBox.information(self, "Debloat",
                                    "Tick at least one tweak first.")
            return
        confirm = QMessageBox.question(
            self, "Apply Tweaks",
            f"Apply {len(keys)} selected tweak(s)?\n"
            "A system restore point will be created first, and every\n"
            "change can be reverted from this tab.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if confirm != QMessageBox.Yes:
            return

        def job(log):
            if not self._ensure_restore_point(log):
                log("WARNING: continuing without a restore point.")
            backup = engine.load_backup()
            applied = 0
            for key in keys:
                tweak = get_tweak(key)
                try:
                    engine.apply_tweak(tweak, backup)
                    applied += 1
                    log(f"Applied: {tweak['name']}")
                except Exception as exc:  # noqa: BLE001 - per-tweak report
                    log(f"FAILED: {tweak['name']} - {exc}")
            log(f"Done: {applied}/{len(keys)} tweaks applied. "
                "Some changes (taskbar, Explorer) need sign-out to show.")
            return applied

        def finished(result):
            self._refresh_tweak_states()
        self._run_worker(job, finished)

    def _on_revert(self):
        keys = self._checked_tweak_keys()
        if not keys:
            QMessageBox.information(self, "Debloat",
                                    "Tick at least one tweak first.")
            return
        confirm = QMessageBox.question(
            self, "Revert Tweaks",
            f"Revert {len(keys)} selected tweak(s) to their previous values?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if confirm != QMessageBox.Yes:
            return

        def job(log):
            backup = engine.load_backup()
            reverted = 0
            for key in keys:
                tweak = get_tweak(key)
                try:
                    engine.revert_tweak(tweak, backup)
                    reverted += 1
                    log(f"Reverted: {tweak['name']}")
                except Exception as exc:  # noqa: BLE001 - per-tweak report
                    log(f"FAILED: {tweak['name']} - {exc}")
            log(f"Done: {reverted}/{len(keys)} tweaks reverted.")
            return reverted

        def finished(result):
            self._refresh_tweak_states()
        self._run_worker(job, finished)

    def _on_remove_apps(self):
        pkgs = self._checked_app_pkgs()
        if not pkgs:
            QMessageBox.information(self, "Debloat",
                                    "Tick at least one app first.")
            return
        confirm = QMessageBox.question(
            self, "Remove Apps",
            f"Remove {len(pkgs)} selected app package(s) for all users?\n"
            "This cannot be undone from here (reinstall from the Store).",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return

        def job(log):
            if not self._ensure_restore_point(log):
                log("WARNING: continuing without a restore point.")
            results = engine.remove_appx_packages(pkgs)
            ok_count = 0
            for pkg, (ok, msg) in results.items():
                log(f"{'Removed' if ok else 'FAILED'}: {pkg} - {msg}")
                ok_count += ok
            log(f"Done: {ok_count}/{len(pkgs)} packages removed.")
            return ok_count

        self._run_worker(job, lambda _r: None)

    def _on_reregister_apps(self):
        pkgs = self._checked_app_pkgs()
        if not pkgs:
            QMessageBox.information(self, "Debloat",
                                    "Tick at least one app first.")
            return
        self._log(f"Re-registering {len(pkgs)} app package(s)...")

        def job(log):
            results = engine.reregister_appx(pkgs)
            ok_count = 0
            for pkg, (ok, msg) in results.items():
                log(f"{'Re-registered' if ok else 'FAILED'}: {pkg} - {msg}")
                ok_count += ok
            log(f"Done: {ok_count}/{len(pkgs)} re-registered.")
            return ok_count

        self._run_worker(job, lambda _r: None)

    def _on_export_profile(self):
        keys = self._checked_tweak_keys()
        if not keys:
            QMessageBox.information(self, "Debloat",
                                    "Tick at least one tweak first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Tweak Profile", "omniture-debloat.json",
            "JSON files (*.json)")
        if not path:
            return
        try:
            count = engine.export_profile(keys, path)
        except OSError as exc:
            QMessageBox.warning(self, "Export failed", str(exc))
            return
        self._log(f"Exported profile with {count} tweak(s) to {path}.")

    def _on_import_profile(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Tweak Profile", "",
            "JSON files (*.json)")
        if not path:
            return
        try:
            keys = set(engine.import_profile(path))
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Import failed", str(exc))
            return
        matched = 0
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            cat = root.child(i)
            for j in range(cat.childCount()):
                child = cat.child(j)
                key = child.data(0, Qt.UserRole)
                if key in keys:
                    child.setCheckState(0, Qt.Checked)
                    matched += 1
        self._log(f"Imported profile: {matched} tweak(s) ticked "
                  f"({len(keys) - matched} unknown).")


def create_panel() -> QWidget:
    return DebloatPanel()
