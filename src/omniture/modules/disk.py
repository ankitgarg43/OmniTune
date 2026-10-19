"""Disk usage analyzer module.

Concept inspired by WinDirStat (GPL-3.0):
https://github.com/windirstat/windirstat
Clean-room reimplementation — no WinDirStat code is used.
"""
from PySide6.QtWidgets import QWidget

from . import make_panel

TITLE = "Disk"
DESCRIPTION = (
    "See exactly what is eating your disk: scan any drive or folder, "
    "explore usage with an interactive treemap, find the largest files "
    "and duplicates, and clean up safely."
)
ROADMAP = [
    "Drive / folder scan with progress",
    "Interactive treemap visualization",
    "Largest-files view and file-type statistics",
    "Duplicate detection (hash-based)",
    "Safe cleanup: temp files, caches, Recycle Bin (with confirmation)",
    "Scan reports (CSV / JSON export)",
]


def create_panel() -> QWidget:
    return make_panel(TITLE, DESCRIPTION, ROADMAP)
