"""Windows Update management module.

Concept inspired by WuMgr (GPL-3.0):
https://github.com/DavidXanatos/wumgr
Clean-room reimplementation — no WuMgr code is used.
"""
from PySide6.QtWidgets import QWidget

from . import make_panel

TITLE = "Updates"
DESCRIPTION = (
    "Take back control of Windows Update: search for available updates, "
    "install them on your schedule, hide the ones you don't want, and "
    "uninstall problem updates — via the Windows Update Agent API."
)
ROADMAP = [
    "Search for available updates (Windows Update Agent API)",
    "Install selected updates with progress",
    "Hide / unhide updates",
    "Uninstall installed updates",
    "Update history view",
    "Automatic-update policy control (notify / download / manual)",
]


def create_panel() -> QWidget:
    return make_panel(TITLE, DESCRIPTION, ROADMAP)
