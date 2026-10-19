"""Smoke tests — run without a display (QT_QPA_PLATFORM=offscreen)."""
from PySide6.QtWidgets import QApplication, QTabWidget

from omniture import version
from omniture.app import MainWindow
from omniture.modules import debloat, disk, drivers, updates


def test_version_format():
    parts = version.__version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_modules_expose_panel_factory():
    for mod in (drivers, updates, debloat, disk):
        assert callable(mod.create_panel)
        assert mod.TITLE
        assert mod.DESCRIPTION
        assert mod.ROADMAP


def test_main_window_has_four_tabs():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert isinstance(window.tabs, QTabWidget)
    assert window.tabs.count() == 4
    assert window.tabs.tabText(0) == "Drivers"
    assert window.tabs.tabText(1) == "Updates"
    assert window.tabs.tabText(2) == "Debloat"
    assert window.tabs.tabText(3) == "Disk"
    window.close()
    app.quit()
