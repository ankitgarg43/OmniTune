"""Test setup.

On Windows CI the real PySide6 is installed and every test runs, including
the GUI smoke test (offscreen platform). On machines without Qt (e.g. this
Linux VM, which lacks the GL system libraries), pure-logic tests still run:
PySide6 is replaced by a minimal stub and the GUI smoke test is skipped.
"""
import sys
import types

try:
    import PySide6.QtWidgets  # noqa: F401  (loads native libs; fails w/o GL)
    USING_QT_STUB = False
except ImportError:
    USING_QT_STUB = True
    _qt = types.ModuleType("PySide6")
    _widgets = types.ModuleType("PySide6.QtWidgets")
    for _name in ("QLabel", "QListWidget", "QVBoxLayout", "QWidget",
                  "QMainWindow", "QMessageBox", "QTabWidget"):
        setattr(_widgets, _name, type(_name, (), {}))
    _qt.QtWidgets = _widgets
    sys.modules["PySide6"] = _qt
    sys.modules["PySide6.QtWidgets"] = _widgets
    # No real Qt -> the GUI smoke test cannot run here.
    collect_ignore = ["test_smoke.py"]
