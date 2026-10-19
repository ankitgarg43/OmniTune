"""Driver management module.

Concept inspired by Snappy Driver Installer (GPL-3.0):
https://github.com/gtumanyan/SDI
Clean-room reimplementation — no SDI code is used.
"""
from PySide6.QtWidgets import QWidget

from . import make_panel

TITLE = "Drivers"
DESCRIPTION = (
    "Scan your hardware, check the status of every installed driver, and "
    "install or update drivers — from Windows Update, local INF packages, "
    "and (later milestone) offline driver packs."
)
ROADMAP = [
    "Enumerate all devices and hardware IDs (SetupAPI)",
    "Driver status: missing / outdated / up to date",
    "Install & update via Windows Update optional drivers",
    "Install from local driver folder / INF (pnputil)",
    "Offline driver-pack index support (torrent / 7z) — later milestone",
    "Driver export for technicians",
]


def create_panel() -> QWidget:
    return make_panel(TITLE, DESCRIPTION, ROADMAP)
